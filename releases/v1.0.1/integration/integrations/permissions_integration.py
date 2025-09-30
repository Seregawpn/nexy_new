"""
Permissions Integration
Обертка для PermissionManager с интеграцией в EventBus
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

# Импорты модулей
from modules.permissions import PermissionManager, PermissionType, PermissionStatus, PermissionResult
from modules.permissions.core.types import PermissionEvent, PermissionConfig

# Импорт конфигурации
from config.unified_config_loader import UnifiedConfigLoader

# Импорты интеграции
from integration.core.event_bus import EventBus, EventPriority
from integration.core.state_manager import ApplicationStateManager, AppMode
from integration.core.error_handler import ErrorHandler, ErrorSeverity, ErrorCategory

logger = logging.getLogger(__name__)

# macOS системные импорты для триггеров разрешений
try:
    from AppKit import NSBundle
    from Quartz import AXIsProcessTrustedWithOptions, kAXTrustedCheckOptionPrompt
    from AVFoundation import AVCaptureDevice, AVMediaTypeAudio
    from PyObjCTools import AppHelper
    MACOS_IMPORTS_AVAILABLE = True
except ImportError:
    MACOS_IMPORTS_AVAILABLE = False
    logger.warning("macOS системные импорты недоступны - триггеры разрешений отключены")

# Убираем дублированную конфигурацию - используем PermissionConfig из модуля

class PermissionsIntegration:
    """Интеграция PermissionManager с EventBus и ApplicationStateManager"""
    
    def __init__(self, event_bus: EventBus, state_manager: ApplicationStateManager, 
                 error_handler: ErrorHandler, config: Optional[PermissionConfig] = None):
        self.event_bus = event_bus
        self.state_manager = state_manager
        self.error_handler = error_handler
        # Загружаем конфигурацию из unified_config.yaml
        unified_config = UnifiedConfigLoader()
        if config is None:
            # Создаем конфигурацию модуля из unified_config
            config_data = unified_config._load_config()
            perm_cfg = config_data['integrations']['permissions']
            
            config = PermissionConfig(
                required_permissions=[
                    PermissionType.MICROPHONE,
                    PermissionType.SCREEN_CAPTURE,
                    PermissionType.NETWORK
                ],  # Из модуля
                check_interval=perm_cfg.get('check_interval', 30.0),
                auto_open_preferences=perm_cfg.get('auto_open_preferences', True),
                show_instructions=perm_cfg.get('show_instructions', True)
            )
        
        self.config = config
        
        # PermissionManager (обертываем существующий модуль)
        self.permission_manager: Optional[PermissionManager] = None
        
        # Состояние интеграции
        self.is_initialized = False
        self.is_running = False
        self.is_monitoring = False
        
        # Кэш статусов разрешений
        self.permission_statuses: Dict[PermissionType, PermissionStatus] = {}
        
        # Критичные разрешения для работы приложения (ПОЛНОСТЬЮ ОТКЛЮЧЕНЫ - НЕ БЛОКИРУЕМ НИЧЕГО)
        self.critical_permissions = set()  # Пустое множество - НЕ блокируем приложение даже без разрешений
        # Текущее состояние блокировки приложения (для устранения дублей событий)
        self._app_blocked: Optional[bool] = None
        # Флаг, чтобы не запускать параллельные запросы прав
        self._request_in_progress: bool = False
    
    async def initialize(self) -> bool:
        """Инициализация интеграции"""
        try:
            logger.info("🔧 Инициализация PermissionsIntegration...")
            
            # Создаем PermissionManager (обертываем существующий модуль)
            self.permission_manager = PermissionManager()
            
            # Инициализируем PermissionManager
            success = await self.permission_manager.initialize()
            if not success:
                logger.error("❌ Ошибка инициализации PermissionManager")
                return False
            
            # Настраиваем обработчики событий
            await self._setup_event_handlers()
            
            # КРИТИЧНО: Только проверяем разрешения, НЕ запрашиваем автоматически
            logger.info("🔐 Проверяем статус разрешений...")
            await self._check_all_permissions()
            
            # Настраиваем callbacks для PermissionManager (если метод существует)
            # Пропускаем add_callback - метод не реализован в PermissionManager
            
            self.is_initialized = True
            logger.info("✅ PermissionsIntegration инициализирован")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации PermissionsIntegration: {e}")
            return False
    
    async def start(self) -> bool:
        """Запуск интеграции"""
        try:
            if not self.is_initialized:
                logger.error("PermissionsIntegration не инициализирован")
                return False
            
            if self.is_running:
                logger.warning("PermissionsIntegration уже запущен")
                return True
            
            logger.info("🚀 Запуск PermissionsIntegration...")
            
            # Проверяем все разрешения (только статус, без запросов)
            await self._check_all_permissions()
            
            # НЕ запрашиваем разрешения автоматически - пользователь должен сделать это вручную
            # if self.config.auto_open_preferences and not self._request_in_progress:
            #     await self._request_required_permissions()
            
            # Запускаем мониторинг
            await self.permission_manager.start_monitoring()
            self.is_monitoring = True
            
            self.is_running = True
            
            # Публикуем событие готовности
            await self.event_bus.publish("permissions.integration_ready", {
                "integration": "permissions",
                "status": "running",
                "permissions": self.permission_statuses
            })
            
            logger.info("✅ PermissionsIntegration запущен")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска PermissionsIntegration: {e}")
            return False
    
    async def stop(self) -> bool:
        """Остановка интеграции"""
        try:
            if not self.is_running:
                logger.warning("PermissionsIntegration не запущен")
                return True
            
            logger.info("⏹️ Остановка PermissionsIntegration...")
            
            # Останавливаем мониторинг
            if self.is_monitoring:
                await self.permission_manager.stop_monitoring()
                self.is_monitoring = False
            
            # Очищаем ресурсы
            if self.permission_manager:
                await self.permission_manager.cleanup()
            
            self.is_running = False
            
            logger.info("✅ PermissionsIntegration остановлен")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка остановки PermissionsIntegration: {e}")
            return False
    
    async def _setup_event_handlers(self):
        """Настройка обработчиков событий"""
        try:
            # Подписываемся на события приложения
            await self.event_bus.subscribe("app.startup", self._on_app_startup, EventPriority.HIGH)
            await self.event_bus.subscribe("app.shutdown", self._on_app_shutdown, EventPriority.HIGH)
            await self.event_bus.subscribe("app.mode_changed", self._on_mode_changed, EventPriority.MEDIUM)
            
            # Подписываемся на события разрешений
            await self.event_bus.subscribe("permissions.check_required", self._on_check_required, EventPriority.HIGH)
            await self.event_bus.subscribe("permissions.request_required", self._on_request_required, EventPriority.HIGH)
            
            logger.info("✅ Обработчики событий PermissionsIntegration настроены")
            
        except Exception as e:
            logger.error(f"❌ Ошибка настройки обработчиков событий: {e}")
    
    async def _check_all_permissions(self):
        """Проверить все разрешения"""
        try:
            logger.info("🔍 Проверка всех разрешений...")
            
            results = await self.permission_manager.check_all_permissions()
            
            # Обновляем кэш статусов
            for perm_type, result in results.items():
                self.permission_statuses[perm_type] = result.status
                
                # Публикуем событие для каждого разрешения
                await self.event_bus.publish("permissions.status_checked", {
                    "permission": perm_type.value,
                    "status": result.status.value,
                    "success": result.success,
                    "message": result.message
                })
            
            # Проверяем критичные разрешения
            await self._check_critical_permissions()
            
            logger.info("✅ Проверка всех разрешений завершена")
            
        except Exception as e:
            logger.error(f"❌ Ошибка проверки разрешений: {e}")
    
    async def _request_required_permissions(self):
        """Запросить обязательные разрешения"""
        try:
            logger.info("📝 Запрос обязательных разрешений...")
            if self._request_in_progress:
                logger.info("⚠️ Запрос прав уже выполняется - пропускаем повторный запуск")
                return
            self._request_in_progress = True

            # НЕ выполняем автоматические запросы - только проверяем статус
            # if MACOS_IMPORTS_AVAILABLE:
            #     await self._request_permissions_sequential()

            results = await self.permission_manager.request_required_permissions()
            
            # Обновляем кэш статусов
            for perm_type, result in results.items():
                self.permission_statuses[perm_type] = result.status
                
                # Публикуем событие для каждого разрешения
                await self.event_bus.publish("permissions.requested", {
                    "permission": perm_type.value,
                    "status": result.status.value,
                    "success": result.success,
                    "message": result.message
                })
            
            logger.info("✅ Запрос обязательных разрешений завершен")
            
        except Exception as e:
            logger.error(f"❌ Ошибка запроса обязательных разрешений: {e}")
        finally:
            self._request_in_progress = False
    
    async def _request_permissions_sequential(self):
        """Последовательный запрос прав на главном потоке UI.
        Порядок: Microphone → ScreenCapture → Accessibility/InputMonitoring (deep-link при отказе).
        """
        try:
            import asyncio
            import subprocess

            logger.info("🔔 Старт последовательного запроса прав...")

            # 1) Microphone (completion handler, UI thread)
            mic_future: asyncio.Future = asyncio.get_event_loop().create_future()

            def _mic_request():
                try:
                    def mic_handler(granted):
                        try:
                            if not mic_future.done():
                                mic_future.set_result(bool(granted))
                        except Exception as e:
                            if not mic_future.done():
                                mic_future.set_exception(e)
                    AVCaptureDevice.requestAccessForMediaType_completionHandler_(AVMediaTypeAudio, mic_handler)
                except Exception as e:
                    if not mic_future.done():
                        mic_future.set_exception(e)

            AppHelper.callAfter(_mic_request)
            mic_granted = await mic_future
            logger.info(f"🎤 Microphone: {'granted' if mic_granted else 'denied'}")
            # НЕ открываем настройки автоматически
            # if not mic_granted:
            #     subprocess.run(["open", "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone"], check=False)

            # 2) Screen Capture (blocking call, prefer main thread, but acceptable via worker)
            try:
                from Quartz import CGPreflightScreenCaptureAccess, CGRequestScreenCaptureAccess
            except Exception as e:
                logger.warning(f"Quartz ScreenCapture API недоступен: {e}")
                CGPreflightScreenCaptureAccess = None
                CGRequestScreenCaptureAccess = None

            if CGPreflightScreenCaptureAccess and CGRequestScreenCaptureAccess:
                has_sc = bool(CGPreflightScreenCaptureAccess())
                if not has_sc:
                    logger.info("📸 ScreenCapture not granted → requesting...")
                    # Выполняем запрос в отдельном потоке, чтобы не блокировать loop
                    sc_granted = await asyncio.to_thread(CGRequestScreenCaptureAccess)
                    logger.info(f"📸 ScreenCapture: {'granted' if sc_granted else 'denied'}")
                    # НЕ открываем настройки автоматически
                    # if not sc_granted:
                    #     subprocess.run(["open", "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture"], check=False)

            # 3) Accessibility (prompt, no completion)
            try:
                logger.info("♿ Проверка Accessibility...")
                trusted = bool(AXIsProcessTrustedWithOptions({kAXTrustedCheckOptionPrompt: False}))  # НЕ показываем prompt
                # НЕ открываем настройки автоматически
                # if not trusted:
                #     subprocess.run(["open", "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"], check=False)
                #     subprocess.run(["open", "x-apple.systempreferences:com.apple.preference.security?Privacy_ListenEvent"], check=False)
            except Exception as e:
                logger.warning(f"Accessibility request error: {e}")

            logger.info("✅ Последовательный запрос прав завершен")

        except Exception as e:
            logger.error(f"❌ Ошибка последовательного запроса прав: {e}")
    
    async def _check_critical_permissions(self):
        """Проверить критичные разрешения"""
        try:
            critical_granted = True
            
            for perm_type in self.critical_permissions:
                status = self.permission_statuses.get(perm_type, PermissionStatus.NOT_DETERMINED)
                if status != PermissionStatus.GRANTED:
                    critical_granted = False
                    break
            
            # Публикуем событие о статусе критичных разрешений
            await self.event_bus.publish("permissions.critical_status", {
                "all_granted": critical_granted,
                "permissions": {
                    perm.value: self.permission_statuses.get(perm, PermissionStatus.NOT_DETERMINED).value
                    for perm in self.critical_permissions
                }
            })
            
            # Избегаем дублей: вызываем блокировку/разблокировку только при смене состояния
            if not critical_granted:
                if self._app_blocked is not True:
                    await self._block_application()
                    self._app_blocked = True
            else:
                if self._app_blocked is not False:
                    await self._unblock_application()
                    self._app_blocked = False
            
        except Exception as e:
            logger.error(f"❌ Ошибка проверки критичных разрешений: {e}")
    
    async def _block_application(self):
        """Заблокировать приложение из-за отсутствия разрешений"""
        try:
            logger.warning("🚫 Блокировка приложения - отсутствуют критичные разрешения")
            
            # Запрашиваем переход в SLEEPING централизованно
            await self.event_bus.publish("mode.request", {
                "target": AppMode.SLEEPING,
                "source": "permissions"
            })
            
            # Публикуем событие блокировки
            await self.event_bus.publish("permissions.app_blocked", {
                "reason": "missing_critical_permissions",
                "permissions": {
                    perm.value: self.permission_statuses.get(perm, PermissionStatus.NOT_DETERMINED).value
                    for perm in self.critical_permissions
                }
            })
            
        except Exception as e:
            logger.error(f"❌ Ошибка блокировки приложения: {e}")
    
    async def _unblock_application(self):
        """Разблокировать приложение"""
        try:
            logger.info("✅ Разблокировка приложения - все критичные разрешения предоставлены")
            
            # Публикуем событие разблокировки
            await self.event_bus.publish("permissions.app_unblocked", {
                "reason": "all_critical_permissions_granted",
                "permissions": {
                    perm.value: self.permission_statuses.get(perm, PermissionStatus.NOT_DETERMINED).value
                    for perm in self.critical_permissions
                }
            })
            
        except Exception as e:
            logger.error(f"❌ Ошибка разблокировки приложения: {e}")
    
    # Обработчики событий EventBus
    
    async def _on_app_startup(self, event):
        """Обработка запуска приложения"""
        try:
            logger.info("🚀 Обработка запуска приложения в PermissionsIntegration")
            await self._check_all_permissions()
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки запуска приложения: {e}")
    
    async def _on_app_shutdown(self, event):
        """Обработка завершения приложения"""
        try:
            logger.info("⏹️ Обработка завершения приложения в PermissionsIntegration")
            await self.stop()
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки завершения приложения: {e}")
    
    async def _on_mode_changed(self, event):
        """Обработка смены режима приложения"""
        try:
            # EventBus события приходят как dict
            if isinstance(event, dict):
                data = event.get("data") or {}
                new_mode = data.get("mode")
            else:
                data = getattr(event, "data", {}) or {}
                new_mode = data.get("mode")

            printable_mode = getattr(new_mode, "value", None) or str(new_mode)
            logger.info(f"🔄 Обработка смены режима в PermissionsIntegration: {printable_mode}")
            
            # Если переходим в режим прослушивания, проверяем разрешения
            if new_mode == AppMode.LISTENING:
                await self._check_critical_permissions()
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки смены режима: {e}")
    
    async def _on_check_required(self, event):
        """Обработка запроса проверки обязательных разрешений"""
        try:
            logger.info("🔍 Обработка запроса проверки обязательных разрешений")
            await self._check_all_permissions()
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки запроса проверки: {e}")
    
    async def _on_request_required(self, event):
        """Обработка запроса обязательных разрешений"""
        try:
            logger.info("📝 Обработка запроса обязательных разрешений")
            await self._request_required_permissions()
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки запроса разрешений: {e}")
    
    def _on_permission_changed(self, event: PermissionEvent):
        """Обработка изменения разрешения от PermissionManager"""
        try:
            # Обновляем кэш
            self.permission_statuses[event.permission] = event.new_status
            
            # Публикуем событие
            asyncio.create_task(self.event_bus.publish("permissions.changed", {
                "permission": event.permission.value,
                "old_status": event.old_status.value,
                "new_status": event.new_status.value,
                "timestamp": event.timestamp
            }))
            
            # Проверяем критичные разрешения
            asyncio.create_task(self._check_critical_permissions())
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки изменения разрешения: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Получить статус интеграции"""
        return {
            "is_initialized": self.is_initialized,
            "is_running": self.is_running,
            "is_monitoring": self.is_monitoring,
            "permission_manager": {
                "initialized": self.permission_manager is not None,
                "monitoring": self.is_monitoring
            },
            "permissions": {
                perm.value: status.value 
                for perm, status in self.permission_statuses.items()
            },
            "critical_permissions": {
                perm.value: self.permission_statuses.get(perm, PermissionStatus.NOT_DETERMINED).value
                for perm in self.critical_permissions
            },
            "config": {
                "check_interval": self.config.check_interval,
                "auto_open_preferences": self.config.auto_open_preferences,
                "show_instructions": self.config.show_instructions,
                "required_permissions": [p.value for p in self.config.required_permissions]
            }
        }
    
    async def check_permission(self, permission_type: PermissionType) -> PermissionResult:
        """Проверить конкретное разрешение"""
        if not self.permission_manager:
            return PermissionResult(
                success=False,
                permission=permission_type,
                status=PermissionStatus.ERROR,
                message="PermissionManager не инициализирован"
            )
        
        return await self.permission_manager.check_permission(permission_type)
    
    async def request_permission(self, permission_type: PermissionType) -> PermissionResult:
        """Запросить конкретное разрешение"""
        if not self.permission_manager:
            return PermissionResult(
                success=False,
                permission=permission_type,
                status=PermissionStatus.ERROR,
                message="PermissionManager не инициализирован"
            )
        
        return await self.permission_manager.request_permission(permission_type)
    
    def are_critical_permissions_granted(self) -> bool:
        """Проверить, предоставлены ли критичные разрешения"""
        for perm_type in self.critical_permissions:
            status = self.permission_statuses.get(perm_type, PermissionStatus.NOT_DETERMINED)
            if status != PermissionStatus.GRANTED:
                return False
        return True
    
    async def _request_all_required_permissions(self):
        """Централизованно запрашиваем все необходимые разрешения"""
        try:
            if not self.permission_manager:
                logger.error("❌ PermissionManager не инициализирован")
                return
            
            logger.info("🔐 Запрашиваем все необходимые разрешения централизованно...")
            
            # Получаем список необходимых разрешений из конфигурации
            required_permissions = self.config.required_permissions if self.config else [
                PermissionType.MICROPHONE,
                PermissionType.SCREEN_CAPTURE,
                PermissionType.NETWORK
            ]
            
            # Запрашиваем все разрешения последовательно
            for permission_type in required_permissions:
                logger.info(f"🔐 Запрашиваем разрешение: {permission_type.value}")
                result = await self.permission_manager.request_permission(permission_type)
                
                if result.success:
                    logger.info(f"✅ Разрешение {permission_type.value} получено")
                else:
                    logger.warning(f"⚠️ Разрешение {permission_type.value} не получено: {result.message}")
                
                # Небольшая пауза между запросами
                await asyncio.sleep(1)
            
            logger.info("✅ Централизованный запрос разрешений завершен")
            
        except Exception as e:
            logger.error(f"❌ Ошибка централизованного запроса разрешений: {e}")
