"""
Режим сна - базовый режим ожидания
"""

import logging
import time
from typing import Optional, Dict, Any
from ..core.types import AppMode, ModeEvent, ModeStatus

logger = logging.getLogger(__name__)

class SleepingMode:
    """Режим сна - базовый режим ожидания"""
    
    def __init__(self):
        self.is_active = False
        self.sleep_start_time = None
        
    async def enter_mode(self, context: Dict[str, Any] = None):
        """Вход в режим сна"""
        try:
            logger.info("😴 Вход в режим сна")
            self.is_active = True
            self.sleep_start_time = time.time()
            
            # Логика входа в режим сна
            logger.info("✅ Режим сна активирован")
            
        except Exception as e:
            logger.error(f"❌ Ошибка входа в режим сна: {e}")
            self.is_active = False
            
    async def exit_mode(self):
        """Выход из режима сна"""
        try:
            logger.info("🌅 Выход из режима сна")
            self.is_active = False
            self.sleep_start_time = None
            
            logger.info("✅ Режим сна деактивирован")
            
        except Exception as e:
            logger.error(f"❌ Ошибка выхода из режима сна: {e}")
            
    async def handle_wake_up(self):
        """Обработка пробуждения"""
        try:
            logger.info("🌅 Пробуждение от сна")
            
            # Логика пробуждения
            logger.info("✅ Пробуждение обработано")
            
        except Exception as e:
            logger.error(f"❌ Ошибка пробуждения: {e}")
            
    def is_sleeping(self) -> bool:
        """Проверяет, спит ли система"""
        return self.is_active
            
    def get_sleep_duration(self) -> float:
        """Возвращает длительность сна в секундах"""
        if not self.sleep_start_time:
            return 0.0
            
        try:
            return time.time() - self.sleep_start_time
        except Exception as e:
            logger.warning(f"⚠️ Ошибка расчета длительности сна: {e}")
            return 0.0
            
    def get_status(self) -> Dict[str, Any]:
        """Возвращает статус режима сна"""
        return {
            "is_active": self.is_active,
            "is_sleeping": self.is_sleeping(),
            "sleep_duration": self.get_sleep_duration(),
        }