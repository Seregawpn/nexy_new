"""
Performance Monitor - Мониторинг производительности на macOS

ОСНОВНЫЕ ФУНКЦИИ:
1. Мониторинг CPU и памяти
2. Отслеживание производительности аудио
3. Оптимизация для macOS
4. Статистика работы
"""

import logging
import threading
import time
import psutil
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class PerformanceStats:
    """Статистика производительности"""
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    audio_latency_ms: float
    buffer_underruns: int
    buffer_overruns: int
    timestamp: float

class PerformanceMonitor:
    """Монитор производительности для macOS"""
    
    def __init__(self):
        self._is_running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._stats_history = []
        self._lock = threading.RLock()
        
    def start(self):
        """Запуск мониторинга"""
        if self._is_running:
            return
        
        self._stop_event.clear()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        self._is_running = True
        
        logger.info("📊 Performance Monitor запущен")
    
    def stop(self):
        """Остановка мониторинга"""
        if not self._is_running:
            return
        
        self._stop_event.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2.0)
        
        self._is_running = False
        logger.info("🛑 Performance Monitor остановлен")
    
    def _monitor_loop(self):
        """Основной цикл мониторинга"""
        while not self._stop_event.is_set():
            try:
                stats = self._collect_stats()
                
                with self._lock:
                    self._stats_history.append(stats)
                    # Ограничиваем размер истории
                    if len(self._stats_history) > 1000:
                        self._stats_history = self._stats_history[-500:]
                
                time.sleep(1.0)  # Обновляем каждую секунду
                
            except Exception as e:
                logger.error(f"❌ Ошибка в цикле мониторинга: {e}")
                time.sleep(1.0)
    
    def _collect_stats(self) -> PerformanceStats:
        """Сбор статистики"""
        try:
            # CPU и память
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            
            return PerformanceStats(
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_used_mb=memory.used / (1024 * 1024),
                audio_latency_ms=0.0,  # Пока не реализовано
                buffer_underruns=0,    # Пока не реализовано
                buffer_overruns=0,     # Пока не реализовано
                timestamp=time.time()
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка сбора статистики: {e}")
            return PerformanceStats(0, 0, 0, 0, 0, 0, time.time())
    
    def get_stats(self) -> Optional[PerformanceStats]:
        """Получить текущую статистику"""
        with self._lock:
            if self._stats_history:
                return self._stats_history[-1]
            return None
    
    def get_stats_history(self, limit: int = 10) -> List[PerformanceStats]:
        """Получить историю статистики"""
        with self._lock:
            return self._stats_history[-limit:]
    
    def get_average_stats(self, duration_seconds: int = 60) -> Optional[PerformanceStats]:
        """Получить среднюю статистику за период"""
        with self._lock:
            if not self._stats_history:
                return None
            
            cutoff_time = time.time() - duration_seconds
            recent_stats = [s for s in self._stats_history if s.timestamp >= cutoff_time]
            
            if not recent_stats:
                return None
            
            return PerformanceStats(
                cpu_percent=sum(s.cpu_percent for s in recent_stats) / len(recent_stats),
                memory_percent=sum(s.memory_percent for s in recent_stats) / len(recent_stats),
                memory_used_mb=sum(s.memory_used_mb for s in recent_stats) / len(recent_stats),
                audio_latency_ms=sum(s.audio_latency_ms for s in recent_stats) / len(recent_stats),
                buffer_underruns=sum(s.buffer_underruns for s in recent_stats),
                buffer_overruns=sum(s.buffer_overruns for s in recent_stats),
                timestamp=time.time()
            )
