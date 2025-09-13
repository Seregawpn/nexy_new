"""
Утилиты валидации для модуля hardware_id
Упрощенная версия - только Hardware UUID
"""

import re
import logging
from typing import Optional, Dict, Any
from ..core.types import HardwareIdValidationError

logger = logging.getLogger(__name__)


class HardwareIdValidator:
    """Валидатор для Hardware ID"""
    
    def __init__(self):
        # Регулярное выражение для UUID формата
        self.uuid_pattern = re.compile(
            r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
        )
    
    def validate_uuid(self, uuid_str: str) -> bool:
        """
        Валидирует Hardware UUID
        
        Args:
            uuid_str: UUID для валидации
            
        Returns:
            bool: True если UUID валиден
        """
        try:
            if not uuid_str:
                logger.warning("⚠️ UUID пустой")
                return False
            
            # Проверяем базовый формат
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
            # Проверяем регулярным выражением
            if not self.uuid_pattern.match(uuid_str):
                return False
            
            # Дополнительная проверка длины
            if len(uuid_str) != 36:  # Стандартная длина UUID
                return False
            
            # Проверяем, что все символы - hex
            clean_uuid = uuid_str.replace('-', '')
            if not all(c in '0123456789ABCDEFabcdef' for c in clean_uuid):
                return False
            
            return True
            
        except Exception:
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
            # Проверяем версию UUID по первому символу после первого дефиса
            if len(uuid_str) >= 14:
                version_char = uuid_str[14]
                
                # Версия 4 - случайный UUID
                if version_char == '4':
                    return True
                
                # Hardware UUID может иметь версии 1, 2, 3, 5, 6
                # Версия 1 - время-основанный
                # Версия 2 - DCE Security
                # Версия 3 - MD5 хеш
                # Версия 5 - SHA-1 хеш (часто используется для Hardware UUID)
                # Версия 6 - время-основанный (новый стандарт)
                if version_char in '12356':
                    return False
                
                # Неизвестная версия - считаем случайным
                return True
            
            # Если не можем определить версию, считаем случайным
            return True
            
        except Exception:
            return True
    
    def validate_hardware_id_result(self, result: 'HardwareIdResult') -> bool:
        """
        Валидирует результат получения Hardware ID
        
        Args:
            result: Результат для валидации
            
        Returns:
            bool: True если результат валиден
        """
        try:
            # Проверяем базовые поля
            if not result.uuid:
                logger.warning("⚠️ UUID пустой в результате")
                return False
            
            if not result.status:
                logger.warning("⚠️ Статус пустой в результате")
                return False
            
            if not result.source:
                logger.warning("⚠️ Источник пустой в результате")
                return False
            
            # Валидируем UUID
            if not self.validate_uuid(result.uuid):
                logger.warning("⚠️ UUID невалиден в результате")
                return False
            
            logger.debug("✅ Результат Hardware ID валиден")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка валидации результата: {e}")
            return False
    
    def sanitize_uuid(self, uuid_str: str) -> Optional[str]:
        """
        Очищает и нормализует UUID
        
        Args:
            uuid_str: UUID для очистки
            
        Returns:
            str: Очищенный UUID или None
        """
        try:
            if not uuid_str:
                return None
            
            # Убираем пробелы и приводим к верхнему регистру
            cleaned = uuid_str.strip().upper()
            
            # Проверяем формат
            if not self._is_valid_uuid_format(cleaned):
                logger.warning(f"⚠️ UUID не удалось очистить: {uuid_str}")
                return None
            
            return cleaned
            
        except Exception as e:
            logger.error(f"❌ Ошибка очистки UUID: {e}")
            return None
    
    def get_validation_info(self, uuid_str: str) -> Dict[str, Any]:
        """
        Получает информацию о валидации UUID
        
        Args:
            uuid_str: UUID для анализа
            
        Returns:
            dict: Информация о валидации
        """
        try:
            info = {
                'is_valid': False,
                'is_random': False,
                'format_correct': False,
                'length_correct': False,
                'characters_valid': False,
                'version': None,
                'errors': []
            }
            
            if not uuid_str:
                info['errors'].append("UUID пустой")
                return info
            
            # Проверяем длину
            info['length_correct'] = len(uuid_str) == 36
            if not info['length_correct']:
                info['errors'].append(f"Неверная длина: {len(uuid_str)} (ожидается 36)")
            
            # Проверяем формат
            info['format_correct'] = self._is_valid_uuid_format(uuid_str)
            if not info['format_correct']:
                info['errors'].append("Неверный формат UUID")
            
            # Проверяем символы
            clean_uuid = uuid_str.replace('-', '')
            info['characters_valid'] = all(c in '0123456789ABCDEFabcdef' for c in clean_uuid)
            if not info['characters_valid']:
                info['errors'].append("Содержит недопустимые символы")
            
            # Определяем версию
            if len(uuid_str) >= 14:
                try:
                    version_char = uuid_str[14]
                    if version_char in '1234':
                        info['version'] = int(version_char)
                    else:
                        info['errors'].append(f"Неверная версия UUID: {version_char}")
                except Exception:
                    info['errors'].append("Не удалось определить версию UUID")
            
            # Проверяем, является ли случайным
            info['is_random'] = self._is_random_uuid(uuid_str)
            if info['is_random']:
                info['errors'].append("UUID выглядит как случайный")
            
            # Общая валидность
            info['is_valid'] = (
                info['length_correct'] and
                info['format_correct'] and
                info['characters_valid'] and
                not info['is_random'] and
                len(info['errors']) == 0
            )
            
            return info
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения информации о валидации: {e}")
            return {
                'is_valid': False,
                'is_random': False,
                'format_correct': False,
                'length_correct': False,
                'characters_valid': False,
                'version': None,
                'errors': [f"Ошибка анализа: {e}"]
            }
