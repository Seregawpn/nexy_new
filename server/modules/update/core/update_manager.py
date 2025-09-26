"""
Update Manager - основной координатор Update Module
"""

import asyncio
import logging
from typing import Dict, Any, Optional, AsyncGenerator
import sys
import os

# Добавляем путь для импорта универсальных компонентов
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../integrations/core'))

from integrations.core.universal_module_interface import UniversalModuleInterface, ModuleStatus
from ..config import UpdateConfig
from ..providers.version_provider import VersionProvider
from ..providers.manifest_provider import ManifestProvider
from ..providers.artifact_provider import ArtifactProvider
from ..providers.update_server_provider import UpdateServerProvider

logger = logging.getLogger(__name__)


class UpdateManager(UniversalModuleInterface):
    """Основной координатор Update Module"""
    
    def __init__(self, config: Optional[UpdateConfig] = None):
        # Преобразуем конфигурацию в словарь для UniversalModuleInterface
        config_dict = (config or UpdateConfig()).to_dict()
        
        # Инициализируем базовый класс
        super().__init__(name="update", config=config_dict)
        
        # Сохраняем оригинальную конфигурацию
        self.config = config or UpdateConfig()
        
        # Провайдеры
        self.version_provider = None
        self.manifest_provider = None
        self.artifact_provider = None
        self.update_server_provider = None
        
        # Статистика
        self.start_time = None
        self.total_requests = 0
        self.total_downloads = 0
        self.total_errors = 0
        
        # Статус
        self.is_running = False
    
    async def initialize(self) -> bool:
        """Инициализация модуля"""
        try:
            logger.info("🔧 Инициализация UpdateManager...")
            
            if not self.config.enabled:
                logger.info("⏭️ Update Module отключен в конфигурации")
                self.is_initialized = True
                self.set_status(ModuleStatus.READY)
                return True
            
            # Валидируем конфигурацию
            if not self.config.is_valid():
                logger.error("❌ Неверная конфигурация Update Module")
                return False
            
            # Инициализируем провайдеры
            await self._initialize_providers()
            
            self.is_initialized = True
            logger.info("✅ UpdateManager инициализирован")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации UpdateManager: {e}")
            return False
    
    async def _initialize_providers(self):
        """Инициализация всех провайдеров"""
        try:
            # VersionProvider
            self.version_provider = VersionProvider(self.config)
            if not await self.version_provider.initialize():
                raise Exception("Ошибка инициализации VersionProvider")
            
            # ManifestProvider
            self.manifest_provider = ManifestProvider(self.config)
            if not await self.manifest_provider.initialize():
                raise Exception("Ошибка инициализации ManifestProvider")
            
            # ArtifactProvider
            self.artifact_provider = ArtifactProvider(self.config)
            if not await self.artifact_provider.initialize():
                raise Exception("Ошибка инициализации ArtifactProvider")
            
            # UpdateServerProvider
            self.update_server_provider = UpdateServerProvider(
                self.config,
                self.manifest_provider,
                self.artifact_provider,
                self.version_provider
            )
            if not await self.update_server_provider.initialize():
                raise Exception("Ошибка инициализации UpdateServerProvider")
            
            logger.info("✅ Все провайдеры инициализированы")
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации провайдеров: {e}")
            raise
    
    async def start(self) -> bool:
        """Запуск модуля"""
        try:
            logger.info("🚀 Запуск UpdateManager...")
            
            if not self.is_initialized:
                logger.error("❌ Модуль не инициализирован")
                return False
            
            if not self.config.enabled:
                logger.info("⏭️ Update Module отключен")
                return True
            
            if self.is_running:
                logger.warning("⚠️ Модуль уже запущен")
                return True
            
            # Проверяем что провайдеры инициализированы
            if not self.update_server_provider:
                logger.error("❌ Провайдеры не инициализированы")
                return False
            
            # Запускаем HTTP сервер
            if not await self.update_server_provider.start_server():
                logger.error("❌ Ошибка запуска HTTP сервера")
                return False
            
            self.is_running = True
            self.start_time = asyncio.get_event_loop().time()
            
            logger.info("✅ UpdateManager запущен")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска UpdateManager: {e}")
            return False
    
    async def stop(self) -> bool:
        """Остановка модуля"""
        try:
            logger.info("🛑 Остановка UpdateManager...")
            
            if not self.is_running:
                logger.info("ℹ️ Модуль уже остановлен")
                return True
            
            # Останавливаем HTTP сервер
            if self.update_server_provider:
                await self.update_server_provider.stop_server()
            
            # Останавливаем провайдеры
            if self.version_provider:
                await self.version_provider.stop()
            if self.manifest_provider:
                await self.manifest_provider.stop()
            if self.artifact_provider:
                await self.artifact_provider.stop()
            if self.update_server_provider:
                await self.update_server_provider.stop()
            
            self.is_running = False
            logger.info("✅ UpdateManager остановлен")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка остановки UpdateManager: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Получение статуса модуля"""
        try:
            uptime = 0
            if self.start_time:
                uptime = asyncio.get_event_loop().time() - self.start_time
            
            status = {
                "status": "running" if self.is_running else "stopped",
                "module": "update",
                "enabled": self.config.enabled,
                "initialized": self.is_initialized,
                "uptime_seconds": uptime,
                "statistics": {
                    "total_requests": self.total_requests,
                    "total_downloads": self.total_downloads,
                    "total_errors": self.total_errors
                },
                "providers": {}
            }
            
            # Статус провайдеров
            if self.version_provider:
                status["providers"]["version"] = self.version_provider.get_status()
            if self.manifest_provider:
                status["providers"]["manifest"] = self.manifest_provider.get_status()
            if self.artifact_provider:
                status["providers"]["artifact"] = self.artifact_provider.get_status()
            if self.update_server_provider:
                status["providers"]["update_server"] = self.update_server_provider.get_status()
            
            return status
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения статуса: {e}")
            return {
                "status": "error",
                "module": "update",
                "error": str(e)
            }
    
    # Методы для работы с версиями
    def create_version_manifest(self, version: str, artifact_path: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Создание манифеста для новой версии
        
        Args:
            version: Версия приложения
            artifact_path: Путь к артефакту
            **kwargs: Дополнительные параметры
            
        Returns:
            Optional[Dict[str, Any]]: Созданный манифест или None
        """
        try:
            if not self.is_running:
                logger.error("❌ Модуль не запущен")
                return None
            
            # Валидируем версию
            if not self.version_provider.validate_version(version):
                logger.error(f"❌ Неверная версия: {version}")
                return None
            
            # Получаем информацию об артефакте
            artifact_info = self.artifact_provider.create_artifact_info(artifact_path)
            
            # Добавляем дополнительные параметры
            artifact_info.update(kwargs)
            
            # Создаем манифест
            build = self.version_provider.version_to_build(version)
            manifest = self.manifest_provider.create_manifest(version, build, artifact_info)
            
            # Сохраняем манифест
            filename = f"manifest_{version}.json"
            self.manifest_provider.save_manifest(manifest, filename)
            
            logger.info(f"✅ Создан манифест для версии {version}")
            return manifest
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания манифеста для версии {version}: {e}")
            return None
    
    def get_latest_version(self) -> Optional[str]:
        """Получение последней версии"""
        try:
            latest_manifest = self.manifest_provider.get_latest_manifest()
            return latest_manifest.get("version") if latest_manifest else None
        except Exception as e:
            logger.error(f"❌ Ошибка получения последней версии: {e}")
            return None
    
    def get_version_history(self, limit: int = 10) -> list:
        """Получение истории версий"""
        try:
            return self.manifest_provider.get_all_manifests()[:limit]
        except Exception as e:
            logger.error(f"❌ Ошибка получения истории версий: {e}")
            return []
    
    def cleanup_old_artifacts(self, keep_count: int = 5) -> int:
        """Очистка старых артефактов"""
        try:
            return self.artifact_provider.cleanup_old_artifacts(keep_count)
        except Exception as e:
            logger.error(f"❌ Ошибка очистки артефактов: {e}")
            return 0
    
    def validate_artifact(self, file_path: str, expected_sha256: Optional[str] = None) -> bool:
        """Валидация артефакта"""
        try:
            return self.artifact_provider.validate_artifact(file_path, expected_sha256)
        except Exception as e:
            logger.error(f"❌ Ошибка валидации артефакта {file_path}: {e}")
            return False
    
    def get_artifact_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Получение информации об артефакте"""
        try:
            return self.artifact_provider.get_file_info(file_path)
        except Exception as e:
            logger.error(f"❌ Ошибка получения информации об артефакте {file_path}: {e}")
            return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """Получение статистики модуля"""
        try:
            uptime = 0
            if self.start_time:
                uptime = asyncio.get_event_loop().time() - self.start_time
            
            return {
                "uptime_seconds": uptime,
                "uptime_formatted": self._format_uptime(uptime),
                "total_requests": self.total_requests,
                "total_downloads": self.total_downloads,
                "total_errors": self.total_errors,
                "success_rate": self._calculate_success_rate(),
                "is_running": self.is_running,
                "enabled": self.config.enabled
            }
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики: {e}")
            return {
                "error": str(e)
            }
    
    def _format_uptime(self, uptime_seconds: float) -> str:
        """Форматирование времени работы"""
        try:
            hours = int(uptime_seconds // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            seconds = int(uptime_seconds % 60)
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        except Exception:
            return "00:00:00"
    
    def _calculate_success_rate(self) -> float:
        """Расчет процента успешных операций"""
        try:
            total_operations = self.total_requests + self.total_downloads
            if total_operations == 0:
                return 100.0
            
            successful_operations = total_operations - self.total_errors
            return round((successful_operations / total_operations) * 100, 2)
        except Exception:
            return 0.0
    
    async def process(self, input_data: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Основная обработка данных (требуется UniversalModuleInterface)
        
        Args:
            input_data: Входные данные для обработки
            
        Yields:
            Результаты обработки
        """
        try:
            # Для Update Module process не используется активно,
            # так как основная работа происходит через HTTP сервер
            logger.debug(f"UpdateManager.process вызван с данными: {input_data}")
            
            # Возвращаем информацию о статусе
            yield {
                "status": "processed",
                "module": "update",
                "message": "Update Module работает в режиме HTTP сервера",
                "data": input_data
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка в process: {e}")
            yield {
                "status": "error",
                "module": "update",
                "error": str(e),
                "data": input_data
            }
    
    async def cleanup(self) -> bool:
        """
        Очистка ресурсов модуля (требуется UniversalModuleInterface)
        
        Returns:
            True если очистка успешна, False иначе
        """
        try:
            logger.info("🧹 Очистка ресурсов UpdateManager...")
            
            # Вызываем stop для остановки всех компонентов
            await self.stop()
            
            # Дополнительная очистка ресурсов
            if self.start_time:
                self.start_time = None
            
            # Сброс статистики
            self.total_requests = 0
            self.total_downloads = 0
            self.total_errors = 0
            
            logger.info("✅ Ресурсы UpdateManager очищены")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка очистки ресурсов UpdateManager: {e}")
            return False
