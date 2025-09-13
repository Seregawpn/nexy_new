"""
macOS Hardware Detector для получения Hardware UUID
Упрощенная версия - только Hardware UUID
"""

import logging
import uuid
from typing import Optional, Dict, Any
from .system_profiler import SystemProfilerBridge
from ..core.types import HardwareIdResult, HardwareIdStatus, HardwareIdError, HardwareIdNotFoundError

logger = logging.getLogger(__name__)


class HardwareDetector:
    """Детектор оборудования для macOS"""
    
    def __init__(self, timeout: int = 5):
        self.system_profiler = SystemProfilerBridge(timeout)
        self.timeout = timeout
    
    def detect_hardware_uuid(self) -> HardwareIdResult:
        """
        Обнаруживает Hardware UUID
        
        Returns:
            HardwareIdResult: Результат обнаружения
        """
        try:
            logger.info("🔍 Начинаем обнаружение Hardware UUID...")
            
            # Проверяем доступность system_profiler
            if not self.system_profiler.is_available():
                logger.error("❌ system_profiler недоступен")
                return HardwareIdResult(
                    uuid="",
                    status=HardwareIdStatus.ERROR,
                    source="system_profiler",
                    cached=False,
                    error_message="system_profiler недоступен"
                )
            
            # Получаем Hardware UUID через system_profiler
            hardware_uuid = self.system_profiler.get_hardware_uuid()
            
            if hardware_uuid:
                logger.info(f"✅ Hardware UUID обнаружен: {hardware_uuid}")
                return HardwareIdResult(
                    uuid=hardware_uuid,
                    status=HardwareIdStatus.SUCCESS,
                    source="system_profiler",
                    cached=False,
                    metadata={
                        "detection_method": "system_profiler",
                        "timestamp": self._get_timestamp()
                    }
                )
            else:
                logger.warning("⚠️ Hardware UUID не найден через system_profiler")
                return HardwareIdResult(
                    uuid="",
                    status=HardwareIdStatus.NOT_FOUND,
                    source="system_profiler",
                    cached=False,
                    error_message="Hardware UUID не найден"
                )
                
        except Exception as e:
            logger.error(f"❌ Ошибка обнаружения Hardware UUID: {e}")
            return HardwareIdResult(
                uuid="",
                status=HardwareIdStatus.ERROR,
                source="system_profiler",
                cached=False,
                error_message=str(e)
            )
    
    def detect_hardware_info(self) -> Dict[str, Any]:
        """
        Обнаруживает полную информацию об оборудовании
        
        Returns:
            dict: Информация об оборудовании
        """
        try:
            logger.info("🔍 Начинаем обнаружение информации об оборудовании...")
            
            # Получаем информацию через system_profiler
            hardware_info = self.system_profiler.get_hardware_info()
            
            if hardware_info:
                logger.info("✅ Информация об оборудовании обнаружена")
                return hardware_info
            else:
                logger.warning("⚠️ Информация об оборудовании не найдена")
                return {}
                
        except Exception as e:
            logger.error(f"❌ Ошибка обнаружения информации об оборудовании: {e}")
            return {}
    
    def validate_hardware_uuid(self, uuid_str: str) -> bool:
        """
        Валидирует Hardware UUID
        
        Args:
            uuid_str: UUID для валидации
            
        Returns:
            bool: True если UUID валиден
        """
        try:
            if not uuid_str:
                return False
            
            # Проверяем базовый формат UUID
            if not self._is_valid_uuid_format(uuid_str):
                logger.warning(f"⚠️ Неверный формат UUID: {uuid_str}")
                return False
            
            # Проверяем, что это не случайный UUID
            if self._is_random_uuid(uuid_str):
                logger.warning(f"⚠️ UUID выглядит как случайный: {uuid_str}")
                return False
            
            logger.debug(f"✅ UUID валиден: {uuid_str}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка валидации UUID: {e}")
            return False
    
    def _is_valid_uuid_format(self, uuid_str: str) -> bool:
        """
        Проверяет формат UUID
        
        Args:
            uuid_str: UUID для проверки
            
        Returns:
            bool: True если формат корректный
        """
        try:
            # Пытаемся создать UUID объект
            uuid.UUID(uuid_str)
            return True
        except ValueError:
            return False
    
    def _is_random_uuid(self, uuid_str: str) -> bool:
        """
        Проверяет, является ли UUID случайным
        
        Args:
            uuid_str: UUID для проверки
            
        Returns:
            bool: True если UUID выглядит случайным
        """
        try:
            # Создаем UUID объект
            uuid_obj = uuid.UUID(uuid_str)
            
            # Проверяем версию UUID
            # Версия 4 - случайный UUID
            if uuid_obj.version == 4:
                return True
            
            # Проверяем, что это не стандартный UUID
            # Hardware UUID обычно имеет версию 1 или 2
            return False
            
        except ValueError:
            return True  # Если не можем распарсить, считаем случайным
    
    def _get_timestamp(self) -> str:
        """Получает текущий timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def is_macos(self) -> bool:
        """
        Проверяет, что мы на macOS
        
        Returns:
            bool: True если macOS
        """
        try:
            import platform
            return platform.system() == "Darwin"
        except Exception:
            return False
    
    def get_system_info(self) -> Dict[str, Any]:
        """
        Получает информацию о системе
        
        Returns:
            dict: Информация о системе
        """
        try:
            import platform
            import sys
            
            return {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "python_version": sys.version,
                "is_macos": self.is_macos()
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения информации о системе: {e}")
            return {}
