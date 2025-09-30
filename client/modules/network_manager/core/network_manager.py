"""
NetworkManager Module - Мониторинг состояния сети
Асинхронный модуль для проверки подключения и качества сети
"""

import asyncio
import time
import logging
from typing import Optional, Callable, Dict, Any, List
from pathlib import Path
import sys

# Пути уже добавлены в main.py - не дублируем

from .types import (
    NetworkStatus,
    NetworkQuality,
    ConnectionType,
    NetworkConfig,
    NetworkMetrics,
    NetworkDiagnostic,
    NetworkTestResult,
    NetworkEvent,
    NetworkManagerState
)
from .config import NetworkManagerConfig
from config.unified_config_loader import unified_config

logger = logging.getLogger(__name__)

class NetworkManager:
    """Менеджер сети для мониторинга подключения и качества"""
    
    def __init__(self, config: Optional[NetworkManagerConfig] = None):
        self.config = config or self._get_config_from_unified()
        self.state = NetworkManagerState()
        self.state.config = self.config.to_network_config()
        
        # Состояние работы
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None
        
        # Callbacks
        self._callbacks: List[Callable[[NetworkEvent], None]] = []
        
    def _get_config_from_unified(self) -> NetworkManagerConfig:
        """Загружает конфигурацию из unified_config.yaml"""
        try:
            config_data = unified_config._load_config()
            network_config = config_data.get('network_manager', {})
            return NetworkManagerConfig.from_unified_config(network_config)
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки конфигурации network_manager: {e}")
            return NetworkManagerConfig()
        
        logger.info(f"NetworkManager initialized with config: {self.config}")
    
    async def initialize(self) -> bool:
        """Инициализация NetworkManager"""
        try:
            logger.info("Initializing NetworkManager...")
            await self._check_connectivity()
            logger.info("NetworkManager initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize NetworkManager: {e}")
            return False
    
    async def start(self) -> bool:
        """Запуск мониторинга сети"""
        if self._running:
            return True
        
        try:
            logger.info("Starting NetworkManager monitoring...")
            self._running = True
            self._monitor_task = asyncio.create_task(self._monitor_loop())
            logger.info("NetworkManager monitoring started")
            return True
        except Exception as e:
            logger.error(f"Failed to start NetworkManager: {e}")
            self._running = False
            return False
    
    async def stop(self) -> bool:
        """Остановка мониторинга сети"""
        if not self._running:
            return True
        
        try:
            logger.info("Stopping NetworkManager monitoring...")
            self._running = False
            
            if self._monitor_task:
                self._monitor_task.cancel()
                try:
                    await self._monitor_task
                except asyncio.CancelledError:
                    pass
                self._monitor_task = None
            
            logger.info("NetworkManager monitoring stopped")
            return True
        except Exception as e:
            logger.error(f"Failed to stop NetworkManager: {e}")
            return False
    
    def add_callback(self, callback: Callable[[NetworkEvent], None]):
        """Добавить callback для событий сети"""
        self._callbacks.append(callback)
        logger.debug(f"Added network callback: {callback.__name__}")
    
    async def _monitor_loop(self):
        """Основной цикл мониторинга сети"""
        logger.info("Network monitoring loop started")
        
        while self._running:
            try:
                await self._check_connectivity()
                await self._update_metrics()
                await asyncio.sleep(self.config.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in network monitoring loop: {e}")
                await asyncio.sleep(5)
        
        logger.info("Network monitoring loop stopped")
    
    async def _check_connectivity(self) -> bool:
        """Проверка подключения к сети"""
        start_time = time.time()
        is_connected = False
        
        for host in self.config.ping_hosts:
            try:
                if await self._test_tcp_connection(host, 53, self.config.ping_timeout):
                    is_connected = True
                    break
            except Exception as e:
                logger.debug(f"Connection test failed for {host}: {e}")
                continue
        
        new_status = NetworkStatus.CONNECTED if is_connected else NetworkStatus.DISCONNECTED
        old_status = self.state.update_status(new_status)
        
        if old_status != new_status:
            await self._emit_status_change(old_status, new_status, {
                'connected': is_connected,
                'test_duration': time.time() - start_time,
                'tested_hosts': self.config.ping_hosts
            })
        
        return is_connected
    
    async def _test_tcp_connection(self, host: str, port: int, timeout: float) -> bool:
        """Тест TCP подключения"""
        try:
            future = asyncio.open_connection(host, port)
            reader, writer = await asyncio.wait_for(future, timeout=timeout)
            writer.close()
            if hasattr(writer, 'wait_closed'):
                await writer.wait_closed()
            return True
        except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
            return False
        except Exception as e:
            logger.debug(f"TCP connection test error for {host}:{port}: {e}")
            return False
    
    async def _update_metrics(self):
        """Обновление метрик сети"""
        if self.state.current_status != NetworkStatus.CONNECTED:
            return
        
        ping_time = await self._measure_ping_time()
        new_metrics = NetworkMetrics(
            ping_time=ping_time,
            last_updated=time.time()
        )
        
        self.state.update_metrics(new_metrics)
        
        new_quality = self._calculate_network_quality(ping_time)
        if self.state.update_quality(new_quality):
            await self._emit_quality_change(new_quality)
    
    async def _measure_ping_time(self) -> float:
        """Измерение времени пинга"""
        if not self.config.ping_hosts:
            return 0.0
        
        host = self.config.ping_hosts[0]
        try:
            start_time = time.time()
            if await self._test_tcp_connection(host, 53, self.config.ping_timeout):
                return (time.time() - start_time) * 1000
        except Exception:
            pass
        return 0.0
    
    def _calculate_network_quality(self, ping_time: float) -> NetworkQuality:
        """Вычисление качества сети на основе ping"""
        if ping_time == 0:
            return NetworkQuality.UNKNOWN
        elif ping_time < 50:
            return NetworkQuality.EXCELLENT
        elif ping_time < 100:
            return NetworkQuality.GOOD
        elif ping_time < 200:
            return NetworkQuality.FAIR
        elif ping_time < 500:
            return NetworkQuality.POOR
        else:
            return NetworkQuality.VERY_POOR
    
    async def _emit_status_change(self, old_status: NetworkStatus, new_status: NetworkStatus, details: Dict[str, Any]):
        """Отправка события изменения статуса"""
        event = NetworkEvent(
            event_type="network.status_changed",
            old_status=old_status,
            new_status=new_status,
            details=details,
            timestamp=time.time()
        )
        
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                logger.error(f"Error in network callback: {e}")
        
        old_status_str = old_status.value if old_status and hasattr(old_status, 'value') else 'None'
        new_status_str = new_status.value if new_status and hasattr(new_status, 'value') else 'None'
        logger.info(f"Network status changed: {old_status_str} -> {new_status_str}")
    
    async def _emit_quality_change(self, new_quality: NetworkQuality):
        """Отправка события изменения качества"""
        if new_quality is None:
            logger.error("new_quality is None in _emit_quality_change")
            return
            
        event = NetworkEvent(
            event_type="network.quality_changed",
            old_status=self.state.current_status or NetworkStatus.UNKNOWN,
            new_status=self.state.current_status or NetworkStatus.UNKNOWN,
            details={'quality': new_quality.value if hasattr(new_quality, 'value') else str(new_quality)},
            timestamp=time.time()
        )
        
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                logger.error(f"Error in network callback: {e}")
                logger.error(f"Event details: {event}")
                logger.error(f"Callback: {callback}")
        
        logger.debug(f"Network quality changed: {new_quality.value if hasattr(new_quality, 'value') else str(new_quality)}")
    
    def get_status(self) -> Dict[str, Any]:
        """Получить текущий статус сети"""
        return {
            'status': self.state.current_status.value,
            'quality': self.state.network_quality.value,
            'connection_type': self.state.connection_type.value,
            'metrics': {
                'ping_time': self.state.metrics.ping_time,
                'last_updated': self.state.metrics.last_updated
            },
            'is_monitoring': self._running,
            'config': {
                'check_interval': self.config.check_interval,
                'ping_timeout': self.config.ping_timeout,
                'ping_hosts': self.config.ping_hosts
            }
        }
    
    def get_diagnostic(self) -> NetworkDiagnostic:
        """Получить диагностику сети"""
        test_results = []
        for host in self.config.ping_hosts:
            test_results.append(NetworkTestResult(
                success=self.state.current_status == NetworkStatus.CONNECTED,
                test_type="tcp_ping",
                duration=self.config.ping_timeout,
                details={'host': host}
            ))
        
        issues = []
        recommendations = []
        
        if self.state.current_status == NetworkStatus.DISCONNECTED:
            issues.append("No network connectivity")
            recommendations.append("Check network connection")
        elif self.state.network_quality == NetworkQuality.POOR:
            issues.append("Poor network quality")
            recommendations.append("Check network stability")
        
        return NetworkDiagnostic(
            overall_status=self.state.current_status,
            connectivity_tests=test_results,
            network_quality=self.state.network_quality,
            connection_type=self.state.connection_type,
            metrics=self.state.metrics,
            issues=issues,
            recommendations=recommendations
        )
    
    async def force_check(self) -> bool:
        """Принудительная проверка сети"""
        logger.info("Forcing network check...")
        return await self._check_connectivity()
    
    def is_connected(self) -> bool:
        """Проверить, подключена ли сеть"""
        return self.state.current_status == NetworkStatus.CONNECTED
    
    def get_connection_quality(self) -> NetworkQuality:
        """Получить качество соединения"""
        return self.state.network_quality
