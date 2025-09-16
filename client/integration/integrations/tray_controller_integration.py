"""
TrayController Integration
Обертка для TrayController с интеграцией в EventBus
Четкое разделение ответственности без дублирования
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

# Импорты модулей (НЕ дублируем логику!)
from modules.tray_controller import TrayController, TrayStatus, TrayConfig
from modules.tray_controller.core.tray_types import TrayEvent

# Импорты интеграции
from core.event_bus import EventBus, EventPriority
from core.state_manager import ApplicationStateManager, AppMode
from core.error_handler import ErrorHandler, ErrorSeverity, ErrorCategory

logger = logging.getLogger(__name__)

@dataclass
class TrayControllerConfig:
    """Конфигурация TrayController Integration"""
    icon_size: int = 16
    show_status_in_menu: bool = True
    enable_notifications: bool = True
    auto_update_status: bool = True
    debug_mode: bool = False

class TrayControllerIntegration:
    """Интеграция TrayController с EventBus и ApplicationStateManager"""
    
    def __init__(self, event_bus: EventBus, state_manager: ApplicationStateManager, 
                 error_handler: ErrorHandler, config: TrayControllerConfig):
        self.event_bus = event_bus
        self.state_manager = state_manager
        self.error_handler = error_handler
        self.config = config
        
        # TrayController (обертываем существующий модуль)
        self.tray_controller: Optional[TrayController] = None
        
        # Состояние интеграции
        self.is_initialized = False
        self.is_running = False
        
        # Маппинг режимов приложения на статусы трея
        self.mode_to_status = {
            AppMode.SLEEPING: TrayStatus.SLEEPING,
            AppMode.LISTENING: TrayStatus.LISTENING,
            AppMode.PROCESSING: TrayStatus.PROCESSING,
            AppMode.SPEAKING: TrayStatus.PROCESSING  # Во время воспроизведения тоже PROCESSING
        }
    
    async def initialize(self) -> bool:
        """Инициализация интеграции"""
        try:
            logger.info("🔧 Инициализация TrayControllerIntegration...")
            
            # Создаем TrayController (обертываем существующий модуль)
            self.tray_controller = TrayController()
            
            # Инициализируем TrayController
            success = await self.tray_controller.initialize()
            if not success:
                logger.error("❌ Ошибка инициализации TrayController")
                return False
            
            # Настраиваем обработчики событий
            await self._setup_event_handlers()
            
            self.is_initialized = True
            logger.info("✅ TrayControllerIntegration инициализирован")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации TrayControllerIntegration: {e}")
            return False
    
    async def start(self) -> bool:
        """Запуск интеграции"""
        try:
            if not self.is_initialized:
                logger.error("TrayControllerIntegration не инициализирован")
                return False
            
            if self.is_running:
                logger.warning("TrayControllerIntegration уже запущен")
                return True
            
            logger.info("🚀 Запуск TrayControllerIntegration...")
            
            # Запускаем TrayController
            success = await self.tray_controller.start()
            if not success:
                logger.error("❌ Ошибка запуска TrayController")
                return False
            
            # Синхронизируем статус с текущим режимом приложения
            await self._sync_with_app_mode()
            
            self.is_running = True
            
            # Публикуем событие готовности
            await self.event_bus.publish("tray.integration_ready", {
                "integration": "tray_controller",
                "status": "running"
            })
            
            logger.info("✅ TrayControllerIntegration запущен")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска TrayControllerIntegration: {e}")
            return False
    
    async def stop(self) -> bool:
        """Остановка интеграции"""
        try:
            if not self.is_running:
                logger.warning("TrayControllerIntegration не запущен")
                return True
            
            logger.info("⏹️ Остановка TrayControllerIntegration...")
            
            # Останавливаем TrayController
            if self.tray_controller:
                success = await self.tray_controller.stop()
                if not success:
                    logger.warning("Ошибка остановки TrayController")
            
            self.is_running = False
            
            logger.info("✅ TrayControllerIntegration остановлен")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка остановки TrayControllerIntegration: {e}")
            return False
    
    async def _setup_event_handlers(self):
        """Настройка обработчиков событий"""
        try:
            # Подписываемся на события приложения
            await self.event_bus.subscribe("app.mode_changed", self._on_mode_changed, EventPriority.HIGH)
            await self.event_bus.subscribe("app.startup", self._on_app_startup, EventPriority.HIGH)
            await self.event_bus.subscribe("app.shutdown", self._on_app_shutdown, EventPriority.HIGH)
            
            # Подписываемся на события клавиатуры
            await self.event_bus.subscribe("keyboard.long_press", self._on_keyboard_event, EventPriority.MEDIUM)
            await self.event_bus.subscribe("keyboard.release", self._on_keyboard_event, EventPriority.MEDIUM)
            await self.event_bus.subscribe("keyboard.short_press", self._on_keyboard_event, EventPriority.MEDIUM)
            
            logger.info("✅ Обработчики событий TrayControllerIntegration настроены")
            
        except Exception as e:
            logger.error(f"❌ Ошибка настройки обработчиков событий: {e}")
    
    async def _sync_with_app_mode(self):
        """Синхронизация с текущим режимом приложения"""
        try:
            current_mode = self.state_manager.get_current_mode()
            if current_mode in self.mode_to_status:
                target_status = self.mode_to_status[current_mode]
                await self._update_tray_status(target_status)
                
                logger.info(f"🔄 Синхронизация с режимом приложения: {current_mode.value} → {target_status.value}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка синхронизации с режимом приложения: {e}")
    
    async def _update_tray_status(self, status: TrayStatus):
        """Обновление статуса трея"""
        try:
            if not self.tray_controller or not self.is_running:
                return
            
            success = await self.tray_controller.update_status(status)
            if success:
                logger.info(f"🔄 Статус трея обновлен: {status.value}")
            else:
                logger.warning(f"⚠️ Не удалось обновить статус трея: {status.value}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка обновления статуса трея: {e}")
    
    # Обработчики событий EventBus (НЕ дублируем логику модуля!)
    
    async def _on_mode_changed(self, event):
        """Обработка смены режима приложения"""
        try:
            new_mode = event.data.get("mode")
            if new_mode in self.mode_to_status:
                target_status = self.mode_to_status[new_mode]
                await self._update_tray_status(target_status)
                
                # Публикуем событие обновления статуса
                await self.event_bus.publish("tray.status_updated", {
                    "status": target_status.value,
                    "mode": new_mode.value,
                    "integration": "tray_controller"
                })
                
                logger.info(f"🔄 Режим приложения изменен: {new_mode.value} → {target_status.value}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки смены режима: {e}")
    
    async def _on_keyboard_event(self, event):
        """Обработка событий клавиатуры"""
        try:
            event_type = event.event_type
            logger.info(f"⌨️ Обработка события клавиатуры в TrayControllerIntegration: {event_type}")
            
            # Обновляем режим приложения в зависимости от события клавиатуры
            if event_type == "keyboard.long_press":
                self.state_manager.set_mode(AppMode.LISTENING)
            elif event_type == "keyboard.release":
                self.state_manager.set_mode(AppMode.PROCESSING)
            elif event_type == "keyboard.short_press":
                self.state_manager.set_mode(AppMode.SLEEPING)
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки события клавиатуры: {e}")
    
    async def _on_app_startup(self, event):
        """Обработка запуска приложения"""
        try:
            logger.info("🚀 Обработка запуска приложения в TrayControllerIntegration")
            await self._sync_with_app_mode()
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки запуска приложения: {e}")
    
    async def _on_app_shutdown(self, event):
        """Обработка завершения приложения"""
        try:
            logger.info("⏹️ Обработка завершения приложения в TrayControllerIntegration")
            await self.stop()
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки завершения приложения: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Получить статус интеграции"""
        return {
            "is_initialized": self.is_initialized,
            "is_running": self.is_running,
            "tray_controller": {
                "initialized": self.tray_controller is not None,
                "running": self.tray_controller.is_running if self.tray_controller else False,
                "current_status": self.tray_controller.current_status.value if self.tray_controller else None
            },
            "config": {
                "icon_size": self.config.icon_size,
                "show_status_in_menu": self.config.show_status_in_menu,
                "enable_notifications": self.config.enable_notifications,
                "auto_update_status": self.config.auto_update_status,
                "debug_mode": self.config.debug_mode
            }
        }
    
    def get_app(self):
        """Получить приложение rumps для запуска в главном потоке"""
        if self.tray_controller:
            return self.tray_controller.get_app()
        return None