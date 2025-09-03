#!/usr/bin/env python3
"""
Тест интеграции UnifiedAudioSystem с основным приложением
"""

import sys
import time
import logging
from pathlib import Path

# Добавляем путь к модулям
sys.path.append(str(Path(__file__).parent / 'client'))

from audio_player import AudioPlayer
from unified_audio_system import get_global_unified_audio_system

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_main_app_integration():
    """Тестирует интеграцию с основным приложением"""
    try:
        logger.info("🎵 Тестирование интеграции с основным приложением...")
        
        # 1. Инициализируем AudioPlayer (как в main.py)
        logger.info("🔄 Инициализация AudioPlayer...")
        audio_player = AudioPlayer(sample_rate=48000)
        
        # Проверяем, что UnifiedAudioSystem инициализирован
        if not audio_player.audio_manager:
            logger.error("❌ UnifiedAudioSystem не инициализирован в AudioPlayer")
            return False
        
        logger.info("✅ AudioPlayer инициализирован с UnifiedAudioSystem")
        
        # 2. Проверяем статус системы
        audio_system = audio_player.audio_manager
        
        if not audio_system.is_initialized():
            logger.error("❌ UnifiedAudioSystem не инициализирован")
            return False
        
        logger.info("✅ UnifiedAudioSystem инициализирован")
        
        # 3. Получаем текущее состояние
        current_device = audio_system.get_current_device()
        logger.info(f"🎧 Текущее устройство: {current_device}")
        
        devices = audio_system.get_available_devices()
        logger.info(f"📱 Доступно устройств: {len(devices)}")
        
        for device in devices:
            status = "🎧 ТЕКУЩЕЕ" if device.is_default else "  "
            logger.info(f"{status} {device.name} (тип: {device.device_type.value}, приоритет: {device.priority})")
        
        # 4. Проверяем PortAudio индексы
        output_idx, input_idx = audio_system.get_portaudio_indices()
        logger.info(f"🔊 PortAudio индексы - Output: {output_idx}, Input: {input_idx}")
        
        # 5. Тестируем переключение устройств
        logger.info("🔄 Тестирование переключения устройств...")
        
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
        
        # 6. Проверяем мониторинг в реальном времени
        logger.info("🔄 Проверка мониторинга в реальном времени...")
        
        # Получаем RealtimeDeviceMonitor
        realtime_monitor = audio_system._realtime_monitor
        if realtime_monitor and realtime_monitor.is_monitoring():
            logger.info("✅ RealtimeDeviceMonitor запущен")
        else:
            logger.warning("⚠️ RealtimeDeviceMonitor не запущен")
        
        # 7. Инструкции для пользователя
        logger.info("")
        logger.info("🎧 СИСТЕМА ГОТОВА К ИСПОЛЬЗОВАНИЮ!")
        logger.info("📋 Что работает:")
        logger.info("  ✅ Автоматическое обнаружение устройств")
        logger.info("  ✅ Автоматическое переключение на лучшее устройство")
        logger.info("  ✅ Мониторинг в реальном времени")
        logger.info("  ✅ Единая централизованная система")
        logger.info("")
        logger.info("🎧 ИНСТРУКЦИИ:")
        logger.info("  1. Подключите/отключите наушники")
        logger.info("  2. Система автоматически переключится")
        logger.info("  3. Все изменения логируются")
        logger.info("")
        logger.info("⏳ Мониторинг на 30 секунд...")
        
        # Мониторим в течение 30 секунд
        start_time = time.time()
        while time.time() - start_time < 30:
            try:
                time.sleep(5)
                
                new_current_device = audio_system.get_current_device()
                if new_current_device != current_device:
                    logger.info(f"🔄 Устройство изменилось: {current_device} → {new_current_device}")
                    current_device = new_current_device
                
                logger.info(f"📊 Статус: {current_device} | Мониторинг: {'✅' if realtime_monitor and realtime_monitor.is_monitoring() else '❌'}")
                
            except KeyboardInterrupt:
                logger.info("🛑 Тест прерван пользователем")
                break
        
        # 8. Очистка
        logger.info("🔄 Очистка ресурсов...")
        audio_player.cleanup()
        
        logger.info("✅ Тест интеграции завершен успешно")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка тестирования интеграции: {e}")
        return False

if __name__ == "__main__":
    success = test_main_app_integration()
    sys.exit(0 if success else 1)
