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
    """Основная функция клиента с push-to-talk логикой"""
    
    # Инициализируем компоненты
    audio_player = AudioPlayer(sample_rate=48000)
    stt_recognizer = StreamRecognizer()
    grpc_client = GrpcClient()
    
    # Очередь для событий от клавиатуры
    event_queue = asyncio.Queue()
    loop = asyncio.get_running_loop()
    input_handler = InputHandler(loop, event_queue)
    
    # Состояние приложения
    state = AppState.IDLE
    
    console.print("[bold green]✅ Ассистент готов![/bold green]")
    console.print("[yellow]📋 Управление:[/yellow]")
    console.print("[yellow]  • Долгое нажатие пробела (>0.6s) - активировать ассистента[/yellow]")
    console.print("[yellow]  • Короткое нажатие пробела (<0.6s) - прервать речь ассистента[/yellow]")
    console.print("[yellow]  • Удерживайте пробел во время разговора[/yellow]")

    try:
        # Подключаемся к gRPC серверу
        if not await grpc_client.connect():
            console.print("[bold red]❌ Не удалось подключиться к серверу[/bold red]")
            return
            
        console.print("[bold green]✅ Подключено к серверу[/bold green]")
        
        # Основной цикл обработки событий
        while True:
            event = await event_queue.get()
            
            if event == "long_press" and state == AppState.IDLE:
                # Активируем ассистента - начинаем слушать команду
                state = AppState.LISTENING
                stt_recognizer.start_recording()
                console.print("[bold green]🎤 Слушаю команду...[/bold green]")
                console.print("[yellow]💡 Удерживайте пробел и говорите команду[/yellow]")
                
            elif event == "short_press":
                if state == AppState.SPEAKING:
                    # Прерываем речь ассистента
                    audio_player.stop_playback()
                    state = AppState.IDLE
                    console.print("[bold red]⏹️ Речь прервана[/bold red]")
                elif state == AppState.LISTENING:
                    # Прерываем запись команды
                    stt_recognizer.stop_recording_and_recognize()
                    state = AppState.IDLE
                    console.print("[bold yellow]⚠️ Запись команды прервана[/bold yellow]")
                else:
                    console.print("[yellow]ℹ️ Ассистент не активен[/yellow]")
                    
            elif event == "space_released" and state == AppState.LISTENING:
                # Пользователь отпустил пробел - обрабатываем команду
                state = AppState.PROCESSING
                console.print("[bold blue]🔍 Обрабатываю команду...[/bold blue]")
                
                # Останавливаем запись и распознаем речь
                command = stt_recognizer.stop_recording_and_recognize()
                
                if command and command.strip():
                    console.print(f"[bold green]📝 Команда: {command}[/bold green]")
                    
                    # Отправляем команду на сервер
                    try:
                        await grpc_client.stream_audio(command)
                        state = AppState.IDLE
                        console.print("[bold green]✅ Команда выполнена[/bold green]")
                    except Exception as e:
                        console.print(f"[bold red]❌ Ошибка выполнения команды: {e}[/bold red]")
                        state = AppState.IDLE
                else:
                    console.print("[yellow]⚠️ Команда не распознана[/yellow]")
                    state = AppState.IDLE
                    
    except KeyboardInterrupt:
        console.print("\n[bold yellow]👋 Выход...[/bold yellow]")
    except Exception as e:
        console.print(f"[bold red]❌ Критическая ошибка: {e}[/bold red]")
    finally:
        # Очищаем ресурсы
        stt_recognizer.cleanup()
        if audio_player.is_playing:
            audio_player.stop_playback()
        logger.info("Клиент завершил работу.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[bold yellow]👋 Выход...[/bold yellow]")
