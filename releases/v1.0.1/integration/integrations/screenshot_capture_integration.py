"""
ScreenshotCaptureIntegration - Интеграция модуля захвата экрана с EventBus
Назначение: выполнить один захват скриншота при входе в PROCESSING и опубликовать результат
"""

import asyncio
import logging
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any
import subprocess
import shlex
import os
import datetime

from integration.core.event_bus import EventBus, EventPriority
from integration.core.state_manager import ApplicationStateManager, AppMode
from integration.core.error_handler import ErrorHandler

# Модуль захвата скриншотов
from modules.screenshot_capture.core.screenshot_capture import ScreenshotCapture
from modules.screenshot_capture.core.types import (
    ScreenshotConfig, ScreenshotFormat, ScreenshotQuality, ScreenshotRegion
)

# Конфиг
from config.unified_config_loader import UnifiedConfigLoader

logger = logging.getLogger(__name__)


@dataclass
class ScreenshotCaptureIntegrationConfig:
    format: str = "jpeg"  # только JPEG
    max_width: int = 1920
    max_height: int = 1080
    quality: int = 85
    region: str = "full_screen"  # full_screen|primary_monitor|custom


class ScreenshotCaptureIntegration:
    """Интеграция с модулем ScreenshotCapture"""

    def __init__(
        self,
        event_bus: EventBus,
        state_manager: ApplicationStateManager,
        error_handler: ErrorHandler,
    ):
        self.event_bus = event_bus
        self.state_manager = state_manager
        self.error_handler = error_handler
        self._initialized = False
        self._running = False

        # Сессии/идемпотентность
        self._last_session_id: Optional[float] = None
        self._captured_for_session: Optional[float] = None
        self._screen_permission_granted: Optional[bool] = None

        # Компоненты
        self._capture: Optional[ScreenshotCapture] = None
        self._config = self._load_config()
        self._prepared_screens: Dict[float, Dict[str, Any]] = {}
        self._prepare_tasks: Dict[float, asyncio.Task] = {}

    def _load_config(self) -> ScreenshotCaptureIntegrationConfig:
        try:
            loader = UnifiedConfigLoader()
            cfg = loader.get_screen_capture_config()
            return ScreenshotCaptureIntegrationConfig(
                format=str(cfg.get("format", "jpeg")).lower(),
                max_width=int(cfg.get("max_width", 1920)),
                max_height=int(cfg.get("max_height", 1080)),
                quality=int(cfg.get("quality", 85)),
                region=str(cfg.get("region", "full_screen")).lower() if isinstance(cfg.get("region", "full_screen"), str) else "full_screen",
            )
        except Exception:
            return ScreenshotCaptureIntegrationConfig()

    async def initialize(self) -> bool:
        try:
            # Пытаемся инициализировать модуль захвата
            try:
                self._capture = ScreenshotCapture(self._build_module_config())
                logger.info("ScreenshotCaptureIntegration: capture module ready")
            except Exception as e:
                # Если модуль недоступен (нет bridge/pyobjc) — работаем в degraded-режиме
                self._capture = None
                logger.warning(f"ScreenshotCaptureIntegration: disabled (module unavailable): {e}")

            # Подписки на события — даже в degraded-режиме, чтобы отдавать screenshot.error
            await self.event_bus.subscribe("app.mode_changed", self._on_mode_changed, EventPriority.HIGH)
            await self.event_bus.subscribe("voice.recording_stop", self._on_voice_recording_stop, EventPriority.HIGH)
            
            # Дополнительная подписка для отладки
            logger.info("🔧 ScreenshotCapture: Подписки настроены - app.mode_changed, voice.recording_stop")
            # Подписки на статусы разрешений, чтобы не пытаться снимать без Screen Recording
            try:
                await self.event_bus.subscribe("permissions.status_checked", self._on_permission_status, EventPriority.MEDIUM)
                await self.event_bus.subscribe("permissions.critical_status", self._on_permissions_critical, EventPriority.MEDIUM)
            except Exception:
                pass

            self._initialized = True
            logger.info("ScreenshotCaptureIntegration initialized")
            # Плановая очистка старых файлов
            try:
                asyncio.create_task(self._cleanup_old_screenshots())
            except Exception:
                pass
            return True
        except Exception as e:
            logger.error(f"Failed to initialize ScreenshotCaptureIntegration: {e}")
            return True  # не блокируем всё приложение

    async def start(self) -> bool:
        if not self._initialized:
            logger.error("ScreenshotCaptureIntegration not initialized")
            return False
        if self._running:
            return True
        
        # Проверяем разрешения Screen Capture перед запуском
        await self._check_screen_capture_permissions()
        
        self._running = True
        logger.info("ScreenshotCaptureIntegration started")
        return True

    async def stop(self) -> bool:
        self._running = False
        logger.info("ScreenshotCaptureIntegration stopped")
        return True

    def _build_module_config(self) -> ScreenshotConfig:
        # Маппинг качества (интеграция хранит int, модуль использует Enum уровней)
        q = self._config.quality
        if q >= 95:
            quality_enum = ScreenshotQuality.MAXIMUM
        elif q >= 85:
            quality_enum = ScreenshotQuality.HIGH
        elif q >= 70:
            quality_enum = ScreenshotQuality.MEDIUM
        else:
            quality_enum = ScreenshotQuality.LOW

        # Формат — только JPEG
        fmt = (self._config.format or "jpeg").lower()
        format_enum = ScreenshotFormat.JPEG

        # Регион
        region_map = {
            "full_screen": ScreenshotRegion.FULL_SCREEN,
            "primary_monitor": ScreenshotRegion.PRIMARY_MONITOR,
            "custom": ScreenshotRegion.CUSTOM,
        }
        region_enum = region_map.get(self._config.region, ScreenshotRegion.FULL_SCREEN)

        return ScreenshotConfig(
            format=format_enum,
            quality=quality_enum,
            region=region_enum,
            max_width=1400,
            max_height=900,
            timeout=5.0,
        )

    async def _on_voice_recording_stop(self, event: Dict[str, Any]):
        try:
            data = (event or {}).get("data", {})
            session_id = data.get("session_id")
            self._last_session_id = session_id
            
            logger.info(f"🎤 ScreenshotCapture: Получено voice.recording_stop, session_id={session_id}")
            
            # ПРЯМОЙ ТРИГГЕР: захватываем скриншот сразу при остановке записи
            # (это происходит при переходе в PROCESSING)
            if session_id is not None:
                if self._captured_for_session == session_id:
                    logger.debug("ScreenshotCaptureIntegration: already captured for session (voice_stop)")
                    return
                if session_id in self._prepared_screens:
                    logger.info(f"📸 ScreenshotCapture: Используем подготовленный скриншот для session {session_id}")
                    await self._publish_prepared(session_id)
                else:
                    logger.info(f"📸 ScreenshotCapture: ПРЯМОЙ ЗАХВАТ по voice.recording_stop, session_id={session_id}")
                    await self._capture_once(session_id=session_id)
                
        except Exception as e:
            logger.error(f"ScreenshotCaptureIntegration: error in voice_recording_stop: {e}")

    async def _on_mode_changed(self, event: Dict[str, Any]):
        try:
            data = (event or {}).get("data", {})
            mode = data.get("mode")
            logger.info(f"🔍 ScreenshotCapture: Получено событие app.mode_changed - mode={mode} (type: {type(mode)})")
            
            # Проверяем режим (может быть enum или строка)
            if mode == AppMode.LISTENING or mode == "listening" or str(mode) == "listening":
                session_id = self._last_session_id
                if session_id is not None:
                    logger.debug(f"ScreenshotCapture: LISTENING detected, preparing screenshot for session {session_id}")
                    await self._schedule_preparation(session_id)
                return

            if mode != AppMode.PROCESSING and mode != "processing" and str(mode) != "processing":
                logger.debug(f"ScreenshotCapture: Игнорируем режим {mode}, ждем PROCESSING")
                return

            sid = self._last_session_id
            if sid is not None and self._captured_for_session == sid:
                logger.debug("ScreenshotCaptureIntegration: already captured for session")
                return
            logger.info(f"📸 ScreenshotCaptureIntegration: app entered PROCESSING, session_id={sid}")
            if self._screen_permission_granted is False:
                await self.event_bus.publish("screenshot.error", {
                    "session_id": sid,
                    "error": "permissions_denied",
                })
                logger.info("Screenshot skipped: screen recording permission denied")
                return
            if sid is not None and sid in self._prepared_screens:
                await self._publish_prepared(sid)
            else:
                await self._capture_once(session_id=sid)
        except Exception as e:
            logger.error(f"ScreenshotCaptureIntegration: error in mode_changed: {e}")

    async def _on_state_changed(self, event: Dict[str, Any]):
        """Резервный триггер по старому событию состояния"""
        try:
            new_mode = (event or {}).get("data", {}).get("new_mode")
            # В старом ивенте StateManager кладёт данные без вложенного data
            if new_mode is None and isinstance(event, dict):
                new_mode = event.get("new_mode") or ((event.get("data") or {}).get("new_mode"))
            
            logger.info(f"🔍 ScreenshotCapture: Получено событие app.state_changed - new_mode={new_mode} (type: {type(new_mode)})")
            
            # Проверяем режим (может быть enum или строка)
            if new_mode != AppMode.PROCESSING and new_mode != "processing" and str(new_mode) != "processing":
                logger.debug(f"ScreenshotCapture: Игнорируем режим {new_mode} в state_changed, ждем PROCESSING")
                return
                
            sid = self._last_session_id
            logger.info(f"📸 ScreenshotCaptureIntegration: state_changed→PROCESSING, session_id={sid}")
            if self._screen_permission_granted is False:
                await self.event_bus.publish("screenshot.error", {
                    "session_id": sid,
                    "error": "permissions_denied",
                })
                return
            await self._capture_once(session_id=sid)
        except Exception as e:
            logger.error(f"ScreenshotCaptureIntegration: error in state_changed: {e}")

    async def _capture_once(self, session_id: Optional[float]):
        if not self._capture:
            # Fallback: используем системную утилиту screencapture (macOS)
            ok, out_path, meta = await self._fallback_capture_cli()
            if ok and out_path:
                await self.event_bus.publish("screenshot.captured", {
                    "session_id": session_id,
                    "image_path": str(out_path),
                    "format": "jpeg",
                    "width": meta.get("width"),
                    "height": meta.get("height"),
                    "size_bytes": meta.get("size_bytes"),
                    "mime_type": "image/jpeg",
                    "capture_time": 0.0,
                })
                self._captured_for_session = session_id
                logger.info(f"Screenshot (CLI) captured: {out_path}")
            else:
                logger.info("ScreenshotCaptureIntegration: module unavailable, publishing screenshot.error(module_unavailable)")
                await self.event_bus.publish("screenshot.error", {
                    "session_id": session_id,
                    "error": "module_unavailable",
                })
            return
        try:
            await asyncio.sleep(0.05)
            # Выполняем захват (в фоне внутри модуля)
            result = await self._capture.capture_screenshot()
            if result and result.success and result.data:
                await self._store_and_publish(session_id, result)
            else:
                await self.event_bus.publish("screenshot.error", {
                    "session_id": session_id,
                    "error": (result.error if result else "unknown"),
                })
                logger.warning(f"Screenshot capture failed: {(result.error if result else 'unknown')}")
        except Exception as e:
            logger.error(f"ScreenshotCaptureIntegration: unexpected error: {e}")
            await self.event_bus.publish("screenshot.error", {
                "session_id": session_id,
                "error": str(e),
            })

    async def _fallback_capture_cli(self) -> (bool, Optional[Path], Dict[str, Any]):
        """Пытается сделать скриншот через системную утилиту screencapture (macOS).
        Возвращает (ok, path, meta)."""
        try:
            tmp_dir = Path(tempfile.gettempdir()) / "nexy_screenshots"
            tmp_dir.mkdir(parents=True, exist_ok=True)
            out_path = tmp_dir / f"shot_{int(asyncio.get_event_loop().time()*1000)}.jpg"

            # Захват всего экрана без звука, в JPEG
            cmd = f"screencapture -x -t jpg {shlex.quote(str(out_path))}"
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0 or not out_path.exists():
                logger.warning(f"screencapture failed rc={proc.returncode}, err={stderr.decode().strip()}")
                return False, None, {}

            # При необходимости ограничим размер (макс. стороны) через sips
            try:
                max_w = int(self._config.max_width or 0)
                max_h = int(self._config.max_height or 0)
                max_side = max(max_w, max_h)
                if max_side > 0:
                    resize_cmd = f"sips -Z {max_side} {shlex.quote(str(out_path))}"
                    proc2 = await asyncio.create_subprocess_shell(
                        resize_cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    await proc2.communicate()
            except Exception as e:
                logger.debug(f"sips resize skipped/failed: {e}")

            # Получим размеры через sips
            width = height = None
            try:
                info_cmd = f"sips -g pixelWidth -g pixelHeight {shlex.quote(str(out_path))}"
                proc3 = await asyncio.create_subprocess_shell(
                    info_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                out, _ = await proc3.communicate()
                text = out.decode()
                # Ищем строки вида: pixelWidth: 1440
                for line in text.splitlines():
                    if "pixelWidth:" in line:
                        try:
                            width = int(line.split(":")[-1].strip())
                        except Exception:
                            pass
                    if "pixelHeight:" in line:
                        try:
                            height = int(line.split(":")[-1].strip())
                        except Exception:
                            pass
            except Exception as e:
                logger.debug(f"sips info failed: {e}")

            size_bytes = None
            try:
                size_bytes = os.path.getsize(out_path)
            except Exception:
                pass

            meta = {"width": width, "height": height, "size_bytes": size_bytes}
            return True, out_path, meta
        except Exception as e:
            logger.debug(f"CLI capture fallback failed: {e}")
            return False, None, {}

    async def _on_permission_status(self, event: Dict[str, Any]):
        try:
            data = (event or {}).get("data", {})
            perm = data.get("permission")
            status = data.get("status")
            if str(perm) == "screen_capture":
                self._screen_permission_granted = (status == "granted")
        except Exception:
            pass

    async def _on_permissions_critical(self, event: Dict[str, Any]):
        try:
            data = (event or {}).get("data", {})
            perms = data.get("permissions", {}) or {}
            sc = perms.get("screen_capture")
            if sc is not None:
                self._screen_permission_granted = (sc == "granted")
        except Exception:
            pass

    async def _cleanup_old_screenshots(self, ttl_hours: int = 24):
        """Удаляет файлы скриншотов старше ttl_hours из tmp каталога."""
        try:
            base = Path(tempfile.gettempdir()) / "nexy_screenshots"
            if not base.exists():
                return
            cutoff = datetime.datetime.now().timestamp() - ttl_hours * 3600
            removed = 0
            for p in base.glob("shot_*.jpg"):
                try:
                    if p.stat().st_mtime < cutoff:
                        p.unlink()
                        removed += 1
                except Exception:
                    continue
            if removed:
                logger.info(f"ScreenshotCleanup: removed {removed} old files")
        except Exception:
            pass

    def get_status(self) -> Dict[str, Any]:
        return {
            "initialized": self._initialized,
            "running": self._running,
            "last_session_id": self._last_session_id,
            "captured_for_session": self._captured_for_session,
        }

    async def _schedule_preparation(self, session_id: float):
        if session_id in self._prepare_tasks and not self._prepare_tasks[session_id].done():
            return
        if self._screen_permission_granted is False or not self._capture:
            return
        task = asyncio.create_task(self._prepare_screenshot(session_id))
        self._prepare_tasks[session_id] = task
        task.add_done_callback(lambda _: self._prepare_tasks.pop(session_id, None))

    async def _prepare_screenshot(self, session_id: float):
        try:
            result = await asyncio.wait_for(self._capture.capture_screenshot(), timeout=1.0)
            if result and result.success and result.data:
                self._prepared_screens[session_id] = {
                    "result": result,
                    "created": datetime.datetime.now(),
                }
                logger.debug(f"✅ Предварительный скриншот подготовлен для session {session_id}")
        except Exception as e:
            logger.debug(f"⚠️ Не удалось подготовить скриншот заранее для session {session_id}: {e}")

    async def _publish_prepared(self, session_id: float):
        payload = self._prepared_screens.pop(session_id, None)
        if not payload:
            await self._capture_once(session_id=session_id)
            return
        result = payload.get("result")
        await self._store_and_publish(session_id, result)

    async def _store_and_publish(self, session_id: Optional[float], result):
        tmp_dir = Path(tempfile.gettempdir()) / "nexy_screenshots"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        filename = f"shot_{int(asyncio.get_event_loop().time()*1000)}.jpg"
        out_path = tmp_dir / filename

        import base64
        raw = base64.b64decode(result.data.base64_data)
        out_path.write_bytes(raw)

        size_bytes = None
        try:
            size_bytes = os.path.getsize(out_path)
        except Exception:
            pass

        await self.event_bus.publish("screenshot.captured", {
            "session_id": session_id,
            "image_path": str(out_path),
            "format": "jpeg",
            "width": result.data.width,
            "height": result.data.height,
            "size_bytes": size_bytes,
            "mime_type": "image/jpeg",
            "capture_time": result.capture_time,
        })
        self._captured_for_session = session_id
        logger.info(f"Screenshot captured: {out_path}")
        try:
            asyncio.create_task(self._cleanup_old_screenshots())
        except Exception:
            pass

    async def _check_screen_capture_permissions(self):
        """Проверить разрешения Screen Capture"""
        try:
            # Пробуем системный preflight API, без Bundle ID
            try:
                from Quartz import CGPreflightScreenCaptureAccess  # type: ignore
            except Exception:
                CGPreflightScreenCaptureAccess = None

            granted = False
            if CGPreflightScreenCaptureAccess is not None:
                try:
                    granted = bool(CGPreflightScreenCaptureAccess())
                except Exception:
                    granted = False
            else:
                # Фоллбек: пробуем создать изображение всего экрана
                try:
                    from Quartz import CGWindowListCreateImage, kCGWindowListOptionOnScreenOnly, kCGNullWindowID, kCGWindowImageDefault  # type: ignore
                    rect = ((0, 0), (1, 1))
                    img = CGWindowListCreateImage(rect, kCGWindowListOptionOnScreenOnly, kCGNullWindowID, kCGWindowImageDefault)
                    granted = bool(img)
                except Exception:
                    granted = False

            if not granted:
                logger.info("ℹ️ Screen Capture not accessible - screenshots will be disabled")
                self._capture = None
                logger.info("🔄 ScreenshotCapture disabled due to missing Screen Capture access")
            else:
                logger.info("✅ Screen Capture accessible (preflight/probe succeeded)")
                
        except Exception as e:
            logger.info(f"ℹ️ Screen Capture probe failed: {e}")
            self._capture = None
