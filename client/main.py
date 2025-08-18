import asyncio
import logging
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
    IDLE = 1          # Ассистент спит, микрофон выключен
    LISTENING = 2     # Записываем команду (пробел зажат)
    PROCESSING = 3    # Обрабатываем команду
    SPEAKING = 4      # Ассистент говорит

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
    
    # Состояние приложения
    state = AppState.IDLE
    
    # Переменные для хранения скриншота и активного вызова
    current_screenshot = None
    current_screen_info = None
    active_call = None
    streaming_task = None  # Задача для фоновой обработки стрима
    
    console.print("[bold green]✅ Ассистент готов![/bold green]")
    console.print("[yellow]📋 Управление:[/yellow]")
    console.print("[yellow]  • Зажмите пробел → СРАЗУ активируется микрофон[/yellow]")
    console.print("[yellow]  • Удерживайте пробел → продолжается запись[/yellow]")
    console.print("[yellow]  • Отпустите пробел → останавливается запись + отправка команды[/yellow]")
    console.print("[yellow]  • Короткое нажатие → прерывание речи ассистента[/yellow]")
    console.print("[yellow]  • При активации автоматически захватывается экран[/yellow]")
    console.print("[yellow]  • Hardware ID отправляется с каждой командой[/yellow]")

    # --- Вспомогательная функция для обработки стрима в фоне ---
    async def consume_stream(stream_generator, player):
        nonlocal state, active_call, streaming_task
        loop = asyncio.get_running_loop()
        try:
            # Потребляем генератор до конца
            async for _ in stream_generator:
                pass
            
            # Естественное завершение: ждем, пока доиграет аудио
            await loop.run_in_executor(None, player.wait_for_queue_empty)
            
            # Сбрасываем состояние в IDLE только при естественном завершении
            state = AppState.IDLE
            active_call = None
            streaming_task = None
            logger.info("Состояние сброшено в IDLE после завершения речи.")
            console.print(f"[dim]✅ Состояние сброшено: {state.name}[/dim]")

        except asyncio.CancelledError:
            # При отмене задачи, тот, кто ее отменил, отвечает за состояние.
            # Просто логируем и выходим.
            logger.info("Задача стриминга была отменена.")
            console.print("[bold yellow]🔄 Задача стриминга отменена[/bold yellow]")
        except Exception as e:
            console.print(f"[bold red]❌ Ошибка в задаче обработки стрима: {e}[/bold red]")
            # При ошибке сбрасываем состояние
            state = AppState.IDLE
            active_call = None
            streaming_task = None
            console.print(f"[dim]✅ Состояние сброшено после ошибки: {state.name}[/dim]")
    # ---------------------------------------------------------

    try:
        # Получаем информацию об экране
        screen_info = screen_capture.get_screen_info()
        console.print(f"[bold blue]📱 Экран: {screen_info.get('width', 0)}x{screen_info.get('height', 0)} пикселей[/bold blue]")
        
        # Подключаемся к gRPC серверу (после инициализации всех компонентов)
        console.print("[blue]🔌 Подключение к серверу...[/blue]")
        if not await grpc_client.connect():
            console.print("[bold red]❌ Не удалось подключиться к серверу[/bold red]")
            return
            
        console.print("[bold green]✅ Подключено к серверу[/bold green]")
        
        # Основной цикл обработки событий
        while True:
            try:
                # Добавляем таймаут для предотвращения блокировки
                event = await asyncio.wait_for(event_queue.get(), timeout=0.1)
                
                # Логируем текущее состояние для отладки
                console.print(f"[dim]🔍 Состояние: {state.name}[/dim]")
                
                # Проверяем состояние аудио каждые несколько событий
                if hasattr(audio_player, 'get_audio_status'):
                    audio_status = audio_player.get_audio_status()
                    if audio_status.get('has_error'):
                        console.print(f"[dim]🔇 Аудио статус: {audio_status.get('error_message', 'Ошибка')}[/dim]")

                if event == "start_recording":
                    # Любое зажатие пробела прерывает речь и СРАЗУ начинает запись
                    if state == AppState.SPEAKING:
                        console.print("[bold yellow]🔇 Прерываю речь и начинаю запись...[/bold yellow]")
                        
                        # Немедленно отменяем все активные задачи
                        if streaming_task and not streaming_task.done():
                            streaming_task.cancel()
                            console.print("[yellow]🔄 Задача стриминга отменена[/yellow]")
                        
                        if active_call and not active_call.done():
                            active_call.cancel()
                            console.print("[yellow]🔄 gRPC вызов отменен[/yellow]")
                        
                        # Немедленно прерываем аудио
                        try:
                            audio_player.interrupt()
                            console.print("[green]✅ Аудио прервано[/green]")
                        except Exception as e:
                            console.print(f"[red]⚠️ Ошибка прерывания аудио: {e}[/red]")
                            # Пробуем принудительную остановку
                            try:
                                audio_player.force_stop()
                                console.print("[green]✅ Аудио принудительно остановлено[/green]")
                            except Exception as e2:
                                console.print(f"[red]❌ Критическая ошибка остановки аудио: {e2}[/red]")
                        
                        # Сбрасываем переменные
                        active_call = None
                        streaming_task = None

                    # Переходим в состояние прослушивания
                    state = AppState.LISTENING
                    console.print(f"[dim]✅ Состояние обновлено: {state.name}[/dim]")

                    console.print("[bold blue]📸 Захватываю экран в JPEG...[/bold blue]")
                    current_screenshot = screen_capture.capture_screen(quality=80)
                    current_screen_info = screen_info

                    if current_screenshot:
                        console.print(f"[bold green]✅ JPEG скриншот захвачен: {len(current_screenshot)} символов Base64[/bold green]")
                    else:
                        console.print("[bold yellow]⚠️ Не удалось захватить скриншот[/bold yellow]")

                    stt_recognizer.start_recording()
                    console.print("[bold green]🎤 Слушаю команду...[/bold green]")
                    console.print("[yellow]💡 Удерживайте пробел и говорите команду[/yellow]")

                elif event == "interrupt_or_cancel":
                    # Короткое нажатие: прерывает речь или отменяет запись
                    console.print(f"[blue]🔇 Обрабатываю прерывание (текущее состояние: {state.name})[/blue]")
                    
                    if state == AppState.SPEAKING:
                        console.print("[bold red]🔇 Прерывание речи ассистента...[/bold red]")
                        
                        # Немедленно отменяем все активные задачи
                        if streaming_task and not streaming_task.done():
                            streaming_task.cancel()
                            console.print("[yellow]🔄 Задача стриминга отменена[/yellow]")
                        
                        if active_call and not active_call.done():
                            active_call.cancel()
                            console.print("[yellow]🔄 gRPC вызов отменен[/yellow]")
                        
                        # Немедленно прерываем аудио
                        try:
                            audio_player.interrupt()
                            console.print("[green]✅ Аудио прервано[/green]")
                        except Exception as e:
                            console.print(f"[red]⚠️ Ошибка прерывания аудио: {e}[/red]")
                            # Пробуем принудительную остановку
                            try:
                                audio_player.force_stop()
                                console.print("[green]✅ Аудио принудительно остановлено[/green]")
                            except Exception as e2:
                                console.print(f"[red]❌ Критическая ошибка остановки аудио: {e2}[/red]")
                        
                        # Сбрасываем состояние
                        state = AppState.IDLE
                        active_call = None
                        streaming_task = None
                        
                        console.print("[bold green]✅ Речь прервана, готов к новым командам[/bold green]")

                    elif state == AppState.LISTENING:
                        console.print("[bold yellow]🚫 Запись отменена (короткое нажатие)[/bold yellow]")
                        # Останавливаем запись, но не обрабатываем результат
                        _ = stt_recognizer.stop_recording_and_recognize()
                        state = AppState.IDLE
                        
                    elif state == AppState.PROCESSING:
                        console.print("[bold yellow]🚫 Обработка команды отменена[/bold yellow]")
                        state = AppState.IDLE
                        
                    else:
                        console.print("[blue]ℹ️ Нет активных действий для прерывания[/blue]")
                        
                    console.print(f"[dim]✅ Состояние обновлено: {state.name}[/dim]")

                elif event == "stop_recording" and state == AppState.LISTENING:
                    # Длинное нажатие: обрабатываем команду
                    state = AppState.PROCESSING
                    console.print("[bold blue]🔍 Обрабатываю команду...[/bold blue]")

                    command = stt_recognizer.stop_recording_and_recognize()

                    if command and command.strip():
                        console.print(f"[bold green]📝 Команда: {command}[/bold green]")

                        try:
                            stream_generator = grpc_client.stream_audio(
                                command,
                                current_screenshot,
                                current_screen_info,
                                hardware_id
                            )

                            active_call = await stream_generator.__anext__()
                            state = AppState.SPEAKING

                            streaming_task = asyncio.create_task(consume_stream(stream_generator, audio_player))

                        except Exception as e:
                            console.print(f"[bold red]❌ Ошибка выполнения команды: {e}[/bold red]")
                            state = AppState.IDLE
                            console.print(f"[dim]✅ Состояние сброшено: {state.name}[/dim]")
                    else:
                        console.print("[yellow]⚠️ Команда не распознана[/yellow]")
                        state = AppState.IDLE
                        console.print(f"[dim]✅ Состояние сброшено: {state.name}[/dim]")
                        
            except asyncio.TimeoutError:
                # Таймаут для ожидания события, просто пропускаем
                pass
            except KeyboardInterrupt:
                console.print("\n[bold yellow]👋 Выход...[/bold yellow]")
                break # Выходим из основного цикла при прерывании
            except Exception as e:
                console.print(f"[bold red]❌ Критическая ошибка: {e}[/bold red]")
                break # Выходим из основного цикла при критической ошибке
    finally:
        if streaming_task and not streaming_task.done():
            streaming_task.cancel()
        if active_call and not active_call.done():
            active_call.cancel()
        stt_recognizer.cleanup()
        if audio_player.is_playing:
            audio_player.stop_playback()
        logger.info("Клиент завершил работу.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[bold yellow]👋 Выход...[/bold yellow]")

