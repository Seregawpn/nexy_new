"""
Welcome Message Module — серверная генерация приветственного сообщения при запуске приложения.
"""

from .core.welcome_player import WelcomePlayer
from .core.types import WelcomeConfig, WelcomeState, WelcomeResult

__version__ = "1.0.0"
__all__ = ["WelcomePlayer", "WelcomeConfig", "WelcomeState", "WelcomeResult"]
