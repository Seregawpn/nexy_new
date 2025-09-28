"""
Session Management Module - Управление сессиями

Модуль предоставляет функциональность для:
- Управления пользовательскими сессиями
- Генерации уникальных Hardware ID
- Отслеживания активных сессий
- Интеграции с gRPC сервисом

Совместим с существующим кодом сессий
"""

from .core.session_manager import SessionManager
from .config import SessionManagementConfig

__all__ = ['SessionManager', 'SessionManagementConfig']
__version__ = '1.0.0'



