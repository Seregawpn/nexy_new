"""
Управление LaunchAgent для macOS.
"""

import os
import subprocess
from typing import Optional

class LaunchAgentManager:
    """Менеджер LaunchAgent для автозапуска."""
    
    def __init__(self, config):
        self.config = config
        self.bundle_id = config.bundle_id
        self.plist_path = os.path.expanduser(config.launch_agent_path)
        
    async def install(self) -> bool:
        """Установка LaunchAgent."""
        try:
            # Создаем директорию LaunchAgents если не существует
            plist_dir = os.path.dirname(self.plist_path)
            os.makedirs(plist_dir, exist_ok=True)
            
            # Создаем plist файл
            plist_content = self._generate_plist_content()
            with open(self.plist_path, 'w') as f:
                f.write(plist_content)
            
            # Загружаем LaunchAgent
            result = subprocess.run([
                'launchctl', 'bootstrap', f'gui/{os.getuid()}', self.plist_path
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"⚠️ LaunchAgent уже загружен, перезагружаем...")
                # Пытаемся выгрузить и загрузить заново
                subprocess.run([
                    'launchctl', 'bootout', f'gui/{os.getuid()}/{self.bundle_id}'
                ], capture_output=True)
                
                result = subprocess.run([
                    'launchctl', 'bootstrap', f'gui/{os.getuid()}', self.plist_path
                ], capture_output=True, text=True)
            
            return result.returncode == 0
            
        except Exception as e:
            print(f"❌ Ошибка установки LaunchAgent: {e}")
            return False
    
    async def uninstall(self) -> bool:
        """Удаление LaunchAgent."""
        try:
            # Выгружаем LaunchAgent
            subprocess.run([
                'launchctl', 'bootout', f'gui/{os.getuid()}/{self.bundle_id}'
            ], capture_output=True)
            
            # Удаляем plist файл
            if os.path.exists(self.plist_path):
                os.remove(self.plist_path)
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка удаления LaunchAgent: {e}")
            return False
    
    async def is_installed(self) -> bool:
        """Проверка установки LaunchAgent."""
        try:
            result = subprocess.run([
                'launchctl', 'print', f'gui/{os.getuid()}/{self.bundle_id}'
            ], capture_output=True)
            
            return result.returncode == 0
            
        except Exception:
            return False
    
    def _generate_plist_content(self) -> str:
        """Генерация содержимого plist файла."""
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{self.bundle_id}</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/open</string>
        <string>-b</string>
        <string>{self.bundle_id}</string>
    </array>
    
    <key>RunAtLoad</key>
    <true/>
    
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>
    
    <key>StandardOutPath</key>
    <string>/tmp/nexy.log</string>
    
    <key>StandardErrorPath</key>
    <string>/tmp/nexy.error.log</string>
    
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
</dict>
</plist>'''
