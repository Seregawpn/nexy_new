"""
Основной класс системы обновлений
"""

import json
import tempfile
import os
import subprocess
from typing import Optional, Dict, Any
from .config import UpdaterConfig
from .net import UpdateHTTPClient
from .verify import sha256_checksum, verify_ed25519_signature, verify_app_signature
from .dmg import mount_dmg, unmount_dmg, find_app_in_dmg
from .replace import atomic_replace_app
from .migrate import get_user_app_path
import logging

logger = logging.getLogger(__name__)

class Updater:
    """Основной класс системы обновлений"""
    
    def __init__(self, config: UpdaterConfig):
        self.config = config
        self.http_client = UpdateHTTPClient(config.timeout, config.retries)
    
    def get_current_build(self) -> int:
        """Получение текущего номера сборки"""
        try:
            import plistlib
            info_plist_path = os.path.join(get_user_app_path(), "Contents", "Info.plist")
            with open(info_plist_path, "rb") as f:
                plist = plistlib.load(f)
            return int(plist.get("CFBundleVersion", 0))
        except Exception:
            return 0
    
    def check_for_updates(self) -> Optional[Dict[str, Any]]:
        """Проверка доступности обновлений"""
        try:
            manifest = self.http_client.get_manifest(self.config.manifest_url)
            current_build = self.get_current_build()
            latest_build = int(manifest.get("build", 0))
            
            if latest_build > current_build:
                return manifest
            return None
        except Exception as e:
            logger.error(f"Ошибка проверки обновлений: {e}")
            return None
    
    def download_and_verify(self, artifact_info: Dict[str, Any]) -> str:
        """Скачивание и проверка артефакта"""
        artifact_type = artifact_info.get("type", "dmg")
        artifact_url = artifact_info["url"]
        expected_size = artifact_info.get("size")
        expected_sha256 = artifact_info.get("sha256")
        expected_signature = artifact_info.get("ed25519")
        
        # Создаем временный файл
        suffix = ".dmg" if artifact_type == "dmg" else ".zip"
        temp_file = tempfile.mktemp(suffix=suffix)
        
        logger.info(f"Скачивание {artifact_type}...")
        self.http_client.download_file(artifact_url, temp_file, expected_size)
        
        # Проверяем SHA256
        if expected_sha256:
            actual_sha256 = sha256_checksum(temp_file)
            if actual_sha256.lower() != expected_sha256.lower():
                os.unlink(temp_file)
                raise RuntimeError("SHA256 хеш не совпадает")
        
        # Проверяем Ed25519 подпись
        if expected_signature and self.config.public_key:
            if not verify_ed25519_signature(temp_file, expected_signature, self.config.public_key):
                os.unlink(temp_file)
                raise RuntimeError("Ed25519 подпись неверна")
        
        return temp_file
    
    def install_update(self, artifact_path: str, artifact_info: Dict[str, Any]):
        """Установка обновления"""
        artifact_type = artifact_info.get("type", "dmg")
        user_app_path = get_user_app_path()
        
        if artifact_type == "dmg":
            mount_point = mount_dmg(artifact_path)
            try:
                new_app_path = find_app_in_dmg(mount_point)
                if not new_app_path:
                    raise RuntimeError("Не найден .app файл в DMG")
                
                # Проверяем подпись нового приложения
                if not verify_app_signature(new_app_path):
                    raise RuntimeError("Подпись нового приложения неверна")
                
                # Атомарно заменяем приложение
                atomic_replace_app(new_app_path, user_app_path)
                
            finally:
                unmount_dmg(mount_point)
        else:
            # ZIP файл - аналогично, но с распаковкой
            raise NotImplementedError("ZIP пока не поддерживается")
        
        # Удаляем временный файл
        os.unlink(artifact_path)
    
    def relaunch_app(self):
        """Перезапуск приложения"""
        user_app_path = get_user_app_path()
        subprocess.Popen(["/usr/bin/open", "-a", user_app_path])
        os._exit(0)
    
    def update(self) -> bool:
        """Полный цикл обновления"""
        try:
            # Проверяем обновления
            manifest = self.check_for_updates()
            if not manifest:
                return False
            
            logger.info(f"Найдено обновление до версии {manifest.get('version')}")
            
            # Скачиваем и проверяем
            artifact_path = self.download_and_verify(manifest["artifact"])
            
            # Устанавливаем
            self.install_update(artifact_path, manifest["artifact"])
            
            # Перезапускаем
            self.relaunch_app()
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка обновления: {e}")
            return False
