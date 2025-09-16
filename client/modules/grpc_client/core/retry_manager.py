"""
Менеджер повторных попыток для gRPC клиента
"""

import asyncio
import logging
import random
from typing import Callable, Any
from .types import RetryStrategy, RetryConfig

logger = logging.getLogger(__name__)


class RetryManager:
    """Менеджер повторных попыток с различными стратегиями"""
    
    def __init__(self, config: RetryConfig = None):
        self.config = config or RetryConfig()
    
    async def execute_with_retry(self, operation: Callable, *args, **kwargs) -> Any:
        """Выполняет операцию с retry механизмом"""
        last_exception = None
        
        for attempt in range(self.config.max_attempts):
            try:
                return await operation(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if attempt < self.config.max_attempts - 1:
                    delay = self._calculate_delay(attempt)
                    logger.warning(f"⚠️ Попытка {attempt + 1} неудачна, повтор через {delay:.2f}с: {e}")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"❌ Все {self.config.max_attempts} попыток неудачны")
        
        raise last_exception
    
    def _calculate_delay(self, attempt: int) -> float:
        """Вычисляет задержку для следующей попытки"""
        if self.config.strategy == RetryStrategy.LINEAR:
            delay = self.config.base_delay * (attempt + 1)
        elif self.config.strategy == RetryStrategy.EXPONENTIAL:
            delay = self.config.base_delay * (2 ** attempt)
        elif self.config.strategy == RetryStrategy.FIBONACCI:
            delay = self.config.base_delay * self._fibonacci(attempt + 1)
        else:
            delay = self.config.base_delay
        
        # Ограничиваем максимальной задержкой
        delay = min(delay, self.config.max_delay)
        
        # Добавляем jitter для избежания thundering herd
        if self.config.jitter:
            jitter = random.uniform(0.1, 0.3) * delay
            delay += jitter
        
        return delay
    
    def _fibonacci(self, n: int) -> int:
        """Вычисляет n-е число Фибоначчи"""
        if n <= 1:
            return n
        return self._fibonacci(n - 1) + self._fibonacci(n - 2)
    
    def reset(self):
        """Сбрасывает состояние retry менеджера"""
        # В будущем можно добавить сброс счетчиков
        pass
