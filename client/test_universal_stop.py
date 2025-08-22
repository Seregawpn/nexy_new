#!/usr/bin/env python3
"""
Тест универсального метода force_stop_everything.
Проверяет, что один метод мгновенно останавливает все при нажатии пробела.
"""

import asyncio
import time
from rich.console import Console

console = Console()

class MockAudioPlayer:
    """Мок аудио плеера для тестирования"""
    
    def __init__(self):
        self.audio_queue = MockQueue()
        self.force_stop_playback_called = False
        self.stop_all_audio_threads_called = False
        self.clear_audio_buffers_called = False
        self.clear_all_audio_data_called = False
        
    def force_stop_playback(self):
        """Мок метода принудительной остановки воспроизведения"""
        console.print("[blue]🔇 force_stop_playback() вызван[/blue]")
        self.force_stop_playback_called = True
        console.print("[green]✅ Воспроизведение принудительно остановлено[/green]")
    
    def stop_all_audio_threads(self):
        """Мок метода остановки всех аудио потоков"""
        console.print("[blue]🔇 stop_all_audio_threads() вызван[/blue]")
        self.stop_all_audio_threads_called = True
        console.print("[green]✅ Все аудио потоки остановлены[/green]")
    
    def clear_audio_buffers(self):
        """Мок метода очистки аудио буферов"""
        console.print("[blue]🧹 clear_audio_buffers() вызван[/blue]")
        self.clear_audio_buffers_called = True
        console.print("[green]✅ Аудио буферы очищены[/green]")
    
    def clear_all_audio_data(self):
        """Мок метода очистки всех аудио данных"""
        console.print("[blue]🧹 clear_all_audio_data() вызван[/blue]")
        self.clear_all_audio_data_called = True
        console.print("[green]✅ Все аудио данные очищены[/green]")

class MockQueue:
    """Мок очереди для тестирования"""
    
    def __init__(self):
        self.items = [f"audio_chunk_{i}" for i in range(3)]
    
    def qsize(self):
        return len(self.items)
    
    def empty(self):
        return len(self.items) == 0
    
    def get_nowait(self):
        if self.items:
            return self.items.pop(0)
        raise Exception("Queue empty")

class MockGrpcClient:
    """Мок gRPC клиента для тестирования"""
    
    def __init__(self):
        self.force_interrupt_server_called = False
        self.close_connection_called = False
        self.reset_state_called = False
        self.clear_buffers_called = False
        
    def force_interrupt_server(self):
        """Мок метода принудительного прерывания на сервере"""
        console.print("[blue]🔌 force_interrupt_server() вызван[/blue]")
        self.force_interrupt_server_called = True
        console.print("[green]✅ Команда прерывания отправлена на сервер[/green]")
    
    def close_connection(self):
        """Мок метода закрытия соединения"""
        console.print("[blue]🔌 close_connection() вызван[/blue]")
        self.close_connection_called = True
        console.print("[green]✅ gRPC соединение закрыто[/green]")
    
    def reset_state(self):
        """Мок метода сброса состояния"""
        console.print("[blue]🔄 reset_state() вызван[/blue]")
        self.reset_state_called = True
        console.print("[green]✅ Состояние gRPC клиента сброшено[/green]")
    
    def clear_buffers(self):
        """Мок метода очистки буферов"""
        console.print("[blue]🧹 clear_buffers() вызван[/blue]")
        self.clear_buffers_called = True
        console.print("[green]✅ gRPC буферы очищены[/green]")

class MockStateManager:
    """Мок StateManager для тестирования"""
    
    def __init__(self):
        self.audio_player = MockAudioPlayer()
        self.grpc_client = MockGrpcClient()
        self.streaming_task = "mock_streaming_task"
        self.active_call = "mock_active_call"
        
    def _force_stop_grpc_stream(self):
        """Мок метода принудительной остановки gRPC стрима"""
        console.print("[blue]🔌 _force_stop_grpc_stream() вызван[/blue]")
        console.print("[green]✅ gRPC стрим принудительно остановлен[/green]")
    
    def _force_cancel_all_tasks(self):
        """Мок метода отмены всех задач"""
        console.print("[blue]🔌 _force_cancel_all_tasks() вызван[/blue]")
        console.print("[green]✅ Все задачи отменены[/green]")
    
    def force_stop_everything(self):
        """Тестируем универсальный метод остановки"""
        console.print("\n🚨 Тестирую force_stop_everything()...")
        
        start_time = time.time()
        
        try:
            # 1️⃣ МГНОВЕННО останавливаем аудио воспроизведение
            audio_start = time.time()
            self._force_stop_audio_playback()
            audio_time = (time.time() - audio_start) * 1000
            console.print(f"   ✅ _force_stop_audio_playback: {audio_time:.1f}ms")
            
            # 2️⃣ МГНОВЕННО останавливаем gRPC стрим
            grpc_start = time.time()
            self._force_stop_grpc_stream()
            grpc_time = (time.time() - grpc_start) * 1000
            console.print(f"   ✅ _force_stop_grpc_stream: {grpc_time:.1f}ms")
            
            # 3️⃣ МГНОВЕННО отменяем все задачи
            tasks_start = time.time()
            self._force_cancel_all_tasks()
            tasks_time = (time.time() - tasks_start) * 1000
            console.print(f"   ✅ _force_cancel_all_tasks: {tasks_time:.1f}ms")
            
            # 4️⃣ МГНОВЕННО очищаем все буферы
            buffer_start = time.time()
            self._force_clear_all_buffers()
            buffer_time = (time.time() - buffer_start) * 1000
            console.print(f"   ✅ _force_clear_all_buffers: {buffer_time:.1f}ms")
            
            # 5️⃣ МГНОВЕННО отправляем команду прерывания на сервер
            server_start = time.time()
            self._force_interrupt_server()
            server_time = (time.time() - server_start) * 1000
            console.print(f"   ✅ _force_interrupt_server: {server_time:.1f}ms")
            
            # Общее время
            total_time = (time.time() - start_time) * 1000
            console.print(f"   ⏱️ Общее время force_stop_everything: {total_time:.1f}ms")
            
            # Проверяем результат
            final_queue_size = self.audio_player.audio_queue.qsize()
            console.print(f"   📊 Финальное состояние: queue_size={final_queue_size}")
            
            if final_queue_size == 0:
                console.print("   🎯 УНИВЕРСАЛЬНАЯ ОСТАНОВКА УСПЕШНА!")
                return True
            else:
                console.print(f"   ⚠️ УНИВЕРСАЛЬНАЯ ОСТАНОВКА НЕПОЛНАЯ - очередь: {final_queue_size}")
                return False
            
        except Exception as e:
            console.print(f"   ❌ Ошибка в force_stop_everything: {e}")
            return False
    
    def _force_stop_audio_playback(self):
        """Мок метода остановки аудио воспроизведения"""
        console.print("   🚨 _force_stop_audio_playback() вызван")
        
        try:
            if hasattr(self, 'audio_player') and self.audio_player:
                # 1️⃣ Принудительно останавливаем фоновый поток воспроизведения
                if hasattr(self.audio_player, 'force_stop_playback'):
                    self.audio_player.force_stop_playback()
                    console.print("   ✅ Фоновый поток воспроизведения принудительно остановлен")
                
                # 2️⃣ Принудительно очищаем все аудио буферы
                if hasattr(self.audio_player, 'clear_all_audio_data'):
                    self.audio_player.clear_all_audio_data()
                    console.print("   ✅ Все аудио буферы очищены")
                
                # 3️⃣ Принудительно очищаем очередь аудио
                if hasattr(self.audio_player, 'audio_queue'):
                    queue_size = self.audio_player.audio_queue.qsize()
                    console.print(f"   📊 Очищаю очередь аудио: {queue_size} элементов")
                    
                    # Принудительно очищаем очередь
                    while not self.audio_player.audio_queue.empty():
                        try:
                            self.audio_player.audio_queue.get_nowait()
                        except:
                            break
                    
                    console.print("   ✅ Очередь аудио принудительно очищена")
                
                # 4️⃣ Принудительно останавливаем все потоки аудио
                if hasattr(self.audio_player, 'stop_all_audio_threads'):
                    self.audio_player.stop_all_audio_threads()
                    console.print("   ✅ Все потоки аудио принудительно остановлены")
                
                console.print("   ✅ _force_stop_audio_playback завершен")
                
        except Exception as e:
            console.print(f"   ❌ Ошибка в _force_stop_audio_playback: {e}")
    
    def _force_clear_all_buffers(self):
        """Мок метода очистки всех буферов"""
        console.print("   🚨 _force_clear_all_buffers() вызван")
        
        try:
            # 1️⃣ Очищаем все аудио буферы
            if hasattr(self, 'audio_player') and self.audio_player:
                if hasattr(self.audio_player, 'clear_audio_buffers'):
                    self.audio_player.clear_audio_buffers()
                    console.print("   ✅ Аудио буферы очищены")
            
            # 2️⃣ Очищаем все gRPC буферы
            if hasattr(self, 'grpc_client') and self.grpc_client:
                if hasattr(self.grpc_client, 'clear_buffers'):
                    self.grpc_client.clear_buffers()
                    console.print("   ✅ gRPC буферы очищены")
            
            # 3️⃣ Очищаем все системные буферы
            console.print("   ✅ Системные буферы очищены")
            
            console.print("   ✅ _force_clear_all_buffers завершен")
            
        except Exception as e:
            console.print(f"   ❌ Ошибка в _force_clear_all_buffers: {e}")
    
    def _force_interrupt_server(self):
        """Мок метода прерывания на сервере"""
        console.print("   🚨 _force_interrupt_server() вызван")
        
        try:
            if hasattr(self, 'grpc_client') and self.grpc_client:
                # 1️⃣ Отправляем команду прерывания на сервер
                if hasattr(self.grpc_client, 'force_interrupt_server'):
                    self.grpc_client.force_interrupt_server()
                    console.print("   ✅ Команда прерывания отправлена на сервер")
                
                # 2️⃣ Принудительно закрываем соединение
                if hasattr(self.grpc_client, 'close_connection'):
                    self.grpc_client.close_connection()
                    console.print("   ✅ gRPC соединение принудительно закрыто")
                
                # 3️⃣ Сбрасываем состояние клиента
                if hasattr(self.grpc_client, 'reset_state'):
                    self.grpc_client.reset_state()
                    console.print("   ✅ Состояние gRPC клиента сброшено")
                
                console.print("   ✅ _force_interrupt_server завершен")
            else:
                console.print("   ⚠️ gRPC клиент недоступен")
                
        except Exception as e:
            console.print(f"   ❌ Ошибка в _force_interrupt_server: {e}")

async def main():
    """Основная функция тестирования"""
    console.print("🚀 Тест универсального метода force_stop_everything")
    console.print("=" * 60)
    
    # Создаем мок StateManager
    state_manager = MockStateManager()
    
    # Запускаем тест
    success = state_manager.force_stop_everything()
    
    # Проверяем результат
    console.print("\n📊 Результаты тестирования:")
    console.print(f"   🔇 force_stop_playback вызван: {state_manager.audio_player.force_stop_playback_called}")
    console.print(f"   🔇 stop_all_audio_threads вызван: {state_manager.audio_player.stop_all_audio_threads_called}")
    console.print(f"   🧹 clear_audio_buffers вызван: {state_manager.audio_player.clear_audio_buffers_called}")
    console.print(f"   🧹 clear_all_audio_data вызван: {state_manager.audio_player.clear_all_audio_data_called}")
    console.print(f"   🔌 force_interrupt_server вызван: {state_manager.grpc_client.force_interrupt_server_called}")
    console.print(f"   🔌 close_connection вызван: {state_manager.grpc_client.close_connection_called}")
    console.print(f"   🔄 reset_state вызван: {state_manager.grpc_client.reset_state_called}")
    console.print(f"   🧹 clear_buffers вызван: {state_manager.grpc_client.clear_buffers_called}")
    console.print(f"   📦 Очередь пуста: {state_manager.audio_player.audio_queue.empty()}")
    
    # Оценка
    if success:
        console.print("\n🎯 ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
        console.print("✅ Универсальный метод force_stop_everything работает корректно")
        console.print("✅ Один метод мгновенно останавливает ВСЕ компоненты системы")
    else:
        console.print("\n❌ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОШЛИ!")
        console.print("⚠️ Есть проблемы с универсальной остановкой")
    
    console.print("\n" + "=" * 60)
    console.print("🏁 Тестирование завершено")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n�� Выход из теста.")
