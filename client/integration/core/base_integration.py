"""
Базовый класс для всех интеграций
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

from .event_bus import EventBus
from .state_manager import ApplicationStateManager
from .error_handler import ErrorHandler

logger = logging.getLogger(__name__)


class BaseIntegration(ABC):
    """Базовый класс для всех интеграций"""
    
    def __init__(
        self,
        event_bus: EventBus,
        state_manager: ApplicationStateManager,
        error_handler: ErrorHandler,
        name: str
    ):
        self.event_bus = event_bus
        self.state_manager = state_manager
        self.error_handler = error_handler
        self.name = name
        
        # Состояние интеграции
        self._initialized = False
        self._running = False
        
        logger.info(f"{self.name} integration created")
    
    # --------------------- Lifecycle ---------------------
    
    async def initialize(self) -> bool:
        """Инициализация интеграции"""
        try:
            if self._initialized:
                logger.warning(f"{self.name} already initialized")
                return True
                
            logger.info(f"Initializing {self.name}...")
            
            # Вызываем специфичную инициализацию
            success = await self._do_initialize()
            
            if success:
                self._initialized = True
                logger.info(f"{self.name} initialized successfully")
            else:
                logger.error(f"Failed to initialize {self.name}")
                
            return success
            
        except Exception as e:
            await self._handle_error(e, where="initialize")
            return False
    
    async def start(self) -> bool:
        """Запуск интеграции"""
        try:
            if not self._initialized:
                logger.error(f"{self.name} not initialized")
                return False
                
            if self._running:
                logger.warning(f"{self.name} already running")
                return True
                
            logger.info(f"Starting {self.name}...")
            
            # Вызываем специфичный запуск
            success = await self._do_start()
            
            if success:
                self._running = True
                logger.info(f"{self.name} started successfully")
            else:
                logger.error(f"Failed to start {self.name}")
                
            return success
            
        except Exception as e:
            await self._handle_error(e, where="start")
            return False
    
    async def stop(self) -> bool:
        """Остановка интеграции"""
        try:
            if not self._running:
                logger.warning(f"{self.name} not running")
                return True
                
            logger.info(f"Stopping {self.name}...")
            
            # Вызываем специфичную остановку
            success = await self._do_stop()
            
            if success:
                self._running = False
                logger.info(f"{self.name} stopped successfully")
            else:
                logger.error(f"Failed to stop {self.name}")
                
            return success
            
        except Exception as e:
            await self._handle_error(e, where="stop")
            return False
    
    # --------------------- Abstract Methods ---------------------
    
    @abstractmethod
    async def _do_initialize(self) -> bool:
        """Специфичная инициализация интеграции"""
        pass
    
    @abstractmethod
    async def _do_start(self) -> bool:
        """Специфичный запуск интеграции"""
        pass
    
    @abstractmethod
    async def _do_stop(self) -> bool:
        """Специфичная остановка интеграции"""
        pass
    
    # --------------------- Common Methods ---------------------
    
    async def _handle_error(self, e: Exception, *, where: str, severity: str = "error"):
        """Унифицированная обработка ошибок"""
        try:
            if hasattr(self.error_handler, 'handle'):
                await self.error_handler.handle(
                    error=e,
                    category=self.name.lower(),
                    severity=severity,
                    context={"where": where}
                )
            elif hasattr(self.error_handler, 'handle_error'):
                await self.error_handler.handle_error(
                    severity=severity,
                    category=self.name.lower(),
                    message=f"Error in {self.name} ({where}): {e}",
                    context={"where": where}
                )
            else:
                logger.error(f"Error in {self.name} ({where}): {e}")
        except Exception as handler_error:
            logger.error(f"Error handler failed for {self.name}: {handler_error}")
            logger.error(f"Original error in {self.name} ({where}): {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Получить статус интеграции"""
        return {
            "name": self.name,
            "initialized": self._initialized,
            "running": self._running
        }
    
    @property
    def is_initialized(self) -> bool:
        """Проверить, инициализирована ли интеграция"""
        return self._initialized
    
    @property
    def is_running(self) -> bool:
        """Проверить, запущена ли интеграция"""
        return self._running
