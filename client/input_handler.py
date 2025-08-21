import asyncio
import time
from pynput import keyboard
from threading import Thread, Timer
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
        self.short_press_threshold = 0.3   # Порог для коротких нажатий (300ms - оптимальное время)
        self.space_pressed = False
        self.last_event_time = 0
        self.event_cooldown = 0.1
        self.recording_started = False
        self.recording_timer = None # Таймер для отложенного старта записи

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
                return
                
            # Устанавливаем флаги
            self.space_pressed = True
            self.press_time = current_time
            self.last_event_time = current_time
            
            # 1. ВСЕГДА немедленно отправляем прерывание
            self.loop.call_soon_threadsafe(self.queue.put_nowait, "interrupt_or_cancel")
            console.print("[bold red]🔇 ПРОБЕЛ НАЖАТ - МГНОВЕННОЕ ПРЕРЫВАНИЕ РЕЧИ![/bold red]")
            
            # 2. Отменяем предыдущий таймер, если он есть
            if self.recording_timer:
                self.recording_timer.cancel()

            # 3. УМЕНЬШАЕМ задержку с 50ms до 10ms для мгновенного отклика!
            def start_recording_action():
                # Эта функция будет вызвана, если отпускание не произошло в течение 10 мс
                self.loop.call_soon_threadsafe(self.queue.put_nowait, "start_recording")
                console.print("[bold green]🎤 МИКРОФОН АКТИВИРОВАН - начинаю запись команды![/bold green]")

            # Задержка в 10мс - практически незаметна для пользователя, но достаточна для отмены
            self.recording_timer = Timer(0.01, start_recording_action)
            self.recording_timer.start()

    def on_release(self, key):
        """Обрабатывает отпускание клавиши"""
        if key == keyboard.Key.space and self.space_pressed:
            current_time = time.time()
            
            # Проверяем cooldown для предотвращения множественных событий
            if current_time - self.last_event_time < self.event_cooldown:
                return
                
            # Сбрасываем флаг нажатия
            self.space_pressed = False
            
            # Отменяем таймер, если он еще не сработал
            if self.recording_timer:
                self.recording_timer.cancel()
            
            # Вычисляем длительность нажатия
            duration = current_time - self.press_time
            self.press_time = None
            self.last_event_time = current_time

            # ПРОСТАЯ ЛОГИКА: определяем действие по длительности
            if duration >= self.short_press_threshold:
                # ДЛИННОЕ нажатие: таймер уже отправил start_recording, теперь отправляем stop_recording
                console.print(f"⏹️ Длинное нажатие ({duration:.2f}s) - останавливаю запись и отправляю команду")
                self.loop.call_soon_threadsafe(self.queue.put_nowait, "stop_recording")
            else:
                # КОРОТКОЕ нажатие: таймер был отменен, start_recording не был отправлен.
                # Прерывание уже было отправлено в on_press. Больше ничего делать не нужно.
                console.print(f"🔇 Короткое нажатие ({duration:.2f}s) - только прерывание, запись отменена")
            
            console.print("🔄 Готов к новым событиям")

async def main_test():
    """Функция для тестирования InputHandler"""
    print("🧪 Тест упрощенного InputHandler:")
    print("• Зажмите пробел → СРАЗУ активируется микрофон")
    print("• Удерживайте пробел → продолжается запись")
    print("• Отпустите пробел → останавливается запись + отправка команды")
    print("• Короткое нажатие → прерывание речи ассистента")
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

