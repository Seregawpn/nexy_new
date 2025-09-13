"""
Модуль управления состояниями приложения - УПРОЩЕННАЯ ВЕРСИЯ

Этот модуль предоставляет:
- Простое управление 3 состояниями: SLEEPING, LISTENING, PROCESSING
- Точную копию логики из main.py StateManager
- Совместимость с существующим кодом
- Минимальную сложность и максимальную понятность
"""

from .core.simple_state_manager import SimpleStateManager, create_simple_state_manager
from .core.types import AppState, StateTransition, StateConfig, StateMetrics, StateInfo
from .config.state_config import create_config

# Для обратной совместимости
StateManager = SimpleStateManager
create_state_manager = create_simple_state_manager

# Версия модуля
__version__ = "2.0.0-simplified"

# Экспортируемые классы и функции
__all__ = [
    # Основные классы
    "SimpleStateManager",
    "StateManager",  # Алиас для совместимости
    
    # Типы данных
    "AppState",
    "StateTransition", 
    "StateConfig",
    "StateMetrics",
    "StateInfo",
    
    # Функции создания
    "create_simple_state_manager",
    "create_state_manager",  # Алиас для совместимости
    "create_config",
    
    # Версия
    "__version__"
]


def create_default_state_manager(console=None, audio_player=None, stt_recognizer=None, 
                                screen_capture=None, grpc_client=None, network_manager=None, 
                                hardware_id=None, input_handler=None, tray_controller=None) -> StateManager:
    """
    Создает SimpleStateManager с конфигурацией по умолчанию
    
    Args:
        console: Консоль для вывода
        audio_player: Аудио плеер
        stt_recognizer: Распознаватель речи
        screen_capture: Захват экрана
        grpc_client: gRPC клиент
        network_manager: Менеджер сети
        hardware_id: ID оборудования
        input_handler: Обработчик ввода
        tray_controller: Контроллер трея
        
    Returns:
        StateManager: Экземпляр менеджера состояний
    """
    config = create_config("default")
    return create_simple_state_manager(
        console=console,
        audio_player=audio_player,
        stt_recognizer=stt_recognizer,
        screen_capture=screen_capture,
        grpc_client=grpc_client,
        network_manager=network_manager,
        hardware_id=hardware_id,
        input_handler=input_handler,
        tray_controller=tray_controller,
        config=config
    )
