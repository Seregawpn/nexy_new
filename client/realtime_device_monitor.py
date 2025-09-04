"""
RealtimeDeviceMonitor - Система мониторинга аудио устройств в реальном времени

Эта система отслеживает подключение/отключение устройств в реальном времени
и автоматически переключается на лучшее доступное устройство.
"""

import subprocess
import time
import threading
import logging
from typing import Set, Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import queue

logger = logging.getLogger(__name__)

class DeviceEventType(Enum):
    """Типы событий устройств"""
    DEVICE_ADDED = "device_added"
    DEVICE_REMOVED = "device_removed"
    DEVICE_CHANGED = "device_changed"

@dataclass
class DeviceEvent:
    """Событие изменения устройства"""
    event_type: DeviceEventType
    device_name: str
    timestamp: float
    previous_devices: Set[str]
    current_devices: Set[str]

class RealtimeDeviceMonitor:
    """
    Мониторинг аудио устройств в реальном времени
    
    Принципы:
    1. Непрерывный мониторинг изменений устройств
    2. Автоматическое переключение на лучшее устройство
    3. Обработка событий в реальном времени
    4. Надежная обработка ошибок
    """
    
    def __init__(self, switch_audio_path: str = '/opt/homebrew/bin/SwitchAudioSource'):
        self.switch_audio_path = switch_audio_path
        self.monitoring = False
        self.monitor_thread = None
        self.monitor_interval = 1.0  # Проверяем каждую секунду
        
        # Кэш устройств для сравнения
        self._previous_devices: Set[str] = set()
        self._current_devices: Set[str] = set()
        
        # Callbacks для уведомлений
        self._callbacks: List[Callable] = []
        
        # Очередь событий для обработки
        self._event_queue = queue.Queue()
        
        # Блокировка для thread-safe операций
        self._lock = threading.RLock()
        
        logger.info("🎵 RealtimeDeviceMonitor инициализирован")
    
    def start_monitoring(self):
        """Запускает мониторинг в реальном времени"""
        try:
            with self._lock:
                if self.monitoring:
                    logger.info("♻️ Мониторинг уже запущен")
                    return
                
                logger.info("🔄 Запуск мониторинга устройств в реальном времени...")
                
                # Получаем начальный список устройств
                self._current_devices = self._get_current_devices()
                self._previous_devices = self._current_devices.copy()
                
                logger.info(f"📱 Начальный список устройств: {len(self._current_devices)} устройств")
                for device in self._current_devices:
                    logger.info(f"  📱 {device}")
                
                # Запускаем поток мониторинга
                self.monitoring = True
                self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
                self.monitor_thread.start()
                
                # Запускаем поток обработки событий
                self.event_thread = threading.Thread(target=self._event_processor_loop, daemon=True)
                self.event_thread.start()
                
                logger.info("✅ Мониторинг устройств запущен")
                
        except Exception as e:
            logger.error(f"❌ Ошибка запуска мониторинга: {e}")
    
    def stop_monitoring(self):
        """Останавливает мониторинг"""
        try:
            with self._lock:
                if not self.monitoring:
                    logger.info("♻️ Мониторинг уже остановлен")
                    return
                
                logger.info("🔄 Остановка мониторинга устройств...")
                
                self.monitoring = False
                
                if self.monitor_thread and self.monitor_thread.is_alive():
                    self.monitor_thread.join(timeout=2.0)
                
                if hasattr(self, 'event_thread') and self.event_thread.is_alive():
                    self.event_thread.join(timeout=2.0)
                
                logger.info("✅ Мониторинг устройств остановлен")
                
        except Exception as e:
            logger.error(f"❌ Ошибка остановки мониторинга: {e}")
    
    def _monitor_loop(self):
        """Основной цикл мониторинга"""
        logger.info("🔄 Запуск цикла мониторинга...")
        
        while self.monitoring:
            try:
                # Получаем текущий список устройств
                current_devices = self._get_current_devices()
                
                # Сравниваем с предыдущим списком
                if current_devices != self._previous_devices:
                    logger.info("🔔 Обнаружены изменения в устройствах!")
                    
                    # Определяем добавленные устройства
                    added_devices = current_devices - self._previous_devices
                    removed_devices = self._previous_devices - current_devices
                    
                    # Создаем события
                    if added_devices:
                        event = DeviceEvent(
                            event_type=DeviceEventType.DEVICE_ADDED,
                            device_name=list(added_devices)[0],  # Берем первое добавленное
                            timestamp=time.time(),
                            previous_devices=self._previous_devices.copy(),
                            current_devices=current_devices.copy()
                        )
                        self._event_queue.put(event)
                        logger.info(f"➕ Добавлено устройство: {added_devices}")
                    
                    if removed_devices:
                        event = DeviceEvent(
                            event_type=DeviceEventType.DEVICE_REMOVED,
                            device_name=list(removed_devices)[0],  # Берем первое удаленное
                            timestamp=time.time(),
                            previous_devices=self._previous_devices.copy(),
                            current_devices=current_devices.copy()
                        )
                        self._event_queue.put(event)
                        logger.info(f"➖ Удалено устройство: {removed_devices}")
                    
                    # Обновляем кэш
                    self._previous_devices = current_devices.copy()
                    self._current_devices = current_devices
                
                # Ждем перед следующей проверкой
                time.sleep(self.monitor_interval)
                
            except Exception as e:
                logger.error(f"❌ Ошибка в цикле мониторинга: {e}")
                time.sleep(self.monitor_interval)
    
    def _event_processor_loop(self):
        """Цикл обработки событий"""
        logger.info("🔄 Запуск обработчика событий...")
        
        while self.monitoring:
            try:
                # Получаем событие из очереди
                event = self._event_queue.get(timeout=1.0)
                
                # Обрабатываем событие
                self._process_device_event(event)
                
                # Помечаем задачу как выполненную
                self._event_queue.task_done()
                
            except queue.Empty:
                # Нет событий, продолжаем
                continue
            except Exception as e:
                logger.error(f"❌ Ошибка обработки события: {e}")
    
    def _process_device_event(self, event: DeviceEvent):
        """Обрабатывает событие изменения устройства"""
        try:
            logger.info(f"🔔 Обработка события: {event.event_type.value} - {event.device_name}")
            
            if event.event_type == DeviceEventType.DEVICE_ADDED:
                self._handle_device_added(event)
            elif event.event_type == DeviceEventType.DEVICE_REMOVED:
                self._handle_device_removed(event)
            
            # Уведомляем callbacks
            self._notify_callbacks(event)
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки события устройства: {e}")
    
    def _handle_device_added(self, event: DeviceEvent):
        """Обрабатывает добавление устройства"""
        try:
            logger.info(f"➕ Обработка добавления устройства: {event.device_name}")
            
            # Проверяем, является ли устройство высокоприоритетным
            if self._is_high_priority_device(event.device_name):
                logger.info(f"🎯 Обнаружено высокоприоритетное устройство: {event.device_name}")
                
                # Переключаемся на новое устройство
                success = self._switch_to_device(event.device_name)
                if success:
                    logger.info(f"✅ Успешно переключились на: {event.device_name}")
                else:
                    logger.error(f"❌ Не удалось переключиться на: {event.device_name}")
            else:
                logger.info(f"ℹ️ Устройство {event.device_name} имеет низкий приоритет, не переключаемся")
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки добавления устройства: {e}")
    
    def _handle_device_removed(self, event: DeviceEvent):
        """Обрабатывает удаление устройства"""
        try:
            logger.info(f"➖ Обработка удаления устройства: {event.device_name}")
            
            # Получаем текущее устройство
            current_device = self._get_current_device()
            
            if current_device == event.device_name:
                logger.info(f"🔄 Текущее устройство отключено: {event.device_name}")
                
                # Находим лучшее доступное устройство
                best_device = self._find_best_available_device(event.current_devices)
                
                if best_device:
                    logger.info(f"🎯 Переключаемся на лучшее доступное устройство: {best_device}")
                    success = self._switch_to_device(best_device)
                    if success:
                        logger.info(f"✅ Успешно переключились на: {best_device}")
                    else:
                        logger.error(f"❌ Не удалось переключиться на: {best_device}")
                else:
                    logger.warning("⚠️ Нет доступных устройств для переключения")
            else:
                logger.info(f"ℹ️ Отключенное устройство {event.device_name} не было текущим")
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки удаления устройства: {e}")
    
    def _get_current_devices(self) -> Set[str]:
        """Получает текущий список устройств"""
        try:
            result = subprocess.run([self.switch_audio_path, '-a'],
                                  capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                devices = {line.strip() for line in result.stdout.strip().split('\n') if line.strip()}
                return devices
            else:
                logger.error(f"❌ Ошибка получения списка устройств: {result.stderr}")
                return set()
                
        except Exception as e:
            logger.error(f"❌ Ошибка выполнения SwitchAudioSource: {e}")
            return set()
    
    def _get_current_device(self) -> Optional[str]:
        """Получает текущее устройство"""
        try:
            result = subprocess.run([self.switch_audio_path, '-c'],
                                  capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                logger.error(f"❌ Ошибка получения текущего устройства: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Ошибка выполнения SwitchAudioSource: {e}")
            return None
    
    def _is_high_priority_device(self, device_name: str) -> bool:
        """Проверяет, является ли устройство высокоприоритетным"""
        name_lower = device_name.lower()
        
        # Высокоприоритетные устройства
        high_priority_keywords = [
            'airpods', 'beats', 'bluetooth', 'wireless', 'bt'
        ]
        
        return any(keyword in name_lower for keyword in high_priority_keywords)
    
    def _find_best_available_device(self, available_devices: Set[str]) -> Optional[str]:
        """Находит лучшее доступное устройство"""
        try:
            # Исключаем виртуальные устройства и микрофоны
            real_devices = [name for name in available_devices 
                          if not self._is_virtual_device(name) 
                          and 'microphone' not in name.lower()]
            
            if not real_devices:
                logger.warning("⚠️ Нет реальных аудио устройств")
                return None
            
            # Приоритеты устройств
            device_priorities = {
                'airpods': 95,
                'beats': 90,
                'bluetooth': 85,
                'wireless': 85,
                'bt': 85,
                'usb': 80,
                'speakers': 70
            }
            
            # Находим устройство с наивысшим приоритетом
            best_device = None
            best_priority = 0
            
            for device in real_devices:
                device_lower = device.lower()
                priority = 50  # Приоритет по умолчанию
                
                for keyword, device_priority in device_priorities.items():
                    if keyword in device_lower:
                        priority = device_priority
                        break
                
                if priority > best_priority:
                    best_priority = priority
                    best_device = device
            
            return best_device
            
        except Exception as e:
            logger.error(f"❌ Ошибка поиска лучшего устройства: {e}")
            return None
    
    def _is_virtual_device(self, device_name: str) -> bool:
        """Проверяет, является ли устройство виртуальным"""
        name_lower = device_name.lower()
        virtual_keywords = ['blackhole', 'loopback', 'virtual']
        return any(keyword in name_lower for keyword in virtual_keywords)
    
    def _switch_to_device(self, device_name: str) -> bool:
        """Переключается на указанное устройство"""
        try:
            logger.info(f"🔄 Переключение на устройство: {device_name}")
            
            # Переключаем OUTPUT
            result_output = subprocess.run([self.switch_audio_path, '-s', device_name],
                                         capture_output=True, text=True, timeout=5)
            
            if result_output.returncode != 0:
                logger.error(f"❌ Ошибка переключения OUTPUT: {result_output.stderr}")
                return False
            
            # Переключаем INPUT (только если устройство поддерживает)
            result_input = subprocess.run([self.switch_audio_path, '-i', device_name],
                                        capture_output=True, text=True, timeout=5)
            
            if result_input.returncode != 0:
                # Это нормально для некоторых устройств (например, AirPods)
                if 'airpods' in device_name.lower():
                    logger.info(f"ℹ️ AirPods не поддерживают INPUT переключение через SwitchAudioSource")
                else:
                    logger.warning(f"⚠️ Не удалось переключить INPUT: {result_input.stderr}")
            else:
                logger.info(f"✅ INPUT переключен на: {device_name}")
            
            # Стабилизация
            time.sleep(1.0)
            
            logger.info(f"✅ Успешно переключились на: {device_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка переключения устройства: {e}")
            return False
    
    def add_callback(self, callback: Callable):
        """Добавляет callback для уведомлений"""
        self._callbacks.append(callback)
    
    def _notify_callbacks(self, event: DeviceEvent):
        """Уведомляет все callbacks"""
        for callback in self._callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"❌ Ошибка в callback: {e}")
    
    def get_current_devices(self) -> Set[str]:
        """Получает текущий список устройств"""
        return self._current_devices.copy()
    
    def is_monitoring(self) -> bool:
        """Проверяет, запущен ли мониторинг"""
        return self.monitoring

# Глобальный экземпляр RealtimeDeviceMonitor
_global_realtime_monitor = None

def get_global_realtime_monitor() -> RealtimeDeviceMonitor:
    """Получает глобальный экземпляр RealtimeDeviceMonitor"""
    global _global_realtime_monitor
    
    if _global_realtime_monitor is None:
        _global_realtime_monitor = RealtimeDeviceMonitor()
    
    return _global_realtime_monitor

def stop_global_realtime_monitor():
    """Останавливает глобальный экземпляр RealtimeDeviceMonitor"""
    global _global_realtime_monitor
    
    if _global_realtime_monitor:
        _global_realtime_monitor.stop_monitoring()
        _global_realtime_monitor = None
