"""
Buffer Management - Управление буферами чанков

ОСНОВНЫЕ ПРИНЦИПЫ:
1. Без лимитов размера - накопление всех данных
2. FIFO порядок - строгий порядок чанков
3. Thread-safety - безопасная работа в многопоточной среде
4. Memory protection - защита от критических утечек памяти
"""

import logging
import queue
import threading
import time
import numpy as np
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime
from .state import ChunkState

logger = logging.getLogger(__name__)

@dataclass
class ChunkInfo:
    """Информация о чанке"""
    id: str
    data: np.ndarray
    timestamp: float
    size: int
    state: ChunkState
    priority: int = 0
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Инициализация после создания"""
        if self.metadata is None:
            self.metadata = {}

class ChunkBuffer:
    """
    Буфер для управления чанками аудио (2D: frames x channels)
    
    ВАЖНО: Параметры по умолчанию - fallback значения.
    Рекомендуется передавать параметры из централизованной конфигурации.
    """

    def __init__(self, max_memory_mb: int = 256, channels: int = 1, dtype: np.dtype = np.int16):
        """
        Инициализация буфера

        Args:
            max_memory_mb: Максимальное использование памяти в МБ
            channels: Количество каналов вывода
            dtype: Тип данных внутреннего буфера
        """
        self._chunk_queue = queue.Queue()
        self._channels = max(1, min(2, int(channels)))
        self._dtype = dtype
        self._playback_buffer = np.zeros((0, self._channels), dtype=self._dtype)
        self._buffer_lock = threading.RLock()
        self._max_memory_bytes = max_memory_mb * 1024 * 1024
        self._current_memory_usage = 0
        self._chunk_counter = 0
        self._stats = {
            'chunks_added': 0,
            'chunks_processed': 0,
            'chunks_completed': 0,
            'chunks_errors': 0,
            'total_data_size': 0,
            'peak_memory_usage': 0
        }

        logger.info(f"🔧 ChunkBuffer инициализирован (max_memory: {max_memory_mb}MB, channels: {self._channels})")

    def set_channels(self, channels: int):
        """Изменить число каналов буфера с безопасной конвертацией текущих данных"""
        new_ch = max(1, min(2, int(channels)))
        with self._buffer_lock:
            if new_ch == self._channels:
                return
            # ✅ ПРАВИЛЬНО: Убраны конвертации каналов
            # Буфер переинициализируется при смене каналов
            self._playback_buffer = np.zeros((0, new_ch), dtype=self._dtype)
            self._channels = new_ch
    
    @property
    def queue_size(self) -> int:
        """Размер очереди чанков"""
        return self._chunk_queue.qsize()
    
    @property
    def buffer_size(self) -> int:
        """Размер буфера воспроизведения"""
        with self._buffer_lock:
            return len(self._playback_buffer)
    
    @property
    def memory_usage_mb(self) -> float:
        """Использование памяти в МБ"""
        return self._current_memory_usage / (1024 * 1024)
    
    @property
    def is_empty(self) -> bool:
        """Пуст ли буфер"""
        return self.queue_size == 0 and self.buffer_size == 0
    
    @property
    def has_data(self) -> bool:
        """Есть ли данные для воспроизведения"""
        return self.buffer_size > 0
    
    def add_chunk(self, audio_data: np.ndarray, priority: int = 0, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Добавить чанк в буфер
        
        Args:
            audio_data: Аудио данные
            priority: Приоритет чанка
            metadata: Дополнительные метаданные
            
        Returns:
            ID чанка
        """
        try:
            # Создаем ID чанка
            chunk_id = f"chunk_{self._chunk_counter}_{int(time.time() * 1000)}"
            self._chunk_counter += 1
            
            # Создаем информацию о чанке
            chunk_info = ChunkInfo(
                id=chunk_id,
                data=audio_data.copy(),  # Копируем данные для безопасности
                timestamp=time.time(),
                size=len(audio_data),
                state=ChunkState.PENDING,
                priority=priority,
                metadata=metadata or {}
            )
            
            # Проверяем использование памяти
            if self._current_memory_usage + audio_data.nbytes > self._max_memory_bytes:
                logger.warning(f"⚠️ Превышен лимит памяти: {self.memory_usage_mb:.1f}MB")
                self._emergency_cleanup()
            
            # Добавляем в очередь
            self._chunk_queue.put(chunk_info)
            
            # Обновляем статистику
            self._stats['chunks_added'] += 1
            self._stats['total_data_size'] += audio_data.nbytes
            self._current_memory_usage += audio_data.nbytes
            
            if self._current_memory_usage > self._stats['peak_memory_usage']:
                self._stats['peak_memory_usage'] = self._current_memory_usage
            
            logger.info(f"✅ Чанк добавлен: {chunk_id} (size: {len(audio_data)}, queue: {self.queue_size})")
            
            return chunk_id
            
        except Exception as e:
            logger.error(f"❌ Ошибка добавления чанка: {e}")
            raise
    
    def get_next_chunk(self, timeout: float = 0.1) -> Optional[ChunkInfo]:
        """
        Получить следующий чанк из очереди
        
        Args:
            timeout: Таймаут ожидания в секундах
            
        Returns:
            Информация о чанке или None
        """
        try:
            chunk_info = self._chunk_queue.get(timeout=timeout)
            chunk_info.state = ChunkState.QUEUED
            logger.debug(f"🔍 Получен чанк: {chunk_info.id}")
            return chunk_info
        except queue.Empty:
            return None
        except Exception as e:
            logger.error(f"❌ Ошибка получения чанка: {e}")
            return None
    
    def add_to_playback_buffer(self, chunk_info: ChunkInfo) -> bool:
        """
        Добавить чанк в буфер воспроизведения
        
        Args:
            chunk_info: Информация о чанке
            
        Returns:
            Успешность операции
        """
        try:
            with self._buffer_lock:
                old_size = len(self._playback_buffer)

                data = chunk_info.data
                # ✅ ПРАВИЛЬНО: Данные уже в правильном формате из SequentialSpeechPlayer
                # Убраны все конвертации - плеер уже подготовил данные
                
                # Только проверяем форму (должна быть 2D)
                if data.ndim == 1:
                    data = data.reshape(-1, 1)
                elif data.ndim > 2:
                    data = data.reshape(data.shape[0], -1)

                # Добавляем в буфер (по rows)
                if len(self._playback_buffer) == 0:
                    self._playback_buffer = data
                else:
                    self._playback_buffer = np.vstack([self._playback_buffer, data])

                chunk_info.state = ChunkState.BUFFERED

                logger.info(
                    f"✅ Чанк добавлен в буфер: {chunk_info.id} (frames: {len(data)}, buffer: {old_size} → {len(self._playback_buffer)}, ch={self._channels})"
                )

                return True
                
        except Exception as e:
            logger.error(f"❌ Ошибка добавления в буфер: {e}")
            chunk_info.state = ChunkState.ERROR
            self._stats['chunks_errors'] += 1
            return False
    
    def get_playback_data(self, frames: int) -> np.ndarray:
        """
        Получить данные для воспроизведения
        
        Args:
            frames: Количество сэмплов
            
        Returns:
            Аудио данные
        """
        with self._buffer_lock:
            if len(self._playback_buffer) >= frames:
                data = self._playback_buffer[:frames]
                self._playback_buffer = self._playback_buffer[frames:]
                logger.debug(f"🎵 Воспроизведено: {frames} фреймов (осталось: {len(self._playback_buffer)})")
                return data
            else:
                # Если данных недостаточно, возвращаем то что есть + тишина (2D)
                if len(self._playback_buffer) > 0:
                    data = self._playback_buffer.copy()
                    current_dtype = self._playback_buffer.dtype
                    current_ch = self._playback_buffer.shape[1]
                    self._playback_buffer = np.zeros((0, current_ch), dtype=current_dtype)
                    silence = np.zeros((frames - len(data), current_ch), dtype=current_dtype)
                    result = np.vstack([data, silence])
                    logger.debug(
                        f"🎵 Воспроизведено: {len(data)} фреймов + {len(silence)} тишины (dtype={current_dtype}, ch={current_ch})"
                    )
                    return result
                else:
                    logger.debug(f"🎵 Нет данных, воспроизводим тишину: {frames} фреймов, ch={self._channels}")
                    return np.zeros((frames, self._channels), dtype=self._dtype)
    
    def mark_chunk_completed(self, chunk_info: ChunkInfo):
        """Отметить чанк как завершенный"""
        chunk_info.state = ChunkState.COMPLETED
        self._stats['chunks_completed'] += 1
        
        # Освобождаем память
        self._current_memory_usage -= chunk_info.data.nbytes
        chunk_info.data = np.array([], dtype=np.int16)  # Очищаем данные
        chunk_info.state = ChunkState.CLEANED
        
        logger.debug(f"✅ Чанк завершен: {chunk_info.id}")
    
    def clear_queue(self):
        """Очистить очередь чанков"""
        cleared_count = 0
        while not self._chunk_queue.empty():
            try:
                chunk_info = self._chunk_queue.get_nowait()
                self._current_memory_usage -= chunk_info.data.nbytes
                cleared_count += 1
            except queue.Empty:
                break
        
        logger.info(f"🧹 Очередь очищена: {cleared_count} чанков")
    
    def clear_playback_buffer(self):
        """Очистить буфер воспроизведения"""
        with self._buffer_lock:
            old_size = len(self._playback_buffer)
            self._playback_buffer = np.zeros((0, self._channels), dtype=self._dtype)
            logger.info(f"🧹 Буфер воспроизведения очищен: {old_size} фреймов")
    
    def clear_all(self):
        """Очистить все буферы"""
        self.clear_queue()
        self.clear_playback_buffer()
        self._current_memory_usage = 0
        logger.info("🧹 Все буферы очищены")
    
    def _emergency_cleanup(self):
        """Экстренная очистка при превышении лимита памяти"""
        logger.warning("🚨 Экстренная очистка памяти...")
        
        # Очищаем очередь
        self.clear_queue()
        
        # Очищаем буфер воспроизведения
        self.clear_playback_buffer()
        
        # Принудительная сборка мусора
        import gc
        gc.collect()
        
        logger.info("✅ Экстренная очистка завершена")
    
    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику буфера"""
        return {
            **self._stats,
            'current_memory_usage_mb': self.memory_usage_mb,
            'queue_size': self.queue_size,
            'buffer_size': self.buffer_size,
            'is_empty': self.is_empty,
            'has_data': self.has_data
        }
    
    def wait_for_completion(self, timeout: float = None) -> bool:
        """
        Ждать завершения обработки всех чанков
        
        Args:
            timeout: Таймаут ожидания в секундах (None = без таймаута)
            
        Returns:
            Успешность завершения
        """
        start_time = time.time()
        
        while True:
            if self.is_empty:
                elapsed = time.time() - start_time
                logger.info(f"✅ Все чанки обработаны за {elapsed:.1f}с")
                return True
            
            # Проверяем таймаут только если он задан
            if timeout is not None and time.time() - start_time >= timeout:
                logger.warning(f"⚠️ Таймаут ожидания завершения ({timeout}s)")
                return False
            
            time.sleep(0.1)









































