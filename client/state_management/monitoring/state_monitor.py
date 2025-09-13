"""
Монитор состояний и метрик
"""

import threading
import logging
from typing import List, Optional
from datetime import datetime
from ..core.types import AppState, StateMetrics, StateInfo

logger = logging.getLogger(__name__)


class StateMonitor:
    """Монитор состояний и метрик"""
    
    def __init__(self, max_history_size: int = 100):
        self.metrics = StateMetrics()
        self.state_history: List[StateInfo] = []
        self.max_history_size = max_history_size
        self._lock = threading.RLock()
    
    def record_transition(self, from_state: AppState, to_state: AppState, 
                         duration: float, success: bool, reason: str = ""):
        """
        Записывает переход между состояниями
        
        Args:
            from_state: Исходное состояние
            to_state: Целевое состояние
            duration: Длительность перехода
            success: Успешность перехода
            reason: Причина перехода
        """
        try:
            with self._lock:
                self.metrics.total_transitions += 1
                if success:
                    self.metrics.successful_transitions += 1
                else:
                    self.metrics.failed_transitions += 1
                
                self.metrics.last_transition_time = datetime.now()
                
                # Обновляем время в состояниях
                if from_state == AppState.SLEEPING:
                    self.metrics.time_in_sleeping += duration
                elif from_state == AppState.LISTENING:
                    self.metrics.time_in_listening += duration
                elif from_state == AppState.PROCESSING:
                    self.metrics.time_in_processing += duration
                elif from_state == AppState.ERROR:
                    self.metrics.time_in_error += duration
                
                # Обновляем среднее время перехода
                if self.metrics.total_transitions > 0:
                    self.metrics.average_transition_time = (
                        (self.metrics.average_transition_time * (self.metrics.total_transitions - 1) + duration) 
                        / self.metrics.total_transitions
                    )
                
                # Добавляем в историю
                state_info = StateInfo(
                    state=to_state,
                    timestamp=datetime.now(),
                    duration=duration,
                    reason=reason
                )
                self.state_history.append(state_info)
                
                # Ограничиваем размер истории
                if len(self.state_history) > self.max_history_size:
                    self.state_history.pop(0)
                
        except Exception as e:
            logger.error(f"Ошибка записи перехода: {e}")
    
    def record_error(self, error: Exception, context: str):
        """
        Записывает ошибку
        
        Args:
            error: Исключение
            context: Контекст ошибки
        """
        try:
            with self._lock:
                self.metrics.error_count += 1
                logger.error(f"Ошибка в {context}: {error}")
        except Exception as e:
            logger.error(f"Ошибка записи ошибки: {e}")
    
    def record_recovery(self):
        """Записывает восстановление"""
        try:
            with self._lock:
                self.metrics.recovery_count += 1
                logger.info("Зафиксировано восстановление")
        except Exception as e:
            logger.error(f"Ошибка записи восстановления: {e}")
    
    def get_metrics(self) -> StateMetrics:
        """
        Возвращает метрики
        
        Returns:
            StateMetrics: Текущие метрики
        """
        with self._lock:
            return self.metrics
    
    def get_state_history(self, limit: int = 10) -> List[StateInfo]:
        """
        Возвращает историю состояний
        
        Args:
            limit: Максимальное количество записей
            
        Returns:
            List[StateInfo]: История состояний
        """
        with self._lock:
            return self.state_history[-limit:] if limit > 0 else self.state_history
    
    def get_success_rate(self) -> float:
        """
        Возвращает процент успешных переходов
        
        Returns:
            float: Процент успешных переходов (0.0 - 1.0)
        """
        with self._lock:
            if self.metrics.total_transitions == 0:
                return 0.0
            return self.metrics.successful_transitions / self.metrics.total_transitions
    
    def get_average_time_in_state(self, state: AppState) -> float:
        """
        Возвращает среднее время в состоянии
        
        Args:
            state: Состояние
            
        Returns:
            float: Среднее время в состоянии
        """
        with self._lock:
            if state == AppState.SLEEPING:
                return self.metrics.time_in_sleeping
            elif state == AppState.LISTENING:
                return self.metrics.time_in_listening
            elif state == AppState.PROCESSING:
                return self.metrics.time_in_processing
            elif state == AppState.ERROR:
                return self.metrics.time_in_error
            else:
                return 0.0
    
    def reset_metrics(self):
        """Сбрасывает метрики"""
        try:
            with self._lock:
                self.metrics = StateMetrics()
                self.state_history.clear()
                logger.info("Метрики сброшены")
        except Exception as e:
            logger.error(f"Ошибка сброса метрик: {e}")
    
    def export_metrics(self) -> dict:
        """
        Экспортирует метрики в словарь
        
        Returns:
            dict: Словарь с метриками
        """
        with self._lock:
            return {
                'total_transitions': self.metrics.total_transitions,
                'successful_transitions': self.metrics.successful_transitions,
                'failed_transitions': self.metrics.failed_transitions,
                'success_rate': self.get_success_rate(),
                'time_in_sleeping': self.metrics.time_in_sleeping,
                'time_in_listening': self.metrics.time_in_listening,
                'time_in_processing': self.metrics.time_in_processing,
                'time_in_error': self.metrics.time_in_error,
                'average_transition_time': self.metrics.average_transition_time,
                'error_count': self.metrics.error_count,
                'recovery_count': self.metrics.recovery_count,
                'last_transition_time': self.metrics.last_transition_time.isoformat() if self.metrics.last_transition_time else None
            }
