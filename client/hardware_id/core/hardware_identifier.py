"""
Основной класс для получения Hardware ID
Упрощенная версия - только Hardware UUID для macOS
"""

import logging
from typing import Optional, Dict, Any
from .types import (
    HardwareIdResult, HardwareIdStatus, HardwareIdConfig,
    HardwareIdError, HardwareIdNotFoundError, HardwareIdValidationError
)
from .config import get_hardware_id_config
from ..macos.hardware_detector import HardwareDetector
from ..utils.caching import HardwareIdCache
from ..utils.validation import HardwareIdValidator

logger = logging.getLogger(__name__)


class HardwareIdentifier:
    """Основной класс для получения Hardware ID"""
    
    def __init__(self, config: Optional[HardwareIdConfig] = None):
        self.config = config or get_hardware_id_config()
        self.detector = HardwareDetector(timeout=self.config.system_profiler_timeout)
        self.cache = HardwareIdCache(
            cache_file_path=self.config.cache_file_path,
            ttl_seconds=self.config.cache_ttl_seconds
        )
        self.validator = HardwareIdValidator()
        self._cached_result: Optional[HardwareIdResult] = None
    
    def get_hardware_id(self, force_regenerate: bool = False) -> HardwareIdResult:
        """
        Получает Hardware ID с кэшированием
        
        Args:
            force_regenerate: Принудительно пересоздать ID (игнорировать кэш)
            
        Returns:
            HardwareIdResult: Результат получения Hardware ID
        """
        try:
            logger.info("🔍 Начинаем получение Hardware ID...")
            
            # Если не принудительная регенерация, пробуем загрузить из кэша
            if not force_regenerate and self.config.cache_enabled:
                cached_result = self._get_cached_id()
                if cached_result:
                    self._cached_result = cached_result
                    logger.info("✅ Hardware ID загружен из кэша")
                    return cached_result
            
            # Если кэш не сработал, получаем новый ID
            logger.info("🔄 Получаем новый Hardware ID...")
            result = self._get_new_hardware_id()
            
            # Сохраняем в кэш если успешно
            if result.status == HardwareIdStatus.SUCCESS and self.config.cache_enabled:
                self._save_to_cache(result)
            
            self._cached_result = result
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения Hardware ID: {e}")
            return HardwareIdResult(
                uuid="",
                status=HardwareIdStatus.ERROR,
                source="hardware_identifier",
                cached=False,
                error_message=str(e)
            )
    
    def _get_cached_id(self) -> Optional[HardwareIdResult]:
        """
        Получает Hardware ID из кэша
        
        Returns:
            HardwareIdResult: Кэшированный результат или None
        """
        try:
            if not self.config.cache_enabled:
                logger.debug("🔍 Кэширование отключено")
                return None
            
            cached_result = self.cache.get_cached_uuid()
            if not cached_result:
                logger.debug("🔍 Кэш пуст или невалиден")
                return None
            
            # Валидируем кэшированный результат
            if self.config.validate_uuid_format:
                if not self.validator.validate_hardware_id_result(cached_result):
                    logger.warning("⚠️ Кэшированный результат невалиден")
                    return None
            
            logger.info(f"✅ Hardware ID загружен из кэша: {cached_result.uuid[:16]}...")
            return cached_result
            
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки из кэша: {e}")
            return None
    
    def _get_new_hardware_id(self) -> HardwareIdResult:
        """
        Получает новый Hardware ID
        
        Returns:
            HardwareIdResult: Результат получения
        """
        try:
            # Обнаруживаем Hardware UUID
            result = self.detector.detect_hardware_uuid()
            
            if result.status == HardwareIdStatus.SUCCESS:
                # Валидируем результат
                if self.config.validate_uuid_format:
                    if not self.validator.validate_hardware_id_result(result):
                        logger.warning("⚠️ Полученный Hardware ID невалиден")
                        return HardwareIdResult(
                            uuid="",
                            status=HardwareIdStatus.ERROR,
                            source=result.source,
                            cached=False,
                            error_message="Hardware ID невалиден"
                        )
                
                logger.info(f"✅ Hardware ID получен: {result.uuid[:16]}...")
                return result
            
            elif result.status == HardwareIdStatus.NOT_FOUND:
                logger.warning("⚠️ Hardware UUID не найден")
                
                # Если разрешен fallback, генерируем случайный UUID
                if self.config.fallback_to_random:
                    logger.info("🔄 Генерируем случайный UUID как fallback...")
                    return self._generate_fallback_uuid()
                else:
                    return result
            
            else:
                logger.error(f"❌ Ошибка получения Hardware ID: {result.error_message}")
                return result
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения нового Hardware ID: {e}")
            return HardwareIdResult(
                uuid="",
                status=HardwareIdStatus.ERROR,
                source="hardware_identifier",
                cached=False,
                error_message=str(e)
            )
    
    def _generate_fallback_uuid(self) -> HardwareIdResult:
        """
        Генерирует случайный UUID как fallback
        
        Returns:
            HardwareIdResult: Результат с случайным UUID
        """
        try:
            import uuid
            
            random_uuid = str(uuid.uuid4())
            logger.warning(f"⚠️ Сгенерирован случайный UUID: {random_uuid[:16]}...")
            
            return HardwareIdResult(
                uuid=random_uuid,
                status=HardwareIdStatus.SUCCESS,
                source="fallback",
                cached=False,
                metadata={
                    "fallback": True,
                    "generated_at": self._get_timestamp()
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка генерации fallback UUID: {e}")
            return HardwareIdResult(
                uuid="",
                status=HardwareIdStatus.ERROR,
                source="fallback",
                cached=False,
                error_message=str(e)
            )
    
    def _save_to_cache(self, result: HardwareIdResult) -> bool:
        """
        Сохраняет результат в кэш
        
        Args:
            result: Результат для сохранения
            
        Returns:
            bool: True если успешно сохранено
        """
        try:
            if not self.config.cache_enabled:
                logger.debug("🔍 Кэширование отключено")
                return False
            
            metadata = result.metadata or {}
            metadata.update({
                "cached_at": self._get_timestamp(),
                "source": result.source,
                "status": result.status.value
            })
            
            success = self.cache.save_uuid_to_cache(result.uuid, metadata)
            if success:
                logger.info("✅ Hardware ID сохранен в кэш")
            else:
                logger.warning("⚠️ Не удалось сохранить в кэш")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения в кэш: {e}")
            return False
    
    def clear_cache(self) -> bool:
        """
        Очищает кэш
        
        Returns:
            bool: True если успешно очищено
        """
        try:
            success = self.cache.clear_cache()
            if success:
                self._cached_result = None
                logger.info("✅ Кэш очищен")
            return success
            
        except Exception as e:
            logger.error(f"❌ Ошибка очистки кэша: {e}")
            return False
    
    def get_cache_info(self) -> Dict[str, Any]:
        """
        Получает информацию о кэше
        
        Returns:
            dict: Информация о кэше
        """
        try:
            cache_info = self.cache.get_cache_info()
            
            return {
                "exists": cache_info.exists,
                "size_bytes": cache_info.size_bytes,
                "created_at": cache_info.created_at,
                "modified_at": cache_info.modified_at,
                "ttl_remaining": cache_info.ttl_remaining,
                "is_valid": cache_info.is_valid,
                "cache_enabled": self.config.cache_enabled,
                "ttl_seconds": self.config.cache_ttl_seconds
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения информации о кэше: {e}")
            return {"error": str(e)}
    
    def get_hardware_info(self) -> Dict[str, Any]:
        """
        Получает полную информацию об оборудовании
        
        Returns:
            dict: Информация об оборудовании
        """
        try:
            hardware_info = self.detector.detect_hardware_info()
            system_info = self.detector.get_system_info()
            
            return {
                "hardware": hardware_info,
                "system": system_info,
                "config": {
                    "cache_enabled": self.config.cache_enabled,
                    "validate_uuid_format": self.config.validate_uuid_format,
                    "fallback_to_random": self.config.fallback_to_random
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения информации об оборудовании: {e}")
            return {"error": str(e)}
    
    def validate_hardware_id(self, uuid_str: str) -> bool:
        """
        Валидирует Hardware ID
        
        Args:
            uuid_str: UUID для валидации
            
        Returns:
            bool: True если UUID валиден
        """
        try:
            return self.validator.validate_uuid(uuid_str)
        except Exception as e:
            logger.error(f"❌ Ошибка валидации Hardware ID: {e}")
            return False
    
    def get_validation_info(self, uuid_str: str) -> Dict[str, Any]:
        """
        Получает информацию о валидации UUID
        
        Args:
            uuid_str: UUID для анализа
            
        Returns:
            dict: Информация о валидации
        """
        try:
            return self.validator.get_validation_info(uuid_str)
        except Exception as e:
            logger.error(f"❌ Ошибка получения информации о валидации: {e}")
            return {"error": str(e)}
    
    def _get_timestamp(self) -> str:
        """Получает текущий timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def is_available(self) -> bool:
        """
        Проверяет доступность модуля
        
        Returns:
            bool: True если модуль доступен
        """
        try:
            # Проверяем, что мы на macOS
            if not self.detector.is_macos():
                logger.warning("⚠️ Не macOS система")
                return False
            
            # Проверяем доступность system_profiler
            if not self.detector.system_profiler.is_available():
                logger.warning("⚠️ system_profiler недоступен")
                return False
            
            # Проверяем доступность кэша
            if not self.cache.is_cache_available():
                logger.warning("⚠️ Кэш недоступен")
                return False
            
            logger.info("✅ Модуль hardware_id доступен")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка проверки доступности: {e}")
            return False
