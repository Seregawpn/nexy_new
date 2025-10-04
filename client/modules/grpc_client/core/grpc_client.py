"""
Основной gRPC клиент с модульной архитектурой
"""

import asyncio
import logging
from typing import Optional, Dict, Any, AsyncGenerator, Tuple, List
import importlib
import sys
from pathlib import Path
from datetime import datetime

import numpy as np

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
        
        # Устанавливаем сервер по умолчанию из конфигурации
        self._set_default_server()
    
    def _create_default_config(self) -> Dict[str, Any]:
        """Создает конфигурацию по умолчанию из централизованной системы"""
        try:
            # Загружаем конфигурацию из unified_config.yaml
            import yaml
            with open('config/unified_config.yaml', 'r') as f:
                config = yaml.safe_load(f)
            
            grpc_data = config.get('grpc', {})
            servers_config = grpc_data.get('servers', {})
            
            # Преобразуем конфигурацию в формат, ожидаемый GrpcClient
            servers = {}
            for server_name, server_config in servers_config.items():
                servers[server_name] = {
                    'address': server_config.get('host', '127.0.0.1'),
                    'port': server_config.get('port', 50051),
                    'use_ssl': server_config.get('ssl', False),
                    'timeout': server_config.get('timeout', grpc_data.get('connection_timeout', 30)),
                    'retry_attempts': server_config.get('retry_attempts', grpc_data.get('retry_attempts', 3)),
                    'retry_delay': server_config.get('retry_delay', grpc_data.get('retry_delay', 1.0))
                }
            
            return {
                'servers': servers,
                'auto_fallback': True,
                'health_check_interval': 30,
                'connection_timeout': grpc_data.get('connection_timeout', 10),
                'max_retry_attempts': grpc_data.get('retry_attempts', 3),
                'retry_strategy': 'exponential',
                'circuit_breaker_threshold': 5,
                'circuit_breaker_timeout': 60,
                'welcome_timeout_sec': 30.0
            }
            
        except Exception as e:
            logger.warning(f"⚠️ Не удалось загрузить централизованную конфигурацию: {e}")
            # Fallback к минимальной конфигурации
            return {
                'servers': {
                    'local': {
                        'address': '127.0.0.1',
                        'port': 50051,
                        'use_ssl': False,
                        'timeout': 30,
                        'retry_attempts': 3,
                        'retry_delay': 1.0
                    }
                },
                'auto_fallback': True,
                'health_check_interval': 30,
                'connection_timeout': 10,
                'max_retry_attempts': 3,
                'retry_strategy': 'exponential',
                'circuit_breaker_threshold': 5,
                'circuit_breaker_timeout': 60,
                'welcome_timeout_sec': 30.0
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
    
    def _set_default_server(self):
        """Устанавливает сервер по умолчанию из конфигурации"""
        try:
            # Пытаемся получить сервер из unified_config.yaml
            import yaml
            with open('config/unified_config.yaml', 'r') as f:
                config = yaml.safe_load(f)
            
            # Получаем настройки gRPC клиента из секции integrations
            integrations = config.get('integrations', {})
            grpc_config = integrations.get('grpc_client', {})
            default_server = grpc_config.get('server', 'local')
            
            # Устанавливаем сервер по умолчанию
            if default_server in self.connection_manager.servers:
                self.connection_manager.current_server = default_server
                logger.info(f"🌐 Установлен сервер по умолчанию: {default_server}")
            else:
                logger.warning(f"⚠️ Сервер '{default_server}' не найден, используем 'local'")
                self.connection_manager.current_server = 'local'
                
        except Exception as e:
            logger.warning(f"⚠️ Не удалось загрузить конфигурацию gRPC: {e}")
            # Используем local по умолчанию
            self.connection_manager.current_server = 'local'
    
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

    async def generate_welcome_audio(
        self,
        text: str,
        *,
        voice: Optional[str] = None,
        language: Optional[str] = None,
        session_id: Optional[str] = None,
        timeout: Optional[float] = None,
        server_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Запрашивает серверную генерацию приветственного аудио.

        Returns dict c numpy массивом аудио и метаданными.
        """
        if not text or not text.strip():
            raise ValueError("Welcome text must be non-empty")

        target_server = server_name or self.connection_manager.current_server

        if not self.is_connected():
            await self.connect(target_server)
        elif server_name and self.connection_manager.current_server != server_name:
            await self.connection_manager.switch_server(server_name)

        streaming_pb2, streaming_pb2_grpc = self._import_proto_modules()

        request = streaming_pb2.WelcomeRequest(
            text=text,
            session_id=session_id or f"welcome_{datetime.now().timestamp()}",
        )

        if voice:
            request.voice = voice
        if language:
            request.language = language

        stub = streaming_pb2_grpc.StreamingServiceStub(self.connection_manager.channel)
        rpc_timeout = timeout or self.config.get('welcome_timeout_sec', 30.0)

        audio_chunks: List[bytes] = []
        metadata: Dict[str, Any] = {}
        chunk_dtype: Optional[str] = None

        try:
            async for response in stub.GenerateWelcomeAudio(request, timeout=rpc_timeout):
                content = response.WhichOneof('content')
                if content == 'audio_chunk':
                    chunk = response.audio_chunk
                    if chunk.audio_data:
                        audio_bytes = bytes(chunk.audio_data)
                        if audio_bytes:
                            audio_chunks.append(audio_bytes)
                            chunk_dtype = chunk.dtype or chunk_dtype
                elif content == 'metadata':
                    metadata = {
                        'method': response.metadata.method,
                        'duration_sec': response.metadata.duration_sec,
                        'sample_rate': response.metadata.sample_rate,
                        'channels': response.metadata.channels,
                    }
                elif content == 'error_message':
                    raise RuntimeError(response.error_message)
                elif content == 'end_message':
                    break

        except Exception as e:
            logger.error(f"❌ Ошибка генерации приветственного аудио: {e}")
            raise

        if not audio_chunks:
            raise RuntimeError("Server returned no audio data")

        raw_bytes = b''.join(audio_chunks)
        dtype = (chunk_dtype or 'int16').lower()

        if dtype not in ('int16', 'pcm_s16le', 'short'):
            logger.warning(f"⚠️ Неподдерживаемый dtype '{dtype}', привожу к int16")
            dtype = 'int16'

        np_dtype = np.int16
        audio_array = np.frombuffer(raw_bytes, dtype=np_dtype)

        if metadata.get('channels', 1) > 1:
            try:
                audio_array = audio_array.reshape(-1, metadata['channels'])
            except Exception:
                logger.warning("⚠️ Не удалось изменить форму аудио по каналам, оставляю одномерный массив")

        result = {
            'audio': audio_array,
            'metadata': {
                'method': metadata.get('method', 'server'),
                'duration_sec': metadata.get('duration_sec'),
                'sample_rate': metadata.get('sample_rate', 48000),
                'channels': metadata.get('channels', 1),
                'dtype': 'int16',
            }
        }

        return result

    async def cleanup(self):
        """Очистка ресурсов"""
        try:
            await self.connection_manager.cleanup()
            logger.info("🧹 GrpcClient очищен")
        except Exception as e:
            logger.error(f"❌ Ошибка очистки GrpcClient: {e}")

    def _import_proto_modules(self) -> Tuple[Any, Any]:
        """Гибкий импорт streaming_pb2 и streaming_pb2_grpc.
        Сначала пробуем из proto директории модуля, затем fallback в server/.
        """
        # 1) Пытаемся импортировать из proto директории модуля
        try:
            # Путь: client/modules/grpc_client/proto/
            proto_dir = Path(__file__).resolve().parent.parent / 'proto'
            
            if proto_dir.exists() and str(proto_dir) not in sys.path:
                sys.path.insert(0, str(proto_dir))
                logger.info(f"✅ Добавлен путь к proto модулям: {proto_dir}")
            
            pb2 = importlib.import_module('streaming_pb2')
            pb2_grpc = importlib.import_module('streaming_pb2_grpc')
            logger.info("✅ Protobuf модули успешно импортированы из proto/")
            return pb2, pb2_grpc
        except Exception as local_err:
            logger.warning(f"⚠️ Не удалось импортировать из proto/: {local_err}")

        # 2) Пытаемся взять из server/ (репозиторий корень/ server)
        try:
            repo_root = Path(__file__).resolve().parents[4]
            server_dir = repo_root / 'server'
            
            # Проверяем существование и добавляем только если нужно
            if server_dir.exists() and str(server_dir) not in sys.path:
                sys.path.append(str(server_dir))
                logger.info(f"✅ Добавлен путь к server модулям: {server_dir}")
            
            pb2 = importlib.import_module('streaming_pb2')
            pb2_grpc = importlib.import_module('streaming_pb2_grpc')
            logger.info("✅ Protobuf модули успешно импортированы из server/")
            return pb2, pb2_grpc
        except Exception as e:
            raise ImportError(f"Unable to import protobuf modules (streaming_pb2*). Error: {e}")
