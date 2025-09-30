"""
AutostartManagerIntegration - Минимальная интеграция для управления автозапуском
Поскольку автозапуск уже настроен через PKG LaunchAgent, эта интеграция только мониторит статус
"""

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Optional, Dict, Any

from integration.core.event_bus import EventBus, EventPriority
from integration.core.state_manager import ApplicationStateManager
from integration.core.error_handler import ErrorHandler

# Импорт конфигурации

logger = logging.getLogger(__name__)

@dataclass
class AutostartManagerIntegrationConfig:
    """Конфигурация AutostartManagerIntegration"""
    check_interval: float = 60.0  # Проверка каждую минуту
    monitor_enabled: bool = True
    auto_repair: bool = False  # Не чиним автоматически - PKG управляет

class AutostartManagerIntegration:
    """
    Минимальная интеграция autostart_manager
    
    ВАЖНО: Автозапуск настроен через PKG LaunchAgent!
    Эта интеграция только мониторит статус, не управляет.
    """
    
    def __init__(self, event_bus: EventBus, state_manager: ApplicationStateManager, 
                 error_handler: ErrorHandler, config: Dict[str, Any] = None):
        self.event_bus = event_bus
        self.state_manager = state_manager
        self.error_handler = error_handler
        
        # Конфигурация
        config = config or {}
        self.config = AutostartManagerIntegrationConfig(
            check_interval=config.get('check_interval', 60.0),
            monitor_enabled=config.get('monitor_enabled', True),
            auto_repair=config.get('auto_repair', False)
        )
        
        # Состояние
        self.is_initialized = False
        self.is_running = False
        self._monitor_task: Optional[asyncio.Task] = None
        
        logger.info("AutostartManagerIntegration created (мониторинг LaunchAgent)")
    
    async def initialize(self) -> bool:
        """Инициализация интеграции"""
        try:
            logger.info("🔧 Инициализация AutostartManagerIntegration")
            
            # Подписываемся на события
            await self.event_bus.subscribe("app.startup", self._on_app_startup, EventPriority.LOW)
            await self.event_bus.subscribe("autostart.check_status", self._on_check_status, EventPriority.MEDIUM)
            
            self.is_initialized = True
            logger.info("✅ AutostartManagerIntegration инициализирован")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации AutostartManagerIntegration: {e}")
            return False
    
    async def start(self) -> bool:
        """Запуск интеграции"""
        try:
            if not self.is_initialized:
                logger.error("❌ AutostartManagerIntegration не инициализирован")
                return False
            
            if self.is_running:
                logger.warning("⚠️ AutostartManagerIntegration уже запущен")
                return True
            
            logger.info("🚀 Запуск AutostartManagerIntegration")
            
            # Проверяем текущий статус автозапуска
            await self._check_autostart_status()
            
            # Запускаем мониторинг если включен
            if self.config.monitor_enabled:
                self._monitor_task = asyncio.create_task(self._monitor_autostart())
            
            self.is_running = True
            logger.info("✅ AutostartManagerIntegration запущен")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска AutostartManagerIntegration: {e}")
            return False
    
    async def stop(self) -> bool:
        """Остановка интеграции"""
        try:
            if not self.is_running:
                return True
            
            logger.info("⏹️ Остановка AutostartManagerIntegration")
            
            # Останавливаем мониторинг
            if self._monitor_task and not self._monitor_task.done():
                self._monitor_task.cancel()
                try:
                    await self._monitor_task
                except asyncio.CancelledError:
                    pass
            
            self.is_running = False
            logger.info("✅ AutostartManagerIntegration остановлен")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка остановки AutostartManagerIntegration: {e}")
            return False
    
    async def _on_app_startup(self, event):
        """Обработка события запуска приложения"""
        try:
            logger.info("📱 App startup - проверяем статус автозапуска")
            await self._check_autostart_status()
        except Exception as e:
            logger.error(f"❌ Ошибка обработки app.startup: {e}")
    
    async def _on_check_status(self, event):
        """Обработка запроса проверки статуса"""
        try:
            await self._check_autostart_status()
        except Exception as e:
            logger.error(f"❌ Ошибка проверки статуса: {e}")
    
    async def _check_autostart_status(self):
        """Проверка статуса автозапуска"""
        try:
            # Проверяем LaunchAgent
            launch_agent_path = os.path.expanduser("~/Library/LaunchAgents/com.nexy.assistant.plist")
            launch_agent_exists = os.path.exists(launch_agent_path)
            
            # Публикуем статус
            status_data = {
                "launch_agent_exists": launch_agent_exists,
                "launch_agent_path": launch_agent_path,
                "method": "launch_agent",
                "managed_by": "PKG installer"
            }
            
            await self.event_bus.publish("autostart.status_checked", status_data)
            
            if launch_agent_exists:
                logger.info("✅ LaunchAgent автозапуск настроен корректно")
            else:
                logger.warning("⚠️ LaunchAgent автозапуск не найден")
            
        except Exception as e:
            logger.error(f"❌ Ошибка проверки автозапуска: {e}")
    
    async def _monitor_autostart(self):
        """Мониторинг автозапуска"""
        try:
            while self.is_running:
                await self._check_autostart_status()
                await asyncio.sleep(self.config.check_interval)
                
        except asyncio.CancelledError:
            logger.info("🔄 Мониторинг автозапуска остановлен")
        except Exception as e:
            logger.error(f"❌ Ошибка мониторинга автозапуска: {e}")
