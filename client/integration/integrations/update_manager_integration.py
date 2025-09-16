"""
Интеграция модуля обновлений с EventBus и ApplicationStateManager
"""

import asyncio
import logging
from typing import Optional, Dict, Any

# Импорты core компонентов
from integration.core.event_bus import EventBus, EventPriority
from integration.core.state_manager import ApplicationStateManager, AppMode
from integration.core.error_handler import ErrorHandler, ErrorSeverity, ErrorCategory

# Импорты модуля обновлений
from modules.update_manager import UpdateManager, UpdateConfig, UpdateStatus, UpdateInfo

logger = logging.getLogger(__name__)

class UpdateManagerIntegration:
    """Интеграция модуля обновлений"""
    
    def __init__(self, event_bus: EventBus, state_manager: ApplicationStateManager, 
                 error_handler: ErrorHandler, config: 'UpdateManagerIntegrationConfig'):
        self.event_bus = event_bus
        self.state_manager = state_manager
        self.error_handler = error_handler
        self.config = config
        
        # Создаем конфигурацию обновлений
        self.update_config = UpdateConfig(
            enabled=config.enabled,
            check_interval=config.check_interval,
            check_time=config.check_time,
            auto_install=config.auto_install,
            announce_updates=config.announce_updates,
            check_on_startup=config.check_on_startup,
            appcast_url=config.appcast_url,
            retry_attempts=config.retry_attempts,
            retry_delay=config.retry_delay,
            silent_mode=config.silent_mode,
            log_updates=config.log_updates
        )
        
        # Создаем менеджер обновлений
        self.update_manager = UpdateManager(
            config=self.update_config,
            event_bus=self.event_bus,
            state_manager=self.state_manager
        )
        
        self.is_running = False
        
    async def initialize(self) -> bool:
        """Инициализация интеграции"""
        try:
            logger.info("🔄 Инициализация UpdateManagerIntegration...")
            
            # Проверяем, включен ли менеджер обновлений
            if not self.update_manager.is_enabled():
                logger.warning("⚠️ Менеджер обновлений отключен - Sparkle Framework недоступен")
                return True  # Не критическая ошибка
            
            # Настраиваем обработчики событий
            await self._setup_event_handlers()
            
            logger.info("✅ UpdateManagerIntegration инициализирован")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации UpdateManagerIntegration: {e}")
            await self.error_handler.handle_error(
                severity=ErrorSeverity.WARNING,
                category=ErrorCategory.INTEGRATION,
                message=f"Ошибка инициализации UpdateManagerIntegration: {e}",
                context={"where": "UpdateManagerIntegration.initialize"}
            )
            return False
    
    async def start(self) -> bool:
        """Запуск интеграции"""
        try:
            if not self.update_manager.is_enabled():
                logger.info("⏭️ Пропускаю запуск UpdateManagerIntegration - отключен")
                return True
                
            logger.info("🚀 Запуск UpdateManagerIntegration...")
            
            # Запускаем менеджер обновлений
            await self.update_manager.start()
            
            self.is_running = True
            logger.info("✅ UpdateManagerIntegration запущен")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска UpdateManagerIntegration: {e}")
            await self.error_handler.handle_error(
                severity=ErrorSeverity.ERROR,
                category=ErrorCategory.INTEGRATION,
                message=f"Ошибка запуска UpdateManagerIntegration: {e}",
                context={"where": "UpdateManagerIntegration.start"}
            )
            return False
    
    async def stop(self) -> bool:
        """Остановка интеграции"""
        try:
            if not self.is_running:
                return True
                
            logger.info("🛑 Остановка UpdateManagerIntegration...")
            
            # Останавливаем менеджер обновлений
            await self.update_manager.stop()
            
            self.is_running = False
            logger.info("✅ UpdateManagerIntegration остановлен")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка остановки UpdateManagerIntegration: {e}")
            await self.error_handler.handle_error(
                severity=ErrorSeverity.ERROR,
                category=ErrorCategory.INTEGRATION,
                message=f"Ошибка остановки UpdateManagerIntegration: {e}",
                context={"where": "UpdateManagerIntegration.stop"}
            )
            return False
    
    async def _setup_event_handlers(self):
        """Настройка обработчиков событий"""
        # Подписываемся на события обновлений
        await self.event_bus.subscribe("update.available", self._on_update_available, EventPriority.HIGH)
        await self.event_bus.subscribe("update.status_changed", self._on_update_status_changed, EventPriority.MEDIUM)
        await self.event_bus.subscribe("update.restarting", self._on_update_restarting, EventPriority.HIGH)
        
        # Подписываемся на события приложения
        await self.event_bus.subscribe("app.startup", self._on_app_startup, EventPriority.MEDIUM)
        await self.event_bus.subscribe("app.shutdown", self._on_app_shutdown, EventPriority.HIGH)
        
    async def _on_update_available(self, event_data):
        """Обработка события доступности обновления"""
        try:
            version = event_data.get("version", "неизвестная")
            build_number = event_data.get("build_number", 0)
            
            logger.info(f"📢 Доступно обновление версии {version} (build {build_number})")
            
            # Публикуем событие для других компонентов
            await self.event_bus.publish("integration.update_available", {
                "version": version,
                "build_number": build_number,
                "integration": "update_manager"
            })
            
        except Exception as e:
            logger.error(f"Ошибка обработки события update.available: {e}")
    
    async def _on_update_status_changed(self, event_data):
        """Обработка события смены статуса обновления"""
        try:
            old_status = event_data.get("old_status", "неизвестный")
            new_status = event_data.get("new_status", "неизвестный")
            
            logger.info(f"🔄 Статус обновления: {old_status} → {new_status}")
            
            # Публикуем событие для других компонентов
            await self.event_bus.publish("integration.update_status_changed", {
                "old_status": old_status,
                "new_status": new_status,
                "integration": "update_manager"
            })
            
        except Exception as e:
            logger.error(f"Ошибка обработки события update.status_changed: {e}")
    
    async def _on_update_restarting(self, event_data):
        """Обработка события перезапуска приложения"""
        try:
            version = event_data.get("version", "неизвестная")
            build_number = event_data.get("build_number", 0)
            
            logger.info(f"🔄 Перезапуск приложения с версией {version} (build {build_number})")
            
            # Публикуем событие для других компонентов
            await self.event_bus.publish("integration.update_restarting", {
                "version": version,
                "build_number": build_number,
                "integration": "update_manager"
            })
            
        except Exception as e:
            logger.error(f"Ошибка обработки события update.restarting: {e}")
    
    async def _on_app_startup(self, event_data):
        """Обработка события запуска приложения"""
        try:
            logger.info("🚀 Обработка запуска приложения в UpdateManagerIntegration")
            
            # Публикуем событие для других компонентов
            await self.event_bus.publish("integration.app_startup", {
                "integration": "update_manager"
            })
            
        except Exception as e:
            logger.error(f"Ошибка обработки события app.startup: {e}")
    
    async def _on_app_shutdown(self, event_data):
        """Обработка события завершения приложения"""
        try:
            logger.info("🛑 Обработка завершения приложения в UpdateManagerIntegration")
            
            # Останавливаем менеджер обновлений
            await self.stop()
            
            # Публикуем событие для других компонентов
            await self.event_bus.publish("integration.app_shutdown", {
                "integration": "update_manager"
            })
            
        except Exception as e:
            logger.error(f"Ошибка обработки события app.shutdown: {e}")
    
    def get_current_status(self) -> UpdateStatus:
        """Получение текущего статуса обновлений"""
        return self.update_manager.get_current_status()
    
    def get_available_update(self) -> Optional[UpdateInfo]:
        """Получение информации об доступном обновлении"""
        return self.update_manager.get_available_update()
    
    def is_enabled(self) -> bool:
        """Проверка, включен ли менеджер обновлений"""
        return self.update_manager.is_enabled()
    
    def is_running(self) -> bool:
        """Проверка, запущен ли менеджер обновлений"""
        return self.is_running
    
    def get_status(self) -> Dict[str, Any]:
        """Получить статус UpdateManagerIntegration"""
        return {
            "initialized": self.is_initialized,
            "running": self.is_running,
            "enabled": self.is_enabled(),
            "current_status": self.get_current_status().value if self.get_current_status() else "unknown",
            "available_update": self.get_available_update() is not None
        }

class UpdateManagerIntegrationConfig:
    """Конфигурация интеграции обновлений"""
    
    def __init__(self, enabled: bool = True, check_interval: int = 24, 
                 check_time: str = "02:00", auto_install: bool = True,
                 announce_updates: bool = False, check_on_startup: bool = True,
                 appcast_url: str = "", retry_attempts: int = 3,
                 retry_delay: int = 300, silent_mode: bool = True,
                 log_updates: bool = True):
        self.enabled = enabled
        self.check_interval = check_interval
        self.check_time = check_time
        self.auto_install = auto_install
        self.announce_updates = announce_updates
        self.check_on_startup = check_on_startup
        self.appcast_url = appcast_url
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        self.silent_mode = silent_mode
        self.log_updates = log_updates
