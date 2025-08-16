import asyncio
import websockets
import json
import numpy as np
import base64
import logging
from rich.console import Console

# Импортируем AudioPlayer из текущей директории
from audio_player import AudioPlayer

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

console = Console()

async def main():
    """Основная функция клиента"""
    uri = "ws://localhost:8000/ws"
    
    # SAMPLE_RATE должен совпадать с серверным
    # В идеале, сервер мог бы присылать свою конфигурацию при подключении
    audio_player = AudioPlayer(sample_rate=48000)

    try:
        async with websockets.connect(uri) as websocket:
            console.print("[bold green]✅ Успешно подключено к серверу.[/bold green]")
            
            while True:
                prompt = console.input("[bold cyan]🎤 Введите промпт (или 'quit'): [/bold cyan]")
                if prompt.lower() == 'quit':
                    break

                console.print(f"[bold yellow]🚀 Запуск стриминга для: {prompt}[/bold yellow]")
                
                # Запускаем воспроизведение заранее
                audio_player.start_playback()
                
                # Отправляем промпт на сервер
                await websocket.send(prompt)

                # Обрабатываем ответы от сервера
                while True:
                    response_str = await websocket.recv()
                    response = json.loads(response_str)
                    
                    msg_type = response.get("type")
                    
                    if msg_type == "text":
                        console.print(f"[green]📄 Текст: {response['data']}[/green]")
                    
                    elif msg_type == "audio":
                        # Декодируем аудио данные
                        audio_bytes = base64.b64decode(response['data'])
                        dtype = response['dtype']
                        shape = tuple(response['shape'])
                        
                        # Восстанавливаем NumPy массив
                        audio_chunk = np.frombuffer(audio_bytes, dtype=dtype).reshape(shape)
                        audio_player.add_chunk(audio_chunk)
                    
                    elif msg_type == "end":
                        console.print("[bold green]✅ Стриминг завершен![/bold green]")
                        break
                        
                    elif msg_type == "error":
                        console.print(f"[bold red]❌ Ошибка от сервера: {response['data']}[/bold red]")
                        break

                # Ждем, пока все аудио в очереди будет воспроизведено
                audio_player.wait_for_queue_empty()
                audio_player.stop_playback()

    except websockets.exceptions.ConnectionClosedError:
        console.print("[bold red]❌ Соединение с сервером потеряно.[/bold red]")
    except ConnectionRefusedError:
        console.print("[bold red]❌ Не удалось подключиться к серверу. Убедитесь, что сервер запущен.[/bold red]")
    except Exception as e:
        console.print(f"[bold red]❌ Произошла непредвиденная ошибка: {e}[/bold red]")
    finally:
        if audio_player.is_playing:
            audio_player.stop_playback()
        logger.info("Клиент завершил работу.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[bold yellow]👋 Выход...[/bold yellow]")
