"""
Упрощенный State Manager - точная копия логики из main.py
Только 3 состояния: SLEEPING, LISTENING, PROCESSING
"""

import asyncio
import time
import threading
from typing import Optional, Callable, Dict, Any
from datetime import datetime

from .types import AppState, StateTransition, StateMetrics, StateInfo, StateConfig


class SimpleStateManager:
    """
    Упрощенный менеджер состояний - точная копия StateManager из main.py
    Управляет переходами между состояниями приложения.
    Каждое состояние знает, как реагировать на каждое событие.
    """
    
    def __init__(self, console=None, audio_player=None, stt_recognizer=None, 
                 screen_capture=None, grpc_client=None, network_manager=None, 
                 hardware_id=None, input_handler=None, tray_controller=None, 
                 config: Optional[StateConfig] = None):
        self.console = console
        self.audio_player = audio_player
        self.stt_recognizer = stt_recognizer
        self.screen_capture = screen_capture
        self.grpc_client = grpc_client
        self.network_manager = network_manager
        self.hardware_id = hardware_id
        self.input_handler = input_handler
        self.tray_controller = tray_controller
        self.config = config or StateConfig()
        
        # Состояние приложения - точно как в main.py
        self.state = AppState.SLEEPING
        self.active_call = None
        self.streaming_task = None
        self.current_screenshot = None
        self.current_screen_info = None
        
        # Флаг для fade-in первого аудио чанка
        self._first_tts_chunk = True
        
        # Время начала прерывания для логирования
        self.interrupt_start_time = time.time()
        
        # Защита от дублирования команд
        self._last_command_time = 0
        self._command_debounce = 0.5  # 500ms защита от дублирования команд
        
        # Централизованное управление состоянием микрофона
        self._microphone_state = {
            'is_recording': False,
            'last_start_time': 0,
            'last_stop_time': 0,
            'state_lock': threading.Lock()
        }
        
        # Метрики
        self.metrics = StateMetrics()
        self.state_history: list[StateInfo] = []
        
        # Callbacks
        self.on_state_changed: Optional[Callable[[AppState, AppState, str], None]] = None
        self.on_error: Optional[Callable[[Exception, str], None]] = None
        self.on_recovery: Optional[Callable[[AppState], None]] = None
        
        # Инициализация
        self._initialize_components()
        
        if self.console:
            self.console.print("[bold green]✅ Simple State Manager инициализирован[/bold green]")
    
    def _initialize_components(self):
        """Инициализирует компоненты"""
        try:
            # Инициализируем tray controller если не передан
            if self.tray_controller is None:
                try:
                    from tray_controller import create_tray_controller, create_default_config
                    tray_config = create_default_config()
                    self.tray_controller = create_tray_controller(tray_config)
                    self._setup_tray_callbacks()
                except Exception as e:
                    if self.console:
                        self.console.print(f"[yellow]⚠️ Tray controller недоступен: {e}[/yellow]")
                    self.tray_controller = None
        except Exception as e:
            if self.console:
                self.console.print(f"[yellow]⚠️ Ошибка инициализации компонентов: {e}[/yellow]")
    
    def _setup_tray_callbacks(self):
        """Настраивает callback'и для tray controller"""
        if self.tray_controller is None:
            return
        
        try:
            # Callback для статуса
            self.tray_controller.add_callback("status", self._on_tray_status)
            
            # Callback для настроек
            self.tray_controller.add_callback("settings", self._on_tray_settings)
            
            # Callback для информации
            self.tray_controller.add_callback("about", self._on_tray_about)
            
            # Callback для выхода
            self.tray_controller.add_callback("quit", self._on_tray_quit)
            
        except Exception as e:
            if self.console:
                self.console.print(f"[yellow]⚠️ Ошибка настройки tray callbacks: {e}[/yellow]")
    
    def _on_tray_status(self, data=None):
        """Обрабатывает нажатие на Status в tray menu"""
        try:
            status = self.tray_controller.get_status() if self.tray_controller else {}
            if self.console:
                self.console.print(f"[blue]📊 Tray Status: {status}[/blue]")
        except Exception as e:
            if self.console:
                self.console.print(f"[yellow]⚠️ Ошибка обработки tray status: {e}[/yellow]")
    
    def _on_tray_settings(self, data=None):
        """Обрабатывает нажатие на Settings в tray menu"""
        try:
            if self.console:
                self.console.print("[blue]⚙️ Настройки (пока не реализованы)[/blue]")
        except Exception as e:
            if self.console:
                self.console.print(f"[yellow]⚠️ Ошибка обработки tray settings: {e}[/yellow]")
    
    def _on_tray_about(self, data=None):
        """Обрабатывает нажатие на About в tray menu"""
        try:
            if self.console:
                self.console.print("[blue]ℹ️ Nexy AI Voice Assistant v1.0[/blue]")
        except Exception as e:
            if self.console:
                self.console.print(f"[yellow]⚠️ Ошибка обработки tray about: {e}[/yellow]")
    
    def _on_tray_quit(self, data=None):
        """Обрабатывает нажатие на Quit в tray menu"""
        try:
            if self.console:
                self.console.print("[yellow]👋 Выход по запросу из tray menu[/yellow]")
            # Здесь можно добавить логику для graceful shutdown
        except Exception as e:
            if self.console:
                self.console.print(f"[yellow]⚠️ Ошибка обработки tray quit: {e}[/yellow]")
    
    def _write_tray_status_file(self, state_name: str):
        """Записывает статус в файл для tray controller"""
        def write_async():
            try:
                import json
                path = self._get_status_file_path()
                with open(path, "w") as f:
                    json.dump({"state": state_name, "ts": time.time()}, f)
            except Exception:
                pass
        
        # Запускаем в фоне
        threading.Thread(target=write_async, daemon=True).start()
    
    def _get_status_file_path(self):
        """Возвращает путь к файлу статуса"""
        from pathlib import Path
        return Path.home() / "Library" / "Application Support" / "Nexy" / "tray_status.json"

    def _log_state_transition(self, from_state: AppState, to_state: AppState, reason: str = ""):
        """Логирует переходы между состояниями"""
        if self.console:
            self.console.print(f"[dim]🔄 {from_state.name} → {to_state.name}[/dim] {reason}")
        
        self._write_tray_status_file(to_state.name)
        
        # Синхронизируем с tray controller
        if self.tray_controller:
            try:
                from tray_controller import TrayState
                # Маппинг состояний AppState на TrayState
                state_mapping = {
                    AppState.SLEEPING: TrayState.SLEEPING,
                    AppState.LISTENING: TrayState.LISTENING,
                    AppState.PROCESSING: TrayState.PROCESSING
                }
                
                tray_state = state_mapping.get(to_state, TrayState.SLEEPING)
                self.tray_controller.set_state(tray_state)
                
            except Exception as e:
                if self.console:
                    self.console.print(f"[yellow]⚠️ Ошибка синхронизации с tray controller: {e}[/yellow]")
        
        # Записываем в историю
        state_info = StateInfo(
            state=to_state,
            timestamp=datetime.now(),
            duration=0.0,
            reason=reason
        )
        self.state_history.append(state_info)
        
        # Ограничиваем размер истории
        if len(self.state_history) > self.config.max_history_size:
            self.state_history.pop(0)
        
        # Обновляем метрики
        self.metrics.total_transitions += 1
        self.metrics.successful_transitions += 1
        self.metrics.last_transition_time = datetime.now()
        
        # Уведомляем callback
        if self.on_state_changed:
            try:
                self.on_state_changed(from_state, to_state, reason)
            except Exception as e:
                if self.console:
                    self.console.print(f"[yellow]⚠️ Ошибка callback состояния: {e}[/yellow]")

    def _can_start_listening(self) -> bool:
        """Проверяет, можно ли начать прослушивание"""
        return self.state == AppState.SLEEPING

    def _can_stop_listening(self) -> bool:
        """Проверяет, можно ли остановить прослушивание"""
        return self.state == AppState.LISTENING

    def _can_start_processing(self) -> bool:
        """Проверяет, можно ли начать обработку"""
        return self.state == AppState.LISTENING

    def _can_stop_processing(self) -> bool:
        """Проверяет, можно ли остановить обработку"""
        return self.state == AppState.PROCESSING

    def _can_sleep(self) -> bool:
        """Проверяет, можно ли перейти в режим сна"""
        return self.state in [AppState.LISTENING, AppState.PROCESSING]

    def start_listening(self) -> bool:
        """Начинает прослушивание команд"""
        if not self._can_start_listening():
            return False
        
        self._log_state_transition(self.state, AppState.LISTENING, "(пользователь нажал кнопку)")
        self.state = AppState.LISTENING
        
        # Запускаем STT
        if self.stt_recognizer:
            self.stt_recognizer.start_recording_without_activation()
        
        return True

    def stop_listening(self) -> bool:
        """Останавливает прослушивание команд и обрабатывает распознанный текст"""
        if not self._can_stop_listening():
            return False
        
        self._log_state_transition(self.state, AppState.SLEEPING, "(пользователь отпустил кнопку)")
        self.state = AppState.SLEEPING
        
        # Останавливаем STT и получаем распознанный текст
        if self.stt_recognizer:
            future = self.stt_recognizer.stop_recording_and_recognize()
            if future:
                # Используем синхронное ожидание с таймаутом
                try:
                    recognized_text = future.result(timeout=10)  # 10 секунд таймаут
                except Exception as e:
                    if self.console:
                        self.console.print(f"[yellow]⚠️ Ошибка распознавания: {e}[/yellow]")
                    recognized_text = None
            else:
                recognized_text = None
            
            # Если текст распознан, отправляем на сервер
            if recognized_text and recognized_text.strip():
                if self.console:
                    self.console.print(f"[bold green]🎤 Распознано: {recognized_text}[/bold green]")
                # Запускаем обработку команды асинхронно
                asyncio.create_task(self._process_command(recognized_text))
            else:
                if self.console:
                    self.console.print("[yellow]⚠️ Речь не распознана[/yellow]")
        
        return True

    async def _process_command(self, command: str):
        """Обрабатывает распознанную команду - отправляет на сервер"""
        try:
            if self.console:
                self.console.print(f"[blue]🔄 Обработка команды: {command}[/blue]")
            
            # Переходим в состояние обработки
            self._log_state_transition(self.state, AppState.PROCESSING, "(команда распознана)")
            self.state = AppState.PROCESSING
            
            # Создаем задачу для отслеживания прерывания
            self.streaming_task = asyncio.current_task()
            
            # Получаем скриншот
            screenshot_data = None
            screen_info = None
            if self.screen_capture:
                try:
                    # Захват экрана в фоновом потоке
                    screenshot_data = await asyncio.get_event_loop().run_in_executor(
                        None, self.screen_capture.capture_screen
                    )
                    if screenshot_data:
                        # Получаем реальную информацию об экране
                        screen_info_obj = self.screen_capture.get_screen_info()
                        screen_info = {
                            'width': screen_info_obj.width,
                            'height': screen_info_obj.height
                        }
                        if self.console:
                            self.console.print(f"[blue]📸 Скриншот получен: {screen_info.get('width', 0)}x{screen_info.get('height', 0)}[/blue]")
                except Exception as e:
                    if self.console:
                        self.console.print(f"[yellow]⚠️ Ошибка захвата экрана: {e}[/yellow]")
            
            # Отправляем на сервер через gRPC
            if self.grpc_client:
                try:
                    if self.console:
                        self.console.print("[blue]🌐 Отправка на сервер...[/blue]")
                    
                    # Запускаем стриминг с обработкой прерывания
                    try:
                        async for response in self.grpc_client.stream_audio(
                            prompt=command,
                            screenshot_base64=screenshot_data,
                            screen_info=screen_info,
                            hardware_id=self.hardware_id
                        ):
                            # Проверяем, не было ли прерывания
                            if self.state != AppState.PROCESSING:
                                if self.console:
                                    self.console.print("[red]🛑 Прерывание обнаружено, останавливаем стрим[/red]")
                                break
                            
                            # Обрабатываем ответы от сервера
                            if response.HasField("text_chunk"):
                                if self.console:
                                    self.console.print(f"[cyan]📝 {response.text_chunk}[/cyan]")
                            elif response.HasField("audio_chunk"):
                                # Воспроизводим аудио
                                if self.audio_player:
                                    # Запускаем воспроизведение, если еще не запущено
                                    if not self.audio_player._is_playing:
                                        self.audio_player.start_playback()
                                    # Конвертируем bytes в numpy array
                                    import numpy as np
                                    audio_data = np.frombuffer(response.audio_chunk.audio_data, dtype=np.int16)
                                    
                                    # УМНАЯ АДАПТАЦИЯ: Определяем оптимальные параметры для текущего устройства
                                    current_device_info = getattr(self.audio_player, 'current_device_info', None)
                                    current_device = current_device_info.name if current_device_info else 'default'
                                    
                                    # Простая адаптация частоты
                                    if hasattr(self.audio_player, 'sample_rate') and self.audio_player.sample_rate != 44100:
                                        # Простой ресэмплинг
                                        ratio = 44100 / self.audio_player.sample_rate
                                        target_length = int(len(audio_data) * ratio)
                                        if ratio > 1:
                                            indices = np.linspace(0, len(audio_data) - 1, target_length, dtype=int)
                                            audio_data = audio_data[indices]
                                        else:
                                            step = int(1 / ratio)
                                            audio_data = audio_data[::step]
                                    
                                    self.audio_player.add_audio_data(audio_data)
                            elif response.HasField("end_message"):
                                if self.console:
                                    self.console.print(f"[green]✅ {response.end_message}[/green]")
                                break
                            elif response.HasField("error_message"):
                                if self.console:
                                    self.console.print(f"[red]❌ {response.error_message}[/red]")
                                break
                    
                        if self.console:
                            self.console.print("[green]✅ Команда обработана[/green]")
                    
                    except asyncio.CancelledError:
                        if self.console:
                            self.console.print("[red]🛑 gRPC стрим прерван пользователем[/red]")
                        raise
                    except Exception as e:
                        if self.console:
                            self.console.print(f"[red]❌ Ошибка gRPC стрима: {e}[/red]")
                    finally:
                        # Останавливаем воспроизведение после завершения стрима
                        if self.audio_player and self.audio_player._is_playing:
                            self.audio_player.stop_playback()
                    
                except Exception as e:
                    if self.console:
                        self.console.print(f"[red]❌ Ошибка отправки на сервер: {e}[/red]")
            else:
                if self.console:
                    self.console.print("[yellow]⚠️ gRPC клиент недоступен[/yellow]")
            
        except Exception as e:
            if self.console:
                self.console.print(f"[red]❌ Ошибка обработки команды: {e}[/red]")
        finally:
            # Возвращаемся в состояние сна
            self._log_state_transition(self.state, AppState.SLEEPING, "(обработка завершена)")
            self.state = AppState.SLEEPING

    def start_processing(self) -> bool:
        """Начинает обработку команды"""
        if not self._can_start_processing():
            return False
        
        self._log_state_transition(self.state, AppState.PROCESSING, "(команда распознана)")
        self.state = AppState.PROCESSING
        
        # Останавливаем STT
        if self.stt_recognizer:
            future = self.stt_recognizer.stop_recording_and_recognize()
            if future:
                # Не ждем результат, просто останавливаем запись
                pass
        
        return True

    def stop_processing(self) -> bool:
        """Завершает обработку команды"""
        if not self._can_stop_processing():
            return False
        
        self._log_state_transition(self.state, AppState.SLEEPING, "(обработка завершена)")
        self.state = AppState.SLEEPING
        
        return True

    def sleep(self) -> bool:
        """Переводит приложение в режим сна"""
        if not self._can_sleep():
            return False
        
        self._log_state_transition(self.state, AppState.SLEEPING, "(принудительный сон)")
        self.state = AppState.SLEEPING
        
        # Останавливаем STT
        if self.stt_recognizer:
            future = self.stt_recognizer.stop_recording_and_recognize()
            if future:
                # Не ждем результат, просто останавливаем запись
                pass
        
        # ПРЕРЫВАЕМ АУДИО ВОСПРОИЗВЕДЕНИЕ
        if self.audio_player:
            try:
                self.audio_player.stop_playback()
                if self.console:
                    self.console.print("[red]🔇 Аудио прервано[/red]")
            except Exception as e:
                if self.console:
                    self.console.print(f"[yellow]⚠️ Ошибка остановки аудио: {e}[/yellow]")
        
        # ПРЕРЫВАЕМ gRPC СТРИМ
        if self.streaming_task and not self.streaming_task.done():
            self.streaming_task.cancel()
            if self.console:
                self.console.print("[red]🔇 gRPC стрим прерван[/red]")
        
        return True

    def get_state_name(self) -> str:
        """Возвращает название текущего состояния"""
        return self.state.name

    def is_listening(self) -> bool:
        """Проверяет, находится ли приложение в режиме прослушивания"""
        return self.state == AppState.LISTENING

    def is_processing(self) -> bool:
        """Проверяет, находится ли приложение в режиме обработки"""
        return self.state == AppState.PROCESSING

    def is_sleeping(self) -> bool:
        """Проверяет, находится ли приложение в режиме сна"""
        return self.state == AppState.SLEEPING

    def activate_microphone(self) -> bool:
        """Алиас для start_listening() - совместимость с STT"""
        return self.start_listening()

    def deactivate_microphone(self) -> bool:
        """Алиас для stop_listening() - совместимость с STT"""
        return self.stop_listening()

    def is_microphone_recording(self) -> bool:
        """Проверяет, записывается ли микрофон"""
        return self.state == AppState.LISTENING

    def can_start_recording(self) -> bool:
        """Проверяет, можно ли начать запись"""
        return self._can_start_listening()

    def get_metrics(self) -> StateMetrics:
        """Возвращает метрики состояний"""
        return self.metrics

    def get_state_history(self, limit: int = 10) -> list[StateInfo]:
        """Возвращает историю состояний"""
        return self.state_history[-limit:] if limit > 0 else self.state_history

    def set_state_changed_callback(self, callback: Callable[[AppState, AppState, str], None]):
        """Устанавливает callback для изменений состояния"""
        self.on_state_changed = callback

    def set_error_callback(self, callback: Callable[[Exception, str], None]):
        """Устанавливает callback для ошибок"""
        self.on_error = callback

    def set_recovery_callback(self, callback: Callable[[AppState], None]):
        """Устанавливает callback для восстановления"""
        self.on_recovery = callback

    def cleanup(self):
        """Очистка ресурсов при выходе"""
        try:
            # Останавливаем STT
            if self.stt_recognizer:
                future = self.stt_recognizer.stop_recording_and_recognize()
                if future:
                    # Не ждем результат, просто останавливаем запись
                    pass
            
            # Очищаем другие ресурсы
            if self.audio_player:
                self.audio_player.shutdown()
            
            if self.console:
                self.console.print("[dim]🧹 Ресурсы очищены[/dim]")
        except Exception as e:
            if self.console:
                self.console.print(f"[dim]⚠️ Ошибка очистки ресурсов: {e}[/dim]")


def create_simple_state_manager(console=None, audio_player=None, stt_recognizer=None, 
                               screen_capture=None, grpc_client=None, network_manager=None, 
                               hardware_id=None, input_handler=None, tray_controller=None, 
                               config: Optional[StateConfig] = None) -> SimpleStateManager:
    """Создает экземпляр SimpleStateManager"""
    return SimpleStateManager(
        console=console,
        audio_player=audio_player,
        stt_recognizer=stt_recognizer,
        screen_capture=screen_capture,
        grpc_client=grpc_client,
        network_manager=network_manager,
        hardware_id=hardware_id,
        input_handler=input_handler,
        tray_controller=tray_controller,
        config=config
    )
