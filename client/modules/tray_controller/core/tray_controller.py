"""
Основной контроллер трея
"""

import asyncio
import logging
import threading
from typing import Optional, Callable, Dict, Any
from .tray_types import TrayStatus, TrayConfig, TrayMenu, TrayMenuItem, TrayEvent
from .config import TrayConfigManager
from ..macos.tray_icon import MacOSTrayIcon
from ..macos.menu_handler import MacOSTrayMenu

logger = logging.getLogger(__name__)

class TrayController:
    """Основной контроллер трея"""
    
    def __init__(self, config_manager: Optional[TrayConfigManager] = None):
        self.config_manager = config_manager or TrayConfigManager()
        self.config = self.config_manager.get_config()
        
        # Компоненты
        self.tray_icon: Optional[MacOSTrayIcon] = None
        self.tray_menu: Optional[MacOSTrayMenu] = None
        
        # Состояние
        self.current_status = TrayStatus.SLEEPING
        self.is_running = False
        self.event_callbacks: Dict[str, Callable] = {}
        
        # Поток для macOS приложения
        self._menu_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
    
    async def initialize(self) -> bool:
        """Инициализация контроллера трея"""
        try:
            logger.info("🔧 Инициализация TrayController")
            
            # Создаем компоненты
            self.tray_icon = MacOSTrayIcon(
                status=self.current_status,
                size=self.config.icon_size
            )
            
            self.tray_menu = MacOSTrayMenu("Nexy")
            
            # Создаем базовое меню
            await self._create_default_menu()
            
            # Настраиваем обработчики событий
            self._setup_event_handlers()
            
            logger.info("✅ TrayController инициализирован")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации TrayController: {e}")
            return False
    
    async def start(self) -> bool:
        """Запуск контроллера трея"""
        try:
            if self.is_running:
                logger.warning("TrayController уже запущен")
                return True
            
            logger.info("🚀 Запуск TrayController")
            
            # Создаем иконку
            icon_path = self.tray_icon.create_icon_file(self.current_status)
            if not icon_path:
                logger.error("❌ Не удалось создать иконку")
                return False
            
            # Создаем приложение
            app = self.tray_menu.create_app(icon_path)
            if not app:
                logger.error("❌ Не удалось создать приложение трея")
                return False
            
            # Сохраняем приложение для использования в главном потоке
            self.tray_menu.app = app
            
            # После создания rumps.App меню было очищено внутри create_app();
            # пересоздаём дефолтное меню (Status/Output/Quit)
            try:
                await self._create_default_menu()
            except Exception:
                pass

            self.is_running = True
            logger.info("✅ TrayController готов к запуску")
            logger.info("ℹ️ Для отображения иконки запустите app.run() в главном потоке")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска TrayController: {e}")
            return False
    
    async def stop(self) -> bool:
        """Остановка контроллера трея"""
        try:
            if not self.is_running:
                logger.warning("TrayController не запущен")
                return True
            
            logger.info("⏹️ Остановка TrayController")
            
            # Останавливаем меню
            if self.tray_menu:
                self.tray_menu.quit()
            
            # Останавливаем поток
            self._stop_event.set()
            if self._menu_thread and self._menu_thread.is_alive():
                self._menu_thread.join(timeout=2.0)
            
            # Очищаем ресурсы
            if self.tray_icon:
                self.tray_icon.cleanup()
            
            self.is_running = False
            logger.info("✅ TrayController остановлен")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка остановки TrayController: {e}")
            return False
    
    async def update_status(self, status: TrayStatus) -> bool:
        """Обновить статус трея"""
        try:
            if not self.is_running:
                logger.warning("TrayController не запущен")
                return False
            
            logger.info(f"🔄 Обновление статуса трея: {self.current_status.value} → {status.value}")
            
            # Обновляем иконку
            if self.tray_icon:
                icon_path = self.tray_icon.create_icon_file(status)
                if icon_path and self.tray_menu:
                    self.tray_menu.update_icon(icon_path)
            
            self.current_status = status
            
            # Публикуем событие
            await self._publish_event("status_changed", {
                "status": status.value,
                "previous_status": self.current_status.value
            })
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка обновления статуса трея: {e}")
            return False
    
    async def show_notification(self, title: str, message: str, subtitle: str = ""):
        """Показать уведомление"""
        try:
            if self.tray_menu:
                self.tray_menu.show_notification(title, message, subtitle)
        except Exception as e:
            logger.error(f"❌ Ошибка показа уведомления: {e}")

    async def update_menu_status_text(self, status_text: str):
        """Обновить текст статуса в меню (например, Sleeping/Listening/Processing)."""
        try:
            if self.tray_menu:
                self.tray_menu.update_status_text(status_text)
        except Exception as e:
            logger.error(f"❌ Ошибка обновления текста статуса меню: {e}")

    async def update_menu_output_device(self, device_name: str):
        """Обновить пункт меню с текущим устройством вывода."""
        try:
            if self.tray_menu:
                self.tray_menu.update_output_device(device_name)
        except Exception as e:
            logger.error(f"❌ Ошибка обновления пункта меню Output: {e}")
    
    def set_event_callback(self, event_type: str, callback: Callable):
        """Установить обработчик событий"""
        self.event_callbacks[event_type] = callback
    
    async def _create_default_menu(self):
        """Создать меню по умолчанию"""
        try:
            menu_items = [
                TrayMenuItem(
                    title="Nexy AI Assistant",
                    enabled=False
                ),
                TrayMenuItem(title="", separator=True),
                TrayMenuItem(
                    title="Status: Waiting",
                    enabled=False
                ),
                TrayMenuItem(
                    title="Output: Unknown",
                    enabled=False
                ),
                TrayMenuItem(title="", separator=True),
                TrayMenuItem(
                    title="Check for Updates...",
                    action=self._on_check_updates_clicked
                ),
                TrayMenuItem(title="", separator=True),
                TrayMenuItem(
                    title="Quit",
                    action=self._on_quit_clicked
                )
            ]
            
            menu = TrayMenu(items=menu_items)
            
            if self.tray_menu:
                self.tray_menu.update_menu(menu)
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания меню по умолчанию: {e}")
    
    def _setup_event_handlers(self):
        """Настроить обработчики событий"""
        if self.tray_menu:
            self.tray_menu.set_status_callback("icon_click", self._on_icon_clicked)
            self.tray_menu.set_status_callback("icon_right_click", self._on_icon_right_clicked)
    
    def _on_icon_clicked(self, sender):
        """Обработчик клика по иконке"""
        asyncio.create_task(self._publish_event("icon_clicked", {}))
    
    def _on_icon_right_clicked(self, sender):
        """Обработчик правого клика по иконке"""
        asyncio.create_task(self._publish_event("icon_right_clicked", {}))
    
    def _on_settings_clicked(self, sender):
        """Обработчик клика по настройкам"""
        asyncio.create_task(self._publish_event("settings_clicked", {}))
    
    def _on_check_updates_clicked(self, sender):
        """Обработчик клика по проверке обновлений"""
        asyncio.create_task(self._publish_event("updater.check_manual", {}))
    
    def _on_about_clicked(self, sender):
        """Обработчик клика по 'О программе'"""
        asyncio.create_task(self._publish_event("about_clicked", {}))
    
    def _on_quit_clicked(self, sender):
        """Обработчик клика по выходу"""
        # 1) Сообщаем слушателям (например, интеграции), что пользователь инициировал выход
        try:
            logger.info("🔚 Quit requested via tray menu (user action)")
            asyncio.create_task(self._publish_event("quit_clicked", {}))
            # 2) Завершаем приложение через rumps
            if self.tray_menu:
                self.tray_menu.quit()
        except Exception:
            pass
    
    async def _publish_event(self, event_type: str, data: Dict[str, Any]):
        """Публиковать событие"""
        try:
            if event_type in self.event_callbacks:
                callback = self.event_callbacks[event_type]
                if asyncio.iscoroutinefunction(callback):
                    await callback(event_type, data)
                else:
                    callback(event_type, data)
        except Exception as e:
            logger.error(f"❌ Ошибка публикации события {event_type}: {e}")
    
    def _run_menu_thread(self):
        """Запустить меню в отдельном потоке"""
        try:
            if self.tray_menu and self.tray_menu.app:
                # rumps должен запускаться в главном потоке
                # Здесь мы только подготавливаем приложение
                logger.info("ℹ️ Приложение rumps подготовлено для запуска в главном потоке")
            
        except Exception as e:
            logger.error(f"❌ Ошибка в потоке меню: {e}")
    
    def get_status(self) -> TrayStatus:
        """Получить текущий статус"""
        return self.current_status
    
    def is_initialized(self) -> bool:
        """Проверить, инициализирован ли контроллер"""
        return self.tray_icon is not None and self.tray_menu is not None
    
    def get_app(self):
        """Получить приложение rumps для запуска в главном потоке"""
        if self.tray_menu and self.tray_menu.app:
            return self.tray_menu.app
        return None
    
    def run_app(self):
        """Запустить приложение в главном потоке"""
        if self.tray_menu and self.tray_menu.app:
            self.tray_menu.app.run()
