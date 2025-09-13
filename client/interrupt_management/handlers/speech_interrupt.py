"""
Обработчик прерывания речи - ИНТЕГРАЦИЯ с speech_playback
"""

import logging
from typing import Optional, Dict, Any
from ..core.types import InterruptEvent, InterruptType

logger = logging.getLogger(__name__)

class SpeechInterruptHandler:
    """Обработчик прерывания речи - использует speech_playback"""
    
    def __init__(self, speech_player=None, grpc_client=None):
        self.speech_player = speech_player
        self.grpc_client = grpc_client
        
    async def handle_speech_stop(self, event: InterruptEvent) -> bool:
        """Обрабатывает остановку речи через speech_playback"""
        try:
            logger.info("🛑 Обработка остановки речи")
            
            # Останавливаем плеер через speech_playback
            if self.speech_player:
                success = self.speech_player.stop_playback()
                if success:
                    logger.info("✅ Речь остановлена через speech_playback")
                else:
                    logger.warning("⚠️ Не удалось остановить речь через speech_playback")
                    
            # Отправляем прерывание на сервер
            if self.grpc_client:
                try:
                    await self.grpc_client.interrupt_session()
                    logger.info("📡 Прерывание отправлено на сервер")
                except Exception as e:
                    logger.error(f"❌ Ошибка отправки прерывания на сервер: {e}")
                    
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка остановки речи: {e}")
            return False
            
    async def handle_speech_pause(self, event: InterruptEvent) -> bool:
        """Обрабатывает паузу речи через speech_playback"""
        try:
            logger.info("⏸️ Обработка паузы речи")
            
            if self.speech_player:
                success = self.speech_player.pause_playback()
                if success:
                    logger.info("✅ Речь приостановлена через speech_playback")
                else:
                    logger.warning("⚠️ Не удалось приостановить речь")
                    
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка паузы речи: {e}")
            return False
            
    async def handle_speech_resume(self, event: InterruptEvent) -> bool:
        """Обрабатывает возобновление речи через speech_playback"""
        try:
            logger.info("▶️ Обработка возобновления речи")
            
            if self.speech_player:
                success = self.speech_player.resume_playback()
                if success:
                    logger.info("✅ Речь возобновлена через speech_playback")
                else:
                    logger.warning("⚠️ Не удалось возобновить речь")
                    
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка возобновления речи: {e}")
            return False
