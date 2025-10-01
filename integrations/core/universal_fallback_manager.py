"""
Универсальный менеджер fallback для всех модулей
"""

import time
import logging
from typing import List, Dict, Any, Optional, AsyncGenerator
from integrations.core.universal_provider_interface import UniversalProviderInterface, ProviderStatus

logger = logging.getLogger(__name__)

class UniversalFallbackManager:
    """
    Универсальный менеджер fallback логики
    
    Управляет переключением между провайдерами при ошибках,
    реализует circuit breaker паттерн и обеспечивает
    единообразное поведение fallback во всех модулях.
    """
    
    def __init__(self, module_name: str, config: Optional[Dict[str, Any]] = None):
        """
        Инициализация менеджера fallback
        
        Args:
            module_name: Имя модуля
            config: Конфигурация менеджера
        """
        self.module_name = module_name
        self.config = config or {}
        
        # Провайдеры
        self.providers: List[UniversalProviderInterface] = []
        self.circuit_breakers: Dict[str, bool] = {}
        
        # Настройки circuit breaker
        self.failure_threshold = self.config.get('circuit_breaker_threshold', 3)
        self.recovery_timeout = self.config.get('circuit_breaker_timeout', 300)  # 5 минут
        self.timeout = self.config.get('timeout', 30)
        
        # Метрики
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.fallback_switches = 0
        
        logger.info(f"UniversalFallbackManager created for {module_name}")
    
    def register_providers(self, providers: List[UniversalProviderInterface]):
        """
        Регистрация провайдеров
        
        Args:
            providers: Список провайдеров, отсортированных по приоритету
        """
        self.providers = sorted(providers, key=lambda p: p.priority)
        self.circuit_breakers = {provider.name: False for provider in providers}
        
        logger.info(f"Registered {len(providers)} providers for {self.module_name}")
        for provider in providers:
            logger.debug(f"  - {provider.name} (priority: {provider.priority})")
    
    async def process_with_fallback(self, input_data: Any) -> AsyncGenerator[Any, None]:
        """
        Обработка данных с fallback логикой
        
        Args:
            input_data: Входные данные для обработки
            
        Yields:
            Результаты обработки от доступных провайдеров
        """
        self.total_requests += 1
        
        for i, provider in enumerate(self.providers):
            try:
                # Проверяем circuit breaker
                if self.circuit_breakers.get(provider.name, False):
                    if await self._should_reset_circuit_breaker(provider):
                        self._reset_circuit_breaker(provider)
                    else:
                        logger.debug(f"Circuit breaker open for {provider.name}, skipping")
                        continue
                
                # Проверяем здоровье провайдера
                if not await provider.health_check():
                    logger.warning(f"Provider {provider.name} health check failed")
                    continue
                
                # Инициализируем провайдер если нужно
                if not provider.is_initialized:
                    logger.info(f"Initializing provider {provider.name}")
                    if not await provider.initialize():
                        logger.error(f"Failed to initialize provider {provider.name}")
                        continue
                
                # Обрабатываем данные
                logger.debug(f"Processing with provider {provider.name}")
                result_count = 0
                
                async for result in provider.process(input_data):
                    result_count += 1
                    yield result
                
                # Если получили результат - успех
                if result_count > 0:
                    self.successful_requests += 1
                    provider.report_success()
                    logger.debug(f"Successfully processed with provider {provider.name}")
                    return
                else:
                    raise Exception("No results from provider")
                    
            except Exception as e:
                logger.warning(f"Provider {provider.name} failed: {e}")
                provider.report_error(str(e))
                
                # Проверяем circuit breaker
                if provider.error_count >= self.failure_threshold:
                    self._open_circuit_breaker(provider)
                
                # Если это не последний провайдер - переключаемся
                if i < len(self.providers) - 1:
                    self.fallback_switches += 1
                    logger.info(f"Switching to fallback provider (attempt {i + 1}/{len(self.providers)})")
                    continue
                else:
                    # Все провайдеры failed
                    logger.error(f"All providers failed for {self.module_name}")
                    break
        
        # Если дошли сюда - все провайдеры failed
        self.failed_requests += 1
        yield f"Error: All {self.module_name} services are currently unavailable."
    
    async def _should_reset_circuit_breaker(self, provider: UniversalProviderInterface) -> bool:
        """
        Проверка, нужно ли сбросить circuit breaker
        
        Args:
            provider: Провайдер для проверки
            
        Returns:
            True если circuit breaker нужно сбросить
        """
        if provider.last_success is None:
            return True
            
        time_since_success = time.time() - provider.last_success
        return time_since_success >= self.recovery_timeout
    
    def _reset_circuit_breaker(self, provider: UniversalProviderInterface):
        """
        Сброс circuit breaker для провайдера
        
        Args:
            provider: Провайдер для сброса
        """
        self.circuit_breakers[provider.name] = False
        provider.reset_metrics()
        logger.info(f"Circuit breaker reset for {provider.name}")
    
    def _open_circuit_breaker(self, provider: UniversalProviderInterface):
        """
        Открытие circuit breaker для провайдера
        
        Args:
            provider: Провайдер для отключения
        """
        self.circuit_breakers[provider.name] = True
        provider.status = ProviderStatus.FAILED
        logger.warning(f"Circuit breaker opened for {provider.name}")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Получение статуса менеджера fallback
        
        Returns:
            Словарь со статусом менеджера
        """
        provider_statuses = {}
        for provider in self.providers:
            provider_statuses[provider.name] = {
                "status": provider.status.value,
                "circuit_breaker_open": self.circuit_breakers.get(provider.name, False),
                "error_count": provider.error_count,
                "last_error": provider.last_error,
                "last_success": provider.last_success
            }
        
        return {
            "module_name": self.module_name,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "fallback_switches": self.fallback_switches,
            "success_rate": (
                self.successful_requests / self.total_requests 
                if self.total_requests > 0 else 0
            ),
            "providers": provider_statuses,
            "config": {
                "failure_threshold": self.failure_threshold,
                "recovery_timeout": self.recovery_timeout,
                "timeout": self.timeout
            }
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Получение метрик менеджера fallback
        
        Returns:
            Словарь с метриками менеджера
        """
        return {
            "module_name": self.module_name,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "fallback_switches": self.fallback_switches,
            "success_rate": (
                self.successful_requests / self.total_requests 
                if self.total_requests > 0 else 0
            ),
            "active_providers": len([p for p in self.providers if not self.circuit_breakers.get(p.name, False)]),
            "failed_providers": len([p for p in self.providers if self.circuit_breakers.get(p.name, False)]),
            "provider_count": len(self.providers)
        }
    
    def reset_metrics(self):
        """Сброс метрик менеджера"""
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.fallback_switches = 0
        
        # Сбрасываем метрики всех провайдеров
        for provider in self.providers:
            provider.reset_metrics()
            self.circuit_breakers[provider.name] = False
        
        logger.info(f"Metrics reset for {self.module_name} fallback manager")
    
    def get_healthy_providers(self) -> List[UniversalProviderInterface]:
        """
        Получение списка здоровых провайдеров
        
        Returns:
            Список здоровых провайдеров
        """
        healthy_providers = []
        for provider in self.providers:
            if (not self.circuit_breakers.get(provider.name, False) and 
                provider.status != ProviderStatus.FAILED):
                healthy_providers.append(provider)
        return healthy_providers
    
    def get_failed_providers(self) -> List[UniversalProviderInterface]:
        """
        Получение списка failed провайдеров
        
        Returns:
            Список failed провайдеров
        """
        failed_providers = []
        for provider in self.providers:
            if (self.circuit_breakers.get(provider.name, False) or 
                provider.status == ProviderStatus.FAILED):
                failed_providers.append(provider)
        return failed_providers
    
    def __str__(self) -> str:
        """Строковое представление менеджера"""
        return f"FallbackManager({self.module_name}, providers={len(self.providers)})"
    
    def __repr__(self) -> str:
        """Представление менеджера для отладки"""
        return (
            f"UniversalFallbackManager("
            f"module_name='{self.module_name}', "
            f"providers={len(self.providers)}, "
            f"requests={self.total_requests}, "
            f"success_rate={self.successful_requests / self.total_requests if self.total_requests > 0 else 0:.2f}"
            f")"
        )
