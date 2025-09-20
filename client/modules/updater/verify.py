"""
Проверки безопасности для системы обновлений
SHA256 хеши, Ed25519 подписи, codesign проверки
"""

import hashlib
import base64
import subprocess
import logging
from nacl.signing import VerifyKey
from typing import Optional

logger = logging.getLogger(__name__)

def sha256_checksum(file_path: str) -> str:
    """
    Вычисление SHA256 хеша файла
    
    Args:
        file_path: Путь к файлу
        
    Returns:
        str: SHA256 хеш в шестнадцатеричном формате
        
    Raises:
        OSError: Если файл не найден
    """
    sha256_hash = hashlib.sha256()
    
    try:
        with open(file_path, "rb") as f:
            # Читаем файл по частям для экономии памяти
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        
        result = sha256_hash.hexdigest()
        logger.info(f"SHA256 хеш вычислен: {result[:16]}...")
        return result
        
    except OSError as e:
        logger.error(f"Ошибка чтения файла для SHA256: {e}")
        raise

def verify_ed25519_signature(file_path: str, signature_b64: str, public_key_b64: str) -> bool:
    """
    Проверка Ed25519 подписи файла
    
    Args:
        file_path: Путь к файлу
        signature_b64: Подпись в base64
        public_key_b64: Публичный ключ в base64
        
    Returns:
        bool: True если подпись верна
        
    Raises:
        ValueError: Если неверный формат ключа или подписи
    """
    try:
        # Читаем файл
        with open(file_path, "rb") as f:
            data = f.read()
        
        # Декодируем ключ и подпись
        try:
            verify_key = VerifyKey(base64.b64decode(public_key_b64))
            signature = base64.b64decode(signature_b64)
        except Exception as e:
            logger.error(f"Ошибка декодирования ключа/подписи: {e}")
            return False
        
        # Проверяем подпись
        try:
            verify_key.verify(data, signature)
            logger.info("✅ Ed25519 подпись проверена успешно")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ed25519 подпись неверна: {e}")
            return False
            
    except OSError as e:
        logger.error(f"Ошибка чтения файла для проверки подписи: {e}")
        return False

def verify_app_signature(app_path: str) -> bool:
    """
    Проверка подписи приложения Apple
    
    Args:
        app_path: Путь к .app файлу
        
    Returns:
        bool: True если подпись верна
    """
    try:
        logger.info(f"Проверка подписи приложения: {app_path}")
        
        # Проверка codesign
        result = subprocess.run([
            "/usr/bin/codesign", 
            "--verify", 
            "--deep", 
            "--strict", 
            "--verbose=2", 
            app_path
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"❌ codesign проверка не пройдена: {result.stderr}")
            return False
        
        logger.info("✅ codesign проверка пройдена")
        
        # Проверка Gatekeeper (spctl)
        result = subprocess.run([
            "/usr/sbin/spctl", 
            "-a", 
            "-vv", 
            "--type", 
            "execute", 
            app_path
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"❌ Gatekeeper проверка не пройдена: {result.stderr}")
            return False
        
        logger.info("✅ Gatekeeper проверка пройдена")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Ошибка проверки подписи приложения: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Неожиданная ошибка проверки подписи: {e}")
        return False

def verify_file_integrity(file_path: str, expected_sha256: str) -> bool:
    """
    Проверка целостности файла по SHA256
    
    Args:
        file_path: Путь к файлу
        expected_sha256: Ожидаемый SHA256 хеш
        
    Returns:
        bool: True если хеш совпадает
    """
    try:
        actual_sha256 = sha256_checksum(file_path)
        
        # Сравниваем без учета регистра
        if actual_sha256.lower() == expected_sha256.lower():
            logger.info("✅ SHA256 хеш совпадает")
            return True
        else:
            logger.error(
                f"❌ SHA256 хеш не совпадает:\n"
                f"Ожидался: {expected_sha256}\n"
                f"Получен:  {actual_sha256}"
            )
            return False
            
    except Exception as e:
        logger.error(f"❌ Ошибка проверки целостности: {e}")
        return False

def verify_dmg_signature(dmg_path: str) -> bool:
    """
    Проверка подписи DMG файла
    
    Args:
        dmg_path: Путь к DMG файлу
        
    Returns:
        bool: True если подпись верна
    """
    try:
        logger.info(f"Проверка подписи DMG: {dmg_path}")
        
        # Проверяем подпись DMG
        result = subprocess.run([
            "/usr/bin/codesign", 
            "--verify", 
            "--deep", 
            "--strict", 
            dmg_path
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"❌ DMG подпись неверна: {result.stderr}")
            return False
        
        logger.info("✅ DMG подпись проверена")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка проверки подписи DMG: {e}")
        return False

def get_app_bundle_id(app_path: str) -> Optional[str]:
    """
    Получение Bundle ID приложения
    
    Args:
        app_path: Путь к .app файлу
        
    Returns:
        str: Bundle ID или None при ошибке
    """
    try:
        import plistlib
        info_plist_path = os.path.join(app_path, "Contents", "Info.plist")
        
        with open(info_plist_path, "rb") as f:
            plist = plistlib.load(f)
        
        bundle_id = plist.get("CFBundleIdentifier")
        logger.info(f"Bundle ID: {bundle_id}")
        return bundle_id
        
    except Exception as e:
        logger.error(f"Ошибка получения Bundle ID: {e}")
        return None

def get_app_version(app_path: str) -> Optional[str]:
    """
    Получение версии приложения
    
    Args:
        app_path: Путь к .app файлу
        
    Returns:
        str: Версия приложения или None при ошибке
    """
    try:
        import plistlib
        info_plist_path = os.path.join(app_path, "Contents", "Info.plist")
        
        with open(info_plist_path, "rb") as f:
            plist = plistlib.load(f)
        
        version = plist.get("CFBundleShortVersionString")
        build = plist.get("CFBundleVersion")
        
        full_version = f"{version} ({build})" if version and build else version
        logger.info(f"Версия приложения: {full_version}")
        return full_version
        
    except Exception as e:
        logger.error(f"Ошибка получения версии приложения: {e}")
        return None
