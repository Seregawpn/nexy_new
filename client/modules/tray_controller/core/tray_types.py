"""
Типы данных для Tray Controller
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Callable
import base64

class TrayStatus(Enum):
    """Статусы иконки в трее (соответствуют режимам приложения)"""
    SLEEPING = "sleeping"         # Спящий режим - серый кружок
    LISTENING = "listening"       # Прослушивание - синий кружок с пульсацией
    PROCESSING = "processing"     # Обработка - желтый кружок с вращением

class TrayIconType(Enum):
    """Типы иконок"""
    CIRCLE = "circle"            # Простой кружок
    PULSING = "pulsing"          # Пульсирующий кружок
    ROTATING = "rotating"        # Вращающийся кружок
    STATIC = "static"           # Статичная иконка

@dataclass
class TrayIcon:
    """Иконка для трея"""
    status: TrayStatus
    icon_type: TrayIconType
    color: str                   # HEX цвет
    size: int = 16              # Размер в пикселях
    data: Optional[bytes] = None # Данные иконки (если нужна кастомная)
    
    def get_base64_data(self) -> str:
        """Получить данные иконки в base64"""
        if self.data:
            return base64.b64encode(self.data).decode('utf-8')
        return ""

@dataclass
class TrayMenuItem:
    """Элемент меню трея"""
    title: str
    action: Optional[Callable] = None
    enabled: bool = True
    separator: bool = False
    submenu: Optional['TrayMenu'] = None
    shortcut: Optional[str] = None
    icon: Optional[str] = None

@dataclass
class TrayMenu:
    """Меню трея"""
    items: List[TrayMenuItem]
    title: Optional[str] = None

@dataclass
class TrayConfig:
    """Конфигурация трея"""
    show_status: bool = True
    show_menu: bool = True
    enable_click_events: bool = True
    enable_right_click: bool = True
    auto_hide: bool = False
    animation_speed: float = 0.5
    icon_size: int = 16
    menu_font_size: int = 13
    enable_sound: bool = False
    debug_mode: bool = False

@dataclass
class TrayEvent:
    """Событие трея"""
    event_type: str
    data: Optional[Dict[str, Any]] = None
    timestamp: float = 0.0
    source: str = "tray_controller"

class TrayIconGenerator:
    """Генератор иконок для трея"""
    
    @staticmethod
    def create_circle_icon(status: TrayStatus, size: int = 16) -> TrayIcon:
        """Создать простую иконку-кружок"""
        colors = {
            TrayStatus.SLEEPING: "#808080",      # Серый
            TrayStatus.LISTENING: "#007AFF",     # Синий
            TrayStatus.PROCESSING: "#FF9500"     # Желтый
        }
        
        # 🎯 TRAY DEBUG: Логируем генерацию иконки
        print(f"🎯 TRAY DEBUG: TrayIconGenerator.create_circle_icon status={status} (type: {type(status)})")
        print(f"🎯 TRAY DEBUG: Available colors: {colors}")
        print(f"🎯 TRAY DEBUG: Selected color: {colors.get(status, 'NOT_FOUND')}")
        
        icon_types = {
            TrayStatus.SLEEPING: TrayIconType.STATIC,
            TrayStatus.LISTENING: TrayIconType.PULSING,
            TrayStatus.PROCESSING: TrayIconType.ROTATING
        }
        
        return TrayIcon(
            status=status,
            icon_type=icon_types[status],
            color=colors[status],
            size=size
        )
    
    @staticmethod
    def create_svg_icon(status: TrayStatus, size: int = 16) -> str:
        """Создать SVG иконку для трея"""
        colors = {
            TrayStatus.SLEEPING: "#808080",
            TrayStatus.LISTENING: "#007AFF", 
            TrayStatus.PROCESSING: "#FF9500"
        }
        
        color = colors[status]
        
        # Идеально круглый SVG для всех статусов
        center = size // 2
        radius = center - 1  # Оставляем 1 пиксель от края
        
        svg = f'''<svg width="{size}" height="{size}" xmlns="http://www.w3.org/2000/svg">
            <circle cx="{center}" cy="{center}" r="{radius}" fill="{color}" stroke="none"/>
        </svg>'''
        
        return svg
