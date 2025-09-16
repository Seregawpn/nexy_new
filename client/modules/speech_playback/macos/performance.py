"""
Performance Monitor - Мониторинг производительности на macOS
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
        """Инициализация монитора"""
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._stats_history: List[PerformanceStats] = []
        self._max_history = 100  # Максимум 100 записей в истории
        
        # Счетчики
        self._buffer_underruns = 0
        self._buffer_overruns = 0
        self._audio_latency_ms = 0.0
        
        logger.info("📊 PerformanceMonitor создан")
    
    def start(self) -> bool:
        """
        Запускает мониторинг производительности
        
        Returns:
            True если запуск успешен, False иначе
        """
        try:
            if self._running:
                logger.warning("⚠️ Мониторинг уже запущен")
                return True
            
            self._running = True
            self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self._monitor_thread.start()
            
            logger.info("✅ Мониторинг производительности запущен")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска мониторинга: {e}")
            return False
    
    def stop(self):
        """Останавливает мониторинг производительности"""
        try:
            self._running = False
            
            if self._monitor_thread and self._monitor_thread.is_alive():
                self._monitor_thread.join(timeout=1.0)
            
            logger.info("✅ Мониторинг производительности остановлен")
            
        except Exception as e:
            logger.error(f"❌ Ошибка остановки мониторинга: {e}")
    
    def _monitor_loop(self):
        """Основной цикл мониторинга"""
        try:
            while self._running:
                # Собираем статистику
                stats = self._collect_stats()
                
                # Добавляем в историю
                self._stats_history.append(stats)
                
                # Ограничиваем размер истории
                if len(self._stats_history) > self._max_history:
                    self._stats_history.pop(0)
                
                # Логируем каждые 10 секунд
                if len(self._stats_history) % 10 == 0:
                    logger.debug(f"📊 CPU: {stats.cpu_percent:.1f}%, Memory: {stats.memory_percent:.1f}%")
                
                # Ждем 1 секунду
                time.sleep(1.0)
                
        except Exception as e:
            logger.error(f"❌ Ошибка в цикле мониторинга: {e}")
    
    def _collect_stats(self) -> PerformanceStats:
        """
        Собирает текущую статистику производительности
        
        Returns:
            PerformanceStats объект
        """
        try:
            # Получаем информацию о системе
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            
            stats = PerformanceStats(
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_used_mb=memory.used / (1024 * 1024),  # MB
                audio_latency_ms=self._audio_latency_ms,
                buffer_underruns=self._buffer_underruns,
                buffer_overruns=self._buffer_overruns,
                timestamp=time.time()
            )
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Ошибка сбора статистики: {e}")
            # Возвращаем пустую статистику при ошибке
            return PerformanceStats(
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_used_mb=0.0,
                audio_latency_ms=0.0,
                buffer_underruns=0,
                buffer_overruns=0,
                timestamp=time.time()
            )
    
    def get_current_stats(self) -> Optional[PerformanceStats]:
        """
        Получает текущую статистику
        
        Returns:
            Последняя PerformanceStats или None
        """
        try:
            if not self._stats_history:
                return None
            
            return self._stats_history[-1]
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения текущей статистики: {e}")
            return None
    
    def get_stats_history(self, count: int = 10) -> List[PerformanceStats]:
        """
        Получает историю статистики
        
        Args:
            count: Количество последних записей
            
        Returns:
            Список PerformanceStats
        """
        try:
            if not self._stats_history:
                return []
            
            return self._stats_history[-count:]
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения истории статистики: {e}")
            return []
    
    def get_average_stats(self, duration_seconds: int = 60) -> Optional[PerformanceStats]:
        """
        Получает усредненную статистику за период
        
        Args:
            duration_seconds: Период в секундах
            
        Returns:
            Усредненная PerformanceStats или None
        """
        try:
            if not self._stats_history:
                return None
            
            current_time = time.time()
            cutoff_time = current_time - duration_seconds
            
            # Фильтруем записи за период
            recent_stats = [
                stats for stats in self._stats_history
                if stats.timestamp >= cutoff_time
            ]
            
            if not recent_stats:
                return None
            
            # Вычисляем средние значения
            avg_cpu = sum(s.cpu_percent for s in recent_stats) / len(recent_stats)
            avg_memory = sum(s.memory_percent for s in recent_stats) / len(recent_stats)
            avg_memory_mb = sum(s.memory_used_mb for s in recent_stats) / len(recent_stats)
            avg_latency = sum(s.audio_latency_ms for s in recent_stats) / len(recent_stats)
            
            return PerformanceStats(
                cpu_percent=avg_cpu,
                memory_percent=avg_memory,
                memory_used_mb=avg_memory_mb,
                audio_latency_ms=avg_latency,
                buffer_underruns=self._buffer_underruns,
                buffer_overruns=self._buffer_overruns,
                timestamp=current_time
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка вычисления усредненной статистики: {e}")
            return None
    
    def record_buffer_underrun(self):
        """Записывает underrun буфера"""
        self._buffer_underruns += 1
        logger.warning("⚠️ Buffer underrun зафиксирован")
    
    def record_buffer_overrun(self):
        """Записывает overrun буфера"""
        self._buffer_overruns += 1
        logger.warning("⚠️ Buffer overrun зафиксирован")
    
    def set_audio_latency(self, latency_ms: float):
        """
        Устанавливает текущую задержку аудио
        
        Args:
            latency_ms: Задержка в миллисекундах
        """
        self._audio_latency_ms = latency_ms
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Получает сводку производительности
        
        Returns:
            Словарь с сводкой производительности
        """
        try:
            current_stats = self.get_current_stats()
            avg_stats = self.get_average_stats(60)  # За последнюю минуту
            
            summary = {
                'monitor_running': self._running,
                'history_size': len(self._stats_history),
                'current_stats': current_stats.__dict__ if current_stats else None,
                'average_stats_1min': avg_stats.__dict__ if avg_stats else None,
                'buffer_underruns': self._buffer_underruns,
                'buffer_overruns': self._buffer_overruns
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения сводки производительности: {e}")
            return {'error': str(e)}
    
    def cleanup(self):
        """Очистка ресурсов"""
        try:
            self.stop()
            self._stats_history.clear()
            logger.info("✅ PerformanceMonitor очищен")
            
        except Exception as e:
            logger.error(f"❌ Ошибка очистки PerformanceMonitor: {e}")
