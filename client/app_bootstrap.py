#!/usr/bin/env python3
"""
Интеграционный файл для запуска системы мониторинга аудиоустройств
Связывает слушатель системных событий CoreAudio с монитором устройств
"""

import logging
import time
import sys
from pathlib import Path
from Foundation import NSRunLoop, NSDefaultRunLoopMode, NSDate

# Добавляем корневую директорию в путь для импорта
sys.path.append(str(Path(__file__).parent.parent))

from macos_coreaudio_listener import start_listening, stop_listening
from ideal_audio_monitor_v2 import IdealAudioMonitorV2

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AudioDeviceManager:
    """Менеджер аудиоустройств с полной интеграцией."""
    
    def __init__(self):
        self.monitor = None
        self.listener_loop = None
        self.is_running = False
        self.events_received = []
        
        logger.info("🎯 AudioDeviceManager инициализирован")
    
    def on_audio_change(self, **payload):
        """Callback для обработки изменений аудиоустройств."""
        logger.info("🔄 ИЗМЕНЕНИЕ АУДИОУСТРОЙСТВ:")
        
        changes = payload.get('changes', {})
        active_headphones = payload.get('active_headphones')
        active_speakers = payload.get('active_speakers')
        system_default = payload.get('system_default')
        all_devices = payload.get('all_devices', [])
        
        # Логируем изменения
        for change_type, changed in changes.items():
            if changed:
                logger.info(f"   ✅ {change_type}: ДА")
            else:
                logger.info(f"   ❌ {change_type}: НЕТ")
        
        # Логируем активные устройства
        if active_headphones:
            logger.info(f"   🎧 Активные наушники: {active_headphones.name} (UID: {active_headphones.device_uid})")
        else:
            logger.info(f"   🎧 Активные наушники: НЕ НАЙДЕНЫ")
        
        if active_speakers:
            logger.info(f"   📱 Активные динамики: {active_speakers.name} (UID: {active_speakers.device_uid})")
        else:
            logger.info(f"   📱 Активные динамики: НЕ НАЙДЕНЫ")
        
        if system_default:
            logger.info(f"   🔄 Системный default: {system_default.name} (UID: {system_default.device_uid})")
        else:
            logger.info(f"   🔄 Системный default: НЕ НАЙДЕН")
        
        logger.info(f"   📊 Всего устройств: {len(all_devices)}")
        
        # Сохраняем событие для статистики
        self.events_received.append({
            'timestamp': time.time(),
            'changes': changes,
            'active_headphones': active_headphones.name if active_headphones else None,
            'active_speakers': active_speakers.name if active_speakers else None,
            'system_default': system_default.name if system_default else None
        })
        
        # Здесь можно добавить логику переключения аудиоплеера
        self._handle_audio_switch(changes, active_headphones, active_speakers, system_default)
    
    def _handle_audio_switch(self, changes, active_headphones, active_speakers, system_default):
        """Обрабатывает переключение аудиоустройств."""
        try:
            # Определяем приоритетное устройство
            priority_device = active_headphones or active_speakers or system_default
            
            if priority_device:
                logger.info(f"🎯 Переключение на устройство: {priority_device.name}")
                
                # Здесь можно добавить логику:
                # 1. Остановить текущее воспроизведение
                # 2. Переключить устройство вывода
                # 3. Возобновить воспроизведение
                
                if changes.get('headphones_connected'):
                    logger.info("🎧 Наушники подключены - переключаемся на них")
                elif changes.get('headphones_disconnected'):
                    logger.info("🎧 Наушники отключены - переключаемся на динамики")
                elif changes.get('system_default_changed'):
                    logger.info("🔄 Системный default изменился - обновляем устройство")
            
        except Exception as e:
            logger.error(f"❌ Ошибка при переключении аудио: {e}")
    
    def start(self):
        """Запускает систему мониторинга аудиоустройств."""
        if self.is_running:
            logger.warning("⚠️ Система уже запущена")
            return
        
        logger.info("🚀 ЗАПУСК СИСТЕМЫ МОНИТОРИНГА АУДИОУСТРОЙСТВ")
        logger.info("=" * 60)
        
        try:
            # Создаем монитор
            logger.info("📱 Создание монитора устройств...")
            self.monitor = IdealAudioMonitorV2(callback=self.on_audio_change, logger=logger)
            
            # Запускаем мониторинг
            logger.info("🔄 Запуск мониторинга устройств...")
            self.monitor.start_monitoring()
            
            # Запускаем слушатель системных событий
            logger.info("🎧 Запуск слушателя системных событий...")
            self.listener_loop = start_listening(self.monitor.on_system_event)
            
            if not self.listener_loop:
                logger.error("❌ Не удалось запустить слушатель системных событий")
                self.stop()
                return False
            
            self.is_running = True
            logger.info("✅ Система мониторинга аудиоустройств запущена успешно!")
            logger.info("")
            logger.info("🎧 ИНСТРУКЦИИ ДЛЯ ТЕСТИРОВАНИЯ:")
            logger.info("   1. Подключите наушники")
            logger.info("   2. Отключите наушники")
            logger.info("   3. Измените системное устройство по умолчанию")
            logger.info("   4. Наблюдайте за логами изменений")
            logger.info("")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка при запуске системы: {e}")
            self.stop()
            return False
    
    def stop(self):
        """Останавливает систему мониторинга."""
        if not self.is_running:
            logger.info("⚠️ Система не запущена")
            return
        
        logger.info("🛑 ОСТАНОВКА СИСТЕМЫ МОНИТОРИНГА")
        logger.info("=" * 40)
        
        try:
            # Останавливаем слушатель
            if self.listener_loop:
                logger.info("🛑 Остановка слушателя системных событий...")
                stop_listening()
                self.listener_loop = None
            
            # Останавливаем монитор
            if self.monitor:
                logger.info("🛑 Остановка монитора устройств...")
                self.monitor.stop_monitoring()
                self.monitor = None
            
            self.is_running = False
            logger.info("✅ Система мониторинга остановлена")
            
            # Показываем статистику
            self._show_statistics()
            
        except Exception as e:
            logger.error(f"❌ Ошибка при остановке системы: {e}")
    
    def _show_statistics(self):
        """Показывает статистику работы системы."""
        logger.info("📊 СТАТИСТИКА РАБОТЫ:")
        logger.info(f"   Всего событий: {len(self.events_received)}")
        
        if self.events_received:
            # Группируем события по типам
            event_types = {}
            for event in self.events_received:
                for change_type, changed in event['changes'].items():
                    if changed:
                        event_types[change_type] = event_types.get(change_type, 0) + 1
            
            logger.info("   Типы событий:")
            for event_type, count in event_types.items():
                logger.info(f"     {event_type}: {count} раз")
            
            # Показываем последние события
            logger.info("   Последние события:")
            for i, event in enumerate(self.events_received[-3:], 1):
                timestamp = time.strftime("%H:%M:%S", time.localtime(event['timestamp']))
                changes = [k for k, v in event['changes'].items() if v]
                logger.info(f"     {i}. {timestamp}: {', '.join(changes)}")
        else:
            logger.warning("   ⚠️ События не получены")
    
    def run_interactive(self, duration=60):
        """Запускает интерактивный режим на указанное время."""
        if not self.start():
            return False
        
        try:
            logger.info(f"⏱️ Интерактивный режим на {duration} секунд...")
            logger.info("   Нажмите Ctrl+C для досрочной остановки")
            
            start_time = time.time()
            while time.time() - start_time < duration:
                # Обрабатываем события в RunLoop
                if self.listener_loop:
                    self.listener_loop.runMode_beforeDate_(NSDefaultRunLoopMode, NSDate.dateWithTimeIntervalSinceNow_(0.1))
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            logger.info("⏹️ Остановка по Ctrl+C...")
        
        finally:
            self.stop()
        
        return True

def main():
    """Главная функция для запуска системы."""
    logger.info("🎯 ЗАПУСК СИСТЕМЫ МОНИТОРИНГА АУДИОУСТРОЙСТВ")
    logger.info("=" * 60)
    
    # Создаем менеджер
    manager = AudioDeviceManager()
    
    # Запускаем интерактивный режим
    success = manager.run_interactive(duration=60)
    
    if success:
        logger.info("✅ Система завершила работу успешно")
    else:
        logger.error("❌ Система завершила работу с ошибками")
    
    return success

if __name__ == "__main__":
    main()
