"""
AudioDeviceIntegration - Интеграция AudioDeviceManager с EventBus
Тонкая обертка для интеграции AudioDeviceManager в общую архитектуру
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from integration.core.event_bus import EventBus, EventPriority
from integration.core.state_manager import ApplicationStateManager, AppMode
from integration.core.error_handler import ErrorHandler

# Импорты модуля AudioDeviceManager
from modules.audio_device_manager.core.device_manager import AudioDeviceManager
from modules.audio_device_manager.core.types import (
    AudioDevice, DeviceType, DeviceStatus, AudioDeviceManagerConfig
)

# Импорт конфигурации
from config.unified_config_loader import UnifiedConfigLoader

logger = logging.getLogger(__name__)

# Убираем дублированную конфигурацию - используем AudioDeviceManagerConfig из модуля
# и дополнительные настройки из unified_config.yaml

class AudioDeviceIntegration:
    """Интеграция AudioDeviceManager с EventBus и ApplicationStateManager"""
    
    def __init__(
        self,
        event_bus: EventBus,
        state_manager: ApplicationStateManager,
        error_handler: ErrorHandler,
        config: Optional[AudioDeviceManagerConfig] = None,
    ):
        self.event_bus = event_bus
        self.state_manager = state_manager
        self.error_handler = error_handler
        # Загружаем конфигурацию из unified_config.yaml
        unified_config = UnifiedConfigLoader()
        if config is None:
            # Создаем конфигурацию модуля из unified_config
            config_data = unified_config._load_config()
            audio_cfg = config_data['audio']['device_manager']
            integration_cfg = config_data['integrations']['audio_device']
            
            config = AudioDeviceManagerConfig(
                auto_switch_enabled=integration_cfg['auto_switch_enabled'],
                monitoring_interval=integration_cfg['monitoring_interval'],
                switch_delay=integration_cfg['switch_delay'],
                device_priorities=audio_cfg['device_priorities'],
                user_preferences=None,  # Будет заполнено в __post_init__
                macos_settings=None     # Будет заполнено в __post_init__
            )
        
        self.config = config
        
        # Дополнительные настройки интеграции из unified_config
        config_data = unified_config._load_config()
        integration_cfg = config_data['integrations']['audio_device']
        self.enable_microphone_on_listening = integration_cfg['enable_microphone_on_listening']
        self.disable_microphone_on_sleeping = integration_cfg['disable_microphone_on_sleeping']
        self.disable_microphone_on_processing = integration_cfg['disable_microphone_on_processing']
        
        # AudioDeviceManager экземпляр
        self._manager: Optional[AudioDeviceManager] = None
        self._initialized = False
        self._running = False
        self._current_mode: Optional[AppMode] = None
        
        logger.info("AudioDeviceIntegration created")
    
    async def initialize(self) -> bool:
        """Инициализация AudioDeviceIntegration"""
        try:
            logger.info("Initializing AudioDeviceIntegration...")
            
            # Создаем конфигурацию AudioDeviceManager
            audio_config = AudioDeviceManagerConfig(
                auto_switch_enabled=self.config.auto_switch_enabled,
                monitoring_interval=self.config.monitoring_interval,
                switch_delay=self.config.switch_delay
            )
            
            # Создаем AudioDeviceManager
            self._manager = AudioDeviceManager(audio_config)
            
            # Настраиваем callbacks
            self._manager.set_device_changed_callback(self._sync_device_changed_wrapper)
            self._manager.set_device_switched_callback(self._on_device_switched)
            self._manager.set_error_callback(self._on_audio_error)
            
            # Инициализируем AudioDeviceManager
            success = await self._manager.start()
            if not success:
                logger.error("Failed to initialize AudioDeviceManager")
                return False
            
            # Подписываемся на события приложения
            await self.event_bus.subscribe("app.startup", self._on_app_startup, EventPriority.MEDIUM)
            await self.event_bus.subscribe("app.shutdown", self._on_app_shutdown, EventPriority.MEDIUM)
            await self.event_bus.subscribe("app.state_changed", self._on_app_state_changed, EventPriority.HIGH)
            
            self._initialized = True
            logger.info("AudioDeviceIntegration initialized successfully")
            return True
            
        except Exception as e:
            if hasattr(self.error_handler, 'handle_error'):
                await self.error_handler.handle_error(
                    severity="error",
                    category="audio",
                    message=f"Ошибка инициализации AudioDeviceIntegration: {e}",
                    context={"where": "audio.initialize"}
                )
            else:
                logger.error(f"Error in AudioDeviceIntegration.initialize: {e}")
            logger.error(f"Failed to initialize AudioDeviceIntegration: {e}")
            return False
    
    async def start(self) -> bool:
        """Запуск AudioDeviceIntegration"""
        if not self._initialized or not self._manager:
            logger.error("AudioDeviceIntegration not initialized")
            return False
        
        if self._running:
            logger.warning("AudioDeviceIntegration already running")
            return True
        
        try:
            logger.info("Starting AudioDeviceIntegration...")
            
            # Запускаем AudioDeviceManager
            success = await self._manager.start()
            if not success:
                logger.error("Failed to start AudioDeviceManager")
                return False
            
            self._running = True
            
            # Получаем текущий режим и настраиваем микрофон
            current_mode = self.state_manager.get_current_mode()
            await self._handle_mode_change(None, current_mode)
            
            logger.info("AudioDeviceIntegration started successfully")
            return True
            
        except Exception as e:
            if hasattr(self.error_handler, 'handle_error'):
                await self.error_handler.handle_error(
                    severity="error",
                    category="audio",
                    message=f"Ошибка запуска AudioDeviceIntegration: {e}",
                    context={"where": "audio.start"}
                )
            else:
                logger.error(f"Error in AudioDeviceIntegration.start: {e}")
            logger.error(f"Failed to start AudioDeviceIntegration: {e}")
            return False
    
    async def stop(self) -> bool:
        """Остановка AudioDeviceIntegration"""
        if not self._manager:
            return True
        
        if not self._running:
            return True
        
        try:
            logger.info("Stopping AudioDeviceIntegration...")
            
            # Выключаем микрофон перед остановкой
            await self._disable_microphone()
            
            # Останавливаем AudioDeviceManager
            success = await self._manager.stop()
            if not success:
                logger.error("Failed to stop AudioDeviceManager")
            
            self._running = False
            logger.info("AudioDeviceIntegration stopped")
            return success
            
        except Exception as e:
            if hasattr(self.error_handler, 'handle_error'):
                await self.error_handler.handle_error(
                    severity="error",
                    category="audio",
                    message=f"Ошибка остановки AudioDeviceIntegration: {e}",
                    context={"where": "audio.stop"}
                )
            else:
                logger.error(f"Error in AudioDeviceIntegration.stop: {e}")
            logger.error(f"Failed to stop AudioDeviceIntegration: {e}")
            return False
    
    async def _on_app_startup(self, event):
        """Обработка события запуска приложения"""
        try:
            logger.info("App startup - initializing audio devices")
            
            if self._manager:
                # Получаем текущее аудио устройство
                current_device = await self._manager.get_current_device()
                
                # Публикуем снапшот аудио состояния
                await self.event_bus.publish("audio.device_snapshot", {
                    "current_device": current_device.name if current_device else "None",
                    "device_type": current_device.type.value if current_device else "unknown",
                    "is_available": current_device.is_available if current_device else False
                })
            
        except Exception as e:
            if hasattr(self.error_handler, 'handle_error'):
                await self.error_handler.handle_error(
                    severity="warning",
                    category="audio",
                    message=f"Ошибка обработки app startup: {e}",
                    context={"where": "audio.app_startup"}
                )
            else:
                logger.error(f"Error in AudioDeviceIntegration.app_startup: {e}")
    
    async def _on_app_shutdown(self, event):
        """Обработка события остановки приложения"""
        try:
            logger.info("App shutdown - stopping AudioDeviceIntegration")
            await self.stop()
        except Exception as e:
            if hasattr(self.error_handler, 'handle_error'):
                await self.error_handler.handle_error(
                    severity="warning",
                    category="audio",
                    message=f"Ошибка обработки app shutdown: {e}",
                    context={"where": "audio.app_shutdown"}
                )
            else:
                logger.error(f"Error in AudioDeviceIntegration.app_shutdown: {e}")
    
    async def _on_app_state_changed(self, event):
        """Обработка изменения режима приложения"""
        try:
            old_mode = event.get("old_mode")
            new_mode = event.get("new_mode")
            
            if old_mode and new_mode:
                await self._handle_mode_change(old_mode, new_mode)
            
        except Exception as e:
            if hasattr(self.error_handler, 'handle_error'):
                await self.error_handler.handle_error(
                    severity="warning",
                    category="audio",
                    message=f"Ошибка обработки смены режима: {e}",
                    context={"where": "audio.state_changed"}
                )
            else:
                logger.error(f"Error in AudioDeviceIntegration.state_changed: {e}")
    
    async def _handle_mode_change(self, old_mode: Optional[AppMode], new_mode: AppMode):
        """Обработка смены режима приложения"""
        try:
            logger.info(f"Audio mode change: {old_mode} -> {new_mode}")
            
            self._current_mode = new_mode
            
            if new_mode == AppMode.LISTENING:
                # В режиме прослушивания - включаем микрофон
                await self._enable_microphone()
            elif new_mode in [AppMode.SLEEPING, AppMode.PROCESSING]:
                # В режиме сна или обработки - выключаем микрофон
                await self._disable_microphone()
            
        except Exception as e:
            if hasattr(self.error_handler, 'handle_error'):
                await self.error_handler.handle_error(
                    severity="warning",
                    category="audio",
                    message=f"Ошибка обработки смены режима: {e}",
                    context={"where": "audio.mode_change"}
                )
            else:
                logger.error(f"Error in AudioDeviceIntegration.mode_change: {e}")
    
    async def _enable_microphone(self):
        """Включение микрофона"""
        try:
            if not self._manager:
                return
            
            logger.info("Enabling microphone...")
            
            # Получаем лучшее устройство ввода
            input_device = await self._manager.get_best_device(DeviceType.INPUT)
            
            if input_device:
                # Переключаемся на устройство ввода
                await self._manager.switch_to_device(input_device)
                
                # Публикуем событие включения микрофона
                await self.event_bus.publish("audio.microphone_enabled", {
                    "device": input_device.name,
                    "device_type": input_device.type.value,
                    "is_available": input_device.is_available
                })
                
                logger.info(f"Microphone enabled: {input_device.name}")
            else:
                logger.warning("No input device available for microphone")
                
                # Публикуем событие ошибки
                await self.event_bus.publish("audio.microphone_error", {
                    "error": "No input device available",
                    "context": "enable_microphone"
                })
            
        except Exception as e:
            logger.error(f"Error enabling microphone: {e}")
            await self.event_bus.publish("audio.microphone_error", {
                "error": str(e),
                "context": "enable_microphone"
            })
    
    async def _disable_microphone(self):
        """Выключение микрофона"""
        try:
            if not self._manager:
                return
            
            logger.info("Disabling microphone...")
            
            # Публикуем событие выключения микрофона
            await self.event_bus.publish("audio.microphone_disabled", {
                "reason": "mode_change",
                "mode": self._current_mode.value if self._current_mode else "unknown"
            })
            
            logger.info("Microphone disabled")
            
        except Exception as e:
            logger.error(f"Error disabling microphone: {e}")
            await self.event_bus.publish("audio.microphone_error", {
                "error": str(e),
                "context": "disable_microphone"
            })
    
    async def _on_device_changed(self, change):
        """Обработка изменения аудио устройств"""
        try:
            logger.debug(f"Audio devices changed: +{len(change.added)} -{len(change.removed)}")
            
            # Публикуем событие изменения устройств
            await self.event_bus.publish("audio.device_changed", {
                "added": [device.name for device in change.added],
                "removed": [device.name for device in change.removed],
                "total_devices": len(change.added) + len(change.removed)
            })
            
            # Если микрофон включен и устройство ввода изменилось, переключаемся
            if self._current_mode == AppMode.LISTENING:
                await self._enable_microphone()
            
        except Exception as e:
            if hasattr(self.error_handler, 'handle_error'):
                await self.error_handler.handle_error(
                    severity="warning",
                    category="audio",
                    message=f"Ошибка обработки изменения устройств: {e}",
                    context={"where": "audio.device_changed"}
                )
            else:
                logger.error(f"Error in AudioDeviceIntegration.device_changed: {e}")
    
    async def _on_device_switched(self, from_device: AudioDevice, to_device: AudioDevice):
        """Обработка переключения аудио устройства"""
        try:
            logger.info(f"Audio device switched: {from_device.name} -> {to_device.name}")
            
            # Публикуем событие переключения устройства
            await self.event_bus.publish("audio.device_switched", {
                "from_device": from_device.name,
                "to_device": to_device.name,
                "device_type": to_device.type.value,
                "is_available": to_device.is_available
            })
            
        except Exception as e:
            if hasattr(self.error_handler, 'handle_error'):
                await self.error_handler.handle_error(
                    severity="warning",
                    category="audio",
                    message=f"Ошибка обработки переключения устройства: {e}",
                    context={"where": "audio.device_switched"}
                )
            else:
                logger.error(f"Error in AudioDeviceIntegration.device_switched: {e}")
    
    async def _on_audio_error(self, error, context):
        """Обработка ошибок аудио"""
        try:
            logger.error(f"Audio error in {context}: {error}")
            
            # Публикуем событие ошибки аудио
            await self.event_bus.publish("audio.error", {
                "error": str(error),
                "context": context,
                "severity": "error"
            })
            
        except Exception as e:
            logger.error(f"Error handling audio error: {e}")
    
    def _sync_device_changed_wrapper(self, change):
        """Sync wrapper для async _on_device_changed"""
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(self._on_device_changed(change), loop)
            else:
                asyncio.run(self._on_device_changed(change))
        except Exception as e:
            logger.error(f"❌ Ошибка в sync wrapper device_changed: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Получить статус AudioDeviceIntegration"""
        if not self._manager:
            return {
                "initialized": self._initialized,
                "running": self._running,
                "audio": {"status": "unknown"}
            }
        
        return {
            "initialized": self._initialized,
            "running": self._running,
            "current_mode": self._current_mode.value if self._current_mode else "unknown",
            "audio": {
                "manager_running": self._manager.is_running if hasattr(self._manager, 'is_running') else False,
                "current_device": self._manager.current_device.name if self._manager.current_device else "None"
            }
        }
    
    async def get_current_device(self) -> Optional[AudioDevice]:
        """Получить текущее аудио устройство"""
        if not self._manager:
            return None
        
        try:
            return await self._manager.get_current_device()
        except Exception as e:
            logger.error(f"Error getting current device: {e}")
            return None
    
    async def switch_to_device(self, device: AudioDevice) -> bool:
        """Переключиться на указанное устройство"""
        if not self._manager:
            return False
        
        try:
            return await self._manager.switch_to_device(device)
        except Exception as e:
            logger.error(f"Error switching to device {device.name}: {e}")
            return False
