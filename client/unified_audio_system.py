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
    
    def __init__(self, config: Dict):
        self.config = config
        self.switch_audio_path = config.get('switch_audio_path', '/opt/homebrew/bin/SwitchAudioSource')
        
        # Единый кэш устройств - ЕДИНСТВЕННЫЙ источник истины
        self._devices_cache: Dict[str, DeviceInfo] = {}
        self._current_device: Optional[str] = None
        self._last_update_time: float = 0
        
        # Настройки приоритетов
        self.device_priorities = config.get('device_priorities', {})
        self.virtual_device_keywords = config.get('virtual_device_keywords', ['blackhole', 'loopback', 'virtual'])
        self.exclude_virtual_devices = config.get('exclude_virtual_devices', True)
        
        # Callbacks для уведомлений
        self._callbacks: List[Callable] = []
        
        # Блокировка для thread-safe операций
        self._lock = threading.RLock()
        
        # Флаг инициализации
        self._initialized = False
        
        # RealtimeDeviceMonitor для мониторинга в реальном времени
        self._realtime_monitor = None
        
        logger.info("🎵 UnifiedAudioSystem инициализирован")
    
    def initialize(self) -> bool:
        """Инициализация системы"""
        try:
            with self._lock:
                logger.info("🔄 Инициализация UnifiedAudioSystem...")
                
                # Принудительно обновляем кэш устройств
                self._force_refresh_devices()
                
                # Устанавливаем лучшее устройство по умолчанию
                self._auto_select_best_device()
                
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
            logger.info("🔄 Инициализация RealtimeDeviceMonitor...")
            
            # Получаем глобальный экземпляр RealtimeDeviceMonitor
            self._realtime_monitor = get_global_realtime_monitor()
            
            # Добавляем callback для обработки событий
            self._realtime_monitor.add_callback(self._on_device_event)
            
            # Запускаем мониторинг
            self._realtime_monitor.start_monitoring()
            
            logger.info("✅ RealtimeDeviceMonitor инициализирован и запущен")
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации RealtimeDeviceMonitor: {e}")
    
    def _on_device_event(self, event: DeviceEvent):
        """Обрабатывает события от RealtimeDeviceMonitor"""
        try:
            logger.info(f"🔔 Получено событие от RealtimeDeviceMonitor: {event.event_type.value} - {event.device_name}")
            
            # Обновляем кэш устройств
            self._force_refresh_devices()
            
            # Уведомляем наши callbacks
            self._notify_callbacks(event.event_type.value, {
                'device_name': event.device_name,
                'timestamp': event.timestamp,
                'previous_devices': list(event.previous_devices),
                'current_devices': list(event.current_devices)
            })
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки события устройства: {e}")
    
    def _force_refresh_devices(self):
        """Принудительно обновляет кэш устройств из всех источников"""
        try:
            logger.info("🔄 Принудительное обновление кэша устройств...")
            
            # ИСПРАВЛЕНИЕ: Принудительно обновляем SwitchAudioSource
            logger.info("🔄 Принудительное обновление SwitchAudioSource...")
            time.sleep(0.5)  # Даем время системе обновиться
            
            # 1. Получаем список устройств из SwitchAudioSource
            result = subprocess.run([self.switch_audio_path, '-a'],
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                logger.error(f"❌ Ошибка получения списка устройств: {result.stderr}")
                return
            
            device_names = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
            
            # 2. Получаем текущее устройство (с дополнительной задержкой)
            time.sleep(0.3)  # Дополнительная задержка для стабилизации
            current_result = subprocess.run([self.switch_audio_path, '-c'],
                                          capture_output=True, text=True, timeout=5)
            current_device = current_result.stdout.strip() if current_result.returncode == 0 else None
            
            # ИСПРАВЛЕНИЕ: Проверяем, что текущее устройство действительно доступно
            if current_device and current_device not in device_names:
                logger.warning(f"⚠️ Текущее устройство '{current_device}' не найдено в списке доступных")
                logger.info("🔄 Переключаемся на первое доступное устройство...")
                
                # Находим первое подходящее устройство
                real_devices = [name for name in device_names 
                              if not self._is_virtual_device(name) 
                              and 'microphone' not in name.lower()]
                
                if real_devices:
                    current_device = real_devices[0]
                    logger.info(f"🎯 Выбрано новое устройство: {current_device}")
                    
                    # Принудительно переключаемся на новое устройство
                    subprocess.run([self.switch_audio_path, '-s', current_device],
                                 capture_output=True, text=True, timeout=5)
                    subprocess.run([self.switch_audio_path, '-i', current_device],
                                 capture_output=True, text=True, timeout=5)
                    
                    time.sleep(0.5)  # Стабилизация после переключения
                else:
                    logger.error("❌ Нет подходящих устройств для переключения")
                    current_device = None
            
            # 3. Получаем PortAudio устройства
            portaudio_devices = sd.query_devices()
            
            # 4. Очищаем старый кэш
            self._devices_cache.clear()
            
            # 5. Создаем новый кэш
            for device_name in device_names:
                device_info = self._create_device_info(device_name, current_device, portaudio_devices)
                self._devices_cache[device_name] = device_info
            
            self._current_device = current_device
            self._last_update_time = time.time()
            
            logger.info(f"✅ Кэш обновлен: {len(self._devices_cache)} устройств")
            logger.info(f"🎧 Текущее устройство: {current_device}")
            
            # Логируем все устройства
            for name, info in self._devices_cache.items():
                status = "🎧 ТЕКУЩЕЕ" if info.is_default else "  "
                virtual_mark = "🔧 ВИРТУАЛЬНОЕ" if info.device_type == DeviceType.VIRTUAL else ""
                logger.info(f"{status} {name} (тип: {info.device_type.value}, приоритет: {info.priority}) {virtual_mark}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка обновления кэша устройств: {e}")
    
    def _create_device_info(self, device_name: str, current_device: Optional[str], portaudio_devices) -> DeviceInfo:
        """Создает DeviceInfo для устройства"""
        # Определяем тип устройства
        device_type = self._classify_device_type(device_name)
        
        # Определяем приоритет
        priority = self._get_device_priority(device_name, device_type)
        
        # Определяем PortAudio индексы
        output_index, input_index = self._find_portaudio_indices(device_name, portaudio_devices)
        
        # Определяем, является ли устройство текущим
        is_default = (device_name == current_device)
        
        return DeviceInfo(
            name=device_name,
            device_type=device_type,
            priority=priority,
            is_default=is_default,
            portaudio_output_index=output_index,
            portaudio_input_index=input_index,
            is_connected=True
        )
    
    def _classify_device_type(self, device_name: str) -> DeviceType:
        """Классифицирует тип устройства"""
        name_lower = device_name.lower()
        
        # Виртуальные устройства
        if any(keyword in name_lower for keyword in self.virtual_device_keywords):
            return DeviceType.VIRTUAL
        
        # AirPods
        if 'airpods' in name_lower or 'airpods pro' in name_lower:
            return DeviceType.AIRPODS
        
        # Beats
        if 'beats' in name_lower:
            return DeviceType.BEATS
        
        # Bluetooth наушники
        if any(keyword in name_lower for keyword in ['bluetooth', 'wireless', 'bt']):
            if any(keyword in name_lower for keyword in ['headphone', 'earphone', 'bud']):
                return DeviceType.BLUETOOTH_HEADPHONES
        
        # USB наушники
        if 'usb' in name_lower and any(keyword in name_lower for keyword in ['headphone', 'earphone']):
            return DeviceType.USB_HEADPHONES
        
        # Микрофоны
        if 'microphone' in name_lower or 'mic' in name_lower:
            return DeviceType.MICROPHONE
        
        # Динамики (по умолчанию)
        return DeviceType.SPEAKERS
    
    def _get_device_priority(self, device_name: str, device_type: DeviceType) -> int:
        """Получает приоритет устройства"""
        # Виртуальные устройства имеют минимальный приоритет
        if device_type == DeviceType.VIRTUAL:
            return 1
        
        # Используем приоритеты из конфигурации
        type_name = device_type.value
        return self.device_priorities.get(type_name, 50)
    
    def _find_portaudio_indices(self, device_name: str, portaudio_devices) -> Tuple[Optional[int], Optional[int]]:
        """Находит PortAudio индексы для устройства"""
        output_index = None
        input_index = None
        
        for i, dev in enumerate(portaudio_devices):
            name = dev.get('name', 'Unknown')
            if name == device_name:
                if dev.get('max_output_channels', 0) > 0:
                    output_index = i
                if dev.get('max_input_channels', 0) > 0:
                    input_index = i
        
        return output_index, input_index
    
    def _auto_select_best_device(self):
        """Автоматически выбирает лучшее доступное устройство"""
        try:
            available_devices = self.get_available_devices()
            if not available_devices:
                logger.warning("⚠️ Нет доступных устройств")
                return
            
            # Фильтруем устройства
            real_devices = [d for d in available_devices 
                          if not self._is_virtual_device(d.name) 
                          and d.device_type != DeviceType.MICROPHONE
                          and 'microphone' not in d.name.lower()]
            
            if not real_devices:
                logger.warning("⚠️ Нет реальных аудио устройств")
                return
            
            # Находим устройство с наивысшим приоритетом
            best_device = max(real_devices, key=lambda d: d.priority)
            
            if best_device.name != self._current_device:
                logger.info(f"🎯 Автоматический выбор лучшего устройства: {best_device.name}")
                self.switch_to_device(best_device.name)
            else:
                logger.info(f"✅ Уже используется лучшее устройство: {best_device.name}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка автоматического выбора устройства: {e}")
    
    def switch_to_device(self, device_name: str) -> bool:
        """
        Переключается на указанное устройство
        
        Это ЕДИНСТВЕННЫЙ метод переключения устройств в системе!
        """
        try:
            with self._lock:
                logger.info(f"🔄 Переключение на устройство: {device_name}")
                
                # Проверяем, что устройство существует
                if device_name not in self._devices_cache:
                    logger.error(f"❌ Устройство не найдено: {device_name}")
                    return False
                
                device_info = self._devices_cache[device_name]
                
                # 1. Переключаем OUTPUT (динамики)
                result_output = subprocess.run([self.switch_audio_path, '-s', device_name],
                                             capture_output=True, text=True, timeout=10)
                
                if result_output.returncode != 0:
                    logger.error(f"❌ Ошибка переключения OUTPUT: {result_output.stderr}")
                    return False
                
                logger.info(f"✅ OUTPUT переключен на: {device_name}")
                
                # 2. Переключаем INPUT (микрофон)
                result_input = subprocess.run([self.switch_audio_path, '-i', device_name],
                                            capture_output=True, text=True, timeout=10)
                
                if result_input.returncode != 0:
                    # Это нормально для некоторых устройств (например, AirPods)
                    if 'airpods' in device_name.lower():
                        logger.info(f"ℹ️ AirPods не поддерживают INPUT переключение через SwitchAudioSource")
                    else:
                        logger.warning(f"⚠️ Не удалось переключить INPUT: {result_input.stderr}")
                else:
                    logger.info(f"✅ INPUT переключен на: {device_name}")
                
                # 3. Стабилизация системы
                logger.info("⏳ Стабилизация аудио системы...")
                time.sleep(1.5)
                
                # 4. Принудительное обновление PortAudio
                self._refresh_portaudio()
                
                # 5. Дополнительная задержка для полной синхронизации
                time.sleep(0.5)
                
                # 5. Обновляем кэш
                self._force_refresh_devices()
                
                # 6. Уведомляем callbacks
                self._notify_callbacks('device_switched', {
                    'device_name': device_name,
                    'device_info': device_info
                })
                
                logger.info(f"✅ Успешно переключились на: {device_name}")
                return True
                
        except Exception as e:
            logger.error(f"❌ Ошибка переключения устройства: {e}")
            return False
    
    def _refresh_portaudio(self):
        """Принудительно обновляет PortAudio"""
        try:
            logger.info("🔄 Обновление PortAudio...")
            sd._terminate()
            time.sleep(0.5)
            sd._initialize()
            logger.info("✅ PortAudio обновлен")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось обновить PortAudio: {e}")
    
    def handle_device_removed(self, removed_devices: Set[str]):
        """
        Обрабатывает отключение устройств
        
        Это ЕДИНСТВЕННЫЙ метод обработки отключения устройств!
        """
        try:
            with self._lock:
                logger.info(f"🔔 Обработка отключенных устройств: {list(removed_devices)}")
                
                # Проверяем, было ли отключено текущее устройство
                current_removed = False
                for device_name in removed_devices:
                    if device_name == self._current_device:
                        current_removed = True
                        break
                
                if current_removed:
                    logger.info(f"🔄 Текущее устройство отключено: {self._current_device}")
                    
                    # Принудительно обновляем кэш
                    self._force_refresh_devices()
                    
                    # Стабилизация после отключения
                    time.sleep(2.0)
                    
                    # Автоматически выбираем лучшее доступное устройство
                    self._auto_select_best_device()
                
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
        Обрабатывает подключение устройств
        
        Это ЕДИНСТВЕННЫЙ метод обработки подключения устройств!
        """
        try:
            with self._lock:
                logger.info(f"🔔 Обработка подключенных устройств: {list(added_devices)}")
                
                # Принудительно обновляем кэш
                self._force_refresh_devices()
                
                # Проверяем, есть ли высокоприоритетные устройства
                for device_name in added_devices:
                    if device_name in self._devices_cache:
                        device_info = self._devices_cache[device_name]
                        if device_info.priority >= 85:  # Высокий приоритет
                            logger.info(f"🎯 Обнаружено высокоприоритетное устройство: {device_name}")
                            self.switch_to_device(device_name)
                            break
                
                # Уведомляем callbacks
                for device_name in added_devices:
                    self._notify_callbacks('device_added', {
                        'device_name': device_name
                    })
                
                logger.info("✅ Обработка подключения устройств завершена")
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки подключения устройств: {e}")
    
    # === Публичные методы для доступа к данным ===
    
    def get_current_device(self) -> Optional[str]:
        """Получает текущее устройство"""
        return self._current_device
    
    def get_current_device_info(self) -> Optional[DeviceInfo]:
        """Получает информацию о текущем устройстве"""
        if self._current_device and self._current_device in self._devices_cache:
            return self._devices_cache[self._current_device]
        return None
    
    def get_available_devices(self) -> List[DeviceInfo]:
        """Получает список доступных устройств"""
        return list(self._devices_cache.values())
    
    def get_device_info(self, device_name: str) -> Optional[DeviceInfo]:
        """Получает информацию об устройстве"""
        return self._devices_cache.get(device_name)
    
    def _is_virtual_device(self, device_name: str) -> bool:
        """Проверяет, является ли устройство виртуальным"""
        name_lower = device_name.lower()
        return any(keyword in name_lower for keyword in self.virtual_device_keywords)
    
    def add_callback(self, callback: Callable):
        """Добавляет callback для уведомлений"""
        self._callbacks.append(callback)
    
    def _notify_callbacks(self, event_type: str, data: Dict):
        """Уведомляет все callbacks"""
        for callback in self._callbacks:
            try:
                callback(event_type, data)
            except Exception as e:
                logger.error(f"❌ Ошибка в callback: {e}")
    
    def get_portaudio_indices(self) -> Tuple[Optional[int], Optional[int]]:
        """Получает текущие PortAudio индексы"""
        current_info = self.get_current_device_info()
        if current_info:
            return current_info.portaudio_output_index, current_info.portaudio_input_index
        return None, None
    
    def refresh_devices(self):
        """Принудительно обновляет список устройств"""
        with self._lock:
            self._force_refresh_devices()
    
    def is_initialized(self) -> bool:
        """Проверяет, инициализирована ли система"""
        return self._initialized
    
    @property
    def running(self) -> bool:
        """Проверяет, запущена ли система (для совместимости с AudioPlayer)"""
        return self._initialized and (self._realtime_monitor is not None and self._realtime_monitor.is_monitoring())

# Глобальный экземпляр UnifiedAudioSystem
_global_unified_audio_system = None

def get_global_unified_audio_system(config: Optional[Dict] = None) -> UnifiedAudioSystem:
    """Получает глобальный экземпляр UnifiedAudioSystem"""
    global _global_unified_audio_system
    
    if _global_unified_audio_system is None and config:
        _global_unified_audio_system = UnifiedAudioSystem(config)
        _global_unified_audio_system.initialize()
    
    return _global_unified_audio_system

def stop_global_unified_audio_system():
    """Останавливает глобальный экземпляр UnifiedAudioSystem"""
    global _global_unified_audio_system
    _global_unified_audio_system = None
