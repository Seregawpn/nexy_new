#!/usr/bin/env python3
"""
Генератор манифеста обновлений для собственной системы Nexy
Поддерживает SHA256 хеширование и Ed25519 подпись
"""

import json
import hashlib
import base64
import os
import sys
from datetime import datetime
from pathlib import Path

def sha256_checksum(file_path: str) -> str:
    """Вычисление SHA256 хеша файла"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):  # Читаем по 1MB
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()

def sign_file_ed25519(file_path: str, private_key_path: str) -> str:
    """Подпись файла Ed25519 ключом"""
    try:
        from nacl.signing import SigningKey
        
        # Загружаем приватный ключ
        with open(private_key_path, "rb") as f:
            signing_key = SigningKey(f.read())
        
        # Подписываем файл
        with open(file_path, "rb") as f:
            file_data = f.read()
            signature = signing_key.sign(file_data).signature
        
        # Возвращаем подпись в base64
        return base64.b64encode(signature).decode('utf-8')
        
    except ImportError:
        print("⚠️ PyNaCl не установлен, Ed25519 подпись недоступна")
        return ""
    except Exception as e:
        print(f"⚠️ Ошибка Ed25519 подписи: {e}")
        return ""

def generate_manifest(dmg_path: str, version: str, build: int, private_key_path: str = None) -> dict:
    """Генерация манифеста обновлений"""
    
    if not os.path.exists(dmg_path):
        raise FileNotFoundError(f"DMG файл не найден: {dmg_path}")
    
    print(f"📁 Обработка DMG: {dmg_path}")
    
    # Получаем размер файла
    file_size = os.path.getsize(dmg_path)
    print(f"📏 Размер: {file_size:,} байт ({file_size/1024/1024:.1f} MB)")
    
    # Вычисляем SHA256
    print("🔍 Вычисление SHA256...")
    sha256_hash = sha256_checksum(dmg_path)
    print(f"🔒 SHA256: {sha256_hash[:16]}...")
    
    # Ed25519 подпись (если есть ключ)
    ed25519_signature = ""
    if private_key_path and os.path.exists(private_key_path):
        print("🔑 Создание Ed25519 подписи...")
        ed25519_signature = sign_file_ed25519(dmg_path, private_key_path)
        if ed25519_signature:
            print(f"✅ Ed25519: {ed25519_signature[:16]}...")
        else:
            print("❌ Ed25519 подпись не удалась")
    else:
        print("⚠️ Ed25519 ключ не найден, пропускаем подпись")
    
    # Создаем манифест
    manifest = {
        "version": version,
        "build": build,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "artifact": {
            "type": "dmg",
            "url": f"https://api.nexy.ai/updates/Nexy-{version}.dmg",
            "size": file_size,
            "sha256": sha256_hash,
            "ed25519": ed25519_signature
        },
        "requirements": {
            "min_macos": "11.0",
            "architecture": "arm64"
        },
        "changelog": [
            "Исправлены цветные иконки в меню-баре",
            "Улучшения стабильности работы",
            "Оптимизация производительности",
            "Исправления ошибок"
        ],
        "security": {
            "verification_methods": ["sha256", "codesign"] + (["ed25519"] if ed25519_signature else []),
            "signed_by": "Developer ID Application: Sergiy Zasorin (5NKLL2CLB9)",
            "notarized": True
        }
    }
    
    return manifest

def main():
    """Главная функция"""
    if len(sys.argv) < 4:
        print("📋 ГЕНЕРАТОР МАНИФЕСТА NEXY")
        print("===========================")
        print("")
        print("Использование:")
        print("  python3 generate_manifest.py <dmg_path> <version> <build> [private_key_path]")
        print("")
        print("Примеры:")
        print("  python3 generate_manifest.py dist/Nexy.dmg 1.71.0 171")
        print("  python3 generate_manifest.py dist/Nexy.dmg 1.71.0 171 private_key.pem")
        print("")
        sys.exit(1)
    
    dmg_path = sys.argv[1]
    version = sys.argv[2]
    build = int(sys.argv[3])
    private_key_path = sys.argv[4] if len(sys.argv) > 4 else None
    
    print("🔧 ГЕНЕРАТОР МАНИФЕСТА NEXY")
    print("===========================")
    print(f"📦 DMG: {dmg_path}")
    print(f"🏷️ Версия: {version}")
    print(f"🔢 Билд: {build}")
    print(f"🔑 Ed25519 ключ: {private_key_path if private_key_path else 'Нет'}")
    print("")
    
    try:
        # Генерируем манифест
        manifest = generate_manifest(dmg_path, version, build, private_key_path)
        
        # Сохраняем в файл
        os.makedirs("dist", exist_ok=True)
        manifest_path = "dist/manifest.json"
        
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        
        print("")
        print("✅ МАНИФЕСТ СОЗДАН УСПЕШНО!")
        print("===========================")
        print(f"📁 Файл: {manifest_path}")
        print(f"🏷️ Версия: {manifest['version']}")
        print(f"🔒 SHA256: {manifest['artifact']['sha256'][:16]}...")
        print(f"🔑 Ed25519: {'Да' if manifest['artifact']['ed25519'] else 'Нет'}")
        print(f"📏 Размер: {manifest['artifact']['size']:,} байт")
        print(f"🌐 URL: {manifest['artifact']['url']}")
        print("")
        print("📋 Содержимое манифеста:")
        print(json.dumps(manifest, indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"❌ Ошибка создания манифеста: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()