#!/bin/bash

# Update Server Setup Script
# Настройка серверной части для распространения обновлений через Sparkle

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }

print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_header "UPDATE SERVER SETUP"

# Проверяем, что мы в правильной директории
if [ ! -f "main.py" ]; then
    print_error "Скрипт должен запускаться из директории server/"
    exit 1
fi

# Создаем директории
DOWNLOADS_DIR="downloads"
STATIC_DIR="static"
mkdir -p "$DOWNLOADS_DIR"
mkdir -p "$STATIC_DIR"

print_success "Директории созданы"

# Шаг 1: Создание AppCast файла
print_header "STEP 1: CREATING APPCAST FILE"

APPCAST_FILE="$STATIC_DIR/appcast.xml"
cat > "$APPCAST_FILE" << 'EOF'
<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0" xmlns:sparkle="http://www.andymatuschak.org/xml-namespaces/sparkle">
    <channel>
        <title>Nexy AI Voice Assistant</title>
        <description>AI Voice Assistant for macOS with accessibility features</description>
        <language>en</language>
        <link>https://your-server.com/</link>
        
        <!-- Добавьте новые версии здесь -->
        <item>
            <title>Version 1.71.0</title>
            <description>
                <![CDATA[
                <h2>Nexy AI Voice Assistant v1.71.0</h2>
                <p>Новая версия с улучшенной системой автообновлений</p>
                <ul>
                    <li>Интеграция Sparkle Framework для автообновлений</li>
                    <li>Улучшенная поддержка accessibility</li>
                    <li>Автоматическая установка обновлений для слепых пользователей</li>
                    <li>Исправления ошибок и улучшения производительности</li>
                </ul>
                ]]>
            </description>
            <pubDate>Mon, 01 Jan 2024 00:00:00 +0000</pubDate>
            <enclosure 
                url="https://your-server.com/downloads/Nexy_1.71.0.dmg"
                sparkle:version="1.71.0"
                sparkle:shortVersionString="1.71.0"
                length="1572864000"
                type="application/octet-stream"
                sparkle:dsaSignature="[DSA_SIGNATURE]"
                sparkle:edSignature="[ED25519_SIGNATURE]"/>
        </item>
        
        <item>
            <title>Version 1.70.0</title>
            <description>
                <![CDATA[
                <h2>Nexy AI Voice Assistant v1.70.0</h2>
                <p>Базовая версия с основным функционалом</p>
                <ul>
                    <li>Распознавание речи</li>
                    <li>Генерация ответов через AI</li>
                    <li>Поддержка accessibility</li>
                    <li>Интеграция с macOS</li>
                </ul>
                ]]>
            </description>
            <pubDate>Mon, 01 Dec 2023 00:00:00 +0000</pubDate>
            <enclosure 
                url="https://your-server.com/downloads/Nexy_1.70.0.dmg"
                sparkle:version="1.70.0"
                sparkle:shortVersionString="1.70.0"
                length="1572864000"
                type="application/octet-stream"
                sparkle:dsaSignature="[DSA_SIGNATURE]"
                sparkle:edSignature="[ED25519_SIGNATURE]"/>
        </item>
    </channel>
</rss>
EOF

print_success "AppCast файл создан: $APPCAST_FILE"

# Шаг 2: Создание HTTP endpoints для обновлений
print_header "STEP 2: CREATING UPDATE ENDPOINTS"

UPDATE_SERVICE_FILE="update_service.py"
cat > "$UPDATE_SERVICE_FILE" << 'EOF'
"""
Update Service for Nexy AI Voice Assistant
Сервис для распространения обновлений через Sparkle
"""

import os
import json
import hashlib
import subprocess
from pathlib import Path
from aiohttp import web
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class UpdateService:
    def __init__(self):
        self.downloads_dir = Path("downloads")
        self.static_dir = Path("static")
        self.appcast_file = self.static_dir / "appcast.xml"
        self.versions_file = self.static_dir / "versions.json"
        
        # Создаем директории если их нет
        self.downloads_dir.mkdir(exist_ok=True)
        self.static_dir.mkdir(exist_ok=True)
        
        # Инициализируем файл версий
        self._init_versions_file()
    
    def _init_versions_file(self):
        """Инициализация файла версий"""
        if not self.versions_file.exists():
            versions = {
                "latest": {
                    "version": "1.70.0",
                    "short_version": "1.70.0",
                    "download_url": "https://your-server.com/downloads/Nexy_1.70.0.dmg",
                    "file_size": 1572864000,
                    "release_notes": "Базовая версия с основным функционалом",
                    "title": "Version 1.70.0",
                    "pub_date": "2023-12-01T00:00:00Z"
                },
                "versions": [
                    {
                        "version": "1.70.0",
                        "short_version": "1.70.0",
                        "download_url": "https://your-server.com/downloads/Nexy_1.70.0.dmg",
                        "file_size": 1572864000,
                        "release_notes": "Базовая версия с основным функционалом",
                        "title": "Version 1.70.0",
                        "pub_date": "2023-12-01T00:00:00Z"
                    }
                ]
            }
            
            with open(self.versions_file, 'w') as f:
                json.dump(versions, f, indent=2)
    
    async def get_appcast(self, request):
        """Получение AppCast XML"""
        try:
            if self.appcast_file.exists():
                with open(self.appcast_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                return web.Response(
                    text=content,
                    content_type='application/xml; charset=utf-8'
                )
            else:
                return web.Response(
                    text="AppCast not found",
                    status=404
                )
        except Exception as e:
            logger.error(f"Error serving AppCast: {e}")
            return web.Response(
                text="Internal Server Error",
                status=500
            )
    
    async def get_latest_version(self, request):
        """Получение информации о последней версии"""
        try:
            current_version = request.query.get('current', '1.70.0')
            
            with open(self.versions_file, 'r') as f:
                versions_data = json.load(f)
            
            latest = versions_data['latest']
            
            # Сравниваем версии
            if self._compare_versions(latest['version'], current_version) > 0:
                return web.json_response({
                    'update_available': True,
                    'latest_version': latest['version'],
                    'short_version': latest['short_version'],
                    'download_url': latest['download_url'],
                    'release_notes': latest['release_notes'],
                    'title': latest['title'],
                    'file_size': latest['file_size'],
                    'pub_date': latest['pub_date']
                })
            
            return web.json_response({
                'update_available': False,
                'current_version': current_version
            })
            
        except Exception as e:
            logger.error(f"Error getting latest version: {e}")
            return web.json_response({
                'error': 'Internal Server Error'
            }, status=500)
    
    def _compare_versions(self, v1, v2):
        """Сравнение версий"""
        v1_parts = [int(x) for x in v1.split('.')]
        v2_parts = [int(x) for x in v2.split('.')]
        
        # Дополняем до одинаковой длины
        max_len = max(len(v1_parts), len(v2_parts))
        v1_parts.extend([0] * (max_len - len(v1_parts)))
        v2_parts.extend([0] * (max_len - len(v2_parts)))
        
        return (v1_parts > v2_parts) - (v1_parts < v2_parts)
    
    async def upload_update(self, request):
        """Загрузка нового обновления (для админов)"""
        try:
            # Проверяем авторизацию (простая проверка)
            auth_token = request.headers.get('Authorization')
            if auth_token != 'Bearer your-secret-token':
                return web.json_response({
                    'error': 'Unauthorized'
                }, status=401)
            
            # Получаем данные из multipart form
            data = await request.post()
            
            version = data.get('version')
            dmg_file = data.get('dmg_file')
            
            if not version or not dmg_file:
                return web.json_response({
                    'error': 'Missing version or dmg_file'
                }, status=400)
            
            # Сохраняем DMG файл
            dmg_filename = f"Nexy_{version}.dmg"
            dmg_path = self.downloads_dir / dmg_filename
            
            with open(dmg_path, 'wb') as f:
                f.write(dmg_file.file.read())
            
            # Получаем размер файла
            file_size = dmg_path.stat().st_size
            
            # Обновляем файл версий
            await self._update_versions_file(version, dmg_filename, file_size)
            
            # Обновляем AppCast
            await self._update_appcast(version, dmg_filename, file_size)
            
            return web.json_response({
                'success': True,
                'version': version,
                'file_size': file_size,
                'download_url': f"https://your-server.com/downloads/{dmg_filename}"
            })
            
        except Exception as e:
            logger.error(f"Error uploading update: {e}")
            return web.json_response({
                'error': 'Internal Server Error'
            }, status=500)
    
    async def _update_versions_file(self, version, dmg_filename, file_size):
        """Обновление файла версий"""
        with open(self.versions_file, 'r') as f:
            versions_data = json.load(f)
        
        # Создаем новую версию
        new_version = {
            "version": version,
            "short_version": version,
            "download_url": f"https://your-server.com/downloads/{dmg_filename}",
            "file_size": file_size,
            "release_notes": f"Version {version} - New update",
            "title": f"Version {version}",
            "pub_date": datetime.now().isoformat() + "Z"
        }
        
        # Обновляем latest
        versions_data['latest'] = new_version
        
        # Добавляем в список версий
        versions_data['versions'].insert(0, new_version)
        
        # Сохраняем
        with open(self.versions_file, 'w') as f:
            json.dump(versions_data, f, indent=2)
    
    async def _update_appcast(self, version, dmg_filename, file_size):
        """Обновление AppCast XML"""
        # Здесь можно добавить логику обновления AppCast
        # Пока что просто логируем
        logger.info(f"AppCast should be updated for version {version}")

# Создаем экземпляр сервиса
update_service = UpdateService()

# HTTP endpoints
async def appcast_handler(request):
    return await update_service.get_appcast(request)

async def latest_version_handler(request):
    return await update_service.get_latest_version(request)

async def upload_handler(request):
    return await update_service.upload_update(request)

# Регистрируем routes
def setup_update_routes(app):
    """Настройка маршрутов для обновлений"""
    app.router.add_get('/appcast.xml', appcast_handler)
    app.router.add_get('/api/update/check', latest_version_handler)
    app.router.add_post('/api/update/upload', upload_handler)
EOF

print_success "Update Service создан: $UPDATE_SERVICE_FILE"

# Шаг 3: Обновление main.py сервера
print_header "STEP 3: UPDATING SERVER MAIN"

MAIN_FILE="main.py"
if [ -f "$MAIN_FILE" ]; then
    print_info "Обновление main.py с поддержкой обновлений..."
    
    # Создаем backup
    cp "$MAIN_FILE" "${MAIN_FILE}.backup"
    
    # Добавляем импорт и настройку маршрутов
    cat >> "$MAIN_FILE" << 'EOF'

# Import update service
from update_service import setup_update_routes

# Setup update routes
setup_update_routes(app)
EOF
    
    print_success "main.py обновлен с поддержкой обновлений"
else
    print_warning "main.py не найден"
fi

# Шаг 4: Создание скрипта для загрузки обновлений
print_header "STEP 4: CREATING UPLOAD SCRIPT"

UPLOAD_SCRIPT="upload_update.sh"
cat > "$UPLOAD_SCRIPT" << 'EOF'
#!/bin/bash

# Upload Update Script
# Скрипт для загрузки новых версий на сервер

set -e

if [ $# -ne 2 ]; then
    echo "Usage: $0 <version> <dmg_file>"
    echo "Example: $0 1.71.0 /path/to/Nexy_1.71.0.dmg"
    exit 1
fi

VERSION="$1"
DMG_FILE="$2"
SERVER_URL="https://your-server.com"

if [ ! -f "$DMG_FILE" ]; then
    echo "❌ DMG файл не найден: $DMG_FILE"
    exit 1
fi

echo "📤 Загрузка обновления $VERSION..."

# Загружаем файл
curl -X POST \
  -H "Authorization: Bearer your-secret-token" \
  -F "version=$VERSION" \
  -F "dmg_file=@$DMG_FILE" \
  "$SERVER_URL/api/update/upload"

echo ""
echo "✅ Обновление $VERSION загружено успешно!"
echo "🔗 AppCast: $SERVER_URL/appcast.xml"
EOF

chmod +x "$UPLOAD_SCRIPT"
print_success "Скрипт загрузки создан: $UPLOAD_SCRIPT"

# Шаг 5: Создание nginx конфигурации
print_header "STEP 5: CREATING NGINX CONFIG"

NGINX_CONFIG="nginx_update.conf"
cat > "$NGINX_CONFIG" << 'EOF'
# Nginx configuration for Update Server
# Конфигурация Nginx для сервера обновлений

server {
    listen 80;
    server_name your-server.com;
    
    # AppCast XML
    location /appcast.xml {
        alias /path/to/your/server/static/appcast.xml;
        add_header Content-Type application/xml;
        add_header Cache-Control "no-cache, no-store, must-revalidate";
    }
    
    # Downloads directory
    location /downloads/ {
        alias /path/to/your/server/downloads/;
        add_header Content-Type application/octet-stream;
        add_header Content-Disposition "attachment";
        
        # CORS headers
        add_header Access-Control-Allow-Origin "*";
        add_header Access-Control-Allow-Methods "GET, POST, OPTIONS";
        add_header Access-Control-Allow-Headers "Authorization, Content-Type";
    }
    
    # API endpoints
    location /api/update/ {
        proxy_pass http://localhost:50051;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Health check
    location /health {
        proxy_pass http://localhost:50051;
    }
}
EOF

print_success "Nginx конфигурация создана: $NGINX_CONFIG"

print_header "UPDATE SERVER SETUP COMPLETED"

print_success "🎉 Сервер обновлений настроен успешно!"
echo ""
print_info "Созданные файлы:"
echo "   📄 AppCast: $APPCAST_FILE"
echo "   🐍 Update Service: $UPDATE_SERVICE_FILE"
echo "   📤 Upload Script: $UPLOAD_SCRIPT"
echo "   🌐 Nginx Config: $NGINX_CONFIG"
echo ""
print_info "Следующие шаги:"
echo "   1. Настройте домен и SSL сертификат"
echo "   2. Обновите URL в конфигурации"
echo "   3. Загрузите DMG файлы в downloads/"
echo "   4. Обновите appcast.xml с правильными подписями"
echo "   5. Протестируйте систему обновлений"
echo ""
print_info "Для тестирования:"
echo "   curl https://your-server.com/appcast.xml"
echo "   curl https://your-server.com/api/update/check?current=1.70.0"
echo ""
print_success "Готово к распространению обновлений!"

