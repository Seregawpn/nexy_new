#!/usr/bin/env python3
"""
Local Update Server for Testing
Локальный сервер обновлений для тестирования Sparkle
"""

import os
import sys
import json
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class UpdateRequestHandler(SimpleHTTPRequestHandler):
    """Обработчик запросов для сервера обновлений"""
    
    def __init__(self, *args, **kwargs):
        self.updates_dir = Path(__file__).parent / "updates"
        self.downloads_dir = self.updates_dir / "downloads"
        self.appcast_file = self.updates_dir / "appcast.xml"
        super().__init__(*args, directory=str(self.updates_dir), **kwargs)
    
    def do_GET(self):
        """Обработка GET запросов"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        logger.info(f"GET request: {path}")
        
        # AppCast XML
        if path == "/appcast.xml":
            self.serve_appcast()
        # API для проверки обновлений
        elif path == "/api/update/check":
            self.serve_update_check(parsed_path.query)
        # Статические файлы (PKG, DMG)
        elif path.startswith("/downloads/"):
            self.serve_download(path)
        # Корневая страница
        elif path == "/":
            self.serve_index()
        else:
            super().do_GET()
    
    def serve_appcast(self):
        """Отдача AppCast XML"""
        try:
            if self.appcast_file.exists():
                with open(self.appcast_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Заменяем localhost на текущий IP
                content = content.replace("https://your-server.com", f"http://{self.server.server_name}:{self.server.server_port}")
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/xml; charset=utf-8')
                self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(content.encode('utf-8'))
            else:
                self.send_error(404, "AppCast not found")
        except Exception as e:
            logger.error(f"Error serving AppCast: {e}")
            self.send_error(500, "Internal Server Error")
    
    def serve_update_check(self, query_string):
        """API для проверки обновлений"""
        try:
            query_params = parse_qs(query_string)
            current_version = query_params.get('current', ['1.70.0'])[0]
            
            # Простая логика проверки обновлений
            latest_version = "1.71.0"
            
            if self._compare_versions(latest_version, current_version) > 0:
                response = {
                    'update_available': True,
                    'latest_version': latest_version,
                    'short_version': latest_version,
                    'download_url': f"http://{self.server.server_name}:{self.server.server_port}/downloads/Nexy_AI_Voice_Assistant_v{latest_version}.pkg",
                    'release_notes': 'Новая версия с системой автообновлений',
                    'title': f'Version {latest_version}',
                    'file_size': 61439100,
                    'pub_date': '2025-09-10T17:00:00Z'
                }
            else:
                response = {
                    'update_available': False,
                    'current_version': current_version
                }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))
            
        except Exception as e:
            logger.error(f"Error in update check: {e}")
            self.send_error(500, "Internal Server Error")
    
    def serve_download(self, path):
        """Отдача файлов для скачивания"""
        try:
            file_path = self.updates_dir / path[1:]  # Убираем ведущий /
            
            if file_path.exists() and file_path.is_file():
                with open(file_path, 'rb') as f:
                    content = f.read()
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/octet-stream')
                self.send_header('Content-Disposition', f'attachment; filename="{file_path.name}"')
                self.send_header('Content-Length', str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_error(404, "File not found")
        except Exception as e:
            logger.error(f"Error serving download: {e}")
            self.send_error(500, "Internal Server Error")
    
    def serve_index(self):
        """Главная страница сервера"""
        html = f"""
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nexy Update Server</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 40px; background: #f5f5f7; }}
        .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 40px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }}
        h1 {{ color: #1d1d1f; margin-bottom: 20px; }}
        .status {{ background: #e8f5e8; padding: 15px; border-radius: 8px; margin: 20px 0; }}
        .endpoint {{ background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 10px 0; font-family: monospace; }}
        .download {{ background: #e3f2fd; padding: 15px; border-radius: 8px; margin: 10px 0; }}
        a {{ color: #007AFF; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Nexy Update Server</h1>
        
        <div class="status">
            <h3>✅ Сервер работает</h3>
            <p>Локальный сервер обновлений для тестирования Sparkle</p>
            <p><strong>Адрес:</strong> http://{self.server.server_name}:{self.server.server_port}</p>
        </div>
        
        <h3>📡 Endpoints:</h3>
        <div class="endpoint">
            <strong>AppCast:</strong> <a href="/appcast.xml">/appcast.xml</a>
        </div>
        <div class="endpoint">
            <strong>Update Check API:</strong> <a href="/api/update/check?current=1.70.0">/api/update/check?current=1.70.0</a>
        </div>
        
        <h3>📦 Доступные обновления:</h3>
        <div class="download">
            <strong>Nexy v1.71.0:</strong> <a href="/downloads/Nexy_AI_Voice_Assistant_v1.71.0.pkg">Скачать PKG</a>
        </div>
        
        <h3>🔧 Для тестирования:</h3>
        <p>1. Скопируйте PKG файл в папку <code>updates/downloads/</code></p>
        <p>2. Обновите appcast.xml с правильным URL</p>
        <p>3. Протестируйте обновления в приложении</p>
    </div>
</body>
</html>
        """
        
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))
    
    def _compare_versions(self, v1, v2):
        """Сравнение версий"""
        v1_parts = [int(x) for x in v1.split('.')]
        v2_parts = [int(x) for x in v2.split('.')]
        
        max_len = max(len(v1_parts), len(v2_parts))
        v1_parts.extend([0] * (max_len - len(v1_parts)))
        v2_parts.extend([0] * (max_len - len(v2_parts)))
        
        return (v1_parts > v2_parts) - (v1_parts < v2_parts)
    
    def log_message(self, format, *args):
        """Переопределяем логирование"""
        logger.info(f"{self.address_string()} - {format % args}")

def main():
    """Запуск локального сервера обновлений"""
    port = 8080
    host = 'localhost'
    
    # Создаем директории если их нет
    updates_dir = Path(__file__).parent / "updates"
    downloads_dir = updates_dir / "downloads"
    downloads_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"🚀 Запуск локального сервера обновлений...")
    print(f"📡 Адрес: http://{host}:{port}")
    print(f"📁 Директория: {updates_dir}")
    print(f"📦 Downloads: {downloads_dir}")
    print(f"📄 AppCast: {updates_dir / 'appcast.xml'}")
    print()
    print("🔧 Для тестирования:")
    print(f"   1. Скопируйте PKG в: {downloads_dir}")
    print(f"   2. Откройте: http://{host}:{port}")
    print(f"   3. Проверьте AppCast: http://{host}:{port}/appcast.xml")
    print()
    print("⏹️  Нажмите Ctrl+C для остановки")
    print("=" * 50)
    
    try:
        server = HTTPServer((host, port), UpdateRequestHandler)
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Сервер остановлен")
    except Exception as e:
        print(f"❌ Ошибка сервера: {e}")

if __name__ == "__main__":
    main()

