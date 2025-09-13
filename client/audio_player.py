"""
AudioPlayer - Аудио плеер с исправленными race conditions

ИСПРАВЛЕНИЯ:
1. Правильная синхронизация потоков
2. Устранение race conditions
3. Thread-safe операции
4. Правильная обработка состояний
5. Защита от deadlocks
"""

import asyncio
import sounddevice as sd
import numpy as np
import logging
import queue
import threading
import time
import gc
import psutil
import os
from typing import List, Optional, Dict, Callable
from dataclasses import dataclass
from enum import Enum
from utils.device_utils import is_headphones, is_virtual_device, get_device_type_keywords
from error_handler import (
    handle_audio_error, handle_device_error, handle_memory_error, 
    handle_threading_error, error_handler, ErrorSeverity, ErrorCategory
)
from simplified_audio_system import (
    get_universal_audio_config, simple_device_switch, auto_switch_on_device_change,
    handle_portaudio_error
)

logger = logging.getLogger(__name__)

class PlayerState(Enum):
    """Состояния аудио плеера"""
    STOPPED = "stopped"
    STARTING = "starting"
    PLAYING = "playing"
    PAUSED = "paused"
    STOPPING = "stopping"
    ERROR = "error"

@dataclass
class PlayerMetrics:
    """Метрики аудио плеера"""
    state: PlayerState
    is_playing: bool
    queue_size: int
    buffer_size: int
    stream_active: bool
    memory_usage: int
    errors_count: int
    last_activity: float

class ThreadSafeAudioPlayer:
    """
    Thread-safe аудио плеер с исправленными race conditions
    
    ИСПРАВЛЕНИЯ:
    1. Правильная синхронизация потоков
    2. Устранение race conditions
    3. Thread-safe операции
    4. Правильная обработка состояний
    5. Защита от deadlocks
    """
    
    def __init__(self, sample_rate=48000, channels=1, dtype='int16'):
        self.sample_rate = sample_rate
        self.channels = channels
        self.dtype = dtype
        
        # ОГРАНИЧЕНИЯ ДЛЯ ЗАЩИТЫ ОТ УТЕЧЕК ПАМЯТИ
        self.max_queue_size = 1000
        self.max_memory_usage = 512 * 1024 * 1024  # 512MB
        # УБРАНО: max_buffer_size - нет ограничений на размер буфера
        
        # Очередь с ограничением размера
        self.audio_queue = queue.Queue(maxsize=self.max_queue_size)
        
        # Thread-safe состояние
        self._state = PlayerState.STOPPED
        self._state_lock = threading.RLock()
        
        # Thread-safe флаги
        self._is_playing = False
        self._is_starting = False
        self._is_stopping = False
        self._is_shutting_down = False
        
        # Thread-safe события
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.pause_event.set()  # Начинаем в активном состоянии
        
        # Thread-safe потоки
        self.playback_thread = None
        self.stream = None
        
        # Thread-safe буферы
        self.internal_buffer = np.array([], dtype=np.int16)
        self.buffer_lock = threading.RLock()
        self.stream_lock = threading.RLock()
        
        # Thread-safe система управления аудио
        self.audio_manager = None
        self.current_device_info = None
        self._device_info_lock = threading.RLock()
        
        # Thread-safe кэширование
        self._cached_stream_config = None
        self._cached_device_info = None
        self._stream_cache_valid = False
        self._cache_lock = threading.RLock()
        
        # Thread-safe метрики
        self._metrics_lock = threading.RLock()
        self._errors_count = 0
        self._last_activity = time.time()
        
        # Мониторинг памяти
        self._memory_monitor = MemoryMonitor(self.max_memory_usage)
        
        # Callbacks
        self.state_callback: Optional[Callable] = None
        self.error_callback: Optional[Callable] = None
        
        # Инициализация
        self._init_audio_manager()
        
        logger.info("🎵 ThreadSafeAudioPlayer инициализирован")

    def _init_audio_manager(self):
        """Инициализирует систему управления аудио устройствами"""
        try:
            from simplified_audio_system import initialize_global_simplified_audio_system
            
            config = {
                'device_manager': {
                    'enabled': True,
                    'monitoring_interval': 3.0,
                    'switch_cooldown': 2.0,
                    'cache_timeout': 5.0,
                    'auto_switch_to_headphones': True,
                    'auto_switch_to_best': True,
                    'exclude_virtual_devices': True,
                    'virtual_device_keywords': ['blackhole', 'loopback', 'virtual']
                }
            }
            
            self.audio_manager = initialize_global_simplified_audio_system(config)
            
            if not self.audio_manager.initialize():
                raise Exception("Не удалось инициализировать SimplifiedAudioSystem")
            
            self.current_device_info = self.audio_manager.get_current_device()
            self.audio_manager.add_device_callback(self._on_device_change_callback)
            
            logger.info("✅ SimplifiedAudioSystem инициализирован")
            
        except Exception as e:
            handle_audio_error(e, "ThreadSafeAudioPlayer", "_init_audio_manager", "Инициализация аудио системы")
            self._handle_error(e)

    def _on_device_change_callback(self, event):
        """Обрабатывает изменения аудио устройств"""
        try:
            logger.info(f"🔔 Изменение устройства: {event.event_type} - {event.device.name}")
            
            if event.event_type == "device_switched":
                self._handle_device_switched(event.device)
            elif event.event_type == "device_added":
                self._handle_device_added(event.device)
            elif event.event_type == "device_removed":
                self._handle_device_removed(event.device)

        except Exception as e:
            handle_device_error(e, "ThreadSafeAudioPlayer", "_on_device_change_callback", "Обработка изменения устройства")
            self._handle_error(e)

    def _handle_device_switched(self, device):
        """Обрабатывает переключение устройства"""
        try:
            logger.info(f"🔄 Переключение на устройство: {device.name}")
            
            with self._device_info_lock:
                self.current_device_info = device
            
            # Перезапускаем поток, если он активен
            if self._is_playing:
                self._restart_stream()
                
        except Exception as e:
            logger.error(f"❌ Ошибка переключения на устройство: {e}")
            self._handle_error(e)

    def _handle_device_added(self, device):
        """Обрабатывает добавление устройства"""
        try:
            logger.info(f"➕ Устройство добавлено: {device.name}")
            
            if (device.is_output and 
                self._is_headphones(device)):
                
                logger.info(f"🎧 Автоматическое переключение на наушники: {device.name}")
                self.audio_manager.switch_to_device(device.name)
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки добавления устройства: {e}")
            self._handle_error(e)

    def _handle_device_removed(self, device):
        """Обрабатывает удаление устройства"""
        try:
            logger.info(f"➖ Устройство удалено: {device.name}")
            
            with self._device_info_lock:
                if (self.current_device_info and 
                    self.current_device_info.name == device.name):
                    
                    logger.info("🔄 Текущее устройство удалено, переключаемся на лучшее")
                    self.audio_manager.switch_to_best_device()
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки удаления устройства: {e}")
            self._handle_error(e)

    def _is_headphones(self, device):
        """Определяет, являются ли наушники"""
        headphone_types = [
            'airpods', 'beats', 'bluetooth_headphones', 'usb_headphones'
        ]
        return device.device_type.value in headphone_types

    def _restart_stream(self):
        """Перезапускает аудио поток"""
        try:
            logger.info("🔄 Перезапуск аудио потока...")
            
            self._stop_stream()
            time.sleep(0.1)
            self._start_stream()
            
            logger.info("✅ Аудио поток перезапущен")
                    
        except Exception as e:
            logger.error(f"❌ Ошибка перезапуска аудио потока: {e}")
            self._handle_error(e)

    def _start_stream(self):
        """Запускает аудио поток"""
        try:
            with self.stream_lock:
                if self.stream is not None:
                    logger.warning("⚠️ Поток уже запущен")
                    return
                    
                with self._device_info_lock:
                    current_device = self.current_device_info
                
                # Если устройство не подходит для выхода, принудительно выбираем лучшее
                if current_device and (not current_device.is_output or current_device.max_output_channels == 0):
                    logger.warning(f"⚠️ Текущее устройство {current_device.name} не подходит для выхода, выбираем лучшее")
                    if self.audio_manager:
                        # Принудительно выбираем лучшее выходное устройство
                        if self.audio_manager.force_select_best_output_device():
                            current_device = self.audio_manager.get_current_device()
                            logger.info(f"✅ Успешно переключились на лучшее устройство: {current_device.name if current_device else 'None'}")
                        else:
                            # Fallback: используем встроенную логику
                            self.audio_manager.switch_to_best_device()
                            current_device = self.audio_manager.get_current_device()
                
                if not current_device:
                    logger.warning("⚠️ Нет текущего устройства, пытаемся получить лучшее устройство")
                    if self.audio_manager:
                        self.audio_manager.switch_to_best_device()
                        current_device = self.audio_manager.get_current_device()
                    
                    if not current_device:
                        logger.error("❌ Нет доступных устройств для воспроизведения")
                        return
                
                # Создаем конфигурацию потока
                # Используем количество каналов, поддерживаемых устройством
                device_channels = self._get_optimal_channels_for_device(current_device)
                
                # Обновляем количество каналов плеера для соответствия устройству
                self.channels = device_channels
                
                # Логируем детальную информацию о выбранном устройстве
                logger.info(f"🔍 Выбранное устройство: {current_device.name}")
                logger.info(f"🔍 PortAudio индекс: {current_device.portaudio_index}")
                logger.info(f"🔍 Максимальные выходные каналы: {current_device.max_output_channels}")
                logger.info(f"🔍 Выбранные каналы: {device_channels}")
                logger.info(f"🔍 Приоритет устройства: {current_device.priority}")
                logger.info(f"🔍 Подключено: {current_device.is_connected}")
                
                # Получаем сводку всех устройств для отладки
                if self.audio_manager:
                    device_summary = self.audio_manager.get_device_info_summary()
                    logger.info(f"🔍 Всего устройств: {device_summary.get('total_devices', 0)}")
                    logger.info(f"🔍 Выходных устройств: {device_summary.get('output_devices', 0)}")
                    logger.info(f"🔍 Категории: {device_summary.get('categories', {})}")
                
                stream_config = {
                    'device': current_device.portaudio_index,
                    'channels': device_channels,
                    'dtype': self.dtype,
                    'samplerate': self.sample_rate
                }
                
                # Создаем и запускаем поток
                self.stream = sd.OutputStream(
                    callback=self._audio_callback,
                    **stream_config
                )
                
                self.stream.start()
                
                logger.info(f"🎵 Аудио поток запущен на устройстве: {current_device.name}")
            
        except Exception as e:
            handle_audio_error(e, "ThreadSafeAudioPlayer", "_start_stream", "Запуск аудио потока")
            self._handle_error(e)

    def _stop_stream(self):
        """Останавливает аудио поток"""
        try:
            with self.stream_lock:
                if self.stream is None:
                    return
                    
                self.stream.stop()
                self.stream.close()
                self.stream = None
                
                logger.info("🛑 Аудио поток остановлен")
                
        except Exception as e:
            handle_audio_error(e, "ThreadSafeAudioPlayer", "_stop_stream", "Остановка аудио потока")
            self._handle_error(e)

    def _audio_callback(self, outdata, frames, time, status):
        """Callback для воспроизведения аудио"""
        try:
            # ДИАГНОСТИКА: Логируем каждый вызов callback
            logger.info(f"🔍 Audio callback: frames={frames}, buffer_len={len(self.internal_buffer)}, channels={self.channels}")
            
            if status:
                logger.warning(f"⚠️ Статус аудио потока: {status}")
            
            # Проверяем использование памяти
            if self._memory_monitor.is_memory_high():
                logger.warning("⚠️ Высокое использование памяти, очищаем буферы")
                self._emergency_cleanup()
            
            # Получаем данные из буфера
            with self.buffer_lock:
                if len(self.internal_buffer) >= frames:
                    # ДИАГНОСТИКА: Логируем успешное воспроизведение
                    logger.info(f"✅ Audio callback: воспроизводим {frames} сэмплов")
                    
                    # Адаптируем данные под количество каналов устройства
                    if self.channels == 1:
                        # Моно: reshape(-1, 1)
                        outdata[:] = self.internal_buffer[:frames].reshape(-1, 1)
                    else:
                        # Стерео: дублируем моно данные для обоих каналов
                        mono_data = self.internal_buffer[:frames]
                        stereo_data = np.column_stack([mono_data, mono_data])
                        outdata[:] = stereo_data
                    self.internal_buffer = self.internal_buffer[frames:]
                else:
                    # ДИАГНОСТИКА: Логируем пустой буфер
                    logger.warning(f"⚠️ Audio callback: пустой буфер! buffer={len(self.internal_buffer)}, нужно={frames}")
                    outdata[:] = np.zeros((frames, self.channels), dtype=self.dtype)
            
        except Exception as e:
            handle_audio_error(e, "ThreadSafeAudioPlayer", "_audio_callback", "Audio callback")
            self._handle_error(e)
            outdata[:] = np.zeros((frames, self.channels), dtype=self.dtype)

    def _emergency_cleanup(self):
        """Экстренная очистка при высоком использовании памяти"""
        try:
            logger.warning("🚨 Экстренная очистка памяти...")
            
            self._clear_queue()
            
            with self.buffer_lock:
                            self.internal_buffer = np.array([], dtype=np.int16)
            
            gc.collect()
            
            logger.info("✅ Экстренная очистка завершена")
            
        except Exception as e:
            handle_memory_error(e, "ThreadSafeAudioPlayer", "_emergency_cleanup", "Экстренная очистка")

    def _clear_queue(self):
        """Очищает очередь аудио данных"""
        try:
            while not self.audio_queue.empty():
                try:
                    self.audio_queue.get_nowait()
                except queue.Empty:
                    break
        except Exception as e:
            handle_memory_error(e, "ThreadSafeAudioPlayer", "_clear_queue", "Очистка очереди")

    def _clear_buffer(self):
        """Очищает внутренний буфер"""
        try:
            with self.buffer_lock:
                self.internal_buffer = np.array([], dtype=np.int16)
        except Exception as e:
            handle_memory_error(e, "ThreadSafeAudioPlayer", "_clear_buffer", "Очистка буфера")

    def start_playback(self) -> bool:
        """Запускает воспроизведение с защитой от race conditions"""
        try:
            with self._state_lock:
                if self._is_playing:
                    logger.warning("⚠️ Воспроизведение уже запущено")
                    return False
                
                if self._is_starting:
                    logger.warning("⚠️ Воспроизведение уже запускается")
                    return False
                
                if self._is_stopping:
                    logger.warning("⚠️ Воспроизведение останавливается")
                    return False
                
                self._is_starting = True
                self._set_state(PlayerState.STARTING)
                
                try:
                    # Очищаем данные перед запуском
                    self._clear_queue()
                    self._clear_buffer()
                    
                    # Запускаем поток
                    self._start_stream()
                    
                    # Запускаем поток воспроизведения
                    self.stop_event.clear()
                    self.pause_event.set()
                    
                    self.playback_thread = threading.Thread(target=self._playback_loop, daemon=True)
                    self.playback_thread.start()
                    
                    self._is_playing = True
                    self._set_state(PlayerState.PLAYING)
                    
                    logger.info("🎵 Воспроизведение запущено")
                    return True
                    
                finally:
                    self._is_starting = False
                    
        except Exception as e:
            handle_audio_error(e, "ThreadSafeAudioPlayer", "start_playback", "Запуск воспроизведения")
            self._handle_error(e)
            self._is_starting = False
            return False

    def stop_playback(self) -> bool:
        """Останавливает воспроизведение с защитой от race conditions"""
        try:
            with self._state_lock:
                if not self._is_playing:
                    logger.warning("⚠️ Воспроизведение уже остановлено")
                    return False
                
                if self._is_stopping:
                    logger.warning("⚠️ Воспроизведение уже останавливается")
                    return False
                
                self._is_stopping = True
                self._set_state(PlayerState.STOPPING)
                
                logger.info("🛑 Остановка воспроизведения...")
                
            # Устанавливаем флаг остановки
                self.stop_event.set()

                # Останавливаем поток
                self._stop_stream()
            
            # Ждем завершения потока воспроизведения
            if self.playback_thread and self.playback_thread.is_alive():
                self.playback_thread.join(timeout=2.0)
                
                # Очищаем данные
                self._clear_queue()
                self._clear_buffer()
                
                # Принудительная сборка мусора
                gc.collect()
                
                self._is_playing = False
                self._is_stopping = False
                self._set_state(PlayerState.STOPPED)
                
                logger.info("✅ Воспроизведение остановлено")
                return True
            
        except Exception as e:
            handle_audio_error(e, "ThreadSafeAudioPlayer", "stop_playback", "Остановка воспроизведения")
            self._handle_error(e)
            self._is_stopping = False
            return False

    def pause_playback(self) -> bool:
        """Приостанавливает воспроизведение"""
        try:
            with self._state_lock:
                if not self._is_playing:
                    logger.warning("⚠️ Воспроизведение не запущено")
                    return False
                
                if self._state == PlayerState.PAUSED:
                    logger.warning("⚠️ Воспроизведение уже приостановлено")
                    return False
                
                self.pause_event.clear()
                self._set_state(PlayerState.PAUSED)
                
                logger.info("⏸️ Воспроизведение приостановлено")
                return True
            
        except Exception as e:
            handle_audio_error(e, "ThreadSafeAudioPlayer", "pause_playback", "Приостановка воспроизведения")
            self._handle_error(e)
            return False

    def resume_playback(self) -> bool:
        """Возобновляет воспроизведение"""
        try:
            with self._state_lock:
                if not self._is_playing:
                    logger.warning("⚠️ Воспроизведение не запущено")
                    return False
                
                if self._state != PlayerState.PAUSED:
                    logger.warning("⚠️ Воспроизведение не приостановлено")
                    return False
                
                self.pause_event.set()
                self._set_state(PlayerState.PLAYING)
                
                logger.info("▶️ Воспроизведение возобновлено")
                return True
            
        except Exception as e:
            handle_audio_error(e, "ThreadSafeAudioPlayer", "resume_playback", "Возобновление воспроизведения")
            self._handle_error(e)
            return False

    def _process_available_chunks(self) -> int:
        """Обрабатывает все доступные чанки из очереди за одну итерацию"""
        chunks_processed = 0
        
        while not self.audio_queue.empty():
            try:
                audio_data = self.audio_queue.get(timeout=0.01)
                
                # Добавляем в буфер
                with self.buffer_lock:
                    old_size = len(self.internal_buffer)
                    self.internal_buffer = np.concatenate([self.internal_buffer, audio_data])
                    
                    # ДИАГНОСТИКА: Логируем только при обработке чанков
                    if chunks_processed == 0:  # Логируем только первый чанк
                        logger.info(f"✅ Playback loop: получены данные size={len(audio_data)}")
                        logger.info(f"🔍 Буфер: {old_size} → {len(self.internal_buffer)} сэмплов (+{len(audio_data)})")
                
                chunks_processed += 1
                
            except queue.Empty:
                break
        
        # ДИАГНОСТИКА: Логируем общее количество обработанных чанков
        if chunks_processed > 0:
            logger.info(f"🎯 Playback loop: обработано {chunks_processed} чанков за итерацию")
        else:
            logger.warning("⚠️ Playback loop: очередь пуста")
        
        return chunks_processed

    def _playback_loop(self):
        """Основной цикл воспроизведения с защитой от race conditions"""
        max_iterations = 100000
        iteration_count = 0
        
        try:
            logger.info("🔄 Playback loop запущен")
            
            while not self.stop_event.is_set() and iteration_count < max_iterations:
                iteration_count += 1
                
                try:
                    # Проверяем паузу
                    self.pause_event.wait()
                    
                    # ДИАГНОСТИКА: Логируем попытку получения данных
                    logger.info(f"🔍 Playback loop: очередь размер={self.audio_queue.qsize()}")
                    
                    # Обрабатываем все доступные чанки за одну итерацию
                    chunks_processed = self._process_available_chunks()
                    
                    if chunks_processed == 0:
                        # Нет данных в очереди, но продолжаем ждать
                        logger.warning("⚠️ Playback loop: очередь пуста, ждем данные...")
                        # НЕ завершаем цикл - ждем новые данные
                    
                    # Обновляем время последней активности
                    with self._metrics_lock:
                        self._last_activity = time.time()
                    
                    # Небольшая задержка для предотвращения перегрузки CPU
                    time.sleep(0.001)
                    
                except Exception as e:
                    handle_threading_error(e, "ThreadSafeAudioPlayer", "_playback_loop", "Цикл воспроизведения")
                    self._handle_error(e)
                time.sleep(0.1)
                
            if iteration_count >= max_iterations:
                logger.warning("⚠️ Достигнуто максимальное количество итераций в цикле воспроизведения")
                
        except Exception as e:
            handle_threading_error(e, "ThreadSafeAudioPlayer", "_playback_loop", "Основной цикл воспроизведения")
            self._handle_error(e)
        finally:
            logger.info("🔄 Playback loop завершен")

    def add_audio_data(self, audio_data: np.ndarray) -> bool:
        """Добавляет аудио данные с защитой от race conditions"""
        try:
            # ДИАГНОСТИКА: Логируем попытку добавления данных
            logger.info(f"🔍 add_audio_data: size={len(audio_data)}, playing={self._is_playing}")
            
            with self._state_lock:
                if not self._is_playing:
                    logger.warning("⚠️ Воспроизведение не запущено")
                    return False
                
                # Проверяем размер очереди
                if self.audio_queue.qsize() >= self.max_queue_size:
                    logger.warning("⚠️ Очередь аудио переполнена, пропускаем данные")
                    return False
                
                # Проверяем использование памяти
                if self._memory_monitor.is_memory_high():
                    logger.warning("⚠️ Высокое использование памяти, пропускаем данные")
                    return False
                
                # ДИАГНОСТИКА: Логируем успешное добавление
                self.audio_queue.put(audio_data)
                logger.info(f"✅ add_audio_data: данные добавлены в очередь, размер очереди={self.audio_queue.qsize()}")
                return True
            
        except Exception as e:
            handle_threading_error(e, "ThreadSafeAudioPlayer", "add_audio_data", "Добавление аудио данных")
            self._handle_error(e)
            return False

    def _set_state(self, new_state: PlayerState):
        """Устанавливает новое состояние с уведомлением"""
        try:
            old_state = self._state
            self._state = new_state
            
            if self.state_callback:
                try:
                    self.state_callback(old_state, new_state)
                except Exception as e:
                    logger.error(f"❌ Ошибка в state_callback: {e}")
            
        except Exception as e:
            handle_threading_error(e, "ThreadSafeAudioPlayer", "_set_state", "Установка состояния")

    def _get_optimal_channels_for_device(self, device) -> int:
        """Определяет оптимальное количество каналов для устройства"""
        try:
            if not device or not device.is_output:
                return 1
            
            # Максимум 2 канала для стерео, минимум 1 для моно
            optimal_channels = min(device.max_output_channels, 2) if device.max_output_channels > 0 else 1
            
            logger.info(f"🔍 Устройство: {device.name}, каналы: {optimal_channels} (max: {device.max_output_channels})")
            return optimal_channels
            
        except Exception as e:
            logger.warning(f"⚠️ Ошибка определения каналов: {e}, используем 1")
            return 1

    def _handle_error(self, error: Exception):
        """Обрабатывает ошибки"""
        try:
            with self._metrics_lock:
                self._errors_count += 1
            
            if self.error_callback:
                try:
                    self.error_callback(error)
                except Exception as e:
                    logger.error(f"❌ Ошибка в error_callback: {e}")
            
            # Если слишком много ошибок, останавливаем воспроизведение
            if self._errors_count > 10:
                logger.error("❌ Слишком много ошибок, останавливаем воспроизведение")
                self.stop_playback()
            
        except Exception as e:
                handle_threading_error(e, "ThreadSafeAudioPlayer", "_handle_error", "Обработка ошибки")

    def get_current_device(self):
        """Получает текущее устройство"""
        with self._device_info_lock:
            return self.current_device_info

    def get_current_device_name(self) -> Optional[str]:
        """Получает имя текущего устройства"""
        current_device = self.get_current_device()
        return current_device.name if current_device else None

    def switch_to_device(self, device_name: str) -> bool:
        """
        Переключается на указанное устройство используя простой универсальный подход
        
        ПРИНЦИП: Пробуем простое переключение, при ошибке - fallback
        """
        try:
            logger.info(f"🔄 Универсальное переключение на устройство: {device_name}")
            
            # Используем новый простой метод переключения
            success = simple_device_switch(self.audio_manager, device_name)
            
            if success:
                # Перезапускаем поток с новым устройством
                self._restart_stream_for_new_device()
                logger.info(f"✅ Успешно переключились на: {device_name}")
                return True
            else:
                logger.warning(f"❌ Не удалось переключиться на: {device_name}")
                return False
            
        except Exception as e:
            # Анализируем ошибку PortAudio
            current_device = self.audio_manager.get_current_device()
            if current_device:
                handle_portaudio_error(e, current_device)
                
            handle_device_error(e, "ThreadSafeAudioPlayer", "switch_to_device", f"Переключение на устройство {device_name}")
            self._handle_error(e)
            return False
                
    def switch_to_best_device(self) -> bool:
        """
        Переключается на лучшее устройство используя автоматическую логику
        
        ПРИНЦИП: AirPods > USB > Bluetooth > Built-in
        """
        try:
            logger.info("🔄 Автоматическое переключение на лучшее устройство...")
            
            # Используем новую автоматическую логику
            success = auto_switch_on_device_change(self.audio_manager)
            
            if success:
                # Перезапускаем поток с новым устройством
                self._restart_stream_for_new_device()
                current_device = self.audio_manager.get_current_device()
                device_name = current_device.name if current_device else "неизвестное"
                logger.info(f"✅ Автоматически переключились на: {device_name}")
                return True
            else:
                logger.warning("❌ Не удалось автоматически переключиться")
                return False
            
        except Exception as e:
            # Анализируем ошибку PortAudio
            current_device = self.audio_manager.get_current_device()
            if current_device:
                handle_portaudio_error(e, current_device)
            
            handle_device_error(e, "ThreadSafeAudioPlayer", "switch_to_best_device", "Переключение на лучшее устройство")
            self._handle_error(e)
            return False
    
    def _restart_stream_for_new_device(self):
        """
        Перезапускает аудио поток для нового устройства
        
        ПРИНЦИП: Останавливаем старый поток, запускаем новый
        """
        try:
            logger.info("🔄 Перезапуск аудио потока для нового устройства...")
            
            # Останавливаем текущий поток
            was_playing = self.is_playing()
            if was_playing:
                self._stop_stream()
                time.sleep(0.1)  # Небольшая пауза для корректной остановки
            
            # Получаем текущее устройство и его конфигурацию
            current_device = self.audio_manager.get_current_device()
            if current_device:
                # Получаем универсальную конфигурацию для устройства
                config = get_universal_audio_config(current_device)
                
                # Обновляем параметры плеера
                self.sample_rate = config['samplerate']
                self.channels = config['channels']
                self.dtype = config['dtype']
                
                logger.info(f"🎛️ Конфигурация для {current_device.name}: {config['samplerate']}Hz, {config['channels']}ch, {config['dtype']}")
            
            # Запускаем поток заново, если он был активен
            if was_playing:
                self._start_stream()
                logger.info("✅ Аудио поток перезапущен для нового устройства")
            
        except Exception as e:
            logger.error(f"❌ Ошибка перезапуска потока: {e}")
            self._handle_error(e)
        
    def get_available_devices(self):
        """Получает доступные устройства"""
        try:
            return self.audio_manager.get_output_devices()
        except Exception as e:
            handle_device_error(e, "ThreadSafeAudioPlayer", "get_available_devices", "Получение доступных устройств")
            self._handle_error(e)
            return []

    def get_metrics(self) -> PlayerMetrics:
        """Получает метрики плеера"""
        try:
            with self._metrics_lock:
                return PlayerMetrics(
                    state=self._state,
                    is_playing=self._is_playing,
                    queue_size=self.audio_queue.qsize(),
                    buffer_size=len(self.internal_buffer),
                    stream_active=self.stream is not None,
                    memory_usage=self._memory_monitor.get_memory_usage(),
                    errors_count=self._errors_count,
                    last_activity=self._last_activity
                )
        except Exception as e:
            handle_threading_error(e, "ThreadSafeAudioPlayer", "get_metrics", "Получение метрик")
            return PlayerMetrics(
                state=PlayerState.ERROR,
                is_playing=False,
                queue_size=0,
                buffer_size=0,
                stream_active=False,
                memory_usage=0,
                errors_count=0,
                last_activity=0
            )

    def set_state_callback(self, callback: Callable):
        """Устанавливает callback для изменения состояния"""
        self.state_callback = callback

    def set_error_callback(self, callback: Callable):
        """Устанавливает callback для обработки ошибок"""
        self.error_callback = callback

    def shutdown(self):
        """Останавливает аудио плеер с полной очисткой"""
        try:
            with self._state_lock:
                if self._is_shutting_down:
                    logger.warning("⚠️ Уже выполняется shutdown")
                    return
            

                self._is_shutting_down = True
                
                logger.info("🔄 Остановка ThreadSafeAudioPlayer...")
                
                # Останавливаем воспроизведение
                self.stop_playback()
                
                # Удаляем callback
            if self.audio_manager:
                self.audio_manager.remove_device_callback(self._on_device_change_callback)
                
                # Очищаем данные
                self._clear_queue()
                self._clear_buffer()
                
                # Очищаем кэш
                with self._cache_lock:
                    self._cached_stream_config = None
                    self._cached_device_info = None
                    self._stream_cache_valid = False
                
                # Принудительная сборка мусора
                gc.collect()
                
                logger.info("✅ ThreadSafeAudioPlayer остановлен")
                
        except Exception as e:
                    handle_threading_error(e, "ThreadSafeAudioPlayer", "shutdown", "Остановка плеера")

    def __del__(self):
        """Деструктор с очисткой"""
        try:
            self.shutdown()
        except Exception as e:
            handle_threading_error(e, "ThreadSafeAudioPlayer", "__del__", "Деструктор")


class MemoryMonitor:
    """Монитор использования памяти"""
    
    def __init__(self, max_memory_usage: int):
        self.max_memory_usage = max_memory_usage
        self.process = psutil.Process(os.getpid())
    
    def get_memory_usage(self) -> int:
        """Получает текущее использование памяти в байтах"""
        try:
            return self.process.memory_info().rss
        except Exception:
            return 0
    
    def is_memory_high(self) -> bool:
        """Проверяет, высокое ли использование памяти"""
        try:
            current_usage = self.get_memory_usage()
            return current_usage > self.max_memory_usage
        except Exception:
            return False
    

# Глобальный экземпляр
_global_thread_safe_audio_player = None

def get_global_thread_safe_audio_player() -> ThreadSafeAudioPlayer:
    """Получает глобальный экземпляр ThreadSafeAudioPlayer"""
    global _global_thread_safe_audio_player
    
    if _global_thread_safe_audio_player is None:
        _global_thread_safe_audio_player = ThreadSafeAudioPlayer()
    
    return _global_thread_safe_audio_player

def initialize_global_thread_safe_audio_player(config: Dict = None) -> ThreadSafeAudioPlayer:
    """Инициализирует глобальный экземпляр ThreadSafeAudioPlayer"""
    global _global_thread_safe_audio_player
    
    if _global_thread_safe_audio_player is None:
        _global_thread_safe_audio_player = ThreadSafeAudioPlayer()
    
    return _global_thread_safe_audio_player
                   