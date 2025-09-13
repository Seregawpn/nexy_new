"""
Распознавание речи - рефакторинг из stt_recognizer.py
"""

import asyncio
import threading
import time
import logging
from typing import Optional, Callable, Dict, Any

import sounddevice as sd
import numpy as np
import speech_recognition as sr

from .types import SpeechEvent, SpeechEventType, SpeechState, SpeechConfig

logger = logging.getLogger(__name__)

class SpeechRecognizer:
    """Распознавание речи с поддержкой различных состояний"""
    
    def __init__(self, config: SpeechConfig):
        self.config = config
        self.sample_rate = config.sample_rate
        self.chunk_size = config.chunk_size
        self.channels = config.channels
        self.dtype = config.dtype
        
        # Состояние
        self.state = SpeechState.IDLE
        self.is_recording = False
        self.audio_chunks = []
        
        # Threading
        self.recording_thread = None
        self.stream_lock = threading.Lock()
        self.stop_event = threading.Event()
        
        # Callbacks
        self.state_callbacks: Dict[SpeechState, Callable] = {}
        self.event_callbacks: Dict[SpeechEventType, Callable] = {}
        
        # Инициализируем распознаватель
        self._init_recognizer()
    
    def _init_recognizer(self):
        """Инициализирует распознаватель речи"""
        try:
            self.recognizer = sr.Recognizer()
            self.recognizer.energy_threshold = self.config.energy_threshold
            self.recognizer.dynamic_energy_threshold = self.config.dynamic_energy_threshold
            self.recognizer.pause_threshold = self.config.pause_threshold
            self.recognizer.phrase_threshold = self.config.phrase_threshold
            self.recognizer.non_speaking_duration = self.config.non_speaking_duration
            
            logger.info("✅ Распознаватель речи инициализирован")
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации распознавателя: {e}")
            self.state = SpeechState.ERROR
    
    async def start_recording(self) -> bool:
        """Начинает запись речи"""
        try:
            if self.state != SpeechState.IDLE:
                logger.warning(f"⚠️ Невозможно начать запись в состоянии {self.state.value}")
                return False
                
            self.state = SpeechState.RECORDING
            self.is_recording = True
            self.audio_chunks = []
            self.stop_event.clear()
            
            # Уведомляем о начале записи
            await self._notify_state_change(SpeechState.RECORDING)
            await self._notify_event(SpeechEventType.RECORDING_START)
            
            # Запускаем поток записи
            self.recording_thread = threading.Thread(
                target=self._run_recording,
                name="SpeechRecording",
                daemon=True
            )
            self.recording_thread.start()
            
            logger.info("🎤 Запись речи начата")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка начала записи: {e}")
            self.state = SpeechState.ERROR
            await self._notify_state_change(SpeechState.ERROR, error=str(e))
            return False
    
    async def stop_recording(self) -> str:
        """Останавливает запись и возвращает распознанный текст"""
        try:
            if self.state != SpeechState.RECORDING:
                logger.warning(f"⚠️ Невозможно остановить запись в состоянии {self.state.value}")
                return ""
                
            self.state = SpeechState.PROCESSING
            self.is_recording = False
            self.stop_event.set()
            
            # Уведомляем об остановке записи
            await self._notify_event(SpeechEventType.RECORDING_STOP)
            await self._notify_state_change(SpeechState.PROCESSING)
            
            # Ждем завершения потока записи
            if self.recording_thread and self.recording_thread.is_alive():
                self.recording_thread.join(timeout=5.0)
            
            # Распознаем текст
            text = await self._recognize_audio()
            
            self.state = SpeechState.IDLE
            await self._notify_state_change(SpeechState.IDLE)
            
            if text:
                await self._notify_event(SpeechEventType.TEXT_RECOGNIZED, text=text)
                logger.info(f"📝 Распознано: {text[:50]}...")
            else:
                logger.warning("⚠️ Текст не распознан")
                
            return text
            
        except Exception as e:
            logger.error(f"❌ Ошибка остановки записи: {e}")
            self.state = SpeechState.ERROR
            await self._notify_state_change(SpeechState.ERROR, error=str(e))
            return ""
    
    def _run_recording(self):
        """Запускает запись аудио"""
        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=self.dtype,
                blocksize=self.chunk_size,
                callback=self._audio_callback
            ) as stream:
                
                while self.is_recording and not self.stop_event.is_set():
                    time.sleep(0.1)
                    
        except Exception as e:
            logger.error(f"❌ Ошибка записи аудио: {e}")
            self.state = SpeechState.ERROR
    
    def _audio_callback(self, indata, frames, time, status):
        """Callback для записи аудио"""
        try:
            if status:
                logger.warning(f"⚠️ Статус аудио: {status}")
                
            if self.is_recording:
                with self.stream_lock:
                    self.audio_chunks.append(indata.copy())
                    
        except Exception as e:
            logger.error(f"❌ Ошибка в audio callback: {e}")
    
    async def _recognize_audio(self) -> str:
        """Распознает записанное аудио"""
        try:
            if not self.audio_chunks:
                logger.warning("⚠️ Нет аудио данных для распознавания")
                return ""
                
            # Объединяем аудио чанки
            with self.stream_lock:
                audio_data = np.concatenate(self.audio_chunks, axis=0)
                
            # Конвертируем в формат для распознавания
            if self.channels > 1:
                audio_data = np.mean(audio_data, axis=1)
                
            # Нормализуем аудио
            audio_data = audio_data.astype(np.float32) / np.iinfo(np.int16).max
            
            # Создаем AudioData для распознавания
            audio_bytes = (audio_data * 32767).astype(np.int16).tobytes()
            audio_data_obj = sr.AudioData(audio_bytes, self.sample_rate, 2)
            
            # Распознаем речь
            try:
                text = self.recognizer.recognize_google(audio_data_obj, language='ru-RU')
                return text
            except sr.UnknownValueError:
                logger.warning("⚠️ Речь не распознана")
                return ""
            except sr.RequestError as e:
                logger.error(f"❌ Ошибка сервиса распознавания: {e}")
                return ""
                
        except Exception as e:
            logger.error(f"❌ Ошибка распознавания аудио: {e}")
            return ""
    
    def register_callback(self, state: SpeechState, callback: Callable):
        """Регистрирует callback для состояния"""
        self.state_callbacks[state] = callback
        logger.debug(f"📝 Зарегистрирован callback для состояния {state.value}")
    
    def register_event_callback(self, event_type: SpeechEventType, callback: Callable):
        """Регистрирует callback для события"""
        self.event_callbacks[event_type] = callback
        logger.debug(f"📝 Зарегистрирован callback для события {event_type.value}")
    
    async def _notify_state_change(self, state: SpeechState, **kwargs):
        """Уведомляет об изменении состояния"""
        try:
            callback = self.state_callbacks.get(state)
            if callback:
                event = SpeechEvent(
                    event_type=SpeechEventType.STATE_CHANGED,
                    state=state,
                    timestamp=time.time(),
                    **kwargs
                )
                await callback(event)
        except Exception as e:
            logger.error(f"❌ Ошибка уведомления о смене состояния: {e}")
    
    async def _notify_event(self, event_type: SpeechEventType, **kwargs):
        """Уведомляет о событии"""
        try:
            callback = self.event_callbacks.get(event_type)
            if callback:
                event = SpeechEvent(
                    event_type=event_type,
                    state=self.state,
                    timestamp=time.time(),
                    **kwargs
                )
                await callback(event)
        except Exception as e:
            logger.error(f"❌ Ошибка уведомления о событии: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Возвращает статус распознавания речи"""
        return {
            "state": self.state.value,
            "is_recording": self.is_recording,
            "audio_chunks_count": len(self.audio_chunks),
            "config": {
                "sample_rate": self.sample_rate,
                "chunk_size": self.chunk_size,
                "channels": self.channels,
            },
            "callbacks_registered": len(self.state_callbacks) + len(self.event_callbacks)
        }
