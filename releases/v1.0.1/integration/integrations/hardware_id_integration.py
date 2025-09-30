"""
HardwareIdIntegration — тонкая обёртка над modules.hardware_id
Задачи:
- Получить стабильный hardware_id один раз на запуск и кэшировать в памяти
- Отдавать ID по запросу мгновенно через EventBus
- Поддерживать принудительное обновление без блокировки потребителей
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from integration.core.event_bus import EventBus, EventPriority
from integration.core.state_manager import ApplicationStateManager
from integration.core.error_handler import ErrorHandler

# Модуль hardware_id
from modules.hardware_id.core import HardwareIdentifier, HardwareIdResult, HardwareIdStatus

# Конфиг (опционально используем unified_config для интеграционных параметров)
from config.unified_config_loader import UnifiedConfigLoader

logger = logging.getLogger(__name__)


@dataclass
class HardwareIdIntegrationConfig:
    """Небольшая конфигурация уровня интеграции (не дублирует модуль)."""
    wait_ready_timeout_ms: int = 1500
    refresh_on_ttl_expired: bool = True


class HardwareIdIntegration:
    """Интеграция HardwareIdentifier с EventBus и StateManager."""

    def __init__(
        self,
        event_bus: EventBus,
        state_manager: ApplicationStateManager,
        error_handler: ErrorHandler,
        config: Optional[HardwareIdIntegrationConfig] = None,
    ):
        self.event_bus = event_bus
        self.state_manager = state_manager
        self.error_handler = error_handler

        # Интеграционная конфигурация (с безопасными умолчаниями)
        if config is None:
            try:
                uc = UnifiedConfigLoader()
                data = uc._load_config()
                cfg = (data.get('integrations', {}) or {}).get('hardware_id', {})
                config = HardwareIdIntegrationConfig(
                    wait_ready_timeout_ms=int(cfg.get('wait_ready_timeout_ms', 1500)),
                    refresh_on_ttl_expired=bool(cfg.get('refresh_on_ttl_expired', True)),
                )
            except Exception:
                config = HardwareIdIntegrationConfig()
        self.config = config

        # Модульный идентификатор
        self._identifier: Optional[HardwareIdentifier] = None

        # Памятный кэш результата
        self._id_result: Optional[HardwareIdResult] = None
        self._ready_event: asyncio.Event = asyncio.Event()
        self._lock: asyncio.Lock = asyncio.Lock()

        self._initialized = False
        self._running = False

    # --------------------- Lifecycle ---------------------
    async def initialize(self) -> bool:
        try:
            logger.info("Initializing HardwareIdIntegration...")
            self._identifier = HardwareIdentifier()

            # Подписки на события
            await self.event_bus.subscribe("app.startup", self._on_app_startup, EventPriority.HIGH)
            await self.event_bus.subscribe("app.shutdown", self._on_app_shutdown, EventPriority.MEDIUM)
            await self.event_bus.subscribe("hardware.id_request", self._on_id_request, EventPriority.HIGH)
            await self.event_bus.subscribe("hardware.id_refresh", self._on_id_refresh, EventPriority.MEDIUM)

            self._initialized = True
            logger.info("HardwareIdIntegration initialized")
            return True
        except Exception as e:
            await self._handle_error(e, where="hardware_id.initialize")
            return False

    async def start(self) -> bool:
        if not self._initialized:
            logger.error("HardwareIdIntegration not initialized")
            return False
        if self._running:
            return True
        self._running = True
        logger.info("HardwareIdIntegration started")
        
        # Принудительно публикуем Hardware ID при старте для gRPC клиента
        try:
            await self._ensure_id_ready()
            if self._id_result:
                await self._publish_obtained(self._id_result)
                logger.info(f"Hardware ID published on startup: {self._id_result.uuid[:8]}...")
        except Exception as e:
            logger.warning(f"Failed to publish Hardware ID on startup: {e}")
        
        return True

    async def stop(self) -> bool:
        self._running = False
        return True

    # --------------------- Event Handlers ---------------------
    async def _on_app_startup(self, event):
        """Первичное получение ID на старте приложения."""
        try:
            await self._ensure_id_ready()
            if self._id_result:
                await self._publish_obtained(self._id_result)
        except Exception as e:
            await self._handle_error(e, where="hardware_id.on_app_startup")

    async def _on_app_shutdown(self, event):
        try:
            # Ничего специфичного; оставляем для симметрии
            pass
        except Exception as e:
            await self._handle_error(e, where="hardware_id.on_app_shutdown", severity="warning")

    async def _on_id_request(self, event):
        """Отдаёт ID по запросу. Ожидает готовности один раз (по настройке)."""
        try:
            data = (event or {}).get("data", {})
            request_id = data.get("request_id")
            wait_ready = data.get("wait_ready", True)

            if not self._id_result and wait_ready:
                # Ждём готовности с таймаутом
                try:
                    await asyncio.wait_for(self._ensure_id_ready(), timeout=self.config.wait_ready_timeout_ms / 1000.0)
                except asyncio.TimeoutError:
                    logger.warning("hardware.id_request: timeout waiting for id ready")

            # Если всё ещё нет — пытаемся немедленно получить без блокировки
            if not self._id_result:
                asyncio.create_task(self._obtain_id_background(force=False))

            # Публикуем ответ тем, что есть (может быть None)
            if self._id_result:
                await self._publish_response(self._id_result, request_id=request_id)
            else:
                await self.event_bus.publish("hardware.id_error", {
                    "error": "id_unavailable",
                    "cause": "not_ready",
                    "can_retry": True,
                })
        except Exception as e:
            await self._handle_error(e, where="hardware_id.on_id_request")

    async def _on_id_refresh(self, event):
        """Принудительное обновление ID (в фоне)."""
        try:
            asyncio.create_task(self._obtain_id_background(force=True))
        except Exception as e:
            await self._handle_error(e, where="hardware_id.on_id_refresh", severity="warning")

    # --------------------- Core logic ---------------------
    async def _ensure_id_ready(self):
        """Гарантирует, что ID получен и сохранён в памяти (однократно)."""
        if self._id_result:
            # Проверка TTL и фонового рефреша
            if self.config.refresh_on_ttl_expired:
                try:
                    info = self._identifier.get_cache_info() if self._identifier else {}
                    if info and isinstance(info, dict):
                        ttl = info.get("ttl_remaining")
                        is_valid = info.get("is_valid")
                        if isinstance(ttl, int) and ttl <= 0 and is_valid is False:
                            asyncio.create_task(self._obtain_id_background(force=False))
                except Exception:
                    pass
            return

        async with self._lock:
            if self._id_result:
                return
            await self._obtain_id(force=False)

    async def _obtain_id(self, force: bool) -> Optional[HardwareIdResult]:
        if not self._identifier:
            return None
        try:
            res = await asyncio.get_event_loop().run_in_executor(None, self._identifier.get_hardware_id, force)
            self._id_result = res
            self._ready_event.set()
            logger.info(self._fmt_log(f"Hardware ID ready ({res.source}, cached={res.cached})"))
            return res
        except Exception as e:
            await self._handle_error(e, where="hardware_id.obtain")
            return None

    async def _obtain_id_background(self, force: bool):
        try:
            res = await self._obtain_id(force=force)
            if res:
                await self._publish_obtained(res)
        except Exception as e:
            await self._handle_error(e, where="hardware_id.obtain_background", severity="warning")

    # --------------------- Publishing helpers ---------------------
    async def _publish_obtained(self, res: HardwareIdResult):
        try:
            await self.event_bus.publish("hardware.id_obtained", {
                "uuid": res.uuid,
                "source": res.source,
                "cached": res.cached,
                "status": res.status.value if hasattr(res.status, 'value') else str(res.status),
            })
        except Exception as e:
            logger.debug(f"Failed to publish hardware.id_obtained: {e}")

    async def _publish_response(self, res: HardwareIdResult, *, request_id: Optional[str]):
        try:
            await self.event_bus.publish("hardware.id_response", {
                "request_id": request_id,
                "uuid": res.uuid,
                "source": res.source,
                "cached": res.cached,
                "status": res.status.value if hasattr(res.status, 'value') else str(res.status),
            })
        except Exception as e:
            logger.debug(f"Failed to publish hardware.id_response: {e}")

    # --------------------- Utilities ---------------------
    def _fmt_log(self, msg: str) -> str:
        try:
            u = (self._id_result.uuid if self._id_result and self._id_result.uuid else "")
            masked = (u[:8] + "…") if u else "unknown"
            return f"{msg} — uuid={masked}"
        except Exception:
            return msg

    async def _handle_error(self, e: Exception, *, where: str, severity: str = "error"):
        if hasattr(self.error_handler, 'handle'):
            await self.error_handler.handle(
                error=e,
                category="hardware_id",
                severity=severity,
                context={"where": where}
            )
        else:
            logger.error(f"Error in HardwareIdIntegration ({where}): {e}")

    # --------------------- Introspection ---------------------
    def get_status(self) -> Dict[str, Any]:
        res = self._id_result
        return {
            "initialized": self._initialized,
            "running": self._running,
            "id_ready": res is not None,
            "source": getattr(res, 'source', None) if res else None,
            "cached": getattr(res, 'cached', None) if res else None,
            "status": (res.status.value if res and hasattr(res.status, 'value') else None),
        }

