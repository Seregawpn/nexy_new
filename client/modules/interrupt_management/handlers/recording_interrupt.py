"""
Обработчик прерывания записи - ИНТЕГРАЦИЯ с speech_recognizer
"""

import logging
from typing import Optional, Dict, Any
from ..core.types import InterruptEvent, InterruptType

logger = logging.getLogger(__name__)

class RecordingInterruptHandler:
    """Обработчик прерывания записи - использует speech_recognizer"""
    
    def __init__(self, speech_recognizer=None):
        self.speech_recognizer = speech_recognizer
        
    async def handle_recording_stop(self, event: InterruptEvent) -> bool:
        """Обрабатывает остановку записи через speech_recognizer"""
        try:
            logger.info("🛑 Обработка остановки записи")
            
            if self.speech_recognizer:
                # Используем существующий метод stop_recording()
                text = await self.speech_recognizer.stop_recording()
                if text:
                    logger.info(f"✅ Запись остановлена, распознано: {text[:50]}...")
                    event.data = {"recognized_text": text}
                else:
                    logger.info("✅ Запись остановлена")
                    
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка остановки записи: {e}")
            return False
            
    async def handle_recording_start(self, event: InterruptEvent) -> bool:
        """Обрабатывает начало записи через speech_recognizer"""
        try:
            logger.info("🎤 Обработка начала записи")
            
            if self.speech_recognizer:
                success = await self.speech_recognizer.start_recording()
                if success:
                    logger.info("✅ Запись начата через speech_recognizer")
                else:
                    logger.warning("⚠️ Не удалось начать запись")
                    
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка начала записи: {e}")
            return False
