"""
Artifact Provider - управление артефактами обновлений
"""

import hashlib
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class ArtifactProvider:
    """Провайдер для управления артефактами обновлений"""
    
    def __init__(self, config):
        self.config = config
        self.downloads_dir = Path(config.downloads_dir)
        self.supported_types = ["dmg", "pkg", "zip", "app"]
    
    async def initialize(self) -> bool:
        """Инициализация провайдера"""
        try:
            logger.info("🔧 Инициализация ArtifactProvider...")
            
            # Создаем директорию downloads если не существует
            self.downloads_dir.mkdir(parents=True, exist_ok=True)
            
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации ArtifactProvider: {e}")
            return False
    
    def calculate_sha256(self, file_path: str) -> str:
        """
        Вычисление SHA256 хеша файла
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            str: SHA256 хеш в шестнадцатеричном формате
        """
        sha256_hash = hashlib.sha256()
        
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.error(f"❌ Ошибка вычисления SHA256 для {file_path}: {e}")
            return ""
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """
        Получение информации о файле
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            Dict[str, Any]: Информация о файле
        """
        try:
            path = Path(file_path)
            
            if not path.exists():
                return {
                    "exists": False,
                    "error": "File not found"
                }
            
            stat = path.stat()
            
            return {
                "exists": True,
                "filename": path.name,
                "size": stat.st_size,
                "sha256": self.calculate_sha256(file_path),
                "type": self._detect_file_type(file_path),
                "created": stat.st_ctime,
                "modified": stat.st_mtime
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения информации о файле {file_path}: {e}")
            return {
                "exists": False,
                "error": str(e)
            }
    
    def _detect_file_type(self, file_path: str) -> str:
        """
        Определение типа файла по расширению
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            str: Тип файла
        """
        path = Path(file_path)
        extension = path.suffix.lower()
        
        type_mapping = {
            ".dmg": "dmg",
            ".pkg": "pkg",
            ".zip": "zip",
            ".app": "app"
        }
        
        return type_mapping.get(extension, "unknown")
    
    def is_supported_type(self, file_type: str) -> bool:
        """
        Проверка поддерживаемого типа файла
        
        Args:
            file_type: Тип файла
            
        Returns:
            bool: True если тип поддерживается
        """
        return file_type.lower() in self.supported_types
    
    def get_artifact_url(self, filename: str) -> str:
        """
        Получение URL для скачивания артефакта
        
        Args:
            filename: Имя файла
            
        Returns:
            str: URL для скачивания
        """
        # Формируем URL для скачивания
        base_url = f"http://{self.config.host}:{self.config.port}"
        return f"{base_url}/downloads/{filename}"
    
    def list_artifacts(self) -> List[Dict[str, Any]]:
        """
        Получение списка всех артефактов
        
        Returns:
            List[Dict[str, Any]]: Список артефактов
        """
        artifacts = []
        
        try:
            for file_path in self.downloads_dir.iterdir():
                if file_path.is_file():
                    file_info = self.get_file_info(str(file_path))
                    
                    if file_info["exists"]:
                        artifact_info = {
                            "filename": file_info["filename"],
                            "size": file_info["size"],
                            "sha256": file_info["sha256"],
                            "type": file_info["type"],
                            "url": self.get_artifact_url(file_info["filename"]),
                            "created": file_info["created"],
                            "modified": file_info["modified"]
                        }
                        
                        artifacts.append(artifact_info)
            
            # Сортируем по времени модификации (новые сначала)
            artifacts.sort(key=lambda x: x["modified"], reverse=True)
            
            return artifacts
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения списка артефактов: {e}")
            return []
    
    def find_artifact_by_sha256(self, sha256: str) -> Optional[Dict[str, Any]]:
        """
        Поиск артефакта по SHA256 хешу
        
        Args:
            sha256: SHA256 хеш для поиска
            
        Returns:
            Optional[Dict[str, Any]]: Информация об артефакте или None
        """
        try:
            artifacts = self.list_artifacts()
            
            for artifact in artifacts:
                if artifact["sha256"].lower() == sha256.lower():
                    return artifact
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Ошибка поиска артефакта по SHA256: {e}")
            return None
    
    def validate_artifact(self, file_path: str, expected_sha256: Optional[str] = None) -> bool:
        """
        Валидация артефакта
        
        Args:
            file_path: Путь к файлу
            expected_sha256: Ожидаемый SHA256 хеш
            
        Returns:
            bool: True если артефакт валиден
        """
        try:
            file_info = self.get_file_info(file_path)
            
            if not file_info["exists"]:
                logger.error(f"❌ Файл не найден: {file_path}")
                return False
            
            # Проверяем тип файла
            if not self.is_supported_type(file_info["type"]):
                logger.error(f"❌ Неподдерживаемый тип файла: {file_info['type']}")
                return False
            
            # Проверяем SHA256 если указан
            if expected_sha256:
                actual_sha256 = file_info["sha256"]
                if actual_sha256.lower() != expected_sha256.lower():
                    logger.error(f"❌ SHA256 не совпадает. Ожидаемый: {expected_sha256}, Фактический: {actual_sha256}")
                    return False
            
            logger.info(f"✅ Артефакт валиден: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка валидации артефакта {file_path}: {e}")
            return False
    
    def create_artifact_info(self, file_path: str) -> Dict[str, Any]:
        """
        Создание информации об артефакте
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            Dict[str, Any]: Информация об артефакте
        """
        try:
            file_info = self.get_file_info(file_path)
            
            if not file_info["exists"]:
                raise FileNotFoundError(f"Файл не найден: {file_path}")
            
            return {
                "type": file_info["type"],
                "url": self.get_artifact_url(file_info["filename"]),
                "size": file_info["size"],
                "sha256": file_info["sha256"],
                "arch": self.config.default_arch,
                "min_os": self.config.default_min_os
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания информации об артефакте {file_path}: {e}")
            raise
    
    def cleanup_old_artifacts(self, keep_count: int = 5) -> int:
        """
        Очистка старых артефактов
        
        Args:
            keep_count: Количество артефактов для сохранения
            
        Returns:
            int: Количество удаленных файлов
        """
        try:
            artifacts = self.list_artifacts()
            
            if len(artifacts) <= keep_count:
                logger.info(f"📁 Артефактов меньше {keep_count}, очистка не требуется")
                return 0
            
            # Удаляем старые артефакты
            artifacts_to_remove = artifacts[keep_count:]
            removed_count = 0
            
            for artifact in artifacts_to_remove:
                try:
                    file_path = self.downloads_dir / artifact["filename"]
                    file_path.unlink()
                    removed_count += 1
                    logger.info(f"🗑️ Удален старый артефакт: {artifact['filename']}")
                except Exception as e:
                    logger.error(f"❌ Ошибка удаления артефакта {artifact['filename']}: {e}")
            
            logger.info(f"✅ Удалено {removed_count} старых артефактов")
            return removed_count
            
        except Exception as e:
            logger.error(f"❌ Ошибка очистки старых артефактов: {e}")
            return 0
    
    async def stop(self) -> bool:
        """Остановка провайдера"""
        try:
            logger.info("🛑 Остановка ArtifactProvider...")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка остановки ArtifactProvider: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Получение статуса провайдера"""
        try:
            artifacts = self.list_artifacts()
            total_size = sum(artifact["size"] for artifact in artifacts)
            
            return {
                "status": "running",
                "provider": "artifact",
                "downloads_dir": str(self.downloads_dir),
                "artifacts_count": len(artifacts),
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "supported_types": self.supported_types
            }
        except Exception as e:
            logger.error(f"❌ Ошибка получения статуса ArtifactProvider: {e}")
            return {
                "status": "error",
                "provider": "artifact",
                "error": str(e)
            }



