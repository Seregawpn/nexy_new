# 🔄 Внедрение новой системы обновлений "без пароля"

**Дата:** 19 сентября 2025  
**Статус:** Готов к реализации  
**Время реализации:** 4-5 часов  

## 🎯 Цель

Заменить неработающую систему обновлений Sparkle на простую и надежную HTTP-систему с миграцией в `~/Applications`, обеспечивающую автоматические обновления без запроса пароля после первой установки.

---

## 📋 Обзор изменений

### **Текущее состояние (проблемы)**
- ❌ `update_manager.enabled: false` - система отключена
- ❌ SparkleHandler содержит только заглушки
- ❌ Нет PKG файлов для обновлений
- ❌ Сложная интеграция с PyInstaller
- ❌ Требует пароль при каждом обновлении

### **Целевое состояние**
- ✅ Простая HTTP-система с JSON манифестом
- ✅ Миграция в `~/Applications` (пароль только один раз)
- ✅ Атомарная замена .app файлов
- ✅ Многоуровневая безопасность (sha256 + ed25519 + codesign)
- ✅ Полная интеграция с EventBus архитектурой

---

## 🏗️ Архитектура новой системы

### **Принцип работы**
1. **Первый запуск**: PKG → миграция в `~/Applications/Nexy.app`
2. **Периодические проверки**: HTTP запрос к манифесту
3. **Обновление**: DMG → проверки → атомарная замена → перезапуск
4. **Безопасность**: 3 уровня проверки (hash, signature, codesign)

### **Структура файлов**
```
client/
├── modules/updater/                    # Новый модуль обновлений
│   ├── __init__.py
│   ├── config.py                      # Конфигурация
│   ├── net.py                         # HTTP клиент
│   ├── verify.py                      # Проверки безопасности
│   ├── dmg.py                         # Работа с DMG
│   ├── replace.py                     # Атомарная замена
│   ├── migrate.py                     # Миграция в ~/Applications
│   ├── updater.py                     # Основная логика
│   └── scheduler.py                   # Планировщик
├── integration/integrations/
│   └── updater_integration.py         # Замена UpdateManagerIntegration
└── config/
    └── unified_config.yaml            # Обновленная конфигурация

server/
├── update_server.py                   # Обновленный сервер
├── updates/
│   ├── manifests/
│   │   └── manifest.json              # JSON манифест
│   ├── artifacts/
│   │   └── Nexy-2.6.0.dmg            # DMG файлы
│   └── scripts/
│       ├── make_dmg.sh                # Создание DMG
│       ├── sign_ed25519.py            # Подпись артефактов
│       └── make_manifest.py           # Генерация манифеста
```

---

## 🔧 Этап 1: Подготовка (30 минут)

### **1.1 Создание структуры модулей**
```bash
# Создаем новую структуру
mkdir -p client/modules/updater
mkdir -p server/updates/{artifacts,manifests,scripts}

# Устанавливаем зависимости
pip install urllib3 pynacl packaging
```

### **1.2 Обновление requirements.txt**
```bash
echo "urllib3>=1.26.0" >> client/requirements.txt
echo "pynacl>=1.5.0" >> client/requirements.txt
echo "packaging>=21.0" >> client/requirements.txt
```

### **1.3 Обновление конфигурации**
```yaml
# client/config/unified_config.yaml - добавить секцию
updater:
  enabled: true
  manifest_url: "https://updates.nexy.ai/manifest.json"
  check_interval: 3600
  auto_install: true
  security:
    public_key: "BASE64_PUBLIC_ED25519_KEY"
  timeout: 20
  retries: 3
  ui:
    show_notifications: true
    auto_download: true
```

---

## 🚀 Этап 2: Реализация модулей (3-4 часа)

### **2.1 Базовые модули**

#### **config.py** - Конфигурация обновлений
```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class UpdaterConfig:
    enabled: bool = True
    manifest_url: str = ""
    check_interval: int = 3600
    auto_install: bool = True
    public_key: str = ""
    timeout: int = 20
    retries: int = 3
    show_notifications: bool = True
    auto_download: bool = True
```

#### **net.py** - HTTP клиент с ретраями
```python
import urllib3
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class UpdateHTTPClient:
    def __init__(self, timeout: int = 20, retries: int = 3):
        self.http = urllib3.PoolManager(
            retries=urllib3.Retry(total=retries, backoff_factor=0.5),
            timeout=urllib3.Timeout(total=timeout)
        )
    
    def get_manifest(self, url: str) -> dict:
        """Получение манифеста обновлений"""
        response = self.http.request("GET", url)
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status}")
        return response.json()
    
    def download_file(self, url: str, dest_path: str, expected_size: Optional[int] = None):
        """Скачивание файла с проверкой размера"""
        with self.http.request("GET", url, preload_content=False) as response:
            if response.status != 200:
                raise RuntimeError(f"HTTP {response.status}")
            
            with open(dest_path, "wb") as f:
                for chunk in response.stream(1024 * 1024):
                    f.write(chunk)
        
        if expected_size and os.path.getsize(dest_path) != expected_size:
            raise RuntimeError("Размер файла не совпадает")
```

#### **verify.py** - Проверки безопасности
```python
import hashlib
import base64
import subprocess
from nacl.signing import VerifyKey
from typing import Optional

def sha256_checksum(file_path: str) -> str:
    """Вычисление SHA256 хеша файла"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()

def verify_ed25519_signature(file_path: str, signature_b64: str, public_key_b64: str) -> bool:
    """Проверка Ed25519 подписи"""
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        
        verify_key = VerifyKey(base64.b64decode(public_key_b64))
        signature = base64.b64decode(signature_b64)
        verify_key.verify(data, signature)
        return True
    except Exception:
        return False

def verify_app_signature(app_path: str) -> bool:
    """Проверка подписи приложения"""
    try:
        subprocess.check_call([
            "/usr/bin/codesign", "--verify", "--deep", "--strict", "--verbose=2", app_path
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        subprocess.check_call([
            "/usr/sbin/spctl", "-a", "-vv", "--type", "execute", app_path
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        return True
    except subprocess.CalledProcessError:
        return False
```

### **2.2 Модули работы с файлами**

#### **dmg.py** - Работа с DMG файлами
```python
import subprocess
import os
import tempfile
from typing import Optional

def mount_dmg(dmg_path: str) -> str:
    """Монтирование DMG файла"""
    mount_point = tempfile.mkdtemp(prefix="nexy_mount_")
    subprocess.check_call([
        "/usr/bin/hdiutil", "attach", "-nobrowse", "-mountpoint", mount_point, dmg_path
    ])
    return mount_point

def unmount_dmg(mount_point: str):
    """Размонтирование DMG"""
    subprocess.check_call(["/usr/bin/hdiutil", "detach", mount_point])

def find_app_in_dmg(mount_point: str, app_name: str = "Nexy.app") -> Optional[str]:
    """Поиск .app файла в DMG"""
    app_path = os.path.join(mount_point, app_name)
    if os.path.isdir(app_path):
        return app_path
    
    for root, dirs, files in os.walk(mount_point):
        for dir_name in dirs:
            if dir_name.endswith(".app"):
                return os.path.join(root, dir_name)
    
    return None
```

#### **replace.py** - Атомарная замена
```python
import os
import shutil
import subprocess

def atomic_replace_app(new_app_path: str, target_app_path: str):
    """Атомарная замена приложения с возможностью отката"""
    backup_path = target_app_path + ".backup"
    
    if os.path.exists(backup_path):
        shutil.rmtree(backup_path, ignore_errors=True)
    
    os.rename(target_app_path, backup_path)
    
    try:
        subprocess.check_call(["/usr/bin/ditto", new_app_path, target_app_path])
        shutil.rmtree(backup_path, ignore_errors=True)
        print("✅ Приложение успешно обновлено")
    except Exception as e:
        if os.path.exists(target_app_path):
            shutil.rmtree(target_app_path, ignore_errors=True)
        os.rename(backup_path, target_app_path)
        print(f"❌ Ошибка обновления, выполнен откат: {e}")
        raise
```

### **2.3 Миграция и основная логика**

#### **migrate.py** - Миграция в ~/Applications
```python
import os
import subprocess
from pathlib import Path

def get_current_app_path() -> str:
    """Получение пути к текущему приложению"""
    try:
        from Cocoa import NSBundle
        bundle_path = NSBundle.mainBundle().bundlePath()
        if bundle_path and bundle_path.endswith(".app"):
            return bundle_path
    except ImportError:
        pass
    
    return "/Applications/Nexy.app"

def get_user_app_path() -> str:
    """Получение пути к пользовательской папке Applications"""
    user_home = Path.home()
    user_apps = user_home / "Applications"
    user_apps.mkdir(exist_ok=True)
    return str(user_apps / "Nexy.app")

def migrate_to_user_directory() -> bool:
    """Миграция приложения в пользовательскую папку"""
    current_path = get_current_app_path()
    user_path = get_user_app_path()
    
    if os.path.realpath(current_path) == os.path.realpath(user_path):
        return False
    
    print(f"🔄 Миграция из {current_path} в {user_path}")
    
    if os.path.exists(user_path):
        shutil.rmtree(user_path, ignore_errors=True)
    
    subprocess.check_call(["/usr/bin/ditto", current_path, user_path])
    subprocess.Popen(["/usr/bin/open", "-a", user_path])
    os._exit(0)
    
    return True
```

#### **updater.py** - Основная логика обновлений
```python
import json
import tempfile
import os
import subprocess
from typing import Optional, Dict, Any
from .config import UpdaterConfig
from .net import UpdateHTTPClient
from .verify import sha256_checksum, verify_ed25519_signature, verify_app_signature
from .dmg import mount_dmg, unmount_dmg, find_app_in_dmg
from .replace import atomic_replace_app
from .migrate import get_user_app_path

class Updater:
    def __init__(self, config: UpdaterConfig):
        self.config = config
        self.http_client = UpdateHTTPClient(config.timeout, config.retries)
    
    def get_current_build(self) -> int:
        """Получение текущего номера сборки"""
        try:
            import plistlib
            info_plist_path = os.path.join(get_user_app_path(), "Contents", "Info.plist")
            with open(info_plist_path, "rb") as f:
                plist = plistlib.load(f)
            return int(plist.get("CFBundleVersion", 0))
        except Exception:
            return 0
    
    def check_for_updates(self) -> Optional[Dict[str, Any]]:
        """Проверка доступности обновлений"""
        try:
            manifest = self.http_client.get_manifest(self.config.manifest_url)
            current_build = self.get_current_build()
            latest_build = int(manifest.get("build", 0))
            
            if latest_build > current_build:
                return manifest
            return None
        except Exception as e:
            print(f"❌ Ошибка проверки обновлений: {e}")
            return None
    
    def update(self) -> bool:
        """Полный цикл обновления"""
        try:
            manifest = self.check_for_updates()
            if not manifest:
                return False
            
            print(f"🔄 Найдено обновление до версии {manifest.get('version')}")
            
            # Скачиваем и проверяем
            artifact_info = manifest["artifact"]
            temp_file = self._download_and_verify(artifact_info)
            
            # Устанавливаем
            self._install_update(temp_file, artifact_info)
            
            # Перезапускаем
            self._relaunch_app()
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка обновления: {e}")
            return False
```

---

## 🔌 Этап 3: Интеграция с EventBus (30 минут)

### **3.1 UpdaterIntegration**
```python
# client/integration/integrations/updater_integration.py
import asyncio
import logging
from typing import Dict, Any

from core.event_bus import EventBus, EventPriority
from core.state_manager import ApplicationStateManager
from modules.updater import Updater, UpdaterConfig, migrate_to_user_directory

logger = logging.getLogger(__name__)

class UpdaterIntegration:
    def __init__(self, event_bus: EventBus, state_manager: ApplicationStateManager, config: Dict[str, Any]):
        self.event_bus = event_bus
        self.state_manager = state_manager
        
        updater_config = UpdaterConfig(
            enabled=config.get("enabled", True),
            manifest_url=config.get("manifest_url", ""),
            check_interval=config.get("check_interval", 3600),
            auto_install=config.get("auto_install", True),
            public_key=config.get("security", {}).get("public_key", ""),
            timeout=config.get("timeout", 20),
            retries=config.get("retries", 3)
        )
        
        self.updater = Updater(updater_config)
        self.check_task = None
        self.is_running = False
    
    async def initialize(self) -> bool:
        """Инициализация интеграции"""
        try:
            logger.info("🔄 Инициализация UpdaterIntegration...")
            
            # Миграция в пользовательскую папку (один раз)
            migrate_to_user_directory()
            
            await self._setup_event_handlers()
            logger.info("✅ UpdaterIntegration инициализирован")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации UpdaterIntegration: {e}")
            return False
    
    async def start(self) -> bool:
        """Запуск интеграции"""
        try:
            if not self.updater.config.enabled:
                logger.info("⏭️ Пропускаю запуск UpdaterIntegration - отключен")
                return True
            
            logger.info("🚀 Запуск UpdaterIntegration...")
            self.check_task = asyncio.create_task(self._check_loop())
            self.is_running = True
            logger.info("✅ UpdaterIntegration запущен")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска UpdaterIntegration: {e}")
            return False
    
    async def _check_loop(self):
        """Цикл проверки обновлений"""
        while self.is_running:
            try:
                if await self._can_update():
                    if self.updater.update():
                        return  # Приложение перезапустится
                
                await asyncio.sleep(self.updater.config.check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Ошибка в цикле проверки обновлений: {e}")
                await asyncio.sleep(300)
    
    async def _can_update(self) -> bool:
        """Проверка, можно ли обновляться"""
        current_mode = self.state_manager.get_current_mode()
        return current_mode not in ["LISTENING", "PROCESSING"]
    
    async def _setup_event_handlers(self):
        """Настройка обработчиков событий"""
        await self.event_bus.subscribe("app.startup", self._on_app_startup, EventPriority.MEDIUM)
        await self.event_bus.subscribe("app.shutdown", self._on_app_shutdown, EventPriority.HIGH)
        await self.event_bus.subscribe("updater.check_manual", self._on_manual_check, EventPriority.HIGH)
    
    async def _on_app_startup(self, event_data):
        logger.info("🚀 Обработка запуска приложения в UpdaterIntegration")
    
    async def _on_app_shutdown(self, event_data):
        logger.info("🛑 Обработка завершения приложения в UpdaterIntegration")
        await self.stop()
    
    async def _on_manual_check(self, event_data):
        logger.info("🔍 Ручная проверка обновлений")
        if await self._can_update():
            self.updater.update()
    
    async def stop(self):
        if self.check_task:
            self.check_task.cancel()
        self.is_running = False
        logger.info("✅ UpdaterIntegration остановлен")
```

### **3.2 Обновление SimpleModuleCoordinator**
```python
# client/integration/core/simple_module_coordinator.py
# Добавить в список интеграций:
from integrations.updater_integration import UpdaterIntegration

# В методе initialize_integrations():
if "updater" in self.config:
    integration = UpdaterIntegration(
        self.event_bus, 
        self.state_manager, 
        self.config["updater"]
    )
    await integration.initialize()
    self.integrations["updater"] = integration
```

---

## 🖥️ Этап 4: Серверная часть (1 час)

### **4.1 JSON манифест**
```json
{
  "version": "2.6.0",
  "build": 20600,
  "release_date": "2025-09-19T10:00:00Z",
  "artifact": {
    "type": "dmg",
    "url": "https://updates.nexy.ai/Nexy-2.6.0.dmg",
    "size": 12345678,
    "sha256": "a1b2c3d4e5f6...",
    "ed25519": "BASE64_SIGNATURE_HERE",
    "arch": "universal2",
    "min_os": "11.0"
  },
  "notes_url": "https://nexy.ai/changelog/2.6.0"
}
```

### **4.2 Скрипты сборки**

#### **make_dmg.sh**
```bash
#!/bin/bash
# Создание DMG файла

APP_PATH="dist/Nexy.app"
DMG_PATH="dist/Nexy-${VERSION}.dmg"

# Создаем DMG
create-dmg --volname "Nexy ${VERSION}" \
  --window-size 480 320 \
  --app-drop-link 240 170 \
  --overwrite \
  "$DMG_PATH" \
  "$APP_PATH"

echo "✅ DMG создан: $DMG_PATH"
```

#### **sign_ed25519.py**
```python
#!/usr/bin/env python3
import base64
import sys
from nacl.signing import SigningKey

def sign_file(file_path: str, private_key_b64: str) -> str:
    """Подписание файла Ed25519 ключом"""
    with open(file_path, "rb") as f:
        data = f.read()
    
    signing_key = SigningKey(base64.b64decode(private_key_b64))
    signature = signing_key.sign(data)
    
    return base64.b64encode(signature.signature).decode("utf-8")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python sign_ed25519.py <file_path> <private_key_b64>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    private_key_b64 = sys.argv[2]
    
    signature = sign_file(file_path, private_key_b64)
    print(signature)
```

### **4.3 Обновленный update_server.py**
```python
# server/update_server.py - добавить endpoint для манифеста
async def manifest_handler(self, request):
    """Обработчик манифеста обновлений"""
    try:
        manifest_file = self.updates_dir / "manifests" / "manifest.json"
        if manifest_file.exists():
            with open(manifest_file, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
            
            return web.json_response(
                manifest,
                headers={
                    'Cache-Control': 'no-cache, no-store, must-revalidate',
                    'Pragma': 'no-cache',
                    'Expires': '0'
                }
            )
        else:
            return web.Response(text="Manifest not found", status=404)
    except Exception as e:
        logger.error(f"❌ Ошибка чтения манифеста: {e}")
        return web.Response(text="Error reading manifest", status=500)

# Добавить в create_app():
app.router.add_get('/manifest.json', self.manifest_handler)
```

---

## 🧪 Этап 5: Тестирование (1 час)

### **5.1 Локальное тестирование**
```bash
# 1. Тест миграции
python -c "from modules.updater.migrate import migrate_to_user_directory; migrate_to_user_directory()"

# 2. Тест проверки обновлений
python -c "from modules.updater.updater import Updater; u = Updater(config); print(u.check_for_updates())"

# 3. Тест скачивания
python -c "from modules.updater.net import UpdateHTTPClient; c = UpdateHTTPClient(); c.download_file('http://example.com/test.dmg', '/tmp/test.dmg')"
```

### **5.2 Интеграционные тесты**
```python
# client/modules/updater/test_updater.py
import unittest
from unittest.mock import Mock, patch
from .updater import Updater
from .config import UpdaterConfig

class TestUpdater(unittest.TestCase):
    def setUp(self):
        self.config = UpdaterConfig(
            manifest_url="http://localhost:8081/manifest.json",
            enabled=True
        )
        self.updater = Updater(self.config)
    
    def test_check_for_updates(self):
        with patch.object(self.updater.http_client, 'get_manifest') as mock_get:
            mock_get.return_value = {
                "version": "2.6.0",
                "build": 20600,
                "artifact": {"type": "dmg", "url": "http://test.com/test.dmg"}
            }
            
            result = self.updater.check_for_updates()
            self.assertIsNotNone(result)
            self.assertEqual(result["version"], "2.6.0")

if __name__ == "__main__":
    unittest.main()
```

---

## 📋 Чек-лист внедрения

### **Подготовка**
- [ ] Создать структуру папок `client/modules/updater/`
- [ ] Установить зависимости: `urllib3`, `pynacl`, `packaging`
- [ ] Обновить `requirements.txt`
- [ ] Обновить `unified_config.yaml`

### **Реализация модулей**
- [ ] Создать `config.py` - конфигурация
- [ ] Создать `net.py` - HTTP клиент
- [ ] Создать `verify.py` - проверки безопасности
- [ ] Создать `dmg.py` - работа с DMG
- [ ] Создать `replace.py` - атомарная замена
- [ ] Создать `migrate.py` - миграция
- [ ] Создать `updater.py` - основная логика

### **Интеграция**
- [ ] Создать `updater_integration.py`
- [ ] Обновить `simple_module_coordinator.py`
- [ ] Заменить `UpdateManagerIntegration` на `UpdaterIntegration`

### **Серверная часть**
- [ ] Создать `manifest.json`
- [ ] Создать скрипты сборки
- [ ] Обновить `update_server.py`

### **Тестирование**
- [ ] Локальные тесты модулей
- [ ] Интеграционные тесты
- [ ] Тест полного цикла обновления

### **Развертывание**
- [ ] Сборка первого DMG
- [ ] Генерация ключей Ed25519
- [ ] Подписание артефактов
- [ ] Размещение на сервере

---

## ⚠️ Важные моменты

### **Безопасность**
- ✅ Всегда проверяйте SHA256 хеш
- ✅ Обязательно проверяйте Ed25519 подпись
- ✅ Проверяйте codesign и spctl
- ✅ Используйте HTTPS для всех запросов

### **UX**
- ✅ Миграция происходит автоматически при первом запуске
- ✅ Обновления не блокируют работу приложения
- ✅ Пароль запрашивается только при первой установке PKG

### **Отладка**
- ✅ Логи в `~/Library/Logs/Nexy/updater.log`
- ✅ Проверяйте права доступа к `~/Applications`
- ✅ Убедитесь в корректности путей к .app файлам

---

## 🎯 Ожидаемый результат

После внедрения система обновлений будет:
- ✅ **Работать автоматически** без вмешательства пользователя
- ✅ **Не требовать пароль** после первой установки
- ✅ **Быть безопасной** с многоуровневой проверкой
- ✅ **Интегрироваться** с существующей EventBus архитектурой
- ✅ **Логироваться** для отладки и мониторинга

**Время реализации: 4-5 часов**  
**Статус: Готов к немедленному внедрению**
