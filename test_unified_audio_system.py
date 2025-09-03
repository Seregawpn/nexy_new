#!/usr/bin/env python3
"""
Тест UnifiedAudioSystem - единой системы управления аудио устройствами
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

def test_unified_audio_system():
    """Тестирует UnifiedAudioSystem"""
    try:
        logger.info("🎵 Тестирование UnifiedAudioSystem...")
        
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
        
        if not audio_system:
            logger.error("❌ Не удалось получить UnifiedAudioSystem")
            return False
        
        # Проверяем инициализацию
        if not audio_system.is_initialized():
            logger.error("❌ UnifiedAudioSystem не инициализирован")
            return False
        
        logger.info("✅ UnifiedAudioSystem инициализирован")
        
        # Получаем текущее устройство
        current_device = audio_system.get_current_device()
        logger.info(f"🎧 Текущее устройство: {current_device}")
        
        # Получаем информацию о текущем устройстве
        current_info = audio_system.get_current_device_info()
        if current_info:
            logger.info(f"   Тип: {current_info.device_type.value}")
            logger.info(f"   Приоритет: {current_info.priority}")
            logger.info(f"   PortAudio output: {current_info.portaudio_output_index}")
            logger.info(f"   PortAudio input: {current_info.portaudio_input_index}")
        
        # Получаем список всех устройств
        devices = audio_system.get_available_devices()
        logger.info(f"📱 Доступно устройств: {len(devices)}")
        
        for device in devices:
            status = "🎧 ТЕКУЩЕЕ" if device.is_default else "  "
            virtual_mark = "🔧 ВИРТУАЛЬНОЕ" if device.device_type.value == 'virtual' else ""
            logger.info(f"{status} {device.name} (тип: {device.device_type.value}, приоритет: {device.priority}) {virtual_mark}")
        
        # Тестируем переключение на лучшее устройство
        logger.info("🔄 Тестирование автоматического выбора лучшего устройства...")
        
        # Находим лучшее устройство
        real_devices = [d for d in devices 
                       if d.device_type.value != 'virtual' 
                       and d.device_type.value != 'microphone'
                       and 'microphone' not in d.name.lower()]
        
        if real_devices:
            best_device = max(real_devices, key=lambda d: d.priority)
            logger.info(f"🎯 Лучшее устройство: {best_device.name} (приоритет: {best_device.priority})")
            
            if best_device.name != current_device:
                logger.info(f"🔄 Переключение на лучшее устройство...")
                success = audio_system.switch_to_device(best_device.name)
                if success:
                    logger.info("✅ Успешно переключились на лучшее устройство")
                else:
                    logger.error("❌ Не удалось переключиться на лучшее устройство")
            else:
                logger.info("✅ Уже используется лучшее устройство")
        else:
            logger.warning("⚠️ Нет подходящих устройств для переключения")
        
        # Тестируем PortAudio индексы
        output_idx, input_idx = audio_system.get_portaudio_indices()
        logger.info(f"🔊 PortAudio индексы - Output: {output_idx}, Input: {input_idx}")
        
        logger.info("✅ Тест UnifiedAudioSystem завершен успешно")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка тестирования UnifiedAudioSystem: {e}")
        return False

if __name__ == "__main__":
    success = test_unified_audio_system()
    sys.exit(0 if success else 1)
