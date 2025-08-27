import asyncio
import time
from pynput import keyboard
from threading import Thread
from rich.console import Console

console = Console()

class InputHandler:
    """
    Простой и надежный обработчик клавиатуры для push-to-talk.
    Отправляет события в очередь, не управляет состоянием.
    """
    
    def __init__(self, loop: asyncio.AbstractEventLoop, queue: asyncio.Queue):
        self.loop = loop
        self.queue = queue
        self.press_time = None
        self.short_press_threshold = 0.3   # Порог для коротких нажатий (300ms)
        self.space_pressed = False
        self.last_event_time = 0
        self.event_cooldown = 0.1
        self.recording_started = False
        
        # Флаг для отслеживания состояния прерывания
        self.interrupting = False
        # 🆕 Флаг: была ли команда уже обработана в deactivate_microphone
        self.command_processed = False

        # Запускаем listener в отдельном потоке
        self.listener_thread = Thread(target=self._run_listener, daemon=True)
        self.listener_thread.start()

    def _run_listener(self):
        """Запускает listener для клавиатуры"""
        with keyboard.Listener(on_press=self.on_press, on_release=self.on_release) as listener:
            listener.join()

    def on_press(self, key):
        """Обрабатывает нажатие клавиши"""
        if key == keyboard.Key.space and not self.space_pressed:
            current_time = time.time()
            
            # Проверяем cooldown для предотвращения множественных событий
            if current_time - self.last_event_time < self.event_cooldown:
                console.print(f"[dim]⏰ Cooldown активен: {self.event_cooldown - (current_time - self.last_event_time):.3f}s[/dim]")
                return
                
            # Устанавливаем флаг нажатия и время
            self.space_pressed = True
            self.press_time = current_time
            self.last_event_time = current_time
            
            # 1. УСТАНАВЛИВАЕМ ФЛАГ ПРЕРЫВАНИЯ
            self.interrupting = True
            console.print(f"[bold red]🔇 ПРОБЕЛ НАЖАТ - МГНОВЕННОЕ ПРЕРЫВАНИЕ РЕЧИ! (время: {current_time:.3f})[/bold red]")
            console.print(f"[dim]🔍 Флаг interrupting установлен: {self.interrupting}[/dim]")
            
            # 2. ОТПРАВЛЯЕМ ТОЛЬКО ПРЕРЫВАНИЕ - микрофон активируется автоматически!
            self.loop.call_soon_threadsafe(self.queue.put_nowait, "interrupt_or_cancel")
            console.print(f"[dim]📤 Событие interrupt_or_cancel отправлено в очередь[/dim]")
            
            # 🚨 УБИРАЕМ start_recording - микрофон активируется автоматически в handle_interrupt_or_cancel!
            console.print(f"[dim]🎤 Микрофон будет активирован АВТОМАТИЧЕСКИ после прерывания![/dim]")

    def on_release(self, key):
        """Обрабатывает отпускание клавиши"""
        if key == keyboard.Key.space and self.space_pressed:
            current_time = time.time()
            
            # Проверяем cooldown для предотвращения множественных событий
            if current_time - self.last_event_time < self.event_cooldown:
                console.print(f"[dim]⏰ Cooldown активен при отпускании: {self.event_cooldown - (current_time - self.last_event_time):.3f}s[/dim]")
                return
                
            # Сбрасываем флаг нажатия
            self.space_pressed = False
            console.print(f"[dim]🔍 Флаг space_pressed сброшен в {current_time:.3f}[/dim]")
            
            # Вычисляем длительность нажатия
            duration = current_time - self.press_time
            self.press_time = None
            self.last_event_time = current_time
            console.print(f"[dim]📊 Длительность нажатия: {duration:.3f}s[/dim]")

            # 🚨 НОВАЯ ЛОГИКА: при отпускании пробела ВСЕГДА деактивируем микрофон
            console.print(f"🔇 Пробел отпущен - деактивирую микрофон и возвращаюсь в SLEEPING")
            
            # Отправляем событие для деактивации микрофона
            self.loop.call_soon_threadsafe(self.queue.put_nowait, "deactivate_microphone")
            console.print(f"[dim]📤 Событие deactivate_microphone отправлено в очередь[/dim]")
            
            # Если было длинное нажатие, также отправляем команду на обработку
            if duration >= self.short_press_threshold:
                console.print(f"⏹️ Длинное нажатие ({duration:.2f}s) - команда будет обработана")
                # 🚨 НЕ отправляем stop_recording - команда будет обработана в deactivate_microphone
                console.print(f"[dim]📤 Команда будет обработана в deactivate_microphone[/dim]")
            else:
                console.print(f"🔇 Короткое нажатие ({duration:.2f}s) - только прерывание")
                console.print(f"[dim]🔍 Длительность {duration:.3f}s < {self.short_press_threshold}s - короткое нажатие[/dim]")
            
            # СБРАСЫВАЕМ ФЛАГ ПРЕРЫВАНИЯ
            console.print(f"[dim]🔍 Флаг interrupting ДО сброса: {self.interrupting}[/dim]")
            self.interrupting = False
            console.print(f"[dim]🔍 Флаг interrupting ПОСЛЕ сброса: {self.interrupting}[/dim]")
            console.print("🔄 Готов к новым событиям")

    def reset_interrupt_flag(self):
        """Сбрасывает флаг прерывания - вызывается из StateManager"""
        current_time = time.time()
        console.print(f"[dim]🔍 reset_interrupt_flag() вызван в {current_time:.3f}[/dim]")
        console.print(f"[dim]🔍 Флаг interrupting ДО сброса: {self.interrupting}[/dim]")
        self.interrupting = False
        console.print(f"[dim]🔍 Флаг interrupting ПОСЛЕ сброса: {self.interrupting}[/dim]")
        console.print("[dim]🔄 Флаг прерывания сброшен[/dim]")
    
    def reset_command_processed_flag(self):
        """Сбрасывает флаг обработки команды - вызывается при начале новой записи"""
        current_time = time.time()
        console.print(f"[dim]🔍 reset_command_processed_flag() вызван в {current_time:.3f}[/dim]")
        console.print(f"[dim]🔍 Флаг command_processed ДО сброса: {self.command_processed}[/dim]")
        self.command_processed = False
        console.print(f"[dim]🔍 Флаг command_processed ПОСЛЕ сброса: {self.command_processed}[/dim]")
        console.print("[dim]🔄 Флаг обработки команды сброшен[/dim]")
    
    def get_interrupt_status(self):
        """Возвращает текущий статус прерывания"""
        return self.interrupting

async def main_test():
    """Функция для тестирования InputHandler"""
    print("🧪 Тест упрощенного InputHandler:")
    print("• Зажмите пробел → СРАЗУ прерывание + автоматическая активация микрофона")
    print("• Удерживайте пробел → продолжается запись")
    print("• Отпустите пробел → останавливается запись + отправка команды")
    print("• Короткое нажатие → только прерывание речи ассистента")
    print("• Нажмите Ctrl+C для выхода")
    
    event_queue = asyncio.Queue()
    loop = asyncio.get_running_loop()
    
    # Инициализируем обработчик
    InputHandler(loop, event_queue)
    
    while True:
        event = await event_queue.get()
        print(f"📡 Событие: {event}")
        if event == "exit":
            break

if __name__ == "__main__":
    try:
        asyncio.run(main_test())
    except KeyboardInterrupt:
        print("\n👋 Выход.")

