"""
macOS реализация иконки трея
"""

import os
import tempfile
from typing import Optional
from ..core.tray_types import TrayStatus, TrayIconGenerator

try:
    from PIL import Image, ImageDraw  # type: ignore
    _PIL_AVAILABLE = True
except Exception:
    _PIL_AVAILABLE = False


class MacOSTrayIcon:
    """macOS реализация иконки трея"""
    
    def __init__(self, status: TrayStatus = TrayStatus.SLEEPING, size: int = 16):
        self.status = status
        self.size = size
        self.icon_generator = TrayIconGenerator()
        self._temp_files = []
        self._current_icon_path: Optional[str] = None
    
    def create_icon_file(self, status: TrayStatus) -> str:
        """Создать файл иконки для macOS (PNG)."""
        try:
            # Создаём временный PNG-файл
            temp_file = tempfile.NamedTemporaryFile(
                suffix='.png',
                delete=False,
                dir=tempfile.gettempdir()
            )
            temp_path = temp_file.name
            temp_file.close()

            # Вычисляем параметры рисунка (retina-friendly: рендерим в 2x размера)
            scale = 2
            w = h = max(16, self.size) * scale
            radius = int(min(w, h) * 0.45)
            cx = cy = int(min(w, h) / 2)

            # Цвет для статуса
            icon = self.icon_generator.create_circle_icon(status, self.size)
            color = icon.color or "#808080"
            
            # 🎯 TRAY DEBUG: Логируем создание иконки
            print(f"🎯 TRAY DEBUG: create_icon_file вызван для status={status}")
            print(f"🎯 TRAY DEBUG: generated color={color}, PIL_available={_PIL_AVAILABLE}")

            if not _PIL_AVAILABLE:
                # Fallback: создаём пустой файл, чтобы не падать (иконка не обновится)
                with open(temp_path, 'wb') as f:
                    pass
            else:
                # Рисуем круг в прозрачном PNG
                img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
                draw = ImageDraw.Draw(img)
                bbox = [cx - radius, cy - radius, cx + radius, cy + radius]
                draw.ellipse(bbox, fill=color)
                # Сохраняем PNG (умеренная компрессия)
                img.save(temp_path, format="PNG", optimize=True)

            self._temp_files.append(temp_path)
            self._current_icon_path = temp_path
            return temp_path

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









