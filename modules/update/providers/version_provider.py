"""
Version Provider - управление версиями и сборками
"""

import logging
import re
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class VersionProvider:
    """Провайдер для управления версиями и сборками"""
    
    def __init__(self, config):
        self.config = config
        self.version_pattern = re.compile(r'^(\d+)\.(\d+)\.(\d+)$')
    
    async def initialize(self) -> bool:
        """Инициализация провайдера"""
        try:
            logger.info("🔧 Инициализация VersionProvider...")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации VersionProvider: {e}")
            return False
    
    def parse_version(self, version_string: str) -> Tuple[int, int, int]:
        """
        Парсинг версии из строки
        
        Args:
            version_string: Строка версии (например, "1.2.3")
            
        Returns:
            Tuple[int, int, int]: (major, minor, patch)
            
        Raises:
            ValueError: Если версия неверного формата
        """
        match = self.version_pattern.match(version_string)
        if not match:
            raise ValueError(f"Неверный формат версии: {version_string}")
        
        major, minor, patch = map(int, match.groups())
        return major, minor, patch
    
    def version_to_build(self, version: str) -> int:
        """
        Преобразование версии в номер сборки
        
        Формула: major * 10000 + minor * 100 + patch
        
        Args:
            version: Строка версии
            
        Returns:
            int: Номер сборки
        """
        major, minor, patch = self.parse_version(version)
        return major * 10000 + minor * 100 + patch
    
    def build_to_version(self, build: int) -> str:
        """
        Преобразование номера сборки в версию
        
        Args:
            build: Номер сборки
            
        Returns:
            str: Строка версии
        """
        major = build // 10000
        minor = (build % 10000) // 100
        patch = build % 100
        
        return f"{major}.{minor}.{patch}"
    
    def compare_versions(self, version1: str, version2: str) -> int:
        """
        Сравнение версий
        
        Args:
            version1: Первая версия
            version2: Вторая версия
            
        Returns:
            int: -1 если version1 < version2, 0 если равны, 1 если version1 > version2
        """
        try:
            v1_tuple = self.parse_version(version1)
            v2_tuple = self.parse_version(version2)
            
            if v1_tuple < v2_tuple:
                return -1
            elif v1_tuple > v2_tuple:
                return 1
            else:
                return 0
        except ValueError:
            logger.error(f"Ошибка сравнения версий: {version1} vs {version2}")
            return 0
    
    def is_newer_version(self, current_version: str, new_version: str) -> bool:
        """
        Проверка, является ли новая версия более новой
        
        Args:
            current_version: Текущая версия
            new_version: Новая версия
            
        Returns:
            bool: True если новая версия более новая
        """
        return self.compare_versions(new_version, current_version) > 0
    
    def get_version_info(self, version: str) -> Dict[str, Any]:
        """
        Получение информации о версии
        
        Args:
            version: Строка версии
            
        Returns:
            Dict[str, Any]: Информация о версии
        """
        try:
            major, minor, patch = self.parse_version(version)
            build = self.version_to_build(version)
            
            return {
                "version": version,
                "major": major,
                "minor": minor,
                "patch": patch,
                "build": build,
                "is_valid": True
            }
        except ValueError:
            return {
                "version": version,
                "major": 0,
                "minor": 0,
                "patch": 0,
                "build": 0,
                "is_valid": False
            }
    
    def get_default_version(self) -> str:
        """Получение версии по умолчанию"""
        return self.config.default_version
    
    def get_default_build(self) -> int:
        """Получение номера сборки по умолчанию"""
        return self.config.default_build
    
    def validate_version(self, version: str) -> bool:
        """
        Валидация версии
        
        Args:
            version: Строка версии для проверки
            
        Returns:
            bool: True если версия валидна
        """
        try:
            self.parse_version(version)
            return True
        except ValueError:
            return False
    
    def get_version_history(self, manifest_dir: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Получение истории версий из манифестов
        
        Args:
            manifest_dir: Директория с манифестами
            limit: Максимальное количество версий
            
        Returns:
            List[Dict[str, Any]]: Список версий
        """
        versions = []
        
        try:
            manifest_path = Path(manifest_dir)
            if not manifest_path.exists():
                return versions
            
            # Ищем JSON файлы манифестов
            for manifest_file in manifest_path.glob("*.json"):
                try:
                    import json
                    with open(manifest_file, 'r', encoding='utf-8') as f:
                        manifest = json.load(f)
                    
                    version_info = self.get_version_info(manifest.get("version", ""))
                    if version_info["is_valid"]:
                        versions.append({
                            "version": version_info["version"],
                            "build": version_info["build"],
                            "file": manifest_file.name,
                            "release_date": manifest.get("release_date"),
                            "critical": manifest.get("critical", False)
                        })
                except Exception as e:
                    logger.warning(f"Ошибка чтения манифеста {manifest_file}: {e}")
            
            # Сортируем по номеру сборки (по убыванию)
            versions.sort(key=lambda x: x["build"], reverse=True)
            
            return versions[:limit]
            
        except Exception as e:
            logger.error(f"Ошибка получения истории версий: {e}")
            return versions
    
    async def stop(self) -> bool:
        """Остановка провайдера"""
        try:
            logger.info("🛑 Остановка VersionProvider...")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка остановки VersionProvider: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Получение статуса провайдера"""
        return {
            "status": "running",
            "provider": "version",
            "default_version": self.get_default_version(),
            "default_build": self.get_default_build()
        }



