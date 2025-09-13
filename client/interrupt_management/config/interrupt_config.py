"""
Конфигурация модуля прерываний
"""

from dataclasses import dataclass
from typing import Dict, Any

from ..core.types import InterruptConfig, InterruptType, InterruptPriority

@dataclass
class InterruptModuleConfig:
    """Конфигурация модуля прерываний"""
    coordinator: InterruptConfig
    enable_speech_interrupts: bool = True
    enable_recording_interrupts: bool = True
    enable_session_interrupts: bool = True
    enable_full_reset: bool = True
    
    # Настройки для каждого типа прерывания
    speech_interrupt_timeout: float = 5.0
    recording_interrupt_timeout: float = 3.0
    session_interrupt_timeout: float = 10.0
    full_reset_timeout: float = 15.0
    
    # Приоритеты по умолчанию
    default_priorities: Dict[InterruptType, InterruptPriority] = None
    
    def __post_init__(self):
        if self.default_priorities is None:
            self.default_priorities = {
                InterruptType.SPEECH_STOP: InterruptPriority.HIGH,
                InterruptType.SPEECH_PAUSE: InterruptPriority.NORMAL,
                InterruptType.RECORDING_STOP: InterruptPriority.NORMAL,
                InterruptType.SESSION_CLEAR: InterruptPriority.HIGH,
                InterruptType.FULL_RESET: InterruptPriority.CRITICAL,
            }
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'InterruptModuleConfig':
        """Создает конфигурацию из словаря"""
        coordinator_config = InterruptConfig(**config_dict.get('coordinator', {}))
        
        return cls(
            coordinator=coordinator_config,
            enable_speech_interrupts=config_dict.get('enable_speech_interrupts', True),
            enable_recording_interrupts=config_dict.get('enable_recording_interrupts', True),
            enable_session_interrupts=config_dict.get('enable_session_interrupts', True),
            enable_full_reset=config_dict.get('enable_full_reset', True),
            speech_interrupt_timeout=config_dict.get('speech_interrupt_timeout', 5.0),
            recording_interrupt_timeout=config_dict.get('recording_interrupt_timeout', 3.0),
            session_interrupt_timeout=config_dict.get('session_interrupt_timeout', 10.0),
            full_reset_timeout=config_dict.get('full_reset_timeout', 15.0),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразует конфигурацию в словарь"""
        return {
            'coordinator': {
                'max_concurrent_interrupts': self.coordinator.max_concurrent_interrupts,
                'interrupt_timeout': self.coordinator.interrupt_timeout,
                'retry_attempts': self.coordinator.retry_attempts,
                'retry_delay': self.coordinator.retry_delay,
                'enable_logging': self.coordinator.enable_logging,
                'enable_metrics': self.coordinator.enable_metrics,
            },
            'enable_speech_interrupts': self.enable_speech_interrupts,
            'enable_recording_interrupts': self.enable_recording_interrupts,
            'enable_session_interrupts': self.enable_session_interrupts,
            'enable_full_reset': self.enable_full_reset,
            'speech_interrupt_timeout': self.speech_interrupt_timeout,
            'recording_interrupt_timeout': self.recording_interrupt_timeout,
            'session_interrupt_timeout': self.session_interrupt_timeout,
            'full_reset_timeout': self.full_reset_timeout,
        }

# Конфигурация по умолчанию
DEFAULT_INTERRUPT_CONFIG = InterruptModuleConfig(
    coordinator=InterruptConfig(
        max_concurrent_interrupts=5,
        interrupt_timeout=10.0,
        retry_attempts=3,
        retry_delay=1.0,
        enable_logging=True,
        enable_metrics=True
    ),
    enable_speech_interrupts=True,
    enable_recording_interrupts=True,
    enable_session_interrupts=True,
    enable_full_reset=True,
    speech_interrupt_timeout=5.0,
    recording_interrupt_timeout=3.0,
    session_interrupt_timeout=10.0,
    full_reset_timeout=15.0
)
