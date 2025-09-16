"""
Основной менеджер обновлений
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Callable, List
from .types import UpdateStatus, UpdateInfo, UpdateConfig, UpdateResult, UpdateEvent
from ..macos.sparkle_handler import SparkleHandler

logger = logging.getLogger(__name__)

class UpdateManager:
    """Менеджер автоматических обновлений"""
    
    def __init__(self, config: UpdateConfig, event_bus, state_manager):
        self.config = config
        self.event_bus = event_bus
        self.state_manager = state_manager
        self.sparkle_handler = SparkleHandler(config.appcast_url)
        
        self.current_status = UpdateStatus.IDLE
        self.available_update: Optional[UpdateInfo] = None
        self.check_task: Optional[asyncio.Task] = None
        self.update_task: Optional[asyncio.Task] = None
        
        # Callbacks для событий
        self.status_callbacks: List[Callable] = []
        
        # Проверяем доступность Sparkle
        if not self.sparkle_handler.is_framework_available():
            logger.warning("Sparkle Framework недоступен - автообновления отключены")
            self.config.enabled = False
    
    async def start(self):
        """Запуск менеджера обновлений"""
        if not self.config.enabled:
            logger.info("Менеджер обновлений отключен")
            return
            
        logger.info("Запускаю менеджер обновлений...")
        
        # Подписываемся на события
        await self._setup_event_listeners()
        
        # Запускаем проверку при старте
        if self.config.check_on_startup:
            logger.info("Проверяю обновления при запуске...")
            await self.check_for_updates()
            
        # Запускаем периодическую проверку
        await self._start_periodic_check()
        
        logger.info("Менеджер обновлений запущен")
    
    async def _setup_event_listeners(self):
        """Настройка слушателей событий"""
        # Подписываемся на события состояния приложения
        self.event_bus.subscribe("app.state_changed", self._on_app_state_changed)
        self.event_bus.subscribe("app.shutdown", self._on_app_shutdown)
        
    async def _start_periodic_check(self):
        """Запуск периодической проверки"""
        if self.check_task:
            self.check_task.cancel()
            
        self.check_task = asyncio.create_task(self._periodic_check_loop())
        
    async def _periodic_check_loop(self):
        """Основной цикл проверки обновлений"""
        while True:
            try:
                # Ждем до времени проверки
                await self._wait_until_check_time()
                
                # Проверяем, можно ли обновляться
                if await self._can_check_updates():
                    logger.info("Начинаю проверку обновлений...")
                    await self.check_for_updates()
                    
                # Ждем до следующей проверки
                await asyncio.sleep(3600)  # Проверяем каждый час
                
            except asyncio.CancelledError:
                logger.info("Цикл проверки обновлений остановлен")
                break
            except Exception as e:
                logger.error(f"Ошибка в цикле проверки обновлений: {e}")
                await asyncio.sleep(300)  # Ждем 5 минут при ошибке
                
    async def _wait_until_check_time(self):
        """Ожидание времени проверки"""
        now = datetime.now()
        check_time = datetime.strptime(self.config.check_time, "%H:%M").time()
        
        # Если время уже прошло сегодня, ждем до завтра
        if now.time() > check_time:
            next_check = datetime.combine(now.date() + timedelta(days=1), check_time)
        else:
            next_check = datetime.combine(now.date(), check_time)
            
        wait_seconds = (next_check - now).total_seconds()
        logger.info(f"Следующая проверка обновлений в {next_check.strftime('%H:%M')}")
        await asyncio.sleep(wait_seconds)
        
    async def _can_check_updates(self) -> bool:
        """Проверка, можно ли проверять обновления"""
        # Не проверяем во время активной работы
        current_mode = self.state_manager.get_current_mode()
        if current_mode in ["LISTENING", "PROCESSING", "SPEAKING"]:
            logger.info(f"Откладываю проверку обновлений - активный режим: {current_mode}")
            return False
            
        # Не проверяем, если уже идет обновление
        if self.current_status != UpdateStatus.IDLE:
            logger.info(f"Откладываю проверку обновлений - текущий статус: {self.current_status.value}")
            return False
            
        return True
        
    async def check_for_updates(self) -> Optional[UpdateInfo]:
        """Проверка доступности обновлений"""
        try:
            await self._set_status(UpdateStatus.CHECKING)
            
            # Проверяем через Sparkle
            update_info = await self.sparkle_handler.check_for_updates()
            
            if update_info:
                self.available_update = update_info
                logger.info(f"Доступно обновление версии {update_info.version}")
                
                # Публикуем событие
                await self.event_bus.publish("update.available", {
                    "version": update_info.version,
                    "build_number": update_info.build_number,
                    "release_notes": update_info.release_notes
                })
                
                # Если автоустановка включена, начинаем процесс
                if self.config.auto_install:
                    logger.info("Автоматически начинаю процесс обновления...")
                    await self._start_update_process()
                    
                return update_info
            else:
                logger.info("Обновления не найдены")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка проверки обновлений: {e}")
            await self._set_status(UpdateStatus.FAILED)
            return None
        finally:
            await self._set_status(UpdateStatus.IDLE)
            
    async def _start_update_process(self):
        """Запуск процесса обновления (полностью автоматически)"""
        if not self.available_update:
            logger.warning("Нет доступного обновления для установки")
            return
            
        try:
            logger.info(f"🔄 Начинаю автоматическое обновление до версии {self.available_update.version}")
            
            # Скачиваем обновление
            await self._download_update_silent()
            
            # Устанавливаем обновление
            await self._install_update_silent()
            
            # Перезапускаем приложение
            await self._restart_application_silent()
            
        except Exception as e:
            logger.error(f"❌ Ошибка процесса обновления: {e}")
            await self._set_status(UpdateStatus.FAILED)
            
    async def _download_update_silent(self):
        """Тихое скачивание обновления"""
        await self._set_status(UpdateStatus.DOWNLOADING)
        logger.info("📥 Скачиваю обновление...")
        
        result = await self.sparkle_handler.download_update(self.available_update)
        
        if result.success:
            logger.info("✅ Обновление скачано успешно")
        else:
            raise Exception(f"Ошибка скачивания: {result.message}")
            
    async def _install_update_silent(self):
        """Тихая установка обновления"""
        await self._set_status(UpdateStatus.INSTALLING)
        logger.info("🔧 Устанавливаю обновление...")
        
        result = await self.sparkle_handler.install_update(self.available_update)
        
        if result.success:
            logger.info("✅ Обновление установлено успешно")
        else:
            raise Exception(f"Ошибка установки: {result.message}")
            
    async def _restart_application_silent(self):
        """Тихий перезапуск приложения"""
        await self._set_status(UpdateStatus.RESTARTING)
        logger.info("🔄 Перезапускаю приложение...")
        
        # Публикуем событие о перезапуске
        await self.event_bus.publish("update.restarting", {
            "version": self.available_update.version,
            "build_number": self.available_update.build_number
        })
        
        result = await self.sparkle_handler.restart_application()
        
        if result.success:
            logger.info("✅ Приложение перезапущено с новой версией")
        else:
            raise Exception(f"Ошибка перезапуска: {result.message}")
            
    async def _set_status(self, status: UpdateStatus):
        """Установка статуса обновления"""
        old_status = self.current_status
        self.current_status = status
        
        logger.info(f"Статус обновления: {old_status.value} → {status.value}")
        
        # Публикуем событие о смене статуса
        await self.event_bus.publish("update.status_changed", {
            "old_status": old_status.value,
            "new_status": status.value,
            "update_info": self.available_update
        })
        
        # Вызываем callbacks
        for callback in self.status_callbacks:
            try:
                callback(status, self.available_update)
            except Exception as e:
                logger.error(f"Ошибка в callback: {e}")
                
    async def _on_app_state_changed(self, event_data):
        """Обработка смены состояния приложения"""
        new_mode = event_data.get("new_mode")
        
        # Если приложение переходит в активный режим, откладываем обновление
        if new_mode in ["LISTENING", "PROCESSING", "SPEAKING"]:
            if self.current_status in [UpdateStatus.DOWNLOADING, UpdateStatus.INSTALLING]:
                logger.info(f"Приостанавливаю обновление - активный режим: {new_mode}")
                await self._pause_update_process()
                
    async def _on_app_shutdown(self, event_data):
        """Обработка завершения приложения"""
        logger.info("Завершаю менеджер обновлений...")
        
        # Отменяем все задачи
        if self.check_task:
            self.check_task.cancel()
        if self.update_task:
            self.update_task.cancel()
            
    async def _pause_update_process(self):
        """Приостановка процесса обновления"""
        logger.info("Приостанавливаю процесс обновления...")
        await self.sparkle_handler.pause_update()
        
    def add_status_callback(self, callback: Callable):
        """Добавление callback для статуса"""
        self.status_callbacks.append(callback)
        
    def get_current_status(self) -> UpdateStatus:
        """Получение текущего статуса"""
        return self.current_status
        
    def get_available_update(self) -> Optional[UpdateInfo]:
        """Получение информации об доступном обновлении"""
        return self.available_update
        
    def is_enabled(self) -> bool:
        """Проверка, включен ли менеджер обновлений"""
        return self.config.enabled and self.sparkle_handler.is_framework_available()
        
    async def stop(self):
        """Остановка менеджера обновлений"""
        logger.info("Останавливаю менеджер обновлений...")
        
        # Отменяем все задачи
        if self.check_task:
            self.check_task.cancel()
        if self.update_task:
            self.update_task.cancel()
            
        logger.info("Менеджер обновлений остановлен")
