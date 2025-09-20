#!/usr/bin/env python3
"""
Простой HTTP сервер для тестирования Sparkle AppCast
Запускает локальный сервер на localhost:8080
"""

import http.server
import socketserver
import os
import sys
from pathlib import Path

# Порт для сервера
PORT = 8080

class AppCastHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Добавляем CORS заголовки для локальной разработки
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()
    
    def do_GET(self):
        # Логируем запросы
        print(f"📥 GET запрос: {self.path}")
        
        # Если запрашивается appcast.xml
        if self.path == '/updates/appcast.xml':
            appcast_path = Path(__file__).parent / 'updates' / 'appcast.xml'
            if appcast_path.exists():
                self.send_response(200)
                self.send_header('Content-type', 'application/rss+xml')
                self.end_headers()
                with open(appcast_path, 'rb') as f:
                    self.wfile.write(f.read())
                print(f"✅ Отправлен appcast.xml")
                return
        
        # Если запрашивается PKG файл
        if self.path.startswith('/updates/') and self.path.endswith('.pkg'):
            pkg_name = os.path.basename(self.path)
            pkg_path = Path(__file__).parent.parent.parent / pkg_name
            if pkg_path.exists():
                self.send_response(200)
                self.send_header('Content-type', 'application/octet-stream')
                self.send_header('Content-Disposition', f'attachment; filename="{pkg_name}"')
                self.end_headers()
                with open(pkg_path, 'rb') as f:
                    self.wfile.write(f.read())
                print(f"✅ Отправлен PKG файл: {pkg_name}")
                return
            else:
                print(f"❌ PKG файл не найден: {pkg_path}")
                self.send_response(404)
                self.end_headers()
                return
        
        # Для всех остальных запросов используем стандартный обработчик
        super().do_GET()

def main():
    # Переходим в директорию сервера
    os.chdir(Path(__file__).parent)
    
    print(f"🚀 Запуск локального сервера для Sparkle AppCast")
    print(f"📍 URL: http://localhost:{PORT}")
    print(f"📋 AppCast: http://localhost:{PORT}/updates/appcast.xml")
    print(f"📦 PKG файлы: http://localhost:{PORT}/updates/")
    print(f"⏹️  Для остановки нажмите Ctrl+C")
    print("-" * 50)
    
    try:
        with socketserver.TCPServer(("", PORT), AppCastHandler) as httpd:
            print(f"✅ Сервер запущен на порту {PORT}")
            httpd.serve_forever()
    except KeyboardInterrupt:
        print(f"\n⏹️  Сервер остановлен")
    except OSError as e:
        if e.errno == 48:  # Address already in use
            print(f"❌ Порт {PORT} уже используется. Попробуйте другой порт.")
            sys.exit(1)
        else:
            raise

if __name__ == "__main__":
    main()
