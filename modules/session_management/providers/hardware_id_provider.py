"""
Hardware ID Provider для получения и управления Hardware ID от клиентов
"""

import os
import logging
from typing import AsyncGenerator, Dict, Any, Optional
from integrations.core.universal_provider_interface import UniversalProviderInterface

logger = logging.getLogger(__name__)

class HardwareIDProvider(UniversalProviderInterface):
    """
    Провайдер для получения и управления Hardware ID от клиентов
    
    Получает Hardware ID от клиентской части и сохраняет их в базе данных.
    Не генерирует ID самостоятельно - только обрабатывает полученные от клиентов.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Инициализация Hardware ID провайдера
        
        Args:
            config: Конфигурация провайдера
        """
        super().__init__(
            name="hardware_id",
            priority=1,  # Основной провайдер
            config=config
        )
        
        # Настройки для работы с ID от клиентов
        self.require_hardware_id = config.get('require_hardware_id', True)
        self.validate_id_format = config.get('validate_id_format', True)
        
        # Хранилище полученных ID
        self.received_ids: Dict[str, Dict[str, Any]] = {}
        
        logger.info("HardwareID Provider initialized for client ID processing")
    
    async def initialize(self) -> bool:
        """
        Инициализация Hardware ID провайдера
        
        Returns:
            True если инициализация успешна, False иначе
        """
        try:
            logger.info("Initializing HardwareID Provider...")
            
            # Инициализируем хранилище для ID от клиентов
            self.received_ids.clear()
            
            self.is_initialized = True
            logger.info("HardwareID Provider initialized successfully - ready to receive client IDs")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize HardwareID Provider: {e}")
            return False
    
    async def process(self, input_data: Any) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Обработка Hardware ID от клиента
        
        Args:
            input_data: Словарь с данными от клиента, должен содержать 'hardware_id'
            
        Yields:
            Результат обработки Hardware ID
        """
        try:
            if not self.is_initialized:
                raise Exception("HardwareID Provider not initialized")
            
            # Извлекаем Hardware ID из входных данных
            hardware_id = input_data.get('hardware_id') if isinstance(input_data, dict) else None
            
            if not hardware_id:
                raise Exception("No hardware_id provided in input_data")
            
            # Валидируем формат ID если требуется
            if self.validate_id_format and not self._validate_id_format(hardware_id):
                raise Exception(f"Invalid hardware_id format: {hardware_id}")
            
            # Проверяем, существует ли уже этот ID
            if hardware_id in self.received_ids:
                logger.info(f"Hardware ID already exists: {hardware_id[:8]}...")
                result = {
                    "hardware_id": hardware_id,
                    "status": "exists",
                    "action": "none",
                    "message": "Hardware ID already registered"
                }
            else:
                # Сохраняем новый ID
                self.received_ids[hardware_id] = {
                    "first_seen": self._get_timestamp(),
                    "last_seen": self._get_timestamp(),
                    "source": "client"
                }
                logger.info(f"New Hardware ID registered: {hardware_id[:8]}...")
                result = {
                    "hardware_id": hardware_id,
                    "status": "new",
                    "action": "saved",
                    "message": "Hardware ID registered successfully"
                }
            
            # Обновляем метрики
            self.total_requests += 1
            self.report_success()
            
            yield result
            logger.debug("Hardware ID processed successfully")
            
        except Exception as e:
            logger.error(f"HardwareID Provider processing error: {e}")
            self.report_error(str(e))
            raise e
    
    async def cleanup(self) -> bool:
        """
        Очистка ресурсов Hardware ID провайдера
        
        Returns:
            True если очистка успешна, False иначе
        """
        try:
            self.received_ids.clear()
            self.is_initialized = False
            logger.info("HardwareID Provider cleaned up")
            return True
            
        except Exception as e:
            logger.error(f"Error cleaning up HardwareID Provider: {e}")
            return False
    
    def _validate_id_format(self, hardware_id: str) -> bool:
        """
        Валидация формата Hardware ID
        
        Args:
            hardware_id: ID для валидации
            
        Returns:
            True если формат валиден, False иначе
        """
        try:
            # Проверяем базовые требования
            if not hardware_id or len(hardware_id) < 8:
                return False
            
            # Проверяем, что ID содержит только допустимые символы
            # UUID формат: 12345678-1234-1234-1234-123456789ABC
            # Или простой формат: abcdef1234567890
            import re
            
            # UUID формат
            uuid_pattern = r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
            if re.match(uuid_pattern, hardware_id):
                return True
            
            # Простой формат (буквы и цифры)
            simple_pattern = r'^[a-zA-Z0-9]{8,64}$'
            if re.match(simple_pattern, hardware_id):
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error validating hardware_id format: {e}")
            return False
    
    def _get_timestamp(self) -> str:
        """
        Получение текущего timestamp
        
        Returns:
            Строка с текущим timestamp
        """
        import time
        return str(int(time.time()))
    
    def get_received_ids(self) -> Dict[str, Dict[str, Any]]:
        """
        Получение всех полученных Hardware ID
        
        Returns:
            Словарь с полученными ID и их метаданными
        """
        return self.received_ids.copy()
    
    def is_id_registered(self, hardware_id: str) -> bool:
        """
        Проверка, зарегистрирован ли Hardware ID
        
        Args:
            hardware_id: ID для проверки
            
        Returns:
            True если ID зарегистрирован, False иначе
        """
        return hardware_id in self.received_ids
    
    async def _custom_health_check(self) -> bool:
        """
        Кастомная проверка здоровья Hardware ID провайдера
        
        Returns:
            True если провайдер здоров, False иначе
        """
        try:
            # Проверяем, что провайдер инициализирован
            if not self.is_initialized:
                return False
            
            # Проверяем, что можем обрабатывать ID
            return True
            
        except Exception as e:
            logger.warning(f"HardwareID Provider health check failed: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        Получение расширенного статуса Hardware ID провайдера
        
        Returns:
            Словарь со статусом провайдера
        """
        base_status = super().get_status()
        
        # Добавляем специфичную информацию
        base_status.update({
            "provider_type": "hardware_id",
            "received_ids_count": len(self.received_ids),
            "validate_id_format": self.validate_id_format,
            "require_hardware_id": self.require_hardware_id
        })
        
        return base_status
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Получение расширенных метрик Hardware ID провайдера
        
        Returns:
            Словарь с метриками провайдера
        """
        base_metrics = super().get_metrics()
        
        # Добавляем специфичные метрики
        base_metrics.update({
            "provider_type": "hardware_id",
            "received_ids_count": len(self.received_ids),
            "validate_id_format": self.validate_id_format
        })
        
        return base_metrics
