"""
Режим прослушивания - запись и распознавание речи
"""

import logging
import time
from typing import Optional, Dict, Any
from ..core.types import AppMode, ModeEvent, ModeStatus

logger = logging.getLogger(__name__)

class ListeningMode:
    """Режим прослушивания - запись и распознавание речи"""
    
    def __init__(self, speech_recognizer=None, audio_device_manager=None):
        self.speech_recognizer = speech_recognizer
        self.audio_device_manager = audio_device_manager
        self.is_active = False
        self.listening_start_time = None
        self.recognized_text = None
        
    async def enter_mode(self, context: Dict[str, Any] = None):
        """Вход в режим прослушивания"""
        try:
            logger.info("👂 Вход в режим прослушивания")
            self.is_active = True
            self.listening_start_time = time.time()
            self.recognized_text = None
            
            # Настраиваем аудио устройство
            if self.audio_device_manager:
                try:
                    await self.audio_device_manager.switch_to_best_device()
                    logger.info("🔊 Переключились на лучшее аудио устройство")
                except Exception as e:
                    logger.warning(f"⚠️ Не удалось переключить аудио устройство: {e}")
                    
            # Начинаем прослушивание
            if self.speech_recognizer:
                try:
                    success = await self.speech_recognizer.start_recording()
                    if success:
                        logger.info("🎤 Прослушивание начато")
                    else:
                        logger.warning("⚠️ Не удалось начать прослушивание")
                        self.is_active = False
                except Exception as e:
                    logger.error(f"❌ Ошибка начала прослушивания: {e}")
                    self.is_active = False
            else:
                logger.warning("⚠️ Распознаватель речи недоступен")
                self.is_active = False
                
            logger.info("✅ Режим прослушивания активирован")
            
        except Exception as e:
            logger.error(f"❌ Ошибка входа в режим прослушивания: {e}")
            self.is_active = False
            
    async def exit_mode(self):
        """Выход из режима прослушивания"""
        try:
            logger.info("🛑 Выход из режима прослушивания")
            self.is_active = False
            
            # Останавливаем прослушивание
            if self.speech_recognizer:
                try:
                    self.recognized_text = await self.speech_recognizer.stop_recording()
                    if self.recognized_text:
                        logger.info(f"📝 Распознанный текст: {self.recognized_text[:50]}...")
                    else:
                        logger.info("🛑 Прослушивание остановлено")
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка остановки прослушивания: {e}")
                    
            self.listening_start_time = None
            logger.info("✅ Режим прослушивания деактивирован")
            
        except Exception as e:
            logger.error(f"❌ Ошибка выхода из режима прослушивания: {e}")
            
    async def handle_interrupt(self):
        """Обработка прерывания в режиме прослушивания"""
        try:
            logger.info("⚠️ Прерывание в режиме прослушивания")
            
            # Останавливаем прослушивание
            if self.speech_recognizer:
                try:
                    await self.speech_recognizer.stop_recording()
                    logger.info("🛑 Прослушивание прервано")
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка прерывания прослушивания: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Ошибка прерывания в режиме прослушивания: {e}")
            
    def is_listening(self) -> bool:
        """Проверяет, идет ли прослушивание"""
        if not self.speech_recognizer:
            return False
            
        try:
            if hasattr(self.speech_recognizer, 'is_recording'):
                if callable(self.speech_recognizer.is_recording):
                    return self.speech_recognizer.is_recording()
                else:
                    return self.speech_recognizer.is_recording
            elif hasattr(self.speech_recognizer, 'get_status'):
                status = self.speech_recognizer.get_status()
                return status.get('is_recording', False)
            else:
                return False
        except Exception as e:
            logger.warning(f"⚠️ Ошибка проверки состояния прослушивания: {e}")
            return False
            
    def get_listening_duration(self) -> float:
        """Возвращает длительность прослушивания в секундах"""
        if not self.listening_start_time:
            return 0.0
            
        try:
            return time.time() - self.listening_start_time
        except Exception as e:
            logger.warning(f"⚠️ Ошибка расчета длительности прослушивания: {e}")
            return 0.0
            
    def get_recognized_text(self) -> Optional[str]:
        """Возвращает распознанный текст"""
        return self.recognized_text
            
    def get_status(self) -> Dict[str, Any]:
        """Возвращает статус режима прослушивания"""
        return {
            "is_active": self.is_active,
            "is_listening": self.is_listening(),
            "listening_duration": self.get_listening_duration(),
            "recognized_text": self.recognized_text,
            "speech_recognizer_available": self.speech_recognizer is not None,
            "audio_device_manager_available": self.audio_device_manager is not None,
            "description": "Режим прослушивания и распознавания речи"
        }