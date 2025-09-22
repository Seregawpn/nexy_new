"""
Интеграция системы обновлений с EventBus
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any

from integration.core.event_bus import EventBus, EventPriority
from integration.core.state_manager import ApplicationStateManager
from modules.updater import Updater, UpdaterConfig, migrate_to_user_directory

logger = logging.getLogger(__name__)

class UpdaterIntegration:
    """Интеграция системы обновлений с архитектурой приложения"""
    
    def __init__(self, event_bus: EventBus, state_manager: ApplicationStateManager, config: Dict[str, Any]):
        self.event_bus = event_bus
        self.state_manager = state_manager
        
        # Создаем конфигурацию обновлений
        updater_config = UpdaterConfig(
            enabled=config.get("enabled", True),
            manifest_url=config.get("manifest_url", ""),
            check_interval=config.get("check_interval", 3600),
            check_on_startup=config.get("check_on_startup", True),
            auto_install=config.get("auto_install", True),
            public_key=config.get("security", {}).get("public_key", ""),
            timeout=config.get("timeout", 30),
            retries=config.get("retries", 3),
            show_notifications=config.get("ui", {}).get("show_notifications", True),
            auto_download=config.get("ui", {}).get("auto_download", True)
        )
        
        self.updater = Updater(updater_config)
        self.check_task = None
        self.is_running = False
        # Поведение миграции регулируется конфигом/ENV
        self._migrate_mode: str = str(config.get("migrate_mode", "auto")).lower()  # auto | never
        self._migrate_on_start: bool = bool(config.get("migrate_on_start", False)) or (os.getenv("NEXY_MIGRATE_ON_START", "").lower() in {"1","true","yes"})
    
    async def initialize(self) -> bool:
        """Инициализация интеграции"""
        try:
            logger.info("🔄 Инициализация UpdaterIntegration...")
            
            # Миграция в пользовательскую папку (только если включено)
            if self._should_migrate_on_start():
                migrate_to_user_directory()
            
            # Настраиваем обработчики событий
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
            
            # Проверка при запуске (если включена)
            if self.updater.config.check_on_startup:
                logger.info("🔍 Проверка обновлений при запуске...")
                if await self._can_update():
                    if self.updater.update():
                        return True  # Приложение перезапустится
            
            # Запускаем периодическую проверку
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
                # Проверяем, можно ли обновляться
                if await self._can_update():
                    if self.updater.update():
                        return  # Приложение перезапустится
                
                # Ждем до следующей проверки
                await asyncio.sleep(self.updater.config.check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Ошибка в цикле проверки обновлений: {e}")
                await asyncio.sleep(300)  # Ждем 5 минут при ошибке
    
    async def _can_update(self) -> bool:
        """Проверка, можно ли обновляться"""
        current_mode = self.state_manager.get_current_mode()
        if current_mode in ["LISTENING", "PROCESSING"]:
            return False
        return True
    
    async def _setup_event_handlers(self):
        """Настройка обработчиков событий"""
        # Подписываемся на события
        await self.event_bus.subscribe("app.startup", self._on_app_startup, EventPriority.MEDIUM)
        await self.event_bus.subscribe("app.shutdown", self._on_app_shutdown, EventPriority.HIGH)
        await self.event_bus.subscribe("updater.check_manual", self._on_manual_check, EventPriority.HIGH)
        await self.event_bus.subscribe("app.mode_changed", self._on_mode_changed, EventPriority.LOW)
    
    async def _on_app_startup(self, event_data):
        """Обработка запуска приложения"""
        logger.info("🚀 Обработка запуска приложения в UpdaterIntegration")
    
    async def _on_app_shutdown(self, event_data):
        """Обработка завершения приложения"""
        logger.info("🛑 Обработка завершения приложения в UpdaterIntegration")
        await self.stop()
    
    async def _on_manual_check(self, event_data):
        """Ручная проверка обновлений"""
        logger.info("🔍 Ручная проверка обновлений")
        if await self._can_update():
            self.updater.update()
    
    async def _on_mode_changed(self, event_data):
        """Обработка изменения режима приложения"""
        new_mode = event_data.get("mode")
        logger.info(f"Режим приложения изменен на: {new_mode}")
    
    async def stop(self):
        """Остановка интеграции"""
        if self.check_task:
            self.check_task.cancel()
        self.is_running = False
        logger.info("✅ UpdaterIntegration остановлен")


    def _should_migrate_on_start(self) -> bool:
        """Определяет, нужно ли выполнять миграцию при старте.
        Режимы:
        - migrate_on_start=true (или ENV NEXY_MIGRATE_ON_START=1) → принудительно, если не в ~/Applications
        - migrate_mode=never → никогда
        - migrate_mode=auto (по умолчанию) → если запущены как .app И не из ~/Applications
        Всегда игнорируется, если уже запускаемся из ~/Applications.
        """
        # Если уже в ~/Applications — миграция не нужна
        if self._is_in_user_applications():
            return False

        # Жесткий флаг принудительной миграции
        if self._migrate_on_start:
            return True

        # Политика конфигурации
        if self._migrate_mode == "never":
            return False
        # auto: мигрируем только если реально .app вне ~/Applications (например, с DMG)
        if self._migrate_mode == "auto":
            return self._is_running_from_app_bundle()
        try:
            # Fallback: консервативно не мигрируем
            return False
        except Exception:
            # Если не смогли определить — лучше не мигрировать
            return False

    def _is_in_user_applications(self) -> bool:
        """Проверяет, расположен ли бандл в ~/Applications."""
        try:
            p = Path(sys.argv[0]).resolve()
            home_apps = Path.home() / "Applications"
            return str(p).startswith(str(home_apps))
        except Exception:
            return False

    def _is_running_from_app_bundle(self) -> bool:
        """Определяет, запущены ли мы как .app (PyInstaller бандл), и не из ~/Applications.
        Сценарии: запуск из DMG (/Volumes/...), из произвольной папки — да; запуск из исходников — нет.
        """
        try:
            exe_path = Path(sys.argv[0]).resolve()
            s = str(exe_path)
            if ".app/Contents/MacOS" in s or s.endswith("/MacOS/Nexy"):
                # .app бандл
                return not self._is_in_user_applications()
            # Запуск из исходников / интерпретатора — не мигрируем
            return False
        except Exception:
            return False
