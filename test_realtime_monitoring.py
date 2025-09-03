#!/usr/bin/env python3
"""
Тест системы мониторинга устройств в реальном времени
"""

import sys
import time
import logging
from pathlib import Path

# Добавляем путь к модулям
sys.path.append(str(Path(__file__).parent / 'client'))

from unified_audio_system import get_global_unified_audio_system
from realtime_device_monitor import get_global_realtime_monitor, DeviceEvent

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_realtime_monitoring():
    """Тестирует систему мониторинга в реальном времени"""
    try:
        logger.info("🎵 Тестирование системы мониторинга в реальном времени...")
        
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
        
        # Получаем глобальный экземпляр UnifiedAudioSystem
        audio_system = get_global_unified_audio_system(config)
        
        if not audio_system or not audio_system.is_initialized():
            logger.error("❌ UnifiedAudioSystem не инициализирован")
            return False
        
        logger.info("✅ UnifiedAudioSystem инициализирован")
        
        # Получаем RealtimeDeviceMonitor
        realtime_monitor = get_global_realtime_monitor()
        
        if not realtime_monitor.is_monitoring():
            logger.error("❌ RealtimeDeviceMonitor не запущен")
            return False
        
        logger.info("✅ RealtimeDeviceMonitor запущен")
        
        # Получаем текущее состояние
        current_device = audio_system.get_current_device()
        logger.info(f"🎧 Текущее устройство: {current_device}")
        
        devices = audio_system.get_available_devices()
        logger.info(f"📱 Доступно устройств: {len(devices)}")
        
        for device in devices:
            status = "🎧 ТЕКУЩЕЕ" if device.is_default else "  "
            logger.info(f"{status} {device.name} (тип: {device.device_type.value}, приоритет: {device.priority})")
        
        # Инструкции для пользователя
        logger.info("")
        logger.info("🎧 ИНСТРУКЦИИ ДЛЯ ТЕСТИРОВАНИЯ:")
        logger.info("1. Подключите AirPods или другие наушники")
        logger.info("2. Отключите их")
        logger.info("3. Система должна автоматически переключаться")
        logger.info("")
        logger.info("⏳ Мониторинг запущен на 60 секунд...")
        logger.info("   (Нажмите Ctrl+C для досрочного завершения)")
        
        # Мониторим в течение 60 секунд
        start_time = time.time()
        while time.time() - start_time < 60:
            try:
                # Проверяем текущее устройство каждые 5 секунд
                time.sleep(5)
                
                new_current_device = audio_system.get_current_device()
                if new_current_device != current_device:
                    logger.info(f"🔄 Устройство изменилось: {current_device} → {new_current_device}")
                    current_device = new_current_device
                
                # Показываем статус
                logger.info(f"📊 Статус: {current_device} | Мониторинг: {'✅' if realtime_monitor.is_monitoring() else '❌'}")
                
            except KeyboardInterrupt:
                logger.info("🛑 Тест прерван пользователем")
                break
        
        logger.info("✅ Тест системы мониторинга завершен")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка тестирования мониторинга: {e}")
        return False

if __name__ == "__main__":
    success = test_realtime_monitoring()
    sys.exit(0 if success else 1)
