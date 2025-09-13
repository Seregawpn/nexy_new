"""
Режим речи - ИНТЕГРАЦИЯ с speech_playback
"""

import logging
from typing import Optional, Dict, Any
from ..core.types import AppMode, ModeEvent, ModeStatus

logger = logging.getLogger(__name__)

class SpeakingMode:
    """Режим речи - использует speech_playback"""
    
    def __init__(self, speech_player=None, audio_device_manager=None):
        self.speech_player = speech_player
        self.audio_device_manager = audio_device_manager
        self.is_active = False
        
    async def enter_mode(self, context: Dict[str, Any] = None):
        """Вход в режим речи"""
        try:
            logger.info("🎤 Вход в режим речи")
            self.is_active = True
            
            # Убеждаемся, что используется лучшее аудио устройство
            if self.audio_device_manager:
                try:
                    await self.audio_device_manager.switch_to_best_device()
                    logger.info("🔊 Переключились на лучшее аудио устройство")
                except Exception as e:
                    logger.warning(f"⚠️ Не удалось переключить аудио устройство: {e}")
                    
            # Настраиваем плеер для воспроизведения
            if self.speech_player:
                try:
                    # Проверяем, что плеер готов к воспроизведению
                    if hasattr(self.speech_player, 'is_ready'):
                        if not self.speech_player.is_ready():
                            logger.warning("⚠️ Плеер не готов к воспроизведению")
                    else:
                        logger.debug("ℹ️ Плеер готов к воспроизведению")
                        
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка проверки готовности плеера: {e}")
                    
            logger.info("✅ Режим речи активирован")
            
        except Exception as e:
            logger.error(f"❌ Ошибка входа в режим речи: {e}")
            self.is_active = False
            
    async def exit_mode(self):
        """Выход из режима речи"""
        try:
            logger.info("🛑 Выход из режима речи")
            self.is_active = False
            
            # Останавливаем воспроизведение
            if self.speech_player:
                try:
                    self.speech_player.stop_playback()
                    logger.info("🛑 Воспроизведение остановлено")
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка остановки воспроизведения: {e}")
                    
            logger.info("✅ Режим речи деактивирован")
            
        except Exception as e:
            logger.error(f"❌ Ошибка выхода из режима речи: {e}")
            
    async def handle_interrupt(self):
        """Обработка прерывания в режиме речи"""
        try:
            logger.info("⚠️ Прерывание в режиме речи")
            
            # Останавливаем воспроизведение
            if self.speech_player:
                try:
                    self.speech_player.stop_playback()
                    logger.info("🛑 Воспроизведение прервано")
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка прерывания воспроизведения: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Ошибка прерывания в режиме речи: {e}")
            
    async def handle_pause(self):
        """Обработка паузы в режиме речи"""
        try:
            logger.info("⏸️ Пауза в режиме речи")
            
            if self.speech_player:
                try:
                    self.speech_player.pause_playback()
                    logger.info("⏸️ Воспроизведение приостановлено")
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка паузы воспроизведения: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Ошибка паузы в режиме речи: {e}")
            
    async def handle_resume(self):
        """Обработка возобновления в режиме речи"""
        try:
            logger.info("▶️ Возобновление в режиме речи")
            
            if self.speech_player:
                try:
                    self.speech_player.resume_playback()
                    logger.info("▶️ Воспроизведение возобновлено")
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка возобновления воспроизведения: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Ошибка возобновления в режиме речи: {e}")
            
    def is_speaking(self) -> bool:
        """Проверяет, идет ли речь"""
        if not self.speech_player:
            return False
            
        try:
            if hasattr(self.speech_player, 'is_playing'):
                return self.speech_player.is_playing()
            elif hasattr(self.speech_player, 'get_status'):
                status = self.speech_player.get_status()
                return status.get('is_playing', False)
            else:
                return False
        except Exception as e:
            logger.warning(f"⚠️ Ошибка проверки состояния речи: {e}")
            return False
            
    def get_status(self) -> Dict[str, Any]:
        """Возвращает статус режима речи"""
        return {
            "is_active": self.is_active,
            "is_speaking": self.is_speaking(),
            "speech_player_available": self.speech_player is not None,
            "audio_device_manager_available": self.audio_device_manager is not None,
        }
