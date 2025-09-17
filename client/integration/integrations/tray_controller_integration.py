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

# Импорт конфигурации
from config.unified_config_loader import UnifiedConfigLoader

# Импорты интеграции
from integration.core.event_bus import EventBus, EventPriority
from integration.core.state_manager import ApplicationStateManager, AppMode
from integration.core.error_handler import ErrorHandler, ErrorSeverity, ErrorCategory

logger = logging.getLogger(__name__)

# Убираем дублированную конфигурацию - используем TrayConfig из модуля

class TrayControllerIntegration:
    """Интеграция TrayController с EventBus и ApplicationStateManager"""
    
    def __init__(self, event_bus: EventBus, state_manager: ApplicationStateManager, 
                 error_handler: ErrorHandler, config: Optional[TrayConfig] = None):
        self.event_bus = event_bus
        self.state_manager = state_manager
        self.error_handler = error_handler
        # Загружаем конфигурацию из unified_config.yaml
        unified_config = UnifiedConfigLoader()
        if config is None:
            # Создаем конфигурацию модуля из unified_config
            config_data = unified_config._load_config()
            tray_cfg = config_data['integrations']['tray_controller']
            
            config = TrayConfig(
                icon_size=tray_cfg['icon_size'],
                show_status=tray_cfg['show_status_in_menu'],  # Правильное поле
                show_menu=True,  # Из модуля
                enable_click_events=True,  # Из модуля
                enable_right_click=True,  # Из модуля
                auto_hide=False,  # Из модуля
                animation_speed=0.5,  # Из модуля
                menu_font_size=13,  # Из модуля
                enable_sound=tray_cfg['enable_notifications'],  # Маппинг
                debug_mode=tray_cfg['debug_mode']
            )
        
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

            # Подписываемся на события микрофона/распознавания для точной индикации
            await self.event_bus.subscribe("voice.mic_opened", self._on_voice_mic_opened, EventPriority.HIGH)
            await self.event_bus.subscribe("voice.mic_closed", self._on_voice_mic_closed, EventPriority.HIGH)
            # Подписываемся на переключение аудиоустройств
            await self.event_bus.subscribe("audio.device_switched", self._on_audio_device_switched, EventPriority.MEDIUM)
            # Подписываемся на снапшот устройства для первичного заполнения
            await self.event_bus.subscribe("audio.device_snapshot", self._on_audio_device_snapshot, EventPriority.MEDIUM)
            
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
                # Обновляем текст статуса в меню для наглядности
                human = {
                    TrayStatus.SLEEPING: "Sleeping",
                    TrayStatus.LISTENING: "Listening",
                    TrayStatus.PROCESSING: "Processing",
                }.get(status, status.value.title())
                await self.tray_controller.update_menu_status_text(human)
            else:
                logger.warning(f"⚠️ Не удалось обновить статус трея: {status.value}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка обновления статуса трея: {e}")
    
    # Обработчики событий EventBus (НЕ дублируем логику модуля!)
    
    async def _on_mode_changed(self, event):
        """Обработка смены режима приложения"""
        try:
            data = (event.get("data") or {})
            new_mode = data.get("mode")
            logger.info(f"TrayIntegration: app.mode_changed received mode={getattr(new_mode,'value',new_mode)}")
            logger.debug(f"TrayIntegration: app.mode_changed received data={data}, parsed new_mode={new_mode}")
            if new_mode in self.mode_to_status:
                target_status = self.mode_to_status[new_mode]
                logger.debug(f"TrayIntegration: mapping mode -> status: {new_mode} -> {target_status}")
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
            # Безопасное получение типа события
            if isinstance(event, dict):
                event_type = event.get("type", "unknown")
            else:
                event_type = getattr(event, 'event_type', 'unknown')
            
            logger.info(f"⌨️ Обработка события клавиатуры в TrayControllerIntegration: {event_type}")
            
            # Push-to-talk: режимы меняются в InputProcessingIntegration
            # Здесь только логируем/можно обновлять UI, если нужно
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки события клавиатуры: {e}")
            import traceback
            logger.debug(f"Стектрейс: {traceback.format_exc()}")

    async def _on_voice_mic_opened(self, event):
        """Иконка LISTENING при открытии микрофона"""
        try:
            await self._update_tray_status(TrayStatus.LISTENING)
            await self.event_bus.publish("tray.status_updated", {
                "status": TrayStatus.LISTENING.value,
                "reason": "voice.mic_opened",
                "integration": "tray_controller"
            })
        except Exception as e:
            logger.error(f"❌ Ошибка обработки voice.mic_opened: {e}")

    async def _on_voice_mic_closed(self, event):
        """Иконка PROCESSING/SLEEPING в зависимости от режима после закрытия микрофона"""
        try:
            mode = self.state_manager.get_current_mode()
            target = self.mode_to_status.get(mode, TrayStatus.SLEEPING)
            await self._update_tray_status(target)
            await self.event_bus.publish("tray.status_updated", {
                "status": target.value,
                "mode": getattr(mode, 'value', str(mode)),
                "reason": "voice.mic_closed",
                "integration": "tray_controller"
            })
        except Exception as e:
            logger.error(f"❌ Ошибка обработки voice.mic_closed: {e}")

    async def _on_audio_device_switched(self, event):
        """Отображение устройства, на которое произошло переключение."""
        try:
            data = (event or {}).get("data", {})
            to_device = data.get("to_device") or data.get("device") or "Unknown"
            device_type = data.get("device_type", "output")
            # Обновляем пункт меню "Output: ..."
            if self.tray_controller:
                await self.tray_controller.update_menu_output_device(to_device)
                # Ненавязчивая нотификация (без звука)
                await self.tray_controller.show_notification(
                    title="Audio device switched",
                    message=f"Now using: {to_device}",
                    subtitle=device_type
                )
        except Exception as e:
            logger.error(f"❌ Ошибка обработки audio.device_switched: {e}")

    async def _on_audio_device_snapshot(self, event):
        """Первичное отображение текущего устройства в меню на старте."""
        try:
            data = (event or {}).get("data", {})
            cur = data.get("current_device") or "Unknown"
            if self.tray_controller:
                await self.tray_controller.update_menu_output_device(cur)
        except Exception as e:
            logger.debug(f"Failed to handle audio.device_snapshot in tray: {e}")
    
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
