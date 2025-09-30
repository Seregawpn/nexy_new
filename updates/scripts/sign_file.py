#!/usr/bin/env python3
"""
Подпись файлов Ed25519 ключом
"""

import os
import sys
import base64
from nacl.signing import SigningKey
from nacl.encoding import Base64Encoder

def sign_file(file_path: str, private_key_path: str) -> str:
    """
    Подпись файла Ed25519 ключом
    
    Args:
        file_path: Путь к файлу для подписи
        private_key_path: Путь к приватному ключу
        
    Returns:
        str: Подпись в base64
    """
    
    # Читаем приватный ключ
    with open(private_key_path, 'r') as f:
        private_key_b64 = f.read().strip()
    
    private_key = SigningKey(private_key_b64, encoder=Base64Encoder)
    
    # Читаем файл
    with open(file_path, 'rb') as f:
        file_data = f.read()
    
    # Подписываем
    signature = private_key.sign(file_data)
    
    # Кодируем в base64
    signature_b64 = base64.b64encode(signature.signature).decode('utf-8')
    
    return signature_b64

def main():
    if len(sys.argv) != 3:
        print("Использование: python3 sign_file.py <файл> <приватный_ключ>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    private_key_path = sys.argv[2]
    
    if not os.path.exists(file_path):
        print(f"❌ Файл не найден: {file_path}")
        sys.exit(1)
    
    if not os.path.exists(private_key_path):
        print(f"❌ Приватный ключ не найден: {private_key_path}")
        sys.exit(1)
    
    try:
        signature = sign_file(file_path, private_key_path)
        print(f"✅ Файл подписан: {file_path}")
        print(f"📝 Подпись (base64): {signature}")
        
    except Exception as e:
        print(f"❌ Ошибка подписи: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
