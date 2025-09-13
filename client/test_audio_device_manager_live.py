#!/usr/bin/env python3
"""
Интерактивный тест Audio Device Manager в реальном времени
Позволяет тестировать автоматическое переключение устройств
"""

import sys
import os
import asyncio
import logging
import signal
import time
from datetime import datetime

# Добавляем путь к модулю
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LiveAudioDeviceTester:
    """Интерактивный тестер Audio Device Manager"""
    
    def __init__(self):
        self.manager = None
        self.running = False
        self.device_changes = []
        self.device_switches = []
        self.start_time = None
        
    async def setup(self):
        """Настройка тестера"""
        print("🔧 Настраиваем Audio Device Manager...")
        
        try:
            from audio_device_manager import create_default_audio_device_manager
            
            # Создаем менеджер
            self.manager = create_default_audio_device_manager()
            
            # Настраиваем callbacks
            self.manager.set_device_changed_callback(self.on_device_changed)
            self.manager.set_device_switched_callback(self.on_device_switched)
            self.manager.set_error_callback(self.on_error)
            
            print("✅ Audio Device Manager настроен")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка настройки: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def on_device_changed(self, change):
        """Callback для изменений устройств"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"\n🔄 [{timestamp}] ИЗМЕНЕНИЕ УСТРОЙСТВА:")
        print(f"   📱 Устройство: {change.device.name}")
        print(f"   🔄 Тип изменения: {change.change_type}")
        print(f"   📊 Статус: {change.device.status}")
        print(f"   🎯 Тип: {change.device.type}")
        print(f"   ⭐ Приоритет: {change.device.priority}")
        
        self.device_changes.append(change)
    
    def on_device_switched(self, from_device, to_device):
        """Callback для переключения устройств"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"\n🔄 [{timestamp}] ПЕРЕКЛЮЧЕНИЕ УСТРОЙСТВА:")
        if from_device:
            print(f"   📤 С: {from_device.name} ({from_device.type})")
        else:
            print(f"   📤 С: Не определено")
        print(f"   📥 На: {to_device.name} ({to_device.type})")
        
        self.device_switches.append((from_device, to_device))
    
    def on_error(self, error):
        """Callback для ошибок"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"\n❌ [{timestamp}] ОШИБКА: {error}")
    
    async def show_initial_status(self):
        """Показать начальный статус"""
        print("\n" + "="*60)
        print("📊 НАЧАЛЬНЫЙ СТАТУС СИСТЕМЫ")
        print("="*60)
        
        try:
            # Получаем доступные устройства
            devices = await self.manager.get_available_devices()
            print(f"📱 Доступно устройств: {len(devices)}")
            
            # Группируем по типам
            output_devices = [d for d in devices if d.type.value == "output"]
            input_devices = [d for d in devices if d.type.value == "input"]
            
            print(f"\n🔊 Устройства вывода ({len(output_devices)}):")
            for device in sorted(output_devices, key=lambda x: x.priority.value):
                status_icon = "✅" if device.status.value == "available" else "❌"
                print(f"   {status_icon} {device.name} (приоритет: {device.priority.value})")
            
            print(f"\n🎤 Устройства ввода ({len(input_devices)}):")
            for device in sorted(input_devices, key=lambda x: x.priority.value):
                status_icon = "✅" if device.status.value == "available" else "❌"
                print(f"   {status_icon} {device.name} (приоритет: {device.priority.value})")
            
            # Получаем текущее устройство
            current_device = await self.manager.get_current_device()
            if current_device:
                print(f"\n🎯 Текущее активное устройство: {current_device.name}")
            else:
                print(f"\n⚠️ Текущее устройство не определено")
            
        except Exception as e:
            print(f"❌ Ошибка получения статуса: {e}")
    
    async def show_current_status(self):
        """Показать текущий статус"""
        print("\n" + "="*60)
        print("📊 ТЕКУЩИЙ СТАТУС СИСТЕМЫ")
        print("="*60)
        
        try:
            # Получаем доступные устройства
            devices = await self.manager.get_available_devices()
            print(f"📱 Доступно устройств: {len(devices)}")
            
            # Группируем по типам
            output_devices = [d for d in devices if d.type.value == "output"]
            input_devices = [d for d in devices if d.type.value == "input"]
            
            print(f"\n🔊 Устройства вывода ({len(output_devices)}):")
            for device in sorted(output_devices, key=lambda x: x.priority.value):
                status_icon = "✅" if device.status.value == "available" else "❌"
                print(f"   {status_icon} {device.name} (приоритет: {device.priority.value})")
            
            print(f"\n🎤 Устройства ввода ({len(input_devices)}):")
            for device in sorted(input_devices, key=lambda x: x.priority.value):
                status_icon = "✅" if device.status.value == "available" else "❌"
                print(f"   {status_icon} {device.name} (приоритет: {device.priority.value})")
            
            # Получаем текущее устройство
            current_device = await self.manager.get_current_device()
            if current_device:
                print(f"\n🎯 Текущее активное устройство: {current_device.name}")
            else:
                print(f"\n⚠️ Текущее устройство не определено")
            
            # Статистика
            runtime = time.time() - self.start_time if self.start_time else 0
            print(f"\n📈 Статистика (время работы: {runtime:.1f}с):")
            print(f"   Изменений устройств: {len(self.device_changes)}")
            print(f"   Переключений: {len(self.device_switches)}")
            
        except Exception as e:
            print(f"❌ Ошибка получения статуса: {e}")
    
    async def start_monitoring(self):
        """Запуск мониторинга"""
        print("🚀 Запускаем мониторинг устройств...")
        
        try:
            # Запускаем менеджер
            await self.manager.start()
            self.running = True
            self.start_time = time.time()
            print("✅ Мониторинг запущен")
            
            # Показываем начальный статус
            await self.show_initial_status()
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка запуска мониторинга: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def stop_monitoring(self):
        """Остановка мониторинга"""
        print("\n🛑 Останавливаем мониторинг...")
        
        try:
        if self.manager and self.running:
                await self.manager.stop()
                self.running = False
                print("✅ Мониторинг остановлен")
            
            # Показываем финальную статистику
            runtime = time.time() - self.start_time if self.start_time else 0
            print(f"\n📊 ФИНАЛЬНАЯ СТАТИСТИКА (время работы: {runtime:.1f}с):")
            print(f"   Изменений устройств: {len(self.device_changes)}")
            print(f"   Переключений: {len(self.device_switches)}")
            
            except Exception as e:
                print(f"❌ Ошибка остановки: {e}")
    
    async def run_live_test(self):
        """Запуск живого теста"""
        print("🎮 ИНТЕРАКТИВНЫЙ ТЕСТ AUDIO DEVICE MANAGER")
        print("="*60)
        print("📋 ИНСТРУКЦИИ:")
        print("1. 🔌 Подключите наушники или другие аудио устройства")
        print("2. 🔌 Отключите устройства")
        print("3. 👀 Наблюдайте за автоматическим переключением")
        print("4. ⌨️  Нажмите Ctrl+C для выхода")
        print("5. 📊 Статус обновляется каждые 10 секунд")
        print("="*60)
        
        # Настройка обработчика сигналов
        def signal_handler(signum, frame):
            print(f"\n🛑 Получен сигнал {signum}, завершаем тест...")
        asyncio.create_task(self.stop_monitoring())
        
        signal.signal(signal.SIGINT, signal_handler)
        
        try:
            # Запускаем мониторинг
            if not await self.start_monitoring():
                return False
            
            # Основной цикл мониторинга - БЕСКОНЕЧНЫЙ
            last_status_time = time.time()
            print("\n🔄 МОНИТОРИНГ ЗАПУЩЕН - ПОДКЛЮЧАЙТЕ/ОТКЛЮЧАЙТЕ УСТРОЙСТВА!")
            print("⌨️  Нажмите Ctrl+C для выхода")
            print("="*60)
            
            while self.running:
                await asyncio.sleep(1)
                
                # Показываем статус каждые 10 секунд
                current_time = time.time()
                if current_time - last_status_time >= 10:
                    await self.show_current_status()
                    last_status_time = current_time
            
            return True
            
        except KeyboardInterrupt:
            print("\n🛑 Тест прерван пользователем")
            await self.stop_monitoring()
            return True
        except Exception as e:
            print(f"❌ Ошибка в тесте: {e}")
            import traceback
            traceback.print_exc()
            await self.stop_monitoring()
            return False

async def main():
    """Основная функция"""
    print("🧪 ТЕСТ В РЕАЛЬНОМ ВРЕМЕНИ - AUDIO DEVICE MANAGER")
    print("="*60)
    
    # Создаем тестер
    tester = LiveAudioDeviceTester()
    
    # Настраиваем
    if not await tester.setup():
        print("❌ Не удалось настроить тестер")
        return False
    
    # Запускаем живой тест
    success = await tester.run_live_test()
    
    if success:
        print("\n🎉 Тест завершен успешно!")
    else:
        print("\n⚠️ Тест завершен с ошибками")
    
    return success

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n🛑 Тест прерван")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        sys.exit(1)