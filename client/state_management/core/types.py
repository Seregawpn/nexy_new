"""
Типы данных для модуля управления состояниями
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime


class AppState(Enum):
    """Состояния приложения - упрощенная модель как в main.py"""
    SLEEPING = "sleeping"      # Ассистент спит, ждет команды
    LISTENING = "listening"    # Ассистент слушает команды (микрофон активен)
    PROCESSING = "processing"  # Ассистент обрабатывает команду (микрофон неактивен)


class StateTransition(Enum):
    """Переходы между состояниями - упрощенная модель"""
    SLEEP_TO_LISTEN = "sleep_to_listen"      # Пользователь нажал кнопку
    LISTEN_TO_PROCESS = "listen_to_process"  # Команда распознана
    PROCESS_TO_SLEEP = "process_to_sleep"    # Обработка завершена


@dataclass
class StateMetrics:
    """Метрики состояний - упрощенная модель"""
    total_transitions: int = 0
    successful_transitions: int = 0
    failed_transitions: int = 0
    time_in_sleeping: float = 0.0
    time_in_listening: float = 0.0
    time_in_processing: float = 0.0
    average_transition_time: float = 0.0
    last_transition_time: Optional[datetime] = None


@dataclass
class StateInfo:
    """Информация о состоянии"""
    state: AppState
    timestamp: datetime
    duration: float = 0.0
    reason: str = ""
    metadata: Dict[str, Any] = None


@dataclass
class StateConfig:
    """Конфигурация управления состояниями"""
    max_history_size: int = 100
    transition_timeout: float = 30.0
    recovery_attempts: int = 3
    recovery_delay: float = 1.0
    enable_monitoring: bool = True
    enable_recovery: bool = True
    log_transitions: bool = True


# Callback типы
StateChangedCallback = Callable[[AppState, AppState, str], None]
ErrorCallback = Callable[[Exception, str], None]
RecoveryCallback = Callable[[AppState], None]
StateRecoveryCallback = RecoveryCallback  # Алиас для совместимости
