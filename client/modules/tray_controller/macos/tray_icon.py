"""
macOS реализация иконки трея
"""

import os
import tempfile
import base64
from typing import Optional, Callable
from ..core.tray_types import TrayStatus, TrayIcon, TrayIconGenerator

class MacOSTrayIcon:
    """macOS реализация иконки трея"""
    
    def __init__(self, status: TrayStatus = TrayStatus.SLEEPING, size: int = 16):
        self.status = status
        self.size = size
        self.icon_generator = TrayIconGenerator()
        self._temp_files = []
        self._current_icon_path: Optional[str] = None
    
    def create_icon_file(self, status: TrayStatus) -> str:
        """Создать файл иконки для macOS"""
        try:
            # Создаем SVG иконку
            svg_content = self.icon_generator.create_svg_icon(status, self.size)
            
            # Создаем временный файл
            temp_file = tempfile.NamedTemporaryFile(
                suffix='.svg', 
                delete=False,
                dir=tempfile.gettempdir()
            )
            
            temp_file.write(svg_content.encode('utf-8'))
            temp_file.close()
            
            self._temp_files.append(temp_file.name)
            self._current_icon_path = temp_file.name
            
            return temp_file.name
            
        except Exception as e:
            print(f"Ошибка создания иконки: {e}")
            return ""
    
    def update_status(self, status: TrayStatus) -> bool:
        """Обновить статус иконки"""
        try:
            self.status = status
            new_icon_path = self.create_icon_file(status)
            
            if new_icon_path and new_icon_path != self._current_icon_path:
                # Удаляем старую иконку
                if self._current_icon_path and os.path.exists(self._current_icon_path):
                    try:
                        os.unlink(self._current_icon_path)
                    except:
                        pass
                
                self._current_icon_path = new_icon_path
                return True
            
            return False
            
        except Exception as e:
            print(f"Ошибка обновления статуса иконки: {e}")
            return False
    
    def get_icon_path(self) -> Optional[str]:
        """Получить путь к текущей иконке"""
        return self._current_icon_path
    
    def cleanup(self):
        """Очистить временные файлы"""
        for temp_file in self._temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except:
                pass
        self._temp_files.clear()
    
    def __del__(self):
        """Деструктор для очистки"""
        self.cleanup()










