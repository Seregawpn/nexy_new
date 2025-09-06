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
from utils.device_utils import is_virtual_device
import queue
from audio_device_manager import get_global_audio_device_manager

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
                
                # Используем централизованный AudioDeviceManager
                audio_manager = get_global_audio_device_manager()
                if audio_manager:
                    success = audio_manager.switch_to_device(event.device_name)
                    if success:
                        logger.info(f"✅ Успешно переключились на: {event.device_name}")
                    else:
                        logger.error(f"❌ Не удалось переключиться на: {event.device_name}")
                else:
                    logger.error("❌ AudioDeviceManager недоступен")
            else:
                logger.info(f"ℹ️ Устройство {event.device_name} имеет низкий приоритет, не переключаемся")
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки добавления устройства: {e}")
    
    def _handle_device_removed(self, event: DeviceEvent):
        """Обрабатывает удаление устройства - УПРОЩЕННАЯ ЛОГИКА"""
        try:
            logger.info(f"➖ Обработка удаления устройства: {event.device_name}")
            
            # НЕ проверяем, было ли устройство "текущим" - это источник десинхронизации
            # Просто переключаемся на лучшее доступное устройство
            logger.info(f"🔄 Переключаемся на лучшее доступное устройство...")
            
            # Находим лучшее доступное устройство
            best_device = self._find_best_available_device(event.current_devices)
            
            if best_device:
                logger.info(f"🎯 Переключаемся на лучшее доступное устройство: {best_device}")
                
                # Используем централизованный AudioDeviceManager
                audio_manager = get_global_audio_device_manager()
                if audio_manager:
                    success = audio_manager.switch_to_device(best_device)
                    if success:
                        logger.info(f"✅ Успешно переключились на: {best_device}")
                    else:
                        logger.error(f"❌ Не удалось переключиться на: {best_device}")
                else:
                    logger.error("❌ AudioDeviceManager недоступен")
            else:
                logger.warning("⚠️ Нет доступных устройств для переключения")
                
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
    
    # _is_high_priority_device удален - не используется
    
    def _find_best_available_device(self, available_devices: Set[str]) -> Optional[str]:
        """Находит лучшее доступное устройство"""
        try:
            # Исключаем виртуальные устройства и микрофоны
            real_devices = [name for name in available_devices 
                          if not is_virtual_device(name) 
                          and 'microphone' not in name.lower()]
            
            if not real_devices:
                logger.warning("⚠️ Нет реальных аудио устройств")
                return None
            
            # Используем AudioDeviceManager для получения лучшего устройства
            # Это делегирует логику выбора в UnifiedAudioSystem
            try:
                from audio_device_manager import get_global_audio_device_manager
                audio_device_manager = get_global_audio_device_manager()
                
                if audio_device_manager:
                    # Делегируем выбор лучшего устройства в AudioDeviceManager
                    best_device = audio_device_manager.find_best_available_device(real_devices)
                    if best_device:
                        logger.info(f"🎯 AudioDeviceManager выбрал лучшее устройство: {best_device}")
                        return best_device
                
            except Exception as e:
                logger.warning(f"⚠️ Ошибка получения лучшего устройства через AudioDeviceManager: {e}")
            
            # Fallback: простое правило - первое доступное устройство
            logger.warning("⚠️ Используем fallback: первое доступное устройство")
            best_device = real_devices[0] if real_devices else None
            
            return best_device
            
        except Exception as e:
            logger.error(f"❌ Ошибка поиска лучшего устройства: {e}")
            return None
    
    # _is_headphones и _is_virtual_device удалены - используются из utils.device_utils
    
    
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
