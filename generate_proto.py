#!/usr/bin/env python3
"""
Скрипт для генерации protobuf файлов из .proto файла.
Запускайте этот скрипт после изменения streaming.proto
"""

import subprocess
import sys
import os

def generate_proto():
    """Генерирует Python файлы из .proto файла"""
    
    # Проверяем наличие .proto файла
    proto_file = "server/streaming.proto"
    if not os.path.exists(proto_file):
        print(f"❌ Файл {proto_file} не найден!")
        return False
    
    try:
        print("🔧 Генерирую protobuf файлы...")
        
        # Генерируем для сервера
        server_dir = "server"
        cmd = [
            "python", "-m", "grpc_tools.protoc",
            f"--proto_path={server_dir}",
            f"--python_out={server_dir}",
            f"--grpc_python_out={server_dir}",
            proto_file
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Protobuf файлы для сервера сгенерированы успешно!")
        else:
            print(f"❌ Ошибка генерации для сервера: {result.stderr}")
            return False
        
        # Генерируем для клиента
        client_dir = "client"
        cmd = [
            "python", "-m", "grpc_tools.protoc",
            f"--proto_path={server_dir}",
            f"--python_out={client_dir}",
            f"--grpc_python_out={client_dir}",
            proto_file
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Protobuf файлы для клиента сгенерированы успешно!")
        else:
            print(f"❌ Ошибка генерации для клиента: {result.stderr}")
            return False
        
        print("🎉 Все protobuf файлы сгенерированы успешно!")
        return True
        
    except FileNotFoundError:
        print("❌ grpc_tools.protoc не найден!")
        print("Установите: pip install grpcio-tools")
        return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

if __name__ == "__main__":
    success = generate_proto()
    sys.exit(0 if success else 1)
