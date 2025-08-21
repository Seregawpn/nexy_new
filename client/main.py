import asyncio
import logging
import time
from rich.console import Console
from enum import Enum
import sys
from pathlib import Path

# Добавляем корневую директорию в путь для импорта
sys.path.append(str(Path(__file__).parent.parent))

from audio_player import AudioPlayer
from stt_recognizer import StreamRecognizer
from input_handler import InputHandler
from grpc_client import GrpcClient
from screen_capture import ScreenCapture
from utils.hardware_id import get_hardware_id, get_hardware_info

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

console = Console()

class AppState(Enum):
    IDLE = 1          # Ассистент спит, микрофон выключен, готов к командам
    LISTENING = 2     # Записываем команду (пробел зажат)
    PROCESSING = 3    # Обрабатываем команду (gRPC запрос)
    SPEAKING = 4      # Ассистент говорит (аудио воспроизводится)

class StateManager:
    """
    Управляет переходами между состояниями приложения.
    Каждое состояние знает, как реагировать на каждое событие.
    """
    
    def __init__(self, console, audio_player, stt_recognizer, screen_capture, grpc_client, hardware_id):
        self.console = console
        self.audio_player = audio_player
        self.stt_recognizer = stt_recognizer
        self.screen_capture = screen_capture
        self.grpc_client = grpc_client
        self.hardware_id = hardware_id
        
        # Состояние приложения
        self.state = AppState.IDLE
        self.active_call = None
        self.streaming_task = None
        self.current_screenshot = None
        self.current_screen_info = None
        
        # Простое отслеживание состояния
        pass
        
    def get_state(self):
        """Возвращает текущее состояние"""
        return self.state
    
    def set_state(self, new_state):
        """Устанавливает новое состояние"""
        if self.state != new_state:
            self.state = new_state
            self.console.print(f"[dim]✅ Состояние: {self.state.name}[/dim]")
    
    def handle_start_recording(self):
        """Обрабатывает событие начала записи - СНАЧАЛА ПРЕРЫВАНИЕ, ПОТОМ ЗАПИСЬ"""
        self.console.print(f"[blue]🎤 Начинаю запись (текущее состояние: {self.state.name})[/blue]")
        
        # ПАРАЛЛЕЛЬНАЯ АКТИВАЦИЯ: микрофон + прерывание одновременно!
        if self.state == AppState.SPEAKING:
            self.console.print("[bold yellow]🔇 Ассистент говорит - ПАРАЛЛЕЛЬНОЕ прерывание + микрофон![/bold yellow]")
            
            # 1️⃣ ЗАПУСКАЕМ ПРЕРЫВАНИЕ В ФОНЕ (не блокируем!)
            import threading
            interrupt_thread = threading.Thread(target=self._interrupt_background, daemon=True)
            interrupt_thread.start()
            
            # 2️⃣ СРАЗУ АКТИВИРУЕМ МИКРОФОН (не ждем прерывания!)
            self.console.print("[bold green]🎤 МИКРОФОН АКТИВИРОВАН ПАРАЛЛЕЛЬНО![/bold green]")
            
        elif self.state == AppState.IDLE:
            # Ассистент НЕ говорит - просто активируем микрофон
            self.console.print("[blue]ℹ️ Ассистент не говорит - активирую микрофон[/blue]")
        
        # Переходим в состояние прослушивания
        self.set_state(AppState.LISTENING)
        
        # Захватываем экран и начинаем запись
        self._capture_screen()
        self.stt_recognizer.start_recording()
        self.console.print("[bold green]🎤 Слушаю команду...[/bold green]")
        self.console.print("[yellow]💡 Удерживайте пробел и говорите команду[/yellow]")
        
        # КРИТИЧНО: устанавливаем флаг что микрофон активирован
        self._microphone_activated = True
        
        # 3️⃣ ИНФОРМИРУЕМ о параллельной работе
        if self.state == AppState.SPEAKING:
            self.console.print("[blue]ℹ️ Прерывание идет в фоне, микрофон уже работает![/blue]")
    
    def handle_stop_recording(self):
        """Обрабатывает событие остановки записи"""
        if self.state != AppState.LISTENING:
            self.console.print(f"[yellow]⚠️ Получено stop_recording в состоянии {self.state.name}, игнорирую[/yellow]")
            return
        
        # Переходим в состояние обработки
        self.set_state(AppState.PROCESSING)
        self.console.print("[bold blue]🔍 Обрабатываю команду...[/bold blue]")
        
        # Получаем команду
        command = self.stt_recognizer.stop_recording_and_recognize()
        
        if command and command.strip():
            self.console.print(f"[bold green]📝 Команда: {command}[/bold green]")
            self._process_command(command)
        else:
            self.console.print("[yellow]⚠️ Команда не распознана[/yellow]")
            self.set_state(AppState.IDLE)
    
    def handle_interrupt_or_cancel(self):
        """Обрабатывает событие прерывания/отмены - МГНОВЕННОЕ прерывание"""
        self.console.print(f"[blue]🔇 МГНОВЕННОЕ прерывание (текущее состояние: {self.state.name})[/blue]")
        
        # ПРИНУДИТЕЛЬНОЕ ПРЕРЫВАНИЕ ВСЕГО - независимо от состояния!
        self.console.print("[bold red]🔇 ПРИНУДИТЕЛЬНО прерывание ВСЕГО...[/bold red]")
        
        # 1. Прерываем аудио ВСЕГДА - с принудительной остановкой
        self._interrupt_audio()
        
        # 2. Отменяем все задачи ВСЕГДА
        self._cancel_tasks()
        
        # 3. Если записываем - останавливаем запись
        if self.state == AppState.LISTENING:
            try:
                # КРИТИЧНО: используем принудительную остановку БЕЗ распознавания
                if hasattr(self.stt_recognizer, 'force_stop_recording'):
                    self.stt_recognizer.force_stop_recording()
                    self.console.print("[yellow]🚫 Запись ПРИНУДИТЕЛЬНО остановлена[/yellow]")
                else:
                    # Fallback к старому методу
                    _ = self.stt_recognizer.stop_recording_and_recognize()
                    self.console.print("[yellow]🚫 Запись остановлена[/yellow]")
            except Exception as e:
                self.console.print(f"[yellow]⚠️ Ошибка при остановке записи: {e}[/yellow]")
        
        # 4. Переходим в IDLE ВСЕГДА
        self.set_state(AppState.IDLE)
        self.console.print("[bold green]✅ ВСЕ МГНОВЕННО прервано и остановлено![/bold green]")
        
        # 5. ДОПОЛНИТЕЛЬНАЯ ПРОВЕРКА - убеждаемся что все остановлено
        if hasattr(self.audio_player, 'is_playing') and self.audio_player.is_playing:
            self.console.print("[red]⚠️ Аудио все еще играет, принудительно останавливаю...[/red]")
            try:
                self.audio_player.force_stop()
                self.console.print("[green]✅ Аудио принудительно остановлено[/green]")
            except Exception as e:
                self.console.print(f"[red]❌ Критическая ошибка остановки аудио: {e}[/red]")
    
    def _interrupt_audio(self):
        """МГНОВЕННОЕ прерывание аудио - БЕЗ ОЖИДАНИЙ!"""
        self.console.print(f"[blue]🔇 МГНОВЕННОЕ прерывание аудио...[/blue]")
        
        # МГНОВЕННО останавливаем аудио - используем ТОЛЬКО clear_all_audio_data!
        try:
            if hasattr(self.audio_player, 'clear_all_audio_data'):
                self.audio_player.clear_all_audio_data()
                self.console.print("[green]✅ Аудио clear_all_audio_data() выполнен[/green]")
            else:
                # Fallback на старые методы
                if hasattr(self.audio_player, 'force_stop_immediately'):
                    self.audio_player.force_stop_immediately()
                    self.console.print("[green]✅ Аудио force_stop_immediately() выполнен (fallback)[/green]")
                elif hasattr(self.audio_player, 'force_stop'):
                    self.audio_player.force_stop()
                    self.console.print("[green]✅ Аудио force_stop() выполнен (fallback)[/green]")
                else:
                    self.console.print("[yellow]⚠️ Ни один метод остановки аудио недоступен[/yellow]")
        except Exception as e:
            self.console.print(f"[red]⚠️ Ошибка остановки аудио: {e}[/red]")
        
        # НЕ ЖДЕМ - сразу считаем что аудио остановлено!
        self.console.print("[green]✅ Аудио остановлено МГНОВЕННО![/green]")
    
    def _cancel_tasks(self):
        """МГНОВЕННО отменяет активные задачи - БЕЗ ОЖИДАНИЙ!"""
        self.console.print("[bold red]🔍 ДЕТАЛЬНАЯ ДИАГНОСТИКА ОТМЕНЫ ЗАДАЧ...[/bold red]")
        
        # КРИТИЧНО: проверяем текущее состояние
        if hasattr(self, 'state'):
            self.console.print(f"[bold red]🚨 Текущее состояние: {self.state.name}[/bold red]")
            if self.state == AppState.SPEAKING:
                self.console.print("[bold red]🚨 АССИСТЕНТ ГОВОРИТ - ПРИНУДИТЕЛЬНО ПРЕРЫВАЮ![/bold red]")
            elif self.state == AppState.PROCESSING:
                self.console.print("[bold red]🚨 АССИСТЕНТ ОБРАБАТЫВАЕТ - ПРИНУДИТЕЛЬНО ПРЕРЫВАЮ![/bold red]")
        
        # 1️⃣ МГНОВЕННО отменяем gRPC задачи
        if self.streaming_task:
            try:
                self.streaming_task.cancel()
                self.console.print("[yellow]🔄 Задача стриминга МГНОВЕННО отменена[/yellow]")
            except Exception as e:
                self.console.print(f"[red]⚠️ Ошибка отмены streaming_task: {e}[/red]")
        else:
            self.console.print("[yellow]⚠️ streaming_task = None[/yellow]")
        
        if self.active_call:
            try:
                self.active_call.cancel()
                self.console.print("[yellow]🔄 gRPC вызов МГНОВЕННО отменен[/yellow]")
            except Exception as e:
                self.console.print(f"[red]⚠️ Ошибка отмены active_call: {e}[/red]")
        else:
            self.console.print("[yellow]⚠️ active_call = None[/yellow]")
        
        # 2️⃣ КРИТИЧНО: ВСЕГДА отправляем команду прерывания на сервер!
        try:
            self.console.print("[bold red]🚨 ОТПРАВЛЯЮ КОМАНДУ ПРЕРЫВАНИЯ НА СЕРВЕР![/bold red]")
            self.grpc_client.force_interrupt_server()
            self.console.print("[bold red]🚨 Команда прерывания отправлена на сервер![/bold red]")
        except Exception as e:
            self.console.print(f"[red]⚠️ Ошибка отправки команды прерывания: {e}[/red]")
        
        # 3️⃣ Сразу сбрасываем ссылки
        self.active_call = None
        self.streaming_task = None
        
        self.console.print("[green]✅ Все задачи МГНОВЕННО отменены![/green]")
    
    def _force_interrupt_all(self):
        """ЕДИНЫЙ метод для принудительного прерывания ВСЕГО"""
        logger.info(f"🚨 _force_interrupt_all() вызван в {time.time():.3f}")
        
        # Логируем состояние ДО прерывания
        queue_size = self.audio_player.audio_queue.qsize()
        logger.info(f"   📊 Состояние ДО: queue_size={queue_size}, state={self.state.name}")
        
        start_time = time.time()
        
        # 1️⃣ Останавливаем аудио
        audio_start = time.time()
        self._interrupt_audio()
        audio_time = (time.time() - audio_start) * 1000
        logger.info(f"   ✅ _interrupt_audio: {audio_time:.1f}ms")
        
        # 2️⃣ Отменяем задачи
        tasks_start = time.time()
        self._cancel_tasks()
        tasks_time = (time.time() - tasks_start) * 1000
        logger.info(f"   ✅ _cancel_tasks: {tasks_time:.1f}ms")
        
        total_time = (time.time() - start_time) * 1000
        
        # Логируем состояние ПОСЛЕ прерывания
        final_queue_size = self.audio_player.audio_queue.qsize()
        logger.info(f"   📊 Состояние ПОСЛЕ: queue_size={final_queue_size}")
        logger.info(f"   ⏱️ Общее время прерывания: {total_time:.1f}ms")
        
        # Проверяем результат
        if final_queue_size == 0:
            logger.info("   🎯 ПРЕРЫВАНИЕ УСПЕШНО - очередь очищена!")
        else:
            logger.warning(f"   ⚠️ ПРЕРЫВАНИЕ НЕПОЛНОЕ - очередь: {final_queue_size}")
        
        self.console.print("[bold red]🚨 ВСЕ ПРИНУДИТЕЛЬНО ПРЕРВАНО![/bold red]")
    
    def _interrupt_background(self):
        """ФОНОВОЕ прерывание - работает параллельно с активацией микрофона!"""
        try:
            self.console.print("[blue]🔄 Запуск фонового прерывания...[/blue]")
            
            # 1️⃣ МГНОВЕННО останавливаем аудио
            self._interrupt_audio()
            self.console.print("[green]✅ Фоновое прерывание аудио завершено[/green]")
            
            # 2️⃣ МГНОВЕННО отменяем все задачи
            self._cancel_tasks()
            self.console.print("[green]✅ Фоновое прерывание задач завершено[/green]")
            
            # 3️⃣ ЗАЩИТА ОТ ЗАВИСАНИЯ: таймаут на фоновое прерывание
            import time
            start_time = time.time()
            max_background_time = 0.5  # Уменьшаем с 3.0s до 0.5s для мгновенной остановки!
            
            # Проверяем что прерывание завершилось в разумное время
            while time.time() - start_time < max_background_time:
                if not hasattr(self.audio_player, 'is_playing') or not self.audio_player.is_playing:
                    break
                time.sleep(0.1)  # Проверяем каждые 100ms
            
            # Если прерывание зависло - принудительно останавливаем
            if hasattr(self.audio_player, 'is_playing') and self.audio_player.is_playing:
                self.console.print("[bold red]🚨 Фоновое прерывание зависло - ПРИНУДИТЕЛЬНАЯ остановка![/bold red]")
                self.audio_player.force_stop()
            
            self.console.print("[bold green]✅ Фоновое прерывание полностью завершено![/bold green]")
            
        except Exception as e:
            self.console.print(f"[red]❌ Ошибка в фоновом прерывании: {e}[/red]")
            # В случае ошибки - принудительно останавливаем
            try:
                if hasattr(self.audio_player, 'force_stop'):
                    self.audio_player.force_stop()
            except:
                pass
    
    async def _force_cancel_task(self, task):
        """Принудительно отменяет задачу с повторными попытками"""
        try:
            self.console.print(f"[bold red]🔧 ПРИНУДИТЕЛЬНАЯ отмена задачи: {task}[/bold red]")
            
            # Попытка 1: стандартная отмена
            if not task.done():
                task.cancel()
                self.console.print("[blue]🔧 Попытка 1: cancel() вызван[/blue]")
                
                # Ждем немного и проверяем
                await asyncio.sleep(0.1)
                if not task.cancelled():
                    self.console.print("[red]🚨 Задача НЕ отменена после cancel()![/red]")
                    
                    # Попытка 2: принудительная отмена через исключение
                    if hasattr(task, '_coro'):
                        self.console.print("[red]🚨 ПРИНУДИТЕЛЬНО прерываю корутину![/red]")
                        # Здесь можно попробовать более агрессивные методы
                    
                    # Попытка 3: создаем новую задачу для "убийства" старой
                    self.console.print("[red]🚨 Создаю задачу-убийцу для старой задачи![/red]")
                    killer_task = asyncio.create_task(self._kill_task(task))
                    await killer_task
                else:
                    self.console.print("[green]✅ Задача успешно отменена![/green]")
            else:
                self.console.print("[green]✅ Задача уже завершена[/green]")
                
        except Exception as e:
            self.console.print(f"[red]⚠️ Ошибка принудительной отмены: {e}[/red]")
    
    async def _kill_task(self, task):
        """Пытается "убить" задачу любыми способами"""
        try:
            self.console.print(f"[bold red]💀 Пытаюсь УБИТЬ задачу: {task}[/bold red]")
            
            # Метод 1: множественные cancel()
            for i in range(5):
                if not task.done():
                    task.cancel()
                    await asyncio.sleep(0.05)
                    if task.cancelled():
                        self.console.print(f"[green]✅ Задача убита попыткой {i+1}[/green]")
                        break
                else:
                    break
            
            # Метод 2: если задача все еще жива, создаем исключение
            if not task.done() and not task.cancelled():
                self.console.print("[red]🚨 Задача НЕИЗЛЕЧИМА! Создаю исключение...[/red]")
                # Здесь можно попробовать создать исключение в задаче
                
        except Exception as e:
            self.console.print(f"[red]⚠️ Ошибка убийства задачи: {e}[/red]")
    
    def _capture_screen(self):
        """Захватывает экран"""
        self.console.print("[bold blue]📸 Захватываю экран в JPEG...[/bold blue]")
        self.current_screenshot = self.screen_capture.capture_screen(quality=80)
        
        if self.current_screenshot:
            self.console.print(f"[bold green]✅ JPEG скриншот захвачен: {len(self.current_screenshot)} символов Base64[/bold green]")
        else:
            self.console.print("[bold yellow]⚠️ Не удалось захватить скриншот[/bold yellow]")
    
    def _process_command(self, command):
        """Обрабатывает команду через gRPC"""
        try:
            # Сбрасываем флаг отмены для новой команды
            self._cancelled = False
            self.console.print("[blue]🔍 Сброшен флаг отмены для новой команды[/blue]")
            
            # Просто создаем gRPC стрим
            stream_generator = self.grpc_client.stream_audio(
                command,
                self.current_screenshot,
                self.current_screen_info,
                self.hardware_id
            )
            
            # Создаем задачу для обработки стрима
            self.streaming_task = asyncio.create_task(self._consume_stream(stream_generator))
            
        except Exception as e:
            self.console.print(f"[bold red]❌ Ошибка выполнения команды: {e}[/bold red]")
            self.set_state(AppState.IDLE)
    
    async def _consume_stream(self, stream_generator):
        """Обрабатывает gRPC стрим в фоне"""
        logger.info(f"🚨 _consume_stream() начат в {time.time():.3f}")
        
        try:
            self.set_state(AppState.SPEAKING)
            logger.info(f"   📊 Состояние установлено: {self.state.name}")
            
            # Потребляем генератор до конца
            chunk_count = 0
            self.console.print("[bold red]🚨 НАЧАЛО ОБРАБОТКИ gRPC СТРИМА![/bold red]")
            logger.info("   🚀 Начало обработки gRPC стрима")
            
            try:
                async for chunk in stream_generator:
                    chunk_count += 1
                    logger.info(f"   📦 Получен чанк {chunk_count} в {time.time():.3f}")
                    
                    self.console.print(f"[blue]🔍 Обрабатываю чанк {chunk_count}...[/blue]")
                    
                    # Обрабатываем каждый чанк!
                    if hasattr(chunk, 'text_chunk') and chunk.text_chunk:
                        self.console.print(f"[green]📄 Текст: {chunk.text_chunk[:100]}...[/green]")
                    
                    if hasattr(chunk, 'audio_chunk') and chunk.audio_chunk:
                        audio_data = chunk.audio_chunk.audio_data
                        audio_samples = len(audio_data)//2
                        logger.info(f"   🎵 Аудио чанк {chunk_count}: {audio_samples} сэмплов")
                        self.console.print(f"[green]🎵 Аудио чанк получен: {audio_samples} сэмплов[/green]")
                        
                        # Добавляем аудио в плеер!
                        try:
                            import numpy as np
                            audio_array = np.frombuffer(audio_data, dtype=np.int16)
                            
                            # Логируем состояние очереди ДО добавления
                            queue_before = self.audio_player.audio_queue.qsize()
                            logger.info(f"   📊 Очередь ДО добавления: {queue_before}")
                            
                            # КРИТИЧНО: используем правильное имя метода!
                            self.audio_player.add_chunk(audio_array)
                            
                            # Логируем состояние очереди ПОСЛЕ добавления
                            queue_after = self.audio_player.audio_queue.qsize()
                            logger.info(f"   📊 Очередь ПОСЛЕ добавления: {queue_after}")
                            
                            self.console.print(f"[green]✅ Аудио добавлено в плеер[/green]")
                        except Exception as e:
                            logger.error(f"   ❌ Ошибка добавления аудио: {e}")
                            self.console.print(f"[red]❌ Ошибка добавления аудио: {e}[/red]")
                    
                    if hasattr(chunk, 'error_message') and chunk.error_message:
                        self.console.print(f"[red]❌ Ошибка сервера: {chunk.error_message}[/red]")
                    
                    if hasattr(chunk, 'end_message') and chunk.end_message:
                        self.console.print(f"[green]✅ Получен сигнал завершения: {chunk.end_message}[/green]")
                        break
                        
            except Exception as stream_error:
                self.console.print(f"[red]❌ Ошибка в async for: {stream_error}[/red]")
                
        except Exception as e:
            logger.error(f"   ❌ Ошибка в _consume_stream: {e}")
            self.console.print(f"[red]❌ Ошибка в _consume_stream: {e}[/red]")
        finally:
            # КРИТИЧНО: всегда сбрасываем состояние
            final_time = time.time()
            logger.info(f"   🏁 _consume_stream завершен в {final_time:.3f}")
            self.set_state(AppState.IDLE)
            logger.info(f"   📊 Финальное состояние: {self.state.name}")
            self.console.print(f"[blue]✅ _consume_stream завершен, состояние: {self.state.name}[/blue]")
    
    def cleanup(self):
        """Очищает ресурсы"""
        if self.streaming_task and not self.streaming_task.done():
            self.streaming_task.cancel()
        if self.active_call and not self.active_call.done():
            self.active_call.cancel()

async def main():
    """Основная функция клиента с push-to-talk логикой, захватом экрана и Hardware ID"""
    
    # Инициализируем компоненты в правильном порядке
    console.print("[bold blue]🔧 Инициализация компонентов...[/bold blue]")
    
    # 1. Сначала инициализируем STT (до gRPC)
    console.print("[blue]🎤 Инициализация STT...[/blue]")
    stt_recognizer = StreamRecognizer()
    
    # 2. Инициализируем захват экрана
    console.print("[blue]📸 Инициализация захвата экрана...[/blue]")
    screen_capture = ScreenCapture()
    
    # 3. Инициализируем аудио плеер
    console.print("[blue]🔊 Инициализация аудио плеера...[/blue]")
    try:
        audio_player = AudioPlayer(sample_rate=48000)
        console.print("[bold green]✅ Аудио плеер инициализирован[/bold green]")
    except Exception as e:
        console.print(f"[bold red]❌ Ошибка инициализации аудио плеера: {e}[/bold red]")
        console.print("[yellow]⚠️ Ассистент будет работать без звука[/yellow]")
        # Создаем заглушку для аудио плеера
        class AudioPlayerStub:
            def __init__(self):
                self.is_playing = False
                self.audio_error = True
                self.audio_error_message = str(e)
            
            def start_playback(self):
                console.print("[yellow]🔇 Аудио недоступно[/yellow]")
    except Exception as e:
        console.print(f"[bold red]❌ Ошибка инициализации аудио плеера: {e}[/bold red]")
        console.print("[yellow]⚠️ Ассистент будет работать без звука[/yellow]")
        # Создаем заглушку для аудио плеера
        class AudioPlayerStub:
            def __init__(self):
                self.is_playing = False
                self.audio_error = True
                self.audio_error_message = str(e)
            
            def start_playback(self):
                console.print("[yellow]🔇 Аудио недоступно[/yellow]")
            
            def stop_playback(self):
                pass
            
            def interrupt(self):
                pass
            
            def add_audio_chunk(self, audio_chunk):
                console.print(f"[dim]🔇 Аудио чанк получен (звук отключен): {len(audio_chunk)} сэмплов[/dim]")
            
            def wait_for_queue_empty(self):
                pass
            
            def cleanup(self):
                pass
            
            def get_audio_status(self):
                return {'is_playing': False, 'has_error': True, 'error_message': str(e)}
        
        audio_player = AudioPlayerStub()
    
    # 4. Инициализируем gRPC клиент (последним)
    console.print("[blue]🌐 Инициализация gRPC клиента...[/blue]")
    grpc_client = GrpcClient()
    
    # 5. Получаем Hardware ID (один раз при запуске, с кэшированием)
    console.print("[blue]🆔 Получение Hardware ID...[/blue]")
    
    # Проверяем аргументы командной строки для управления кэшем
    import sys
    force_regenerate = "--force-regenerate" in sys.argv
    clear_cache = "--clear-cache" in sys.argv
    
    if clear_cache:
        from utils.hardware_id import clear_hardware_id_cache
        clear_hardware_id_cache()
        console.print("[yellow]🗑️ Кэш Hardware ID очищен[/yellow]")
    
    hardware_id = get_hardware_id(force_regenerate=force_regenerate)  # Автоматически использует кэш если доступен
    hardware_info = get_hardware_info()
    
    console.print(f"[bold green]✅ Hardware ID получен: {hardware_id[:16]}...[/bold green]")
    console.print(f"[blue]📱 UUID: {hardware_info['hardware_uuid'][:16]}...[/blue]")
    console.print(f"[blue]🔢 Serial: {hardware_info['serial_number']}[/blue]")
    
    # Показываем информацию о кэше
    from utils.hardware_id import get_cache_info
    cache_info = get_cache_info()
    if cache_info['exists']:
        console.print(f"[green]💾 Hardware ID загружен из кэша[/green]")
    else:
        console.print(f"[yellow]🔄 Hardware ID сгенерирован заново[/yellow]")
    
    # Показываем справку по управлению кэшем
    if "--help" in sys.argv:
        console.print("\n[yellow]📋 Управление кэшем Hardware ID:[/yellow]")
        console.print("[yellow]  • --clear-cache      - очистить кэш[/yellow]")
        console.print("[yellow]  • --force-regenerate - принудительно пересоздать ID[/yellow]")
        console.print("[yellow]  • --help            - показать эту справку[/yellow]")
        console.print("[yellow]  • Без аргументов    - использовать кэш если доступен[/yellow]")
    
    # Очередь для событий от клавиатуры
    event_queue = asyncio.Queue()
    loop = asyncio.get_running_loop()
    input_handler = InputHandler(loop, event_queue)
    
    # Получаем информацию об экране
    screen_info = screen_capture.get_screen_info()
    console.print(f"[bold blue]📱 Экран: {screen_info.get('width', 0)}x{screen_info.get('height', 0)} пикселей[/bold blue]")
    
    # Создаем StateManager
    state_manager = StateManager(console, audio_player, stt_recognizer, screen_capture, grpc_client, hardware_id)
    state_manager.current_screen_info = screen_info
    
    # КРИТИЧНО: передаем hardware_id в grpc_client для прерывания на сервере
    grpc_client.hardware_id = hardware_id
    console.print(f"[blue]🔧 Hardware ID {hardware_id[:16]}... передан в gRPC клиент[/blue]")
    
    # Подключаемся к gRPC серверу
    console.print("[blue]🔌 Подключение к серверу...[/blue]")
    if not await grpc_client.connect():
        console.print("[bold red]❌ Не удалось подключиться к серверу[/bold red]")
        return
        
    console.print("[bold green]✅ Подключено к серверу[/bold green]")
    
    # Показываем справку по управлению
    console.print("[bold green]✅ Ассистент готов![/bold green]")
    console.print("[yellow]📋 Управление:[/yellow]")
    console.print("[yellow]  • Зажмите пробел → СРАЗУ активируется микрофон[/yellow]")
    console.print("[yellow]  • Удерживайте пробел → продолжается запись[/yellow]")
    console.print("[yellow]  • Отпустите пробел → останавливается запись + отправка команды[/yellow]")
    console.print("[yellow]  • Короткое нажатие → прерывание речи ассистента[/yellow]")
    console.print("[yellow]  • При активации автоматически захватывается экран[/yellow]")
    console.print("[yellow]  • Hardware ID отправляется с каждой командой[/yellow]")

    # Основной цикл обработки событий
    try:
        while True:
            try:
                # УСКОРЕННЫЙ таймаут для быстрой реакции
                event = await asyncio.wait_for(event_queue.get(), timeout=0.05)  # 50ms вместо 100ms
                
                # Логируем текущее состояние для отладки
                console.print(f"[dim]🔍 Текущее состояние: {state_manager.get_state().name}, событие: {event}[/dim]")
                
                # ДЕТАЛЬНОЕ ЛОГИРОВАНИЕ СОБЫТИЙ
                start_time = time.time()
                console.print(f"[bold blue]🎯 ОБРАБАТЫВАЮ СОБЫТИЕ: {event}[/bold blue]")
                console.print(f"[bold blue]🎯 ТЕКУЩЕЕ СОСТОЯНИЕ: {state_manager.get_state().name}[/bold blue]")

                if event == "start_recording":
                    state_manager.handle_start_recording()
                elif event == "interrupt_or_cancel":
                    state_manager.handle_interrupt_or_cancel()
                elif event == "stop_recording":
                    state_manager.handle_stop_recording()
                elif event == "process_command":
                    state_manager.handle_process_command()
                
                # ДИАГНОСТИКА ВРЕМЕНИ ОБРАБОТКИ
                processing_time = (time.time() - start_time) * 1000  # в миллисекундах
                console.print(f"[dim]⚡ Время обработки события: {processing_time:.1f}ms[/dim]")
                
                # ПРОВЕРКА СОСТОЯНИЯ ПОСЛЕ ОБРАБОТКИ СОБЫТИЯ
                new_state = state_manager.get_state()
                console.print(f"[bold green]✅ СОБЫТИЕ {event} ОБРАБОТАНО! Новое состояние: {new_state.name}[/bold green]")
                
                # ДИАГНОСТИКА АУДИО - проверяем состояние после каждого события
                if hasattr(audio_player, 'is_playing'):
                    audio_playing = audio_player.is_playing
                    console.print(f"[dim]🔇 Аудио статус: {'ИГРАЕТ' if audio_playing else 'ОСТАНОВЛЕНО'}[/dim]")
                    
                    # Если аудио все еще играет после interrupt_or_cancel - это проблема!
                    if event == "interrupt_or_cancel" and audio_playing:
                        console.print(f"[bold red]🚨 ПРОБЛЕМА: Аудио все еще играет после прерывания![/bold red]")
                        console.print(f"[bold red]🚨 Принудительно останавливаю аудио...[/bold red]")
                        try:
                            if hasattr(audio_player, 'force_stop'):
                                audio_player.force_stop()
                                console.print(f"[bold green]✅ Аудио принудительно остановлено[/bold green]")
                        except Exception as e:
                            console.print(f"[bold red]❌ Критическая ошибка: {e}[/bold red]")
                
                # ЗАЩИТА ОТ ЗАВИСАНИЯ: если ассистент завис в SPEAKING более 15 секунд
                current_state = state_manager.get_state()
                if current_state == AppState.SPEAKING:
                    if not hasattr(state_manager, '_speaking_start_time'):
                        state_manager._speaking_start_time = time.time()
                    elif time.time() - state_manager._speaking_start_time > 15.0:  # 15 секунд максимум
                        console.print("[bold red]🚨 ЗАВИСАНИЕ! Ассистент завис в SPEAKING более 15 секунд![/bold red]")
                        console.print("[bold red]🔧 Принудительно сбрасываю состояние...[/bold red]")
                        audio_player.force_stop()
                        state_manager.set_state(AppState.IDLE)
                        state_manager._speaking_start_time = None
                else:
                    # Сбрасываем таймер если не в SPEAKING
                    if hasattr(state_manager, '_speaking_start_time'):
                        state_manager._speaking_start_time = None
                
                # Проверяем состояние аудио каждые несколько событий
                if hasattr(audio_player, 'get_audio_status'):
                    audio_status = audio_player.get_audio_status()
                    if audio_status.get('has_error'):
                        console.print(f"[dim]🔇 Аудио статус: {audio_status.get('error_message', 'Ошибка')}[/dim]")

            except asyncio.TimeoutError:
                # Таймаут для ожидания события, просто пропускаем
                pass
    except KeyboardInterrupt:
        console.print("\n[bold yellow]👋 Выход...[/bold yellow]")
    except Exception as e:
        console.print(f"[bold red]❌ Критическая ошибка: {e}[/bold red]")
    finally:
        state_manager.cleanup()
        if audio_player.is_playing:
            audio_player.stop_playback()
        logger.info("Клиент завершил работу.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[bold yellow]👋 Выход...[/bold yellow]")

