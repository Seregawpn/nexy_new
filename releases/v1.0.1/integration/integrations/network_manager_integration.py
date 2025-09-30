"""
NetworkManagerIntegration - Интеграция NetworkManager с EventBus
Тонкая обертка для интеграции NetworkManager в общую архитектуру
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

# Импорты модуля NetworkManager
from modules.network_manager.core.types import NetworkEvent, NetworkStatus
from modules.network_manager.core.network_manager import NetworkManager
from modules.network_manager.core.config import NetworkManagerConfig

# Импорт конфигурации
from config.unified_config_loader import UnifiedConfigLoader

logger = logging.getLogger(__name__)

# Убираем дублированную конфигурацию - используем NetworkManagerConfig из модуля

class NetworkManagerIntegration:
    """Интеграция NetworkManager с EventBus и ApplicationStateManager"""
    
    def __init__(
        self,
        event_bus: EventBus,
        state_manager: ApplicationStateManager,
        error_handler: ErrorHandler,
        config: Optional[NetworkManagerConfig] = None,
    ):
        self.event_bus = event_bus
        self.state_manager = state_manager
        self.error_handler = error_handler
        
        # Загружаем конфигурацию из unified_config.yaml
        unified_config = UnifiedConfigLoader()
        if config is None:
            # Создаем конфигурацию модуля из unified_config (с безопасными дефолтами)
            config_data = unified_config._load_config()
            integrations_cfg = (config_data.get('integrations') or {})
            net_cfg = (integrations_cfg.get('network_manager') or {})
            
            config = NetworkManagerConfig(
                check_interval=net_cfg.get('check_interval', (config_data.get('network') or {}).get('keepalive_time', 10)),
                ping_timeout=net_cfg.get('ping_timeout', (config_data.get('network') or {}).get('keepalive_timeout', 3)),
                max_retries=3,  # из модуля
                retry_delay=5.0,  # из модуля
                ping_hosts=net_cfg.get('ping_hosts', ['1.1.1.1', '8.8.8.8']),
                test_urls=['https://www.google.com', 'https://www.apple.com']  # из модуля
            )
        
        self.config = config
        
        # NetworkManager экземпляр
        self._manager: Optional[NetworkManager] = None
        self._initialized = False
        self._running = False
        
        logger.info("NetworkManagerIntegration created")
    
    async def initialize(self) -> bool:
        """Инициализация NetworkManagerIntegration"""
        try:
            logger.info("Initializing NetworkManagerIntegration...")
            
            # Создаем конфигурацию NetworkManager
            network_config = NetworkManagerConfig(
                check_interval=self.config.check_interval,
                ping_timeout=self.config.ping_timeout,
                ping_hosts=self.config.ping_hosts
            )
            
            # Создаем NetworkManager
            self._manager = NetworkManager(network_config)
            
            # Добавляем callback для событий сети
            self._manager.add_callback(self._on_network_event)
            
            # Инициализируем NetworkManager
            success = await self._manager.initialize()
            if not success:
                logger.error("Failed to initialize NetworkManager")
                return False
            
            # Подписываемся на события приложения
            await self.event_bus.subscribe("app.startup", self._on_app_startup, EventPriority.MEDIUM)
            await self.event_bus.subscribe("app.shutdown", self._on_app_shutdown, EventPriority.MEDIUM)
            
            self._initialized = True
            logger.info("NetworkManagerIntegration initialized successfully")
            return True
            
        except Exception as e:
            if hasattr(self.error_handler, 'handle'):
                await self.error_handler.handle(
                    error=e,
                    category="network",
                    severity="error",
                    context={"where": "network.initialize"}
                )
            else:
                logger.error(f"Error in NetworkManagerIntegration.initialize: {e}")
            logger.error(f"Failed to initialize NetworkManagerIntegration: {e}")
            return False
    
    async def start(self) -> bool:
        """Запуск NetworkManagerIntegration"""
        if not self._initialized or not self._manager:
            logger.error("NetworkManagerIntegration not initialized")
            return False
        
        if self._running:
            logger.warning("NetworkManagerIntegration already running")
            return True
        
        try:
            logger.info("Starting NetworkManagerIntegration...")
            
            # Запускаем NetworkManager
            success = await self._manager.start()
            if not success:
                logger.error("Failed to start NetworkManager")
                return False
            
            self._running = True
            logger.info("NetworkManagerIntegration started successfully")
            return True
            
        except Exception as e:
            if hasattr(self.error_handler, 'handle'):
                await self.error_handler.handle(
                    error=e,
                    category="network",
                    severity="error",
                    context={"where": "network.start"}
                )
            else:
                logger.error(f"Error in NetworkManagerIntegration.start: {e}")
            logger.error(f"Failed to start NetworkManagerIntegration: {e}")
            return False
    
    async def stop(self) -> bool:
        """Остановка NetworkManagerIntegration"""
        if not self._manager:
            return True
        
        if not self._running:
            return True
        
        try:
            logger.info("Stopping NetworkManagerIntegration...")
            
            # Останавливаем NetworkManager
            success = await self._manager.stop()
            if not success:
                logger.error("Failed to stop NetworkManager")
            
            self._running = False
            logger.info("NetworkManagerIntegration stopped")
            return success
            
        except Exception as e:
            if hasattr(self.error_handler, 'handle'):
                await self.error_handler.handle(
                    error=e,
                    category="network",
                    severity="error",
                    context={"where": "network.stop"}
                )
            else:
                logger.error(f"Error in NetworkManagerIntegration.stop: {e}")
            logger.error(f"Failed to stop NetworkManagerIntegration: {e}")
            return False
    
    async def _on_app_startup(self, event):
        """Обработка события запуска приложения"""
        try:
            logger.info("App startup - publishing network status snapshot")
            
            if self._manager:
                # Получаем текущий статус сети
                status = self._manager.get_status()
                
                # Публикуем снапшот статуса сети
                await self.event_bus.publish("network.status_snapshot", status)
                
                # Обновляем tooltip в трее
                await self._update_tray_tooltip(status)
            
        except Exception as e:
            if hasattr(self.error_handler, 'handle'):
                await self.error_handler.handle(
                    error=e,
                    category="network",
                    severity="warning",
                    context={"where": "network.app_startup"}
                )
            else:
                logger.error(f"Error in NetworkManagerIntegration.app_startup: {e}")
    
    async def _on_app_shutdown(self, event):
        """Обработка события остановки приложения"""
        try:
            logger.info("App shutdown - stopping NetworkManagerIntegration")
            await self.stop()
        except Exception as e:
            if hasattr(self.error_handler, 'handle'):
                await self.error_handler.handle(
                    error=e,
                    category="network",
                    severity="warning",
                    context={"where": "network.app_shutdown"}
                )
            else:
                logger.error(f"Error in NetworkManagerIntegration.app_shutdown: {e}")
    
    async def _on_network_event(self, event: NetworkEvent):
        """Обработка событий от NetworkManager"""
        try:
            logger.debug(f"Network event received: {event.event_type}")
            
            if event.event_type == "network.status_changed":
                # Публикуем событие изменения статуса
                await self.event_bus.publish("network.status_changed", {
                    "old": event.old_status.value,
                    "new": event.new_status.value,
                    "details": event.details,
                    "timestamp": event.timestamp
                })
                
                # Обновляем tooltip в трее
                if self._manager:
                    status = self._manager.get_status()
                    await self._update_tray_tooltip(status)
                
                # Если сеть отключена, публикуем специальное событие
                if event.new_status == NetworkStatus.DISCONNECTED:
                    await self.event_bus.publish("network.connection_lost", {
                        "details": event.details,
                        "timestamp": event.timestamp
                    })
            
            elif event.event_type == "network.quality_changed":
                # Публикуем событие изменения качества
                await self.event_bus.publish("network.quality_changed", {
                    "quality": event.details.get("quality"),
                    "timestamp": event.timestamp
                })
            
        except Exception as e:
            if hasattr(self.error_handler, 'handle'):
                await self.error_handler.handle(
                    error=e,
                    category="network",
                    severity="warning",
                    context={"where": "network.event_handler"}
                )
            else:
                logger.error(f"Error in NetworkManagerIntegration.event_handler: {e}")
    
    async def _update_tray_tooltip(self, status: Dict[str, Any]):
        """Обновление tooltip в трее с информацией о сети"""
        try:
            # Формируем tooltip с информацией о сети
            tooltip = f"Network: {status['status'].title()}"
            if status['quality'] != 'unknown':
                tooltip += f" ({status['quality'].title()})"
            
            if status['metrics']['ping_time'] > 0:
                tooltip += f" - Ping: {status['metrics']['ping_time']:.0f}ms"
            
            # Публикуем событие обновления tooltip
            await self.event_bus.publish("tray.update_tooltip", {
                "tooltip": tooltip
            })
            
        except Exception as e:
            logger.debug(f"Failed to update tray tooltip: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Получить статус NetworkManagerIntegration"""
        if not self._manager:
            return {
                "initialized": self._initialized,
                "running": self._running,
                "network": {"status": "unknown"}
            }
        
        return {
            "initialized": self._initialized,
            "running": self._running,
            "network": self._manager.get_status()
        }
    
    async def force_check(self) -> bool:
        """Принудительная проверка сети"""
        if not self._manager:
            return False
        
        try:
            return await self._manager.force_check()
        except Exception as e:
            if hasattr(self.error_handler, 'handle'):
                await self.error_handler.handle(
                    error=e,
                    category="network",
                    severity="warning",
                    context={"where": "network.force_check"}
                )
            else:
                logger.error(f"Error in NetworkManagerIntegration.force_check: {e}")
            return False
    
    def is_connected(self) -> bool:
        """Проверить, подключена ли сеть"""
        if not self._manager:
            return False
        
        return self._manager.is_connected()
    
    def get_connection_quality(self) -> str:
        """Получить качество соединения"""
        if not self._manager:
            return "unknown"
        
        return self._manager.get_connection_quality().value
