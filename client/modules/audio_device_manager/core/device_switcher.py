"""
Device Switcher - логика автоматического переключения устройств
"""

import logging
from typing import List, Optional, Dict, Callable
from .types import AudioDevice, DeviceChange, DeviceType
from .device_monitor import DeviceMonitor

logger = logging.getLogger(__name__)

class DeviceSwitcher:
    """Логика автоматического переключения аудио устройств"""
    
    def __init__(self, device_monitor: DeviceMonitor):
        self.device_monitor = device_monitor
        self.current_device: Optional[AudioDevice] = None
        self.auto_switch_enabled = True
        
        # Callbacks
        self.on_device_switched: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
    
    def set_switch_callback(self, callback: Callable):
        """Установка callback для переключения устройств"""
        self.on_device_switched = callback
    
    def set_error_callback(self, callback: Callable):
        """Установка callback для ошибок"""
        self.on_error = callback
        
    async def handle_device_changes(self, changes: DeviceChange):
        """Обработка изменений устройств и автоматическое переключение"""
        try:
            if not self.auto_switch_enabled:
                logger.debug("🔄 Автоматическое переключение отключено")
                return
            
            # Если есть новые устройства, проверяем приоритеты
            if changes.added:
                await self._handle_new_devices(changes.added, changes.current_devices)
            
            # Если текущее устройство отключено, переключаемся на лучшее доступное
            if changes.removed:
                await self._handle_removed_devices(changes.removed, changes.current_devices)
            
            # Обновляем текущее устройство
            await self._update_current_device(changes.current_devices)
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки изменений устройств: {e}")
    
    async def _handle_new_devices(self, new_devices: List[AudioDevice], all_devices: Dict[str, AudioDevice]):
        """Обработка новых устройств"""
        try:
            if not new_devices:
                return
            
            # Находим лучшее устройство среди новых
            best_new_device = self._find_best_device(new_devices)
            if not best_new_device:
                return
            
            # Сравниваем с текущим устройством
            if self.current_device:
                # Меньшее числовое значение = более высокий приоритет
                if best_new_device.priority.value < self.current_device.priority.value:
                    logger.info(f"🔄 Переключение на более приоритетное устройство: {best_new_device.name}")
                    await self._switch_to_device(best_new_device)
                else:
                    logger.info(f"ℹ️ Новое устройство {best_new_device.name} имеет более низкий приоритет, оставляем текущее")
            else:
                # Если нет текущего устройства, переключаемся на лучшее
                logger.info(f"🔄 Переключение на новое устройство: {best_new_device.name}")
                await self._switch_to_device(best_new_device)
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки новых устройств: {e}")
    
    async def _handle_removed_devices(self, removed_devices: List[AudioDevice], all_devices: Dict[str, AudioDevice]):
        """Обработка отключенных устройств"""
        try:
            if not removed_devices:
                return
            
            # Проверяем, было ли отключено текущее устройство
            current_removed = False
            if self.current_device:
                for removed_device in removed_devices:
                    if removed_device.id == self.current_device.id:
                        current_removed = True
                        logger.info(f"⚠️ Текущее устройство отключено: {removed_device.name}")
                        break
            
            if current_removed:
                # Переключаемся на лучшее доступное устройство
                best_available = self._find_best_device(list(all_devices.values()))
                if best_available:
                    logger.info(f"🔄 Переключение на доступное устройство: {best_available.name}")
                    await self._switch_to_device(best_available)
                else:
                    logger.warning("⚠️ Нет доступных устройств для переключения")
                    self.current_device = None
                    
        except Exception as e:
            logger.error(f"❌ Ошибка обработки отключенных устройств: {e}")
    
    async def _update_current_device(self, all_devices: Dict[str, AudioDevice]):
        """Обновление информации о текущем устройстве"""
        try:
            if not all_devices:
                self.current_device = None
                return
            
            # Если нет текущего устройства, выбираем лучшее
            if not self.current_device:
                best_device = self._find_best_device(list(all_devices.values()))
                if best_device:
                    self.current_device = best_device
                    logger.info(f"🎯 Установлено текущее устройство: {best_device.name}")
            else:
                # Обновляем информацию о текущем устройстве
                if self.current_device.id in all_devices:
                    self.current_device = all_devices[self.current_device.id]
                else:
                    # Текущее устройство больше не доступно
                    self.current_device = None
                    
        except Exception as e:
            logger.error(f"❌ Ошибка обновления текущего устройства: {e}")
    
    def _find_best_device(self, devices: List[AudioDevice]) -> Optional[AudioDevice]:
        """Поиск лучшего устройства по приоритету"""
        try:
            if not devices:
                return None
            
            # Фильтруем только подключенные устройства вывода (исключаем микрофоны)
            connected_devices = [
                d for d in devices 
                if d.status.value == "available" and d.type == DeviceType.OUTPUT
            ]
            
            if not connected_devices:
                logger.warning("⚠️ Нет подходящих устройств для переключения")
                return None
            
            # Сортируем по приоритету (меньшее значение = выше приоритет)
            sorted_devices = sorted(connected_devices, key=lambda x: x.priority.value)
            
            best_device = sorted_devices[0]
            logger.info(f"🏆 Лучшее устройство: {best_device.name} (тип: {best_device.type.value}, приоритет: {best_device.priority})")
            
            return best_device
            
        except Exception as e:
            logger.error(f"❌ Ошибка поиска лучшего устройства: {e}")
            return None
    
    async def _switch_to_device(self, device: AudioDevice):
        """Переключение на указанное устройство"""
        try:
            logger.info(f"🔄 Переключение на устройство: {device.name} ({device.type.value})")
            
            # Устанавливаем устройство по умолчанию
            success = await self.device_monitor.set_default_device(device.id)
            if success:
                self.current_device = device
                logger.info(f"✅ Успешно переключено на: {device.name}")
                
                # Логируем информацию об устройстве
                self._log_device_info(device)
            else:
                logger.error(f"❌ Не удалось переключиться на: {device.name}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка переключения на устройство {device.name}: {e}")
    
    def _log_device_info(self, device: AudioDevice):
        """Логирование информации об устройстве"""
        try:
            logger.info(f"📱 Устройство: {device.name}")
            logger.info(f"   Тип: {device.type.value}")
            logger.info(f"   Каналы: {device.channels}")
            logger.info(f"   Приоритет: {device.priority}")
            # Определяем тип устройства по названию
            name_lower = device.name.lower()
            is_bluetooth = 'bluetooth' in name_lower or 'airpods' in name_lower
            is_usb = 'usb' in name_lower
            is_builtin = 'built-in' in name_lower or 'internal' in name_lower or 'macbook' in name_lower
            
            logger.info(f"   Bluetooth: {'Да' if is_bluetooth else 'Нет'}")
            logger.info(f"   USB: {'Да' if is_usb else 'Нет'}")
            logger.info(f"   Встроенное: {'Да' if is_builtin else 'Нет'}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка логирования информации об устройстве: {e}")
    
    async def switch_to_best_device(self) -> bool:
        """Переключение на лучшее доступное устройство"""
        try:
            devices = await self.device_monitor.get_current_devices()
            best_device = self._find_best_device(devices)
            
            if best_device:
                await self._switch_to_device(best_device)
                return True
            else:
                logger.warning("⚠️ Нет доступных устройств для переключения")
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка переключения на лучшее устройство: {e}")
            return False
    
    async def switch_to_device_type(self, device_type: DeviceType) -> bool:
        """Переключение на устройство определенного типа"""
        try:
            devices = await self.device_monitor.get_current_devices()
            type_devices = [d for d in devices if d.type == device_type and d.status.value == "available"]
            
            if not type_devices:
                logger.warning(f"⚠️ Нет доступных устройств типа {device_type.value}")
                return False
            
            best_device = self._find_best_device(type_devices)
            if best_device:
                await self._switch_to_device(best_device)
                return True
            else:
                logger.warning(f"⚠️ Не удалось найти подходящее устройство типа {device_type.value}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка переключения на тип устройства {device_type.value}: {e}")
            return False
    
    def enable_auto_switch(self):
        """Включение автоматического переключения"""
        self.auto_switch_enabled = True
        logger.info("✅ Автоматическое переключение включено")
    
    def disable_auto_switch(self):
        """Отключение автоматического переключения"""
        self.auto_switch_enabled = False
        logger.info("❌ Автоматическое переключение отключено")
    
    def get_current_device(self) -> Optional[AudioDevice]:
        """Получение текущего устройства"""
        return self.current_device
    
    def is_auto_switch_enabled(self) -> bool:
        """Проверка, включено ли автоматическое переключение"""
        return self.auto_switch_enabled










































