"""
macOS реализация меню трея
"""

import os
import rumps
from typing import List, Optional, Callable, Dict, Any
from ..core.tray_types import TrayMenuItem, TrayMenu, TrayStatus

class MacOSTrayMenu:
    """macOS реализация меню трея"""
    
    def __init__(self, app_name: str = "Nexy"):
        self.app_name = app_name
        self.app: Optional[rumps.App] = None
        self.menu_items: List[TrayMenuItem] = []
        self.status_callbacks: Dict[str, Callable] = {}
        # Ссылки на изменяемые пункты меню
        self._status_item: Optional[rumps.MenuItem] = None
        self._output_item: Optional[rumps.MenuItem] = None
    
    def create_app(self, icon_path: str) -> rumps.App:
        """Создать приложение с иконкой в трее"""
        try:
            # Создаем приложение
            self.app = rumps.App(
                name=self.app_name,
                quit_button=None  # Убираем стандартную кнопку выхода
            )
            
            # Создаём изменяемые элементы меню (статус и текущее устройство)
            title_item = rumps.MenuItem(title="Nexy AI Assistant")
            self._status_item = rumps.MenuItem(title="Status: Waiting")
            self._output_item = rumps.MenuItem(title="Output: Unknown")

            # Добавляем простое меню (с объектами MenuItem)
            self.app.menu = [
                title_item,
                None,
                self._status_item,
                self._output_item,
                None,
                "Quit"
            ]
            
            # Добавляем обработчик выхода
            def quit_app(sender):
                rumps.quit_application()
            
            self.app.menu["Quit"].set_callback(quit_app)
            
            # Устанавливаем иконку если есть
            if icon_path and os.path.exists(icon_path):
                self.app.icon = icon_path
            
            return self.app
            
        except Exception as e:
            print(f"Ошибка создания приложения трея: {e}")
            return None
    
    def _setup_event_handlers(self):
        """Настроить обработчики событий"""
        if not self.app:
            return
        
        # Обработчики событий будут добавлены через rumps
    
    def add_menu_item(self, item: TrayMenuItem):
        """Добавить элемент меню"""
        if not self.app:
            return
        
        try:
            if item.separator:
                # Добавляем разделитель
                rumps.separator()
            else:
                # Создаем элемент меню
                menu_item = rumps.MenuItem(
                    title=item.title,
                    callback=item.action,
                    key=item.shortcut
                )
                
                if not item.enabled:
                    menu_item.state = 0  # Отключен
                
                # Добавляем в меню
                self.app.menu.add(menu_item)
                
                # Если есть подменю
                if item.submenu:
                    self._add_submenu(menu_item, item.submenu)
            
            self.menu_items.append(item)
            
        except Exception as e:
            print(f"Ошибка добавления элемента меню: {e}")
    
    def _add_submenu(self, parent_item, submenu: TrayMenu):
        """Добавить подменю"""
        try:
            for sub_item in submenu.items:
                if sub_item.separator:
                    parent_item.add(rumps.separator())
                else:
                    sub_menu_item = rumps.MenuItem(
                        title=sub_item.title,
                        callback=sub_item.action,
                        key=sub_item.shortcut
                    )
                    
                    if not sub_item.enabled:
                        sub_menu_item.state = 0
                    
                    parent_item.add(sub_menu_item)
                    
                    # Рекурсивно добавляем подменю
                    if sub_item.submenu:
                        self._add_submenu(sub_menu_item, sub_item.submenu)
        
        except Exception as e:
            print(f"Ошибка добавления подменю: {e}")
    
    def update_menu(self, menu: TrayMenu):
        """Обновить меню"""
        if not self.app:
            return
        
        try:
            # Очищаем существующее меню
            self.app.menu.clear()
            self.menu_items.clear()
            
            # Добавляем новые элементы
            for item in menu.items:
                self.add_menu_item(item)
        
        except Exception as e:
            print(f"Ошибка обновления меню: {e}")
    
    def set_status_callback(self, event_type: str, callback: Callable):
        """Установить обработчик статуса"""
        self.status_callbacks[event_type] = callback
    
    def show_notification(self, title: str, message: str, subtitle: str = ""):
        """Показать уведомление"""
        if not self.app:
            return
        
        try:
            rumps.notification(
                title=title,
                subtitle=subtitle,
                message=message,
                sound=False
            )
        except Exception as e:
            print(f"Ошибка показа уведомления: {e}")

    def update_status_text(self, text: str):
        """Обновить текст статуса в меню."""
        if not self.app or not self._status_item:
            return
        try:
            self._status_item.title = f"Status: {text}"
        except Exception as e:
            print(f"Ошибка обновления статуса меню: {e}")

    def update_output_device(self, device_name: str):
        """Обновить название текущего устройства вывода в меню."""
        if not self.app or not self._output_item:
            return
        try:
            self._output_item.title = f"Output: {device_name}"
        except Exception as e:
            print(f"Ошибка обновления устройства в меню: {e}")
    
    def update_icon(self, icon_path: str):
        """Обновить иконку"""
        if not self.app:
            return
        
        try:
            self.app.icon = icon_path
        except Exception as e:
            print(f"Ошибка обновления иконки: {e}")
    
    def run(self):
        """Запустить приложение"""
        if self.app:
            self.app.run()
    
    def quit(self):
        """Завершить приложение"""
        if self.app:
            rumps.quit_application()
