"""
Улучшенный gRPC клиент для надежного сетевого взаимодействия

Этот модуль предоставляет:
- Централизованную обработку ошибок
- Retry механизмы с exponential backoff
- Health check систему
- Fallback режим для offline работы
- Thread-safe операции
- Мониторинг и метрики
"""

import asyncio
import logging
import time
import threading
from typing import Optional, Dict, Any, List, Callable, Union
from dataclasses import dataclass
from enum import Enum
import grpc
import grpc.aio
from concurrent.futures import ThreadPoolExecutor

from error_handler import (
    handle_network_error, handle_config_error, handle_threading_error,
    ErrorSeverity, ErrorCategory
)

logger = logging.getLogger(__name__)

class ConnectionState(Enum):
    """Состояния соединения"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"

class RetryStrategy(Enum):
    """Стратегии повторных попыток"""
    NONE = "none"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    FIBONACCI = "fibonacci"

@dataclass
class ServerConfig:
    """Конфигурация сервера"""
    address: str
    port: int
    use_ssl: bool = False
    timeout: int = 30
    retry_attempts: int = 3
    retry_delay: float = 1.0
    max_message_size: int = 50 * 1024 * 1024  # 50MB
    keep_alive_time: int = 30
    keep_alive_timeout: int = 5
    keep_alive_permit_without_calls: bool = True

@dataclass
class ConnectionMetrics:
    """Метрики соединения"""
    total_connections: int = 0
    successful_connections: int = 0
    failed_connections: int = 0
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_response_time: float = 0.0
    last_connection_time: Optional[float] = None
    last_error: Optional[str] = None

class ImprovedGrpcClient:
    """Улучшенный gRPC клиент с надежным сетевым взаимодействием"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._create_default_config()
        self.servers: Dict[str, ServerConfig] = {}
        self.current_server: Optional[str] = None
        self.connection_state = ConnectionState.DISCONNECTED
        self.metrics = ConnectionMetrics()
        
        # Сетевые компоненты
        self.channel: Optional[grpc.aio.Channel] = None
        self.stub: Optional[Any] = None
        self.health_check_task: Optional[asyncio.Task] = None
        self.retry_manager = RetryManager()
        
        # Thread safety
        self._lock = threading.RLock()
        self._connection_lock = asyncio.Lock()
        
        # Callbacks
        self.on_connection_changed: Optional[Callable[[ConnectionState], None]] = None
        self.on_error: Optional[Callable[[Exception, str], None]] = None
        
        # Инициализация
        self._initialize_servers()
        self._start_health_checker()
    
    def _create_default_config(self) -> Dict[str, Any]:
        """Создает конфигурацию по умолчанию"""
        return {
            'servers': {
                'local': {
                    'address': '127.0.0.1',
                    'port': 50051,
                    'use_ssl': False,
                    'timeout': 30,
                    'retry_attempts': 3,
                    'retry_delay': 1.0
                },
                'production': {
                    'address': '20.151.51.172',
                    'port': 50051,
                    'use_ssl': False,
                    'timeout': 120,
                    'retry_attempts': 5,
                    'retry_delay': 2.0
                }
            },
            'auto_fallback': True,
            'health_check_interval': 30,
            'connection_timeout': 10,
            'max_retry_attempts': 3,
            'retry_strategy': RetryStrategy.EXPONENTIAL,
            'circuit_breaker_threshold': 5,
            'circuit_breaker_timeout': 60
        }
    
    def _initialize_servers(self):
        """Инициализирует конфигурации серверов"""
        try:
            servers_config = self.config.get('servers', {})
            for name, server_config in servers_config.items():
                self.servers[name] = ServerConfig(
                    address=server_config['address'],
                    port=server_config['port'],
                    use_ssl=server_config.get('use_ssl', False),
                    timeout=server_config.get('timeout', 30),
                    retry_attempts=server_config.get('retry_attempts', 3),
                    retry_delay=server_config.get('retry_delay', 1.0),
                    max_message_size=server_config.get('max_message_size', 50 * 1024 * 1024)
                )
            
            # Выбираем первый доступный сервер
            if self.servers:
                self.current_server = list(self.servers.keys())[0]
                logger.info(f"🌐 Инициализировано {len(self.servers)} серверов")
            else:
                logger.warning("⚠️ Нет доступных серверов в конфигурации")
                
        except Exception as e:
            handle_config_error(e, "ImprovedGrpcClient", "_initialize_servers", "Инициализация серверов")
            logger.error(f"❌ Ошибка инициализации серверов: {e}")
    
    def _start_health_checker(self):
        """Запускает проверку здоровья соединения"""
        try:
            if self.health_check_task and not self.health_check_task.done():
                self.health_check_task.cancel()
            
            # Проверяем, есть ли активный event loop
            try:
                loop = asyncio.get_running_loop()
                self.health_check_task = loop.create_task(self._health_check_loop())
                logger.info("🔍 Запущен health checker")
            except RuntimeError:
                # Нет активного event loop, запустим позже
                logger.info("🔍 Health checker будет запущен при первом подключении")
                self.health_check_task = None
        except Exception as e:
            handle_threading_error(e, "ImprovedGrpcClient", "_start_health_checker", "Запуск health checker")
    
    async def _health_check_loop(self):
        """Основной цикл проверки здоровья"""
        while True:
            try:
                await asyncio.sleep(self.config.get('health_check_interval', 30))
                await self._check_connection_health()
            except asyncio.CancelledError:
                break
            except Exception as e:
                handle_threading_error(e, "ImprovedGrpcClient", "_health_check_loop", "Health check loop")
                await asyncio.sleep(5)  # Короткая пауза при ошибке
    
    async def _check_connection_health(self):
        """Проверяет здоровье текущего соединения"""
        try:
            if self.connection_state == ConnectionState.CONNECTED:
                # Простая проверка доступности канала
                if self.channel and not self.channel.get_state() == grpc.ChannelConnectivity.READY:
                    logger.warning("⚠️ Соединение потеряно, переподключаемся...")
                    await self._reconnect()
            elif self.connection_state == ConnectionState.DISCONNECTED:
                # Пытаемся переподключиться
                await self._connect()
        except Exception as e:
            handle_network_error(e, "ImprovedGrpcClient", "_check_connection_health", "Проверка здоровья соединения")
    
    async def connect(self, server_name: Optional[str] = None) -> bool:
        """Подключается к серверу"""
        try:
            async with self._connection_lock:
                if server_name and server_name in self.servers:
                    self.current_server = server_name
                
                return await self._connect()
        except Exception as e:
            handle_network_error(e, "ImprovedGrpcClient", "connect", "Подключение к серверу")
            return False
    
    async def _connect(self) -> bool:
        """Внутренний метод подключения"""
        try:
            if not self.current_server or self.current_server not in self.servers:
                logger.error("❌ Нет доступного сервера для подключения")
                return False
            
            self.connection_state = ConnectionState.CONNECTING
            self._notify_connection_changed()
            
            server_config = self.servers[self.current_server]
            address = f"{server_config.address}:{server_config.port}"
            
            # Закрываем предыдущее соединение
            if self.channel:
                try:
                    await self.channel.close()
                except:
                    pass
            
            # Настройки gRPC
            options = [
                ('grpc.max_send_message_length', server_config.max_message_size),
                ('grpc.max_receive_message_length', server_config.max_message_size),
                ('grpc.max_metadata_size', 1024 * 1024),
                ('grpc.keepalive_time_ms', server_config.keep_alive_time * 1000),
                ('grpc.keepalive_timeout_ms', server_config.keep_alive_timeout * 1000),
                ('grpc.keepalive_permit_without_calls', server_config.keep_alive_permit_without_calls),
                ('grpc.http2.max_pings_without_data', 0),
                ('grpc.http2.min_time_between_pings_ms', 10000),
                ('grpc.http2.min_ping_interval_without_data_ms', 300000)
            ]
            
            # Создаем канал
            if server_config.use_ssl:
                self.channel = grpc.aio.secure_channel(
                    address, 
                    grpc.aio.ssl_channel_credentials(), 
                    options=options
                )
            else:
                self.channel = grpc.aio.insecure_channel(address, options=options)
            
            # Создаем stub
            self.stub = self._create_stub()
            
            # Ждем готовности канала
            try:
                await asyncio.wait_for(
                    self.channel.channel_ready(),
                    timeout=self.config.get('connection_timeout', 10)
                )
                
                self.connection_state = ConnectionState.CONNECTED
                self.metrics.successful_connections += 1
                self.metrics.last_connection_time = time.time()
                self._notify_connection_changed()
                
                # Запускаем health checker если он еще не запущен
                if self.health_check_task is None:
                    self.health_check_task = asyncio.create_task(self._health_check_loop())
                    logger.info("🔍 Запущен health checker")
                
                logger.info(f"✅ Подключение к {address} установлено")
                return True
                
            except asyncio.TimeoutError:
                logger.error(f"⏰ Таймаут подключения к {address}")
                self.connection_state = ConnectionState.FAILED
                self.metrics.failed_connections += 1
                self._notify_connection_changed()
                return False
                
        except Exception as e:
            handle_network_error(e, "ImprovedGrpcClient", "_connect", "Подключение к серверу")
            self.connection_state = ConnectionState.FAILED
            self.metrics.failed_connections += 1
            self.metrics.last_error = str(e)
            self._notify_connection_changed()
            return False
    
    def _create_stub(self):
        """Создает gRPC stub (должен быть переопределен в наследниках)"""
        # Это базовый класс, stub создается в наследниках
        return None
    
    async def disconnect(self):
        """Отключается от сервера"""
        try:
            async with self._connection_lock:
                if self.channel:
                    await self.channel.close()
                    self.channel = None
                    self.stub = None
                
                self.connection_state = ConnectionState.DISCONNECTED
                self._notify_connection_changed()
                logger.info("🔌 Отключение от сервера")
        except Exception as e:
            handle_network_error(e, "ImprovedGrpcClient", "disconnect", "Отключение от сервера")
    
    async def _reconnect(self):
        """Переподключается к серверу"""
        try:
            logger.info("🔄 Переподключение к серверу...")
            await self.disconnect()
            await asyncio.sleep(1)  # Короткая пауза
            return await self._connect()
        except Exception as e:
            handle_network_error(e, "ImprovedGrpcClient", "_reconnect", "Переподключение")
            return False
    
    async def switch_server(self, server_name: str) -> bool:
        """Переключается на другой сервер"""
        try:
            if server_name not in self.servers:
                logger.error(f"❌ Сервер {server_name} не найден")
                return False
            
            logger.info(f"🔄 Переключение на сервер {server_name}")
            self.current_server = server_name
            return await self._reconnect()
        except Exception as e:
            handle_network_error(e, "ImprovedGrpcClient", "switch_server", "Переключение сервера")
            return False
    
    async def execute_with_retry(self, operation: Callable, *args, **kwargs) -> Any:
        """Выполняет операцию с retry механизмом"""
        try:
            return await self.retry_manager.execute_with_retry(
                operation, *args, **kwargs
            )
        except Exception as e:
            handle_network_error(e, "ImprovedGrpcClient", "execute_with_retry", "Выполнение операции с retry")
            raise
    
    def get_connection_state(self) -> ConnectionState:
        """Возвращает текущее состояние соединения"""
        return self.connection_state
    
    def get_metrics(self) -> ConnectionMetrics:
        """Возвращает метрики соединения"""
        return self.metrics
    
    def is_connected(self) -> bool:
        """Проверяет, подключен ли клиент"""
        return self.connection_state == ConnectionState.CONNECTED
    
    def set_connection_callback(self, callback: Callable[[ConnectionState], None]):
        """Устанавливает callback для изменений состояния соединения"""
        self.on_connection_changed = callback
    
    def set_error_callback(self, callback: Callable[[Exception, str], None]):
        """Устанавливает callback для ошибок"""
        self.on_error = callback
    
    def _notify_connection_changed(self):
        """Уведомляет о изменении состояния соединения"""
        if self.on_connection_changed:
            try:
                self.on_connection_changed(self.connection_state)
            except Exception as e:
                logger.error(f"❌ Ошибка в callback соединения: {e}")
    
    def _notify_error(self, error: Exception, context: str):
        """Уведомляет об ошибке"""
        if self.on_error:
            try:
                self.on_error(error, context)
            except Exception as e:
                logger.error(f"❌ Ошибка в error callback: {e}")
    
    async def stream_audio(self, prompt: str, screenshot_base64: str, screen_info: dict, hardware_id: str):
        """Стриминг аудио и текста на сервер"""
        try:
            # Отладочная информация
            logger.info(f"🔍 screen_info type: {type(screen_info)}")
            logger.info(f"🔍 screen_info content: {screen_info}")
            
            if not self.is_connected():
                await self.connect()
            
            # Импортируем необходимые модули
            import streaming_pb2_grpc
            import streaming_pb2
            
            # Создаем запрос
            # Проверяем тип screen_info и извлекаем данные
            if hasattr(screen_info, 'get'):
                # Это словарь
                screen_width = screen_info.get('width')
                screen_height = screen_info.get('height')
            elif hasattr(screen_info, 'width') and hasattr(screen_info, 'height'):
                # Это объект с атрибутами width и height
                screen_width = screen_info.width
                screen_height = screen_info.height
            else:
                # Неизвестный тип, используем значения по умолчанию
                logger.warning(f"⚠️ Неизвестный тип screen_info: {type(screen_info)}, используем значения по умолчанию")
                screen_width = None
                screen_height = None
            
            request = streaming_pb2.StreamRequest(
                prompt=prompt,
                screenshot=screenshot_base64,
                screen_width=screen_width,
                screen_height=screen_height,
                hardware_id=hardware_id,
                session_id=None  # Опциональное поле
            )
            
            # Выполняем стриминг
            async for response in streaming_pb2_grpc.StreamingServiceStub(self.channel).StreamAudio(
                request,
                timeout=30
            ):
                yield response
                
        except Exception as e:
            logger.error(f"❌ Ошибка стриминга аудио: {e}")
            raise
    
    async def cleanup(self):
        """Очистка ресурсов"""
        try:
            if self.health_check_task and not self.health_check_task.done():
                self.health_check_task.cancel()
                try:
                    await self.health_check_task
                except asyncio.CancelledError:
                    pass
            
            await self.disconnect()
            logger.info("🧹 ImprovedGrpcClient очищен")
        except Exception as e:
            handle_network_error(e, "ImprovedGrpcClient", "cleanup", "Очистка ресурсов")

class RetryManager:
    """Менеджер повторных попыток"""
    
    def __init__(self, max_attempts: int = 3, base_delay: float = 1.0, strategy: RetryStrategy = RetryStrategy.EXPONENTIAL):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.strategy = strategy
    
    async def execute_with_retry(self, operation: Callable, *args, **kwargs) -> Any:
        """Выполняет операцию с retry"""
        last_exception = None
        
        for attempt in range(self.max_attempts):
            try:
                return await operation(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if attempt < self.max_attempts - 1:
                    delay = self._calculate_delay(attempt)
                    logger.warning(f"⚠️ Попытка {attempt + 1} неудачна, повтор через {delay:.2f}с: {e}")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"❌ Все {self.max_attempts} попыток неудачны")
        
        raise last_exception
    
    def _calculate_delay(self, attempt: int) -> float:
        """Вычисляет задержку для следующей попытки"""
        if self.strategy == RetryStrategy.LINEAR:
            return self.base_delay * (attempt + 1)
        elif self.strategy == RetryStrategy.EXPONENTIAL:
            return self.base_delay * (2 ** attempt)
        elif self.strategy == RetryStrategy.FIBONACCI:
            return self.base_delay * self._fibonacci(attempt + 1)
        else:
            return self.base_delay
    
    def _fibonacci(self, n: int) -> int:
        """Вычисляет n-е число Фибоначчи"""
        if n <= 1:
            return n
        return self._fibonacci(n - 1) + self._fibonacci(n - 2)

def create_improved_grpc_client(config: Optional[Dict[str, Any]] = None) -> ImprovedGrpcClient:
    """Создает экземпляр ImprovedGrpcClient"""
    return ImprovedGrpcClient(config)

def create_default_config() -> Dict[str, Any]:
    """Создает конфигурацию по умолчанию"""
    return {
        'servers': {
            'local': {
                'address': '127.0.0.1',
                'port': 50051,
                'use_ssl': False,
                'timeout': 30,
                'retry_attempts': 3,
                'retry_delay': 1.0
            },
            'production': {
                'address': '20.151.51.172',
                'port': 50051,
                'use_ssl': False,
                'timeout': 120,
                'retry_attempts': 5,
                'retry_delay': 2.0
            }
        },
        'auto_fallback': True,
        'health_check_interval': 30,
        'connection_timeout': 10,
        'max_retry_attempts': 3,
        'retry_strategy': 'exponential',
        'circuit_breaker_threshold': 5,
        'circuit_breaker_timeout': 60
    }
