"""
Основной класс распознавания речи с использованием SpeechRecognition
"""

import asyncio
import logging
import time
import threading
from typing import Optional, Callable, Dict, Any, List
import sounddevice as sd
import numpy as np
import speech_recognition as sr

from .types import (
    RecognitionConfig, RecognitionResult, RecognitionState, 
    RecognitionEventType, RecognitionMetrics
)

logger = logging.getLogger(__name__)

class SpeechRecognizer:
    """Основной класс распознавания речи"""
    
    def __init__(self, config: RecognitionConfig):
        self.config = config
        self.state = RecognitionState.IDLE
        
        # Аудио данные
        self.audio_data = []
        self.is_listening = False
        self.listen_start_time = None
        
        # Threading
        self.listen_thread = None
        self.stop_event = threading.Event()
        self.audio_lock = threading.Lock()
        
        # Callbacks
        self.state_callbacks: Dict[RecognitionState, Callable] = {}
        self.event_callbacks: Dict[RecognitionEventType, Callable] = {}
        
        # Метрики
        self.metrics = RecognitionMetrics()

        # Параметры входного устройства
        self.input_device_index: Optional[int] = None
        self.actual_input_rate: int = self.config.sample_rate
        
        # Инициализируем распознаватель
        self._init_recognizer()
        
    def _init_recognizer(self):
        """Инициализирует распознаватель речи"""
        try:
            self.recognizer = sr.Recognizer()
            self.microphone = sr.Microphone()
            
            # Настраиваем параметры
            self.recognizer.energy_threshold = self.config.energy_threshold
            self.recognizer.dynamic_energy_threshold = self.config.dynamic_energy_threshold
            self.recognizer.pause_threshold = self.config.pause_threshold
            self.recognizer.phrase_threshold = self.config.phrase_threshold
            self.recognizer.non_speaking_duration = self.config.non_speaking_duration
            
            # Настраиваем микрофон для фонового шума (БЕЗ БЛОКИРОВКИ)
            try:
                with self.microphone as source:
                    logger.info("🔧 Настраиваем микрофон для фонового шума...")
                    self.recognizer.adjust_for_ambient_noise(source, duration=1)
                    logger.info(f"📊 Энергетический порог установлен: {self.recognizer.energy_threshold}")
            except Exception as mic_error:
                # НЕ блокируем приложение - используем значения по умолчанию
                logger.warning(f"⚠️ Не удалось настроить микрофон (используем значения по умолчанию): {mic_error}")
                self.recognizer.energy_threshold = 300  # Значение по умолчанию
            
            logger.info(f"✅ Распознаватель речи инициализирован (язык: {self.config.language})")
            
        except Exception as e:
            logger.warning(f"⚠️ Ошибка инициализации распознавателя (продолжаем работу): {e}")
            # НЕ устанавливаем ERROR - позволяем работать в degraded режиме
            self.state = RecognitionState.IDLE
            
    def _pick_input_device(self) -> Optional[int]:
        """Подбирает стабильное входное устройство. Предпочтение: встроенный микрофон."""
        try:
            devices = sd.query_devices()
            # Популярные названия встроенного микрофона на macOS
            builtin_keywords = [
                'built-in microphone', 'macbook', 'internal microphone',
                'microphone (built-in)', 'default - built-in'
            ]
            # Ищем по имени
            for i, d in enumerate(devices):
                name = str(d.get('name', '')).lower()
                if d.get('max_input_channels', 0) > 0 and any(k in name for k in builtin_keywords):
                    return i
            # Если не нашли — берем девайс с наибольшим числом входных каналов, избегая bluetooth-headset
            candidates = []
            for i, d in enumerate(devices):
                ch = d.get('max_input_channels', 0)
                if ch > 0:
                    name = str(d.get('name', '')).lower()
                    is_bt_headset = ('airpods' in name) or ('headset' in name) or ('hands-free' in name)
                    candidates.append((i, ch, 0 if is_bt_headset else 1))
            if candidates:
                # Сортируем: non-bt приоритетнее, затем по каналам
                candidates.sort(key=lambda x: (x[2], x[1]), reverse=True)
                return candidates[0][0]
        except Exception:
            pass
        return None

    async def start_listening(self) -> bool:
        """Начинает прослушивание микрофона"""
        try:
            if self.state != RecognitionState.IDLE:
                logger.warning(f"⚠️ Невозможно начать прослушивание в состоянии {self.state.value}")
                return False
                
            self.state = RecognitionState.LISTENING
            self.is_listening = True
            self.audio_data = []
            self.stop_event.clear()
            
            # Уведомляем о начале прослушивания
            await self._notify_state_change(RecognitionState.LISTENING)
            await self._notify_event(RecognitionEventType.LISTENING_START)
            
            # Запускаем поток прослушивания
            self.listen_thread = threading.Thread(
                target=self._run_listening,
                name="SpeechListening",
                daemon=True
            )
            self.listen_thread.start()
            
            logger.info("🎤 Прослушивание микрофона начато")
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ Ошибка начала прослушивания (продолжаем работу): {e}")
            # НЕ устанавливаем ERROR - возвращаемся в IDLE для повторных попыток
            self.state = RecognitionState.IDLE
            await self._notify_state_change(RecognitionState.IDLE, error=str(e))
            return False
            
    async def stop_listening(self) -> RecognitionResult:
        """Останавливает прослушивание и возвращает результат распознавания"""
        try:
            if self.state != RecognitionState.LISTENING:
                logger.warning(f"⚠️ Невозможно остановить прослушивание в состоянии {self.state.value}")
                return RecognitionResult(text="", error="Not listening")
                
            self.state = RecognitionState.PROCESSING
            self.is_listening = False
            self.stop_event.set()
            
            # Уведомляем об остановке прослушивания
            await self._notify_event(RecognitionEventType.LISTENING_STOP)
            await self._notify_state_change(RecognitionState.PROCESSING)
            
            # Ждем завершения потока прослушивания
            if self.listen_thread and self.listen_thread.is_alive():
                self.listen_thread.join(timeout=5.0)
            
            # Распознаем речь
            result = await self._recognize_audio()
            
            # Обновляем метрики
            self._update_metrics(result)
            
            self.state = RecognitionState.IDLE
            await self._notify_state_change(RecognitionState.IDLE)
            
            if result.text:
                logger.info(f"📝 Распознано: {result.text}")
            else:
                logger.warning("⚠️ Речь не распознана")
                
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка остановки прослушивания: {e}")
            self.state = RecognitionState.ERROR
            await self._notify_state_change(RecognitionState.ERROR, error=str(e))
            return RecognitionResult(text="", error=str(e))
            
    def _run_listening(self):
        """Запускает прослушивание микрофона"""
        try:
            # Подбираем устройство
            self.input_device_index = self._pick_input_device()
            device_param = self.input_device_index if self.input_device_index is not None else None
            # Пробуем с желаемой частотой
            try:
                self.actual_input_rate = self.config.sample_rate
                stream = sd.InputStream(
                    device=device_param,
                    samplerate=self.config.sample_rate,
                    channels=self.config.channels,
                    dtype=self.config.dtype,
                    blocksize=self.config.chunk_size,
                    callback=self._audio_callback
                )
                stream.start()
            except Exception as e1:
                logger.warning(f"⚠️ Не удалось открыть InputStream с {self.config.sample_rate} Hz: {e1}")
                # Пробуем с дефолтной частотой устройства
                try:
                    if device_param is not None:
                        dev_info = sd.query_devices(device_param)
                    else:
                        dev_info = sd.query_devices(None, 'input')
                    fallback_rate = int(dev_info.get('default_samplerate') or 16000)
                    self.actual_input_rate = fallback_rate
                    stream = sd.InputStream(
                        device=device_param,
                        samplerate=fallback_rate,
                        channels=self.config.channels,
                        dtype=self.config.dtype,
                        blocksize=self.config.chunk_size,
                        callback=self._audio_callback
                    )
                    stream.start()
                except Exception as e2:
                    logger.error(f"❌ Ошибка открытия InputStream даже с дефолтной частотой: {e2}")
                    self.state = RecognitionState.ERROR
                    return

            with stream:
                self.listen_start_time = time.time()
                
                while self.is_listening and not self.stop_event.is_set():
                    time.sleep(0.1)
                    
        except Exception as e:
            logger.error(f"❌ Ошибка прослушивания микрофона: {e}")
            self.state = RecognitionState.ERROR
            
    def _audio_callback(self, indata, frames, time, status):
        """Callback для записи аудио"""
        try:
            if status:
                logger.warning(f"⚠️ Статус аудио: {status}")
                
            if self.is_listening:
                with self.audio_lock:
                    self.audio_data.append(indata.copy())
                    
        except Exception as e:
            logger.error(f"❌ Ошибка в audio callback: {e}")
            
    async def _recognize_audio(self) -> RecognitionResult:
        """Распознает записанное аудио"""
        try:
            if not self.audio_data:
                logger.warning("⚠️ Нет аудио данных для распознавания")
                return RecognitionResult(text="", error="No audio data")
                
            # Объединяем аудио чанки
            with self.audio_lock:
                audio_data = np.concatenate(self.audio_data, axis=0)
                
            # Конвертируем в формат для распознавания
            if self.config.channels > 1:
                audio_data = np.mean(audio_data, axis=1)
                
            # Если запись велась не на той частоте, приводим к целевой
            try:
                if self.actual_input_rate != self.config.sample_rate:
                    from modules.voice_recognition.utils.audio_utils import resample_audio
                    audio_data = resample_audio(audio_data, self.actual_input_rate, self.config.sample_rate)
            except Exception as re:
                logger.debug(f"Resample skipped: {re}")

            # Нормализуем аудио
            audio_data = audio_data.astype(np.float32) / np.iinfo(np.int16).max
            
            # Создаем AudioData для распознавания
            audio_bytes = (audio_data * 32767).astype(np.int16).tobytes()
            audio_data_obj = sr.AudioData(audio_bytes, self.config.sample_rate, 2)
            
            # Распознаем речь
            start_time = time.time()
            await self._notify_event(RecognitionEventType.RECOGNITION_START)
            
            try:
                text = await self._recognize_with_engine(audio_data_obj)
                duration = time.time() - start_time
                
                result = RecognitionResult(
                    text=text,
                    confidence=None,  # SpeechRecognition не всегда предоставляет confidence
                    language=self.config.language,
                    duration=duration,
                    timestamp=time.time()
                )
                
                await self._notify_event(RecognitionEventType.RECOGNITION_COMPLETE, result=result)
                return result
                
            except sr.UnknownValueError:
                logger.warning("⚠️ Речь не распознана")
                return RecognitionResult(text="", error="Speech not recognized")
            except sr.RequestError as e:
                logger.error(f"❌ Ошибка сервиса распознавания: {e}")
                return RecognitionResult(text="", error=str(e))
                
        except Exception as e:
            logger.error(f"❌ Ошибка распознавания аудио: {e}")
            return RecognitionResult(text="", error=str(e))
            
    async def _recognize_with_engine(self, audio_data: sr.AudioData) -> str:
        """Распознает аудио с помощью Google Speech Recognition"""
        try:
            return self.recognizer.recognize_google(audio_data, language=self.config.language)
                
        except Exception as e:
            logger.error(f"❌ Ошибка распознавания с Google Speech Recognition: {e}")
            raise
            
    def _update_metrics(self, result: RecognitionResult):
        """Обновляет метрики распознавания"""
        self.metrics.total_recognitions += 1
        
        if result.text and not result.error:
            self.metrics.successful_recognitions += 1
            self.metrics.recognitions_by_language[result.language] = (
                self.metrics.recognitions_by_language.get(result.language, 0) + 1
            )
            
            if result.confidence:
                # Обновляем среднюю уверенность
                if self.metrics.successful_recognitions > 0:
                    self.metrics.average_confidence = (
                        (self.metrics.average_confidence * (self.metrics.successful_recognitions - 1) + result.confidence) 
                        / self.metrics.successful_recognitions
                    )
        else:
            self.metrics.failed_recognitions += 1
            
                
    def register_callback(self, state: RecognitionState, callback: Callable):
        """Регистрирует callback для состояния"""
        self.state_callbacks[state] = callback
        logger.debug(f"📝 Зарегистрирован callback для состояния {state.value}")
        
    def register_event_callback(self, event_type: RecognitionEventType, callback: Callable):
        """Регистрирует callback для события"""
        self.event_callbacks[event_type] = callback
        logger.debug(f"📝 Зарегистрирован callback для события {event_type.value}")
        
    async def _notify_state_change(self, state: RecognitionState, **kwargs):
        """Уведомляет об изменении состояния"""
        try:
            callback = self.state_callbacks.get(state)
            if callback:
                from .types import RecognitionEvent
                event = RecognitionEvent(
                    event_type=RecognitionEventType.LISTENING_START,  # Базовое событие
                    state=state,
                    timestamp=time.time(),
                    **kwargs
                )
                await callback(event)
        except Exception as e:
            logger.error(f"❌ Ошибка уведомления о смене состояния: {e}")
            
    async def _notify_event(self, event_type: RecognitionEventType, **kwargs):
        """Уведомляет о событии"""
        try:
            callback = self.event_callbacks.get(event_type)
            if callback:
                from .types import RecognitionEvent
                event = RecognitionEvent(
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
            "is_listening": self.is_listening,
            "audio_data_chunks": len(self.audio_data),
            "config": {
                "language": self.config.language,
                "sample_rate": self.config.sample_rate,
                "chunk_size": self.config.chunk_size,
                "channels": self.config.channels,
            },
            "metrics": {
                "total_recognitions": self.metrics.total_recognitions,
                "successful_recognitions": self.metrics.successful_recognitions,
                "failed_recognitions": self.metrics.failed_recognitions,
                "success_rate": (
                    self.metrics.successful_recognitions / max(self.metrics.total_recognitions, 1) * 100
                ),
                "average_confidence": self.metrics.average_confidence,
                "average_duration": self.metrics.average_duration,
            },
            "callbacks_registered": len(self.state_callbacks) + len(self.event_callbacks)
        }
        
    def get_metrics(self) -> RecognitionMetrics:
        """Возвращает метрики распознавания"""
        return self.metrics
