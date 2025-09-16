"""
Главный менеджер аудио устройств
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List, Callable

from .types import (
    AudioDevice, DeviceChange, DeviceType, DeviceStatus, 
    DeviceMetrics, AudioDeviceManagerConfig,
    DeviceChangeCallback, DeviceSwitchCallback, ErrorCallback, MetricsCallback
)
from .device_monitor import DeviceMonitor
from .device_switcher import DeviceSwitcher

logger = logging.getLogger(__name__)


class AudioDeviceManager:
    """Главный менеджер аудио устройств"""
    
    def __init__(self, config: Optional[AudioDeviceManagerConfig] = None):
        self.config = config or AudioDeviceManagerConfig()
        
        # Компоненты модуля
        self.device_monitor = DeviceMonitor()
        self.device_switcher = DeviceSwitcher(self.device_monitor)
        
        # Состояние
        self.is_running = False
        self.current_device: Optional[AudioDevice] = None
        self.metrics = DeviceMetrics()
        
        # Callbacks
        self.on_device_changed: Optional[DeviceChangeCallback] = None
        self.on_device_switched: Optional[DeviceSwitchCallback] = None
        self.on_error: Optional[ErrorCallback] = None
        self.on_metrics_updated: Optional[MetricsCallback] = None
        
        # Настройка компонентов
        self._setup_components()
    
    def _setup_components(self):
        """Настройка компонентов"""
        try:
            # Настраиваем DeviceMonitor
            self.device_monitor.register_callback("device_manager", self._on_device_changed)
            
            # Настраиваем DeviceSwitcher
            self.device_switcher.set_switch_callback(self._on_device_switched)
            
            logger.info("✅ Компоненты AudioDeviceManager настроены")
        except Exception as e:
            logger.error(f"❌ Ошибка настройки компонентов: {e}")
            raise
    
    async def start(self) -> bool:
        """Запуск менеджера устройств"""
        try:
            if self.is_running:
                logger.warning("⚠️ AudioDeviceManager уже запущен")
                return True
            
            logger.info("🚀 Запуск AudioDeviceManager...")
            
            # Запускаем мониторинг
            await self.device_monitor.start_monitoring()
            
            # Получаем начальный список устройств через DeviceMonitor
            devices = await self.device_monitor.get_available_devices()
            self.metrics.total_devices = len(devices)
            self.metrics.available_devices = len([d for d in devices if d.is_available])
            self.metrics.unavailable_devices = len([d for d in devices if not d.is_available])
            
            # Определяем текущее устройство
            self.current_device = self._find_current_device(devices)
            
            # Автоматически переключаемся на лучшее доступное устройство
            if self.config.auto_switch_enabled:
                await self._auto_switch_to_best_device()
            
            self.is_running = True
            logger.info(f"✅ AudioDeviceManager запущен, найдено {len(devices)} устройств")
            
            # Уведомляем о метриках
            self._notify_metrics_updated()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска AudioDeviceManager: {e}")
            self._notify_error(e, "start")
            return False
    
    async def stop(self) -> bool:
        """Остановка менеджера устройств"""
        try:
            if not self.is_running:
                logger.warning("⚠️ AudioDeviceManager не запущен")
                return True
            
            logger.info("🛑 Остановка AudioDeviceManager...")
            
            # Останавливаем мониторинг
            await self.device_monitor.stop_monitoring()
            
            self.is_running = False
            self.current_device = None
            
            logger.info("✅ AudioDeviceManager остановлен")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка остановки AudioDeviceManager: {e}")
            self._notify_error(e, "stop")
            return False
    
    async def get_available_devices(self, device_type: Optional[DeviceType] = None) -> List[AudioDevice]:
        """Получение списка доступных устройств"""
        try:
            devices = await self.device_monitor.get_available_devices()
            
            if device_type:
                devices = [d for d in devices if d.type == device_type]
            
            return devices
        except Exception as e:
            logger.error(f"❌ Ошибка получения устройств: {e}")
            self._notify_error(e, "get_available_devices")
            return []
    
    async def get_current_device(self) -> Optional[AudioDevice]:
        """Получение текущего устройства"""
        try:
            if not self.is_running:
                return None
            
            # Обновляем текущее устройство
            devices = await self.device_monitor.get_available_devices()
            self.current_device = self._find_current_device(devices)
            
            return self.current_device
        except Exception as e:
            logger.error(f"❌ Ошибка получения текущего устройства: {e}")
            self._notify_error(e, "get_current_device")
            return None
    
    async def switch_to_device(self, device: AudioDevice) -> bool:
        """Переключение на конкретное устройство"""
        try:
            if not self.is_running:
                logger.warning("⚠️ AudioDeviceManager не запущен")
                return False
            
            logger.info(f"🔄 Переключение на устройство: {device.name}")
            
            # Выполняем переключение через DeviceSwitcher
            success = await self.device_switcher._switch_to_device(device)
            
            if success:
                self.current_device = device
                self.metrics.total_switches += 1
                self.metrics.successful_switches += 1
                self.metrics.last_switch_time = device.last_seen
                logger.info(f"✅ Успешно переключились на: {device.name}")
            else:
                self.metrics.total_switches += 1
                self.metrics.failed_switches += 1
                logger.error(f"❌ Не удалось переключиться на: {device.name}")
            
            # Уведомляем о переключении
            self._notify_device_switched(device, success)
            self._notify_metrics_updated()
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Ошибка переключения устройства: {e}")
            self._notify_error(e, "switch_to_device")
            return False
    
    async def get_best_device(self, device_type: DeviceType = DeviceType.OUTPUT) -> Optional[AudioDevice]:
        """Получение лучшего устройства по типу"""
        try:
            devices = await self.get_available_devices(device_type)
            if not devices:
                return None
            
            # Используем логику DeviceSwitcher для поиска лучшего устройства
            if hasattr(self.device_switcher, '_find_best_device'):
                return self.device_switcher._find_best_device(devices)
            else:
                # Если метод недоступен, используем простую логику
                output_devices = [d for d in devices if d.type == DeviceType.OUTPUT and d.is_available]
                if output_devices:
                    return min(output_devices, key=lambda x: x.priority.value)
                return None
        except Exception as e:
            logger.error(f"❌ Ошибка поиска лучшего устройства: {e}")
            self._notify_error(e, "get_best_device")
            return None
    
    def get_metrics(self) -> DeviceMetrics:
        """Получение метрик"""
        return self.metrics
    
    def is_device_available(self, device_id: str) -> bool:
        """Проверка доступности устройства"""
        try:
            device = self.device_monitor.get_device_by_id(device_id)
            return device is not None and device.is_available
        except Exception as e:
            logger.error(f"❌ Ошибка проверки доступности устройства: {e}")
            return False
    
    def set_auto_switch_enabled(self, enabled: bool):
        """Включение/отключение автоматического переключения"""
        self.config.auto_switch_enabled = enabled
        self.device_switcher.auto_switch_enabled = enabled
        logger.info(f"🔄 Автоматическое переключение: {'включено' if enabled else 'отключено'}")
    
    def set_device_priority(self, device_id: str, priority: int):
        """Установка приоритета устройства"""
        try:
            self.config.device_priorities[device_id] = priority
            logger.info(f"📊 Приоритет устройства {device_id} установлен: {priority}")
        except Exception as e:
            logger.error(f"❌ Ошибка установки приоритета: {e}")
            self._notify_error(e, "set_device_priority")
    
    # Callback методы
    def set_device_changed_callback(self, callback: DeviceChangeCallback):
        """Установка callback для изменений устройств"""
        self.on_device_changed = callback
    
    def set_device_switched_callback(self, callback: DeviceSwitchCallback):
        """Установка callback для переключений устройств"""
        self.on_device_switched = callback
    
    def set_error_callback(self, callback: ErrorCallback):
        """Установка callback для ошибок"""
        self.on_error = callback
    
    def set_metrics_callback(self, callback: MetricsCallback):
        """Установка callback для метрик"""
        self.on_metrics_updated = callback
    
    # Внутренние методы
    def _find_current_device(self, devices: List[AudioDevice]) -> Optional[AudioDevice]:
        """Поиск текущего устройства"""
        try:
            # Ищем устройство по умолчанию
            default_devices = [d for d in devices if d.is_default and d.is_available]
            if default_devices:
                return default_devices[0]
            
            # Если нет устройства по умолчанию, ищем лучшее доступное устройство вывода
            output_devices = [d for d in devices if d.type == DeviceType.OUTPUT and d.is_available]
            if output_devices:
                # Сортируем по приоритету (меньшее число = выше приоритет)
                best_device = min(output_devices, key=lambda x: x.priority.value)
                logger.info(f"🎯 Найдено лучшее устройство: {best_device.name} (приоритет: {best_device.priority.value})")
                return best_device
            
            return None
        except Exception as e:
            logger.error(f"❌ Ошибка поиска текущего устройства: {e}")
            return None
    
    async def _auto_switch_to_best_device(self):
        """Автоматическое переключение на лучшее устройство"""
        try:
            devices = await self.get_available_devices()
            if not devices:
                logger.warning("⚠️ Нет устройств для автоматического переключения")
                return
            
            # Находим лучшее устройство
            best_device = self._find_current_device(devices)
            if not best_device:
                logger.warning("⚠️ Не найдено подходящее устройство для переключения")
                return
            
            # Переключаемся на лучшее устройство
            logger.info(f"🔄 Автоматическое переключение на: {best_device.name}")
            success = await self.device_switcher.switch_to_device_type(DeviceType.OUTPUT)
            
            if success:
                self.current_device = best_device
                logger.info(f"✅ Успешно переключились на: {best_device.name}")
                self.metrics.total_switches += 1
                self.metrics.successful_switches += 1
            else:
                logger.warning(f"⚠️ Не удалось переключиться на: {best_device.name}")
                self.metrics.total_switches += 1
            
        except Exception as e:
            logger.error(f"❌ Ошибка автоматического переключения: {e}")
    
    async def _handle_device_changes_async(self, change: DeviceChange):
        """Асинхронная обработка изменений устройств"""
        try:
            logger.debug("🔍 [DEBUG] Начало обработки изменений устройств")
            
            # Проверяем что DeviceSwitcher доступен
            if not self.device_switcher:
                logger.warning("⚠️ DeviceSwitcher недоступен")
                return
            
            logger.debug(f"🔍 [DEBUG] DeviceSwitcher: {type(self.device_switcher)}")
            logger.debug(f"🔍 [DEBUG] DeviceSwitcher методы: {dir(self.device_switcher)}")
            
            # Обрабатываем изменения через DeviceSwitcher
            if hasattr(self.device_switcher, 'handle_device_changes'):
                logger.debug("🔍 [DEBUG] Вызываем device_switcher.handle_device_changes")
                result = await self.device_switcher.handle_device_changes(change)
                logger.debug(f"🔍 [DEBUG] Результат handle_device_changes: {result}")
            else:
                logger.warning("⚠️ DeviceSwitcher не имеет метода handle_device_changes")
            
            # Если есть новые устройства, переключаемся на лучшее
            if change.added:
                logger.info(f"➕ Обнаружены новые устройства: {[d.name for d in change.added]}")
                logger.debug("🔍 [DEBUG] Вызываем _auto_switch_to_best_device")
                await self._auto_switch_to_best_device()
            
            logger.debug("🔍 [DEBUG] Завершение обработки изменений устройств")
            
        except Exception as e:
            logger.error(f"❌ Ошибка асинхронной обработки изменений: {e}")
            import traceback
            logger.error(f"🔍 [DEBUG] Traceback: {traceback.format_exc()}")
    
    def _on_device_changed(self, change: DeviceChange):
        """Обработка изменений устройств"""
        try:
            # Обновляем метрики
            self.metrics.total_devices = len(change.current_devices)
            self.metrics.available_devices = len([d for d in change.current_devices.values() if d.is_available])
            self.metrics.unavailable_devices = len([d for d in change.current_devices.values() if not d.is_available])
            
            # Обрабатываем изменения через DeviceSwitcher (без await)
            if hasattr(self.config, 'auto_switch_enabled') and self.config.auto_switch_enabled:
                # Создаем задачу для асинхронной обработки
                try:
                    logger.debug("🔍 [DEBUG] Создание задачи для обработки изменений")
                    loop = asyncio.get_event_loop()
                    logger.debug(f"🔍 [DEBUG] Event loop: {loop}")
                    logger.debug(f"🔍 [DEBUG] Event loop запущен: {loop.is_running()}")
                    
                    if loop.is_running():
                        # Используем create_task правильно
                        logger.debug("🔍 [DEBUG] Создаем задачу _handle_device_changes_async")
                        task = loop.create_task(self._handle_device_changes_async(change))
                        logger.debug(f"🔍 [DEBUG] Задача создана: {task}")
                        # Не ждем завершения задачи
                    else:
                        logger.debug("Event loop не запущен, пропускаем обработку изменений")
                except RuntimeError as e:
                    logger.debug(f"Нет активного event loop: {e}")
                except Exception as e:
                    logger.error(f"Ошибка создания задачи: {e}")
                    import traceback
                    logger.error(f"🔍 [DEBUG] Traceback создания задачи: {traceback.format_exc()}")
            
            # Уведомляем о изменениях
            self._notify_device_changed(change)
            self._notify_metrics_updated()
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки изменений устройств: {e}")
            self._notify_error(e, "_on_device_changed")
    
    def _on_device_switched(self, device: AudioDevice, success: bool):
        """Обработка переключения устройств"""
        try:
            if success:
                self.current_device = device
                self.metrics.successful_switches += 1
            else:
                self.metrics.failed_switches += 1
            
            self.metrics.total_switches += 1
            self.metrics.last_switch_time = device.last_seen
            
            # Уведомляем о переключении
            self._notify_device_switched(device, success)
            self._notify_metrics_updated()
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки переключения устройств: {e}")
            self._notify_error(e, "_on_device_switched")
    
    def _notify_device_changed(self, change: DeviceChange):
        """Уведомление об изменениях устройств"""
        if self.on_device_changed:
            try:
                self.on_device_changed(change)
            except Exception as e:
                logger.error(f"❌ Ошибка в callback изменений устройств: {e}")
    
    def _notify_device_switched(self, device: AudioDevice, success: bool):
        """Уведомление о переключении устройств"""
        if self.on_device_switched:
            try:
                self.on_device_switched(device, success)
            except Exception as e:
                logger.error(f"❌ Ошибка в callback переключения устройств: {e}")
    
    def _notify_error(self, error: Exception, context: str):
        """Уведомление об ошибках"""
        if self.on_error:
            try:
                self.on_error(error, context)
            except Exception as e:
                logger.error(f"❌ Ошибка в error callback: {e}")
    
    def _notify_metrics_updated(self):
        """Уведомление об обновлении метрик"""
        if self.on_metrics_updated:
            try:
                self.on_metrics_updated(self.metrics)
            except Exception as e:
                logger.error(f"❌ Ошибка в metrics callback: {e}")
    
    async def cleanup(self):
        """Очистка ресурсов"""
        try:
            await self.stop()
            logger.info("🧹 AudioDeviceManager очищен")
        except Exception as e:
            logger.error(f"❌ Ошибка очистки AudioDeviceManager: {e}")
