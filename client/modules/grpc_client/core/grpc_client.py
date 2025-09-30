"""
Основной gRPC клиент с модульной архитектурой
"""

import asyncio
import logging
from typing import Optional, Dict, Any, AsyncGenerator, Tuple
import importlib
import sys
from pathlib import Path

from .types import ServerConfig, RetryConfig, HealthCheckConfig, RetryStrategy
from .retry_manager import RetryManager
from .connection_manager import ConnectionManager

logger = logging.getLogger(__name__)


class GrpcClient:
    """Основной gRPC клиент с модульной архитектурой"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._create_default_config()
        
        # Модульные компоненты
        self.connection_manager = ConnectionManager()
        self.retry_manager = RetryManager(
            RetryConfig(
                max_attempts=self.config.get('max_retry_attempts', 3),
                base_delay=self.config.get('retry_delay', 1.0),
                strategy=RetryStrategy.EXPONENTIAL  # Используем enum вместо строки
            )
        )
        
        # Инициализация
        self._initialize_servers()
        self._setup_callbacks()
    
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
            'retry_strategy': 'exponential',
            'circuit_breaker_threshold': 5,
            'circuit_breaker_timeout': 60
        }
    
    def _initialize_servers(self):
        """Инициализирует конфигурации серверов"""
        try:
            servers_config = self.config.get('servers', {})
            for name, server_config in servers_config.items():
                config = ServerConfig(
                    address=server_config['address'],
                    port=server_config['port'],
                    use_ssl=server_config.get('use_ssl', False),
                    timeout=server_config.get('timeout', 30),
                    retry_attempts=server_config.get('retry_attempts', 3),
                    retry_delay=server_config.get('retry_delay', 1.0),
                    max_message_size=server_config.get('max_message_size', 50 * 1024 * 1024)
                )
                self.connection_manager.add_server(name, config)
            
            logger.info(f"🌐 Инициализировано {len(servers_config)} серверов")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации серверов: {e}")
    
    def _setup_callbacks(self):
        """Настраивает callback'и"""
        self.connection_manager.set_connection_callback(self._on_connection_changed)
        self.connection_manager.set_error_callback(self._on_error)
    
    def _on_connection_changed(self, state):
        """Обрабатывает изменения состояния соединения"""
        logger.info(f"🔄 Состояние соединения: {state.value}")
    
    def _on_error(self, error: Exception, context: str):
        """Обрабатывает ошибки"""
        logger.error(f"❌ Ошибка в {context}: {error}")
    
    async def connect(self, server_name: Optional[str] = None) -> bool:
        """Подключается к серверу"""
        return await self.connection_manager.connect(server_name)
    
    async def disconnect(self):
        """Отключается от сервера"""
        await self.connection_manager.disconnect()
    
    async def switch_server(self, server_name: str) -> bool:
        """Переключается на другой сервер"""
        return await self.connection_manager.switch_server(server_name)
    
    async def execute_with_retry(self, operation, *args, **kwargs):
        """Выполняет операцию с retry механизмом"""
        return await self.retry_manager.execute_with_retry(operation, *args, **kwargs)
    
    def get_connection_state(self):
        """Возвращает текущее состояние соединения"""
        return self.connection_manager.get_connection_state()
    
    def get_metrics(self):
        """Возвращает метрики соединения"""
        return self.connection_manager.get_metrics()
    
    def is_connected(self) -> bool:
        """Проверяет, подключен ли клиент"""
        return self.connection_manager.is_connected()
    
    async def stream_audio(self, prompt: str, screenshot_base64: str, screen_info: dict, hardware_id: str) -> AsyncGenerator[Any, None]:
        """Стриминг аудио и текста на сервер"""
        try:
            logger.info(f"🔍 screen_info type: {type(screen_info)}")
            logger.info(f"🔍 screen_info content: {screen_info}")
            
            if not self.is_connected():
                await self.connect()

            # Импортируем protobuf-модули с фолбэком на server/
            streaming_pb2, streaming_pb2_grpc = self._import_proto_modules()
            
            # Создаем запрос
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
                session_id=None
            )
            
            # Выполняем стриминг
            async for response in streaming_pb2_grpc.StreamingServiceStub(
                self.connection_manager.channel
            ).StreamAudio(request, timeout=30):
                yield response
                
        except Exception as e:
            logger.error(f"❌ Ошибка стриминга аудио: {e}")
            raise
    
    async def cleanup(self):
        """Очистка ресурсов"""
        try:
            await self.connection_manager.cleanup()
            logger.info("🧹 GrpcClient очищен")
        except Exception as e:
            logger.error(f"❌ Ошибка очистки GrpcClient: {e}")

    def _import_proto_modules(self) -> Tuple[Any, Any]:
        """Гибкий импорт streaming_pb2 и streaming_pb2_grpc.
        Сначала пробуем локальные модули, затем fallback в server/.
        """
        # 1) Пытаемся локально
        try:
            pb2 = importlib.import_module('streaming_pb2')
            pb2_grpc = importlib.import_module('streaming_pb2_grpc')
            return pb2, pb2_grpc
        except Exception:
            pass

        # 2) Пытаемся взять из server/ (репозиторий корень/ server)
        try:
            repo_root = Path(__file__).resolve().parents[4]
            server_dir = repo_root / 'server'
            
            # Проверяем существование и добавляем только если нужно
            if server_dir.exists() and str(server_dir) not in sys.path:
                sys.path.append(str(server_dir))
            
            pb2 = importlib.import_module('streaming_pb2')
            pb2_grpc = importlib.import_module('streaming_pb2_grpc')
            return pb2, pb2_grpc
        except Exception as e:
            raise ImportError(f"Unable to import protobuf modules (streaming_pb2*). Error: {e}")
