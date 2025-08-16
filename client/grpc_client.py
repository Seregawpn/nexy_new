import asyncio
import logging
import numpy as np
import grpc
import sys
import os

# Добавляем корневую директорию в путь для импорта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streaming_pb2
import streaming_pb2_grpc
from audio_player import AudioPlayer
from rich.console import Console

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

console = Console()

class GrpcClient:
    """gRPC клиент для стриминга аудио и текста"""
    
    def __init__(self, server_address: str = "localhost:50051"):
        self.server_address = server_address
        self.audio_player = AudioPlayer(sample_rate=48000)
        self.channel = None
        self.stub = None
    
    async def connect(self):
        """Подключение к gRPC серверу"""
        try:
            # Создаем неблокирующий канал
            self.channel = grpc.aio.insecure_channel(self.server_address)
            self.stub = streaming_pb2_grpc.StreamingServiceStub(self.channel)
            
            console.print(f"[bold green]✅ Подключение к gRPC серверу {self.server_address} установлено[/bold green]")
            return True
            
        except Exception as e:
            console.print(f"[bold red]❌ Ошибка подключения к серверу: {e}[/bold red]")
            return False
    
    async def disconnect(self):
        """Отключение от сервера"""
        if self.channel:
            await self.channel.close()
            console.print("[bold yellow]🔌 Отключено от сервера[/bold yellow]")
    
    async def stream_audio(self, prompt: str):
        """Стриминг аудио и текста для промпта"""
        if not self.stub:
            console.print("[bold red]❌ Не подключен к серверу[/bold red]")
            return
        
        try:
            console.print(f"[bold yellow]🚀 Запуск gRPC стриминга для: {prompt}[/bold yellow]")
            
            # Запускаем воспроизведение заранее
            self.audio_player.start_playback()
            
            # Создаем запрос
            request = streaming_pb2.StreamRequest(prompt=prompt)
            
            # Запускаем стриминг
            async for response in self.stub.StreamAudio(request):
                # Обрабатываем разные типы ответов
                if response.HasField('text_chunk'):
                    console.print(f"[green]📄 Текст: {response.text_chunk}[/green]")
                
                elif response.HasField('audio_chunk'):
                    # Восстанавливаем NumPy массив из AudioChunk
                    audio_chunk = np.frombuffer(
                        response.audio_chunk.audio_data, 
                        dtype=response.audio_chunk.dtype
                    ).reshape(response.audio_chunk.shape)
                    
                    # Добавляем в плеер
                    self.audio_player.add_chunk(audio_chunk)
                
                elif response.HasField('end_message'):
                    console.print(f"[bold green]✅ {response.end_message}[/bold green]")
                    break
                
                elif response.HasField('error_message'):
                    console.print(f"[bold red]❌ Ошибка от сервера: {response.error_message}[/bold red]")
                    break
            
            # Ждем, пока все аудио в очереди будет воспроизведено
            self.audio_player.wait_for_queue_empty()
            self.audio_player.stop_playback()
            
        except grpc.RpcError as e:
            if e.code() == grpc.StatusCode.UNAVAILABLE:
                console.print("[bold red]❌ Сервер недоступен[/bold red]")
            elif e.code() == grpc.StatusCode.CANCELLED:
                console.print("[bold yellow]⚠️ Стриминг отменен[/bold yellow]")
            else:
                console.print(f"[bold red]❌ gRPC ошибка: {e.details()}[/bold red]")
        except Exception as e:
            console.print(f"[bold red]❌ Произошла непредвиденная ошибка: {e}[/bold red]")
        finally:
            if self.audio_player.is_playing:
                self.audio_player.stop_playback()

async def main():
    """Основная функция клиента"""
    client = GrpcClient()
    
    try:
        # Подключаемся к серверу
        if not await client.connect():
            return
        
        # Основной цикл
        while True:
            prompt = console.input("[bold cyan]🎤 Введите промпт (или 'quit'): [/bold cyan]")
            if prompt.lower() == 'quit':
                break
            
            # Запускаем стриминг
            await client.stream_audio(prompt)
    
    except KeyboardInterrupt:
        console.print("\n[bold yellow]👋 Выход...[/bold yellow]")
    except Exception as e:
        console.print(f"[bold red]❌ Произошла непредвиденная ошибка: {e}[/bold red]")
    finally:
        await client.disconnect()
        logger.info("gRPC клиент завершил работу.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[bold yellow]👋 Выход...[/bold yellow]")
