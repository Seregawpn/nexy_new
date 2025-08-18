import asyncio
import time
from pynput import keyboard
from threading import Thread

class InputHandler:
    """
    Обрабатывает глобальные нажатия клавиш для push-to-talk логики:
    - Зажатие пробела = активация микрофона
    - Отпускание пробела = остановка записи + отправка команды
    - Короткое нажатие = прерывание речи ассистента
    """
    def __init__(self, loop: asyncio.AbstractEventLoop, queue: asyncio.Queue):
        self.loop = loop
        self.queue = queue
        self.press_time = None
        self.short_press_threshold = 0.15  # Уменьшаем порог для более точного определения коротких нажатий
        self.space_pressed = False
        self.recording_started = False
        self.last_event_time = 0  # Добавляем отслеживание времени последнего события
        self.event_cooldown = 0.1  # Минимальный интервал между событиями (100ms)

        # Запускаем listener в отдельном потоке
        self.listener_thread = Thread(target=self._run_listener, daemon=True)
        self.listener_thread.start()

    def _run_listener(self):
        with keyboard.Listener(on_press=self.on_press, on_release=self.on_release) as listener:
            listener.join()

    def on_press(self, key):
        if key == keyboard.Key.space and not self.space_pressed:
            current_time = time.time()
            
            # Проверяем cooldown для предотвращения множественных событий
            if current_time - self.last_event_time < self.event_cooldown:
                return
                
            self.space_pressed = True
            self.press_time = current_time
            self.last_event_time = current_time
            
            # СРАЗУ при зажатии пробела активируем микрофон
            if not self.recording_started:
                self.recording_started = True
                self.loop.call_soon_threadsafe(self.queue.put_nowait, "start_recording")
                print("🎤 Микрофон активирован (пробел зажат)")

    def on_release(self, key):
        if key == keyboard.Key.space and self.space_pressed:
            current_time = time.time()
            
            # Проверяем cooldown для предотвращения множественных событий
            if current_time - self.last_event_time < self.event_cooldown:
                return
                
            self.space_pressed = False
            duration = current_time - self.press_time
            self.press_time = None
            self.last_event_time = current_time
            
            # Сбрасываем флаг, так как клавиша отпущена
            if self.recording_started:
                self.recording_started = False

            if duration < self.short_press_threshold:
                # Короткое нажатие: прервать/отменить текущее действие
                print(f"🔇 Короткое нажатие ({duration:.2f}s) - прерывание/отмена")
                self.loop.call_soon_threadsafe(self.queue.put_nowait, "interrupt_or_cancel")
            else:
                # Длинное нажатие: завершить запись и обработать
                print(f"⏹️ Длинное нажатие ({duration:.2f}s) - запись завершена")
                self.loop.call_soon_threadsafe(self.queue.put_nowait, "stop_recording")

async def main_test():
    """Функция для тестирования InputHandler"""
    print("🧪 Тест push-to-talk логики:")
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
        print("\n👋 Выход.")

        print("\n👋 Выход.")

