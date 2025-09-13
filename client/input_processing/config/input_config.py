"""
Конфигурация модулей ввода
"""

from dataclasses import dataclass
from typing import Dict, Any

from ..keyboard.types import KeyboardConfig
from ..speech.types import SpeechConfig

@dataclass
class InputConfig:
    """Общая конфигурация модулей ввода"""
    keyboard: KeyboardConfig
    speech: SpeechConfig
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'InputConfig':
        """Создает конфигурацию из словаря"""
        keyboard_config = KeyboardConfig(**config_dict.get('keyboard', {}))
        speech_config = SpeechConfig(**config_dict.get('speech', {}))
        
        return cls(
            keyboard=keyboard_config,
            speech=speech_config
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразует конфигурацию в словарь"""
        return {
            'keyboard': {
                'key_to_monitor': self.keyboard.key_to_monitor,
                'short_press_threshold': self.keyboard.short_press_threshold,
                'long_press_threshold': self.keyboard.long_press_threshold,
                'event_cooldown': self.keyboard.event_cooldown,
                'hold_check_interval': self.keyboard.hold_check_interval,
                'debounce_time': self.keyboard.debounce_time,
            },
            'speech': {
                'sample_rate': self.speech.sample_rate,
                'chunk_size': self.speech.chunk_size,
                'channels': self.speech.channels,
                'dtype': self.speech.dtype,
                'energy_threshold': self.speech.energy_threshold,
                'dynamic_energy_threshold': self.speech.dynamic_energy_threshold,
                'pause_threshold': self.speech.pause_threshold,
                'phrase_threshold': self.speech.phrase_threshold,
                'non_speaking_duration': self.speech.non_speaking_duration,
                'max_duration': self.speech.max_duration,
                'auto_start': self.speech.auto_start,
            }
        }

# Конфигурация по умолчанию
DEFAULT_INPUT_CONFIG = InputConfig(
    keyboard=KeyboardConfig(
        key_to_monitor="space",
        short_press_threshold=0.6,
        long_press_threshold=2.0,
        event_cooldown=0.1,
        hold_check_interval=0.05,
        debounce_time=0.1
    ),
    speech=SpeechConfig(
        sample_rate=16000,
        chunk_size=1024,
        channels=1,
        dtype='int16',
        energy_threshold=100,
        dynamic_energy_threshold=True,
        pause_threshold=0.5,
        phrase_threshold=0.3,
        non_speaking_duration=0.3,
        max_duration=30.0,
        auto_start=True
    )
)
