"""
Sequential Speech Player - Основной плеер для последовательного воспроизведения

ОСНОВНЫЕ ПРИНЦИПЫ:
1. Последовательное воспроизведение - один чанк за раз
2. Без лимитов размера - накопление всех данных
3. Thread-safety - безопасная работа в многопоточной среде
4. macOS совместимость - для PKG упаковки
5. Простота и надежность - минимальная сложность
"""

import logging
import threading
import time
import asyncio
import sounddevice as sd
import numpy as np
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass

from .state import StateManager, PlaybackState, ChunkState
from .buffer import ChunkBuffer, ChunkInfo
from ..utils.audio_utils import resample_audio, convert_channels
from ..utils.device_utils import get_best_audio_device
from ..macos.core_audio import CoreAudioManager
from ..macos.performance import PerformanceMonitor

# ЦЕНТРАЛИЗОВАННАЯ КОНФИГУРАЦИЯ АУДИО
from config.unified_config_loader import unified_config

logger = logging.getLogger(__name__)

@dataclass
class PlayerConfig:
    """
    Конфигурация плеера
    
    ВАЖНО: Используйте from_centralized_config() для загрузки из unified_config.yaml
    Хардкод значения ниже - только fallback на случай ошибки загрузки конфигурации.
    """
    sample_rate: int = 48000  # Fallback - загружается из централизованной конфигурации
    channels: int = 1         # Fallback - загружается из централизованной конфигурации
    dtype: str = 'int16'      # Fallback - загружается из централизованной конфигурации
    buffer_size: int = 512    # Fallback - загружается из централизованной конфигурации
    max_memory_mb: int = 1024 # Fallback - загружается из централизованной конфигурации
    device_id: Optional[int] = None
    auto_device_selection: bool = True
    
    @classmethod
    def from_centralized_config(cls) -> 'PlayerConfig':
        """
        Создать PlayerConfig из централизованной конфигурации
        
        Returns:
            PlayerConfig: Конфигурация из unified_config.yaml
        """
        try:
            audio_config = unified_config.get_audio_config()
            config_dict = audio_config.get_speech_playback_config()
            
            return cls(
                sample_rate=config_dict['sample_rate'],
                channels=config_dict['channels'],
                dtype=config_dict['dtype'],
                buffer_size=config_dict['buffer_size'],
                max_memory_mb=config_dict['max_memory_mb'],
                auto_device_selection=config_dict['auto_device_selection'],
                device_id=None  # Определяется автоматически
            )
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки централизованной конфигурации: {e}")
            logger.info("🔄 Используем конфигурацию по умолчанию")
            return cls()  # Fallback к defaults

class SequentialSpeechPlayer:
    """Плеер для последовательного воспроизведения речи"""
    
    def __init__(self, config: Optional[PlayerConfig] = None):
        """
        Инициализация плеера
        
        Args:
            config: Конфигурация плеера (если None, загружается из централизованной конфигурации)
        """
        # Используем централизованную конфигурацию по умолчанию
        if config is None:
            try:
                self.config = PlayerConfig.from_centralized_config()
                logger.info("✅ PlayerConfig загружен из централизованной конфигурации")
            except Exception as e:
                logger.warning(f"⚠️ Ошибка загрузки централизованной конфигурации: {e}")
                logger.info("🔄 Используем fallback конфигурацию")
                self.config = PlayerConfig()
        else:
            self.config = config
        self.state_manager = StateManager()
        # Выбираем dtype буфера под конфиг (унифицировано на int16)
        buf_dtype = np.int16 if str(self.config.dtype).lower() in ('int16', 'short') else np.int16  # Всегда int16
        self.chunk_buffer = ChunkBuffer(max_memory_mb=self.config.max_memory_mb, channels=self.config.channels, dtype=buf_dtype)
        
        # Потоки и синхронизация
        self._playback_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()  # Начинаем с разблокированной паузы
        
        # Аудио поток
        self._audio_stream: Optional[sd.OutputStream] = None
        self._stream_lock = threading.RLock()
        
        # macOS компоненты
        self._core_audio_manager = CoreAudioManager()
        self._performance_monitor = PerformanceMonitor()
        
        # Callbacks
        self._on_chunk_started: Optional[Callable[[ChunkInfo], None]] = None
        self._on_chunk_completed: Optional[Callable[[ChunkInfo], None]] = None
        self._on_playback_completed: Optional[Callable[[], None]] = None
        self._on_error: Optional[Callable[[Exception], None]] = None
        
        logger.info("🔧 SequentialSpeechPlayer инициализирован")
    
    def initialize(self) -> bool:
        """Инициализация плеера"""
        try:
            # Инициализация macOS компонентов
            if not self._core_audio_manager.initialize():
                logger.error("❌ Ошибка инициализации Core Audio")
                return False
            
            # Выбор аудио устройства
            if self.config.auto_device_selection:
                device = get_best_audio_device()
                if device:
                    self.config.device_id = device.portaudio_index
                    # Определяем целевое число каналов по устройству (1..2)
                    target_channels = 1 if device.channels <= 1 else 2
                    if target_channels != self.config.channels:
                        self.config.channels = target_channels
                    # Синхронизируем буфер под новое число каналов
                    try:
                        self.chunk_buffer.set_channels(self.config.channels)
                    except Exception:
                        pass
                    logger.info(f"🎵 Выбрано устройство: {device.name} (channels: {device.channels}, sample_rate: {device.sample_rate})")
                else:
                    logger.warning("⚠️ Не удалось выбрать аудио устройство")
            
            # Логируем конфигурацию плеера для отладки
            logger.info(f"🎵 Конфигурация плеера: sample_rate={self.config.sample_rate}Hz, channels={self.config.channels}, dtype={self.config.dtype}")
            
            # Инициализация мониторинга производительности
            self._performance_monitor.start()
            
            logger.info("✅ Плеер инициализирован успешно")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации плеера: {e}")
            self.state_manager.set_state(PlaybackState.ERROR)
            return False
    
    def add_audio_data(self, audio_data: np.ndarray, priority: int = 0, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Добавить аудио данные для воспроизведения
        
        Args:
            audio_data: Аудио данные
            priority: Приоритет чанка
            metadata: Дополнительные метаданные
            
        Returns:
            ID чанка
        """
        try:
            # Нормализация формата на уровне плеера
            # 1) Ресемплинг при наличии источника sample_rate в metadata
            try:
                src_sr = None
                if isinstance(metadata, dict):
                    src_sr = metadata.get('sample_rate')
                if src_sr and int(src_sr) != int(self.config.sample_rate):
                    # Убедимся, что аудио 2D [samples, channels]
                    arr = audio_data
                    if arr.ndim == 1:
                        arr = arr.reshape(-1, 1)
                    audio_data = resample_audio(arr, target_sample_rate=int(self.config.sample_rate), original_sample_rate=int(src_sr))
            except Exception:
                pass

            # Конвертация каналов под целевые (1..2) и приведение к 2D
            # 2) Приведение числа каналов
            try:
                # Попытаемся учесть источники каналов из metadata для корректной конверсии
                converted = convert_channels(audio_data, self.config.channels)
            except Exception:
                converted = audio_data
            # Убеждаемся, что на выходе 2D [frames, channels]
            if converted.ndim == 1:
                if self.config.channels == 1:
                    converted = converted.reshape(-1, 1)
                else:
                    converted = np.column_stack([converted, converted])
            elif converted.ndim > 2:
                converted = converted.reshape(converted.shape[0], -1)

            # Приводим dtype к конфигу (унифицировано на int16)
            try:
                if str(self.config.dtype).lower() in ('int16', 'short'):
                    # Внутренний вывод — int16
                    if converted.dtype == np.float32 or converted.dtype == np.float64:
                        audio_data = np.clip(converted, -1.0, 1.0)
                        audio_data = (audio_data * 32767.0).astype(np.int16)
                    elif converted.dtype != np.int16:
                        audio_data = converted.astype(np.int16)
                    else:
                        audio_data = converted
                else:
                    # Fallback — всё равно приводим к int16 для sd.OutputStream
                    if converted.dtype == np.float32 or converted.dtype == np.float64:
                        audio_data = np.clip(converted, -1.0, 1.0)
                        audio_data = (audio_data * 32767.0).astype(np.int16)
                    else:
                        audio_data = converted.astype(np.int16)
            except Exception:
                audio_data = converted
            
            # Добавляем в буфер
            chunk_id = self.chunk_buffer.add_chunk(audio_data, priority, metadata)
            
            logger.info(f"✅ Аудио данные добавлены: {chunk_id} (size: {len(audio_data)})")
            
            return chunk_id
            
        except Exception as e:
            logger.error(f"❌ Ошибка добавления аудио данных: {e}")
            self.state_manager.set_state(PlaybackState.ERROR)
            raise
    
    def start_playback(self) -> bool:
        """Запуск воспроизведения"""
        try:
            # Проверяем, что можем запустить воспроизведение
            if self.state_manager.current_state not in [PlaybackState.IDLE, PlaybackState.PAUSED]:
                logger.warning("⚠️ Невозможно запустить воспроизведение в текущем состоянии")
                return False
            
            # Переходим в состояние PLAYING
            self.state_manager.set_state(PlaybackState.PLAYING)
            
            # НЕ очищаем данные - они уже добавлены в буфер
            
            # Запускаем аудио поток
            if not self._start_audio_stream():
                self.state_manager.set_state(PlaybackState.ERROR)
                return False
            
            # Запускаем поток воспроизведения
            self._stop_event.clear()
            self._pause_event.set()
            
            self._playback_thread = threading.Thread(target=self._playback_loop, daemon=True)
            self._playback_thread.start()
            
            logger.info("🎵 Воспроизведение запущено")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска воспроизведения: {e}")
            self.state_manager.set_state(PlaybackState.ERROR)
            return False
    
    def stop_playback(self) -> bool:
        """Остановка воспроизведения"""
        try:
            # Проверяем, что можем остановить воспроизведение
            if self.state_manager.current_state not in [PlaybackState.PLAYING, PlaybackState.PAUSED]:
                logger.warning("⚠️ Невозможно остановить воспроизведение в текущем состоянии")
                return False
            
            # Переходим в состояние STOPPING
            self.state_manager.set_state(PlaybackState.STOPPING)
            
            # Останавливаем поток воспроизведения
            self._stop_event.set()
            
            # Ждем завершения потока
            if self._playback_thread and self._playback_thread.is_alive():
                self._playback_thread.join(timeout=5.0)
            
            # Останавливаем аудио поток
            self._stop_audio_stream()
            
            # Очищаем буферы
            self.chunk_buffer.clear_all()
            
            # Переходим в состояние STOPPED
            self.state_manager.set_state(PlaybackState.IDLE)
            
            logger.info("🛑 Воспроизведение остановлено")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка остановки воспроизведения: {e}")
            self.state_manager.set_state(PlaybackState.ERROR)
            return False
    
    def pause_playback(self) -> bool:
        """Приостановка воспроизведения"""
        try:
            # Проверяем, что можем поставить на паузу
            if self.state_manager.current_state != PlaybackState.PLAYING:
                logger.warning("⚠️ Невозможно приостановить воспроизведение в текущем состоянии")
                return False
            
            self._pause_event.clear()
            self.state_manager.set_state(PlaybackState.PAUSED)
            
            logger.info("⏸️ Воспроизведение приостановлено")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка приостановки воспроизведения: {e}")
            self.state_manager.set_state(PlaybackState.ERROR)
            return False
    
    def resume_playback(self) -> bool:
        """Возобновление воспроизведения"""
        try:
            # Проверяем, что можем возобновить воспроизведение
            if self.state_manager.current_state != PlaybackState.PAUSED:
                logger.warning("⚠️ Невозможно возобновить воспроизведение в текущем состоянии")
                return False
            
            self._pause_event.set()
            self.state_manager.set_state(PlaybackState.PLAYING)
            
            logger.info("▶️ Воспроизведение возобновлено")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка возобновления воспроизведения: {e}")
            self.state_manager.set_state(PlaybackState.ERROR)
            return False
    
    def _start_audio_stream(self) -> bool:
        """Запуск аудио потока"""
        try:
            with self._stream_lock:
                if self._audio_stream is not None:
                    logger.warning("⚠️ Аудио поток уже запущен")
                    return True
                
                # Конфигурация потока
                stream_config = {
                    'device': self.config.device_id,
                    'channels': self.config.channels,
                    'dtype': self.config.dtype,
                    'samplerate': self.config.sample_rate,
                    'blocksize': self.config.buffer_size,
                    'callback': self._audio_callback
                }
                
                # Создаем поток
                self._audio_stream = sd.OutputStream(**stream_config)
                self._audio_stream.start()
                
                logger.info(f"🎵 Аудио поток запущен (device: {self.config.device_id}, channels: {self.config.channels})")
                return True
                
        except Exception as e:
            logger.error(f"❌ Ошибка запуска аудио потока: {e}")
            return False
    
    def _stop_audio_stream(self):
        """Остановка аудио потока"""
        try:
            with self._stream_lock:
                if self._audio_stream is not None:
                    self._audio_stream.stop()
                    self._audio_stream.close()
                    self._audio_stream = None
                    logger.info("🛑 Аудио поток остановлен")
                    
        except Exception as e:
            logger.error(f"❌ Ошибка остановки аудио потока: {e}")
    
    def _audio_callback(self, outdata, frames, time, status):
        """Callback для воспроизведения аудио"""
        try:
            if status:
                logger.warning(f"⚠️ Статус аудио потока: {status}")

            # Получаем данные из буфера (2D: frames x channels)
            data = self.chunk_buffer.get_playback_data(frames)
            
            # Логируем для отладки (только первые несколько вызовов)
            if not hasattr(self, '_callback_debug_count'):
                self._callback_debug_count = 0
            if self._callback_debug_count < 3:
                logger.debug(f"🎵 Audio callback: frames={frames}, data_shape={data.shape if len(data) > 0 else 'empty'}, target_channels={self.config.channels}")
                self._callback_debug_count += 1
            
            # Формируем выходные данные (ожидаем 2D)
            if len(data) == 0:
                outdata[:] = 0
            else:
                copy_ch = min(self.config.channels, data.shape[1])
                out_frames = min(frames, data.shape[0])
                outdata[:out_frames, :copy_ch] = data[:out_frames, :copy_ch]
                if out_frames < frames:
                    outdata[out_frames:, :] = 0
                
        except Exception as e:
            logger.error(f"❌ Ошибка в audio callback: {e}")
            outdata[:] = 0

    def reconfigure_channels(self, new_channels: int) -> bool:
        """Безопасно переинициализировать аудиовывод под новое число каналов (1..2)"""
        try:
            new_ch = 1 if new_channels <= 1 else 2
            if new_ch == self.config.channels:
                return True
            # Останавливаем текущий поток
            self._stop_audio_stream()
            # Обновляем конфиг и буфер
            self.config.channels = new_ch
            try:
                self.chunk_buffer.set_channels(new_ch)
            except Exception:
                pass
            # Запускаем заново если были в состоянии PLAYING
            if self.state_manager.is_playing or self.state_manager.is_paused:
                return self._start_audio_stream()
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка reconfigure_channels: {e}")
            return False
    
    def _playback_loop(self):
        """Основной цикл воспроизведения - упрощенная версия"""
        try:
            logger.info("🔄 Playback loop запущен")
            
            while not self._stop_event.is_set():
                # Проверяем паузу
                self._pause_event.wait()
                
                # Получаем следующий чанк
                chunk_info = self.chunk_buffer.get_next_chunk(timeout=0.1)
                
                if chunk_info is not None:
                    # Отмечаем начало обработки
                    chunk_info.state = ChunkState.PLAYING
                    
                    # Callback начала чанка
                    if self._on_chunk_started:
                        self._on_chunk_started(chunk_info)
                    
                    # Добавляем в буфер воспроизведения
                    if not self.chunk_buffer.add_to_playback_buffer(chunk_info):
                        logger.error(f"❌ Ошибка добавления чанка {chunk_info.id} в буфер воспроизведения")
                        chunk_info.state = ChunkState.ERROR
                        continue
                    
                    # Ждем завершения воспроизведения этого чанка
                    self._wait_for_chunk_completion(chunk_info)
                    
                    # Отмечаем завершение
                    self.chunk_buffer.mark_chunk_completed(chunk_info)
                    
                    # Callback завершения чанка
                    if self._on_chunk_completed:
                        self._on_chunk_completed(chunk_info)
                    
                    logger.info(f"✅ Чанк обработан: {chunk_info.id}")
                else:
                    # Нет чанков - небольшая задержка
                    time.sleep(0.01)
            
            logger.info("🔄 Playback loop завершен")
            # Устанавливаем состояние IDLE после естественного завершения
            try:
                self.state_manager.set_state(PlaybackState.IDLE)
            except Exception:
                pass
            # Коллбек завершения воспроизведения (если задан)
            try:
                if self._on_playback_completed:
                    self._on_playback_completed()
            except Exception:
                pass
            
        except Exception as e:
            logger.error(f"❌ Ошибка в playback loop: {e}")
            self.state_manager.set_state(PlaybackState.ERROR)
    
    def _wait_for_chunk_completion(self, chunk_info: ChunkInfo, timeout: float = 30.0):
        """Ждать завершения воспроизведения чанка"""
        start_time = time.time()
        
        # Ожидаем, пока буфер воспроизведения не будет пустым
        # Это означает, что весь чанк был воспроизведен
        while time.time() - start_time < timeout:
            if not self.chunk_buffer.has_data:
                logger.info(f"✅ Чанк {chunk_info.id} полностью воспроизведен")
                return
            
            time.sleep(0.01)
        
        logger.warning(f"⚠️ Таймаут ожидания завершения чанка {chunk_info.id}")
    
    def wait_for_completion(self, timeout: float = None) -> bool:
        """Ждать завершения воспроизведения всех чанков (без таймаута)"""
        return self.chunk_buffer.wait_for_completion(timeout)
    
    def set_callbacks(self, 
                     on_chunk_started: Optional[Callable[[ChunkInfo], None]] = None,
                     on_chunk_completed: Optional[Callable[[ChunkInfo], None]] = None,
                     on_playback_completed: Optional[Callable[[], None]] = None,
                     on_error: Optional[Callable[[Exception], None]] = None):
        """Установить callbacks"""
        self._on_chunk_started = on_chunk_started
        self._on_chunk_completed = on_chunk_completed
        self._on_playback_completed = on_playback_completed
        self._on_error = on_error
    
    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику плеера"""
        return {
            'state': self.state_manager.current_state.value,
            'is_playing': self.state_manager.is_playing,
            'is_paused': self.state_manager.is_paused,
            'has_error': self.state_manager.has_error,
            'buffer_stats': self.chunk_buffer.get_stats(),
            'performance_stats': self._performance_monitor.get_stats()
        }
    
    def shutdown(self):
        """Завершение работы плеера"""
        try:
            # Останавливаем воспроизведение
            self.stop_playback()
            
            # Останавливаем мониторинг производительности
            self._performance_monitor.stop()
            
            # Очищаем буферы
            self.chunk_buffer.clear_all()
            
            logger.info("🛑 Плеер завершил работу")
            
        except Exception as e:
            logger.error(f"❌ Ошибка завершения работы плеера: {e}")












































    def get_status(self) -> Dict[str, Any]:
        """
        Получает статус плеера
        
        Returns:
            Dict с информацией о статусе
        """
        return {
            "state": self.state_manager.current_state.value,
            "chunk_count": self.chunk_buffer.queue_size,
            "buffer_size": self.chunk_buffer.buffer_size,
            "is_playing": self.state_manager.current_state == PlaybackState.PLAYING,
            "is_paused": self.state_manager.current_state == PlaybackState.PAUSED,
            "device_id": self.config.device_id,
            "sample_rate": self.config.sample_rate,
            "channels": self.config.channels
        }
