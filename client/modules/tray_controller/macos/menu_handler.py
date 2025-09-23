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
        # UI таймер/очередь не используются на уровне модуля (обновления делает интеграция)
        # Callback для обработки завершения приложения
        self._quit_callback: Optional[Callable] = None
    
    def create_app(self, icon_path: str) -> rumps.App:
        """Создать приложение с иконкой в трее"""
        try:
            # Создаем приложение
            self.app = rumps.App(
                name=self.app_name,
                quit_button=None  # Убираем стандартную кнопку выхода
            )
            # Включаем цветные иконки (отключаем шаблонный режим)
            try:
                self.app.template = False
            except Exception:
                pass
            
            # Изначально меню заполняется интеграцией через TrayController._create_default_menu()
            # Здесь не создаём собственных пунктов меню, чтобы избежать дублирования и несинхронности.
            self.app.menu = []

            # Устанавливаем иконку если есть
            if icon_path and os.path.exists(icon_path):
                self.app.icon = icon_path
            
            # Добавляем метод applicationShouldTerminate если его нет
            if not hasattr(self.app, 'applicationShouldTerminate'):
                def applicationShouldTerminate(sender):
                    return True
                self.app.applicationShouldTerminate = applicationShouldTerminate
            
            # Настраиваем обработчик завершения приложения
            self._setup_quit_handler()
            
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
                # Добавляем разделитель в меню приложения
                try:
                    self.app.menu.add(rumps.separator())
                except Exception:
                    pass
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

                # Сохраняем ссылки на изменяемые элементы (по префиксу заголовка)
                try:
                    if isinstance(item.title, str):
                        if item.title.startswith("Status:"):
                            self._status_item = menu_item
                        elif item.title.startswith("Output:"):
                            self._output_item = menu_item
                except Exception:
                    pass
                
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
            # Добавляем метод applicationShouldTerminate если его нет
            if not hasattr(self.app, 'applicationShouldTerminate'):
                def applicationShouldTerminate(sender):
                    return True
                self.app.applicationShouldTerminate = applicationShouldTerminate
            self.app.run()
    
    def set_quit_callback(self, callback: Callable):
        """Установить callback для обработки завершения приложения"""
        self._quit_callback = callback
    
    def _setup_quit_handler(self):
        """Настроить обработчик завершения приложения"""
        if not self.app:
            return
        
        # Переопределяем метод applicationShouldTerminate для предотвращения автоматического завершения
        original_should_terminate = self.app.applicationShouldTerminate
        
        def custom_should_terminate(sender):
            """Кастомный обработчик завершения приложения"""
            try:
                # Если есть callback, вызываем его
                if self._quit_callback:
                    self._quit_callback()
                # Возвращаем False чтобы предотвратить завершение
                return False
            except Exception as e:
                print(f"Ошибка в обработчике завершения: {e}")
                return True  # Разрешаем завершение в случае ошибки
        
        # Устанавливаем наш обработчик
        self.app.applicationShouldTerminate = custom_should_terminate
    
    def quit(self):
        """Завершить приложение"""
        if self.app:
            rumps.quit_application()

    
