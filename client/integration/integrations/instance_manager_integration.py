"""
Instance Manager Integration

Интеграция для управления экземплярами приложения и предотвращения дублирования.
Выполняется ПЕРВОЙ и является БЛОКИРУЮЩЕЙ.
"""

import sys
import asyncio
import logging
from typing import Optional, Dict, Any

from modules.instance_manager import InstanceManager, InstanceStatus, InstanceManagerConfig
from integration.core.error_handler import ErrorHandler
from integration.core.state_manager import ApplicationStateManager
from integration.core.event_bus import EventBus

logger = logging.getLogger(__name__)


class InstanceManagerIntegration:
    """Интеграция для управления экземплярами приложения."""
    
    def __init__(self, event_bus: EventBus, state_manager: ApplicationStateManager, 
                 error_handler: ErrorHandler, config: Optional[Dict[str, Any]] = None):
        self.event_bus = event_bus
        self.state_manager = state_manager
        self.error_handler = error_handler
        self.config = config or {}
        
        # Создаем конфигурацию модуля
        instance_config = InstanceManagerConfig(
            enabled=self.config.get('enabled', True),
            lock_file=self.config.get('lock_file', '~/Library/Application Support/Nexy/nexy.lock'),
            timeout_seconds=self.config.get('timeout_seconds', 30),
            cleanup_on_startup=self.config.get('cleanup_on_startup', True),
            show_duplicate_message=self.config.get('show_duplicate_message', True),
            pid_check=self.config.get('pid_check', True)
        )
        
        self.instance_manager = InstanceManager(instance_config)
        self._initialized = False
        
    async def initialize(self) -> bool:
        """Инициализация интеграции - НЕ БЛОКИРУЮЩАЯ."""
        try:
            # Подписка на события
            await self.event_bus.subscribe("app.startup", self._on_app_startup)
            await self.event_bus.subscribe("app.shutdown", self._on_app_shutdown)
            await self.event_bus.subscribe("instance.check_request", self._on_instance_check_request)
            
            self._initialized = True
            print("✅ InstanceManagerIntegration инициализирован")
            return True
            
        except Exception as e:
            await self.error_handler.handle_error("instance_manager_initialize", e)
            return False
    
    async def start(self) -> bool:
        """Запуск интеграции - БЛОКИРУЮЩИЙ МЕТОД."""
        try:
            print("🚀 InstanceManagerIntegration.start() вызван")
            
            if not self._initialized:
                await self.initialize()
            
            # КРИТИЧНО: Проверка дублирования при старте
            print("🔍 Проверка дублирования экземпляров...")
            status = await self.instance_manager.check_single_instance()
            print(f"🔍 Результат проверки дублирования: {status}")
            
            if status == InstanceStatus.DUPLICATE:
                # ДУБЛИРОВАНИЕ ОБНАРУЖЕНО - ЗАВЕРШАЕМ РАБОТУ
                print("❌ Nexy уже запущен! Завершаем дубликат.")
                try:
                    logger.warning("🚫 InstanceManager: duplicate instance detected — exiting with code 1")
                except Exception:
                    pass
                
                # АУДИО-СИГНАЛ ДЛЯ НЕЗРЯЧИХ ПОЛЬЗОВАТЕЛЕЙ
                try:
                    await self.event_bus.publish("signal.duplicate_instance", {
                        "message": "Nexy уже запущен",
                        "sound": "error"
                    })
                except Exception as e:
                    print(f"⚠️ Не удалось отправить аудио-сигнал: {e}")
                
                if self.instance_manager.config.show_duplicate_message:
                    print("❌ Nexy уже запущен! Проверьте меню-бар.")
                
                # НЕМЕДЛЕННОЕ ЗАВЕРШЕНИЕ
                print("💀 ВЫХОД ИЗ ПРИЛОЖЕНИЯ С КОДОМ 1")
                sys.exit(1)
            
            elif status == InstanceStatus.ERROR:
                print("❌ Ошибка проверки дублирования")
                await self.error_handler.handle_error("instance_check_error", 
                                                     Exception("Failed to check instance status"))
                return False
            
            # ПЕРВЫЙ ЭКЗЕМПЛЯР - ПРОДОЛЖАЕМ
            print("✅ Дублирование не обнаружено, захватываем блокировку...")
            lock_acquired = await self.instance_manager.acquire_lock()
            
            if not lock_acquired:
                print("❌ Не удалось захватить блокировку")
                await self.error_handler.handle_error("lock_acquisition_failed", 
                                                     Exception("Failed to acquire lock"))
                return False
            
            print("✅ Nexy запущен успешно (первый экземпляр)")
            
            # Публикация события о успешном запуске
            try:
                lock_info = await self.instance_manager.get_lock_info()
                await self.event_bus.publish("instance.status_checked", {
                    "status": InstanceStatus.SINGLE.value,
                    "lock_info": lock_info
                })
            except Exception as e:
                print(f"⚠️ Не удалось опубликовать событие: {e}")
            
            return True
            
        except Exception as e:
            print(f"❌ Критическая ошибка в InstanceManagerIntegration.start(): {e}")
            import traceback
            traceback.print_exc()
            await self.error_handler.handle_error("instance_manager_start", e)
            return False
    
    async def stop(self) -> bool:
        """Остановка интеграции."""
        try:
            # Освобождение блокировки
            if self.instance_manager:
                await self.instance_manager.release_lock()
                print("✅ Блокировка освобождена")
            
            # Отписка от событий
            try:
                await self.event_bus.unsubscribe("app.startup", self._on_app_startup)
                await self.event_bus.unsubscribe("app.shutdown", self._on_app_shutdown)
                await self.event_bus.unsubscribe("instance.check_request", self._on_instance_check_request)
            except Exception as e:
                print(f"⚠️ Ошибка отписки от событий: {e}")
            
            return True
            
        except Exception as e:
            await self.error_handler.handle_error("instance_manager_stop", e)
            return False
    
    # Event handlers
    async def _on_app_startup(self, event: Dict[str, Any]) -> None:
        """Обработчик события запуска приложения."""
        try:
            print("📱 Обработка события app.startup")
            # Дополнительная логика при запуске (если нужна)
        except Exception as e:
            await self.error_handler.handle_error("app_startup_handler", e)
    
    async def _on_app_shutdown(self, event: Dict[str, Any]) -> None:
        """Обработчик события завершения приложения."""
        try:
            print("📱 Обработка события app.shutdown")
            # Освобождение блокировки при завершении
            await self.stop()
        except Exception as e:
            await self.error_handler.handle_error("app_shutdown_handler", e)
    
    async def _on_instance_check_request(self, event: Dict[str, Any]) -> None:
        """Обработчик запроса проверки экземпляра."""
        try:
            print("📱 Обработка события instance.check_request")
            status = await self.instance_manager.check_single_instance()
            
            await self.event_bus.publish("instance.status_response", {
                "status": status.value,
                "timestamp": asyncio.get_event_loop().time()
            })
        except Exception as e:
            await self.error_handler.handle_error("instance_check_request_handler", e)
