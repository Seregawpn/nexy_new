"""
Утилиты кэширования для модуля hardware_id
Упрощенная версия - только Hardware UUID
"""

import json
import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from ..core.types import HardwareIdResult, HardwareIdStatus, CacheInfo, HardwareIdCacheError

logger = logging.getLogger(__name__)


class HardwareIdCache:
    """Кэш для Hardware ID"""
    
    def __init__(self, cache_file_path: str, ttl_seconds: int = 86400 * 30):
        self.cache_file_path = os.path.expanduser(cache_file_path)
        self.ttl_seconds = ttl_seconds
        self._cache_dir = Path(self.cache_file_path).parent
        
        # Создаем директорию для кэша
        self._cache_dir.mkdir(parents=True, exist_ok=True)
    
    def get_cached_uuid(self) -> Optional[HardwareIdResult]:
        """
        Получает Hardware UUID из кэша
        
        Returns:
            HardwareIdResult: Кэшированный результат или None
        """
        try:
            if not os.path.exists(self.cache_file_path):
                logger.debug("🔍 Кэш не существует")
                return None
            
            # Загружаем кэш
            with open(self.cache_file_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # Проверяем валидность кэша
            if not self._is_cache_valid(cache_data):
                logger.warning("⚠️ Кэш невалиден или устарел")
                return None
            
            # Извлекаем данные
            uuid = cache_data.get('uuid', '')
            if not uuid:
                logger.warning("⚠️ UUID не найден в кэше")
                return None
            
            logger.info(f"✅ Hardware UUID загружен из кэша: {uuid[:16]}...")
            
            return HardwareIdResult(
                uuid=uuid,
                status=HardwareIdStatus.CACHED,
                source="cache",
                cached=True,
                metadata=cache_data.get('metadata', {})
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки кэша: {e}")
            return None
    
    def save_uuid_to_cache(self, uuid: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Сохраняет Hardware UUID в кэш
        
        Args:
            uuid: Hardware UUID для сохранения
            metadata: Дополнительные метаданные
            
        Returns:
            bool: True если успешно сохранено
        """
        try:
            cache_data = {
                'uuid': uuid,
                'cached_at': datetime.now().isoformat(),
                'ttl_seconds': self.ttl_seconds,
                'version': '1.0',
                'metadata': metadata or {}
            }
            
            # Сохраняем в кэш
            with open(self.cache_file_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Hardware UUID сохранен в кэш: {uuid[:16]}...")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения в кэш: {e}")
            return False
    
    def _is_cache_valid(self, cache_data: Dict[str, Any]) -> bool:
        """
        Проверяет валидность кэша
        
        Args:
            cache_data: Данные кэша
            
        Returns:
            bool: True если кэш валиден
        """
        try:
            # Проверяем обязательные поля
            required_fields = ['uuid', 'cached_at', 'ttl_seconds', 'version']
            if not all(field in cache_data for field in required_fields):
                logger.warning("⚠️ Отсутствуют обязательные поля в кэше")
                return False
            
            # Проверяем версию кэша
            if cache_data.get('version') != '1.0':
                logger.warning("⚠️ Неверная версия кэша")
                return False
            
            # Проверяем TTL
            cached_at_str = cache_data.get('cached_at', '')
            if not cached_at_str:
                logger.warning("⚠️ Отсутствует время создания кэша")
                return False
            
            try:
                cached_at = datetime.fromisoformat(cached_at_str)
                ttl_seconds = cache_data.get('ttl_seconds', 0)
                
                if datetime.now() - cached_at > timedelta(seconds=ttl_seconds):
                    logger.warning("⚠️ Кэш устарел")
                    return False
                
            except ValueError as e:
                logger.warning(f"⚠️ Неверный формат времени в кэше: {e}")
                return False
            
            # Проверяем UUID
            uuid = cache_data.get('uuid', '')
            if not uuid or len(uuid) < 10:
                logger.warning("⚠️ Неверный UUID в кэше")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка валидации кэша: {e}")
            return False
    
    def clear_cache(self) -> bool:
        """
        Очищает кэш
        
        Returns:
            bool: True если успешно очищено
        """
        try:
            if os.path.exists(self.cache_file_path):
                os.remove(self.cache_file_path)
                logger.info("✅ Кэш очищен")
            else:
                logger.info("ℹ️ Кэш уже пуст")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка очистки кэша: {e}")
            return False
    
    def get_cache_info(self) -> CacheInfo:
        """
        Получает информацию о кэше
        
        Returns:
            CacheInfo: Информация о кэше
        """
        try:
            if not os.path.exists(self.cache_file_path):
                return CacheInfo(
                    exists=False,
                    size_bytes=0,
                    created_at="",
                    modified_at="",
                    ttl_remaining=0,
                    is_valid=False
                )
            
            # Получаем информацию о файле
            stat = os.stat(self.cache_file_path)
            size_bytes = stat.st_size
            modified_at = datetime.fromtimestamp(stat.st_mtime).isoformat()
            
            # Загружаем данные кэша
            with open(self.cache_file_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # Проверяем валидность
            is_valid = self._is_cache_valid(cache_data)
            
            # Вычисляем оставшееся время TTL
            ttl_remaining = 0
            if is_valid:
                try:
                    cached_at = datetime.fromisoformat(cache_data.get('cached_at', ''))
                    ttl_seconds = cache_data.get('ttl_seconds', 0)
                    remaining = ttl_seconds - (datetime.now() - cached_at).total_seconds()
                    ttl_remaining = max(0, int(remaining))
                except Exception:
                    ttl_remaining = 0
            
            return CacheInfo(
                exists=True,
                size_bytes=size_bytes,
                created_at=cache_data.get('cached_at', ''),
                modified_at=modified_at,
                ttl_remaining=ttl_remaining,
                is_valid=is_valid
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения информации о кэше: {e}")
            return CacheInfo(
                exists=False,
                size_bytes=0,
                created_at="",
                modified_at="",
                ttl_remaining=0,
                is_valid=False
            )
    
    def is_cache_available(self) -> bool:
        """
        Проверяет доступность кэша
        
        Returns:
            bool: True если кэш доступен
        """
        try:
            # Проверяем, что директория существует и доступна для записи
            return self._cache_dir.exists() and os.access(self._cache_dir, os.W_OK)
        except Exception:
            return False
