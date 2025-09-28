"""
Database Module - Управление базой данных

Модуль предоставляет функциональность для:
- Управления подключением к PostgreSQL
- CRUD операций для всех таблиц БД
- Асинхронных операций с базой данных
- Управления соединениями и пулом

100% совместим с существующим database_manager.py
"""

from .core.database_manager import DatabaseManager
from .config import DatabaseConfig

__all__ = ['DatabaseManager', 'DatabaseConfig']
__version__ = '1.0.0'



