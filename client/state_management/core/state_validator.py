"""
Валидатор состояний и переходов
"""

import logging
from typing import Optional, Dict, Set
from .types import AppState, StateTransition

logger = logging.getLogger(__name__)


class StateValidator:
    """Валидатор состояний и переходов"""
    
    def __init__(self):
        # Разрешенные переходы
        self.allowed_transitions: Dict[AppState, Set[AppState]] = {
            AppState.SLEEPING: {AppState.LISTENING, AppState.ERROR, AppState.SHUTDOWN},
            AppState.LISTENING: {AppState.PROCESSING, AppState.SLEEPING, AppState.ERROR, AppState.SHUTDOWN},
            AppState.PROCESSING: {AppState.SLEEPING, AppState.ERROR, AppState.SHUTDOWN},
            AppState.ERROR: {AppState.SLEEPING, AppState.SHUTDOWN},
            AppState.SHUTDOWN: set()  # Финальное состояние
        }
    
    def can_transition(self, from_state: AppState, to_state: AppState) -> bool:
        """
        Проверяет, возможен ли переход между состояниями
        
        Args:
            from_state: Исходное состояние
            to_state: Целевое состояние
            
        Returns:
            bool: True если переход возможен
        """
        try:
            if from_state == to_state:
                return True  # Остаемся в том же состоянии
            
            allowed = self.allowed_transitions.get(from_state, set())
            return to_state in allowed
        except Exception as e:
            logger.error(f"Ошибка проверки перехода: {e}")
            return False
    
    def validate_state(self, state: AppState) -> bool:
        """
        Валидирует корректность состояния
        
        Args:
            state: Состояние для проверки
            
        Returns:
            bool: True если состояние корректно
        """
        try:
            return isinstance(state, AppState) and state in AppState
        except Exception as e:
            logger.error(f"Ошибка валидации состояния: {e}")
            return False
    
    def get_transition_type(self, from_state: AppState, to_state: AppState) -> Optional[StateTransition]:
        """
        Определяет тип перехода
        
        Args:
            from_state: Исходное состояние
            to_state: Целевое состояние
            
        Returns:
            StateTransition: Тип перехода или None
        """
        try:
            if from_state == to_state:
                return None
            
            transition_map = {
                (AppState.SLEEPING, AppState.LISTENING): StateTransition.SLEEP_TO_LISTEN,
                (AppState.LISTENING, AppState.PROCESSING): StateTransition.LISTEN_TO_PROCESS,
                (AppState.PROCESSING, AppState.SLEEPING): StateTransition.PROCESS_TO_SLEEP,
                (AppState.ERROR, AppState.SLEEPING): StateTransition.ERROR_TO_SLEEP,
            }
            
            # Проверяем специальные переходы
            if to_state == AppState.ERROR:
                return StateTransition.ANY_TO_ERROR
            if to_state == AppState.SHUTDOWN:
                return StateTransition.ANY_TO_SHUTDOWN
            
            return transition_map.get((from_state, to_state))
        except Exception as e:
            logger.error(f"Ошибка определения типа перехода: {e}")
            return None
    
    def get_allowed_transitions(self, from_state: AppState) -> Set[AppState]:
        """
        Возвращает список разрешенных переходов из состояния
        
        Args:
            from_state: Исходное состояние
            
        Returns:
            Set[AppState]: Множество разрешенных состояний
        """
        return self.allowed_transitions.get(from_state, set())
    
    def is_final_state(self, state: AppState) -> bool:
        """
        Проверяет, является ли состояние финальным
        
        Args:
            state: Состояние для проверки
            
        Returns:
            bool: True если состояние финальное
        """
        return state == AppState.SHUTDOWN
