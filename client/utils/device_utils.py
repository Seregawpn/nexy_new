"""
Утилиты для работы с аудио устройствами

Централизованные методы для определения типов устройств,
чтобы избежать дублирования кода между компонентами.
"""

import logging

logger = logging.getLogger(__name__)

def is_headphones(device_name: str) -> bool:
    """
    Проверяет, являются ли наушниками
    
    Args:
        device_name: Название устройства
        
    Returns:
        True если устройство является наушниками
    """
    try:
        device_lower = device_name.lower()
        
        # Ключевые слова для наушников
        headphones_keywords = [
            'airpods', 'beats', 'sony', 'bose', 'sennheiser',
            'headphones', 'earbuds', 'earphones', 'headset',
            'наушники', 'беспроводные наушники'
        ]
        
        return any(keyword in device_lower for keyword in headphones_keywords)
        
    except Exception as e:
        logger.warning(f"⚠️ Ошибка определения типа наушников для {device_name}: {e}")
        return False

def is_virtual_device(device_name: str) -> bool:
    """
    Проверяет, является ли устройство виртуальным
    
    Args:
        device_name: Название устройства
        
    Returns:
        True если устройство является виртуальным
    """
    try:
        device_lower = device_name.lower()
        
        # Ключевые слова для виртуальных устройств
        virtual_keywords = [
            'blackhole', 'soundflower', 'loopback', 'virtual',
            'aggregate', 'multi-output', 'sound source', 'audio hijack'
        ]
        
        return any(keyword in device_lower for keyword in virtual_keywords)
        
    except Exception as e:
        logger.warning(f"⚠️ Ошибка определения виртуального устройства для {device_name}: {e}")
        return False

def is_high_priority_device(device_name: str) -> bool:
    """
    Проверяет, является ли устройство высокоприоритетным
    
    Args:
        device_name: Название устройства
        
    Returns:
        True если устройство имеет высокий приоритет
    """
    try:
        device_lower = device_name.lower()
        
        # Высокоприоритетные ключевые слова
        high_priority_keywords = [
            'airpods', 'beats', 'bluetooth', 'wireless', 'bt'
        ]
        
        return any(keyword in device_lower for keyword in high_priority_keywords)
        
    except Exception as e:
        logger.warning(f"⚠️ Ошибка определения приоритета устройства {device_name}: {e}")
        return False

def get_device_type_keywords(device_name: str) -> str:
    """
    Определяет тип устройства по ключевым словам
    
    Args:
        device_name: Название устройства
        
    Returns:
        Строка с типом устройства для маппинга приоритетов
    """
    try:
        device_lower = device_name.lower()
        
        # AirPods
        if 'airpods' in device_lower:
            return 'airpods'
        
        # Beats
        elif 'beats' in device_lower:
            return 'beats'
        
        # Bluetooth наушники
        elif 'bluetooth' in device_lower and is_headphones(device_name):
            return 'bluetooth_headphones'
        
        # USB наушники
        elif 'usb' in device_lower and is_headphones(device_name):
            return 'usb_headphones'
        
        # Bluetooth колонки
        elif 'bluetooth' in device_lower:
            return 'bluetooth_speakers'
        
        # USB аудио
        elif 'usb' in device_lower:
            return 'usb_audio'
        
        # Системные динамики
        elif any(tag in device_lower for tag in ['macbook', 'built-in', 'internal', 'speakers']):
            return 'system_speakers'
        
        # Встроенные устройства
        elif 'built-in' in device_lower:
            return 'built_in'
        
        # Микрофоны
        elif 'microphone' in device_lower or 'микрофон' in device_lower:
            return 'microphone'
        
        # Виртуальные устройства
        elif is_virtual_device(device_name):
            return 'virtual_device'
        
        # Остальные устройства
        else:
            return 'other'
            
    except Exception as e:
        logger.warning(f"⚠️ Ошибка определения типа устройства {device_name}: {e}")
        return 'unknown'
