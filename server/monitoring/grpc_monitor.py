"""
Мониторинг производительности gRPC сервера
Отслеживание метрик для масштабирования до 100 пользователей
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict, deque
import psutil
import os

logger = logging.getLogger(__name__)

@dataclass
class GrpcMetrics:
    """Метрики gRPC сервера"""
    active_connections: int = 0
    total_requests: int = 0
    requests_per_minute: int = 0
    error_rate: float = 0.0
    avg_response_time: float = 0.0
    memory_usage: float = 0.0
    cpu_usage: float = 0.0
    timestamp: float = field(default_factory=time.time)

@dataclass
class PerformanceLimits:
    """Лимиты производительности"""
    max_connections: int = 100
    max_requests_per_minute: int = 1000
    max_error_rate: float = 0.05  # 5%
    max_memory_usage: float = 80.0  # 80%
    max_cpu_usage: float = 80.0  # 80%
    max_response_time: float = 5.0  # 5 секунд

class GrpcMonitor:
    """Монитор производительности gRPC сервера"""
    
    def __init__(self, limits: Optional[PerformanceLimits] = None):
        self.limits = limits or PerformanceLimits()
        self.metrics = GrpcMetrics()
        self.request_times = deque(maxlen=1000)  # Последние 1000 запросов
        self.error_count = 0
        self.start_time = time.time()
        self.process = psutil.Process(os.getpid())
        
        # Счетчики для расчета RPS
        self.requests_in_minute = deque(maxlen=60)  # Запросы за последнюю минуту
        self.last_minute_check = time.time()
        
        logger.info("🔍 GrpcMonitor инициализирован")
        logger.info(f"📊 Лимиты: {self.limits.max_connections} соединений, {self.limits.max_requests_per_minute} RPS")
    
    def record_request(self, response_time: float, is_error: bool = False):
        """Записать метрику запроса"""
        current_time = time.time()
        
        # Обновляем счетчики
        self.metrics.total_requests += 1
        self.request_times.append(response_time)
        
        if is_error:
            self.error_count += 1
        
        # Добавляем запрос в минуту
        self.requests_in_minute.append(current_time)
        
        # Обновляем метрики
        self._update_metrics()
        
        # Проверяем лимиты
        self._check_limits()
    
    def set_active_connections(self, count: int):
        """Установить количество активных соединений"""
        self.metrics.active_connections = count
        self._check_limits()
    
    def _update_metrics(self):
        """Обновить метрики"""
        current_time = time.time()
        
        # Обновляем RPS
        if current_time - self.last_minute_check >= 60:
            # Удаляем старые запросы (старше минуты)
            minute_ago = current_time - 60
            while self.requests_in_minute and self.requests_in_minute[0] < minute_ago:
                self.requests_in_minute.popleft()
            
            self.metrics.requests_per_minute = len(self.requests_in_minute)
            self.last_minute_check = current_time
        
        # Обновляем среднее время ответа
        if self.request_times:
            self.metrics.avg_response_time = sum(self.request_times) / len(self.request_times)
        
        # Обновляем процент ошибок
        if self.metrics.total_requests > 0:
            self.metrics.error_rate = self.error_count / self.metrics.total_requests
        
        # Обновляем системные метрики
        self.metrics.memory_usage = self.process.memory_percent()
        self.metrics.cpu_usage = self.process.cpu_percent()
        self.metrics.timestamp = current_time
    
    def _check_limits(self):
        """Проверить лимиты и выдать предупреждения"""
        warnings = []
        
        # Проверяем соединения
        if self.metrics.active_connections >= self.limits.max_connections * 0.8:
            warnings.append(f"⚠️ Высокая нагрузка: {self.metrics.active_connections}/{self.limits.max_connections} соединений (80%+)")
        
        # Проверяем RPS
        if self.metrics.requests_per_minute >= self.limits.max_requests_per_minute * 0.8:
            warnings.append(f"⚠️ Высокая нагрузка: {self.metrics.requests_per_minute}/{self.limits.max_requests_per_minute} RPS (80%+)")
        
        # Проверяем ошибки
        if self.metrics.error_rate >= self.limits.max_error_rate:
            warnings.append(f"❌ Высокая ошибка: {self.metrics.error_rate:.1%} ошибок (лимит: {self.limits.max_error_rate:.1%})")
        
        # Проверяем память
        if self.metrics.memory_usage >= self.limits.max_memory_usage:
            warnings.append(f"⚠️ Высокая память: {self.metrics.memory_usage:.1f}% (лимит: {self.limits.max_memory_usage}%)")
        
        # Проверяем CPU
        if self.metrics.cpu_usage >= self.limits.max_cpu_usage:
            warnings.append(f"⚠️ Высокий CPU: {self.metrics.cpu_usage:.1f}% (лимит: {self.limits.max_cpu_usage}%)")
        
        # Проверяем время ответа
        if self.metrics.avg_response_time >= self.limits.max_response_time:
            warnings.append(f"⚠️ Медленный ответ: {self.metrics.avg_response_time:.2f}s (лимит: {self.limits.max_response_time}s)")
        
        # Выводим предупреждения
        for warning in warnings:
            logger.warning(warning)
        
        return warnings
    
    def get_metrics(self) -> Dict[str, Any]:
        """Получить текущие метрики"""
        self._update_metrics()
        return {
            "active_connections": self.metrics.active_connections,
            "total_requests": self.metrics.total_requests,
            "requests_per_minute": self.metrics.requests_per_minute,
            "error_rate": self.metrics.error_rate,
            "avg_response_time": self.metrics.avg_response_time,
            "memory_usage": self.metrics.memory_usage,
            "cpu_usage": self.metrics.cpu_usage,
            "uptime": time.time() - self.start_time,
            "timestamp": self.metrics.timestamp
        }
    
    def get_status(self) -> str:
        """Получить статус сервера"""
        metrics = self.get_metrics()
        warnings = self._check_limits()
        
        if warnings:
            return "WARNING"
        elif metrics["active_connections"] > 0:
            return "ACTIVE"
        else:
            return "IDLE"
    
    def reset_metrics(self):
        """Сбросить метрики"""
        self.metrics = GrpcMetrics()
        self.request_times.clear()
        self.error_count = 0
        self.requests_in_minute.clear()
        self.start_time = time.time()
        logger.info("🔄 Метрики сброшены")

# Глобальный экземпляр монитора
_global_monitor: Optional[GrpcMonitor] = None

def get_monitor() -> GrpcMonitor:
    """Получить глобальный экземпляр монитора"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = GrpcMonitor()
    return _global_monitor

def record_request(response_time: float, is_error: bool = False):
    """Записать метрику запроса"""
    monitor = get_monitor()
    monitor.record_request(response_time, is_error)

def set_active_connections(count: int):
    """Установить количество активных соединений"""
    monitor = get_monitor()
    monitor.set_active_connections(count)

def get_metrics() -> Dict[str, Any]:
    """Получить текущие метрики"""
    monitor = get_monitor()
    return monitor.get_metrics()

def get_status() -> str:
    """Получить статус сервера"""
    monitor = get_monitor()
    return monitor.get_status()
