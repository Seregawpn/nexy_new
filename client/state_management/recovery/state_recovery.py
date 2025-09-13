"""
Система восстановления состояний
"""

import asyncio
import logging
from typing import Dict, Callable, Optional
from ..core.types import AppState, StateRecoveryCallback

logger = logging.getLogger(__name__)


class StateRecovery:
    """Система восстановления состояний"""
    
    def __init__(self, state_manager=None):
        self.state_manager = state_manager
        self.recovery_strategies: Dict[AppState, Callable] = {
            AppState.ERROR: self._recover_from_error,
            AppState.PROCESSING: self._recover_from_processing,
            AppState.LISTENING: self._recover_from_listening
        }
        self.max_attempts = 3
        self.retry_delay = 1.0
    
    async def attempt_recovery(self, current_state: AppState, error: Exception) -> bool:
        """
        Пытается восстановить состояние
        
        Args:
            current_state: Текущее состояние
            error: Ошибка, которая произошла
            
        Returns:
            bool: True если восстановление успешно
        """
        try:
            if current_state in self.recovery_strategies:
                strategy = self.recovery_strategies[current_state]
                return await strategy(error)
            return False
        except Exception as e:
            logger.error(f"Ошибка восстановления: {e}")
            return False
    
    async def _recover_from_error(self, error: Exception) -> bool:
        """
        Восстанавливается из состояния ошибки
        
        Args:
            error: Ошибка
            
        Returns:
            bool: True если восстановление успешно
        """
        try:
            logger.info("Попытка восстановления из состояния ошибки")
            
            # Переходим в состояние сна
            if self.state_manager:
                await self.state_manager._transition_to_state(AppState.SLEEPING, "error_recovery")
            
            logger.info("Восстановление из ошибки успешно")
            return True
        except Exception as e:
            logger.error(f"Ошибка восстановления из ошибки: {e}")
            return False
    
    async def _recover_from_processing(self, error: Exception) -> bool:
        """
        Восстанавливается из состояния обработки
        
        Args:
            error: Ошибка
            
        Returns:
            bool: True если восстановление успешно
        """
        try:
            logger.info("Попытка восстановления из состояния обработки")
            
            # Останавливаем обработку и переходим в сон
            if self.state_manager:
                await self.state_manager._transition_to_state(AppState.SLEEPING, "processing_recovery")
            
            logger.info("Восстановление из обработки успешно")
            return True
        except Exception as e:
            logger.error(f"Ошибка восстановления из обработки: {e}")
            return False
    
    async def _recover_from_listening(self, error: Exception) -> bool:
        """
        Восстанавливается из состояния прослушивания
        
        Args:
            error: Ошибка
            
        Returns:
            bool: True если восстановление успешно
        """
        try:
            logger.info("Попытка восстановления из состояния прослушивания")
            
            # Останавливаем прослушивание и переходим в сон
            if self.state_manager:
                await self.state_manager._transition_to_state(AppState.SLEEPING, "listening_recovery")
            
            logger.info("Восстановление из прослушивания успешно")
            return True
        except Exception as e:
            logger.error(f"Ошибка восстановления из прослушивания: {e}")
            return False
    
    async def recover_with_retry(self, current_state: AppState, error: Exception) -> bool:
        """
        Восстанавливается с повторными попытками
        
        Args:
            current_state: Текущее состояние
            error: Ошибка
            
        Returns:
            bool: True если восстановление успешно
        """
        for attempt in range(self.max_attempts):
            try:
                logger.info(f"Попытка восстановления {attempt + 1}/{self.max_attempts}")
                
                success = await self.attempt_recovery(current_state, error)
                if success:
                    logger.info("Восстановление успешно")
                    return True
                
                if attempt < self.max_attempts - 1:
                    logger.info(f"Ожидание {self.retry_delay} секунд перед следующей попыткой")
                    await asyncio.sleep(self.retry_delay)
                
            except Exception as e:
                logger.error(f"Ошибка в попытке восстановления {attempt + 1}: {e}")
                if attempt < self.max_attempts - 1:
                    await asyncio.sleep(self.retry_delay)
        
        logger.error("Все попытки восстановления исчерпаны")
        return False
    
    def set_state_manager(self, state_manager):
        """
        Устанавливает ссылку на state manager
        
        Args:
            state_manager: Экземпляр state manager
        """
        self.state_manager = state_manager
    
    def add_recovery_strategy(self, state: AppState, strategy: Callable):
        """
        Добавляет стратегию восстановления для состояния
        
        Args:
            state: Состояние
            strategy: Функция восстановления
        """
        self.recovery_strategies[state] = strategy
        logger.info(f"Добавлена стратегия восстановления для {state.value}")
    
    def remove_recovery_strategy(self, state: AppState):
        """
        Удаляет стратегию восстановления для состояния
        
        Args:
            state: Состояние
        """
        if state in self.recovery_strategies:
            del self.recovery_strategies[state]
            logger.info(f"Удалена стратегия восстановления для {state.value}")
    
    def get_recovery_strategies(self) -> Dict[AppState, Callable]:
        """
        Возвращает доступные стратегии восстановления
        
        Returns:
            Dict[AppState, Callable]: Словарь стратегий
        """
        return self.recovery_strategies.copy()
