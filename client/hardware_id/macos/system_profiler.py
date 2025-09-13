"""
macOS system_profiler bridge для получения Hardware UUID
Упрощенная версия - только Hardware UUID
"""

import subprocess
import logging
from typing import Optional, Dict, Any
from ..core.types import HardwareIdError, HardwareIdNotFoundError

logger = logging.getLogger(__name__)


class SystemProfilerBridge:
    """Bridge для работы с system_profiler на macOS"""
    
    def __init__(self, timeout: int = 5):
        self.timeout = timeout
    
    def get_hardware_uuid(self) -> Optional[str]:
        """
        Получает Hardware UUID через system_profiler
        
        Returns:
            str: Hardware UUID или None если не найден
        """
        try:
            logger.debug("🔍 Получаем Hardware UUID через system_profiler...")
            
            result = subprocess.run(
                ["system_profiler", "SPHardwareDataType"],
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            if result.returncode != 0:
                logger.error(f"❌ system_profiler завершился с ошибкой: {result.stderr}")
                return None
            
            # Парсим вывод system_profiler
            uuid = self._parse_hardware_uuid(result.stdout)
            
            if uuid:
                logger.info(f"✅ Hardware UUID получен: {uuid}")
                return uuid
            else:
                logger.warning("⚠️ Hardware UUID не найден в выводе system_profiler")
                return None
                
        except subprocess.TimeoutExpired:
            logger.error(f"❌ system_profiler превысил таймаут {self.timeout} секунд")
            return None
        except FileNotFoundError:
            logger.error("❌ system_profiler не найден (не macOS?)")
            return None
        except Exception as e:
            logger.error(f"❌ Ошибка выполнения system_profiler: {e}")
            return None
    
    def _parse_hardware_uuid(self, output: str) -> Optional[str]:
        """
        Парсит Hardware UUID из вывода system_profiler
        
        Args:
            output: Вывод system_profiler
            
        Returns:
            str: Hardware UUID или None
        """
        try:
            for line in output.split('\n'):
                line = line.strip()
                
                # Ищем строку с Hardware UUID
                if 'Hardware UUID:' in line:
                    # Извлекаем UUID после двоеточия
                    uuid_part = line.split(':', 1)[1].strip()
                    
                    # Валидируем формат UUID
                    if self._is_valid_uuid_format(uuid_part):
                        logger.debug(f"🔍 Найден Hardware UUID: {uuid_part}")
                        return uuid_part
                    else:
                        logger.warning(f"⚠️ Неверный формат UUID: {uuid_part}")
                        continue
            
            logger.debug("🔍 Hardware UUID не найден в выводе system_profiler")
            return None
            
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга Hardware UUID: {e}")
            return None
    
    def _is_valid_uuid_format(self, uuid: str) -> bool:
        """
        Проверяет формат Hardware UUID
        
        Args:
            uuid: UUID для проверки
            
        Returns:
            bool: True если формат корректный
        """
        if not uuid:
            return False
        
        # Hardware UUID обычно имеет формат: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
        # Проверяем базовую структуру
        parts = uuid.split('-')
        if len(parts) != 5:
            return False
        
        # Проверяем длину каждой части
        expected_lengths = [8, 4, 4, 4, 12]
        for i, part in enumerate(parts):
            if len(part) != expected_lengths[i]:
                return False
            
            # Проверяем, что все символы - hex
            if not all(c in '0123456789ABCDEFabcdef' for c in part):
                return False
        
        return True
    
    def get_hardware_info(self) -> Dict[str, Any]:
        """
        Получает полную информацию об оборудовании через system_profiler
        
        Returns:
            dict: Информация об оборудовании
        """
        try:
            logger.debug("🔍 Получаем полную информацию об оборудовании...")
            
            result = subprocess.run(
                ["system_profiler", "SPHardwareDataType"],
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            if result.returncode != 0:
                logger.error(f"❌ system_profiler завершился с ошибкой: {result.stderr}")
                return {}
            
            # Парсим информацию об оборудовании
            hardware_info = self._parse_hardware_info(result.stdout)
            
            logger.info("✅ Информация об оборудовании получена")
            return hardware_info
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения информации об оборудовании: {e}")
            return {}
    
    def _parse_hardware_info(self, output: str) -> Dict[str, Any]:
        """
        Парсит информацию об оборудовании из вывода system_profiler
        
        Args:
            output: Вывод system_profiler
            
        Returns:
            dict: Информация об оборудовании
        """
        hardware_info = {}
        
        try:
            for line in output.split('\n'):
                line = line.strip()
                
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Сохраняем основные поля
                    if key in ['Hardware UUID', 'Serial Number (system)', 'Model Name', 'Model Identifier']:
                        hardware_info[key] = value
                        logger.debug(f"🔍 {key}: {value}")
            
            return hardware_info
            
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга информации об оборудовании: {e}")
            return {}
    
    def is_available(self) -> bool:
        """
        Проверяет доступность system_profiler
        
        Returns:
            bool: True если system_profiler доступен
        """
        try:
            result = subprocess.run(
                ["which", "system_profiler"],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            return result.returncode == 0
            
        except Exception:
            return False
