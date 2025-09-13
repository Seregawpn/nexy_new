"""
Режим записи - ИНТЕГРАЦИЯ с speech_recognizer
"""

import logging
from typing import Optional, Dict, Any
from ..core.types import AppMode, ModeEvent, ModeStatus

logger = logging.getLogger(__name__)

class RecordingMode:
    """Режим записи - использует speech_recognizer"""
    
    def __init__(self, speech_recognizer=None):
        self.speech_recognizer = speech_recognizer
        self.is_active = False
        self.recording_start_time = None
        
    async def enter_mode(self, context: Dict[str, Any] = None):
        """Вход в режим записи"""
        try:
            logger.info("🎤 Вход в режим записи")
            self.is_active = True
            self.recording_start_time = None
            
            # Начинаем запись
            if self.speech_recognizer:
                try:
                    success = await self.speech_recognizer.start_recording()
                    if success:
                        logger.info("🎤 Запись начата")
                        self.recording_start_time = time.time()
                    else:
                        logger.warning("⚠️ Не удалось начать запись")
                        self.is_active = False
                except Exception as e:
                    logger.error(f"❌ Ошибка начала записи: {e}")
                    self.is_active = False
            else:
                logger.warning("⚠️ Распознаватель речи недоступен")
                self.is_active = False
                
            logger.info("✅ Режим записи активирован")
            
        except Exception as e:
            logger.error(f"❌ Ошибка входа в режим записи: {e}")
            self.is_active = False
            
    async def exit_mode(self):
        """Выход из режима записи"""
        try:
            logger.info("🛑 Выход из режима записи")
            self.is_active = False
            
            # Останавливаем запись
            if self.speech_recognizer:
                try:
                    text = await self.speech_recognizer.stop_recording()
                    if text:
                        logger.info(f"📝 Запись остановлена, распознано: {text[:50]}...")
                    else:
                        logger.info("🛑 Запись остановлена")
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка остановки записи: {e}")
                    
            self.recording_start_time = None
            logger.info("✅ Режим записи деактивирован")
            
        except Exception as e:
            logger.error(f"❌ Ошибка выхода из режима записи: {e}")
            
    async def handle_interrupt(self):
        """Обработка прерывания в режиме записи"""
        try:
            logger.info("⚠️ Прерывание в режиме записи")
            
            # Останавливаем запись
            if self.speech_recognizer:
                try:
                    await self.speech_recognizer.stop_recording()
                    logger.info("🛑 Запись прервана")
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка прерывания записи: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Ошибка прерывания в режиме записи: {e}")
            
    def is_recording(self) -> bool:
        """Проверяет, идет ли запись"""
        if not self.speech_recognizer:
            return False
            
        try:
            if hasattr(self.speech_recognizer, 'is_recording'):
                return self.speech_recognizer.is_recording()
            elif hasattr(self.speech_recognizer, 'get_status'):
                status = self.speech_recognizer.get_status()
                return status.get('is_recording', False)
            else:
                return False
        except Exception as e:
            logger.warning(f"⚠️ Ошибка проверки состояния записи: {e}")
            return False
            
    def get_recording_duration(self) -> float:
        """Возвращает длительность записи в секундах"""
        if not self.recording_start_time:
            return 0.0
            
        try:
            import time
            return time.time() - self.recording_start_time
        except Exception as e:
            logger.warning(f"⚠️ Ошибка расчета длительности записи: {e}")
            return 0.0
            
    def get_status(self) -> Dict[str, Any]:
        """Возвращает статус режима записи"""
        return {
            "is_active": self.is_active,
            "is_recording": self.is_recording(),
            "recording_duration": self.get_recording_duration(),
            "speech_recognizer_available": self.speech_recognizer is not None,
        }
