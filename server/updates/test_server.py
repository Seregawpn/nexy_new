#!/usr/bin/env python3
"""
Простой HTTP сервер для тестирования системы обновлений
"""

import http.server
import socketserver
import os
import json
from urllib.parse import urlparse

class UpdateRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Обработчик запросов для тестирования обновлений"""
    
    def __init__(self, *args, **kwargs):
        # Устанавливаем директорию для сервера
        os.chdir(os.path.join(os.path.dirname(__file__)))
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Обработка GET запросов"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/manifest.json':
            self.serve_manifest()
        elif parsed_path.path.startswith('/artifacts/'):
            self.serve_artifact(parsed_path.path)
        else:
            super().do_GET()
    
    def serve_manifest(self):
        """Отдача манифеста обновлений"""
        try:
            manifest_path = os.path.join('manifests', 'manifest.json')
            
            if not os.path.exists(manifest_path):
                self.send_error(404, "Manifest not found")
                return
            
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response = json.dumps(manifest, indent=2)
            self.wfile.write(response.encode('utf-8'))
            
            print(f"✅ Отдан манифест: {manifest.get('version', 'unknown')}")
            
        except Exception as e:
            print(f"❌ Ошибка отдачи манифеста: {e}")
            self.send_error(500, "Internal server error")
    
    def serve_artifact(self, path):
        """Отдача артефактов обновлений"""
        try:
            # Убираем /artifacts/ из пути
            artifact_name = path.replace('/artifacts/', '')
            artifact_path = os.path.join('artifacts', artifact_name)
            
            if not os.path.exists(artifact_path):
                self.send_error(404, f"Artifact not found: {artifact_name}")
                return
            
            # Отдаем файл
            with open(artifact_path, 'rb') as f:
                content = f.read()
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/octet-stream')
            self.send_header('Content-Length', str(len(content)))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            self.wfile.write(content)
            
            print(f"✅ Отдан артефакт: {artifact_name} ({len(content)} байт)")
            
        except Exception as e:
            print(f"❌ Ошибка отдачи артефакта: {e}")
            self.send_error(500, "Internal server error")

def start_test_server(port=8080):
    """Запуск тестового сервера"""
    print(f"🚀 Запуск тестового сервера обновлений на порту {port}")
    print(f"📁 Рабочая директория: {os.getcwd()}")
    print(f"📋 Манифест: http://localhost:{port}/manifest.json")
    print(f"📦 Артефакты: http://localhost:{port}/artifacts/")
    print("⏹️  Для остановки нажмите Ctrl+C")
    
    try:
        with socketserver.TCPServer(("", port), UpdateRequestHandler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Сервер остановлен")

if __name__ == "__main__":
    import sys
    
    port = 8080
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print("❌ Неверный номер порта")
            sys.exit(1)
    
    start_test_server(port)
