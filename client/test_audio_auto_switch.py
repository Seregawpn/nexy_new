#!/usr/bin/env python3
"""
Простой тест автоматического переключения аудио устройств
- Сразу определяет все устройства
- Автоматически выбирает лучшее по приоритету  
- Показывает активное устройство
- Автоматически переключается при изменениях
"""

import asyncio
import time
import signal
import sys
import logging
from datetime import datetime
from typing import List, Optional

# Включаем DEBUG логирование
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

# Импорт модуля
try:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    
    from audio_device_manager import AudioDeviceManager, AudioDevice, DeviceType, DevicePriority
    print("✅ Модуль audio_device_manager импортирован успешно")
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    sys.exit(1)


class SimpleAudioSwitchTest:
    """Простой тест автоматического переключения"""
    
    def __init__(self):
        self.manager = None
        self.running = False
        self.start_time = None
        self.current_device = None
        self.device_changes = []
        
    async def setup(self):
        """Настройка теста"""
        print("🔧 Настройка автоматического переключения...")
        
        try:
            # Создаем менеджер
            self.manager = AudioDeviceManager()
            
            # Регистрируем колбэки
            self.manager.set_device_changed_callback(self.on_device_changed)
            self.manager.set_device_switched_callback(self.on_device_switched)
            
            print("✅ Менеджер настроен")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка настройки: {e}")
            return False
    
    async def start(self):
        """Запуск теста"""
        print("\n🚀 ЗАПУСК АВТОМАТИЧЕСКОГО ПЕРЕКЛЮЧЕНИЯ")
        print("=" * 60)
        
        # Показываем все устройства
        await self.show_all_devices()
        
        # Запускаем менеджер
        success = await self.manager.start()
        if not success:
            print("❌ Не удалось запустить менеджер")
            return False
        
        # Определяем и переключаемся на лучшее устройство
        await self.select_best_device()
        
        # Запускаем мониторинг
        self.running = True
        self.start_time = time.time()
        
        print("\n⚡ МОНИТОРИНГ ЗАПУЩЕН!")
        print("🎧 Подключайте/отключайте наушники для тестирования")
        print("⏹️  Нажмите Ctrl+C для остановки")
        print("=" * 60)
        
        return True
    
    async def show_all_devices(self):
        """Показать все доступные устройства"""
        print("\n📱 ОБНАРУЖЕННЫЕ УСТРОЙСТВА:")
        print("-" * 50)
        
        try:
            devices = await self.manager.get_available_devices()
            
            if not devices:
                print("❌ Устройства не найдены")
                return
            
            # Получаем текущее активное устройство
            current_device = await self.manager.get_current_device()
            
            # Группируем по типам
            output_devices = [d for d in devices if d.type == DeviceType.OUTPUT]
            input_devices = [d for d in devices if d.type == DeviceType.INPUT]
            
            # Показываем устройства вывода (приоритетные)
            if output_devices:
                print("🔊 УСТРОЙСТВА ВЫВОДА (по приоритету):")
                for i, device in enumerate(output_devices, 1):
                    priority_text = self.get_priority_text(device.priority)
                    channels_text = "наушники" if device.channels == 2 else "динамики"
                    
                    # Помечаем активное устройство
                    active_marker = "🎯 АКТИВНО!" if current_device and device.id == current_device.id else ""
                    
                    print(f"   {i}. {device.name} {active_marker}")
                    print(f"      Каналы: {device.channels} ({channels_text})")
                    print(f"      Приоритет: {device.priority.value} ({priority_text})")
                    print()
            
            # Показываем текущее активное устройство отдельно
            if current_device:
                print("🎯 ТЕКУЩЕЕ АКТИВНОЕ УСТРОЙСТВО:")
                device_icon = "🎧" if current_device.channels == 2 else "🔊"
                priority_text = self.get_priority_text(current_device.priority)
                channels_text = "наушники" if current_device.channels == 2 else "динамики"
                print(f"   {device_icon} {current_device.name}")
                print(f"      Каналы: {current_device.channels} ({channels_text})")
                print(f"      Приоритет: {current_device.priority.value} ({priority_text})")
                print()
            else:
                print("⚠️ АКТИВНОЕ УСТРОЙСТВО НЕ ОПРЕДЕЛЕНО")
                print()
            
            # Показываем устройства ввода
            if input_devices:
                print("🎤 УСТРОЙСТВА ВВОДА:")
                for i, device in enumerate(input_devices, 1):
                    print(f"   {i}. {device.name} (каналы: {device.channels})")
                print()
                
        except Exception as e:
            print(f"❌ Ошибка получения устройств: {e}")
    
    async def select_best_device(self):
        """Выбрать лучшее устройство по приоритету"""
        print("🎯 АВТОМАТИЧЕСКИЙ ВЫБОР УСТРОЙСТВА...")
        
        try:
            devices = await self.manager.get_available_devices()
            if not devices:
                print("❌ Нет устройств для выбора")
                return
            
            # Находим лучшее устройство вывода
            output_devices = [d for d in devices if d.type == DeviceType.OUTPUT and d.is_available]
            
            if not output_devices:
                print("❌ Нет доступных устройств вывода")
                return
            
            # Сортируем по приоритету (меньшее число = выше приоритет)
            best_device = min(output_devices, key=lambda x: x.priority.value)
            
            print(f"🏆 ЛУЧШЕЕ УСТРОЙСТВО: {best_device.name}")
            print(f"   Приоритет: {best_device.priority.value} ({self.get_priority_text(best_device.priority)})")
            print(f"   Каналы: {best_device.channels} ({'наушники' if best_device.channels == 2 else 'динамики'})")
            
            # Переключаемся на лучшее устройство
            print("🔄 Переключение на лучшее устройство...")
            success = await self.manager.switch_to_device(best_device)
            
            if success:
                self.current_device = best_device
                print(f"✅ Успешно переключились на: {best_device.name}")
            else:
                print(f"⚠️ Не удалось переключиться на: {best_device.name}")
                
        except Exception as e:
            print(f"❌ Ошибка выбора устройства: {e}")
    
    def get_priority_text(self, priority: DevicePriority) -> str:
        """Получить текстовое описание приоритета"""
        priority_map = {
            DevicePriority.HIGHEST: "САМЫЙ ВЫСОКИЙ",
            DevicePriority.HIGH: "ВЫСОКИЙ", 
            DevicePriority.MEDIUM: "СРЕДНИЙ",
            DevicePriority.NORMAL: "ОБЫЧНЫЙ",
            DevicePriority.LOW: "НИЗКИЙ",
            DevicePriority.LOWEST: "САМЫЙ НИЗКИЙ"
        }
        return priority_map.get(priority, "НЕИЗВЕСТНО")
    
    def on_device_changed(self, change):
        """Обработчик изменения устройств"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Обрабатываем добавленные устройства
        for device in change.added:
            if device.type == DeviceType.OUTPUT:
                print(f"\n🔔 [{timestamp}] НАУШНИКИ ПОДКЛЮЧЕНЫ!")
                print(f"🎧 {device.name} (приоритет: {device.priority.value})")
                print("⚡ Автоматическое переключение...")
                
                # Сохраняем событие
                self.device_changes.append({
                    'time': timestamp,
                    'device': device.name,
                    'action': 'ПОДКЛЮЧЕНО'
                })
        
        # Обрабатываем удаленные устройства  
        for device in change.removed:
            if device.type == DeviceType.OUTPUT:
                print(f"\n🔔 [{timestamp}] НАУШНИКИ ОТКЛЮЧЕНЫ!")
                print(f"🎧 {device.name}")
                print("⚡ Переключение на другое устройство...")
                
                # Сохраняем событие
                self.device_changes.append({
                    'time': timestamp,
                    'device': device.name,
                    'action': 'ОТКЛЮЧЕНО'
                })
    
    def on_device_switched(self, from_device: Optional[AudioDevice], to_device: AudioDevice):
        """Обработчик переключения устройств"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        print(f"\n🔄 [{timestamp}] УСТРОЙСТВО ПЕРЕКЛЮЧЕНО!")
        if from_device is not None:
            print(f"   От: {from_device.name}")
        else:
            print(f"   От: не определено")
        print(f"   На: {to_device.name}")
        
        self.current_device = to_device
        
        # Сохраняем событие
        self.device_changes.append({
            'time': timestamp,
            'from': from_device.name if from_device is not None else "Неизвестно",
            'to': to_device.name,
            'action': 'ПЕРЕКЛЮЧЕНО'
        })
    
    async def show_status(self):
        """Показать текущий статус"""
        if not self.running:
            return
            
        runtime = time.time() - self.start_time if self.start_time else 0
        
        # Принудительно обновляем текущее устройство
        self.current_device = await self.manager.get_current_device()
        
        print(f"\n📊 СТАТУС ({runtime:.0f}с):")
        
        # Показываем активное устройство
        if self.current_device:
            device_icon = "🎧" if self.current_device.channels == 2 else "🔊"
            priority_text = self.get_priority_text(self.current_device.priority)
            channels_text = "наушники" if self.current_device.channels == 2 else "динамики"
            print(f"   🎯 АКТИВНО: {device_icon} {self.current_device.name}")
            print(f"      Тип: {channels_text}")
            print(f"      Приоритет: {self.current_device.priority.value} ({priority_text})")
            print(f"      Каналы: {self.current_device.channels}")
        else:
            print(f"   🎯 АКТИВНО: не определено")
            print(f"   ⚠️ Попытка найти лучшее устройство...")
            
            # Пытаемся найти лучшее устройство
            devices = await self.manager.get_available_devices()
            if devices:
                output_devices = [d for d in devices if d.type == DeviceType.OUTPUT and d.is_available]
                if output_devices:
                    best_device = min(output_devices, key=lambda x: x.priority.value)
                    print(f"   💡 Рекомендуется: {best_device.name} (приоритет: {best_device.priority.value})")
        
        # Показываем статистику
        print(f"   📝 Событий: {len(self.device_changes)}")
        if self.device_changes:
            last_event = self.device_changes[-1]
            print(f"   🔔 Последнее: {last_event['action']} в {last_event['time']}")
    
    async def run(self):
        """Запуск основного цикла"""
        try:
            # Настройка
            if not await self.setup():
                return
            
            # Запуск
            if not await self.start():
                return
            
            # Основной цикл
            while self.running:
                await self.show_status()
                await asyncio.sleep(5)  # Обновляем каждые 5 секунд
                
        except KeyboardInterrupt:
            print("\n\n🛑 Получен сигнал остановки...")
        except Exception as e:
            print(f"\n❌ Ошибка: {e}")
        finally:
            await self.stop()
    
    async def stop(self):
        """Остановка теста"""
        print("\n🛑 Остановка...")
        
        if self.manager:
            await self.manager.stop()
        
        # Показываем итоговую статистику
        if self.device_changes:
            print(f"\n📝 СОБЫТИЯ ({len(self.device_changes)}):")
            for event in self.device_changes[-5:]:  # Последние 5 событий
                print(f"   {event['time']}: {event['action']}")
        
        print("✅ Тест завершен")


async def main():
    """Главная функция"""
    print("🧪 ТЕСТ АВТОМАТИЧЕСКОГО ПЕРЕКЛЮЧЕНИЯ АУДИО УСТРОЙСТВ")
    print("=" * 60)
    
    test = SimpleAudioSwitchTest()
    await test.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 До свидания!")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
