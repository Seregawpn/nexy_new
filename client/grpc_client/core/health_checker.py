"""
Система проверки здоровья gRPC соединения
"""

import asyncio
import logging
import time
from typing import Optional, Callable
from .types import ConnectionState, HealthCheckConfig

logger = logging.getLogger(__name__)


class HealthChecker:
    """Система проверки здоровья соединения"""
    
    def __init__(self, config: HealthCheckConfig = None):
        self.config = config or HealthCheckConfig()
        self.task: Optional[asyncio.Task] = None
        self.failure_count = 0
        self.last_check_time = 0.0
        self.is_healthy = True
        
        # Callbacks
        self.on_health_changed: Optional[Callable[[bool], None]] = None
        self.on_connection_lost: Optional[Callable[[], None]] = None
    
    def start(self, check_function: Callable[[], bool]):
        """Запускает health checker"""
        if not self.config.enabled:
            logger.info("🔍 Health checker отключен")
            return
        
        if self.task and not self.task.done():
            logger.warning("⚠️ Health checker уже запущен")
            return
        
        self.check_function = check_function
        self.task = asyncio.create_task(self._health_check_loop())
        logger.info("🔍 Health checker запущен")
    
    def stop(self):
        """Останавливает health checker"""
        if self.task and not self.task.done():
            self.task.cancel()
            logger.info("🔍 Health checker остановлен")
    
    async def _health_check_loop(self):
        """Основной цикл проверки здоровья"""
        while True:
            try:
                await asyncio.sleep(self.config.interval)
                await self._perform_health_check()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Ошибка в health check loop: {e}")
                await asyncio.sleep(5)  # Короткая пауза при ошибке
    
    async def _perform_health_check(self):
        """Выполняет проверку здоровья"""
        try:
            start_time = time.time()
            is_healthy = self.check_function()
            check_duration = time.time() - start_time
            
            self.last_check_time = time.time()
            
            if is_healthy:
                if not self.is_healthy:
                    logger.info("✅ Соединение восстановлено")
                    self.is_healthy = True
                    self.failure_count = 0
                    if self.on_health_changed:
                        self.on_health_changed(True)
            else:
                self.failure_count += 1
                logger.warning(f"⚠️ Health check неудачен ({self.failure_count}/{self.config.max_failures})")
                
                if self.failure_count >= self.config.max_failures:
                    if self.is_healthy:
                        logger.error("❌ Соединение потеряно")
                        self.is_healthy = False
                        if self.on_health_changed:
                            self.on_health_changed(False)
                        if self.on_connection_lost:
                            self.on_connection_lost()
                else:
                    # Сброс счетчика при частичном восстановлении
                    if self.failure_count >= self.config.recovery_threshold:
                        self.failure_count = 0
            
        except Exception as e:
            logger.error(f"❌ Ошибка health check: {e}")
            self.failure_count += 1
    
    def get_status(self) -> dict:
        """Возвращает статус health checker"""
        return {
            "enabled": self.config.enabled,
            "is_healthy": self.is_healthy,
            "failure_count": self.failure_count,
            "last_check_time": self.last_check_time,
            "is_running": self.task is not None and not self.task.done()
        }
    
    def set_health_changed_callback(self, callback: Callable[[bool], None]):
        """Устанавливает callback для изменений здоровья"""
        self.on_health_changed = callback
    
    def set_connection_lost_callback(self, callback: Callable[[], None]):
        """Устанавливает callback для потери соединения"""
        self.on_connection_lost = callback
