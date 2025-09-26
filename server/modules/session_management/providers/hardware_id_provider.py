"""
Hardware ID Provider для генерации и управления уникальными идентификаторами
"""

import os
import logging
import secrets
import hashlib
import platform
import uuid
from typing import AsyncGenerator, Dict, Any, Optional
from integrations.core.universal_provider_interface import UniversalProviderInterface

logger = logging.getLogger(__name__)

class HardwareIDProvider(UniversalProviderInterface):
    """
    Провайдер для генерации и управления Hardware ID
    
    Создает уникальные идентификаторы на основе аппаратных характеристик
    системы и обеспечивает их кэширование для персистентности.
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
        
        # Настройки генерации ID
        self.cache_file = config.get('cache_file', 'hardware_id.cache')
        self.id_length = config.get('length', 32)
        self.charset = config.get('charset', 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
        self.require_hardware_id = config.get('require_hardware_id', True)
        
        # Кэшированный ID
        self.cached_id = None
        self.id_generated = False
        
        logger.info(f"HardwareID Provider initialized with length: {self.id_length}")
    
    async def initialize(self) -> bool:
        """
        Инициализация Hardware ID провайдера
        
        Returns:
            True если инициализация успешна, False иначе
        """
        try:
            logger.info("Initializing HardwareID Provider...")
            
            # Пытаемся загрузить кэшированный ID
            cached_id = await self._load_cached_id()
            if cached_id:
                self.cached_id = cached_id
                self.id_generated = True
                logger.info("Hardware ID loaded from cache")
            else:
                # Генерируем новый ID
                new_id = await self._generate_hardware_id()
                if new_id:
                    self.cached_id = new_id
                    self.id_generated = True
                    # Сохраняем в кэш
                    await self._save_to_cache(new_id)
                    logger.info("New Hardware ID generated and cached")
                else:
                    logger.error("Failed to generate Hardware ID")
                    return False
            
            self.is_initialized = True
            logger.info(f"HardwareID Provider initialized successfully: {self.cached_id[:8]}...")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize HardwareID Provider: {e}")
            return False
    
    async def process(self, input_data: Any) -> AsyncGenerator[str, None]:
        """
        Получение Hardware ID
        
        Args:
            input_data: Игнорируется (для совместимости с интерфейсом)
            
        Yields:
            Hardware ID
        """
        try:
            if not self.is_initialized:
                raise Exception("HardwareID Provider not initialized")
            
            if not self.cached_id:
                raise Exception("No Hardware ID available")
            
            # Обновляем метрики
            self.total_requests += 1
            self.report_success()
            
            yield self.cached_id
            logger.debug("Hardware ID provided successfully")
            
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
            self.cached_id = None
            self.id_generated = False
            self.is_initialized = False
            logger.info("HardwareID Provider cleaned up")
            return True
            
        except Exception as e:
            logger.error(f"Error cleaning up HardwareID Provider: {e}")
            return False
    
    async def _generate_hardware_id(self) -> Optional[str]:
        """
        Генерация уникального Hardware ID
        
        Returns:
            Сгенерированный Hardware ID или None при ошибке
        """
        try:
            # Собираем аппаратные характеристики
            hardware_info = self._collect_hardware_info()
            
            # Создаем хэш из аппаратной информации
            hardware_hash = self._create_hardware_hash(hardware_info)
            
            # Генерируем уникальный ID на основе хэша
            unique_id = self._generate_unique_id(hardware_hash)
            
            logger.debug(f"Hardware ID generated: {unique_id[:8]}...")
            return unique_id
            
        except Exception as e:
            logger.error(f"Error generating Hardware ID: {e}")
            return None
    
    def _collect_hardware_info(self) -> Dict[str, str]:
        """
        Сбор аппаратной информации системы
        
        Returns:
            Словарь с аппаратной информацией
        """
        hardware_info = {}
        
        try:
            # Информация о системе
            hardware_info['platform'] = platform.platform()
            hardware_info['system'] = platform.system()
            hardware_info['machine'] = platform.machine()
            hardware_info['processor'] = platform.processor()
            
            # MAC адрес (если доступен)
            try:
                mac = ':'.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff) 
                               for ele in range(0,8*6,8)][::-1])
                hardware_info['mac_address'] = mac
            except:
                hardware_info['mac_address'] = 'unknown'
            
            # Имя хоста
            hardware_info['hostname'] = platform.node()
            
            # Информация о Python
            hardware_info['python_version'] = platform.python_version()
            hardware_info['python_implementation'] = platform.python_implementation()
            
        except Exception as e:
            logger.warning(f"Error collecting hardware info: {e}")
            # Добавляем fallback информацию
            hardware_info['fallback'] = str(uuid.uuid4())
        
        return hardware_info
    
    def _create_hardware_hash(self, hardware_info: Dict[str, str]) -> str:
        """
        Создание хэша из аппаратной информации
        
        Args:
            hardware_info: Словарь с аппаратной информацией
            
        Returns:
            SHA-256 хэш аппаратной информации
        """
        # Сортируем ключи для консистентности
        sorted_info = sorted(hardware_info.items())
        
        # Создаем строку из информации
        info_string = '|'.join([f"{k}:{v}" for k, v in sorted_info])
        
        # Создаем хэш
        hash_object = hashlib.sha256(info_string.encode('utf-8'))
        return hash_object.hexdigest()
    
    def _generate_unique_id(self, hardware_hash: str) -> str:
        """
        Генерация уникального ID на основе хэша
        
        Args:
            hardware_hash: SHA-256 хэш аппаратной информации
            
        Returns:
            Уникальный ID заданной длины
        """
        # Используем хэш как seed для генерации
        seed = int(hardware_hash[:8], 16)
        
        # Генерируем ID заданной длины
        unique_id = ''
        for i in range(self.id_length):
            # Используем seed для псевдослучайного выбора
            char_index = (seed + i) % len(self.charset)
            unique_id += self.charset[char_index]
            # Обновляем seed
            seed = (seed * 1103515245 + 12345) & 0x7fffffff
        
        return unique_id
    
    async def _load_cached_id(self) -> Optional[str]:
        """
        Загрузка Hardware ID из кэша
        
        Returns:
            Кэшированный ID или None если не найден
        """
        try:
            if not os.path.exists(self.cache_file):
                logger.debug("No cache file found")
                return None
            
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cached_id = f.read().strip()
            
            if cached_id and len(cached_id) == self.id_length:
                logger.debug(f"Hardware ID loaded from cache: {cached_id[:8]}...")
                return cached_id
            else:
                logger.warning("Invalid cached Hardware ID found")
                return None
                
        except Exception as e:
            logger.warning(f"Error loading cached Hardware ID: {e}")
            return None
    
    async def _save_to_cache(self, hardware_id: str) -> bool:
        """
        Сохранение Hardware ID в кэш
        
        Args:
            hardware_id: Hardware ID для сохранения
            
        Returns:
            True если сохранение успешно, False иначе
        """
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                f.write(hardware_id)
            
            logger.debug(f"Hardware ID saved to cache: {hardware_id[:8]}...")
            return True
            
        except Exception as e:
            logger.error(f"Error saving Hardware ID to cache: {e}")
            return False
    
    async def _custom_health_check(self) -> bool:
        """
        Кастомная проверка здоровья Hardware ID провайдера
        
        Returns:
            True если провайдер здоров, False иначе
        """
        try:
            # Проверяем наличие кэшированного ID
            if not self.cached_id:
                return False
            
            # Проверяем корректность ID
            if len(self.cached_id) != self.id_length:
                return False
            
            # Проверяем, что ID содержит только допустимые символы
            for char in self.cached_id:
                if char not in self.charset:
                    return False
            
            return True
            
        except Exception as e:
            logger.warning(f"HardwareID Provider health check failed: {e}")
            return False
    
    def get_hardware_id(self) -> Optional[str]:
        """
        Получение текущего Hardware ID
        
        Returns:
            Hardware ID или None если не инициализирован
        """
        if self.is_initialized and self.cached_id:
            return self.cached_id
        return None
    
    def regenerate_hardware_id(self) -> bool:
        """
        Принудительная регенерация Hardware ID
        
        Returns:
            True если регенерация успешна, False иначе
        """
        try:
            # Удаляем кэш
            if os.path.exists(self.cache_file):
                os.remove(self.cache_file)
            
            # Сбрасываем текущий ID
            self.cached_id = None
            self.id_generated = False
            
            logger.info("Hardware ID regeneration requested")
            return True
            
        except Exception as e:
            logger.error(f"Error regenerating Hardware ID: {e}")
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
            "id_length": self.id_length,
            "cache_file": self.cache_file,
            "id_generated": self.id_generated,
            "has_cached_id": bool(self.cached_id),
            "cached_id_preview": self.cached_id[:8] + "..." if self.cached_id else None,
            "require_hardware_id": self.require_hardware_id,
            "charset_length": len(self.charset)
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
            "id_length": self.id_length,
            "id_generated": self.id_generated,
            "has_cached_id": bool(self.cached_id),
            "cache_file_exists": os.path.exists(self.cache_file) if self.cache_file else False
        })
        
        return base_metrics
