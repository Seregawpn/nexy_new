#!/usr/bin/env python3
"""
Интерактивный тест Audio Device Manager в реальном времени
Тестирует мониторинг подключения/отключения наушников
"""

import asyncio
import time
import signal
import sys
from typing import Optional

# Импортируем модуль
try:
    from audio_device_manager import (
        AudioDeviceManager, 
        create_default_audio_device_manager,
        AudioDevice, 
        DeviceType, 
        DeviceStatus,
        DeviceChange
    )
    print("✅ Модуль audio_device_manager импортирован успешно")
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    sys.exit(1)

class LiveAudioDeviceTester:
    def __init__(self):
        self.manager: Optional[AudioDeviceManager] = None
        self.running = False
        self.device_changes = []
        self.connection_events = []
        
    async def setup_manager(self):
        """Настройка менеджера устройств"""
        print("🔧 Настройка AudioDeviceManager...")
        
        try:
            # Создаем менеджер с настройками для тестирования
            config = {
                'auto_switch_enabled': True,
                'monitoring_interval': 1.0,  # Проверяем каждую секунду
                'device_priorities': {
                    'bluetooth_headphones': 1,
                    'wired_headphones': 2,
                    'external_speakers': 3,
                    'builtin_speakers': 4
                }
            }
            
            self.manager = create_audio_device_manager(config)
            
            # Регистрируем колбэки
            self.manager.register_device_change_callback("live_tester", self.on_device_changed)
            self.manager.register_device_switch_callback("live_tester", self.on_device_switched)
            
            print("✅ AudioDeviceManager настроен")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка настройки: {e}")
            return False
    
    def on_device_changed(self, change: DeviceChange):
        """Обработчик изменения устройств"""
        timestamp = time.strftime("%H:%M:%S")
        event_type = "ПОДКЛЮЧЕНО" if change.is_connected else "ОТКЛЮЧЕНО"
        
        print(f"\n🔔 [{timestamp}] УСТРОЙСТВО {event_type}:")
        print(f"   Название: {change.device.name}")
        print(f"   Тип: {change.device.type.value}")
        print(f"   ID: {change.device.id}")
        print(f"   Статус: {change.device.status.value}")
        
        # Сохраняем событие
        self.device_changes.append({
            'timestamp': timestamp,
            'device_name': change.device.name,
            'event_type': event_type,
            'device_type': change.device.type.value,
            'is_connected': change.is_connected
        })
        
        # Проверяем, это наушники?
        if any(keyword in change.device.name.lower() for keyword in 
               ['airpods', 'headphone', 'наушник', 'bluetooth', 'wireless']):
            print(f"   🎧 ОБНАРУЖЕНЫ НАУШНИКИ!")
            self.connection_events.append({
                'timestamp': timestamp,
                'action': 'headphones_detected' if change.is_connected else 'headphones_disconnected',
                'device_name': change.device.name
            })
    
    def on_device_switched(self, from_device: AudioDevice, to_device: AudioDevice):
        """Обработчик переключения устройств"""
        timestamp = time.strftime("%H:%M:%S")
        
        print(f"\n🔄 [{timestamp}] ПЕРЕКЛЮЧЕНИЕ УСТРОЙСТВА:")
        print(f"   С: {from_device.name if from_device else 'Неизвестно'}")
        print(f"   На: {to_device.name}")
        print(f"   Тип: {to_device.type.value}")
        
        self.connection_events.append({
            'timestamp': timestamp,
            'action': 'device_switched',
            'from_device': from_device.name if from_device else 'Unknown',
            'to_device': to_device.name
        })
    
    async def start_monitoring(self):
        """Запуск мониторинга"""
        print("🚀 Запуск мониторинга устройств...")
        
        try:
            # Запускаем мониторинг
            await self.manager.start_monitoring()
            self.running = True
            
            print("✅ Мониторинг запущен")
            print("\n" + "="*60)
            print("🎧 ТЕСТИРОВАНИЕ НАУШНИКОВ В РЕАЛЬНОМ ВРЕМЕНИ")
            print("="*60)
            print("📋 ИНСТРУКЦИИ:")
            print("   1. Подключите наушники (Bluetooth или проводные)")
            print("   2. Отключите наушники")
            print("   3. Подключите снова")
            print("   4. Нажмите Ctrl+C для остановки")
            print("="*60)
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка запуска мониторинга: {e}")
            return False
    
    async def show_current_devices(self):
        """Показать текущие устройства"""
        try:
            devices = await self.manager.get_available_devices()
            print(f"\n📱 ТЕКУЩИЕ УСТРОЙСТВА ({len(devices)}):")
            
            for i, device in enumerate(devices, 1):
                status_icon = "🟢" if device.is_available else "🔴"
                default_icon = "⭐" if device.is_default else "  "
                print(f"   {i}. {status_icon} {default_icon} {device.name}")
                print(f"      Тип: {device.type.value} | ID: {device.id}")
            
        except Exception as e:
            print(f"❌ Ошибка получения устройств: {e}")
    
    async def show_metrics(self):
        """Показать метрики"""
        try:
            metrics = self.manager.get_metrics()
            print(f"\n📊 МЕТРИКИ:")
            print(f"   Всего устройств: {metrics.total_devices}")
            print(f"   Доступных: {metrics.available_devices}")
            print(f"   Недоступных: {metrics.unavailable_devices}")
            print(f"   Переключений: {metrics.total_switches}")
            print(f"   Ошибок: {metrics.total_errors}")
            
        except Exception as e:
            print(f"❌ Ошибка получения метрик: {e}")
    
    async def show_events_summary(self):
        """Показать сводку событий"""
        if not self.device_changes:
            print("\n📝 События не обнаружены")
            return
        
        print(f"\n📝 СВОДКА СОБЫТИЙ ({len(self.device_changes)}):")
        for event in self.device_changes[-10:]:  # Последние 10 событий
            print(f"   [{event['timestamp']}] {event['event_type']}: {event['device_name']}")
        
        # Статистика по наушникам
        headphone_events = [e for e in self.connection_events if 'headphones' in e['action']]
        if headphone_events:
            print(f"\n🎧 СОБЫТИЯ НАУШНИКОВ ({len(headphone_events)}):")
            for event in headphone_events:
                print(f"   [{event['timestamp']}] {event['action']}: {event['device_name']}")
    
    async def stop_monitoring(self):
        """Остановка мониторинга"""
        if self.manager and self.running:
            print("\n🛑 Остановка мониторинга...")
            try:
                await self.manager.stop_monitoring()
                self.running = False
                print("✅ Мониторинг остановлен")
            except Exception as e:
                print(f"❌ Ошибка остановки: {e}")
    
    def signal_handler(self, signum, frame):
        """Обработчик сигналов"""
        print(f"\n\n🛑 Получен сигнал {signum}, остановка...")
        asyncio.create_task(self.stop_monitoring())
        sys.exit(0)

async def main():
    """Основная функция"""
    print("🧪 ИНТЕРАКТИВНЫЙ ТЕСТ AUDIO DEVICE MANAGER")
    print("=" * 50)
    
    tester = LiveAudioDeviceTester()
    
    # Настройка обработчика сигналов
    signal.signal(signal.SIGINT, tester.signal_handler)
    signal.signal(signal.SIGTERM, tester.signal_handler)
    
    try:
        # Настройка менеджера
        if not await tester.setup_manager():
            return
        
        # Показать текущие устройства
        await tester.show_current_devices()
        
        # Запуск мониторинга
        if not await tester.start_monitoring():
            return
        
        # Основной цикл мониторинга
        while tester.running:
            await asyncio.sleep(1)
            
            # Каждые 10 секунд показываем метрики
            if len(tester.device_changes) > 0 and len(tester.device_changes) % 10 == 0:
                await tester.show_metrics()
        
    except KeyboardInterrupt:
        print("\n\n🛑 Тест прерван пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
    finally:
        # Остановка и сводка
        await tester.stop_monitoring()
        await tester.show_events_summary()
        print("\n🎉 Тест завершен!")

if __name__ == "__main__":
    asyncio.run(main())
