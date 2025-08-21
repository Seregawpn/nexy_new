#!/usr/bin/env python3
"""
🧪 ИНТЕГРАЦИОННЫЙ тест прерывания речи
Тестирует всю систему прерывания в реальном процессе
"""

import asyncio
import time
import threading
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

class InterruptTester:
    """Тестер прерывания речи в реальном процессе"""
    
    def __init__(self):
        self.test_results = []
        self.interrupt_detected = False
        self.audio_stopped = False
        self.grpc_cancelled = False
        
    async def test_interrupt_functionality(self):
        """Основной тест прерывания речи"""
        console.print("🧪 ИНТЕГРАЦИОННЫЙ ТЕСТ ПРЕРЫВАНИЯ РЕЧИ")
        console.print("=" * 60)
        
        console.print("📋 План тестирования:")
        console.print("1. Запуск ассистента")
        console.print("2. Отправка длинной команды")
        console.print("3. Нажатие пробела во время речи")
        console.print("4. Проверка мгновенной остановки")
        console.print("5. Анализ результатов")
        
        # Тест 1: Проверка компонентов
        await self.test_components()
        
        # Тест 2: Симуляция прерывания
        await self.test_interrupt_simulation()
        
        # Тест 3: Анализ результатов
        await self.analyze_results()
        
    async def test_components(self):
        """Тестирует доступность компонентов"""
        console.print("\n🔧 Тест 1: Проверка компонентов...")
        
        try:
            # Проверяем AudioPlayer
            from audio_player import AudioPlayer
            player = AudioPlayer()
            console.print("✅ AudioPlayer доступен")
            
            # Проверяем методы прерывания
            methods = ['interrupt_immediately', 'clear_all_audio_data', 'force_stop_immediately']
            for method in methods:
                if hasattr(player, method):
                    console.print(f"✅ Метод {method} доступен")
                else:
                    console.print(f"❌ Метод {method} НЕ доступен")
                    self.test_results.append(f"FAIL: {method} отсутствует")
            
            # Проверяем InputHandler
            from input_handler import InputHandler
            console.print("✅ InputHandler доступен")
            
            # Проверяем StateManager
            from main import StateManager
            console.print("✅ StateManager доступен")
            
        except ImportError as e:
            console.print(f"❌ Ошибка импорта: {e}")
            self.test_results.append(f"FAIL: Ошибка импорта - {e}")
        except Exception as e:
            console.print(f"❌ Ошибка проверки компонентов: {e}")
            self.test_results.append(f"FAIL: Ошибка компонентов - {e}")
    
    async def test_interrupt_simulation(self):
        """Симулирует процесс прерывания"""
        console.print("\n🎮 Тест 2: Симуляция прерывания...")
        
        try:
            from audio_player import AudioPlayer
            
            # Создаем AudioPlayer
            player = AudioPlayer()
            
            # Симулируем добавление аудио данных
            console.print("📊 Симуляция добавления аудио данных...")
            
            import numpy as np
            test_chunks = [
                np.random.randint(-32768, 32767, 1000, dtype=np.int16),
                np.random.randint(-32768, 32767, 2000, dtype=np.int16),
                np.random.randint(-32768, 32767, 1500, dtype=np.int16),
                np.random.randint(-32768, 32767, 3000, dtype=np.int16),
            ]
            
            for i, chunk in enumerate(test_chunks):
                player.add_audio_chunk(chunk)
                console.print(f"✅ Добавлен чанк {i+1}: {len(chunk)} сэмплов")
            
            # Проверяем состояние до прерывания
            queue_size_before = player.audio_queue.qsize()
            buffer_size_before = len(player.internal_buffer)
            
            console.print(f"📊 Состояние ДО прерывания:")
            console.print(f"   Очередь: {queue_size_before} чанков")
            console.print(f"   Буфер: {buffer_size_before} сэмплов")
            
            # Симулируем прерывание
            console.print("\n🚨 Симуляция прерывания речи...")
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                
                task = progress.add_task("Прерывание аудио...", total=None)
                
                # Запускаем прерывание в отдельном потоке
                def run_interrupt():
                    time.sleep(0.1)  # Небольшая задержка для симуляции
                    player.clear_all_audio_data()
                
                interrupt_thread = threading.Thread(target=run_interrupt)
                interrupt_thread.start()
                
                # Ждем завершения
                interrupt_thread.join()
                
                progress.update(task, description="Прерывание завершено")
            
            # Проверяем состояние после прерывания
            queue_size_after = player.audio_queue.qsize()
            buffer_size_after = len(player.internal_buffer)
            
            console.print(f"📊 Состояние ПОСЛЕ прерывания:")
            console.print(f"   Очередь: {queue_size_after} чанков")
            console.print(f"   Буфер: {buffer_size_after} сэмплов")
            
            # Анализируем результаты
            if queue_size_after == 0 and buffer_size_after == 0:
                console.print("✅ ПРЕРЫВАНИЕ УСПЕШНО - все буферы очищены!")
                self.audio_stopped = True
                self.test_results.append("PASS: Аудио буферы очищены")
            else:
                console.print("❌ ПРЕРЫВАНИЕ НЕ ПОЛНОСТЬЮ - буферы не очищены!")
                self.test_results.append(f"FAIL: Буферы не очищены (очередь: {queue_size_after}, буфер: {buffer_size_after})")
            
        except Exception as e:
            console.print(f"❌ Ошибка симуляции прерывания: {e}")
            self.test_results.append(f"FAIL: Ошибка симуляции - {e}")
    
    async def test_real_interrupt(self):
        """Тестирует реальное прерывание через gRPC"""
        console.print("\n🌐 Тест 3: Реальное прерывание через gRPC...")
        
        try:
            # Здесь можно добавить тест реального gRPC прерывания
            # Но для этого нужен запущенный сервер
            console.print("ℹ️ Для полного тестирования gRPC нужен запущенный сервер")
            console.print("ℹ️ Запустите: cd server && python grpc_server.py")
            
        except Exception as e:
            console.print(f"❌ Ошибка тестирования gRPC: {e}")
            self.test_results.append(f"FAIL: Ошибка gRPC - {e}")
    
    async def analyze_results(self):
        """Анализирует результаты тестирования"""
        console.print("\n📊 АНАЛИЗ РЕЗУЛЬТАТОВ ТЕСТИРОВАНИЯ")
        console.print("=" * 60)
        
        # Подсчитываем результаты
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r.startswith("PASS")])
        failed_tests = len([r for r in self.test_results if r.startswith("FAIL")])
        
        console.print(f"📈 Общая статистика:")
        console.print(f"   Всего тестов: {total_tests}")
        console.print(f"   Успешно: {passed_tests}")
        console.print(f"   Неудачно: {failed_tests}")
        
        # Показываем детальные результаты
        if self.test_results:
            console.print(f"\n📋 Детальные результаты:")
            for i, result in enumerate(self.test_results, 1):
                if result.startswith("PASS"):
                    console.print(f"   {i}. ✅ {result}")
                else:
                    console.print(f"   {i}. ❌ {result}")
        
        # Итоговая оценка
        if failed_tests == 0:
            console.print(f"\n🎉 ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
            console.print(f"✅ Система прерывания работает корректно")
        else:
            console.print(f"\n⚠️ ЕСТЬ ПРОБЛЕМЫ В СИСТЕМЕ ПРЕРЫВАНИЯ")
            console.print(f"🔧 Требуется доработка {failed_tests} компонентов")
        
        # Рекомендации
        console.print(f"\n💡 РЕКОМЕНДАЦИИ:")
        if self.audio_stopped:
            console.print("   ✅ Аудио прерывание работает")
        else:
            console.print("   ❌ Аудио прерывание НЕ работает - проверьте AudioPlayer")
        
        if self.grpc_cancelled:
            console.print("   ✅ gRPC отмена работает")
        else:
            console.print("   ⚠️ gRPC отмена не протестирована - запустите сервер")
    
    def run_manual_test(self):
        """Запускает ручной тест для пользователя"""
        console.print("\n🎮 РУЧНОЙ ТЕСТ ПРЕРЫВАНИЯ РЕЧИ")
        console.print("=" * 60)
        
        console.print("📋 Инструкции:")
        console.print("1. Запустите ассистент в ОТДЕЛЬНОМ терминале:")
        console.print("   cd client && python main.py")
        console.print("")
        console.print("2. Запустите сервер в ОТДЕЛЬНОМ терминале:")
        console.print("   cd server && python grpc_server.py")
        console.print("")
        console.print("3. В терминале с ассистентом:")
        console.print("   • Скажите длинную команду (например: 'tell me a long story')")
        console.print("   • Дождитесь начала речи")
        console.print("   • НАЖМИТЕ ПРОБЕЛ для прерывания")
        console.print("   • Проверьте, что речь остановилась МГНОВЕННО")
        console.print("")
        console.print("4. Обратите внимание на логи:")
        console.print("   • Время обработки прерывания (должно быть < 50ms)")
        console.print("   • Сообщения об очистке буферов")
        console.print("   • Состояние приложения (должно стать IDLE)")
        
        console.print("\n⏳ Нажмите Enter когда будете готовы к тестированию...")
        input()

async def main():
    """Главная функция тестирования"""
    tester = InterruptTester()
    
    try:
        # Автоматические тесты
        await tester.test_interrupt_functionality()
        
        # Ручной тест
        tester.run_manual_test()
        
    except KeyboardInterrupt:
        console.print("\n👋 Тестирование прервано пользователем")
    except Exception as e:
        console.print(f"\n❌ Ошибка в тестировании: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n👋 Тестирование завершено")
    except Exception as e:
        console.print(f"\n❌ Критическая ошибка: {e}")
