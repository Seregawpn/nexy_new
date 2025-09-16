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
from modules.permissions.core.types import PermissionEvent

# Импорты интеграции
from integration.core.event_bus import EventBus, EventPriority
from integration.core.state_manager import ApplicationStateManager, AppMode
from integration.core.error_handler import ErrorHandler, ErrorSeverity, ErrorCategory

logger = logging.getLogger(__name__)

@dataclass
class PermissionsIntegrationConfig:
    """Конфигурация PermissionsIntegration"""
    check_interval: int = 30  # Интервал проверки разрешений в секундах
    auto_request_required: bool = True  # Автоматически запрашивать обязательные разрешения
    show_instructions: bool = True  # Показывать инструкции для разрешений
    open_preferences: bool = True  # Автоматически открывать настройки
    debug_mode: bool = False

class PermissionsIntegration:
    """Интеграция PermissionManager с EventBus и ApplicationStateManager"""
    
    def __init__(self, event_bus: EventBus, state_manager: ApplicationStateManager, 
                 error_handler: ErrorHandler, config: PermissionsIntegrationConfig):
        self.event_bus = event_bus
        self.state_manager = state_manager
        self.error_handler = error_handler
        self.config = config
        
        # PermissionManager (обертываем существующий модуль)
        self.permission_manager: Optional[PermissionManager] = None
        
        # Состояние интеграции
        self.is_initialized = False
        self.is_running = False
        self.is_monitoring = False
        
        # Кэш статусов разрешений
        self.permission_statuses: Dict[PermissionType, PermissionStatus] = {}
        
        # Критичные разрешения для работы приложения
        self.critical_permissions = {
            PermissionType.MICROPHONE,
            PermissionType.SCREEN_CAPTURE,
            PermissionType.NETWORK
        }
    
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
            
            # Настраиваем callbacks для PermissionManager
            self.permission_manager.add_callback(self._on_permission_changed)
            
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
            
            # Проверяем все разрешения
            await self._check_all_permissions()
            
            # Запрашиваем обязательные разрешения если включено
            if self.config.auto_request_required:
                await self._request_required_permissions()
            
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
            
            # Если критичные разрешения не предоставлены, блокируем приложение
            if not critical_granted:
                await self._block_application()
            else:
                await self._unblock_application()
            
        except Exception as e:
            logger.error(f"❌ Ошибка проверки критичных разрешений: {e}")
    
    async def _block_application(self):
        """Заблокировать приложение из-за отсутствия разрешений"""
        try:
            logger.warning("🚫 Блокировка приложения - отсутствуют критичные разрешения")
            
            # Переводим приложение в режим ожидания
            self.state_manager.set_mode(AppMode.SLEEPING)
            
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
            new_mode = event.data.get("mode")
            logger.info(f"🔄 Обработка смены режима в PermissionsIntegration: {new_mode.value}")
            
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
                "auto_request_required": self.config.auto_request_required,
                "show_instructions": self.config.show_instructions,
                "open_preferences": self.config.open_preferences,
                "debug_mode": self.config.debug_mode
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
