"""
ApplicationStateManager - Управление состоянием приложения
"""

import logging
from typing import Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)

class AppMode(Enum):
    """Режимы приложения"""
    SLEEPING = "sleeping"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"

class ApplicationStateManager:
    """Менеджер состояния приложения"""
    
    def __init__(self):
        self.current_mode = AppMode.SLEEPING
        self.previous_mode = None
        self.mode_history = []
        self.state_data = {}
        
    def set_mode(self, mode: AppMode):
        """Установить режим приложения"""
        try:
            if self.current_mode != mode:
                self.previous_mode = self.current_mode
                self.current_mode = mode
                
                # Добавляем в историю
                self.mode_history.append({
                    "mode": mode,
                    "previous_mode": self.previous_mode,
                    "timestamp": self._get_timestamp()
                })
                
                # Ограничиваем историю
                if len(self.mode_history) > 100:
                    self.mode_history.pop(0)
                
                logger.info(f"🔄 Режим изменен: {self.previous_mode.value} → {mode.value}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка установки режима: {e}")
    
    def get_current_mode(self) -> AppMode:
        """Получить текущий режим"""
        return self.current_mode
    
    def get_previous_mode(self) -> Optional[AppMode]:
        """Получить предыдущий режим"""
        return self.previous_mode
    
    def set_state_data(self, key: str, value: Any):
        """Установить данные состояния"""
        try:
            self.state_data[key] = value
            logger.debug(f"📊 Данные состояния обновлены: {key}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка установки данных состояния: {e}")
    
    def get_state_data(self, key: str, default: Any = None) -> Any:
        """Получить данные состояния"""
        return self.state_data.get(key, default)
    
    def get_mode_history(self, limit: int = 10) -> list:
        """Получить историю режимов"""
        return self.mode_history[-limit:]
    
    def _get_timestamp(self) -> float:
        """Получить текущий timestamp"""
        import time
        return time.time()
    
    def get_status(self) -> Dict[str, Any]:
        """Получить статус менеджера состояния"""
        return {
            "current_mode": self.current_mode.value,
            "previous_mode": self.previous_mode.value if self.previous_mode else None,
            "mode_history_size": len(self.mode_history),
            "state_data_keys": list(self.state_data.keys())
        }
