#!/usr/bin/env python3
"""
Тест обработки отключения устройств в UnifiedAudioSystem
"""

import sys
import time
import logging
from pathlib import Path

# Добавляем путь к модулям
sys.path.append(str(Path(__file__).parent / 'client'))

from unified_audio_system import get_global_unified_audio_system

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_device_removal():
    """Тестирует обработку отключения устройств"""
    try:
        logger.info("🎵 Тестирование обработки отключения устройств...")
        
        # Конфигурация
        config = {
            'switch_audio_path': '/opt/homebrew/bin/SwitchAudioSource',
            'device_priorities': {
                'airpods': 95,
                'beats': 90,
                'bluetooth_headphones': 85,
                'usb_headphones': 80,
                'speakers': 70,
                'microphone': 60,
                'virtual': 1
            },
            'virtual_device_keywords': ['blackhole', 'loopback', 'virtual'],
            'exclude_virtual_devices': True
        }
        
        # Получаем глобальный экземпляр
        audio_system = get_global_unified_audio_system(config)
        
        if not audio_system or not audio_system.is_initialized():
            logger.error("❌ UnifiedAudioSystem не инициализирован")
            return False
        
        logger.info("✅ UnifiedAudioSystem инициализирован")
        
        # Получаем текущее устройство
        current_device = audio_system.get_current_device()
        logger.info(f"🎧 Текущее устройство: {current_device}")
        
        # Получаем список всех устройств
        devices = audio_system.get_available_devices()
        logger.info(f"📱 Доступно устройств: {len(devices)}")
        
        for device in devices:
            status = "🎧 ТЕКУЩЕЕ" if device.is_default else "  "
            logger.info(f"{status} {device.name} (тип: {device.device_type.value}, приоритет: {device.priority})")
        
        # Симулируем отключение текущего устройства
        if current_device:
            logger.info(f"🔄 Симулируем отключение устройства: {current_device}")
            
            # Создаем множество отключенных устройств
            removed_devices = {current_device}
            
            # Вызываем обработчик отключения
            audio_system.handle_device_removed(removed_devices)
            
            # Проверяем результат
            new_current_device = audio_system.get_current_device()
            logger.info(f"🎧 Новое текущее устройство: {new_current_device}")
            
            if new_current_device != current_device:
                logger.info("✅ Устройство успешно переключено после отключения")
            else:
                logger.warning("⚠️ Устройство не изменилось после отключения")
        
        logger.info("✅ Тест обработки отключения устройств завершен")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка тестирования отключения устройств: {e}")
        return False

if __name__ == "__main__":
    success = test_device_removal()
    sys.exit(0 if success else 1)
