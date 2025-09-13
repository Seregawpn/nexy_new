#!/usr/bin/env python3
"""
Скрипт для настройки продакшн сервера системы автообновлений
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

def create_directory_structure(server_path):
    """Создание структуры директорий на сервере"""
    directories = [
        "downloads",
        "keys", 
        "scripts",
        "logs"
    ]
    
    for directory in directories:
        dir_path = Path(server_path) / directory
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"✅ Создана директория: {dir_path}")

def create_appcast_xml(server_path, domain):
    """Создание AppCast XML файла"""
    appcast_content = f'''<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0" xmlns:sparkle="http://www.andymatuschak.org/xml-namespaces/sparkle">
    <channel>
        <title>Nexy Updates</title>
        <description>Автоматические обновления для Nexy</description>
        <language>ru</language>
        <lastBuildDate>Mon, 07 Sep 2025 18:00:00 +0000</lastBuildDate>
        
        <item>
            <title>Nexy 1.71.0</title>
            <description>
                <![CDATA[
                <h2>Что нового в версии 1.71.0:</h2>
                <ul>
                    <li>Добавлена система автообновлений</li>
                    <li>Улучшена поддержка accessibility</li>
                    <li>Исправлены мелкие ошибки</li>
                </ul>
                ]]>
            </description>
            <pubDate>Mon, 07 Sep 2025 18:00:00 +0000</pubDate>
            <enclosure url="https://{domain}/downloads/Nexy_1.71.0.dmg"
                       sparkle:version="1.71.0"
                       sparkle:shortVersionString="1.71.0"
                       length="10485760"
                       type="application/octet-stream"
                       sparkle:edSignature="SIGNATURE_PLACEHOLDER"/>
        </item>
    </channel>
</rss>'''
    
    appcast_path = Path(server_path) / "appcast.xml"
    with open(appcast_path, 'w', encoding='utf-8') as f:
        f.write(appcast_content)
    
    print(f"✅ Создан AppCast XML: {appcast_path}")

def create_update_script(server_path):
    """Создание скрипта для обновления AppCast"""
    script_content = '''#!/bin/bash
# Скрипт для обновления AppCast XML

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_DIR="$(dirname "$SCRIPT_DIR")"
APPCAST_FILE="$SERVER_DIR/appcast.xml"

echo "🔄 Обновление AppCast XML..."

# Проверяем наличие нового DMG файла
if [ -z "$1" ]; then
    echo "❌ Ошибка: Укажите путь к DMG файлу"
    echo "Использование: $0 /path/to/Nexy_1.72.0.dmg"
    exit 1
fi

DMG_FILE="$1"
VERSION=$(basename "$DMG_FILE" .dmg | sed 's/Nexy_//')

if [ ! -f "$DMG_FILE" ]; then
    echo "❌ Ошибка: Файл $DMG_FILE не найден"
    exit 1
fi

# Копируем DMG файл в downloads
cp "$DMG_FILE" "$SERVER_DIR/downloads/"

# Получаем размер файла
FILE_SIZE=$(stat -f%z "$DMG_FILE")

# Генерируем подпись (если есть ключ)
if [ -f "$SERVER_DIR/keys/ed25519_private.pem" ]; then
    SIGNATURE=$(./sign_update.sh "$DMG_FILE")
else
    SIGNATURE="SIGNATURE_PLACEHOLDER"
    echo "⚠️  Предупреждение: Ключ подписи не найден, используется заглушка"
fi

# Обновляем AppCast XML
python3 -c "
import xml.etree.ElementTree as ET
from datetime import datetime

# Загружаем существующий AppCast
tree = ET.parse('$APPCAST_FILE')
root = tree.getroot()

# Создаем новый item
channel = root.find('channel')
new_item = ET.SubElement(channel, 'item')

# Заполняем данные
title = ET.SubElement(new_item, 'title')
title.text = f'Nexy {VERSION}'

description = ET.SubElement(new_item, 'description')
description.text = f'<![CDATA[<h2>Что нового в версии {VERSION}:</h2><ul><li>Улучшения и исправления</li></ul>]]>'

pub_date = ET.SubElement(new_item, 'pubDate')
pub_date.text = datetime.now().strftime('%a, %d %b %Y %H:%M:%S +0000')

enclosure = ET.SubElement(new_item, 'enclosure')
enclosure.set('url', f'https://{os.environ.get(\"DOMAIN\", \"your-domain.com\")}/downloads/Nexy_{VERSION}.dmg')
enclosure.set('sparkle:version', VERSION)
enclosure.set('sparkle:shortVersionString', VERSION)
enclosure.set('length', str($FILE_SIZE))
enclosure.set('type', 'application/octet-stream')
enclosure.set('sparkle:edSignature', '$SIGNATURE')

# Сохраняем обновленный AppCast
tree.write('$APPCAST_FILE', encoding='utf-8', xml_declaration=True)
"

echo "✅ AppCast XML обновлен для версии $VERSION"
echo "📁 DMG файл скопирован в downloads/"
echo "🔗 URL: https://$(echo $DOMAIN || echo 'your-domain.com')/downloads/Nexy_$VERSION.dmg"
'''
    
    script_path = Path(server_path) / "scripts" / "update_appcast.sh"
    with open(script_path, 'w') as f:
        f.write(script_content)
    
    # Делаем скрипт исполняемым
    os.chmod(script_path, 0o755)
    print(f"✅ Создан скрипт обновления: {script_path}")

def create_sign_script(server_path):
    """Создание скрипта для подписи обновлений"""
    script_content = '''#!/bin/bash
# Скрипт для подписи DMG файлов

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_DIR="$(dirname "$SCRIPT_DIR")"
PRIVATE_KEY="$SERVER_DIR/keys/ed25519_private.pem"

if [ -z "$1" ]; then
    echo "❌ Ошибка: Укажите путь к DMG файлу"
    echo "Использование: $0 /path/to/Nexy_1.72.0.dmg"
    exit 1
fi

DMG_FILE="$1"

if [ ! -f "$DMG_FILE" ]; then
    echo "❌ Ошибка: Файл $DMG_FILE не найден"
    exit 1
fi

if [ ! -f "$PRIVATE_KEY" ]; then
    echo "❌ Ошибка: Приватный ключ не найден: $PRIVATE_KEY"
    echo "Скопируйте ed25519_private.pem в $PRIVATE_KEY"
    exit 1
fi

# Генерируем подпись
echo "🔐 Генерация подписи для $DMG_FILE..."

# Используем Sparkle для подписи (если доступен)
if command -v sparkle-cli &> /dev/null; then
    SIGNATURE=$(sparkle-cli sign "$DMG_FILE" --private-key "$PRIVATE_KEY")
else
    # Fallback: используем openssl
    SIGNATURE=$(openssl dgst -sha256 -sign "$PRIVATE_KEY" "$DMG_FILE" | base64)
fi

echo "✅ Подпись сгенерирована: $SIGNATURE"
echo "$SIGNATURE"
'''
    
    script_path = Path(server_path) / "scripts" / "sign_update.sh"
    with open(script_path, 'w') as f:
        f.write(script_content)
    
    # Делаем скрипт исполняемым
    os.chmod(script_path, 0o755)
    print(f"✅ Создан скрипт подписи: {script_path}")

def create_nginx_config(server_path, domain):
    """Создание конфигурации Nginx"""
    nginx_config = f'''server {{
    listen 80;
    server_name {domain};
    return 301 https://$server_name$request_uri;
}}

server {{
    listen 443 ssl http2;
    server_name {domain};
    
    # SSL конфигурация
    ssl_certificate /etc/letsencrypt/live/{domain}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{domain}/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    
    # Корневая директория
    root /var/www/updates;
    index appcast.xml;
    
    # Логирование
    access_log /var/log/nginx/updates_access.log;
    error_log /var/log/nginx/updates_error.log;
    
    # AppCast XML
    location = /appcast.xml {{
        add_header Content-Type application/xml;
        add_header Cache-Control "no-cache, no-store, must-revalidate";
        add_header Pragma "no-cache";
        add_header Expires "0";
    }}
    
    # DMG файлы
    location /downloads/ {{
        add_header Content-Type application/octet-stream;
        add_header Content-Disposition "attachment";
        expires 1y;
        add_header Cache-Control "public, immutable";
    }}
    
    # Безопасность
    location ~ /\\. {{
        deny all;
    }}
    
    location ~ /keys/ {{
        deny all;
    }}
    
    # CORS для API
    add_header Access-Control-Allow-Origin "*" always;
    add_header Access-Control-Allow-Methods "GET, POST, OPTIONS" always;
    add_header Access-Control-Allow-Headers "Content-Type, Authorization" always;
    
    if ($request_method = 'OPTIONS') {{
        add_header Access-Control-Allow-Origin "*";
        add_header Access-Control-Allow-Methods "GET, POST, OPTIONS";
        add_header Access-Control-Allow-Headers "Content-Type, Authorization";
        add_header Access-Control-Max-Age 1728000;
        add_header Content-Type "text/plain; charset=utf-8";
        add_header Content-Length 0;
        return 204;
    }}
}}'''
    
    config_path = Path(server_path) / "nginx.conf"
    with open(config_path, 'w') as f:
        f.write(nginx_config)
    
    print(f"✅ Создана конфигурация Nginx: {config_path}")

def create_deployment_script(server_path):
    """Создание скрипта для развертывания"""
    script_content = f'''#!/bin/bash
# Скрипт для развертывания на сервере

set -e

SERVER_USER="$1"
SERVER_HOST="$2"
SERVER_PATH="/var/www/updates"

if [ -z "$SERVER_USER" ] || [ -z "$SERVER_HOST" ]; then
    echo "❌ Ошибка: Укажите пользователя и хост сервера"
    echo "Использование: $0 user@server.com"
    exit 1
fi

echo "🚀 Развертывание на сервер $SERVER_USER@$SERVER_HOST..."

# Создаем директории на сервере
ssh "$SERVER_USER@$SERVER_HOST" "mkdir -p $SERVER_PATH/{{downloads,keys,scripts,logs}}"

# Загружаем файлы
echo "📁 Загрузка файлов..."
scp appcast.xml "$SERVER_USER@$SERVER_HOST:$SERVER_PATH/"
scp nginx.conf "$SERVER_USER@$SERVER_HOST:$SERVER_PATH/"

# Загружаем скрипты
scp scripts/*.sh "$SERVER_USER@$SERVER_HOST:$SERVER_PATH/scripts/"

# Устанавливаем права доступа
ssh "$SERVER_USER@$SERVER_HOST" "chmod 755 $SERVER_PATH/scripts/*.sh"
ssh "$SERVER_USER@$SERVER_HOST" "chmod 644 $SERVER_PATH/appcast.xml"

echo "✅ Развертывание завершено!"
echo "🔗 AppCast: https://$SERVER_HOST/appcast.xml"
echo "📁 Downloads: https://$SERVER_HOST/downloads/"
'''
    
    script_path = Path(server_path) / "deploy.sh"
    with open(script_path, 'w') as f:
        f.write(script_content)
    
    # Делаем скрипт исполняемым
    os.chmod(script_path, 0o755)
    print(f"✅ Создан скрипт развертывания: {script_path}")

def main():
    """Главная функция"""
    print("🚀 НАСТРОЙКА ПРОДАКШН СЕРВЕРА ДЛЯ СИСТЕМЫ АВТООБНОВЛЕНИЙ")
    print("=" * 60)
    
    # Получаем параметры
    if len(sys.argv) < 3:
        print("❌ Ошибка: Укажите домен и путь к серверу")
        print("Использование: python3 setup_production_server.py your-domain.com /path/to/server")
        sys.exit(1)
    
    domain = sys.argv[1]
    server_path = sys.argv[2]
    
    print(f"🌐 Домен: {domain}")
    print(f"📁 Путь к серверу: {server_path}")
    print()
    
    # Создаем структуру
    create_directory_structure(server_path)
    create_appcast_xml(server_path, domain)
    create_update_script(server_path)
    create_sign_script(server_path)
    create_nginx_config(server_path, domain)
    create_deployment_script(server_path)
    
    print()
    print("=" * 60)
    print("✅ НАСТРОЙКА ЗАВЕРШЕНА!")
    print("=" * 60)
    print("📋 Следующие шаги:")
    print("1. Скопируйте ed25519_private.pem в keys/")
    print("2. Загрузите DMG файлы в downloads/")
    print("3. Настройте Nginx с созданной конфигурацией")
    print("4. Установите SSL сертификат")
    print("5. Протестируйте endpoints")
    print()
    print("🔧 Команды для развертывания:")
    print(f"   ./deploy.sh user@{domain}")
    print()
    print("📡 Endpoints после развертывания:")
    print(f"   AppCast: https://{domain}/appcast.xml")
    print(f"   Downloads: https://{domain}/downloads/")

if __name__ == "__main__":
    main()

