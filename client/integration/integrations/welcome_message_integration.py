"""
WelcomeMessageIntegration — интеграция модуля приветствия с EventBus

Назначение:
- Воспроизводит приветственное сообщение при запуске приложения
- Запрашивает серверную генерацию и передает аудио в SpeechPlaybackIntegration
"""

import asyncio
import contextlib
import logging
import sys
from pathlib import Path
from typing import Optional, Dict, Any
import numpy as np

from integration.core.event_bus import EventBus, EventPriority
from integration.core.state_manager import ApplicationStateManager
from integration.core.error_handler import ErrorHandler

# Импорт модуля приветствия
from modules.welcome_message.core.welcome_player import WelcomePlayer
from modules.welcome_message.core.types import WelcomeConfig, WelcomeResult
from modules.welcome_message.config.welcome_config import WelcomeConfigLoader

# Импорт конфигурации
from config.unified_config_loader import UnifiedConfigLoader

logger = logging.getLogger(__name__)


class WelcomeMessageIntegration:
    """Интеграция модуля приветствия с EventBus"""
    
    def __init__(
        self,
        event_bus: EventBus,
        state_manager: ApplicationStateManager,
        error_handler: ErrorHandler,
    ):
        self.event_bus = event_bus
        self.state_manager = state_manager
        self.error_handler = error_handler
        
        # Загружаем конфигурацию
        try:
            unified_config = UnifiedConfigLoader()
            config_loader = WelcomeConfigLoader.from_unified_config(unified_config)
            self.config = config_loader.load_config()
        except Exception as e:
            logger.error(f"❌ [WELCOME_INTEGRATION] Ошибка загрузки конфигурации: {e}")
            self.config = WelcomeConfig()
        
        # Создаем плеер приветствия
        self.welcome_player = WelcomePlayer(self.config)
        
        # Настраиваем коллбеки
        self.welcome_player.set_callbacks(
            on_started=self._on_welcome_started,
            on_completed=self._on_welcome_completed,
            on_error=self._on_welcome_error
        )
        
        self._initialized = False
        self._running = False
        # Состояние разрешения микрофона (granted/denied/not_determined/None)
        self._microphone_status: Optional[str] = None
        self._pending_welcome = False
        self._permission_prompted = False
        self._permission_recheck_task: Optional[asyncio.Task] = None
        self._enforce_permissions = self._detect_packaged_environment()
        if getattr(self.config, "ignore_microphone_permission", False) and self._enforce_permissions:
            logger.info("🎙️ [WELCOME_INTEGRATION] Игнорируем статус разрешения микрофона для приветствия")
            self._enforce_permissions = False
    
    async def initialize(self) -> bool:
        """Инициализация интеграции"""
        try:
            logger.info("🔧 [WELCOME_INTEGRATION] Инициализация...")
            
            # Подписываемся на события
            await self.event_bus.subscribe("app.startup", self._on_app_startup, EventPriority.MEDIUM)
            await self.event_bus.subscribe("permissions.status_checked", self._on_permission_event, EventPriority.HIGH)
            await self.event_bus.subscribe("permissions.changed", self._on_permission_event, EventPriority.HIGH)
            await self.event_bus.subscribe("permissions.requested", self._on_permission_event, EventPriority.MEDIUM)
            await self.event_bus.subscribe("permissions.integration_ready", self._on_permissions_ready, EventPriority.MEDIUM)
            
            self._initialized = True
            logger.info("✅ [WELCOME_INTEGRATION] Инициализирован")
            # Запрашиваем актуальный статус разрешений (не блокируем initialize)
            asyncio.create_task(self._request_initial_permission_status())
            return True
            
        except Exception as e:
            await self._handle_error(e, where="welcome.initialize")
            return False
    
    async def start(self) -> bool:
        """Запуск интеграции"""
        if not self._initialized:
            logger.error("❌ [WELCOME_INTEGRATION] Не инициализирован")
            return False
        
        self._running = True
        logger.info("✅ [WELCOME_INTEGRATION] Запущен")
        return True
    
    async def stop(self) -> bool:
        """Остановка интеграции"""
        try:
            self._running = False
            await self._cancel_permission_recheck_task()
            logger.info("✅ [WELCOME_INTEGRATION] Остановлен")
            return True
        except Exception as e:
            await self._handle_error(e, where="welcome.stop", severity="warning")
            return False
    
    async def _on_app_startup(self, event):
        """Обработка события запуска приложения"""
        try:
            if not self.config.enabled:
                logger.info("🔇 [WELCOME_INTEGRATION] Приветствие отключено в конфигурации")
                return
            
            logger.info("🚀 [WELCOME_INTEGRATION] Обработка запуска приложения")
            
            # Небольшая задержка для полной инициализации системы
            if self.config.delay_sec > 0:
                await asyncio.sleep(self.config.delay_sec)
            
            if not self._enforce_permissions:
                await self._play_welcome_message(trigger="app_startup")
                return

            # БЛОКИРУЕМ приложение до получения разрешения микрофона
            await self._wait_for_microphone_permission()
            
            # Только после получения разрешения продолжаем
            await self._play_welcome_message(trigger="app_startup")
            
        except Exception as e:
            await self._handle_error(e, where="welcome.on_app_startup", severity="warning")
    
    async def _play_welcome_message(self, trigger: str = "app_startup"):
        """Воспроизводит приветственное сообщение"""
        try:
            logger.info(f"🎵 [WELCOME_INTEGRATION] Начинаю воспроизведение приветствия (trigger={trigger})")
            
            # 🆕 ПЕРЕХОД В PROCESSING РЕЖИМ
            logger.info("🔄 [WELCOME_INTEGRATION] Переход в режим PROCESSING для приветствия")
            await self.event_bus.publish("mode.request", {
                "target": "PROCESSING",
                "source": "welcome_message",
                "reason": "welcome_playback"
            })
            
            # Воспроизводим через плеер
            result = await self.welcome_player.play_welcome()
            
            if result.success:
                logger.info(f"✅ [WELCOME_INTEGRATION] Приветствие воспроизведено: {result.method}, {result.duration_sec:.1f}s")
            else:
                logger.warning(f"⚠️ [WELCOME_INTEGRATION] Приветствие не удалось: {result.error}")
            
            # НЕ переключаем режим здесь - это будет сделано в _on_welcome_completed
            # после завершения воспроизведения аудио
            
        except Exception as e:
            # 🆕 ВОЗВРАТ В SLEEPING ПРИ ОШИБКЕ (с задержкой для видимости)
            logger.error("🔄 [WELCOME_INTEGRATION] Возврат в режим SLEEPING из-за ошибки")
            await asyncio.sleep(0.5)  # Небольшая задержка для видимости изменения иконки
            await self.event_bus.publish("mode.request", {
                "target": "SLEEPING",
                "source": "welcome_message", 
                "reason": "welcome_error"
            })
            await self._handle_error(e, where="welcome.play_message", severity="warning")
    
    def _on_welcome_started(self):
        """Коллбек начала воспроизведения приветствия"""
        try:
            logger.info("🎵 [WELCOME_INTEGRATION] Приветствие началось")
            # Публикуем событие начала
            method = "server" if getattr(self.config, "use_server", True) else "none"
            asyncio.create_task(self.event_bus.publish("welcome.started", {
                "text": self.config.text,
                "method": method  # Будет обновлено в _on_welcome_completed
            }))
        except Exception as e:
            logger.error(f"❌ [WELCOME_INTEGRATION] Ошибка в _on_welcome_started: {e}")
    
    def _on_welcome_completed(self, result: WelcomeResult):
        """Коллбек завершения воспроизведения приветствия"""
        try:
            logger.info(f"🎵 [WELCOME_INTEGRATION] Приветствие завершено: {result.method}, success={result.success}")
            
            # Публикуем событие завершения
            asyncio.create_task(self.event_bus.publish("welcome.completed", {
                "success": result.success,
                "method": result.method,
                "duration_sec": result.duration_sec,
                "error": result.error,
                "metadata": result.metadata or {}
            }))
            
            # Если есть аудио данные, отправляем их в SpeechPlaybackIntegration
            if result.success and result.method == "server":
                audio_data = self.welcome_player.get_audio_data()
                if audio_data is not None:
                    asyncio.create_task(self._send_audio_to_playback(audio_data))
            
            # 🆕 ВОЗВРАТ В SLEEPING РЕЖИМ после завершения воспроизведения
            # (это будет вызвано после завершения воспроизведения аудио)
            asyncio.create_task(self._return_to_sleeping_after_playback())
            
        except Exception as e:
            logger.error(f"❌ [WELCOME_INTEGRATION] Ошибка в _on_welcome_completed: {e}")
    
    def _on_welcome_error(self, error: str):
        """Коллбек ошибки воспроизведения приветствия"""
        try:
            logger.error(f"❌ [WELCOME_INTEGRATION] Ошибка приветствия: {error}")
            
            # Публикуем событие ошибки
            asyncio.create_task(self.event_bus.publish("welcome.failed", {
                "error": error,
                "text": self.config.text
            }))
            
            # 🆕 ВОЗВРАТ В SLEEPING РЕЖИМ при ошибке
            asyncio.create_task(self._return_to_sleeping_after_playback())
            
        except Exception as e:
            logger.error(f"❌ [WELCOME_INTEGRATION] Ошибка в _on_welcome_error: {e}")
    
    async def _return_to_sleeping_after_playback(self):
        """Возвращает приложение в режим SLEEPING после завершения воспроизведения"""
        try:
            # Слушаем событие завершения воспроизведения от SpeechPlaybackIntegration
            logger.info("🔄 [WELCOME_INTEGRATION] Ожидаю завершения воспроизведения...")
            
            # Создаем Future для ожидания события
            playback_completed = asyncio.Future()
            
            async def on_playback_completed(event):
                # Проверяем session_id вместо pattern, так как SpeechPlaybackIntegration
                # не публикует pattern в playback.completed
                session_id = event.get("data", {}).get("session_id", "")
                if "welcome_message" in session_id:
                    logger.info("🎵 [WELCOME_INTEGRATION] Получено событие завершения воспроизведения")
                    if not playback_completed.done():
                        playback_completed.set_result(True)
            
            # Подписываемся на событие завершения воспроизведения
            await self.event_bus.subscribe("playback.completed", on_playback_completed)
            
            try:
                # Ждем завершения воспроизведения с таймаутом
                await asyncio.wait_for(playback_completed, timeout=10.0)
            except asyncio.TimeoutError:
                logger.warning("⚠️ [WELCOME_INTEGRATION] Таймаут ожидания завершения воспроизведения")
            finally:
                # Отписываемся от события
                await self.event_bus.unsubscribe("playback.completed", on_playback_completed)
            
            logger.info("🔄 [WELCOME_INTEGRATION] Возврат в режим SLEEPING после завершения воспроизведения")
            await self.event_bus.publish("mode.request", {
                "target": "SLEEPING",
                "source": "welcome_message",
                "reason": "welcome_playback_completed"
            })
            
        except Exception as e:
            logger.error(f"❌ [WELCOME_INTEGRATION] Ошибка в _return_to_sleeping_after_playback: {e}")
    
    async def _send_audio_to_playback(self, audio_data: np.ndarray):
        """Отправляет аудио данные в SpeechPlaybackIntegration для воспроизведения"""
        try:
            logger.info(f"🎵 [WELCOME_INTEGRATION] Отправляю аудио в SpeechPlaybackIntegration: {len(audio_data)} сэмплов")
            
            # ОТЛАДКА: Проверяем формат данных
            logger.info(f"🔍 [WELCOME_INTEGRATION] Формат данных: dtype={audio_data.dtype}, shape={audio_data.shape}")
            logger.info(f"🔍 [WELCOME_INTEGRATION] Диапазон: min={audio_data.min()}, max={audio_data.max()}")
            metadata = self.welcome_player.get_audio_metadata() or {}
            sample_rate = int(metadata.get('sample_rate', self.config.sample_rate))
            channels = int(metadata.get('channels', self.config.channels))
            method = metadata.get('method', 'server')
            
            # ✅ ПРАВИЛЬНО: Передаем numpy массив напрямую в плеер
            # БЕЗ конвертации в bytes - плеер сам разберется с форматом
            await self.event_bus.publish("playback.raw_audio", {
                "audio_data": audio_data,  # numpy array
                "sample_rate": sample_rate,
                "channels": channels,
                "dtype": "int16",  # для информации
                "priority": 5,  # Высокий приоритет для приветствия
                "pattern": "welcome_message",
                "metadata": metadata,
                "method": method,
            })
            
            logger.info("✅ [WELCOME_INTEGRATION] Аудио отправлено в SpeechPlaybackIntegration")
            
        except Exception as e:
            logger.error(f"❌ [WELCOME_INTEGRATION] Ошибка отправки аудио: {e}")

    async def _on_permission_event(self, event: Dict[str, Any]):
        """Обработка событий статуса разрешений"""
        try:
            data = (event or {}).get("data") or {}
            event_type = (event or {}).get("type", "permissions.unknown")

            # Обновление по одному разрешению
            if "permission" in data:
                perm = data.get("permission")
                status = data.get("status") or data.get("new_status")
                self._process_permission_update(perm, status, source=event_type)

            # Пакетное обновление
            permissions_map = data.get("permissions")
            if permissions_map:
                self._process_permissions_map(permissions_map, source=event_type)

        except Exception as e:
            logger.error(f"❌ [WELCOME_INTEGRATION] Ошибка обработки события разрешений: {e}")

    async def _on_permissions_ready(self, event: Dict[str, Any]):
        """Получение начального статуса от PermissionsIntegration"""
        try:
            data = (event or {}).get("data") or {}
            permissions_map = data.get("permissions")
            if permissions_map:
                self._process_permissions_map(permissions_map, source="permissions.integration_ready")
        except Exception as e:
            logger.error(f"❌ [WELCOME_INTEGRATION] Ошибка обработки permissions.integration_ready: {e}")

    def _process_permissions_map(self, permissions_map: Dict[Any, Any], source: str):
        """Обновить статусы из словаря"""
        try:
            for perm_key, status_value in permissions_map.items():
                # Словарь может содержать PermissionResult или чистые статусы
                status = status_value
                if isinstance(status_value, dict):
                    status = status_value.get("status") or status_value.get("new_status")
                self._process_permission_update(perm_key, status, source=source)
        except Exception as e:
            logger.error(f"❌ [WELCOME_INTEGRATION] Ошибка разбора словаря разрешений ({source}): {e}")

    def _process_permission_update(self, raw_permission: Any, raw_status: Any, source: str):
        """Нормализует и сохраняет статус отдельного разрешения"""
        if raw_permission is None:
            return

        perm_name = getattr(raw_permission, "value", raw_permission)
        if perm_name is None:
            return
        perm_name = str(perm_name).lower()
        if perm_name != "microphone":
            return

        status_value = getattr(raw_status, "value", raw_status)
        if status_value is None:
            return

        status_normalized = str(status_value).lower()
        previous = self._microphone_status

        if previous == status_normalized:
            return

        self._microphone_status = status_normalized
        logger.info(
            "🎙️ [WELCOME_INTEGRATION] Статус микрофона обновлён: %s → %s (source=%s)",
            previous or "unknown",
            status_normalized,
            source,
        )

        if not self._enforce_permissions:
            return

        if status_normalized == "granted":
            self._pending_welcome = False
            self._permission_prompted = False
            asyncio.create_task(self._cancel_permission_recheck_task())
            # Если ожидали приветствие, запускаем его после получения разрешения
            if self.config.enabled and self.welcome_player:
                asyncio.create_task(self._play_welcome_message(trigger="permissions"))
        else:
            # Любой статус кроме granted означает, что приветствие пока нельзя воспроизвести
            self._pending_welcome = True
            self._schedule_permission_recheck()

    def _is_microphone_granted(self) -> bool:
        return (self._microphone_status or "").lower() == "granted"

    async def _prompt_microphone_permission(self):
        """Показывает инструкции и инициирует повторные проверки"""
        if not self._enforce_permissions:
            return
        if self._permission_prompted:
            self._schedule_permission_recheck()
            return

        self._permission_prompted = True
        logger.warning(
            "🎙️ [WELCOME_INTEGRATION] Требуется разрешение на микрофон. "
            "Откройте 'Системные настройки → Конфиденциальность и безопасность → Микрофон' и включите Nexy."
        )

        try:
            await self.event_bus.publish("permissions.request_required", {
                "source": "welcome_message",
                "permissions": ["microphone"],
            })
        except Exception as e:
            logger.error(f"❌ [WELCOME_INTEGRATION] Ошибка публикации запроса разрешений: {e}")

        await self._ensure_permission_status()
        self._schedule_permission_recheck()

    async def _ensure_permission_status(self):
        """Уточняет статус микрофона через PermissionsIntegration"""
        if not self._enforce_permissions:
            return
        try:
            await self.event_bus.publish("permissions.check_required", {
                "source": "welcome_message"
            })
        except Exception as e:
            logger.error(f"❌ [WELCOME_INTEGRATION] Ошибка запроса проверки разрешений: {e}")

    async def _wait_for_microphone_permission(self):
        """Блокируем приложение до получения разрешения микрофона"""
        max_attempts = 60  # 5 минут максимум (60 * 5 секунд)
        attempt = 0
        
        logger.info("🔒 [WELCOME_INTEGRATION] Блокируем приложение до получения разрешения микрофона")
        
        while attempt < max_attempts:
            await self._ensure_permission_status()
            
            if self._is_microphone_granted():
                logger.info("✅ [WELCOME_INTEGRATION] Разрешение микрофона получено, продолжаем запуск")
                return
            
            # Показываем инструкции пользователю только в первый раз
            if attempt == 0:
                await self._show_permission_instructions()
            
            # Ждем 5 секунд перед следующей проверкой
            await asyncio.sleep(5.0)
            attempt += 1
            
            # Показываем прогресс каждые 30 секунд
            if attempt % 6 == 0:  # 6 * 5 секунд = 30 секунд
                remaining_minutes = (max_attempts - attempt) // 12  # 12 * 5 секунд = 1 минута
                logger.info(f"⏳ [WELCOME_INTEGRATION] Ожидание разрешения микрофона... осталось ~{remaining_minutes} мин")
        
        # Если не получили разрешение за 5 минут - продолжаем без него
        logger.warning("⚠️ [WELCOME_INTEGRATION] Разрешение микрофона не получено за 5 минут, продолжаем без него")
        await self._show_timeout_message()

    async def _request_initial_permission_status(self):
        """Фоновый запрос статуса разрешений после инициализации"""
        if not self._enforce_permissions:
            return
        await asyncio.sleep(0)  # yield event loop
        await self._ensure_permission_status()

    def _schedule_permission_recheck(self, interval: float = 5.0, max_attempts: int = 12):
        """Периодически инициирует повторную проверку статуса"""
        if not self._enforce_permissions:
            return
        if self._is_microphone_granted():
            return

        if self._permission_recheck_task and not self._permission_recheck_task.done():
            return

        async def _recheck_loop():
            attempts = 0
            try:
                while not self._is_microphone_granted() and attempts < max_attempts:
                    await asyncio.sleep(interval)
                    attempts += 1
                    await self.event_bus.publish("permissions.check_required", {
                        "source": f"welcome_message.recheck#{attempts}"
                    })
            except asyncio.CancelledError:
                logger.debug("🛑 [WELCOME_INTEGRATION] Повторная проверка разрешений отменена")
                raise
            except Exception as e:
                logger.error(f"❌ [WELCOME_INTEGRATION] Ошибка фоновой проверки разрешений: {e}")
            finally:
                self._permission_recheck_task = None

        self._permission_recheck_task = asyncio.create_task(_recheck_loop())

    async def _cancel_permission_recheck_task(self):
        """Останавливает фоновую задачу проверки (если есть)"""
        if self._permission_recheck_task and not self._permission_recheck_task.done():
            self._permission_recheck_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._permission_recheck_task
        self._permission_recheck_task = None

    async def _show_permission_instructions(self):
        """Показывает инструкции пользователю для получения разрешения микрофона"""
        try:
            logger.warning(
                "🎙️ [WELCOME_INTEGRATION] ТРЕБУЕТСЯ РАЗРЕШЕНИЕ НА МИКРОФОН!\n"
                "📱 Откройте 'Системные настройки → Конфиденциальность и безопасность → Микрофон'\n"
                "🔧 Найдите 'Nexy' в списке и включите переключатель\n"
                "⏳ Приложение будет ждать до 5 минут..."
            )
            
            # Публикуем событие для показа уведомления в UI
            await self.event_bus.publish("permissions.request_required", {
                "source": "welcome_message",
                "permissions": ["microphone"],
                "blocking": True,
                "message": "Требуется разрешение на микрофон для работы Nexy"
            })
            
        except Exception as e:
            logger.error(f"❌ [WELCOME_INTEGRATION] Ошибка показа инструкций: {e}")

    async def _show_timeout_message(self):
        """Показывает сообщение о таймауте ожидания разрешения"""
        try:
            logger.warning(
                "⏰ [WELCOME_INTEGRATION] ТАЙМАУТ ОЖИДАНИЯ РАЗРЕШЕНИЯ!\n"
                "⚠️ Разрешение микрофона не получено за 5 минут\n"
                "🚀 Продолжаем запуск приложения без микрофона\n"
                "💡 Вы можете дать разрешение позже в настройках системы"
            )
            
            # Публикуем событие о таймауте
            await self.event_bus.publish("permissions.timeout", {
                "source": "welcome_message",
                "permissions": ["microphone"],
                "message": "Таймаут ожидания разрешения микрофона"
            })
            
        except Exception as e:
            logger.error(f"❌ [WELCOME_INTEGRATION] Ошибка показа сообщения о таймауте: {e}")

    @staticmethod
    def _detect_packaged_environment() -> bool:
        if getattr(sys, "frozen", False) or hasattr(sys, "_MEIPASS"):
            return True
        try:
            exe_path = Path(sys.argv[0]).resolve()
            return ".app/Contents/MacOS" in str(exe_path)
        except Exception:
            return False

    
    async def _handle_error(self, e: Exception, *, where: str, severity: str = "error"):
        """Обработка ошибок"""
        if hasattr(self.error_handler, 'handle'):
            await self.error_handler.handle(
                error=e,
                category="welcome_message",
                severity=severity,
                context={"where": where}
            )
        else:
            logger.error(f"Welcome message error at {where}: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Получить статус интеграции"""
        return {
            "initialized": self._initialized,
            "running": self._running,
            "config": {
                "enabled": self.config.enabled,
                "text": self.config.text,
                "delay_sec": self.config.delay_sec
            },
            "player_state": self.welcome_player.state.value if hasattr(self.welcome_player, 'state') else "unknown"
        }
