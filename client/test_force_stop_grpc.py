#!/usr/bin/env python3
"""
Тест принудительной остановки gRPC стрима.
Проверяет, что gRPC соединение принудительно закрывается при прерывании.
"""

import asyncio
import time
from rich.console import Console

console = Console()

class MockGrpcClient:
    """Мок gRPC клиента для тестирования"""
    
    def __init__(self):
        self.channel = "mock_channel"
        self.stub = "mock_stub"
        self.audio_player = MockAudioPlayer()
        self.connection_closed = False
        self.state_reset = False
        
    def close_connection(self):
        """Мок метода закрытия соединения"""
        console.print("[blue]🔌 Закрываю gRPC соединение...[/blue]")
        self.connection_closed = True
        self.channel = None
        self.stub = None
        console.print("[green]✅ gRPC соединение закрыто[/green]")
    
    def reset_state(self):
        """Мок метода сброса состояния"""
        console.print("[blue]🔄 Сбрасываю состояние gRPC клиента...[/blue]")
        self.state_reset = True
        console.print("[green]✅ Состояние gRPC клиента сброшено[/green]")

class MockAudioPlayer:
    """Мок аудио плеера для тестирования"""
    
    def __init__(self):
        self.audio_queue = MockQueue()
        self.cleared = False
        self.stopped = False
        
    def clear_all_audio_data(self):
        """Мок метода очистки аудио"""
        console.print("[blue]🧹 Очищаю аудио буферы...[/blue]")
        self.cleared = True
        self.audio_queue.clear()
        console.print("[green]✅ Аудио буферы очищены[/green]")
    
    def force_stop(self):
        """Мок метода принудительной остановки"""
        console.print("[blue]⏹️ Принудительно останавливаю аудио...[/blue]")
        self.stopped = True
        console.print("[green]✅ Аудио принудительно остановлено[/green]")

class MockQueue:
    """Мок очереди для тестирования"""
    
    def __init__(self):
        self.items = [f"item_{i}" for i in range(5)]
    
    def qsize(self):
        return len(self.items)
    
    def empty(self):
        return len(self.items) == 0
    
    def get_nowait(self):
        if self.items:
            return self.items.pop(0)
        raise Exception("Queue empty")
    
    def clear(self):
        self.items.clear()

class MockStateManager:
    """Мок StateManager для тестирования"""
    
    def __init__(self):
        self.grpc_client = MockGrpcClient()
        self.audio_player = self.grpc_client.audio_player
        self.state = "IN_PROCESS"
        self.interrupt_called = False
        
    def _force_stop_grpc_stream(self):
        """Тестируем метод принудительной остановки gRPC стрима"""
        console.print("\n🚨 Тестирую _force_stop_grpc_stream()...")
        
        try:
            # 1️⃣ Принудительно закрываем gRPC соединение
            if hasattr(self, 'grpc_client') and self.grpc_client:
                console.print("   🚨 Принудительно закрываю gRPC соединение...")
                
                # Закрываем соединение
                if hasattr(self.grpc_client, 'close_connection'):
                    self.grpc_client.close_connection()
                    console.print("   ✅ gRPC соединение принудительно закрыто")
                elif hasattr(self.grpc_client, 'channel'):
                    # Закрываем канал
                    try:
                        self.grpc_client.channel = None
                        console.print("   ✅ gRPC канал принудительно закрыт")
                    except Exception as e:
                        console.print(f"   ⚠️ Ошибка закрытия gRPC канала: {e}")
                
                # Сбрасываем состояние клиента
                if hasattr(self.grpc_client, 'reset_state'):
                    self.grpc_client.reset_state()
                    console.print("   ✅ Состояние gRPC клиента сброшено")
                
            # 2️⃣ Принудительно очищаем все буферы
            if hasattr(self, 'audio_player') and self.audio_player:
                console.print("   🚨 Принудительно очищаю все аудио буферы...")
                
                # Очищаем очередь
                if hasattr(self.audio_player, 'audio_queue'):
                    queue_size = self.audio_player.audio_queue.qsize()
                    console.print(f"   📊 Очищаю очередь: {queue_size} элементов")
                    
                    # Принудительно очищаем очередь
                    while not self.audio_player.audio_queue.empty():
                        try:
                            self.audio_player.audio_queue.get_nowait()
                        except:
                            break
                    
                    console.print("   ✅ Очередь принудительно очищена")
                
                # Останавливаем воспроизведение
                if hasattr(self.audio_player, 'force_stop'):
                    self.audio_player.force_stop()
                    console.print("   ✅ Аудио принудительно остановлено")
                elif hasattr(self.audio_player, 'stop'):
                    self.audio_player.stop()
                    console.print("   ✅ Аудио остановлено")
                
                # Очищаем буферы
                if hasattr(self.audio_player, 'clear_all_audio_data'):
                    self.audio_player.clear_all_audio_data()
                    console.print("   ✅ Все аудио буферы очищены")
            
            console.print("   ✅ _force_stop_grpc_stream завершен")
            
        except Exception as e:
            console.print(f"   ❌ Ошибка в _force_stop_grpc_stream: {e}")
    
    async def _cancel_tasks(self):
        """Тестируем метод отмены задач"""
        console.print("\n🚨 Тестирую _cancel_tasks()...")
        
        start_time = time.time()
        
        # 1️⃣ ПРИНУДИТЕЛЬНО ОСТАНАВЛИВАЕМ gRPC СТРИМ
        grpc_start = time.time()
        self._force_stop_grpc_stream()
        grpc_time = (time.time() - grpc_start) * 1000
        console.print(f"   ✅ _force_stop_grpc_stream: {grpc_time:.1f}ms")
        
        # 2️⃣ Отменяем asyncio задачи (мок)
        tasks_start = time.time()
        console.print("   🚨 Отменяю asyncio задачи...")
        
        # Имитируем отмену задач
        await asyncio.sleep(0.01)  # Имитируем время отмены
        
        tasks_time = (time.time() - tasks_start) * 1000
        console.print(f"   ✅ Отмена задач завершена: {tasks_time:.1f}ms")
        
        # 3️⃣ Очищаем ссылки на задачи
        console.print("   🔄 Очищаю ссылки на задачи...")
        
        total_time = (time.time() - start_time) * 1000
        console.print(f"   ⏱️ Общее время _cancel_tasks: {total_time:.1f}ms")
    
    async def test_interruption_flow(self):
        """Тестируем полный поток прерывания"""
        console.print("\n🧪 Тестирую полный поток прерывания...")
        
        # Симулируем прерывание
        console.print("🔇 Пользователь нажимает пробел...")
        
        # 1️⃣ Отменяем задачи
        await self._cancel_tasks()
        
        # 2️⃣ Проверяем результат
        console.print("\n📊 Результаты тестирования:")
        console.print(f"   🔌 gRPC соединение закрыто: {self.grpc_client.connection_closed}")
        console.print(f"   🔄 Состояние gRPC сброшено: {self.grpc_client.state_reset}")
        console.print(f"   🧹 Аудио буферы очищены: {self.audio_player.cleared}")
        console.print(f"   ⏹️ Аудио остановлено: {self.audio_player.stopped}")
        console.print(f"   📦 Очередь пуста: {self.audio_player.audio_queue.empty()}")
        
        # 3️⃣ Оценка
        success = all([
            self.grpc_client.connection_closed,
            self.grpc_client.state_reset,
            self.audio_player.cleared,
            self.audio_player.stopped,
            self.audio_player.audio_queue.empty()
        ])
        
        if success:
            console.print("\n🎯 ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
            console.print("✅ Принудительная остановка gRPC стрима работает корректно")
        else:
            console.print("\n❌ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОШЛИ!")
            console.print("⚠️ Есть проблемы с принудительной остановкой")

async def main():
    """Основная функция тестирования"""
    console.print("🚀 Тест принудительной остановки gRPC стрима")
    console.print("=" * 50)
    
    # Создаем мок StateManager
    state_manager = MockStateManager()
    
    # Запускаем тест
    await state_manager.test_interruption_flow()
    
    console.print("\n" + "=" * 50)
    console.print("🏁 Тестирование завершено")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n�� Выход из теста.")
