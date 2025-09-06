"""
UnifiedAudioSystem - Единая централизованная система управления аудио устройствами

Этот модуль является ЕДИНСТВЕННЫМ источником истины для всех аудио операций:
- Определение доступных устройств
- Переключение устройств
- Мониторинг изменений
- Синхронизация с PortAudio
- Управление приоритетами

Все остальные компоненты (AudioPlayer, AudioManagerDaemon) должны использовать ТОЛЬКО эту систему.
"""

import subprocess
import time
import threading
import logging
from typing import Dict, List, Optional, Set, Callable, Tuple
from dataclasses import dataclass
from enum import Enum
import sounddevice as sd
from realtime_device_monitor import get_global_realtime_monitor, DeviceEvent

logger = logging.getLogger(__name__)

class DeviceType(Enum):
    """Типы аудио устройств"""
    AIRPODS = "airpods"
    BEATS = "beats"
    BLUETOOTH_HEADPHONES = "bluetooth_headphones"
    USB_HEADPHONES = "usb_headphones"
    SPEAKERS = "speakers"
    MICROPHONE = "microphone"
    VIRTUAL = "virtual"
    UNKNOWN = "unknown"

@dataclass
class DeviceInfo:
    """Информация об аудио устройстве"""
    name: str
    device_type: DeviceType
    priority: int
    is_default: bool = False
    portaudio_output_index: Optional[int] = None
    portaudio_input_index: Optional[int] = None
    is_connected: bool = True

class UnifiedAudioSystem:
    """
    Единая централизованная система управления аудио устройствами
    
    Принципы:
    1. ЕДИНСТВЕННЫЙ источник истины для всех аудио операций
    2. Атомарные операции - все изменения происходят в одном месте
    3. Автоматическая синхронизация всех компонентов
    4. Надежная обработка ошибок и восстановление
    """
    
    def __init__(self, config: Dict = None):
        self.config = config if config is not None else {}
        self._lock = threading.RLock()
        self._initialized = False
        self._current_device = None
        self._devices_cache = {}  # Минимальный кэш только для совместимости
        self._callbacks = []
        self._realtime_monitor = None
        
        # Путь к SwitchAudioSource
        self.switch_audio_path = self.config.get('switch_audio_path', 'SwitchAudioSource')
        
        # Приоритеты устройств загружаются из конфигурации
        self.device_priorities = self._load_device_priorities_from_config()
        
        logger.info("🎛️ UnifiedAudioSystem создан")
    
    def _load_device_priorities_from_config(self) -> Dict[str, int]:
        """Загружает приоритеты устройств из конфигурации"""
        try:
            import yaml
            import os
            
            # Путь к конфигурации
            config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'app_config.yaml')
            
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    
                # Получаем приоритеты из конфигурации
                device_priorities = config.get('device_manager', {}).get('device_priorities', {})
                
                if device_priorities:
                    logger.info("✅ Приоритеты устройств загружены из конфигурации")
                    return device_priorities
            
            # Fallback приоритеты, если конфигурация недоступна
            logger.warning("⚠️ Конфигурация недоступна, используем fallback приоритеты")
            return {
                'airpods': 100,
                'beats': 95,
                'bluetooth_headphones': 90,
                'usb_headphones': 85,
                'bluetooth_speakers': 70,
                'usb_audio': 60,
                'speakers': 40,
                'built_in': 20,
                'other': 10,
                'microphone': 5,
                'virtual_device': 1,
                'unknown': 5
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки приоритетов из конфигурации: {e}")
            # Fallback приоритеты
            return {
                'airpods': 100,
                'beats': 95,
                'bluetooth_headphones': 90,
                'usb_headphones': 85,
                'bluetooth_speakers': 70,
                'usb_audio': 60,
                'speakers': 40,
                'built_in': 20,
                'other': 10,
                'microphone': 5,
                'virtual_device': 1,
                'unknown': 5
            }
    
    def initialize(self) -> bool:
        """Инициализирует систему"""
        try:
            with self._lock:
                logger.info("🔄 Инициализация UnifiedAudioSystem...")
                
                # Получаем актуальный список устройств БЕЗ кэширования
                self._current_device = self._get_best_available_device_realtime()
                
                # Инициализируем RealtimeDeviceMonitor
                self._init_realtime_monitor()
                
                self._initialized = True
                logger.info("✅ UnifiedAudioSystem успешно инициализирован")
                return True
                
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации UnifiedAudioSystem: {e}")
            return False
    
    def _init_realtime_monitor(self):
        """Инициализирует RealtimeDeviceMonitor"""
        try:
            self._realtime_monitor = get_global_realtime_monitor()
            if self._realtime_monitor:
                self._realtime_monitor.add_callback(self._on_device_event)
                logger.info("✅ RealtimeDeviceMonitor подключен")
            else:
                logger.warning("⚠️ RealtimeDeviceMonitor недоступен")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации RealtimeDeviceMonitor: {e}")
    
    def _on_device_event(self, event: DeviceEvent):
        """Обрабатывает события от RealtimeDeviceMonitor"""
        try:
            logger.info(f"🔔 Получено событие от RealtimeDeviceMonitor: {event.event_type.value} - {event.device_name}")
            
            # Уведомляем наши callbacks
            self._notify_callbacks(event.event_type.value, {
                'device_name': event.device_name,
                'timestamp': event.timestamp,
                'previous_devices': list(event.previous_devices),
                'current_devices': list(event.current_devices)
            })
            
            # Уведомляем AudioPlayer об изменении устройств
            self._notify_audio_player_device_changed()
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки события устройства: {e}")
    
    def _get_real_time_devices(self) -> List[Dict]:
        """Получает актуальный список устройств БЕЗ кэширования"""
        try:
            # Получаем устройства напрямую из PortAudio
            devices = sd.query_devices()
            real_devices = []
            
            for i, device in enumerate(devices):
                if device.get('max_output_channels', 0) > 0:  # Только выходные устройства
                    device_name = device.get('name', f'Device {i}')
                    device_type = self._detect_device_type(device_name)
                    priority = self._calculate_priority(device_name, device_type)
                    
                    real_devices.append({
                        'name': device_name,
                        'type': device_type,
                        'priority': priority,
                        'index': i,
                        'is_connected': True
                    })
            
            return real_devices
        except Exception as e:
            logger.error(f"❌ Ошибка получения устройств в реальном времени: {e}")
            return []
    
    def _immediate_switch_to_best_device(self, available_devices: Set[str]):
        """Мгновенно переключается на лучшее доступное устройство"""
        try:
            if not available_devices:
                logger.warning("⚠️ Нет доступных устройств")
                return False
            
            # Делегируем выбор лучшего устройства в AudioDeviceManager
            try:
                from audio_device_manager import get_global_audio_device_manager
                audio_device_manager = get_global_audio_device_manager()
                
                if audio_device_manager:
                    best_device = audio_device_manager.find_best_available_device(list(available_devices))
                    if best_device:
                        logger.info(f"🎯 AudioDeviceManager выбрал: {best_device}")
                        
                        # Переключаемся через SwitchAudioSource
                        result = subprocess.run([self.switch_audio_path, '-s', best_device], 
                                              capture_output=True, text=True, timeout=5)
                        
                        if result.returncode == 0:
                            self._current_device = best_device
                            logger.info(f"✅ Успешно переключились на: {best_device}")
                            return True
                        else:
                            logger.error(f"❌ Ошибка переключения на {best_device}: {result.stderr}")
                            return False
                    else:
                        logger.warning("⚠️ AudioDeviceManager не смог выбрать устройство")
                        return False
                else:
                    logger.warning("⚠️ AudioDeviceManager недоступен")
                    return False
                    
            except Exception as e:
                logger.error(f"❌ Ошибка получения AudioDeviceManager: {e}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка мгновенного переключения: {e}")
            return False
    
    def handle_device_removed(self, removed_devices: Set[str]):
        """
        Обрабатывает отключение устройств - РЕАКТИВНО БЕЗ КЭШИРОВАНИЯ
        
        Принцип: НЕ кэшируем, всегда получаем актуальную информацию
        """
        try:
            with self._lock:
                logger.info(f"🔔 Обработка отключенных устройств: {list(removed_devices)}")
                
                # Получаем АКТУАЛЬНЫЙ список устройств (без кэша)
                current_devices = self._get_real_time_devices()
                current_device_names = {device['name'] for device in current_devices}
                
                # Проверяем, было ли отключено текущее устройство
                current_removed = False
                for device_name in removed_devices:
                    if device_name == self._current_device:
                        current_removed = True
                        break
                
                if current_removed:
                    logger.info(f"🔄 Текущее устройство отключено: {self._current_device}")
                    
                    # НЕМЕДЛЕННО переключаемся на лучшее доступное устройство
                    # без кэширования и задержек
                    self._immediate_switch_to_best_device(current_device_names)
                
                # Уведомляем callbacks
                for device_name in removed_devices:
                    self._notify_callbacks('device_removed', {
                        'device_name': device_name
                    })
                
                logger.info("✅ Обработка отключения устройств завершена")
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки отключения устройств: {e}")
    
    def handle_device_added(self, added_devices: Set[str]):
        """
        Обрабатывает подключение устройств - РЕАКТИВНО БЕЗ КЭШИРОВАНИЯ
        """
        try:
            with self._lock:
                logger.info(f"🔔 Обработка подключенных устройств: {list(added_devices)}")
                
                # Получаем АКТУАЛЬНЫЙ список устройств
                current_devices = self._get_real_time_devices()
                current_device_names = {device['name'] for device in current_devices}
                
                # Проверяем, есть ли высокоприоритетные устройства
                for device_name in added_devices:
                    if device_name in current_device_names:
                        device_type = self._detect_device_type(device_name)
                        priority = self._calculate_priority(device_name, device_type)
                        
                        if priority >= 85:  # Высокий приоритет
                            logger.info(f"🎯 Обнаружено высокоприоритетное устройство: {device_name}")
                            self._immediate_switch_to_best_device(current_device_names)
                            break
                
                # Уведомляем callbacks
                for device_name in added_devices:
                    self._notify_callbacks('device_added', {
                        'device_name': device_name
                    })
                
                logger.info("✅ Обработка подключения устройств завершена")
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки подключения устройств: {e}")
    
    def _get_best_available_device_realtime(self) -> Optional[str]:
        """Получает лучшее доступное устройство в реальном времени"""
        try:
            devices = self._get_real_time_devices()
            if not devices:
                return None
            
            # Сортируем по приоритету
            devices.sort(key=lambda x: x['priority'], reverse=True)
            best_device = devices[0]['name']
            
            logger.info(f"🎯 Лучшее доступное устройство: {best_device}")
            return best_device
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения лучшего устройства: {e}")
            return None
    
    def _detect_device_type(self, device_name: str) -> DeviceType:
        """Определяет тип устройства по имени"""
        device_name_lower = device_name.lower()
        
        if 'airpods' in device_name_lower:
            return DeviceType.AIRPODS
        elif 'beats' in device_name_lower:
            return DeviceType.BEATS
        elif 'bluetooth' in device_name_lower and ('headphone' in device_name_lower or 'headset' in device_name_lower):
            return DeviceType.BLUETOOTH_HEADPHONES
        elif 'usb' in device_name_lower and ('headphone' in device_name_lower or 'headset' in device_name_lower):
            return DeviceType.USB_HEADPHONES
        elif 'speaker' in device_name_lower or 'динамик' in device_name_lower:
            return DeviceType.SPEAKERS
        elif 'microphone' in device_name_lower or 'микрофон' in device_name_lower:
            return DeviceType.MICROPHONE
        elif 'virtual' in device_name_lower:
            return DeviceType.VIRTUAL
        else:
            return DeviceType.UNKNOWN
    
    def _calculate_priority(self, device_name: str, device_type: DeviceType) -> int:
        """Вычисляет приоритет устройства"""
        base_priority = self.device_priorities.get(device_type.value, 5)
        
        # Дополнительные бонусы
        if 'default' in device_name.lower():
            base_priority += 10
        if 'built-in' in device_name.lower():
            base_priority += 5
        
        return base_priority
    
    def _notify_audio_player_device_changed(self):
        """Уведомляет AudioPlayer об изменении устройств"""
        try:
            # Ищем AudioPlayer среди callbacks
            for callback in self._callbacks:
                if hasattr(callback, 'notify_device_changed'):
                    logger.info("🔄 UnifiedAudioSystem: Уведомляю AudioPlayer об изменении устройств...")
                    callback.notify_device_changed()
                    logger.info("✅ UnifiedAudioSystem: AudioPlayer уведомлен об изменении устройств")
                    break
            else:
                logger.debug("ℹ️ UnifiedAudioSystem: AudioPlayer не найден среди callbacks")
        except Exception as e:
            logger.error(f"❌ Ошибка уведомления AudioPlayer об изменении устройств: {e}")
    
    # === Публичные методы для доступа к данным ===
    
    def get_current_device(self) -> Optional[str]:
        """Получает текущее устройство"""
        return self._current_device
    
    def get_current_device_info(self) -> Optional[DeviceInfo]:
        """Получает информацию о текущем устройстве"""
        if self._current_device:
            # Получаем актуальную информацию
            devices = self._get_real_time_devices()
            for device in devices:
                if device['name'] == self._current_device:
                    return DeviceInfo(
                        name=device['name'],
                        device_type=device['type'],
                        priority=device['priority'],
                        is_default=False,
                        is_connected=device['is_connected']
                    )
        return None
    
    def get_device_info(self, device_name: str) -> Optional[DeviceInfo]:
        """Получает информацию об устройстве по имени"""
        try:
            devices = self._get_real_time_devices()
            for device in devices:
                if device.get('name') == device_name:
                    return DeviceInfo(
                        name=device['name'],
                        device_type=device['type'],
                        priority=device['priority'],
                        is_default=False,
                        is_connected=device['is_connected']
                    )
            return None
        except Exception as e:
            logger.error(f"❌ Ошибка получения информации об устройстве {device_name}: {e}")
            return None
    
    def get_available_devices(self) -> List[DeviceInfo]:
        """Получает список доступных устройств"""
        devices = self._get_real_time_devices()
        return [DeviceInfo(
            name=device['name'],
            device_type=device['type'],
            priority=device['priority'],
            is_default=False,
            is_connected=device['is_connected']
        ) for device in devices]
    
    def switch_to_device(self, device_name: str) -> bool:
        """Переключается на указанное устройство"""
        try:
            with self._lock:
                logger.info(f"🔄 Переключение на устройство: {device_name}")
                
                # Проверяем, доступно ли устройство
                devices = self._get_real_time_devices()
                device_names = {device['name'] for device in devices}
                
                if device_name not in device_names:
                    logger.error(f"❌ Устройство {device_name} недоступно")
                    return False
                
                # Переключаемся через SwitchAudioSource
                result = subprocess.run([self.switch_audio_path, '-s', device_name], 
                                      capture_output=True, text=True, timeout=5)
                
                if result.returncode == 0:
                    self._current_device = device_name
                    logger.info(f"✅ Успешно переключились на: {device_name}")
                    return True
                else:
                    logger.error(f"❌ Ошибка переключения на {device_name}: {result.stderr}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Ошибка переключения устройства: {e}")
            return False
    
    def get_system_device(self) -> Optional[DeviceInfo]:
        """Получает системное устройство (динамики)"""
        devices = self._get_real_time_devices()
        for device in devices:
            if device['type'] == DeviceType.SPEAKERS:
                return DeviceInfo(
                    name=device['name'],
                    device_type=device['type'],
                    priority=device['priority'],
                    is_default=False,
                    is_connected=device['is_connected']
                )
        return None
    
    def add_callback(self, callback: Callable):
        """Добавляет callback для уведомлений"""
        if callback not in self._callbacks:
            self._callbacks.append(callback)
            logger.info("✅ Callback добавлен")
    
    def remove_callback(self, callback: Callable):
        """Удаляет callback"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
            logger.info("✅ Callback удален")
    
    def _notify_callbacks(self, event_type: str, data: Dict):
        """Уведомляет все callbacks о событии"""
        for callback in self._callbacks:
            try:
                if hasattr(callback, 'on_device_event'):
                    callback.on_device_event(event_type, data)
                elif callable(callback):
                    callback(event_type, data)
            except Exception as e:
                logger.error(f"❌ Ошибка в callback: {e}")
    
    def is_initialized(self) -> bool:
        """Проверяет, инициализирована ли система"""
        return self._initialized
    
    @property
    def running(self) -> bool:
        """Проверяет, запущена ли система (для совместимости с AudioPlayer)"""
        return self._initialized and (self._realtime_monitor is not None and self._realtime_monitor.is_monitoring())

# Глобальный экземпляр
_global_unified_audio_system = None

def get_global_unified_audio_system() -> Optional[UnifiedAudioSystem]:
    """Получает глобальный экземпляр UnifiedAudioSystem"""
    return _global_unified_audio_system

def initialize_global_unified_audio_system(config: Dict = None) -> UnifiedAudioSystem:
    """Инициализирует глобальный экземпляр UnifiedAudioSystem"""
    global _global_unified_audio_system
    
    if _global_unified_audio_system is None:
        _global_unified_audio_system = UnifiedAudioSystem(config)
        _global_unified_audio_system.initialize()
    
    return _global_unified_audio_system

def stop_global_unified_audio_system():
    """Останавливает глобальный экземпляр UnifiedAudioSystem"""
    global _global_unified_audio_system
    
    if _global_unified_audio_system:
        try:
            # Останавливаем мониторинг
            if hasattr(_global_unified_audio_system, '_realtime_monitor') and _global_unified_audio_system._realtime_monitor:
                _global_unified_audio_system._realtime_monitor.stop_monitoring()
            
            # Очищаем callbacks
            _global_unified_audio_system._callbacks.clear()
            
            # Сбрасываем состояние
            _global_unified_audio_system._initialized = False
            _global_unified_audio_system._current_device = None
            
            logger.info("✅ UnifiedAudioSystem остановлен")
        except Exception as e:
            logger.error(f"❌ Ошибка остановки UnifiedAudioSystem: {e}")
        finally:
            _global_unified_audio_system = None
