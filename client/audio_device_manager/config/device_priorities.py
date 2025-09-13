"""
Приоритеты аудио устройств
"""

from typing import Dict, List
from ..core.types import DeviceType, DevicePriority


# Стандартные приоритеты устройств
DEFAULT_DEVICE_PRIORITIES = {
    # Высший приоритет - наушники и гарнитуры
    'bluetooth_headphones': 1,
    'airpods': 1,
    'wireless_headphones': 1,
    'usb_headset': 2,
    'bluetooth_headset': 2,
    'wired_headphones': 2,
    
    # Высокий приоритет - беспроводные устройства
    'wireless_speakers': 3,
    'bluetooth_speakers': 3,
    
    # Средний приоритет - внешние устройства
    'external_speakers': 4,
    'usb_audio': 5,
    'dock_station': 6,
    'hdmi_audio': 6,
    
    # Низкий приоритет - встроенные устройства
    'builtin_speakers': 7,
    'builtin_microphone': 8,
    'default_device': 9
}

# Ключевые слова для определения типа устройства
DEVICE_TYPE_KEYWORDS = {
    DeviceType.OUTPUT: [
        'speaker', 'headphone', 'headset', 'airpods', 'earbuds',
        'динамик', 'наушник', 'гарнитура', 'колонка'
    ],
    DeviceType.INPUT: [
        'microphone', 'mic', 'input', 'recorder',
        'микрофон', 'запись'
    ],
    DeviceType.BOTH: [
        'headset', 'гарнитура', 'usb', 'bluetooth'
    ]
}

# Ключевые слова для определения приоритета
PRIORITY_KEYWORDS = {
    DevicePriority.HIGHEST: [
        'airpods', 'bluetooth', 'wireless', 'беспроводной'
    ],
    DevicePriority.HIGH: [
        'headset', 'headphone', 'гарнитура', 'наушник'
    ],
    DevicePriority.MEDIUM: [
        'wireless', 'bluetooth', 'беспроводной'
    ],
    DevicePriority.NORMAL: [
        'external', 'usb', 'внешний'
    ],
    DevicePriority.LOW: [
        'builtin', 'internal', 'встроенный'
    ],
    DevicePriority.LOWEST: [
        'default', 'system', 'системный'
    ]
}


def get_device_priority(device_name: str, device_type: DeviceType) -> int:
    """
    Определение приоритета устройства по имени и типу
    
    Args:
        device_name: Название устройства
        device_type: Тип устройства
        
    Returns:
        int: Приоритет устройства (1-9, где 1 - высший)
    """
    device_name_lower = device_name.lower()
    
    # Проверяем точные совпадения
    for keyword, priority in DEFAULT_DEVICE_PRIORITIES.items():
        if keyword in device_name_lower:
            return priority
    
    # Проверяем по ключевым словам
    for priority, keywords in PRIORITY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in device_name_lower:
                return priority.value
    
    # Приоритет по умолчанию в зависимости от типа
    if device_type == DeviceType.OUTPUT:
        return DevicePriority.NORMAL.value
    elif device_type == DeviceType.INPUT:
        return DevicePriority.LOW.value
    else:
        return DevicePriority.NORMAL.value


def is_headphone_device(device_name: str) -> bool:
    """
    Проверка, является ли устройство наушниками
    
    Args:
        device_name: Название устройства
        
    Returns:
        bool: True если это наушники
    """
    device_name_lower = device_name.lower()
    
    headphone_keywords = [
        'headphone', 'headset', 'airpods', 'earbuds', 'earphone',
        'наушник', 'гарнитура'
    ]
    
    return any(keyword in device_name_lower for keyword in headphone_keywords)


def is_speaker_device(device_name: str) -> bool:
    """
    Проверка, является ли устройство колонками
    
    Args:
        device_name: Название устройства
        
    Returns:
        bool: True если это колонки
    """
    device_name_lower = device_name.lower()
    
    speaker_keywords = [
        'speaker', 'динамик', 'колонка'
    ]
    
    return any(keyword in device_name_lower for keyword in speaker_keywords)


def is_external_device(device_name: str) -> bool:
    """
    Проверка, является ли устройство внешним
    
    Args:
        device_name: Название устройства
        
    Returns:
        bool: True если это внешнее устройство
    """
    device_name_lower = device_name.lower()
    
    external_keywords = [
        'external', 'usb', 'bluetooth', 'wireless', 'dock',
        'внешний', 'беспроводной'
    ]
    
    return any(keyword in device_name_lower for keyword in external_keywords)


def is_builtin_device(device_name: str) -> bool:
    """
    Проверка, является ли устройство встроенным
    
    Args:
        device_name: Название устройства
        
    Returns:
        bool: True если это встроенное устройство
    """
    device_name_lower = device_name.lower()
    
    builtin_keywords = [
        'builtin', 'internal', 'macbook', 'imac', 'mac pro',
        'встроенный', 'внутренний'
    ]
    
    return any(keyword in device_name_lower for keyword in builtin_keywords)


def get_device_type_from_name(device_name: str) -> DeviceType:
    """
    Определение типа устройства по названию
    
    Args:
        device_name: Название устройства
        
    Returns:
        DeviceType: Тип устройства
    """
    device_name_lower = device_name.lower()
    
    # Проверяем ключевые слова для каждого типа
    for device_type, keywords in DEVICE_TYPE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in device_name_lower:
                return device_type
    
    # По умолчанию считаем устройством вывода
    return DeviceType.OUTPUT


def sort_devices_by_priority(devices: List[dict]) -> List[dict]:
    """
    Сортировка устройств по приоритету
    
    Args:
        devices: Список устройств
        
    Returns:
        List[dict]: Отсортированный список устройств
    """
    def priority_key(device):
        name = device.get('name', '')
        device_type = device.get('type', DeviceType.OUTPUT)
        return get_device_priority(name, device_type)
    
    return sorted(devices, key=priority_key)


def get_priority_name(priority: int) -> str:
    """
    Получение названия приоритета
    
    Args:
        priority: Числовой приоритет
        
    Returns:
        str: Название приоритета
    """
    priority_names = {
        1: "Высший",
        2: "Высокий", 
        3: "Средний",
        4: "Обычный",
        5: "Низкий",
        6: "Очень низкий",
        7: "Минимальный",
        8: "Критический",
        9: "Системный"
    }
    
    return priority_names.get(priority, "Неизвестный")
