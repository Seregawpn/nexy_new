"""
Device Monitor - центральный мониторинг изменений аудио устройств
"""

import asyncio
import logging
from typing import Dict, List, Optional, Callable
from .types import AudioDevice, DeviceChange, DeviceChangeCallback
from ..macos.switchaudio_bridge import SwitchAudioBridge

logger = logging.getLogger(__name__)

class DeviceMonitor:
    """Центральный мониторинг изменений аудио устройств"""
    
    def __init__(self):
        self._is_monitoring = False
        self._callbacks: Dict[str, DeviceChangeCallback] = {}
        self._core_audio_bridge = SwitchAudioBridge()
        self._device_cache: Dict[str, AudioDevice] = {}
        self._monitoring_task: Optional[asyncio.Task] = None
        
    async def start_monitoring(self):
        """Запуск мониторинга изменений устройств"""
        if self._is_monitoring:
            logger.warning("⚠️ Мониторинг уже запущен")
            return
        
        try:
            self._is_monitoring = True
            
            # Запускаем Core Audio мониторинг
            await self._core_audio_bridge.start_monitoring(self._on_device_changed)
            
            # Получаем начальный список устройств
            initial_devices = await self._core_audio_bridge.get_available_devices()
            self._device_cache = {device.id: device for device in initial_devices}
            
            logger.info(f"✅ Мониторинг устройств запущен, найдено {len(initial_devices)} устройств")
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска мониторинга: {e}")
            self._is_monitoring = False
            raise
    
    async def stop_monitoring(self):
        """Остановка мониторинга"""
        if not self._is_monitoring:
            return
        
        try:
            # Останавливаем Core Audio мониторинг
            await self._core_audio_bridge.stop_monitoring()
            
            # Очищаем состояние
            self._is_monitoring = False
            self._callbacks.clear()
            self._device_cache.clear()
            
            if self._monitoring_task and not self._monitoring_task.done():
                self._monitoring_task.cancel()
                try:
                    await self._monitoring_task
                except asyncio.CancelledError:
                    pass
            
            logger.info("✅ Мониторинг устройств остановлен")
            
        except Exception as e:
            logger.error(f"❌ Ошибка остановки мониторинга: {e}")
    
    def register_callback(self, module_name: str, callback: DeviceChangeCallback):
        """Регистрация callback для получения уведомлений об изменениях"""
        try:
            self._callbacks[module_name] = callback
            logger.info(f"✅ Зарегистрирован callback для модуля: {module_name}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка регистрации callback для {module_name}: {e}")
    
    def unregister_callback(self, module_name: str):
        """Отмена регистрации callback"""
        try:
            if module_name in self._callbacks:
                del self._callbacks[module_name]
                logger.info(f"✅ Отменена регистрация callback для модуля: {module_name}")
            else:
                logger.warning(f"⚠️ Callback для модуля {module_name} не найден")
                
        except Exception as e:
            logger.error(f"❌ Ошибка отмены регистрации callback для {module_name}: {e}")
    
    async def get_available_devices(self) -> List[AudioDevice]:
        """Получение доступных устройств"""
        try:
            return await self._core_audio_bridge.get_available_devices()
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения доступных устройств: {e}")
            return []
    
    async def get_current_devices(self) -> List[AudioDevice]:
        """Получение текущего списка устройств"""
        try:
            if self._is_monitoring:
                return list(self._device_cache.values())
            else:
                # Если мониторинг не запущен, получаем устройства напрямую
                return await self._core_audio_bridge.get_available_devices()
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения текущих устройств: {e}")
            return []
    
    async def get_default_device(self) -> Optional[AudioDevice]:
        """Получение устройства по умолчанию"""
        try:
            return await self._core_audio_bridge.get_default_output_device()
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения устройства по умолчанию: {e}")
            return None
    
    async def set_default_device(self, device_id: str) -> bool:
        """Установка устройства по умолчанию"""
        try:
            return await self._core_audio_bridge.set_default_output_device(device_id)
            
        except Exception as e:
            logger.error(f"❌ Ошибка установки устройства по умолчанию: {e}")
            return False
    
    async def _on_device_changed(self, changes: DeviceChange):
        """Обработка изменений устройств от Core Audio"""
        try:
            # Обновляем кэш
            self._device_cache = changes.current_devices
            
            # Логируем изменения
            if changes.added:
                logger.info(f"➕ Добавлены устройства: {[d.name for d in changes.added]}")
            if changes.removed:
                logger.info(f"➖ Удалены устройства: {[d.name for d in changes.removed]}")
            # Логируем изменения устройств
            if changes.added or changes.removed:
                logger.info(f"🔄 Изменения устройств: добавлено={len(changes.added)}, удалено={len(changes.removed)}")
            
            # Уведомляем все зарегистрированные модули
            await self._notify_callbacks(changes)
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки изменений устройств: {e}")
    
    async def _notify_callbacks(self, changes: DeviceChange):
        """Уведомление всех зарегистрированных callback'ов"""
        try:
            if not self._callbacks:
                logger.debug("🔍 Нет зарегистрированных callback'ов")
                return
            
            # Создаем задачи для асинхронного уведомления
            tasks = []
            for module_name, callback in self._callbacks.items():
                task = asyncio.create_task(
                    self._safe_callback_execution(module_name, callback, changes)
                )
                tasks.append(task)
            
            # Ждем выполнения всех callback'ов
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
                
        except Exception as e:
            logger.error(f"❌ Ошибка уведомления callback'ов: {e}")
    
    async def _safe_callback_execution(self, module_name: str, callback: DeviceChangeCallback, changes: DeviceChange):
        """Безопасное выполнение callback'а"""
        try:
            await callback(changes)
            logger.debug(f"✅ Callback модуля {module_name} выполнен успешно")
            
        except Exception as e:
            logger.error(f"❌ Ошибка в callback модуля {module_name}: {e}")
    
    def is_monitoring(self) -> bool:
        """Проверка, запущен ли мониторинг"""
        return self._is_monitoring
    
    def get_registered_modules(self) -> List[str]:
        """Получение списка зарегистрированных модулей"""
        return list(self._callbacks.keys())
    
    def get_device_count(self) -> int:
        """Получение количества отслеживаемых устройств"""
        return len(self._device_cache)
