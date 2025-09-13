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
    """Буфер для управления чанками аудио"""
    
    def __init__(self, max_memory_mb: int = 1024):
        """
        Инициализация буфера
        
        Args:
            max_memory_mb: Максимальное использование памяти в МБ
        """
        self._chunk_queue = queue.Queue()
        self._playback_buffer = np.array([], dtype=np.int16)
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
        
        logger.info(f"🔧 ChunkBuffer инициализирован (max_memory: {max_memory_mb}MB)")
    
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
                
                # Убеждаемся, что данные имеют правильную форму
                data = chunk_info.data
                if len(data.shape) == 2:
                    # 2D данные - преобразуем в 1D
                    data = data.flatten()
                
                # Добавляем в буфер
                if len(self._playback_buffer) == 0:
                    self._playback_buffer = data
                else:
                    self._playback_buffer = np.concatenate([self._playback_buffer, data])
                
                chunk_info.state = ChunkState.BUFFERED
                
                logger.info(f"✅ Чанк добавлен в буфер: {chunk_info.id} (size: {len(data)}, buffer: {old_size} → {len(self._playback_buffer)})")
                
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
                logger.debug(f"🎵 Воспроизведено: {frames} сэмплов (осталось: {len(self._playback_buffer)})")
                return data
            else:
                logger.warning(f"⚠️ Недостаточно данных: {len(self._playback_buffer)} < {frames}")
                return np.zeros(frames, dtype=np.int16)
    
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
            self._playback_buffer = np.array([], dtype=np.int16)
            logger.info(f"🧹 Буфер воспроизведения очищен: {old_size} сэмплов")
    
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
    
    def wait_for_completion(self, timeout: float = 30.0) -> bool:
        """
        Ждать завершения обработки всех чанков
        
        Args:
            timeout: Таймаут ожидания в секундах
            
        Returns:
            Успешность завершения
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.is_empty:
                logger.info("✅ Все чанки обработаны")
                return True
            
            time.sleep(0.1)
        
        logger.warning(f"⚠️ Таймаут ожидания завершения ({timeout}s)")
        return False











































