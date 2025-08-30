import asyncio
import logging
import numpy as np
import grpc
import sys
import os
import time
import yaml

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

def load_config():
    """Загружает конфигурацию из файла"""
    try:
        config_path = os.path.join(os.path.dirname(__file__), 'config', 'app_config.yaml')
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        console.print(f"[yellow]⚠️ Не удалось загрузить конфигурацию: {e}[/yellow]")
        return None

class GrpcClient:
    """gRPC клиент для стриминга аудио и текста"""
    
    def __init__(self, server_address: str = None):
        # Загружаем конфигурацию
        config = load_config()
        
        # Инициализируем настройки серверов
        self.servers = {
            'local': None,
            'production': None
        }
        self.current_server = None
        self.auto_fallback = True
        
        if server_address:
            # Прямой адрес передан
            self.server_address = server_address
            self.use_ssl = False
            self.servers['direct'] = {
                'address': server_address,
                'use_ssl': False,
                'timeout': 30,
                'retry_attempts': 3,
                'retry_delay': 1
            }
            self.current_server = 'direct'
        elif config and 'grpc' in config:
            # Загружаем конфигурацию серверов
            grpc_config = config['grpc']
            
            # Локальный сервер
            if 'local' in grpc_config:
                local_config = grpc_config['local']
                self.servers['local'] = {
                    'address': f"{local_config['server_host']}:{local_config['server_port']}",
                    'use_ssl': local_config.get('use_ssl', False),
                    'timeout': local_config.get('timeout', 10),
                    'retry_attempts': local_config.get('retry_attempts', 2),
                    'retry_delay': local_config.get('retry_delay', 0.5)
                }
            
            # Продакшн сервер
            if 'production' in grpc_config:
                prod_config = grpc_config['production']
                self.servers['production'] = {
                    'address': f"{prod_config['server_host']}:{prod_config['server_port']}",
                    'use_ssl': prod_config.get('use_ssl', False),
                    'timeout': prod_config.get('timeout', 30),
                    'retry_attempts': prod_config.get('retry_attempts', 3),
                    'retry_delay': prod_config.get('retry_delay', 1)
                }
            
            # Общие настройки
            self.auto_fallback = grpc_config.get('auto_fallback', True)
            
            # По умолчанию начинаем с ПРОДАКШН сервера (а не локального)
            if self.servers['production']:
                self.current_server = 'production'
                self.server_address = self.servers['production']['address']
                self.use_ssl = self.servers['production']['use_ssl']
            elif self.servers['local']:
                self.current_server = 'local'
                self.server_address = self.servers['local']['address']
                self.use_ssl = self.servers['local']['use_ssl']
        else:
            # Fallback на localhost
            self.server_address = "localhost:50051"
            self.use_ssl = False
            self.servers['fallback'] = {
                'address': "localhost:50051",
                'use_ssl': False,
                'timeout': 10,
                'retry_attempts': 2,
                'retry_delay': 0.5
            }
            self.current_server = 'fallback'
            
        self.audio_player = AudioPlayer(sample_rate=48000)
        self.channel = None
        self.stub = None
        self.hardware_id = None
        
        # Показываем информацию о доступных серверах
        console.print(f"[blue]🌐 Доступные серверы:[/blue]")
        for server_name, server_config in self.servers.items():
            if server_config:
                status = "✅ Текущий" if server_name == self.current_server else "⏳ Доступен"
                console.print(f"[blue]  • {server_name}: {server_config['address']} {status}[/blue]")
        
        console.print(f"[blue]🔄 Автопереключение: {'Включено' if self.auto_fallback else 'Отключено'}[/blue]")
    
    async def connect(self):
        """Подключение к gRPC серверу с автоматическим fallback"""
        return await self._try_connect_with_fallback()
    
    async def _try_connect_with_fallback(self):
        """Пытается подключиться к серверам с автоматическим fallback"""
        # Сначала пробуем текущий сервер
        if await self._try_connect_to_server(self.current_server):
            return True
        
        # Если не получилось и включен auto_fallback, пробуем другие серверы
        if self.auto_fallback:
            console.print(f"[yellow]🔄 Автопереключение: текущий сервер недоступен, пробую другие...[/yellow]")
            
            # Пробуем подключиться к другим доступным серверам
            for server_name, server_config in self.servers.items():
                if server_name != self.current_server and server_config:
                    console.print(f"[blue]🔄 Пробую подключиться к {server_name}: {server_config['address']}[/blue]")
                    
                    if await self._try_connect_to_server(server_name):
                        console.print(f"[bold green]✅ Автопереключение: подключился к {server_name}[/bold green]")
                        return True
            
            console.print(f"[bold red]❌ Не удалось подключиться ни к одному серверу[/bold red]")
            return False
        else:
            console.print(f"[bold red]❌ Подключение не удалось, автопереключение отключено[/bold red]")
            return False
    
    async def _try_connect_to_server(self, server_name):
        """Пытается подключиться к конкретному серверу"""
        if server_name not in self.servers or not self.servers[server_name]:
            return False
        
        server_config = self.servers[server_name]
        
        try:
            # Настройки для больших сообщений (аудио + скриншоты)
            options = [
                ('grpc.max_send_message_length', 50 * 1024 * 1024),  # 50MB
                ('grpc.max_receive_message_length', 50 * 1024 * 1024),  # 50MB
                ('grpc.max_metadata_size', 1024 * 1024),  # 1MB для метаданных
            ]
            
            # Закрываем предыдущее соединение если есть
            if self.channel:
                try:
                    await self.channel.close()
                except:
                    pass
            
            if server_config['use_ssl']:
                # Для Azure Container Apps используем SSL
                self.channel = grpc.aio.secure_channel(server_config['address'], grpc.ssl_channel_credentials(), options=options)
            else:
                # Для локального тестирования без SSL
                self.channel = grpc.aio.insecure_channel(server_config['address'], options=options)
                
            self.stub = streaming_pb2_grpc.StreamingServiceStub(self.channel)
            
            # Ждем готовности канала с таймаутом; если не готов — считаем, что сервер недоступен
            import asyncio as _asyncio
            try:
                await _asyncio.wait_for(self.channel.channel_ready(), timeout=server_config.get('timeout', 10))
            except Exception:
                console.print(f"[yellow]⚠️ Сервер {server_config['address']} не готов в течение таймаута[/yellow]")
                return False

            # Обновляем текущий сервер
            self.current_server = server_name
            self.server_address = server_config['address']
            self.use_ssl = server_config['use_ssl']
            
            console.print(f"[bold green]✅ Подключение к gRPC серверу {server_config['address']} установлено[/bold green]")
            console.print(f"[blue]📏 Максимальный размер сообщения: 50MB[/blue]")
            console.print(f"[blue]🔒 SSL: {'Включен' if server_config['use_ssl'] else 'Отключен'}[/blue]")
            console.print(f"[blue]🏷️ Сервер: {server_name}[/blue]")
            return True
            
        except Exception as e:
            console.print(f"[red]❌ Ошибка подключения к {server_name} ({server_config['address']}): {e}[/red]")
            return False
    
    def connect_sync(self):
        """Синхронное подключение к gRPC серверу (для восстановления соединения)"""
        try:
            # Пытаемся подключиться к текущему серверу
            if self._try_connect_sync_to_server(self.current_server):
                return True
            
            # Если не получилось и включен auto_fallback, пробуем другие серверы
            if self.auto_fallback:
                console.print(f"[yellow]🔄 Синхронное автопереключение: текущий сервер недоступен, пробую другие...[/yellow]")
                
                for server_name, server_config in self.servers.items():
                    if server_name != self.current_server and server_config:
                        console.print(f"[blue]🔄 Пробую синхронно подключиться к {server_name}: {server_config['address']}[/blue]")
                        
                        if self._try_connect_sync_to_server(server_name):
                            console.print(f"[bold green]✅ Синхронное автопереключение: подключился к {server_name}[/bold green]")
                            return True
                
                console.print(f"[bold red]❌ Не удалось синхронно подключиться ни к одному серверу[/bold red]")
                return False
            else:
                console.print(f"[bold red]❌ Синхронное подключение не удалось, автопереключение отключено[/bold red]")
                return False
                
        except Exception as e:
            console.print(f"[bold red]❌ Ошибка синхронного подключения: {e}[/bold red]")
            return False
    
    def _try_connect_sync_to_server(self, server_name):
        """Синхронно пытается подключиться к конкретному серверу"""
        if server_name not in self.servers or not self.servers[server_name]:
            return False
        
        server_config = self.servers[server_name]
        
        try:
            # Настройки для больших сообщений (аудио + скриншоты)
            options = [
                ('grpc.max_send_message_length', 50 * 1024 * 1024),  # 50MB
                ('grpc.max_receive_message_length', 50 * 1024 * 1024),  # 50MB
                ('grpc.max_metadata_size', 1024 * 1024),  # 1MB для метаданных
            ]
            
            # Закрываем предыдущее соединение если есть
            if self.channel:
                try:
                    self.channel.close()
                except:
                    pass
            
            # Создаем синхронный канал для восстановления с увеличенными лимитами
            import grpc
            self.channel = grpc.insecure_channel(server_config['address'], options=options)
            self.stub = streaming_pb2_grpc.StreamingServiceStub(self.channel)
            
            # Обновляем текущий сервер
            self.current_server = server_name
            self.server_address = server_config['address']
            self.use_ssl = server_config['use_ssl']
            
            console.print(f"[bold green]✅ Синхронное подключение к gRPC серверу {server_config['address']} восстановлено[/bold green]")
            console.print(f"[blue]📏 Максимальный размер сообщения: 50MB[/blue]")
            console.print(f"[blue]🏷️ Сервер: {server_name}[/blue]")
            return True
            
        except Exception as e:
            console.print(f"[red]❌ Ошибка синхронного подключения к {server_name} ({server_config['address']}): {e}[/red]")
            return False
    
    def switch_to_server(self, server_name):
        """Принудительно переключается на указанный сервер"""
        if server_name not in self.servers or not self.servers[server_name]:
            console.print(f"[red]❌ Сервер {server_name} недоступен[/red]")
            return False
        
        console.print(f"[blue]🔄 Принудительное переключение на сервер {server_name}...[/blue]")
        
        # Закрываем текущее соединение
        if self.channel:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.channel.close())
                else:
                    self.channel.close()
            except:
                pass
        
        # Переключаемся на новый сервер
        self.current_server = server_name
        server_config = self.servers[server_name]
        self.server_address = server_config['address']
        self.use_ssl = server_config['use_ssl']
        
        console.print(f"[bold green]✅ Переключение на сервер {server_name}: {server_config['address']}[/bold green]")
        return True
    
    def get_current_server_info(self):
        """Возвращает информацию о текущем сервере"""
        if self.current_server and self.current_server in self.servers:
            server_config = self.servers[self.current_server]
            return {
                'name': self.current_server,
                'address': server_config['address'],
                'use_ssl': server_config['use_ssl'],
                'is_connected': self.channel is not None and self.stub is not None
            }
        return None
    
    async def check_connection_health(self):
        """Проверяет состояние соединения и автоматически восстанавливает при необходимости"""
        if not self.channel or not self.stub:
            console.print(f"[yellow]⚠️ Соединение разорвано, пытаюсь восстановить...[/yellow]")
            return await self._try_connect_with_fallback()
        
        try:
            # Простая проверка соединения через ping
            import asyncio
            await asyncio.wait_for(self._ping_server(), timeout=2.0)
            return True
        except asyncio.TimeoutError:
            console.print(f"[yellow]⚠️ Таймаут проверки соединения, переподключаюсь...[/yellow]")
            return await self._try_connect_with_fallback()
        except Exception as e:
            console.print(f"[yellow]⚠️ Ошибка проверки соединения: {e}, переподключаюсь...[/yellow]")
            return await self._try_connect_with_fallback()
    
    async def _ping_server(self):
        """Простая проверка доступности сервера"""
        try:
            # Создаем простой запрос для проверки
            request = streaming_pb2.StreamRequest(
                prompt="__GREETING__:ping",
                screenshot="",
                screen_width=0,
                screen_height=0,
                hardware_id=self.hardware_id or "ping_test"
            )
            
            # Пытаемся отправить запрос с коротким таймаутом
            call = self.stub.StreamAudio(request)
            await asyncio.wait_for(call.__anext__(), timeout=1.0)
            call.cancel()
            return True
        except Exception:
            return False
    
    def get_servers_status(self):
        """Возвращает статус всех доступных серверов"""
        status = {}
        for server_name, server_config in self.servers.items():
            if server_config:
                status[server_name] = {
                    'address': server_config['address'],
                    'use_ssl': server_config['use_ssl'],
                    'is_current': server_name == self.current_server,
                    'is_connected': (server_name == self.current_server and 
                                   self.channel is not None and self.stub is not None)
                }
        return status
    
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
            if self.stub:
                try:
                    # Создаем запрос прерывания
                    interrupt_request = streaming_pb2.InterruptSessionRequest(
                        session_id="force_interrupt",
                        reason="user_interruption"
                    )
                    
                    # Отправляем запрос прерывания
                    console.print("[blue]🔍 Отправляю запрос прерывания на сервер...[/blue]")
                    logger.info("   🔍 Отправляю запрос прерывания на сервер...")
                    
                    # Создаем задачу для асинхронного вызова
                    import asyncio
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # Создаем задачу для асинхронного вызова
                        loop.create_task(self._send_interrupt_request(interrupt_request))
                    else:
                        console.print("[yellow]⚠️ Цикл событий не запущен[/yellow]")
                        
                except Exception as e:
                    console.print(f"[red]❌ Ошибка отправки запроса прерывания: {e}[/red]")
                    logger.error(f"   ❌ Ошибка отправки запроса прерывания: {e}")
            else:
                console.print("[yellow]⚠️ gRPC stub недоступен[/yellow]")
                logger.warning("   ⚠️ gRPC stub недоступен")
                
        except Exception as e:
            console.print(f"[red]❌ Ошибка в force_interrupt_server: {e}[/red]")
            logger.error(f"   ❌ Ошибка в force_interrupt_server: {e}")
    
    async def _send_interrupt_request(self, interrupt_request):
        """Асинхронно отправляет запрос прерывания на сервер"""
        try:
            console.print("[blue]🔍 Асинхронно отправляю запрос прерывания...[/blue]")
            logger.info("   🔍 Асинхронно отправляю запрос прерывания...")
            
            # Вызываем метод InterruptSession
            response = await self.stub.InterruptSession(interrupt_request)
            
            console.print(f"[bold green]✅ Прерывание на сервере успешно! Ответ: {response}[/bold green]")
            logger.info(f"   ✅ Прерывание на сервере успешно! Ответ: {response}")
            
        except Exception as e:
            console.print(f"[red]❌ Ошибка асинхронной отправки прерывания: {e}[/red]")
            logger.error(f"   ❌ Ошибка асинхронной отправки прерывания: {e}")
    
    def close_connection(self):
        """ПРИНУДИТЕЛЬНО закрывает gRPC соединение"""
        logger.info(f"🚨 close_connection() вызван в {time.time():.3f}")
        
        try:
            console.print("[bold red]🚨 ПРИНУДИТЕЛЬНО закрываю gRPC соединение![/bold red]")
            logger.info("   🚨 ПРИНУДИТЕЛЬНО закрываю gRPC соединение!")
            
            # 1️⃣ Закрываем канал
            if self.channel:
                try:
                    # Создаем задачу для асинхронного закрытия
                    import asyncio
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # Создаем задачу для закрытия
                        close_task = loop.create_task(self._force_close_channel())
                        console.print("[blue]🔍 Задача закрытия канала создана[/blue]")
                    else:
                        # Если цикл не запущен, закрываем напрямую
                        self.channel.close()
                        console.print("[bold green]✅ gRPC канал закрыт напрямую[/bold green]")
                except Exception as e:
                    console.print(f"[red]❌ Ошибка закрытия канала: {e}[/red]")
                    logger.error(f"   ❌ Ошибка закрытия канала: {e}")
            
            # 2️⃣ Сбрасываем stub
            self.stub = None
            console.print("[bold green]✅ gRPC stub сброшен[/bold green]")
            
            # 3️⃣ Сбрасываем канал
            self.channel = None
            console.print("[bold green]✅ gRPC канал сброшен[/bold green]")
            
            logger.info("   ✅ gRPC соединение принудительно закрыто")
            
        except Exception as e:
            console.print(f"[red]❌ Ошибка в close_connection: {e}[/red]")
            logger.error(f"   ❌ Ошибка в close_connection: {e}")
    
    async def _force_close_channel(self):
        """Принудительно закрывает gRPC канал"""
        try:
            console.print("[blue]🔍 Принудительно закрываю gRPC канал...[/blue]")
            logger.info("   🔍 Принудительно закрываю gRPC канал...")
            
            # Проверяем, что канал существует
            if self.channel is None:
                console.print("[yellow]⚠️ gRPC канал уже закрыт или не существует[/yellow]")
                logger.info("   ⚠️ gRPC канал уже закрыт или не существует")
                return
            
            # Закрываем канал
            await self.channel.close()
            
            console.print("[bold green]✅ gRPC канал принудительно закрыт[/bold green]")
            logger.info("   ✅ gRPC канал принудительно закрыт")
            
        except Exception as e:
            console.print(f"[red]❌ Ошибка принудительного закрытия канала: {e}[/red]")
            logger.error(f"   ❌ Ошибка принудительного закрытия канала: {e}")
    
    def reset_state(self):
        """Сбрасывает состояние gRPC клиента"""
        logger.info(f"🚨 reset_state() вызван в {time.time():.3f}")
        
        try:
            console.print("[bold blue]🔄 Сбрасываю состояние gRPC клиента...[/bold blue]")
            logger.info("   🔄 Сбрасываю состояние gRPC клиента...")
            
            # 1️⃣ Сбрасываем stub
            self.stub = None
            console.print("[green]✅ gRPC stub сброшен[/green]")
            
            # 2️⃣ Сбрасываем канал
            self.channel = None
            console.print("[green]✅ gRPC канал сброшен[/green]")
            
            # 3️⃣ Сбрасываем аудио плеер
            if self.audio_player:
                try:
                    if hasattr(self.audio_player, 'clear_all_audio_data'):
                        self.audio_player.clear_all_audio_data()
                        console.print("[green]✅ Аудио плеер очищен[/green]")
                    elif hasattr(self.audio_player, 'force_stop'):
                        self.audio_player.force_stop()
                        console.print("[green]✅ Аудио плеер остановлен[/green]")
                except Exception as e:
                    console.print(f"[yellow]⚠️ Ошибка сброса аудио плеера: {e}[/yellow]")
                    logger.warning(f"   ⚠️ Ошибка сброса аудио плеера: {e}")
            
            console.print("[bold green]✅ Состояние gRPC клиента сброшено![/bold green]")
            logger.info("   ✅ Состояние gRPC клиента сброшено!")
            
        except Exception as e:
            console.print(f"[red]❌ Ошибка в reset_state: {e}[/red]")
            logger.error(f"   ❌ Ошибка в reset_state: {e}")
    
    def clear_buffers(self):
        """Очищает все gRPC буферы"""
        logger.info(f"🧹 clear_buffers() вызван в {time.time():.3f}")
        
        try:
            console.print("[bold blue]🧹 Очищаю все gRPC буферы...[/bold blue]")
            logger.info("   🧹 Очищаю все gRPC буферы...")
            
            # 1️⃣ Очищаем буферы канала
            if self.channel and hasattr(self.channel, 'close'):
                try:
                    # Принудительно закрываем канал для очистки буферов
                    # Создаем задачу для асинхронного закрытия
                    import asyncio
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        loop.create_task(self._force_close_channel())
                        console.print("[blue]🔍 Задача очистки gRPC буферов создана[/blue]")
                    else:
                        # Если цикл не запущен, закрываем напрямую
                        self.channel.close()
                        console.print("[bold green]✅ gRPC буферы очищены напрямую[/bold green]")
                except Exception as e:
                    console.print(f"[yellow]⚠️ Ошибка очистки gRPC буферов: {e}[/yellow]")
                    logger.warning(f"   ⚠️ Ошибка очистки gRPC буферов: {e}")
            else:
                console.print("[blue]ℹ️ gRPC канал уже закрыт или не существует[/blue]")
                logger.info("   ℹ️ gRPC канал уже закрыт или не существует")
            
            # 2️⃣ Очищаем буферы stub
            if self.stub:
                self.stub = None
                console.print("[green]✅ gRPC stub буферы очищены[/green]")
            
            # 3️⃣ Очищаем системные буферы
            import gc
            gc.collect()
            console.print("[green]✅ Системные буферы очищены[/green]")
            
            console.print("[bold green]✅ Все gRPC буферы очищены![/bold green]")
            logger.info("   ✅ Все gRPC буферы очищены!")
            
        except Exception as e:
            console.print(f"[red]❌ Ошибка в clear_buffers: {e}[/red]")
            logger.error(f"   ❌ Ошибка в clear_buffers: {e}")
    
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
            
            # 🔍 ДЕТАЛЬНОЕ ЛОГИРОВАНИЕ ПЕРЕД СОЗДАНИЕМ ЗАПРОСА
            console.print(f"[cyan]🔍 Создаю StreamRequest с параметрами:[/cyan]")
            console.print(f"[cyan]🔍 prompt: '{prompt}' (тип: {type(prompt).__name__})[/cyan]")
            console.print(f"[cyan]🔍 screenshot: {'Да' if screenshot_base64 else 'Нет'} (тип: {type(screenshot_base64).__name__})[/cyan]")
            if screenshot_base64:
                console.print(f"[cyan]🔍 screenshot длина: {len(screenshot_base64)} символов[/cyan]")
            
            console.print(f"[cyan]🔍 screen_info: {screen_info} (тип: {type(screen_info).__name__})[/cyan]")
            if screen_info:
                console.print(f"[cyan]🔍 screen_width: {screen_info.get('width', 'НЕТ')} (тип: {type(screen_info.get('width', 0)).__name__})[/cyan]")
                console.print(f"[cyan]🔍 screen_height: {screen_info.get('height', 'НЕТ')} (тип: {type(screen_info.get('height', 0)).__name__})[/cyan]")
            
            console.print(f"[cyan]🔍 hardware_id: '{hardware_id}' (тип: {type(hardware_id).__name__})[/cyan]")
            
            self.audio_player.start_playback()
            
            try:
                request = streaming_pb2.StreamRequest(
                    prompt=prompt,
                    screenshot=screenshot_base64 if screenshot_base64 else "",
                    screen_width=screen_info.get('width', 0) if screen_info else 0,
                    screen_height=screen_info.get('height', 0) if screen_info else 0,
                    hardware_id=hardware_id if hardware_id else ""
                )
                console.print(f"[green]✅ StreamRequest создан успешно[/green]")
            except Exception as request_error:
                console.print(f"[bold red]❌ ОШИБКА ПРИ СОЗДАНИИ StreamRequest: {request_error}[/bold red]")
                console.print(f"[bold red]❌ Тип ошибки: {type(request_error).__name__}[/bold red]")
                console.print(f"[bold red]❌ Детали: {str(request_error)}[/bold red]")
                
                # 🔍 ДОПОЛНИТЕЛЬНАЯ ДИАГНОСТИКА
                import traceback
                console.print(f"[bold red]❌ Traceback создания запроса:[/bold red]")
                for line in traceback.format_exc().split('\n'):
                    if line.strip():
                        console.print(f"[red]   {line}[/red]")
                
                # Пытаемся создать запрос с безопасными значениями
                console.print(f"[yellow]🔄 Пытаюсь создать запрос с безопасными значениями...[/yellow]")
                try:
                    safe_request = streaming_pb2.StreamRequest(
                        prompt=str(prompt) if prompt else "",
                        screenshot="",
                        screen_width=0,
                        screen_height=0,
                        hardware_id=str(hardware_id) if hardware_id else ""
                    )
                    console.print(f"[green]✅ Безопасный StreamRequest создан[/green]")
                    request = safe_request
                except Exception as safe_error:
                    console.print(f"[bold red]❌ Даже безопасный запрос не создается: {safe_error}[/bold red]")
                    raise  # Перебрасываем ошибку
            
            call = self.stub.StreamAudio(request)
            
            # Сразу возвращаем объект вызова, чтобы main мог его отменить
            yield call
            
            async for response in call:
                # 🔍 ДЕТАЛЬНОЕ ЛОГИРОВАНИЕ КАЖДОГО ОТВЕТА
                console.print(f"[cyan]🔍 Получен ответ типа: {type(response).__name__}[/cyan]")
                console.print(f"[cyan]🔍 Поля ответа: {[field.name for field in response.DESCRIPTOR.fields]}[/cyan]")
                
                if response.HasField('text_chunk'):
                    console.print(f"[green]📄 Текст: {response.text_chunk}[/green]")
                
                elif response.HasField('audio_chunk'):
                    # 🔍 ДЕТАЛЬНОЕ ЛОГИРОВАНИЕ АУДИО ЧАНКА
                    console.print(f"[cyan]🔍 Обрабатываю аудио чанк...[/cyan]")
                    
                    # Логируем информацию об аудио чанке
                    audio_chunk_obj = response.audio_chunk
                    console.print(f"[cyan]🔍 Тип audio_chunk: {type(audio_chunk_obj).__name__}[/cyan]")
                    console.print(f"[cyan]🔍 Поля audio_chunk: {[field.name for field in audio_chunk_obj.DESCRIPTOR.fields]}[/cyan]")
                    
                    # Логируем audio_data
                    audio_data = audio_chunk_obj.audio_data
                    console.print(f"[cyan]🔍 Тип audio_data: {type(audio_data).__name__}[/cyan]")
                    console.print(f"[cyan]🔍 Размер audio_data: {len(audio_data)} байт[/cyan]")
                    console.print(f"[cyan]🔍 Первые 10 байт: {audio_data[:10]}[/cyan]")
                    
                    # Логируем dtype
                    dtype_str = audio_chunk_obj.dtype
                    console.print(f"[cyan]🔍 dtype строка: '{dtype_str}' (тип: {type(dtype_str).__name__})[/cyan]")
                    
                    # Логируем shape
                    shape = audio_chunk_obj.shape
                    console.print(f"[cyan]🔍 shape: {shape} (тип: {type(shape).__name__})[/cyan]")
                    
                    try:
                        # 🔧 ИСПРАВЛЕНИЕ: конвертируем строку dtype в numpy dtype
                        if dtype_str == 'int16':
                            dtype = np.int16
                        elif dtype_str == 'float32':
                            dtype = np.float32
                        elif dtype_str == 'float64':
                            dtype = np.float64
                        else:
                            # Fallback на int16 если dtype не распознан
                            dtype = np.int16
                            console.print(f"[yellow]⚠️ Неизвестный dtype '{dtype_str}', использую int16[/yellow]")
                        
                        console.print(f"[cyan]🔍 Выбранный numpy dtype: {dtype}[/cyan]")
                        
                        # Создаем numpy массив
                        console.print(f"[cyan]🔍 Создаю numpy массив...[/cyan]")
                        audio_chunk = np.frombuffer(audio_data, dtype=dtype)
                        console.print(f"[cyan]🔍 numpy массив создан: {type(audio_chunk).__name__}, размер: {audio_chunk.shape}[/cyan]")
                        
                        # Применяем reshape
                        console.print(f"[cyan]🔍 Применяю reshape к {shape}...[/cyan]")
                        audio_chunk = audio_chunk.reshape(shape)
                        console.print(f"[cyan]🔍 reshape применен: {audio_chunk.shape}[/cyan]")
                        
                        console.print(f"[blue]🎵 Аудио чанк получен: {len(audio_chunk)} сэмплов[/blue]")
                        
                        # Добавляем в плеер
                        console.print(f"[cyan]🔍 Добавляю в аудио плеер...[/cyan]")
                        self.audio_player.add_chunk(audio_chunk)
                        console.print(f"[green]✅ Аудио добавлено в плеер[/green]")
                        
                    except Exception as audio_error:
                        console.print(f"[bold red]❌ ОШИБКА ПРИ ОБРАБОТКЕ АУДИО: {audio_error}[/bold red]")
                        console.print(f"[bold red]❌ Тип ошибки: {type(audio_error).__name__}[/bold red]")
                        console.print(f"[bold red]❌ Детали: {str(audio_error)}[/bold red]")
                        # Продолжаем обработку других чанков
                        continue
                
                elif response.HasField('end_message'):
                    console.print(f"[bold green]✅ {response.end_message}[/bold green]")
                    break
                
                elif response.HasField('error_message'):
                    console.print(f"[bold red]❌ Ошибка от сервера: {response.error_message}[/bold red]")
                    break
            
            # НЕ вызываем wait_for_queue_empty - пусть аудио воспроизводится естественным образом
            # self.audio_player.wait_for_queue_empty()
            
            # Запускаем ожидание естественного завершения воспроизведения
            # self.audio_player.wait_for_natural_completion()  # ← ЭТОТ МЕТОД НЕ СУЩЕСТВУЕТ!
            
            # Используем существующий метод для проверки статуса
            if hasattr(self.audio_player, 'wait_for_queue_empty'):
                # Проверяем статус без блокировки
                is_completed = self.audio_player.wait_for_queue_empty()
                if is_completed:
                    console.print("[blue]🎵 Аудио уже завершено[/blue]")
                else:
                    console.print("[blue]🎵 Аудио продолжает воспроизводиться...[/blue]")
            else:
                console.print("[yellow]⚠️ Метод wait_for_queue_empty недоступен[/yellow]")
            
            # Логируем завершение стрима, но НЕ останавливаем воспроизведение
            console.print("[bold green]✅ gRPC стрим завершен, аудио продолжает воспроизводиться...[/bold green]")
            
        except grpc.aio.AioRpcError as e:
            if e.code() == grpc.StatusCode.CANCELLED:
                console.print("[bold yellow]⚠️ Стриминг отменен клиентом[/bold yellow]")
            elif e.code() == grpc.StatusCode.UNAVAILABLE:
                console.print(f"[bold red]❌ Сервер недоступен: {e.details()}[/bold red]")
                # Пытаемся автоматически переподключиться к другому серверу
                if self.auto_fallback:
                    console.print(f"[yellow]🔄 Автоматическое переподключение при ошибке UNAVAILABLE...[/yellow]")
                    if await self._try_connect_with_fallback():
                        console.print(f"[bold green]✅ Автопереподключение успешно![/bold green]")
                    else:
                        console.print(f"[bold red]❌ Автопереподключение не удалось[/bold red]")
            else:
                console.print(f"[bold red]❌ gRPC ошибка: {e.details()} (код: {e.code()})[/bold red]")
        except Exception as e:
            console.print(f"[bold red]❌ Произошла непредвиденная ошибка в стриминге: {e}[/bold red]")
            console.print(f"[bold red]❌ Тип ошибки: {type(e).__name__}[/bold red]")
            console.print(f"[bold red]❌ Детали: {str(e)}[/bold red]")
            
            # 🔍 ДОПОЛНИТЕЛЬНАЯ ДИАГНОСТИКА
            import traceback
            console.print(f"[bold red]❌ Traceback:[/bold red]")
            for line in traceback.format_exc().split('\n'):
                if line.strip():
                    console.print(f"[red]   {line}[/red]")
        finally:
            # НЕ останавливаем воспроизведение автоматически - пусть аудио играет до конца
            # if self.audio_player.is_playing:
            #     self.audio_player.stop_playback()
            
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
