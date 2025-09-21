#!/usr/bin/env python3
"""
Генерация манифеста обновлений
"""

import os
import json
import hashlib
import sys
from datetime import datetime
from sign_file import sign_file

def calculate_sha256(file_path: str) -> str:
    """Вычисление SHA256 хеша файла"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()

def generate_manifest(artifact_path: str, version: str, build: int, 
                     artifact_type: str = "dmg", private_key_path: str = None,
                     notes_url: str = None, critical: bool = False) -> dict:
    """
    Генерация манифеста обновлений
    
    Args:
        artifact_path: Путь к артефакту (DMG/ZIP)
        version: Версия приложения (например, "2.6.0")
        build: Номер сборки (например, 20600)
        artifact_type: Тип артефакта ("dmg" или "zip")
        private_key_path: Путь к приватному ключу для подписи
        notes_url: URL с заметками о версии
        critical: Критическое ли обновление
        
    Returns:
        dict: Манифест обновлений
    """
    
    if not os.path.exists(artifact_path):
        raise FileNotFoundError(f"Артефакт не найден: {artifact_path}")
    
    # Получаем информацию о файле
    file_size = os.path.getsize(artifact_path)
    sha256_hash = calculate_sha256(artifact_path)
    
    # Генерируем URL (в реальном проекте будет из конфигурации)
    filename = os.path.basename(artifact_path)
    artifact_url = f"https://updates.nexy.ai/artifacts/{filename}"
    
    # Создаем базовый манифест
    manifest = {
        "version": version,
        "build": build,
        "release_date": datetime.utcnow().isoformat() + "Z",
        "artifact": {
            "type": artifact_type,
            "url": artifact_url,
            "size": file_size,
            "sha256": sha256_hash,
            "arch": "arm64",
            "min_os": "11.0"
        },
        "critical": critical,
        "auto_install": not critical  # Критические обновления требуют подтверждения
    }
    
    # Добавляем Ed25519 подпись если есть ключ
    if private_key_path and os.path.exists(private_key_path):
        try:
            ed25519_signature = sign_file(artifact_path, private_key_path)
            manifest["artifact"]["ed25519"] = ed25519_signature
            print(f"✅ Артефакт подписан Ed25519")
        except Exception as e:
            print(f"⚠️ Не удалось подписать артефакт: {e}")
    
    # Добавляем URL заметок если указан
    if notes_url:
        manifest["notes_url"] = notes_url
    
    return manifest

def save_manifest(manifest: dict, output_path: str):
    """Сохранение манифеста в файл"""
    
    # Создаем директорию если нужно
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Сохраняем с красивым форматированием
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Манифест сохранен: {output_path}")

def main():
    if len(sys.argv) < 4:
        print("Использование: python3 generate_manifest.py <артефакт> <версия> <сборка> [тип] [приватный_ключ] [заметки_url]")
        print("Пример: python3 generate_manifest.py Nexy-2.6.0.dmg 2.6.0 20600 dmg keys/ed25519_private.key")
        sys.exit(1)
    
    artifact_path = sys.argv[1]
    version = sys.argv[2]
    build = int(sys.argv[3])
    artifact_type = sys.argv[4] if len(sys.argv) > 4 else "dmg"
    private_key_path = sys.argv[5] if len(sys.argv) > 5 else None
    notes_url = sys.argv[6] if len(sys.argv) > 6 else None
    
    try:
        # Генерируем манифест
        manifest = generate_manifest(
            artifact_path=artifact_path,
            version=version,
            build=build,
            artifact_type=artifact_type,
            private_key_path=private_key_path,
            notes_url=notes_url
        )
        
        # Сохраняем манифест
        manifests_dir = os.path.join(os.path.dirname(__file__), "..", "manifests")
        output_path = os.path.join(manifests_dir, "manifest.json")
        save_manifest(manifest, output_path)
        
        print(f"📋 Манифест для версии {version} (сборка {build}) создан")
        
    except Exception as e:
        print(f"❌ Ошибка генерации манифеста: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
