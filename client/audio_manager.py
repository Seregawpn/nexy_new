#!/usr/bin/env python3
"""
AudioManagerDaemon - Централизованный менеджер аудио устройств
Автоматически отслеживает и переключает аудио устройства с использованием SwitchAudioSource
"""

import subprocess
import threading
import time
import logging
import queue
from typing import List, Dict, Optional, Callable, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class DeviceType(Enum):
    """Типы аудио устройств"""
    AIRPODS = "airpods"
    BEATS = "beats"
    BLUETOOTH_HEADPHONES = "bluetooth_headphones"
    USB_HEADPHONES = "usb_headphones"
    BLUETOOTH_SPEAKERS = "bluetooth_speakers"
    USB_AUDIO = "usb_audio"
    SYSTEM_SPEAKERS = "system_speakers"
    VIRTUAL_DEVICE = "virtual_device"
    BUILT_IN = "built_in"
    MICROPHONE = "microphone"
    OTHER = "other"

@dataclass
class DeviceInfo:
    """Информация об аудио устройстве"""
    name: str
    index: int
    device_type: DeviceType
    priority: int
    is_available: bool = True
    is_default: bool = False
    max_channels: int = 0
    default_samplerate: int = 0
    max_samplerate: int = 0

class DeviceInfoManager:
    """Менеджер информации об аудио устройствах"""
    
    def __init__(self):
        self.switch_audio_path = self._find_switch_audio_source()
        self.device_cache = {}
        self.cache_timeout = 5.0  # секунды
        self.last_cache_update = 0
        
        # Черный список виртуальных устройств
        self.virtual_device_keywords = [
            'blackhole', 'soundflower', 'loopback', 'virtual', 
            'aggregate', 'multi-output', 'sound source', 'audio hijack'
        ]
        
    def _find_switch_audio_source(self) -> str:
        """Находит путь к SwitchAudioSource"""
        try:
            # Проверяем стандартные пути
            paths = [
                '/usr/local/bin/SwitchAudioSource',
                '/opt/homebrew/bin/SwitchAudioSource',
                '/usr/bin/SwitchAudioSource'
            ]
            
            for path in paths:
                try:
                    result = subprocess.run([path, '-a'], 
                                          capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        logger.info(f"✅ SwitchAudioSource найден: {path}")
                        return path
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    continue
            
            # Пробуем найти через which
            try:
                result = subprocess.run(['which', 'SwitchAudioSource'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    path = result.stdout.strip()
                    logger.info(f"✅ SwitchAudioSource найден через which: {path}")
                    return path
            except subprocess.TimeoutExpired:
                pass
            
            raise FileNotFoundError("SwitchAudioSource не найден")
            
        except Exception as e:
            logger.error(f"❌ Ошибка поиска SwitchAudioSource: {e}")
            raise
    
    def get_all_devices(self) -> List[str]:
        """Получает список всех аудио устройств"""
        try:
            result = subprocess.run([self.switch_audio_path, '-a'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                devices = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
                logger.debug(f"📱 Получено {len(devices)} устройств")
                return devices
            else:
                logger.error(f"❌ Ошибка получения устройств: {result.stderr}")
                return []
        except Exception as e:
            logger.error(f"❌ Ошибка выполнения SwitchAudioSource: {e}")
            return []
    
    def get_current_device(self) -> Optional[str]:
        """Получает текущее аудио устройство"""
        try:
            result = subprocess.run([self.switch_audio_path, '-c'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                device = result.stdout.strip()
                logger.debug(f"🎧 Текущее устройство: {device}")
                return device
            else:
                logger.error(f"❌ Ошибка получения текущего устройства: {result.stderr}")
                return None
        except Exception as e:
            logger.error(f"❌ Ошибка выполнения SwitchAudioSource: {e}")
            return None
    
    def is_virtual_device(self, device_name: str) -> bool:
        """Проверяет, является ли устройство виртуальным"""
        name_lower = device_name.lower()
        return any(keyword in name_lower for keyword in self.virtual_device_keywords)
    
    def _classify_device_type(self, device_name: str) -> Tuple[DeviceType, int]:
        """Классифицирует устройство по типу и возвращает приоритет"""
        name_lower = device_name.lower()
        
        # ИСПРАВЛЕНИЕ: Виртуальные устройства получают минимальный приоритет
        if self.is_virtual_device(device_name):
            return DeviceType.VIRTUAL_DEVICE, 1  # Минимальный приоритет!
        
        # Система приоритетов (чем выше число, тем выше приоритет)
        if 'airpods' in name_lower:
            return DeviceType.AIRPODS, 100
        elif 'beats' in name_lower:
            return DeviceType.BEATS, 95
        elif any(tag in name_lower for tag in ['bluetooth', 'wireless']) and any(tag in name_lower for tag in ['headphone', 'earbud', 'earphone']):
            return DeviceType.BLUETOOTH_HEADPHONES, 90
        elif 'usb' in name_lower and any(tag in name_lower for tag in ['headphone', 'earbud', 'earphone']):
            return DeviceType.USB_HEADPHONES, 85
        elif any(tag in name_lower for tag in ['bluetooth', 'wireless']) and any(tag in name_lower for tag in ['speaker', 'sound']):
            return DeviceType.BLUETOOTH_SPEAKERS, 70
        elif 'usb' in name_lower:
            return DeviceType.USB_AUDIO, 60
        elif any(tag in name_lower for tag in ['macbook', 'built-in', 'internal', 'speaker']):
            return DeviceType.SYSTEM_SPEAKERS, 40
        elif any(tag in name_lower for tag in ['microphone', 'mic']):
            return DeviceType.MICROPHONE, 5
        else:
            return DeviceType.OTHER, 10
    
    def get_device_info(self, device_name: str) -> DeviceInfo:
        """Получает подробную информацию об устройстве"""
        device_type, priority = self._classify_device_type(device_name)
        
        return DeviceInfo(
            name=device_name,
            index=-1,  # SwitchAudioSource не предоставляет индексы
            device_type=device_type,
            priority=priority,
            is_available=True,
            is_default=False
        )
    
    def get_available_devices_info(self) -> List[DeviceInfo]:
        """Получает информацию о всех доступных устройствах"""
        current_time = time.time()
        
        # Проверяем кэш
        if (current_time - self.last_cache_update) < self.cache_timeout and self.device_cache:
            return list(self.device_cache.values())
        
        # Обновляем кэш
        devices = self.get_all_devices()
        current_device = self.get_current_device()
        
        device_info_list = []
        for device_name in devices:
            device_info = self.get_device_info(device_name)
            device_info.is_default = (device_name == current_device)
            device_info_list.append(device_info)
            self.device_cache[device_name] = device_info
        
        self.last_cache_update = current_time
        return device_info_list
    
    def _update_device_list(self):
        """Принудительно обновляет список устройств"""
        try:
            logger.info(f"🔄 Принудительное обновление списка устройств...")
            
            # Получаем свежий список устройств
            result = subprocess.run([self.switch_audio_path, '-a'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                # Парсим новый список
                new_devices = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
                
                # Очищаем кэш
                self.device_cache.clear()
                
                logger.info(f"✅ Список устройств обновлен: {len(new_devices)} устройств")
                
                # Логируем изменения
                for device_name in new_devices:
                    device_info = self.get_device_info(device_name)
                    logger.info(f"   📱 {device_name} (тип: {device_info.device_type.value}, приоритет: {device_info.priority})")
            else:
                logger.error(f"❌ Ошибка обновления списка устройств: {result.stderr}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка при обновлении списка устройств: {e}")

class AudioDeviceController:
    """Контроллер для управления аудио устройствами"""
    
    def __init__(self, device_manager: DeviceInfoManager):
        self.device_manager = device_manager
        self.switch_cooldown = 2.0  # секунды между переключениями
        self.last_switch_time = 0
        
    def switch_to_device(self, device_name: str) -> bool:
        """Переключается на указанное устройство"""
        try:
            current_time = time.time()
            if current_time - self.last_switch_time < self.switch_cooldown:
                logger.info(f"⏱️ Слишком частое переключение, пропускаю")
                return False
            
            logger.info(f"🔄 Переключение на устройство: {device_name}")
            
            # ИСПРАВЛЕНИЕ: Переключаем и OUTPUT и INPUT устройства
            # 1. Переключаем OUTPUT (динамики)
            result_output = subprocess.run([self.device_manager.switch_audio_path, '-s', device_name], 
                                         capture_output=True, text=True, timeout=10)
            
            # 2. Переключаем INPUT (микрофон) - ищем устройство с таким же именем
            result_input = subprocess.run([self.device_manager.switch_audio_path, '-i', device_name], 
                                        capture_output=True, text=True, timeout=10)
            
            if result_output.returncode == 0:
                self.last_switch_time = current_time
                logger.info(f"✅ Успешно переключились на OUTPUT: {device_name}")
                
                if result_input.returncode == 0:
                    logger.info(f"✅ Успешно переключились на INPUT: {device_name}")
                else:
                    logger.warning(f"⚠️ Не удалось переключить INPUT на {device_name}: {result_input.stderr}")
                
                # ИСПРАВЛЕНИЕ: Добавляем задержку для стабилизации системы
                logger.info(f"⏳ Ожидание стабилизации аудио системы...")
                time.sleep(1.5)  # 1.5 секунды для стабилизации
                
                # ИСПРАВЛЕНИЕ: Принудительно обновляем PortAudio после переключения
                logger.info(f"🔄 Принудительное обновление PortAudio после переключения...")
                try:
                    import sounddevice as sd
                    # Принудительно обновляем PortAudio
                    sd._terminate()
                    time.sleep(0.5)
                    sd._initialize()
                    logger.info(f"✅ PortAudio обновлен после переключения")
                except Exception as pa_e:
                    logger.warning(f"⚠️ Не удалось обновить PortAudio: {pa_e}")
                
                # Проверяем, что переключение действительно произошло
                current_device = self.device_manager.get_current_device()
                if current_device == device_name:
                    logger.info(f"✅ Подтверждено: текущее устройство {current_device}")
                else:
                    logger.warning(f"⚠️ Ожидали {device_name}, но текущее устройство: {current_device}")
                
                return True
            else:
                logger.error(f"❌ Ошибка переключения OUTPUT на {device_name}: {result_output.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка переключения устройства: {e}")
            return False
    
    def auto_switch_to_best_device(self) -> bool:
        """Автоматически переключается на лучшее доступное устройство"""
        try:
            devices = self.device_manager.get_available_devices_info()
            if not devices:
                logger.warning("⚠️ Нет доступных устройств")
                return False
            
            # ИСПРАВЛЕНИЕ: Исключаем виртуальные устройства и микрофоны из автоматического выбора
            # Предпочитаем устройства вывода (динамики) над устройствами ввода (микрофоны)
            real_devices = [d for d in devices 
                          if not self.device_manager.is_virtual_device(d.name) 
                          and d.device_type != DeviceType.MICROPHONE
                          and 'microphone' not in d.name.lower()]
            
            if not real_devices:
                logger.warning("⚠️ Нет реальных аудио устройств (только виртуальные)")
                # В крайнем случае - находим устройство с наивысшим приоритетом среди всех
                best_device = max(devices, key=lambda d: d.priority)
                if self.device_manager.is_virtual_device(best_device.name):
                    logger.warning(f"⚠️ Переключаемся на виртуальное устройство в крайнем случае: {best_device.name}")
                return self.switch_to_device(best_device.name)
            
            # Находим устройство с наивысшим приоритетом среди реальных устройств
            best_device = max(real_devices, key=lambda d: d.priority)
            current_device = self.device_manager.get_current_device()
            
            if best_device.name == current_device:
                logger.info(f"✅ Уже используется лучшее устройство: {best_device.name}")
                return True
            
            logger.info(f"🎯 Автоматическое переключение на лучшее устройство: {best_device.name} (приоритет: {best_device.priority})")
            return self.switch_to_device(best_device.name)
            
        except Exception as e:
            logger.error(f"❌ Ошибка автоматического переключения: {e}")
            return False
    
    def switch_to_headphones(self) -> bool:
        """Переключается на наушники если они доступны"""
        try:
            devices = self.device_manager.get_available_devices_info()
            headphones = [d for d in devices if d.device_type in [
                DeviceType.AIRPODS, DeviceType.BEATS, 
                DeviceType.BLUETOOTH_HEADPHONES, DeviceType.USB_HEADPHONES
            ]]
            
            if not headphones:
                logger.info("🎧 Наушники не найдены")
                return False
            
            # Выбираем наушники с наивысшим приоритетом
            best_headphones = max(headphones, key=lambda d: d.priority)
            logger.info(f"🎧 Переключение на наушники: {best_headphones.name}")
            return self.switch_to_device(best_headphones.name)
            
        except Exception as e:
            logger.error(f"❌ Ошибка переключения на наушники: {e}")
            return False

class DeviceMonitor:
    """Монитор изменений аудио устройств"""
    
    def __init__(self, device_manager: DeviceInfoManager, controller: AudioDeviceController):
        self.device_manager = device_manager
        self.controller = controller
        self.monitoring = False
        self.monitor_thread = None
        self.monitoring_interval = 3.0  # секунды
        self.callbacks = []
        self.last_device_state = set()
        
    def add_callback(self, callback: Callable[[str, Dict], None]):
        """Добавляет callback для уведомлений об изменениях"""
        self.callbacks.append(callback)
    
    def start_monitoring(self):
        """Запускает мониторинг устройств"""
        if self.monitoring:
            logger.info("🔄 Мониторинг уже запущен")
            return
        
        logger.info("🔄 Запуск мониторинга аудио устройств...")
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("✅ Мониторинг аудио устройств запущен")
    
    def stop_monitoring(self):
        """Останавливает мониторинг устройств"""
        if not self.monitoring:
            return
        
        logger.info("🔄 Остановка мониторинга аудио устройств...")
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2.0)
        logger.info("✅ Мониторинг аудио устройств остановлен")
    
    def _monitor_loop(self):
        """Основной цикл мониторинга"""
        logger.info("🔄 Цикл мониторинга запущен")
        
        # Инициализируем начальное состояние
        self._check_device_changes()
        
        while self.monitoring:
            try:
                time.sleep(self.monitoring_interval)
                if self.monitoring:  # Проверяем еще раз после сна
                    self._check_device_changes()
            except Exception as e:
                logger.error(f"❌ Ошибка в цикле мониторинга: {e}")
                time.sleep(1.0)  # Короткая пауза при ошибке
        
        logger.info("🔄 Цикл мониторинга завершен")
    
    def _check_device_changes(self):
        """Проверяет изменения в списке устройств"""
        try:
            current_devices = set(self.device_manager.get_all_devices())
            
            if not self.last_device_state:
                # Первый запуск - просто сохраняем состояние
                self.last_device_state = current_devices
                return
            
            # Находим изменения
            added_devices = current_devices - self.last_device_state
            removed_devices = self.last_device_state - current_devices
            
            if added_devices:
                logger.info(f"🔔 Новые устройства: {list(added_devices)}")
                self._handle_device_added(added_devices)
            
            if removed_devices:
                logger.info(f"🔔 Удаленные устройства: {list(removed_devices)}")
                self._handle_device_removed(removed_devices)
            
            # Обновляем состояние
            self.last_device_state = current_devices
            
        except Exception as e:
            logger.error(f"❌ Ошибка проверки изменений устройств: {e}")
    
    def _handle_device_added(self, added_devices: set):
        """Обрабатывает добавление новых устройств"""
        for device_name in added_devices:
            device_info = self.device_manager.get_device_info(device_name)
            
            # ИСПРАВЛЕНИЕ: Принудительно обновляем список устройств
            logger.info(f"🔄 Обновляем список устройств после подключения...")
            self.device_manager._update_device_list()
            
            # ИСПРАВЛЕНИЕ: Не переключаемся автоматически на виртуальные устройства!
            if (not self.device_manager.is_virtual_device(device_name) 
                and device_info.priority >= 85):  # AirPods, Beats, Bluetooth наушники
                logger.info(f"🎧 Обнаружены высокоприоритетные наушники: {device_name}")
                
                # Проверяем, не является ли это уже текущим устройством
                current_device = self.device_manager.get_current_device()
                if current_device != device_name:
                    logger.info(f"🔄 Переключение на новое устройство: {device_name}")
                    self.controller.switch_to_device(device_name)
                else:
                    logger.info(f"ℹ️ Устройство {device_name} уже является текущим")
                    # Даже если устройство уже текущее, принудительно переключаемся для обновления
                    logger.info(f"🔄 Принудительное переключение для обновления состояния")
                    self.controller.switch_to_device(device_name)
            
            # Уведомляем callback'и
            for callback in self.callbacks:
                try:
                    callback('device_added', {
                        'name': device_name,
                        'type': device_info.device_type.value,
                        'priority': device_info.priority
                    })
                except Exception as e:
                    logger.error(f"❌ Ошибка в callback: {e}")
    
    def _handle_device_removed(self, removed_devices: set):
        """Обрабатывает удаление устройств"""
        for device_name in removed_devices:
            device_info = self.device_manager.get_device_info(device_name)
            
            # Если удалили текущее устройство - переключаемся на лучшее доступное
            current_device = self.device_manager.get_current_device()
            if device_name == current_device:
                logger.info(f"🔄 Текущее устройство удалено: {device_name}")
                
                # ИСПРАВЛЕНИЕ: Принудительно обновляем список устройств
                logger.info(f"🔄 Обновляем список устройств после отключения...")
                self.device_manager._update_device_list()
                
                # ИСПРАВЛЕНИЕ: Добавляем стабилизацию после отключения устройства
                logger.info(f"⏳ Стабилизация аудио системы после отключения устройства...")
                time.sleep(2.0)  # 2 секунды для стабилизации после отключения
                
                self.controller.auto_switch_to_best_device()
            
            # Уведомляем callback'и
            for callback in self.callbacks:
                try:
                    callback('device_removed', {
                        'name': device_name,
                        'type': device_info.device_type.value,
                        'priority': device_info.priority
                    })
                except Exception as e:
                    logger.error(f"❌ Ошибка в callback: {e}")

class AudioManagerDaemon:
    """Главный класс для управления аудио устройствами"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.running = False
        
        # Инициализируем компоненты
        try:
            self.device_manager = DeviceInfoManager()
            self.controller = AudioDeviceController(self.device_manager)
            self.monitor = DeviceMonitor(self.device_manager, self.controller)
            
            # Настраиваем параметры из конфигурации
            self._apply_config()
            
            logger.info("✅ AudioManagerDaemon инициализирован")
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации AudioManagerDaemon: {e}")
            raise
    
    def _apply_config(self):
        """Применяет конфигурацию"""
        # Интервал мониторинга
        if 'monitoring_interval' in self.config:
            self.monitor.monitoring_interval = float(self.config['monitoring_interval'])
        
        # Cooldown переключений
        if 'switch_cooldown' in self.config:
            self.controller.switch_cooldown = float(self.config['switch_cooldown'])
        
        # Время кэширования
        if 'cache_timeout' in self.config:
            self.device_manager.cache_timeout = float(self.config['cache_timeout'])
    
    def start(self, daemon_mode: bool = True):
        """Запускает менеджер аудио устройств"""
        if self.running:
            logger.info("🔄 AudioManagerDaemon уже запущен")
            return
        
        logger.info("🚀 Запуск AudioManagerDaemon...")
        
        try:
            # Запускаем мониторинг
            self.monitor.start_monitoring()
            
            # Автоматически переключаемся на лучшее устройство при старте
            self.controller.auto_switch_to_best_device()
            
            self.running = True
            logger.info("✅ AudioManagerDaemon запущен")
            
            if not daemon_mode:
                # Если не daemon режим - ждем завершения
                try:
                    while self.running:
                        time.sleep(1.0)
                except KeyboardInterrupt:
                    logger.info("🛑 Получен сигнал остановки")
                    self.stop()
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска AudioManagerDaemon: {e}")
            self.stop()
            raise
    
    def stop(self):
        """Останавливает менеджер аудио устройств"""
        if not self.running:
            return
        
        logger.info("🛑 Остановка AudioManagerDaemon...")
        
        try:
            self.running = False
            self.monitor.stop_monitoring()
            logger.info("✅ AudioManagerDaemon остановлен")
            
        except Exception as e:
            logger.error(f"❌ Ошибка остановки AudioManagerDaemon: {e}")
    
    def add_device_callback(self, callback: Callable[[str, Dict], None]):
        """Добавляет callback для уведомлений об изменениях устройств"""
        self.monitor.add_callback(callback)
    
    def switch_to_device(self, device_name: str) -> bool:
        """Переключается на указанное устройство"""
        return self.controller.switch_to_device(device_name)
    
    def switch_to_headphones(self) -> bool:
        """Переключается на наушники"""
        return self.controller.switch_to_headphones()
    
    def auto_switch_to_best(self) -> bool:
        """Автоматически переключается на лучшее устройство"""
        return self.controller.auto_switch_to_best_device()
    
    def get_current_device(self) -> Optional[str]:
        """Получает текущее аудио устройство"""
        return self.device_manager.get_current_device()
    
    def get_available_devices(self) -> List[DeviceInfo]:
        """Получает список доступных устройств"""
        return self.device_manager.get_available_devices_info()
    
    def get_device_info(self, device_name: str) -> DeviceInfo:
        """Получает информацию об устройстве"""
        return self.device_manager.get_device_info(device_name)

def main():
    """Основная функция для тестирования"""
    import argparse
    
    parser = argparse.ArgumentParser(description='AudioManagerDaemon - Менеджер аудио устройств')
    parser.add_argument('--daemon', action='store_true', help='Запуск в daemon режиме')
    parser.add_argument('--list', action='store_true', help='Показать список устройств')
    parser.add_argument('--current', action='store_true', help='Показать текущее устройство')
    parser.add_argument('--switch', type=str, help='Переключиться на устройство')
    parser.add_argument('--auto', action='store_true', help='Автоматически переключиться на лучшее устройство')
    parser.add_argument('--headphones', action='store_true', help='Переключиться на наушники')
    
    args = parser.parse_args()
    
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Создаем менеджер
        config = {
            'monitoring_interval': 3.0,
            'switch_cooldown': 2.0,
            'cache_timeout': 5.0
        }
        
        manager = AudioManagerDaemon(config)
        
        if args.list:
            devices = manager.get_available_devices()
            print("📱 Доступные аудио устройства:")
            for device in devices:
                status = "🎧 ТЕКУЩЕЕ" if device.is_default else "  "
                virtual_mark = "🔧 ВИРТУАЛЬНОЕ" if manager.device_manager.is_virtual_device(device.name) else ""
                print(f"{status} {device.name} (тип: {device.device_type.value}, приоритет: {device.priority}) {virtual_mark}")
        
        elif args.current:
            current = manager.get_current_device()
            if current:
                print(f"🎧 Текущее устройство: {current}")
            else:
                print("❌ Не удалось определить текущее устройство")
        
        elif args.switch:
            success = manager.switch_to_device(args.switch)
            if success:
                print(f"✅ Переключились на: {args.switch}")
            else:
                print(f"❌ Не удалось переключиться на: {args.switch}")
        
        elif args.auto:
            success = manager.auto_switch_to_best()
            if success:
                print("✅ Автоматически переключились на лучшее устройство")
            else:
                print("❌ Не удалось автоматически переключиться")
        
        elif args.headphones:
            success = manager.switch_to_headphones()
            if success:
                print("✅ Переключились на наушники")
            else:
                print("❌ Наушники не найдены")
        
        else:
            # Запускаем в daemon режиме
            manager.start(daemon_mode=args.daemon)
    
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        return 1
    
    return 0

# Глобальный экземпляр AudioManagerDaemon для избежания дублирования
_global_audio_manager = None

def get_global_audio_manager(config: Optional[Dict] = None) -> AudioManagerDaemon:
    """Получает глобальный экземпляр AudioManagerDaemon"""
    global _global_audio_manager
    
    if _global_audio_manager is None:
        logger.info("🔄 Создание глобального экземпляра AudioManagerDaemon...")
        _global_audio_manager = AudioManagerDaemon(config)
        logger.info("✅ Глобальный AudioManagerDaemon создан")
    else:
        logger.info("♻️ Используем существующий глобальный AudioManagerDaemon")
    
    return _global_audio_manager

def stop_global_audio_manager():
    """Останавливает глобальный экземпляр AudioManagerDaemon"""
    global _global_audio_manager
    
    if _global_audio_manager is not None:
        logger.info("🛑 Остановка глобального AudioManagerDaemon...")
        _global_audio_manager.stop()
        _global_audio_manager = None
        logger.info("✅ Глобальный AudioManagerDaemon остановлен")

if __name__ == "__main__":
    exit(main())
