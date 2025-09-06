import asyncio
import time
from pynput import keyboard
from threading import Thread
from threading import Timer
from rich.console import Console

console = Console()

class InputHandler:
    """
    Простой и надежный обработчик клавиатуры для push-to-talk.
    Отправляет события в очередь, не управляет состоянием.
    """
    
    def __init__(self, loop: asyncio.AbstractEventLoop, queue: asyncio.Queue, state_manager=None):
        self.loop = loop
        self.queue = queue
        self.state_manager = state_manager
        self.press_time = None
        self.short_press_threshold = 0.1   # Порог для коротких нажатий (100ms) - быстрая реакция
        self.space_pressed = False
        self.last_event_time = 0
        self.event_cooldown = 0.3  # УВЕЛИЧИВАЕМ cooldown до 300ms для предотвращения быстрых повторных нажатий
        self.recording_started = False
        self._start_timer = None
        
        # Флаг для отслеживания состояния прерывания
        self.interrupting = False
        # 🆕 Флаг: была ли команда уже обработана в deactivate_microphone
        self.command_processed = False
        # 🆕 Флаг для предотвращения множественных быстрых нажатий
        self.processing_event = False

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
            
            # 🆕 ДОПОЛНИТЕЛЬНАЯ ЗАЩИТА: если уже обрабатываем событие
            if self.processing_event:
                console.print(f"[dim]⏰ Событие уже обрабатывается, игнорирую нажатие[/dim]")
                return
            
            # Проверяем cooldown для предотвращения множественных событий
            if current_time - self.last_event_time < self.event_cooldown:
                console.print(f"[dim]⏰ Cooldown активен: {self.event_cooldown - (current_time - self.last_event_time):.3f}s[/dim]")
                return
                
            # Устанавливаем флаг нажатия и время
            self.space_pressed = True
            self.press_time = current_time
            self.last_event_time = current_time
            self.recording_started = False
            self.processing_event = True  # 🆕 БЛОКИРУЕМ новые события
            
            # На всякий случай отменяем предыдущий таймер, если он ещё активен
            try:
                if self._start_timer and self._start_timer.is_alive():
                    self._start_timer.cancel()
            except Exception:
                pass
            
            # 1. УСТАНАВЛИВАЕМ ФЛАГ ПРЕРЫВАНИЯ
            self.interrupting = True
            console.print(f"[bold red]🔇 ПРОБЕЛ НАЖАТ - ПОДГОТОВКА К ПРЕРЫВАНИЮ! (время: {current_time:.3f})[/bold red]")
            console.print(f"[dim]🔍 Флаг interrupting установлен: {self.interrupting}[/dim]")
            
            # 2. ЗАПУСК ЗАПИСИ при удержании дольше порога
            def start_if_still_pressed():
                try:
                    if self.space_pressed and not self.recording_started:
                        # ПРОВЕРЯЕМ состояние через StateManager
                        if self.state_manager and hasattr(self.state_manager, 'can_start_recording') and not self.state_manager.can_start_recording():
                            console.print(f"[yellow]⚠️ Запись невозможна - микрофон уже активен или неподходящее состояние[/yellow]")
                            return
                            
                        # СБРАСЫВАЕМ флаг прерывания перед отправкой start_recording
                        self.interrupting = False
                        console.print(f"[dim]🔄 Флаг interrupting сброшен перед start_recording[/dim]")
                        self.recording_started = True
                        self.loop.call_soon_threadsafe(self.queue.put_nowait, "start_recording")
                        console.print(f"[dim]📤 Порог удержания пройден → start_recording отправлен[/dim]")
                except Exception:
                    pass

            try:
                self._start_timer = Timer(self.short_press_threshold, start_if_still_pressed)
                self._start_timer.daemon = True
                self._start_timer.start()
            except Exception:
                self._start_timer = None

    def on_release(self, key):
        """Обрабатывает отпускание клавиши"""
        if key == keyboard.Key.space and self.space_pressed:
            current_time = time.time()

            # Отменяем таймер старта записи ДО любых других действий
            try:
                if self._start_timer and self._start_timer.is_alive():
                    self._start_timer.cancel()
            except Exception:
                pass

            # Не прерываем логику на cooldown — лишь логируем
            if current_time - self.last_event_time < self.event_cooldown:
                console.print(f"[dim]⏰ Cooldown активен при отпускании: {self.event_cooldown - (current_time - self.last_event_time):.3f}s (продолжаю обработку) [/dim]")

            # Сбрасываем флаг нажатия
            self.space_pressed = False
            console.print(f"[dim]🔍 Флаг space_pressed сброшен в {current_time:.3f}[/dim]")
            
            # Вычисляем длительность нажатия
            duration = current_time - self.press_time
            self.press_time = None
            self.last_event_time = current_time
            console.print(f"[dim]📊 Длительность нажатия: {duration:.3f}s[/dim]")

            if self.recording_started:
                # Запись успела стартовать → останавливаем её на отпускании
                console.print(f"🔇 Пробел отпущен - деактивирую микрофон и возвращаюсь в SLEEPING")
                self.loop.call_soon_threadsafe(self.queue.put_nowait, "deactivate_microphone")
                console.print(f"[dim]📤 Событие deactivate_microphone отправлено в очередь[/dim]")
            else:
                # Короткое нажатие → ТОЛЬКО прерывание (без автоматической активации микрофона)
                console.print(f"🔇 Короткое нажатие ({duration:.2f}s) - только прерывание")
                console.print(f"[dim]🔍 Длительность {duration:.3f}s < {self.short_press_threshold}s - короткое нажатие[/dim]")
                # Отправляем ТОЛЬКО interrupt_or_cancel для прерывания
                self.loop.call_soon_threadsafe(self.queue.put_nowait, "interrupt_or_cancel")
                console.print(f"[dim]📤 Событие interrupt_or_cancel отправлено в очередь[/dim]")
                # УБИРАЕМ автоматическую отправку start_recording
                # Пользователь должен нажать пробел еще раз для активации микрофона
            
            # СБРАСЫВАЕМ ФЛАГ ПРЕРЫВАНИЯ
            console.print(f"[dim]🔍 Флаг interrupting ДО сброса: {self.interrupting}[/dim]")
            self.interrupting = False
            console.print(f"[dim]🔍 Флаг interrupting ПОСЛЕ сброса: {self.interrupting}[/dim]")
            console.print("🔄 Готов к новым событиям")

            # Сбрасываем флаги запуска записи
            self.recording_started = False
            self._start_timer = None
            
            # 🆕 РАЗБЛОКИРУЕМ новые события с небольшой задержкой
            def unblock_events():
                self.processing_event = False
                console.print(f"[dim]🔄 События разблокированы[/dim]")
            
            try:
                Timer(0.1, unblock_events).start()  # Разблокируем через 100ms
            except Exception:
                self.processing_event = False

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
    print("• Короткое нажатие пробела → только прерывание речи ассистента")
    print("• Удерживайте пробел → активация микрофона + запись")
    print("• Отпустите пробел → останавливается запись + отправка команды")
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

