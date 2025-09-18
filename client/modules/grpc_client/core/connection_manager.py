"""
Менеджер gRPC соединений
"""

import asyncio
import logging
import time
from typing import Optional, Dict, Any
import grpc
import grpc.aio

from .types import ConnectionState, ServerConfig, ConnectionMetrics
from .health_checker import HealthChecker

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Менеджер gRPC соединений"""
    
    def __init__(self):
        self.servers: Dict[str, ServerConfig] = {}
        self.current_server: Optional[str] = None
        self.connection_state = ConnectionState.DISCONNECTED
        self.metrics = ConnectionMetrics()
        
        # gRPC компоненты
        self.channel: Optional[grpc.aio.Channel] = None
        self.stub: Optional[Any] = None
        
        # Thread safety
        self._connection_lock = asyncio.Lock()
        
        # Health checker
        self.health_checker = HealthChecker()
        
        # Callbacks
        self.on_connection_changed: Optional[callable] = None
        self.on_error: Optional[callable] = None
    
    def add_server(self, name: str, config: ServerConfig):
        """Добавляет сервер в конфигурацию"""
        self.servers[name] = config
        if not self.current_server:
            self.current_server = name
        logger.info(f"🌐 Добавлен сервер {name}: {config.address}:{config.port}")
    
    async def connect(self, server_name: Optional[str] = None) -> bool:
        """Подключается к серверу"""
        try:
            async with self._connection_lock:
                if server_name and server_name in self.servers:
                    self.current_server = server_name
                
                return await self._connect()
        except Exception as e:
            logger.error(f"❌ Ошибка подключения: {e}")
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
            options = self._create_grpc_options(server_config)
            
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
                    timeout=server_config.timeout
                )
                
                self.connection_state = ConnectionState.CONNECTED
                self.metrics.successful_connections += 1
                self.metrics.last_connection_time = time.time()
                self._notify_connection_changed()
                
                # Запускаем health checker
                self.health_checker.start(self._check_connection_health)
                
                logger.info(f"✅ Подключение к {address} установлено")
                return True
                
            except asyncio.TimeoutError:
                logger.error(f"⏰ Таймаут подключения к {address}")
                self.connection_state = ConnectionState.FAILED
                self.metrics.failed_connections += 1
                self._notify_connection_changed()
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка подключения: {e}")
            self.connection_state = ConnectionState.FAILED
            self.metrics.failed_connections += 1
            self.metrics.last_error = str(e)
            self._notify_connection_changed()
            return False
    
    def _create_grpc_options(self, server_config: ServerConfig) -> list:
        """Создает опции gRPC"""
        # Консервативные keepalive-настройки, чтобы избежать ENHANCE_YOUR_CALM/too_many_pings
        return [
            ('grpc.max_send_message_length', server_config.max_message_size),
            ('grpc.max_receive_message_length', server_config.max_message_size),
            ('grpc.max_metadata_size', 1024 * 1024),
            ('grpc.keepalive_time_ms', max(60000, server_config.keep_alive_time * 1000)),  # >= 60s
            ('grpc.keepalive_timeout_ms', max(5000, server_config.keep_alive_timeout * 1000)),
            ('grpc.keepalive_permit_without_calls', server_config.keep_alive_permit_without_calls),
            ('grpc.http2.max_pings_without_data', 1),
            ('grpc.http2.min_time_between_pings_ms', 60000),
            ('grpc.http2.min_ping_interval_without_data_ms', 600000),
        ]
    
    def _create_stub(self):
        """Создает gRPC stub (должен быть переопределен в наследниках)"""
        # Это базовый класс, stub создается в наследниках
        return None
    
    def _check_connection_health(self) -> bool:
        """Проверяет здоровье соединения"""
        try:
            if self.channel:
                state = self.channel.get_state()
                return state == grpc.ChannelConnectivity.READY
            return False
        except Exception:
            return False
    
    async def disconnect(self):
        """Отключается от сервера"""
        try:
            async with self._connection_lock:
                # Останавливаем health checker
                self.health_checker.stop()
                
                if self.channel:
                    await self.channel.close()
                    self.channel = None
                    self.stub = None
                
                self.connection_state = ConnectionState.DISCONNECTED
                self._notify_connection_changed()
                logger.info("🔌 Отключение от сервера")
        except Exception as e:
            logger.error(f"❌ Ошибка отключения: {e}")
    
    async def reconnect(self) -> bool:
        """Переподключается к серверу"""
        try:
            logger.info("🔄 Переподключение к серверу...")
            await self.disconnect()
            await asyncio.sleep(1)  # Короткая пауза
            return await self._connect()
        except Exception as e:
            logger.error(f"❌ Ошибка переподключения: {e}")
            return False
    
    async def switch_server(self, server_name: str) -> bool:
        """Переключается на другой сервер"""
        try:
            if server_name not in self.servers:
                logger.error(f"❌ Сервер {server_name} не найден")
                return False
            
            logger.info(f"🔄 Переключение на сервер {server_name}")
            self.current_server = server_name
            return await self.reconnect()
        except Exception as e:
            logger.error(f"❌ Ошибка переключения сервера: {e}")
            return False
    
    def get_connection_state(self) -> ConnectionState:
        """Возвращает текущее состояние соединения"""
        return self.connection_state
    
    def get_metrics(self) -> ConnectionMetrics:
        """Возвращает метрики соединения"""
        return self.metrics
    
    def is_connected(self) -> bool:
        """Проверяет, подключен ли клиент"""
        return self.connection_state == ConnectionState.CONNECTED
    
    def set_connection_callback(self, callback: callable):
        """Устанавливает callback для изменений состояния соединения"""
        self.on_connection_changed = callback
    
    def set_error_callback(self, callback: callable):
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
    
    async def cleanup(self):
        """Очистка ресурсов"""
        try:
            self.health_checker.stop()
            await self.disconnect()
            logger.info("🧹 ConnectionManager очищен")
        except Exception as e:
            logger.error(f"❌ Ошибка очистки ConnectionManager: {e}")
