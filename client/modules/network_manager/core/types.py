"""
Типы данных для NetworkManager Module
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Optional, Callable, Any
import asyncio
import time

class NetworkStatus(Enum):
    """Статусы сети"""
    CONNECTED = "connected"           # Сеть подключена
    DISCONNECTED = "disconnected"     # Сеть отключена
    CONNECTING = "connecting"         # Подключение в процессе
    FAILED = "failed"                 # Ошибка подключения
    UNKNOWN = "unknown"               # Статус неизвестен

class NetworkQuality(Enum):
    """Качество сети"""
    EXCELLENT = "excellent"           # Отличное (ping < 50ms)
    GOOD = "good"                     # Хорошее (ping 50-100ms)
    FAIR = "fair"                     # Удовлетворительное (ping 100-200ms)
    POOR = "poor"                     # Плохое (ping 200-500ms)
    VERY_POOR = "very_poor"           # Очень плохое (ping > 500ms)
    UNKNOWN = "unknown"               # Неизвестное качество

class ConnectionType(Enum):
    """Типы соединения"""
    ETHERNET = "ethernet"             # Проводное соединение
    WIFI = "wifi"                     # Wi-Fi
    CELLULAR = "cellular"             # Мобильная сеть
    UNKNOWN = "unknown"               # Неизвестный тип

@dataclass
class NetworkMetrics:
    """Метрики сети"""
    ping_time: float = 0.0            # Время пинга в мс
    download_speed: float = 0.0       # Скорость загрузки в Мбит/с
    upload_speed: float = 0.0         # Скорость выгрузки в Мбит/с
    packet_loss: float = 0.0          # Потеря пакетов в %
    jitter: float = 0.0               # Джиттер в мс
    last_updated: float = 0.0         # Время последнего обновления

@dataclass
class NetworkConfig:
    """Конфигурация NetworkManager"""
    check_interval: float = 30.0      # Интервал проверки в секундах
    ping_timeout: float = 5.0         # Таймаут пинга в секундах
    max_retries: int = 3              # Максимальное количество попыток
    retry_delay: float = 5.0          # Задержка между попытками в секундах
    test_urls: List[str] = None       # URL для тестирования
    ping_hosts: List[str] = None      # Хосты для пинга
    
    def __post_init__(self):
        if self.test_urls is None:
            self.test_urls = [
                "https://www.google.com",
                "https://www.apple.com",
                "https://www.cloudflare.com"
            ]
        if self.ping_hosts is None:
            self.ping_hosts = [
                "8.8.8.8",      # Google DNS
                "1.1.1.1",      # Cloudflare DNS
                "208.67.222.222" # OpenDNS
            ]

@dataclass
class NetworkTestResult:
    """Результат тестирования сети"""
    success: bool                     # Успешность теста
    test_type: str                    # Тип теста
    duration: float                   # Время выполнения в секундах
    details: Dict[str, Any]           # Дополнительные детали
    error_message: Optional[str] = None # Сообщение об ошибке
    timestamp: float = 0.0            # Время выполнения теста
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()

@dataclass
class NetworkDiagnostic:
    """Диагностика сети"""
    overall_status: NetworkStatus     # Общий статус
    connectivity_tests: List[NetworkTestResult]  # Результаты тестов
    network_quality: NetworkQuality   # Качество сети
    connection_type: ConnectionType   # Тип соединения
    metrics: NetworkMetrics           # Метрики сети
    issues: List[str]                 # Обнаруженные проблемы
    recommendations: List[str]        # Рекомендации по исправлению
    timestamp: float = 0.0            # Время диагностики
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()

@dataclass
class NetworkEvent:
    """Событие сети"""
    event_type: str                   # Тип события
    old_status: NetworkStatus         # Предыдущий статус
    new_status: NetworkStatus         # Новый статус
    details: Dict[str, Any]           # Дополнительные детали
    timestamp: float = 0.0            # Время события
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()

class NetworkCallback:
    """Callback для событий сети"""
    
    def __init__(self, callback: Callable[[NetworkEvent], None]):
        self.callback = callback
        self.is_async = asyncio.iscoroutinefunction(callback)
    
    async def call(self, event: NetworkEvent):
        """Вызвать callback"""
        try:
            if self.is_async:
                await self.callback(event)
            else:
                self.callback(event)
        except Exception as e:
            print(f"Network callback error: {e}")

class NetworkManagerState:
    """Состояние NetworkManager"""
    
    def __init__(self):
        self.current_status: NetworkStatus = NetworkStatus.UNKNOWN
        self.network_quality: NetworkQuality = NetworkQuality.UNKNOWN
        self.connection_type: ConnectionType = ConnectionType.UNKNOWN
        self.metrics: NetworkMetrics = NetworkMetrics()
        self.is_monitoring: bool = False
        self.last_check: float = 0.0
        self.callbacks: List[NetworkCallback] = []
        self.config: Optional[NetworkConfig] = None
        self.diagnostic_history: List[NetworkDiagnostic] = []
    
    def add_callback(self, callback: Callable[[NetworkEvent], None]):
        """Добавить callback"""
        self.callbacks.append(NetworkCallback(callback))
    
    async def notify_callbacks(self, event: NetworkEvent):
        """Уведомить все callbacks"""
        for callback in self.callbacks:
            await callback.call(event)
    
    def update_status(self, new_status: NetworkStatus):
        """Обновить статус"""
        if self.current_status != new_status:
            old_status = self.current_status
            self.current_status = new_status
            return old_status
        return self.current_status  # Возвращаем текущий статус вместо None
    
    def update_quality(self, new_quality: NetworkQuality):
        """Обновить качество"""
        if self.network_quality != new_quality:
            self.network_quality = new_quality
            return True
        return False
    
    def update_metrics(self, new_metrics: NetworkMetrics):
        """Обновить метрики"""
        self.metrics = new_metrics
        self.metrics.last_updated = time.time()
    
    def add_diagnostic(self, diagnostic: NetworkDiagnostic):
        """Добавить диагностику в историю"""
        self.diagnostic_history.append(diagnostic)
        # Ограничиваем историю последними 10 записями
        if len(self.diagnostic_history) > 10:
            self.diagnostic_history = self.diagnostic_history[-10:]
    
    def get_latest_diagnostic(self) -> Optional[NetworkDiagnostic]:
        """Получить последнюю диагностику"""
        return self.diagnostic_history[-1] if self.diagnostic_history else None










