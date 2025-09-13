"""
Управление состоянием воспроизведения речи
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import time

class PlaybackState(Enum):
    """Состояния воспроизведения"""
    IDLE = "idle"
    PLAYING = "playing"
    PAUSED = "paused"
    STOPPING = "stopping"
    ERROR = "error"

class ChunkState(Enum):
    """Состояния чанков"""
    PENDING = "pending"
    QUEUED = "queued"
    BUFFERED = "buffered"
    PLAYING = "playing"
    COMPLETED = "completed"
    CLEANED = "cleaned"
    ERROR = "error"
    FAILED = "failed"

@dataclass
class ChunkInfo:
    """Информация о чанке"""
    chunk_id: str
    data: bytes
    timestamp: float
    state: ChunkState = ChunkState.PENDING
    duration: Optional[float] = None
    error: Optional[str] = None

class StateManager:
    """Менеджер состояния воспроизведения"""
    
    def __init__(self):
        self.current_state = PlaybackState.IDLE
        self.previous_state = None
        self.state_history: List[PlaybackState] = []
        self.state_change_time = time.time()
        self.chunks: Dict[str, ChunkInfo] = {}
        self.current_chunk_id: Optional[str] = None
        
    def set_state(self, new_state: PlaybackState):
        """Устанавливает новое состояние"""
        if new_state != self.current_state:
            self.previous_state = self.current_state
            self.current_state = new_state
            self.state_history.append(new_state)
            self.state_change_time = time.time()
            
    def get_state(self) -> PlaybackState:
        """Возвращает текущее состояние"""
        return self.current_state
        
    def is_playing(self) -> bool:
        """Проверяет, идет ли воспроизведение"""
        return self.current_state == PlaybackState.PLAYING
        
    def is_paused(self) -> bool:
        """Проверяет, приостановлено ли воспроизведение"""
        return self.current_state == PlaybackState.PAUSED
        
    def is_idle(self) -> bool:
        """Проверяет, находится ли в режиме ожидания"""
        return self.current_state == PlaybackState.IDLE
        
    def add_chunk(self, chunk_id: str, data: bytes) -> ChunkInfo:
        """Добавляет чанк"""
        chunk = ChunkInfo(
            chunk_id=chunk_id,
            data=data,
            timestamp=time.time()
        )
        self.chunks[chunk_id] = chunk
        return chunk
        
    def get_chunk(self, chunk_id: str) -> Optional[ChunkInfo]:
        """Возвращает чанк по ID"""
        return self.chunks.get(chunk_id)
        
    def update_chunk_state(self, chunk_id: str, state: ChunkState, error: str = None):
        """Обновляет состояние чанка"""
        if chunk_id in self.chunks:
            self.chunks[chunk_id].state = state
            if error:
                self.chunks[chunk_id].error = error
                
    def get_status(self) -> Dict[str, Any]:
        """Возвращает статус"""
        return {
            "current_state": self.current_state.value,
            "previous_state": self.previous_state.value if self.previous_state else None,
            "is_playing": self.is_playing(),
            "is_paused": self.is_paused(),
            "is_idle": self.is_idle(),
            "state_change_time": self.state_change_time,
            "chunks_count": len(self.chunks),
            "current_chunk_id": self.current_chunk_id
        }
