#!/usr/bin/env python3
"""
Генерация Ed25519 ключей для подписи обновлений
"""

import os
import base64
from nacl.signing import SigningKey
from nacl.encoding import Base64Encoder

def generate_ed25519_keys():
    """Генерация пары Ed25519 ключей"""
    
    # Создаем директорию для ключей
    keys_dir = os.path.join(os.path.dirname(__file__), "..", "keys")
    os.makedirs(keys_dir, exist_ok=True)
    
    # Генерируем ключи
    private_key = SigningKey.generate()
    public_key = private_key.verify_key
    
    # Кодируем в base64
    private_key_b64 = private_key.encode(encoder=Base64Encoder).decode('utf-8')
    public_key_b64 = public_key.encode(encoder=Base64Encoder).decode('utf-8')
    
    # Сохраняем ключи
    private_key_path = os.path.join(keys_dir, "ed25519_private.key")
    public_key_path = os.path.join(keys_dir, "ed25519_public.key")
    
    with open(private_key_path, 'w') as f:
        f.write(private_key_b64)
    
    with open(public_key_path, 'w') as f:
        f.write(public_key_b64)
    
    # Устанавливаем правильные права доступа
    os.chmod(private_key_path, 0o600)  # Только владелец может читать/писать
    
    print("✅ Ed25519 ключи сгенерированы:")
    print(f"   Приватный ключ: {private_key_path}")
    print(f"   Публичный ключ: {public_key_path}")
    print(f"   Публичный ключ (base64): {public_key_b64}")
    
    return private_key_path, public_key_path, public_key_b64

if __name__ == "__main__":
    generate_ed25519_keys()
