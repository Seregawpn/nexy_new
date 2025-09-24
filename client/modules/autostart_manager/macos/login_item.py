"""
Управление Login Items для macOS (альтернативный метод автозапуска).
"""

import os
import subprocess
from typing import Optional

class LoginItemManager:
    """Менеджер Login Items для автозапуска."""
    
    def __init__(self, config):
        self.config = config
        self.bundle_id = config.bundle_id
        
    async def add_login_item(self) -> bool:
        """Добавление приложения в Login Items."""
        try:
            # Используем osascript для добавления в Login Items
            script = f'''
            tell application "System Events"
                make login item at end with properties {{name:"Nexy", path:"/Applications/Nexy.app", hidden:false}}
            end tell
            '''
            
            result = subprocess.run([
                'osascript', '-e', script
            ], capture_output=True, text=True)
            
            return result.returncode == 0
            
        except Exception as e:
            print(f"❌ Ошибка добавления в Login Items: {e}")
            return False
    
    async def remove_login_item(self) -> bool:
        """Удаление приложения из Login Items."""
        try:
            script = f'''
            tell application "System Events"
                delete login item "Nexy"
            end tell
            '''
            
            result = subprocess.run([
                'osascript', '-e', script
            ], capture_output=True, text=True)
            
            return result.returncode == 0
            
        except Exception as e:
            print(f"❌ Ошибка удаления из Login Items: {e}")
            return False
    
    async def is_in_login_items(self) -> bool:
        """Проверка наличия в Login Items."""
        try:
            script = '''
            tell application "System Events"
                set loginItems to name of every login item
                return "Nexy" is in loginItems
            end tell
            '''
            
            result = subprocess.run([
                'osascript', '-e', script
            ], capture_output=True, text=True)
            
            return "true" in result.stdout.lower()
            
        except Exception:
            return False
