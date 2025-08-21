import asyncio
import logging
import numpy as np
import grpc
import sys
import os
import time

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
    
    def interrupt_stream(self):
        """МГНОВЕННО прерывает активный gRPC стриминг на сервере!"""
        try:
            console.print(f"[bold red]🔍 ДИАГНОСТИКА gRPC: channel={self.channel}, stub={self.stub}[/bold red]")
            
            if self.channel:
                # Проверяем статус канала
                try:
                    is_closed = self.channel.closed()
                    console.print(f"[blue]🔍 Канал закрыт: {is_closed}[/blue]")
                except AttributeError:
                    console.print("[blue]🔍 Метод .closed() недоступен, пробуем другой способ[/blue]")
                    is_closed = False
                
                if not is_closed:
                    # МГНОВЕННО закрываем канал - это принудительно прервет все активные вызовы!
                    console.print("[bold red]🚨 ЗАКРЫВАЮ gRPC канал...[/bold red]")
                    
                    # КРИТИЧНО: channel.close() - это корутина, нужно создать задачу для её выполнения
                    import asyncio
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # Создаем задачу для асинхронного закрытия канала
                        console.print("[blue]🔍 Создаю задачу для закрытия канала...[/blue]")
                        loop.create_task(self._close_channel_and_recreate())
                    else:
                        # Если цикл не запущен, создаем канал напрямую
                        console.print("[blue]🔍 Создаю канал напрямую...[/blue]")
                        self.channel = grpc.aio.insecure_channel(self.server_address)
                        self.stub = streaming_pb2_grpc.StreamingServiceStub(self.channel)
                        console.print("[bold green]✅ Новый gRPC канал создан для следующих вызовов[/bold green]")
                else:
                    console.print("[yellow]⚠️ gRPC канал уже закрыт[/yellow]")
            else:
                console.print("[yellow]⚠️ gRPC канал = None[/yellow]")
        except Exception as e:
            console.print(f"[red]⚠️ Ошибка прерывания gRPC стриминга: {e}[/red]")
            import traceback
            console.print(f"[red]🔍 Traceback: {traceback.format_exc()}[/red]")
    
    def force_interrupt_server(self):
        """ПРИНУДИТЕЛЬНОЕ прерывание на сервере через вызов InterruptSession!"""
        logger.info(f"🚨 force_interrupt_server() вызван в {time.time():.3f}")
        
        try:
            console.print("[bold red]🚨 ПРИНУДИТЕЛЬНОЕ прерывание на СЕРВЕРЕ![/bold red]")
            logger.info("   🚨 ПРИНУДИТЕЛЬНОЕ прерывание на СЕРВЕРЕ!")
            
            # КРИТИЧНО: вызываем новый метод InterruptSession на сервере!
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Создаем задачу для принудительного прерывания на сервере
                logger.info("   🔄 Создаю задачу для прерывания на сервере...")
                loop.create_task(self._force_interrupt_server_call())
                console.print("[bold red]🚨 Задача принудительного прерывания на сервере запущена![/bold red]")
            else:
                # Если цикл не запущен, вызываем синхронно
                console.print("[blue]🔍 Вызываю прерывание синхронно...[/blue]")
                self._force_interrupt_server_sync()
        except Exception as e:
            console.print(f"[red]⚠️ Ошибка принудительного прерывания: {e}[/red]")
            import traceback
            console.print(f"[red]🔍 Traceback: {traceback.format_exc()}[/red]")
    
    def interrupt_immediately(self):
        """СИНХРОННОЕ мгновенное прерывание - атомарная операция!"""
        try:
            console.print("[bold red]🚨 СИНХРОННОЕ мгновенное прерывание![/bold red]")
            
            # 1. НЕМЕДЛЕННО отменяем текущий вызов
            if hasattr(self, 'current_call') and self.current_call and not self.current_call.done():
                self.current_call.cancel()
                console.print("[bold red]🚨 Текущий gRPC вызов ОТМЕНЕН![/bold red]")
            
            # 2. Создаем НОВЫЙ канал ТОЛЬКО для команды прерывания
            import grpc
            interrupt_channel = grpc.insecure_channel(self.server_address)
            interrupt_stub = streaming_pb2_grpc.StreamingServiceStub(interrupt_channel)
            
            # 3. СИНХРОННО вызываем InterruptSession
            if hasattr(self, 'hardware_id') and self.hardware_id:
                request = streaming_pb2.InterruptRequest(hardware_id=self.hardware_id)
                try:
                    response = interrupt_stub.InterruptSession(request, timeout=0.5)
                    console.print(f"[bold green]✅ Сервер прервал {len(response.interrupted_sessions)} сессий![/bold green]")
                except Exception as e:
                    console.print(f"[red]⚠️ Ошибка вызова InterruptSession: {e}[/red]")
                finally:
                    interrupt_channel.close()
                    console.print("[bold red]🚨 Канал прерывания закрыт![/bold red]")
            else:
                console.print("[yellow]⚠️ Hardware ID недоступен для прерывания[/yellow]")
                
        except Exception as e:
            console.print(f"[red]⚠️ Ошибка синхронного прерывания: {e}[/red]")
            import traceback
            console.print(f"[red]🔍 Traceback: {traceback.format_exc()}[/red]")
    
    async def _force_interrupt_server_call(self):
        """Асинхронно вызывает прерывание на сервере"""
        logger.info(f"🚨 _force_interrupt_server_call() начат в {time.time():.3f}")
        
        try:
            if hasattr(self, 'hardware_id') and self.hardware_id:
                logger.info(f"   🆔 Hardware ID: {self.hardware_id[:20]}...")
                
                # Создаем запрос на прерывание
                request = streaming_pb2.InterruptRequest(hardware_id=self.hardware_id)
                logger.info("   📤 Создан InterruptRequest")
                
                # Вызываем метод на сервере
                logger.info("   🔄 Вызываю stub.InterruptSession...")
                start_time = time.time()
                response = await self.stub.InterruptSession(request)
                call_time = (time.time() - start_time) * 1000
                logger.info(f"   ⏱️ stub.InterruptSession: {call_time:.1f}ms")
                
                if response.success:
                    logger.info(f"   ✅ Сервер успешно прервал {len(response.interrupted_sessions)} сессий")
                    console.print(f"[bold green]✅ Сервер успешно прервал {len(response.interrupted_sessions)} сессий![/bold green]")
                    console.print(f"[bold green]✅ Прерванные сессии: {response.interrupted_sessions}[/bold green]")
                else:
                    logger.warning("   ⚠️ Сервер не нашел активных сессий для прерывания")
                    console.print(f"[yellow]⚠️ Сервер не нашел активных сессий для прерывания[/yellow]")
            else:
                logger.warning("   ⚠️ Hardware ID недоступен для прерывания")
                console.print("[yellow]⚠️ Hardware ID недоступен для прерывания[/yellow]")
        except Exception as e:
            logger.error(f"   ❌ Ошибка вызова прерывания на сервере: {e}")
            console.print(f"[red]⚠️ Ошибка вызова прерывания на сервере: {e}[/red]")
        
        logger.info(f"   🏁 _force_interrupt_server_call завершен в {time.time():.3f}")
    
    def _force_interrupt_server_sync(self):
        """Синхронно вызывает прерывание на сервере (fallback)"""
        try:
            if hasattr(self, 'hardware_id') and self.hardware_id:
                # Создаем запрос на прерывание
                request = streaming_pb2.InterruptRequest(hardware_id=self.hardware_id)
                
                # Вызываем метод на сервере синхронно
                response = self.stub.InterruptSession(request)
                
                if response.success:
                    console.print(f"[bold green]✅ Сервер успешно прервал {len(response.interrupted_sessions)} сессий![/bold green]")
                    console.print(f"[bold green]✅ Прерванные сессии: {response.interrupted_sessions}[/bold green]")
                else:
                    console.print(f"[yellow]⚠️ Сервер не нашел активных сессий для прерывания[/yellow]")
            else:
                console.print("[yellow]⚠️ Hardware ID недоступен для прерывания[/yellow]")
        except Exception as e:
            console.print(f"[red]⚠️ Ошибка вызова прерывания на сервере: {e}[/red]")
    
    async def _force_recreate_channel(self):
        """Принудительно создает новый канал для прерывания старого"""
        try:
            # Сначала закрываем старый канал
            if self.channel:
                try:
                    await self.channel.close()
                    console.print("[bold red]🚨 Старый канал ПРИНУДИТЕЛЬНО закрыт![/bold red]")
                except:
                    pass
            
            # Создаем новый канал
            self.channel = grpc.aio.insecure_channel(self.server_address)
            self.stub = streaming_pb2_grpc.StreamingServiceStub(self.channel)
            console.print("[bold green]✅ Новый gRPC канал создан для принудительного прерывания[/bold green]")
        except Exception as e:
            console.print(f"[red]⚠️ Ошибка принудительного создания канала: {e}[/red]")
    
    async def _close_channel_and_recreate(self):
        """Асинхронно закрывает канал и воссоздает его"""
        try:
            # Асинхронно закрываем канал
            await self.channel.close()
            console.print("[bold red]🚨 МГНОВЕННОЕ прерывание gRPC канала![/bold red]")
            
            # Создаем новый канал
            await self._recreate_channel()
        except Exception as e:
            console.print(f"[red]⚠️ Ошибка закрытия канала: {e}[/red]")
    
    async def _recreate_channel(self):
        """Воссоздает gRPC канал асинхронно"""
        try:
            self.channel = grpc.aio.insecure_channel(self.server_address)
            self.stub = streaming_pb2_grpc.StreamingServiceStub(self.channel)
            console.print("[bold green]✅ Новый gRPC канал создан для следующих вызовов[/bold green]")
        except Exception as e:
            console.print(f"[red]⚠️ Ошибка воссоздания gRPC канала: {e}[/red]")
    
    async def stream_audio(self, prompt: str, screenshot_base64: str = None, screen_info: dict = None, hardware_id: str = None):
        """
        Запускает стриминг аудио и текста.
        Эта функция является асинхронным генератором, который сначала возвращает 
        объект вызова (для возможности отмены), а затем ничего не возвращает, 
        поскольку обработка происходит внутри.
        """
        if not self.stub:
            console.print("[bold red]❌ Не подключен к серверу[/bold red]")
            return
        
        call = None
        try:
            console.print(f"[bold yellow]🚀 Запуск gRPC стриминга для: {prompt}[/bold yellow]")
            
            if screenshot_base64:
                console.print(f"[bold blue]📸 Отправляю скриншот: {screen_info.get('width', 0)}x{screen_info.get('height', 0)} пикселей[/bold blue]")
            
            if hardware_id:
                console.print(f"[bold blue]🆔 Отправляю Hardware ID: {hardware_id[:16]}...[/bold blue]")
            
            self.audio_player.start_playback()
            
            request = streaming_pb2.StreamRequest(
                prompt=prompt,
                screenshot=screenshot_base64 if screenshot_base64 else "",
                screen_width=screen_info.get('width', 0) if screen_info else 0,
                screen_height=screen_info.get('height', 0) if screen_info else 0,
                hardware_id=hardware_id if hardware_id else ""
            )
            
            call = self.stub.StreamAudio(request)
            
            # Сразу возвращаем объект вызова, чтобы main мог его отменить
            yield call
            
            async for response in call:
                if response.HasField('text_chunk'):
                    console.print(f"[green]📄 Текст: {response.text_chunk}[/green]")
                
                elif response.HasField('audio_chunk'):
                    audio_chunk = np.frombuffer(
                        response.audio_chunk.audio_data, 
                        dtype=response.audio_chunk.dtype
                    ).reshape(response.audio_chunk.shape)
                    console.print(f"[blue]🎵 Аудио чанк получен: {len(audio_chunk)} сэмплов[/blue]")
                    self.audio_player.add_chunk(audio_chunk)
                
                elif response.HasField('end_message'):
                    console.print(f"[bold green]✅ {response.end_message}[/bold green]")
                    break
                
                elif response.HasField('error_message'):
                    console.print(f"[bold red]❌ Ошибка от сервера: {response.error_message}[/bold red]")
                    break
            
            # ПРАВИЛЬНАЯ логика завершения воспроизведения
            # Когда gRPC стрим заканчивается, аудио должно естественно завершиться
            # после воспроизведения всех полученных чанков
            logger.info("🎵 gRPC стрим завершен, ожидаю естественного завершения воспроизведения...")
            
            # Ждем завершения воспроизведения всех полученных чанков
            # НЕ останавливаем принудительно - пусть аудио играет до конца
            while self.audio_player.is_playing:
                # Проверяем, есть ли еще чанки для воспроизведения
                queue_size = self.audio_player.audio_queue.qsize()
                with self.audio_player.buffer_lock:
                    buffer_size = len(self.audio_player.internal_buffer)
                
                if queue_size == 0 and buffer_size == 0:
                    logger.info("✅ Все чанки воспроизведены, воспроизведение завершено естественным образом")
                    break
                
                # Ждем немного и проверяем снова
                await asyncio.sleep(0.1)  # 100ms
            
        except grpc.aio.AioRpcError as e:
            if e.code() == grpc.StatusCode.CANCELLED:
                console.print("[bold yellow]⚠️ Стриминг отменен клиентом[/bold yellow]")
            else:
                console.print(f"[bold red]❌ gRPC ошибка: {e.details()}[/bold red]")
        except Exception as e:
            console.print(f"[bold red]❌ Произошла непредвиденная ошибка в стриминге: {e}[/bold red]")
        finally:
            # УБИРАЕМ дублирующую логику прерывания!
            # Аудио должно воспроизводиться естественным образом до конца
            # Прерывание уже реализовано в StateManager через пробел
            
            # Убеждаемся, что call завершен, если он был создан
            if call and not call.done():
                call.cancel()

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
