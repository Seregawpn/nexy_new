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
    LISTENING = 1     # Ассистент слушает команды (микрофон активен)
    IN_PROCESS = 2    # Ассистент работает (обрабатывает команду или говорит)
    SLEEPING = 3      # Ассистент спит, ждет команды (микрофон неактивен)

class StateManager:
    """
    Управляет переходами между состояниями приложения.
    Каждое состояние знает, как реагировать на каждое событие.
    """
    
    def __init__(self, console, audio_player, stt_recognizer, screen_capture, grpc_client, hardware_id, input_handler=None):
        self.console = console
        self.audio_player = audio_player
        self.stt_recognizer = stt_recognizer
        self.screen_capture = screen_capture
        self.grpc_client = grpc_client
        self.hardware_id = hardware_id
        self.input_handler = input_handler  # Ссылка на InputHandler для синхронизации
        
        # Состояние приложения
        self.state = AppState.SLEEPING
        self.active_call = None
        self.streaming_task = None
        self.current_screenshot = None
        self.current_screen_info = None
        
        # Время начала прерывания для логирования
        self.interrupt_start_time = time.time()
        
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
        """ПРОБЕЛ ЗАЖАТ - включаем микрофон"""
        
        if self.state == AppState.SLEEPING:
            # Переходим в LISTENING и включаем микрофон
            self.set_state(AppState.LISTENING)
            self.stt_recognizer.start_recording()
            self.console.print("[green]🎤 Микрофон включен - говорите команду[/green]")
            logger.info("   🎤 Микрофон активирован из состояния SLEEPING")
        
        elif self.state == AppState.IN_PROCESS:
            # Прерываем работу и переходим в LISTENING
            self.console.print("[bold yellow]🔇 Ассистент работает - ПРЕРЫВАЮ и перехожу в LISTENING![/bold yellow]")
            logger.info("   🚨 Прерывание работы ассистента")
            
            # 🚨 ИСПОЛЬЗУЕМ УНИВЕРСАЛЬНЫЙ МЕТОД!
            success = self.force_stop_everything()
            
            if success:
                logger.info("   ✅ Универсальная остановка успешна")
                self.console.print("[bold green]✅ ВСЕ ПРИНУДИТЕЛЬНО ОСТАНОВЛЕНО![/bold green]")
            else:
                logger.warning("   ⚠️ Универсальная остановка неполная")
                self.console.print("[yellow]⚠️ Остановка неполная[/yellow]")
            
            # Переходим в LISTENING и включаем микрофон
            self.set_state(AppState.LISTENING)
            self.stt_recognizer.start_recording()
            self.console.print("[bold green]✅ Переход в LISTENING - микрофон включен![/bold green]")
            logger.info("   🎤 Микрофон активирован после прерывания")
            
            # СБРАСЫВАЕМ ФЛАГИ В INPUT_HANDLER
            if self.input_handler and hasattr(self.input_handler, 'reset_interrupt_flag'):
                self.input_handler.reset_interrupt_flag()
                logger.info(f"   🔄 Флаг прерывания сброшен в InputHandler после прерывания IN_PROCESS")
            
            if self.input_handler and hasattr(self.input_handler, 'reset_command_processed_flag'):
                self.input_handler.reset_command_processed_flag()
                logger.info(f"   🔄 Флаг обработки команды сброшен в InputHandler")
        
        elif self.state == AppState.LISTENING:
            # Уже слушаем → перезапускаем запись для надежности
            self.console.print("[blue]🔄 Уже слушаю - перезапускаю запись для надежности[/blue]")
            logger.info("   🔄 Перезапуск записи в состоянии LISTENING")
            
            # Останавливаем текущую запись и начинаем новую
            try:
                self.stt_recognizer.stop_recording_and_recognize()
                logger.info("   ✅ Текущая запись остановлена")
            except:
                pass
            
            # Начинаем новую запись
            self.stt_recognizer.start_recording()
            logger.info("   ✅ Новая запись запущена")
            self.console.print("[green]🎤 Запись перезапущена - говорите команду[/green]")
            
            # Сбрасываем флаг обработки команды
            if self.input_handler and hasattr(self.input_handler, 'reset_command_processed_flag'):
                self.input_handler.reset_command_processed_flag()
                logger.info(f"   🔄 Флаг обработки команды сброшен в InputHandler")
        
        else:
            # Неизвестное состояние → переходим в LISTENING
            self.console.print(f"[yellow]⚠️ Неизвестное состояние {self.state.name}, перехожу в LISTENING[/yellow]")
            self.set_state(AppState.LISTENING)
            self.stt_recognizer.start_recording()
            self.console.print("[green]🎤 Микрофон включен - говорите команду[/green]")
            logger.info("   🎤 Микрофон активирован из неизвестного состояния")
    
    def handle_stop_recording(self):
        """ПРОБЕЛ ОТПУЩЕН - выключаем микрофон и обрабатываем команду"""
        
        # 🚨 ИСПРАВЛЕНИЕ: Обрабатываем stop_recording из любого состояния
        
        if self.state == AppState.LISTENING:
            # Нормальная остановка записи
            command = self.stt_recognizer.stop_recording_and_recognize()
            logger.info("   ✅ Запись остановлена, микрофон выключен")
            
            if command and command.strip():
                # КОМАНДА ПРИНЯТА → переходим в IN_PROCESS
                self.console.print(f"[bold green]📝 Команда принята: {command}[/bold green]")
                self.set_state(AppState.IN_PROCESS)
                self.console.print("[blue]🔄 Переход в IN_PROCESS - обрабатываю команду...[/blue]")
                self._process_command(command)
            else:
                # КОМАНДА НЕ ПРИНЯТА → возвращаемся в SLEEPING
                self.console.print("[yellow]⚠️ Команда не распознана[/yellow]")
                self.set_state(AppState.SLEEPING)
                self.console.print("[blue]✅ Возврат в SLEEPING - готов к новым командам[/blue]")
                
        elif self.state == AppState.IN_PROCESS:
            # Ассистент работает → прерываем и переходим в LISTENING
            self.console.print("[bold yellow]🔇 Ассистент работает - ПРЕРЫВАЮ и перехожу в LISTENING![/bold yellow]")
            
            # Прерываем работу
            success = self.force_stop_everything()
            if success:
                logger.info("   ✅ Универсальная остановка успешна")
                self.console.print("[bold green]✅ ВСЕ ПРИНУДИТЕЛЬНО ОСТАНОВЛЕНО![/bold green]")
            
            # Переходим в LISTENING и включаем микрофон
            self.set_state(AppState.LISTENING)
            self.stt_recognizer.start_recording()
            self.console.print("[bold green]✅ Переход в LISTENING - микрофон включен![/bold green]")
            
        elif self.state == AppState.SLEEPING:
            # Ассистент спит → активируем микрофон
            self.console.print("[blue]🎤 Активирую микрофон из состояния SLEEPING[/blue]")
            self.set_state(AppState.LISTENING)
            self.stt_recognizer.start_recording()
            self.console.print("[green]🎤 Микрофон включен - говорите команду[/green]")
            
        else:
            # Неизвестное состояние → возвращаемся в SLEEPING
            self.console.print(f"[yellow]⚠️ Неизвестное состояние {self.state.name}, возвращаюсь в SLEEPING[/yellow]")
            self.set_state(AppState.SLEEPING)
    
    def handle_deactivate_microphone(self):
        """ПРОБЕЛ ОТПУЩЕН - деактивируем микрофон и возвращаемся в SLEEPING"""
        logger.info("   🔇 handle_deactivate_microphone() вызван")
        
        if self.state == AppState.LISTENING:
            # Останавливаем запись и РАСПОЗНАЕМ КОМАНДУ
            command = None
            try:
                if hasattr(self, 'stt_recognizer') and self.stt_recognizer:
                    command = self.stt_recognizer.stop_recording_and_recognize()
                    logger.info("   ✅ Запись остановлена")
            except Exception as e:
                logger.warning(f"   ⚠️ Ошибка остановки записи: {e}")
            
            # Если команда распознана - ОБРАБАТЫВАЕМ ЕЕ
            if command and command.strip():
                self.console.print(f"[bold green]📝 Команда распознана: {command}[/bold green]")
                logger.info(f"   📝 Команда распознана: {command}")
                
                # Переходим в IN_PROCESS для обработки команды
                self.set_state(AppState.IN_PROCESS)
                logger.info("   🔄 Переход в IN_PROCESS для обработки команды")
                
                # Обрабатываем команду
                self._process_command(command)
            else:
                # Команда не распознана - переходим в SLEEPING
                self.console.print("[yellow]⚠️ Команда не распознана[/yellow]")
                logger.info("   ⚠️ Команда не распознана")
                
                # Переходим в SLEEPING
                self.set_state(AppState.SLEEPING)
                self.console.print("[blue]🔇 Микрофон деактивирован - возврат в SLEEPING[/blue]")
                logger.info("   🔄 Переход в SLEEPING после деактивации микрофона")
            
        elif self.state == AppState.IN_PROCESS:
            # Ассистент работает → ничего не делаем
            self.console.print("[blue]ℹ️ Ассистент работает - микрофон неактивен[/blue]")
            logger.info("   ℹ️ Ассистент работает - микрофон неактивен")
            
        elif self.state == AppState.SLEEPING:
            # Уже спим → ничего не делаем
            self.console.print("[blue]ℹ️ Уже в состоянии SLEEPING[/blue]")
            logger.info("   ℹ️ Уже в состоянии SLEEPING")
    
    async def handle_interrupt_or_cancel(self):
        """Обрабатывает событие прерывания или отмены"""
        # Обновляем время начала прерывания
        self.interrupt_start_time = time.time()
        
        logger.info(f"🚨 handle_interrupt_or_cancel() начат в {self.interrupt_start_time:.3f}")
        
        current_state = self.state
        logger.info(f"   📊 Текущее состояние: {current_state.name}")
        
        if current_state == AppState.IN_PROCESS:
            # Ассистент работает → ПРИНУДИТЕЛЬНО прерываем работу!
            logger.info(f"   🚨 Прерывание работы (состояние: {current_state.name})")
            self.console.print("[bold red]🚨 ПРИНУДИТЕЛЬНО прерывание работы![/bold red]")
            
            # 🚨 ИСПОЛЬЗУЕМ УНИВЕРСАЛЬНЫЙ МЕТОД!
            success = self.force_stop_everything()
            
            if success:
                logger.info("   ✅ Универсальная остановка успешна")
                self.console.print("[bold green]✅ ВСЕ ПРИНУДИТЕЛЬНО ОСТАНОВЛЕНО![/bold green]")
            else:
                logger.warning("   ⚠️ Универсальная остановка неполная")
                self.console.print("[yellow]⚠️ Остановка неполная[/yellow]")
            
            # ПОСЛЕ ПРЕРЫВАНИЯ АВТОМАТИЧЕСКИ АКТИВИРУЕМ МИКРОФОН!
            logger.info("   🎤 АВТОМАТИЧЕСКАЯ активация микрофона после прерывания...")
            self.console.print("[blue]🎤 АВТОМАТИЧЕСКИ активирую микрофон после прерывания...[/blue]")
            
            # 3️⃣ Активируем микрофон
            try:
                # Захватываем экран
                self._capture_screen()
                logger.info("   ✅ Экран захвачен")
                
                # АВТОМАТИЧЕСКИ активируем микрофон после прерывания!
                logger.info("   🎤 АВТОМАТИЧЕСКАЯ активация микрофона после прерывания...")
                
                # Переходим в LISTENING и активируем микрофон
                self.set_state(AppState.LISTENING)
                self.stt_recognizer.start_recording()
                logger.info("   ✅ Микрофон активирован автоматически после прерывания")
                
                self.console.print("[bold green]✅ Микрофон активирован автоматически![/bold green]")
                self.console.print("[bold green]🎤 Слушаю команду...[/bold green]")
                
            except Exception as e:
                logger.error(f"   ❌ Ошибка обработки прерывания: {e}")
                self.console.print(f"[red]❌ Ошибка обработки прерывания: {e}[/red]")
                
                # В случае ошибки переходим в SLEEPING
                self.set_state(AppState.SLEEPING)
                logger.info("   🔄 Переход в SLEEPING после ошибки")
            
            # СБРАСЫВАЕМ ФЛАГ ПРЕРЫВАНИЯ В INPUT_HANDLER
            if self.input_handler and hasattr(self.input_handler, 'reset_interrupt_flag'):
                self.input_handler.reset_interrupt_flag()
                logger.info(f"   🔄 Флаг прерывания сброшен в InputHandler")
            
        elif current_state == AppState.LISTENING:
            # Ассистент слушает → прерываем запись и возвращаемся в SLEEPING
            logger.info(f"   🎤 Прерывание записи (состояние: {current_state.name})")
            self.console.print("[bold red]🔇 Прерывание записи команды[/bold red]")
            
            # Останавливаем запись и распознаем речь
            if hasattr(self, 'stt_recognizer') and self.stt_recognizer:
                command = self.stt_recognizer.stop_recording_and_recognize()
                
                if command and command.strip():
                    # Команда распознана - переходим в IN_PROCESS
                    self.console.print(f"[bold green]📝 Команда распознана: {command}[/bold green]")
                    logger.info(f"   📝 Команда распознана: {command}")
                    
                    # Переходим в IN_PROCESS для обработки команды
                    self.set_state(AppState.IN_PROCESS)
                    logger.info("   🔄 Переход в IN_PROCESS для обработки команды")
                    
                    # Обрабатываем команду
                    self._process_command(command)
                    
            else:
                # Команда не распознана - переходим в SLEEPING
                self.console.print("[yellow]⚠️ Команда не распознана[/yellow]")
                logger.info("   ⚠️ Команда не распознана")
                
                # Переходим в SLEEPING
                self.set_state(AppState.SLEEPING)
                logger.info("   🔄 Переход в SLEEPING после неудачного распознавания")
                
        elif not hasattr(self, 'stt_recognizer') or not self.stt_recognizer:
            # STT recognizer недоступен
            self.console.print("[yellow]⚠️ STT recognizer недоступен[/yellow]")
            logger.warning("   ⚠️ STT recognizer недоступен")
            
            # Переходим в SLEEPING
            self.set_state(AppState.SLEEPING)
            logger.info("   🔄 Переход в SLEEPING - STT недоступен")
            
            # СБРАСЫВАЕМ ФЛАГ ПРЕРЫВАНИЯ В INPUT_HANDLER
            if self.input_handler and hasattr(self.input_handler, 'reset_interrupt_flag'):
                self.input_handler.reset_interrupt_flag()
                logger.info(f"   🔄 Флаг прерывания сброшен в InputHandler после прерывания записи")
                
        elif current_state == AppState.SLEEPING:
            # Ассистент спит → прерываем и автоматически активируем микрофон!
            logger.info(f"   🌙 Ассистент спит - прерываю и активирую микрофон (состояние: {current_state.name})")
            self.console.print("[blue]🌙 Ассистент спит - прерываю и активирую микрофон[/blue]")
            
            # 🚨 ИСПОЛЬЗУЕМ УНИВЕРСАЛЬНЫЙ МЕТОД ДЛЯ ОЧИСТКИ!
            success = self.force_stop_everything()
            
            if success:
                logger.info("   ✅ Универсальная очистка успешна")
                self.console.print("[bold green]✅ ВСЕ ОЧИЩЕНО![/bold green]")
            else:
                logger.warning("   ⚠️ Универсальная очистка неполная")
                self.console.print("[yellow]⚠️ Очистка неполная[/yellow]")
            
            # АВТОМАТИЧЕСКИ активируем микрофон
            try:
                # Захватываем экран
                self._capture_screen()
                logger.info("   ✅ Экран захвачен")
                
                # Активируем микрофон
                self.stt_recognizer.start_recording()
                logger.info("   ✅ Микрофон активирован")
                
                # Переходим в LISTENING
                self.set_state(AppState.LISTENING)
                logger.info("   🔄 Переход в LISTENING после активации микрофона")
                
                self.console.print("[bold green]✅ Микрофон активирован автоматически![/bold green]")
                self.console.print("[bold green]🎤 Слушаю команду...[/bold green]")
                self.console.print("[yellow]💡 Удерживайте пробел и говорите команду[/yellow]")
                
            except Exception as e:
                logger.error(f"   ❌ Ошибка автоматической активации микрофона: {e}")
                self.console.print(f"[red]❌ Ошибка активации микрофона: {e}[/red]")
                
                # В случае ошибки переходим в SLEEPING
                self.set_state(AppState.SLEEPING)
                logger.info("   🔄 Переход в SLEEPING после ошибки активации микрофона")
            
            # СБРАСЫВАЕМ ФЛАГ ПРЕРЫВАНИЯ В INPUT_HANDLER
            if self.input_handler and hasattr(self.input_handler, 'reset_interrupt_flag'):
                self.input_handler.reset_interrupt_flag()
                logger.info(f"   🔄 Флаг прерывания сброшен в InputHandler (состояние SLEEPING)")
        
        # Логируем время выполнения
        end_time = time.time()
        execution_time = (end_time - self.interrupt_start_time) * 1000
        logger.info(f"   ⏱️ handle_interrupt_or_cancel завершен за {execution_time:.1f}ms")
        
        # Логируем финальное состояние
        logger.info(f"   📊 Финальное состояние: {self.state.name}")
    
    async def handle_event(self, event):
        """Маршрутизирует события к соответствующим обработчикам"""
        start_time = time.time()
        logger.info(f"   🎯 handle_event() начат для события: {event} в {start_time:.3f}")
        
        try:
            if event == "start_recording":
                logger.info(f"   🎤 Маршрутизация события start_recording")
                self.handle_start_recording()
            elif event == "interrupt_or_cancel":
                logger.info(f"   🔇 Маршрутизация события interrupt_or_cancel")
                await self.handle_interrupt_or_cancel()  # 🚨 ДОБАВЛЯЕМ await!
            elif event == "stop_recording":
                logger.info(f"   ⏹️ Маршрутизация события stop_recording")
                self.handle_stop_recording()
            elif event == "deactivate_microphone":
                logger.info(f"   🔇 Маршрутизация события deactivate_microphone")
                self.handle_deactivate_microphone()
            elif event == "process_command":
                logger.info(f"   ⚙️ Маршрутизация события process_command")
                self.handle_process_command()
            else:
                logger.warning(f"   ⚠️ Неизвестное событие: {event}")
                self.console.print(f"[yellow]⚠️ Неизвестное событие: {event}[/yellow]")
                
        except Exception as e:
            logger.error(f"   ❌ Ошибка в handle_event для {event}: {e}")
            self.console.print(f"[bold red]❌ Ошибка обработки события {event}: {e}[/bold red]")
            # Восстанавливаемся в SLEEPING при ошибке
            self.set_state(AppState.SLEEPING)
            self.console.print("[blue]🔄 Восстановление в SLEEPING при ошибке[/blue]")
        
        end_time = time.time()
        processing_time = (end_time - start_time) * 1000
        logger.info(f"   ⏱️ handle_event завершен за {processing_time:.1f}ms")
        logger.info(f"   📊 Финальное состояние: {self.state.name}")
    
    def _process_command(self, command):
        """Обрабатывает команду через gRPC"""
        try:
            # Сбрасываем флаг отмены для новой команды
            self._cancelled = False
            self.console.print("[blue]🔄 Сброшен флаг отмены для новой команды[/blue]")
            
            # 🚨 КРИТИЧНО: Проверяем и восстанавливаем gRPC соединение!
            if not self.grpc_client.stub:
                self.console.print("[yellow]⚠️ gRPC соединение разорвано, восстанавливаю...[/yellow]")
                logger.info("   🔌 Восстанавливаю gRPC соединение...")
                
                try:
                    # Восстанавливаем соединение
                    import asyncio
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # Создаем задачу для асинхронного восстановления
                        restore_task = loop.create_task(self.grpc_client.connect())
                        # Ждем завершения (неблокирующе)
                        if not restore_task.done():
                            self.console.print("[blue]⏳ Восстановление соединения в фоне...[/blue]")
                        else:
                            if restore_task.result():
                                self.console.print("[green]✅ gRPC соединение восстановлено![/green]")
                                logger.info("   ✅ gRPC соединение восстановлено")
                            else:
                                self.console.print("[red]❌ Не удалось восстановить gRPC соединение[/red]")
                                logger.error("   ❌ Не удалось восстановить gRPC соединение")
                                raise Exception("gRPC соединение не восстановлено")
                    else:
                        # Если цикл не запущен, восстанавливаем синхронно
                        if self.grpc_client.connect_sync():
                            self.console.print("[green]✅ gRPC соединение восстановлено синхронно![/green]")
                            logger.info("   ✅ gRPC соединение восстановлено синхронно")
                        else:
                            self.console.print("[red]❌ Не удалось восстановить gRPC соединение синхронно[/red]")
                            logger.error("   ❌ Не удалось восстановить gRPC соединение синхронно")
                            raise Exception("gRPC соединение не восстановлено синхронно")
                
                except Exception as e:
                    self.console.print(f"[bold red]❌ Ошибка восстановления gRPC соединения: {e}[/bold red]")
                    logger.error(f"   ❌ Ошибка восстановления gRPC соединения: {e}")
                    raise Exception(f"gRPC соединение не восстановлено: {e}")
            
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
            logger.error(f"   ❌ Ошибка выполнения команды: {e}")
            self.set_state(AppState.SLEEPING)
    
    async def _consume_stream(self, stream_generator):
        """Обрабатывает gRPC стрим в фоне"""
        logger.info(f"🚨 _consume_stream() начат в {time.time():.3f}")
        
        try:
            self.set_state(AppState.IN_PROCESS)
            logger.info(f"   📊 Состояние установлено: {self.state.name}")
            
            # Потребляем генератор до конца
            chunk_count = 0
            self.console.print("[bold red]🚨 НАЧАЛО ОБРАБОТКИ gRPC СТРИМА![/bold red]")
            logger.info("   🚀 Начало обработки gRPC стрима")
            
            try:
                async for chunk in stream_generator:
                    # 🚨 КРИТИЧНО: ПРОВЕРЯЕМ ПРЕРЫВАНИЕ ПЕРЕД КАЖДЫМ ЧАНКОМ
                    if hasattr(self, 'input_handler') and self.input_handler:
                        interrupt_status = self.input_handler.get_interrupt_status()
                        if interrupt_status:
                            logger.warning(f"   🚨 ОБНАРУЖЕНО ПРЕРЫВАНИЕ! Останавливаю обработку чанков")
                            self.console.print("[bold red]🚨 ОБНАРУЖЕНО ПРЕРЫВАНИЕ! Останавливаю обработку чанков![/bold red]")
                            
                            # Принудительно очищаем аудио буферы при прерывании
                            try:
                                if hasattr(self.audio_player, 'clear_all_audio_data'):
                                    self.audio_player.clear_all_audio_data()
                                    logger.info(f"   🚨 Аудио буферы очищены при прерывании")
                                    self.console.print("[green]✅ Аудио буферы очищены при прерывании[/green]")
                                elif hasattr(self.audio_player, 'force_stop'):
                                    self.audio_player.force_stop()
                                    logger.info(f"   🚨 Аудио принудительно остановлено при прерывании")
                                    self.console.print("[green]✅ Аудио принудительно остановлено при прерывании[/green]")
                                else:
                                    logger.warning(f"   ⚠️ Не найден метод очистки аудио")
                                    self.console.print("[yellow]⚠️ Не найден метод очистки аудио[/yellow]")
                            except Exception as e:
                                logger.error(f"   ❌ Ошибка очистки аудио при прерывании: {e}")
                                self.console.print(f"[red]❌ Ошибка очистки аудио при прерывании: {e}[/red]")
                            
                            # Выходим из цикла обработки чанков
                            logger.info(f"   🚨 Выход из цикла обработки чанков при прерывании")
                            self.console.print("[bold red]🚨 Выход из цикла обработки чанков при прерывании![/bold red]")
                            break
                    
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
            # КРИТИЧНО: всегда сбрасываем состояние в SLEEPING после завершения
            final_time = time.time()
            logger.info(f"   🏁 _consume_stream завершен в {final_time:.3f}")
            
            # 🚨 ДОПОЛНИТЕЛЬНАЯ ПРОВЕРКА: если было прерывание, принудительно очищаем аудио
            if hasattr(self, 'input_handler') and self.input_handler:
                if self.input_handler.get_interrupt_status():
                    logger.warning(f"   🚨 В finally: обнаружено прерывание, принудительно очищаю аудио")
                    self.console.print("[bold red]🚨 В finally: обнаружено прерывание, принудительно очищаю аудио![/bold red]")
                    
                    try:
                        if hasattr(self.audio_player, 'clear_all_audio_data'):
                            self.audio_player.clear_all_audio_data()
                            logger.info(f"   🚨 Аудио буферы очищены в finally при прерывании")
                        elif hasattr(self.audio_player, 'force_stop'):
                            self.audio_player.force_stop()
                            logger.info(f"   🚨 Аудио принудительно остановлено в finally при прерывании")
                    except Exception as e:
                        logger.error(f"   ❌ Ошибка очистки аудио в finally: {e}")
                    
                    # При прерывании НЕ запускаем ожидание завершения аудио
                    logger.info(f"   🚨 Прерывание обнаружено - пропускаю ожидание завершения аудио")
                    self.console.print("[bold red]🚨 Прерывание обнаружено - пропускаю ожидание завершения аудио![/bold red]")
                    
                    # Сразу переходим в SLEEPING
                    self.set_state(AppState.SLEEPING)
                    logger.info(f"   📊 Финальное состояние при прерывании: {self.state.name}")
                    self.console.print(f"[blue]✅ _consume_stream завершен при прерывании, переход в SLEEPING[/blue]")
                    self.console.print(f"[green]🌙 Ассистент прерван, перешел в режим ожидания[/green]")
                    return  # Выходим из finally
            
            # ДОЖИДАЕМСЯ ЗАВЕРШЕНИЯ ВОСПРОИЗВЕДЕНИЯ АУДИО ПЕРЕД ПЕРЕХОДОМ В SLEEPING
            try:
                if hasattr(self.audio_player, 'wait_for_queue_empty'):
                    logger.info(f"   🎵 Ожидаю естественного завершения воспроизведения аудио...")
                    self.console.print("[blue]🎵 Ожидаю завершения воспроизведения аудио...[/blue]")
                    
                    # Запускаем ожидание в фоне, чтобы не блокировать основной поток
                    import threading
                    wait_thread = threading.Thread(target=self._wait_for_audio_completion, daemon=True)
                    wait_thread.start()
                    
                    # Даем немного времени для инициализации ожидания
                    await asyncio.sleep(0.1)
                    
                    logger.info(f"   🎵 Ожидание завершения аудио запущено в фоне")
                    self.console.print("[blue]✅ Ожидание завершения аудио запущено в фоне[/blue]")
                    
                else:
                    logger.warning(f"   ⚠️ Метод wait_for_queue_empty недоступен")
                    self.console.print("[yellow]⚠️ Не могу дождаться завершения аудио[/yellow]")
                    
            except Exception as e:
                logger.error(f"   ❌ Ошибка ожидания завершения аудио: {e}")
                self.console.print(f"[red]❌ Ошибка ожидания завершения аудио: {e}[/red]")
            
            # Переходим в SLEEPING только после запуска ожидания аудио
            self.set_state(AppState.SLEEPING)
            logger.info(f"   📊 Финальное состояние: {self.state.name}")
            self.console.print(f"[blue]✅ _consume_stream завершен, переход в SLEEPING[/blue]")
            self.console.print(f"[green]🌙 Ассистент завершил работу, перешел в режим ожидания[/green]")
    
    def _wait_for_audio_completion(self):
        """Ожидает завершения воспроизведения аудио в фоновом режиме"""
        try:
            logger.info(f"   🎵 Фоновое ожидание завершения аудио начато")
            
            # Используем существующий метод wait_for_queue_empty
            if hasattr(self.audio_player, 'wait_for_queue_empty'):
                # Блокирующее ожидание завершения аудио
                while True:
                    # Проверяем статус каждые 100ms
                    import time
                    time.sleep(0.1)
                    
                    # Проверяем, завершилось ли аудио
                    if self.audio_player.wait_for_queue_empty():
                        logger.info(f"   🎵 Аудио естественно завершено")
                        self.console.print("[green]🎵 Аудио естественно завершено[/green]")
                        break
                        
                    # Проверяем, не прервано ли воспроизведение
                    if not self.audio_player.is_playing:
                        logger.info(f"   🎵 Воспроизведение прервано")
                        self.console.print("[yellow]🎵 Воспроизведение прервано[/yellow]")
                        break
                        
            else:
                logger.warning(f"   ⚠️ Метод wait_for_queue_empty недоступен")
                
        except Exception as e:
            logger.error(f"   ❌ Ошибка в фоновом ожидании аудио: {e}")
    
    def _force_stop_grpc_stream(self):
        """ПРИНУДИТЕЛЬНО останавливает gRPC стрим на уровне соединения"""
        logger.info(f"   🚨 _force_stop_grpc_stream() вызван в {time.time():.3f}")
        
        try:
            # 1️⃣ Принудительно закрываем gRPC соединение
            if hasattr(self, 'grpc_client') and self.grpc_client:
                logger.info(f"   🚨 Принудительно закрываю gRPC соединение...")
                
                # Закрываем соединение
                if hasattr(self.grpc_client, 'close_connection'):
                    self.grpc_client.close_connection()
                    logger.info(f"   ✅ gRPC соединение принудительно закрыто")
                elif hasattr(self.grpc_client, 'channel'):
                    # Закрываем канал
                    try:
                        self.grpc_client.channel.close()
                        logger.info(f"   ✅ gRPC канал принудительно закрыт")
                    except Exception as e:
                        logger.warning(f"   ⚠️ Ошибка закрытия gRPC канала: {e}")
                
                # Сбрасываем состояние клиента
                if hasattr(self.grpc_client, 'reset_state'):
                    self.grpc_client.reset_state()
                    logger.info(f"   ✅ Состояние gRPC клиента сброшено")
                
            # 2️⃣ Принудительно очищаем все буферы
            if hasattr(self, 'audio_player') and self.audio_player:
                logger.info(f"   🚨 Принудительно очищаю все аудио буферы...")
                
                # Очищаем очередь
                if hasattr(self.audio_player, 'audio_queue'):
                    queue_size = self.audio_player.audio_queue.qsize()
                    logger.info(f"   📊 Очищаю очередь: {queue_size} элементов")
                    
                    # Принудительно очищаем очередь
                    while not self.audio_player.audio_queue.empty():
                        try:
                            self.audio_player.audio_queue.get_nowait()
                        except:
                            break
                    
                    logger.info(f"   ✅ Очередь принудительно очищена")
                
                # Останавливаем воспроизведение
                if hasattr(self.audio_player, 'force_stop'):
                    self.audio_player.force_stop()
                    logger.info(f"   ✅ Аудио принудительно остановлено")
                elif hasattr(self.audio_player, 'stop'):
                    self.audio_player.stop()
                    logger.info(f"   ✅ Аудио остановлено")
                
                # Очищаем буферы
                if hasattr(self.audio_player, 'clear_all_audio_data'):
                    self.audio_player.clear_all_audio_data()
                    logger.info(f"   ✅ Все аудио буферы очищены")
            
            # 3️⃣ Принудительно прерываем все потоки
            import threading
            current_thread = threading.current_thread()
            all_threads = threading.enumerate()
            
            logger.info(f"   🚨 Проверяю активные потоки: {len(all_threads)}")
            
            for thread in all_threads:
                if (thread != current_thread and 
                    thread != threading.main_thread() and 
                    thread.is_alive() and
                    'grpc' in thread.name.lower()):
                    
                    logger.info(f"   🚨 Прерываю gRPC поток: {thread.name}")
                    try:
                        # Принудительно прерываем поток
                        import ctypes
                        thread_id = thread.ident
                        if thread_id:
                            res = ctypes.pythonapi.PyThreadState_SetAsyncExc(
                                ctypes.c_long(thread_id), 
                                ctypes.py_object(SystemExit)
                            )
                            if res > 1:
                                ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, 0)
                                logger.warning(f"   ⚠️ Не удалось прервать поток: {thread.name}")
                            else:
                                logger.info(f"   ✅ Поток прерван: {thread.name}")
                    except Exception as e:
                        logger.warning(f"   ⚠️ Ошибка прерывания потока {thread.name}: {e}")
            
            logger.info(f"   ✅ _force_stop_grpc_stream завершен")
            
        except Exception as e:
            logger.error(f"   ❌ Ошибка в _force_stop_grpc_stream: {e}")
    
    async def _wait_for_task_cancellation(self, task):
        """Ожидает завершения отмены задачи"""
        try:
            if not task.done():
                # Ждем завершения с таймаутом
                await asyncio.wait_for(task, timeout=0.1)
        except asyncio.TimeoutError:
            logger.warning(f"   ⚠️ Таймаут ожидания отмены задачи")
        except asyncio.CancelledError:
            logger.info(f"   ✅ Задача успешно отменена")
        except Exception as e:
            logger.warning(f"   ⚠️ Ошибка ожидания отмены: {e}")
    
    def cleanup(self):
        """Очищает ресурсы"""
        if self.streaming_task and not self.streaming_task.done():
            self.streaming_task.cancel()
        if self.active_call and not self.active_call.done():
            self.active_call.cancel()

    def _capture_screen(self):
        """Захватывает экран"""
        self.console.print("[bold blue]📸 Захватываю экран в JPEG...[/bold blue]")
        self.current_screenshot = self.screen_capture.capture_screen(quality=80)
        
        if self.current_screenshot:
            self.console.print(f"[bold green]✅ JPEG скриншот захвачен: {len(self.current_screenshot)} символов Base64[/bold green]")
        else:
            self.console.print("[bold yellow]⚠️ Не удалось захватить скриншот[/bold yellow]")
    
    def force_stop_everything(self):
        """🚨 УНИВЕРСАЛЬНЫЙ МЕТОД: мгновенно останавливает ВСЕ при нажатии пробела!"""
        logger.info(f"🚨 force_stop_everything() вызван в {time.time():.3f}")
        self.console.print("[bold red]🚨 УНИВЕРСАЛЬНАЯ ОСТАНОВКА ВСЕГО![/bold red]")
        
        start_time = time.time()
        
        try:
            # 1️⃣ МГНОВЕННО останавливаем аудио воспроизведение
            audio_start = time.time()
            self._force_stop_audio_playback()
            audio_time = (time.time() - audio_start) * 1000
            logger.info(f"   ✅ _force_stop_audio_playback: {audio_time:.1f}ms")
            
            # 2️⃣ МГНОВЕННО останавливаем gRPC стрим
            grpc_start = time.time()
            self._force_stop_grpc_stream()
            grpc_time = (time.time() - grpc_start) * 1000
            logger.info(f"   ✅ _force_stop_grpc_stream: {grpc_time:.1f}ms")
            
            # 3️⃣ МГНОВЕННО отменяем все задачи
            tasks_start = time.time()
            self._force_cancel_all_tasks()
            tasks_time = (time.time() - tasks_start) * 1000
            logger.info(f"   ✅ _force_cancel_all_tasks: {tasks_time:.1f}ms")
            
            # 4️⃣ МГНОВЕННО очищаем все буферы
            buffer_start = time.time()
            self._force_clear_all_buffers()
            buffer_time = (time.time() - buffer_start) * 1000
            logger.info(f"   ✅ _force_clear_all_buffers: {buffer_time:.1f}ms")
            
            # 5️⃣ МГНОВЕННО отправляем команду прерывания на сервер
            server_start = time.time()
            self._force_interrupt_server()
            server_time = (time.time() - server_start) * 1000
            logger.info(f"   ✅ _force_interrupt_server: {server_time:.1f}ms")
            
            # Общее время
            total_time = (time.time() - start_time) * 1000
            logger.info(f"   ⏱️ Общее время force_stop_everything: {total_time:.1f}ms")
            
            # Проверяем результат
            final_queue_size = self.audio_player.audio_queue.qsize()
            logger.info(f"   📊 Финальное состояние: queue_size={final_queue_size}")
            
            if final_queue_size == 0:
                logger.info("   🎯 УНИВЕРСАЛЬНАЯ ОСТАНОВКА УСПЕШНА!")
                self.console.print("[bold green]✅ ВСЕ ПРИНУДИТЕЛЬНО ОСТАНОВЛЕНО![/bold green]")
            else:
                logger.warning(f"   ⚠️ УНИВЕРСАЛЬНАЯ ОСТАНОВКА НЕПОЛНАЯ - очередь: {final_queue_size}")
                self.console.print(f"[yellow]⚠️ Остановка неполная - очередь: {final_queue_size}[/yellow]")
            
            return True
            
        except Exception as e:
            logger.error(f"   ❌ Ошибка в force_stop_everything: {e}")
            self.console.print(f"[red]❌ Ошибка универсальной остановки: {e}[/red]")
            return False
    
    def _force_stop_audio_playback(self):
        """МГНОВЕННО останавливает воспроизведение аудио"""
        logger.info(f"   🚨 _force_stop_audio_playback() вызван")
        
        try:
            if hasattr(self, 'audio_player') and self.audio_player:
                # 1️⃣ Принудительно останавливаем фоновый поток воспроизведения
                if hasattr(self.audio_player, 'force_stop_playback'):
                    self.audio_player.force_stop_playback()
                    logger.info("   ✅ Фоновый поток воспроизведения принудительно остановлен")
                elif hasattr(self.audio_player, 'force_stop'):
                    self.audio_player.force_stop()
                    logger.info("   ✅ Аудио принудительно остановлено")
                
                # 2️⃣ Принудительно очищаем все аудио буферы
                if hasattr(self.audio_player, 'clear_all_audio_data'):
                    self.audio_player.clear_all_audio_data()
                    logger.info("   ✅ Все аудио буферы очищены")
                
                # 3️⃣ Принудительно очищаем очередь аудио
                if hasattr(self.audio_player, 'audio_queue'):
                    queue_size = self.audio_player.audio_queue.qsize()
                    logger.info(f"   📊 Очищаю очередь аудио: {queue_size} элементов")
                    
                    # Принудительно очищаем очередь
                    while not self.audio_player.audio_queue.empty():
                        try:
                            self.audio_player.audio_queue.get_nowait()
                        except:
                            break
                    
                    logger.info("   ✅ Очередь аудио принудительно очищена")
                
                # 4️⃣ Принудительно останавливаем все потоки аудио
                if hasattr(self.audio_player, 'stop_all_audio_threads'):
                    self.audio_player.stop_all_audio_threads()
                    logger.info("   ✅ Все потоки аудио принудительно остановлены")
                
                logger.info("   ✅ _force_stop_audio_playback завершен")
                
        except Exception as e:
            logger.error(f"   ❌ Ошибка в _force_stop_audio_playback: {e}")
    
    def _force_cancel_all_tasks(self):
        """МГНОВЕННО отменяет все asyncio задачи"""
        logger.info(f"   🚨 _force_cancel_all_tasks() вызван")
        
        try:
            # 1️⃣ Отменяем streaming_task
            if self.streaming_task and not self.streaming_task.done():
                logger.info(f"   🚨 Принудительно отменяю streaming_task: {self.streaming_task}")
                self.streaming_task.cancel()
                
                # Ждем завершения отмены с таймаутом
                try:
                    import asyncio
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # Создаем задачу для ожидания отмены
                        wait_task = loop.create_task(self._wait_for_task_cancellation(self.streaming_task))
                        # Даем немного времени на отмену
                        import threading
                        def wait_in_thread():
                            try:
                                import asyncio
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                loop.run_until_complete(asyncio.sleep(0.1))
                            except:
                                pass
                        
                        wait_thread = threading.Thread(target=wait_in_thread, daemon=True)
                        wait_thread.start()
                        wait_thread.join(timeout=0.2)
                        
                except Exception as e:
                    logger.warning(f"   ⚠️ Ошибка ожидания отмены streaming_task: {e}")
            
            # 2️⃣ Отменяем active_call
            if self.active_call and not self.active_call.done():
                logger.info(f"   🚨 Принудительно отменяю active_call: {self.active_call}")
                self.active_call.cancel()
                
                # Ждем завершения отмены с таймаутом
                try:
                    import asyncio
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # Создаем задачу для ожидания отмены
                        wait_task = loop.create_task(self._wait_for_task_cancellation(self.active_call))
                        # Даем немного времени на отмену
                        import threading
                        def wait_in_thread():
                            try:
                                import asyncio
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                loop.run_until_complete(asyncio.sleep(0.1))
                            except:
                                pass
                        
                        wait_thread = threading.Thread(target=wait_in_thread, daemon=True)
                        wait_thread.start()
                        wait_thread.join(timeout=0.2)
                        
                except Exception as e:
                    logger.warning(f"   ⚠️ Ошибка ожидания отмены active_call: {e}")
            
            # 3️⃣ Очищаем ссылки на задачи
            self.streaming_task = None
            self.active_call = None
            logger.info("   ✅ Все ссылки на задачи очищены")
            
            logger.info("   ✅ _force_cancel_all_tasks завершен")
            
        except Exception as e:
            logger.error(f"   ❌ Ошибка в _force_cancel_all_tasks: {e}")
    
    def _force_clear_all_buffers(self):
        """МГНОВЕННО очищает все буферы"""
        logger.info(f"   🚨 _force_clear_all_buffers() вызван")
        
        try:
            # 1️⃣ Очищаем все аудио буферы
            if hasattr(self, 'audio_player') and self.audio_player:
                if hasattr(self.audio_player, 'clear_all_audio_data'):
                    self.audio_player.clear_all_audio_data()
                    logger.info("   ✅ Все аудио буферы очищены")
                
                if hasattr(self.audio_player, 'clear_audio_buffers'):
                    self.audio_player.clear_audio_buffers()
                    logger.info("   ✅ Аудио буферы очищены")
            
            # 2️⃣ Очищаем все gRPC буферы
            if hasattr(self, 'grpc_client') and self.grpc_client:
                if hasattr(self.grpc_client, 'clear_buffers'):
                    self.grpc_client.clear_buffers()
                    logger.info("   ✅ gRPC буферы очищены")
            
            # 3️⃣ Очищаем все системные буферы
            import gc
            gc.collect()
            logger.info("   ✅ Системные буферы очищены")
            
            logger.info("   ✅ _force_clear_all_buffers завершен")
            
        except Exception as e:
            logger.error(f"   ❌ Ошибка в _force_clear_all_buffers: {e}")
    
    def _force_interrupt_server(self):
        """МГНОВЕННО отправляет команду прерывания на сервер"""
        logger.info(f"   🚨 _force_interrupt_server() вызван")
        
        try:
            if hasattr(self, 'grpc_client') and self.grpc_client:
                # 1️⃣ Отправляем команду прерывания на сервер
                if hasattr(self.grpc_client, 'force_interrupt_server'):
                    self.grpc_client.force_interrupt_server()
                    logger.info("   ✅ Команда прерывания отправлена на сервер")
                
                # 2️⃣ Принудительно закрываем соединение
                if hasattr(self.grpc_client, 'close_connection'):
                    self.grpc_client.close_connection()
                    logger.info("   ✅ gRPC соединение принудительно закрыто")
                
                # 3️⃣ Сбрасываем состояние клиента
                if hasattr(self.grpc_client, 'reset_state'):
                    self.grpc_client.reset_state()
                    logger.info("   ✅ Состояние gRPC клиента сброшено")
                
                logger.info("   ✅ _force_interrupt_server завершен")
            else:
                logger.warning("   ⚠️ gRPC клиент недоступен")
                
        except Exception as e:
            logger.error(f"   ❌ Ошибка в _force_interrupt_server: {e}")

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
    
    # КРИТИЧНО: ждем инициализации InputHandler
    console.print("[blue]⏳ Инициализация InputHandler...[/blue]")
    await asyncio.sleep(0.5)  # Даем время на инициализацию
    console.print("[blue]✅ InputHandler инициализирован[/blue]")
    
    # Получаем информацию об экране
    screen_info = screen_capture.get_screen_info()
    console.print(f"[bold blue]📱 Экран: {screen_info.get('width', 0)}x{screen_info.get('height', 0)} пикселей[/bold blue]")
    
    # Создаем StateManager
    state_manager = StateManager(console, audio_player, stt_recognizer, screen_capture, grpc_client, hardware_id, input_handler)
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
    console.print("[yellow]📋 Управление (3 состояния):[/yellow]")
    console.print("[yellow]  • Нажмите пробел → прерывание работы ассистента[/yellow]")
    console.print("[yellow]  • Удерживайте пробел → запись команды[/yellow]")
    console.print("[yellow]  • Отпустите пробел → отправка команды[/yellow]")
    console.print("[yellow]  • Три состояния:[/yellow]")
    console.print("[yellow]    - SLEEPING: спит, ждет команды[/yellow]")
    console.print("[yellow]    - LISTENING: слушает команды[/yellow]")
    console.print("[yellow]    - IN_PROCESS: работает (обрабатывает/говорит)[/yellow]")
    console.print("[yellow]  • При активации автоматически захватывается экран[/yellow]")
    console.print("[yellow]  • Hardware ID отправляется с каждой командой[/yellow]")

    # Основной цикл обработки событий
    console.print("🔄 Запуск основного цикла обработки событий...")
    
    try:
        while True:
            try:
                # Получаем событие из очереди
                event = await event_queue.get()
                event_time = time.time()
                
                # Логируем получение события
                logger.info(f"📡 СОБЫТИЕ ПОЛУЧЕНО: {event} в {event_time:.3f}")
                console.print(f"[dim]📡 Событие получено: {event}[/dim]")
                
                # Получаем текущее состояние
                current_state = state_manager.get_state()
                logger.info(f"   📊 Текущее состояние: {current_state.name}")
                
                # Обрабатываем событие
                start_time = time.time()
                logger.info(f"   🎯 ОБРАБАТЫВАЮ СОБЫТИЕ: {event}")
                console.print(f"[blue]🔍 Текущее состояние: {current_state.name}, событие: {event}[/blue]")
                
                # Обрабатываем событие через StateManager
                await state_manager.handle_event(event)
                
                # Логируем завершение обработки
                end_time = time.time()
                processing_time = (end_time - start_time) * 1000
                logger.info(f"   ⏱️ Время обработки события: {processing_time:.1f}ms")
                
                # Получаем новое состояние
                new_state = state_manager.get_state()
                logger.info(f"   📊 Новое состояние: {new_state.name}")
                
                # Проверяем изменение состояния
                if current_state != new_state:
                    logger.info(f"   🔄 ИЗМЕНЕНИЕ СОСТОЯНИЯ: {current_state.name} → {new_state.name}")
                    console.print(f"[green]✅ СОБЫТИЕ {event} ОБРАБОТАНО! Новое состояние: {new_state.name}[/green]")
                else:
                    logger.info(f"   🔄 Состояние не изменилось: {current_state.name}")
                    console.print(f"[green]✅ СОБЫТИЕ {event} ОБРАБОТАНО! Новое состояние: {new_state.name}[/green]")
                
                # Показываем статус аудио
                audio_status = audio_player.get_audio_status()
                if audio_status.get('is_playing', False):
                    console.print("🔊 Аудио статус: ВОСПРОИЗВОДИТСЯ")
                else:
                    console.print("🔇 Аудио статус: ОСТАНОВЛЕНО")
                        
            except asyncio.CancelledError:
                logger.info("   🚨 Основной цикл отменен")
                break
            except Exception as e:
                logger.error(f"   ❌ Ошибка в основном цикле: {e}")
                console.print(f"[bold red]❌ Критическая ошибка в основном цикле: {e}[/bold red]")
                # Восстанавливаемся в SLEEPING
                state_manager.set_state(AppState.SLEEPING)
                console.print("[blue]🔄 Восстановление в SLEEPING[/blue]")
                
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

