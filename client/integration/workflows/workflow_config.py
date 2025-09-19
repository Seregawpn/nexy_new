"""
Конфигурация для Workflows
Настройки таймаутов, дебаунса и других параметров
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass
class ListeningWorkflowConfig:
    """Конфигурация для ListeningWorkflow"""
    
    # Дебаунс - защита от случайных нажатий
    debounce_threshold: float = 0.3  # секунд
    
    # Таймауты
    max_listening_duration: float = 30.0  # секунд - максимальная длительность записи
    silence_timeout: float = 5.0  # секунд - таймаут тишины
    
    # Активность голоса
    voice_activity_enabled: bool = False  # мониторинг активности голоса
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'ListeningWorkflowConfig':
        """Создание конфигурации из словаря"""
        return cls(
            debounce_threshold=float(config_dict.get('debounce_threshold', 0.3)),
            max_listening_duration=float(config_dict.get('max_listening_duration', 30.0)),
            silence_timeout=float(config_dict.get('silence_timeout', 5.0)),
            voice_activity_enabled=bool(config_dict.get('voice_activity_enabled', False))
        )

@dataclass  
class ProcessingWorkflowConfig:
    """Конфигурация для ProcessingWorkflow"""
    
    # Таймауты этапов
    stage_timeout: float = 30.0  # секунд на каждый этап
    total_timeout: float = 300.0  # секунд общий таймаут (5 минут)
    
    # Специфичные таймауты
    screenshot_timeout: float = 10.0  # секунд на захват скриншота
    grpc_timeout: float = 60.0  # секунд на gRPC запрос
    playback_timeout: float = 180.0  # секунд на воспроизведение (3 минуты)
    
    # Graceful degradation
    continue_without_screenshot: bool = True  # продолжать без скриншота при ошибке
    max_retries: int = 1  # количество повторных попыток при ошибках
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'ProcessingWorkflowConfig':
        """Создание конфигурации из словаря"""
        return cls(
            stage_timeout=float(config_dict.get('stage_timeout', 30.0)),
            total_timeout=float(config_dict.get('total_timeout', 300.0)),
            screenshot_timeout=float(config_dict.get('screenshot_timeout', 10.0)),
            grpc_timeout=float(config_dict.get('grpc_timeout', 60.0)),
            playback_timeout=float(config_dict.get('playback_timeout', 180.0)),
            continue_without_screenshot=bool(config_dict.get('continue_without_screenshot', True)),
            max_retries=int(config_dict.get('max_retries', 1))
        )

@dataclass
class WorkflowsConfig:
    """Общая конфигурация для всех Workflows"""
    
    listening: ListeningWorkflowConfig
    processing: ProcessingWorkflowConfig
    
    # Общие настройки
    enabled: bool = True
    debug_mode: bool = False
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'WorkflowsConfig':
        """Создание конфигурации из словаря"""
        listening_config = ListeningWorkflowConfig.from_dict(
            config_dict.get('listening', {})
        )
        processing_config = ProcessingWorkflowConfig.from_dict(
            config_dict.get('processing', {})
        )
        
        return cls(
            listening=listening_config,
            processing=processing_config,
            enabled=bool(config_dict.get('enabled', True)),
            debug_mode=bool(config_dict.get('debug_mode', False))
        )
    
    @classmethod
    def default(cls) -> 'WorkflowsConfig':
        """Конфигурация по умолчанию"""
        return cls(
            listening=ListeningWorkflowConfig(),
            processing=ProcessingWorkflowConfig()
        )

# Конфигурация по умолчанию для macOS
DEFAULT_MACOS_CONFIG = {
    'enabled': True,
    'debug_mode': False,
    'listening': {
        'debounce_threshold': 0.3,  # Быстрая реакция для macOS
        'max_listening_duration': 30.0,
        'silence_timeout': 5.0,
        'voice_activity_enabled': False  # Отключено для стабильности
    },
    'processing': {
        'stage_timeout': 30.0,
        'total_timeout': 300.0,  # 5 минут для длинных ответов
        'screenshot_timeout': 10.0,
        'grpc_timeout': 60.0,
        'playback_timeout': 180.0,  # 3 минуты для длинных аудио
        'continue_without_screenshot': True,  # Graceful degradation
        'max_retries': 1
    }
}
