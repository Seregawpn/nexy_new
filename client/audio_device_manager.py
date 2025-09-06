"""
AudioDeviceManager - Единый централизованный интерфейс для управления аудио устройствами

Этот модуль предоставляет единую точку входа для всех операций с аудио устройствами:
- Переключение устройств
- Получение информации об устройствах
- Автоматическое управление
- Fallback стратегии

Все компоненты должны использовать ТОЛЬКО этот интерфейс.
"""

import logging
from typing import Optional, Dict, List, Set
from utils.device_utils import is_headphones, get_device_type_keywords

logger = logging.getLogger(__name__)

class AudioDeviceManager:
    """
    Единый централизованный менеджер аудио устройств
    
    Принципы:
    1. ЕДИНСТВЕННАЯ точка входа для всех операций с устройствами
    2. Централизованное управление состоянием
    3. Автоматические fallback стратегии
    4. Thread-safe операции
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        
        # Инициализируем компоненты
        self._unified_system = None
        self._realtime_monitor = None
        self._initialized = False
        
        logger.info("🎛️ AudioDeviceManager инициализирован")
    
    def initialize(self, unified_system=None, realtime_monitor=None) -> bool:
        """Инициализирует все компоненты системы"""
        try:
            logger.info("🔄 Инициализация AudioDeviceManager...")
            
            # Получаем компоненты через параметры или глобальные функции
            if unified_system:
                self._unified_system = unified_system
            else:
                # Импортируем только когда нужно, чтобы избежать циклических импортов
                from unified_audio_system import get_global_unified_audio_system
                self._unified_system = get_global_unified_audio_system()
            
            if not self._unified_system:
                logger.error("❌ UnifiedAudioSystem недоступен")
                return False
            
            if realtime_monitor:
                self._realtime_monitor = realtime_monitor
            else:
                # Импортируем только когда нужно, чтобы избежать циклических импортов
                from realtime_device_monitor import get_global_realtime_monitor
                self._realtime_monitor = get_global_realtime_monitor()
            
            if not self._realtime_monitor:
                logger.error("❌ RealtimeDeviceMonitor недоступен")
                return False
            
            self._initialized = True
            logger.info("✅ AudioDeviceManager успешно инициализирован")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации AudioDeviceManager: {e}")
            return False
    
    def switch_to_device(self, device_name: str) -> bool:
        """
        ЕДИНСТВЕННЫЙ метод переключения устройств в системе
        
        Args:
            device_name: Имя устройства для переключения
            
        Returns:
            bool: True если переключение успешно, False иначе
        """
        if not self._initialized:
            logger.error("❌ AudioDeviceManager не инициализирован")
            return False
        
        try:
            logger.info(f"🎛️ [AudioDeviceManager] Переключение на устройство: {device_name}")
            success = self._unified_system.switch_to_device(device_name)
            
            if success:
                logger.info(f"✅ [AudioDeviceManager] Успешно переключились на: {device_name}")
            else:
                logger.error(f"❌ [AudioDeviceManager] Не удалось переключиться на: {device_name}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ [AudioDeviceManager] Ошибка переключения устройства: {e}")
            return False
    
    def switch_to_system_device(self) -> bool:
        """
        Переключается на системное устройство (динамики)
        
        Returns:
            bool: True если переключение успешно, False иначе
        """
        if not self._initialized:
            logger.error("❌ AudioDeviceManager не инициализирован")
            return False
        
        try:
            logger.info("🎛️ [AudioDeviceManager] Переключение на системное устройство")
            
            # Получаем системное устройство
            system_device = self._unified_system.get_system_device()
            if not system_device:
                logger.error("❌ [AudioDeviceManager] Системное устройство не найдено")
                return False
            
            # Переключаемся на системное устройство
            success = self.switch_to_device(system_device.name)
            
            if success:
                logger.info(f"✅ [AudioDeviceManager] Переключились на системное устройство: {system_device.name}")
            else:
                logger.error(f"❌ [AudioDeviceManager] Не удалось переключиться на системное устройство")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ [AudioDeviceManager] Ошибка переключения на системное устройство: {e}")
            return False
    
    def auto_switch_to_best(self) -> bool:
        """
        Автоматически переключается на лучшее доступное устройство
        
        Returns:
            bool: True если переключение успешно, False иначе
        """
        if not self._initialized:
            logger.error("❌ AudioDeviceManager не инициализирован")
            return False
        
        try:
            logger.info("🎛️ [AudioDeviceManager] Автоматическое переключение на лучшее устройство")
            
            success = self._unified_system.auto_switch_to_best()
            
            if success:
                logger.info("✅ [AudioDeviceManager] Автоматически переключились на лучшее устройство")
            else:
                logger.error("❌ [AudioDeviceManager] Не удалось автоматически переключиться на лучшее устройство")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ [AudioDeviceManager] Ошибка автоматического переключения: {e}")
            return False
    
    def get_current_device(self) -> Optional[str]:
        """
        Получает текущее активное устройство
        
        Returns:
            str: Имя текущего устройства или None
        """
        if not self._initialized:
            logger.error("❌ AudioDeviceManager не инициализирован")
            return None
        
        try:
            return self._unified_system.get_current_device()
        except Exception as e:
            logger.error(f"❌ [AudioDeviceManager] Ошибка получения текущего устройства: {e}")
            return None
    
    def get_current_device_info(self) -> Optional[Dict]:
        """
        Получает информацию о текущем устройстве
        
        Returns:
            Dict: Информация о текущем устройстве или None
        """
        if not self._initialized:
            logger.error("❌ AudioDeviceManager не инициализирован")
            return None
        
        try:
            current_device = self.get_current_device()
            if current_device:
                return self._unified_system.get_device_info(current_device)
            return None
        except Exception as e:
            logger.error(f"❌ [AudioDeviceManager] Ошибка получения информации об устройстве: {e}")
            return None
    
    def get_available_devices(self) -> List[Dict]:
        """
        Получает список доступных устройств
        
        Returns:
            List[Dict]: Список доступных устройств
        """
        if not self._initialized:
            logger.error("❌ AudioDeviceManager не инициализирован")
            return []
        
        try:
            return self._unified_system.get_available_devices()
        except Exception as e:
            logger.error(f"❌ [AudioDeviceManager] Ошибка получения списка устройств: {e}")
            return []
    
    def is_device_available(self, device_name: str) -> bool:
        """
        Проверяет, доступно ли устройство
        
        Args:
            device_name: Имя устройства для проверки
            
        Returns:
            bool: True если устройство доступно, False иначе
        """
        if not self._initialized:
            return False
        
        try:
            devices = self.get_available_devices()
            return any(device.get('name') == device_name for device in devices)
        except Exception as e:
            logger.error(f"❌ [AudioDeviceManager] Ошибка проверки доступности устройства: {e}")
            return False
    
    def get_system_device(self) -> Optional[Dict]:
        """
        Получает системное устройство (динамики)
        
        Returns:
            Dict: Системное устройство или None
        """
        if not self._initialized:
            return None
        
        try:
            return self._unified_system.get_system_device()
        except Exception as e:
            logger.error(f"❌ [AudioDeviceManager] Ошибка получения системного устройства: {e}")
            return None
    
    def find_best_available_device(self, available_devices: List[str]) -> Optional[str]:
        """Находит лучшее доступное устройство из списка"""
        try:
            if not self._unified_system:
                logger.warning("⚠️ [AudioDeviceManager] UnifiedAudioSystem недоступен")
                return available_devices[0] if available_devices else None
            
            # Получаем приоритеты из конфигурации
            device_priorities = self._unified_system.device_priorities
            
            best_device = None
            best_priority = 0
            
            for device in available_devices:
                device_lower = device.lower()
                priority = 50  # Приоритет по умолчанию
                
                # Определяем тип устройства и получаем приоритет из конфигурации
                if 'airpods' in device_lower:
                    priority = device_priorities.get('airpods', 100)
                elif 'beats' in device_lower:
                    priority = device_priorities.get('beats', 95)
                elif 'bluetooth' in device_lower and is_headphones(device):
                    priority = device_priorities.get('bluetooth_headphones', 90)
                elif 'usb' in device_lower and is_headphones(device):
                    priority = device_priorities.get('usb_headphones', 85)
                elif 'bluetooth' in device_lower:
                    priority = device_priorities.get('bluetooth_speakers', 70)
                elif 'usb' in device_lower:
                    priority = device_priorities.get('usb_audio', 60)
                elif any(tag in device_lower for tag in ['macbook', 'built-in', 'internal', 'speakers']):
                    priority = device_priorities.get('system_speakers', 40)
                elif any(tag in device_lower for tag in ['blackhole', 'soundflower', 'loopback', 'virtual']):
                    priority = device_priorities.get('virtual_device', 1)
                else:
                    priority = device_priorities.get('other', 10)
                
                if priority > best_priority:
                    best_priority = priority
                    best_device = device
            
            logger.info(f"🎯 [AudioDeviceManager] Выбрано устройство: {best_device} (приоритет: {best_priority})")
            return best_device
            
        except Exception as e:
            logger.error(f"❌ [AudioDeviceManager] Ошибка выбора лучшего устройства: {e}")
            return available_devices[0] if available_devices else None
    
    # _is_headphones удален - используется из utils.device_utils

# Глобальный экземпляр
_global_audio_device_manager = None

def get_global_audio_device_manager() -> Optional[AudioDeviceManager]:
    """Получает глобальный экземпляр AudioDeviceManager"""
    return _global_audio_device_manager

def initialize_global_audio_device_manager(config: Dict = None, unified_system=None, realtime_monitor=None) -> AudioDeviceManager:
    """Инициализирует глобальный экземпляр AudioDeviceManager"""
    global _global_audio_device_manager
    
    if _global_audio_device_manager is None:
        _global_audio_device_manager = AudioDeviceManager(config)
        _global_audio_device_manager.initialize(unified_system, realtime_monitor)
    
    return _global_audio_device_manager
