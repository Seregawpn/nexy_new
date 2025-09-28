"""
Модуль системы обновлений Nexy
HTTP-система обновлений без пароля с миграцией в ~/Applications
"""

from .config import UpdaterConfig
from .net import UpdateHTTPClient
from .verify import sha256_checksum, verify_ed25519_signature, verify_app_signature
from .dmg import mount_dmg, unmount_dmg, find_app_in_dmg
from .replace import atomic_replace_app
from .updater import Updater

__all__ = [
    'UpdaterConfig',
    'UpdateHTTPClient', 
    'sha256_checksum',
    'verify_ed25519_signature',
    'verify_app_signature',
    'mount_dmg',
    'unmount_dmg',
    'find_app_in_dmg',
    'atomic_replace_app',
    'Updater'
]
