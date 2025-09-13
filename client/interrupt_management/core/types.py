"""
Типы данных для управления прерываниями
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

class InterruptType(Enum):
    """Типы прерываний"""
    SPEECH_STOP = "speech_stop"           # Остановка речи
    SPEECH_PAUSE = "speech_pause"         # Пауза речи
    RECORDING_STOP = "recording_stop"     # Остановка записи
    SESSION_CLEAR = "session_clear"       # Очистка сессии
    FULL_RESET = "full_reset"             # Полный сброс

class InterruptPriority(Enum):
    """Приоритеты прерываний"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4

class InterruptStatus(Enum):
    """Статусы прерываний"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class InterruptEvent:
    """Событие прерывания"""
    type: InterruptType
    priority: InterruptPriority
    source: str
    timestamp: float
    status: InterruptStatus = InterruptStatus.PENDING
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    result: Optional[Any] = None

@dataclass
class InterruptConfig:
    """Конфигурация прерываний"""
    max_concurrent_interrupts: int = 5
    interrupt_timeout: float = 10.0
    retry_attempts: int = 3
    retry_delay: float = 1.0
    enable_logging: bool = True
    enable_metrics: bool = True

@dataclass
class InterruptMetrics:
    """Метрики прерываний"""
    total_interrupts: int = 0
    successful_interrupts: int = 0
    failed_interrupts: int = 0
    average_processing_time: float = 0.0
    interrupts_by_type: Dict[InterruptType, int] = None
    interrupts_by_priority: Dict[InterruptPriority, int] = None
    
    def __post_init__(self):
        if self.interrupts_by_type is None:
            self.interrupts_by_type = {t: 0 for t in InterruptType}
        if self.interrupts_by_priority is None:
            self.interrupts_by_priority = {p: 0 for p in InterruptPriority}
