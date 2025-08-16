import asyncio
import time
from pynput import keyboard
from threading import Thread

class InputHandler:
    """
    Обрабатывает глобальные нажатия клавиш в отдельном потоке
    и передает события в основной цикл asyncio.
    """
    def __init__(self, loop: asyncio.AbstractEventLoop, queue: asyncio.Queue):
        self.loop = loop
        self.queue = queue
        self.press_time = None
        self.long_press_duration = 0.6  # секунды
        self.space_pressed = False

        # Запускаем listener в отдельном потоке
        self.listener_thread = Thread(target=self._run_listener, daemon=True)
        self.listener_thread.start()

    def _run_listener(self):
        with keyboard.Listener(on_press=self.on_press, on_release=self.on_release) as listener:
            listener.join()

    def on_press(self, key):
        if key == keyboard.Key.space and not self.space_pressed:
            self.space_pressed = True
            self.press_time = time.time()
            
            # Отправляем событие нажатия пробела для push-to-talk
            self.loop.call_soon_threadsafe(self.queue.put_nowait, "space_pressed")

    def on_release(self, key):
        if key == keyboard.Key.space and self.space_pressed:
            self.space_pressed = False
            duration = time.time() - self.press_time
            self.press_time = None
            
            # Определяем тип события для прерывания
            if duration < self.long_press_duration:
                event_type = "short_press"
            else:
                event_type = "long_press"
            
            # Отправляем событие отпускания пробела для push-to-talk
            self.loop.call_soon_threadsafe(self.queue.put_nowait, "space_released")
            
            # Отправляем событие типа нажатия для прерывания
            self.loop.call_soon_threadsafe(self.queue.put_nowait, event_type)

async def main_test():
    """Функция для тестирования InputHandler"""
    print("Тест push-to-talk логики:")
    print("• Нажмите и удерживайте пробел для записи")
    print("• Отпустите пробел для отправки команды")
    print("• Нажмите Ctrl+C для выхода")
    
    event_queue = asyncio.Queue()
    loop = asyncio.get_running_loop()
    
    # Инициализируем обработчик
    InputHandler(loop, event_queue)
    
    while True:
        event = await event_queue.get()
        print(f"Событие: {event}")
        if event == "exit":
            break

if __name__ == "__main__":
    try:
        asyncio.run(main_test())
    except KeyboardInterrupt:
        print("\nВыход.")
