#!/usr/bin/env python3
"""
Nexy AI Voice Assistant - Основной файл приложения
Включает интеграцию Sparkle Framework для автообновлений
"""

import asyncio
import logging
import time
import threading
from rich.console import Console
from enum import Enum
import sys
from pathlib import Path

import os
import yaml
import fcntl
import atexit
import subprocess
import json
import signal

# НАСТРОЙКА ЛОГИРОВАНИЯ
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Добавляем корневую директорию в путь для импорта
# sys.path.append(str(Path(__file__).parent.parent))  # Отключено для PyInstaller

from audio_player import ThreadSafeAudioPlayer, get_global_thread_safe_audio_player
from simplified_audio_system import get_global_simplified_audio_system
from stt_recognizer import StreamRecognizer
# from input_handler import InputHandler  # Старый модуль, заменен на improved_input_handler
from improved_input_handler import ImprovedInputHandler, InputEventType, create_improved_input_handler, create_default_config as create_input_config
from tray_controller import (
    TrayController, TrayState, create_default_config,
    initialize_global_tray_controller, shutdown_global_tray_controller
)
from error_handler import (
    handle_audio_error, handle_network_error, handle_device_error, 
    handle_memory_error, handle_threading_error, handle_config_error,
    handle_permission_error, ErrorSeverity, ErrorCategory
)

# ИМПОРТ SPARKLE UPDATE MANAGER
try:    
    from improved_sparkle_update_manager import ImprovedSparkleUpdateManager, create_improved_sparkle_update_manager
    SPARKLE_AVAILABLE = True
    print("✅ Sparkle Update Manager импортирован успешно")
except ImportError as e:
    print(f"⚠️ Sparkle Update Manager не найден: {e}")
    SPARKLE_AVAILABLE = False

# from grpc_client import GrpcClient  # Старый модуль, заменен на improved_grpc_client
from improved_grpc_client import ImprovedGrpcClient, create_improved_grpc_client, create_default_config as create_grpc_config
from network_manager import NetworkManager, create_network_manager, create_default_config as create_network_config
# from screen_capture import ScreenCapture  # Старый модуль, заменен на improved_screen_capture
from improved_screen_capture import ImprovedScreenCapture, create_improved_screen_capture, create_default_config as create_screen_config                                                                              
from improved_permissions import PermissionManager, PermissionType, PermissionStatus
from utils.hardware_id import get_hardware_id, get_hardware_info
TrayController = None  # Используем helper-процесс вместо прямого UI в этом процессе

def _get_support_dir() -> Path:
    return Path.home() / "Library" / "Application Support" / "Nexy"

def _get_status_file_path() -> Path:
    support_dir = _get_support_dir()
    support_dir.mkdir(parents=True, exist_ok=True)
    return support_dir / "tray_status.json"

def _run_tray_helper_if_requested():
    """Если процесс запущен в режиме helper (`--tray-helper`), поднимаем rumps UI и выходим."""
    if "--tray-helper" not in sys.argv:
        return
    try:
        import rumps
    except Exception as e:
        handle_permission_error(e, "main", "import_rumps", "Импорт rumps")
        print(f"Tray helper failed to import rumps: {e}")
        sys.exit(1)

def acquire_single_instance_lock():
    """Проверяет, что приложение не запущено дважды"""
    lock_file = Path.home() / "Library" / "Application Support" / "Nexy" / "nexy.lock"
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        fd = os.open(str(lock_file), os.O_CREAT | os.O_WRONLY | os.O_TRUNC)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        
        # Сохраняем fd для освобождения при выходе
        atexit.register(_release_single_instance_lock, fd, lock_file)
        
        return True
    except (OSError, IOError):
        print("❌ Приложение уже запущено. Закройте предыдущий экземпляр.")
        return False

def _release_single_instance_lock(fd, lock_file):
    """Освобождает блокировку при выходе"""
    try:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
        lock_file.unlink(missing_ok=True)
    except Exception as e:
        print(f"⚠️ Ошибка освобождения блокировки: {e}")

def get_optimal_audio_config(device_name: str = None):
    """
    Умная функция определения оптимальных параметров аудио для любого устройства
    
    Args:
        device_name: Название устройства (опционально)
        
    Returns:
        dict: Оптимальные параметры аудио
    """
    if not device_name:
        device_name = "default"
    
    device_lower = device_name.lower()
    
    # Определяем тип устройства и оптимальные параметры
    if any(keyword in device_lower for keyword in ['airpods', 'beats', 'bluetooth']):
        # Bluetooth наушники - требуют 44100 Hz
        return {
            'sample_rate': 44100,
            'channels': 2,
            'dtype': 'int16',
            'device_type': 'bluetooth_headphones'
        }
    elif any(keyword in device_lower for keyword in ['usb', 'wired', 'headphones', 'headset']):
        # Проводные наушники - могут использовать 48000 Hz
        return {
            'sample_rate': 48000,
            'channels': 2,
            'dtype': 'int16',
            'device_type': 'wired_headphones'
        }
    elif any(keyword in device_lower for keyword in ['speakers', 'built-in', 'macbook', 'imac']):
        # Встроенные динамики - 48000 Hz
        return {
            'sample_rate': 48000,
            'channels': 2,
            'dtype': 'int16',
            'device_type': 'speakers'
        }
    else:
        # Универсальная конфигурация - 48000 Hz
        return {
            'sample_rate': 48000,
            'channels': 2,
            'dtype': 'int16',
            'device_type': 'unknown'
        }

def resample_audio_for_device(audio_data, from_rate, to_rate):
    """
    Умный ресэмплинг аудио для совместимости с устройством
    
    Args:
        audio_data: numpy array с аудио данными
        from_rate: Исходная частота дискретизации
        to_rate: Целевая частота дискретизации
        
    Returns:
        numpy array: Ресэмплированные аудио данные
    """
    import numpy as np
    
    if from_rate == to_rate:
        return audio_data
    
    # Простой ресэмплинг без scipy
    ratio = to_rate / from_rate
    target_length = int(len(audio_data) * ratio)
    
    if ratio > 1:
        # Увеличиваем частоту - интерполяция
        indices = np.linspace(0, len(audio_data) - 1, target_length, dtype=int)
        return audio_data[indices]
    else:
        # Уменьшаем частоту - децимация
        step = int(1 / ratio)
        return audio_data[::step]

class AppState(Enum):
    LISTENING = 1     # Ассистент слушает команды (микрофон активен)
    PROCESSING = 2    # Ассистент обрабатывает команду (микрофон неактивен)
    SLEEPING = 3      # Ассистент спит, ждет команды (микрофон неактивен)

class StateManager:
    """
    Управляет переходами между состояниями приложения.
    Каждое состояние знает, как реагировать на каждое событие.
    """
    
    def __init__(self, console, audio_player, stt_recognizer, screen_capture, grpc_client, network_manager=None, hardware_id=None, input_handler=None, tray_controller=None, config=None):
        self.console = console
        self.audio_player = audio_player
        self.stt_recognizer = stt_recognizer
        self.screen_capture = screen_capture
        self.grpc_client = grpc_client
        self.network_manager = network_manager
        self.hardware_id = hardware_id
        self.input_handler = input_handler  # Ссылка на InputHandler для синхронизации
        self.tray_controller = tray_controller
        self.config = config or {}
        self.update_manager = None  # Инициализируем update_manager
        
        # Инициализируем tray controller если не передан
        if self.tray_controller is None:
            try:
                tray_config = create_default_config()
                self.tray_controller = initialize_global_tray_controller(tray_config)
                self._setup_tray_callbacks()
            except Exception as e:
                handle_permission_error(e, "StateManager", "__init__", "Инициализация tray controller")
                self.tray_controller = None
        
        # Состояние приложения
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
            
            # Callback для изменения состояния
            self.tray_controller.add_callback("state_changed", self._on_tray_state_changed)
            
        except Exception as e:
            handle_threading_error(e, "StateManager", "_setup_tray_callbacks", "Настройка tray callbacks")
    
    def _on_tray_status(self, data=None):
        """Обрабатывает нажатие на Status в tray menu"""
        try:
            status = self.tray_controller.get_status() if self.tray_controller else {}
            self.console.print(f"[blue]📊 Tray Status: {status}[/blue]")
        except Exception as e:
            handle_threading_error(e, "StateManager", "_on_tray_status", "Обработка tray status")
    
    def _on_tray_settings(self, data=None):
        """Обрабатывает нажатие на Settings в tray menu"""
        try:
            self.console.print("[blue]⚙️ Настройки (пока не реализованы)[/blue]")
        except Exception as e:
            handle_threading_error(e, "StateManager", "_on_tray_settings", "Обработка tray settings")
    
    def _on_tray_about(self, data=None):
        """Обрабатывает нажатие на About в tray menu"""
        try:
            self.console.print("[blue]ℹ️ Nexy AI Voice Assistant v1.0[/blue]")
        except Exception as e:
            handle_threading_error(e, "StateManager", "_on_tray_about", "Обработка tray about")
    
    def _on_tray_quit(self, data=None):
        """Обрабатывает нажатие на Quit в tray menu"""
        try:
            self.console.print("[yellow]👋 Выход по запросу из tray menu[/yellow]")
            # Здесь можно добавить логику для graceful shutdown
        except Exception as e:
            handle_threading_error(e, "StateManager", "_on_tray_quit", "Обработка tray quit")
    
    def _on_tray_state_changed(self, data=None):
        """Обрабатывает изменение состояния tray icon"""
        try:
            if data and "old_state" in data and "new_state" in data:
                old_state = data["old_state"]
                new_state = data["new_state"]
                self.console.print(f"[dim]🔄 Tray state changed: {old_state.value} → {new_state.value}[/dim]")
        except Exception as e:
            handle_threading_error(e, "StateManager", "_on_tray_state_changed", "Обработка tray state change")
        
        # Централизованное управление состоянием микрофона
        import threading
        self._microphone_state = {
            'is_recording': False,
            'last_start_time': 0,
            'last_stop_time': 0,
            'state_lock': threading.Lock()
        }
        
        # SPARKLE UPDATE MANAGER ИНИЦИАЛИЗАЦИЯ
        self.update_manager = None
        self.update_task = None
        
        if SPARKLE_AVAILABLE and self.config.get('sparkle', {}).get('enabled', True):
            try:
                self.update_manager = create_improved_sparkle_update_manager(self.config)
                self.console.print("[bold green]✅ Sparkle Update Manager инициализирован[/bold green]")
            except Exception as e:
                handle_config_error(e, "StateManager", "init_sparkle", "Инициализация Sparkle")
                self.console.print(f"[bold yellow]⚠️ Ошибка инициализации Sparkle: {e}[/bold yellow]")
                self.update_manager = None
        else:
            self.console.print("[bold yellow]⚠️ Sparkle Update Manager отключен[/bold yellow]")
    
    async def start_update_checker(self):
        """Запуск проверки обновлений в фоне"""
        if not self.update_manager:
            self.console.print("[yellow]⚠️ Sparkle Update Manager не инициализирован[/yellow]")
            return
        
        if self.update_task is None:
            self.update_task = asyncio.create_task(
                self.update_manager.start_update_checker()
            )
            self.console.print("[bold green]🔄 Sparkle Update Checker запущен[/bold green]")
        else:
            self.console.print("[yellow]⚠️ Sparkle Update Checker уже запущен[/yellow]")
    
    async def stop_update_checker(self):
        """Остановка проверки обновлений"""
        if self.update_task:
            self.update_task.cancel()
            try:
                await self.update_task
            except asyncio.CancelledError:
                pass
            self.update_task = None
            self.console.print("[yellow]⏹️ Sparkle Update Checker остановлен[/yellow]")
    
    def get_update_status(self):
        """Получение статуса системы обновлений"""
        if self.update_manager:
            return self.update_manager.get_status()
        return {'sparkle_available': False, 'error': 'Update manager not initialized'}
    
    def _write_tray_status_file(self, state_name: str):
        def write_async():
            try:
                path = _get_status_file_path()
                with open(path, "w") as f:
                    json.dump({"state": state_name, "ts": time.time()}, f)
            except Exception:
                pass
        
        # Запускаем в фоне
        threading.Thread(target=write_async, daemon=True).start()

    def _log_state_transition(self, from_state: AppState, to_state: AppState, reason: str = ""):
        """Логирует переходы между состояниями"""
        self.console.print(f"[dim]🔄 {from_state.name} → {to_state.name}[/dim] {reason}")
        self._write_tray_status_file(to_state.name)
        
        # Синхронизируем с tray controller
        if self.tray_controller:
            try:
                # Маппинг состояний AppState на TrayState
                state_mapping = {
                    AppState.SLEEPING: TrayState.SLEEPING,
                    AppState.LISTENING: TrayState.LISTENING,
                    AppState.PROCESSING: TrayState.PROCESSING
                }
                
                tray_state = state_mapping.get(to_state, TrayState.SLEEPING)
                self.tray_controller.set_state(tray_state)
                
            except Exception as e:
                handle_threading_error(e, "StateManager", "_log_state_transition", "Синхронизация с tray controller")

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
        
        # Запускаем STT - ИСПРАВЛЕНО: используем правильный метод
        if self.stt_recognizer:
            self.stt_recognizer.start_recording_without_activation()
        
        return True

    def stop_listening(self) -> bool:
        """Останавливает прослушивание команд и обрабатывает распознанный текст"""
        if not self._can_stop_listening():
            return False
        
        self._log_state_transition(self.state, AppState.SLEEPING, "(пользователь отпустил кнопку)")
        self.state = AppState.SLEEPING
        
        # Останавливаем STT и получаем распознанный текст - ИСПРАВЛЕНО
        if self.stt_recognizer:
            future = self.stt_recognizer.stop_recording_and_recognize()
            if future:
                # Используем синхронное ожидание с таймаутом
                try:
                    recognized_text = future.result(timeout=10)  # 10 секунд таймаут
                except Exception as e:
                    handle_audio_error(e, "StateManager", "process_command", "Распознавание речи")
                    self.console.print(f"[yellow]⚠️ Ошибка распознавания: {e}[/yellow]")
                    recognized_text = None
            else:
                recognized_text = None
            
            # Если текст распознан, отправляем на сервер
            if recognized_text and recognized_text.strip():
                self.console.print(f"[bold green]🎤 Распознано: {recognized_text}[/bold green]")
                # Запускаем обработку команды асинхронно
                asyncio.create_task(self._process_command(recognized_text))
            else:
                self.console.print("[yellow]⚠️ Речь не распознана[/yellow]")
        
        return True

    async def _process_command(self, command: str):
        """Обрабатывает распознанную команду - отправляет на сервер"""
        try:
            self.console.print(f"[blue]🔄 Обработка команды: {command}[/blue]")
            
            # Переходим в состояние обработки
            self._log_state_transition(self.state, AppState.PROCESSING, "(команда распознана)")
            self.state = AppState.PROCESSING
            
            # Создаем задачу для отслеживания прерывания
            self.streaming_task = asyncio.current_task()
            
            # Получаем скриншот с помощью Improved Screen Capture
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
                        self.console.print(f"[blue]📸 Скриншот получен: {screen_info.get('width', 0)}x{screen_info.get('height', 0)}[/blue]")
                except Exception as e:
                    handle_device_error(e, "StateManager", "process_command", "Захват экрана")
                    self.console.print(f"[yellow]⚠️ Ошибка захвата экрана: {e}[/yellow]")
            
            # Отправляем на сервер через gRPC
            if self.grpc_client:
                try:
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
                                self.console.print("[red]🛑 Прерывание обнаружено, останавливаем стрим[/red]")
                                break
                            
                            # Обрабатываем ответы от сервера
                            if response.HasField("text_chunk"):
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
                                    optimal_config = get_optimal_audio_config(current_device)
                                    
                                    self.console.print(f"[blue]🔍 Аудио данные: shape={audio_data.shape}, dtype={audio_data.dtype}, min={audio_data.min()}, max={audio_data.max()}[/blue]")
                                    self.console.print(f"[blue]🔍 AudioPlayer: sample_rate={self.audio_player.sample_rate}, channels={self.audio_player.channels}[/blue]")
                                    self.console.print(f"[blue]🔍 Устройство: {current_device} → оптимальная частота: {optimal_config['sample_rate']} Hz[/blue]")
                                    
                                    # УМНЫЙ РЕСЭМПЛИНГ: Адаптируем аудио под устройство
                                    if self.audio_player.sample_rate != optimal_config['sample_rate']:
                                        self.console.print(f"[yellow]🔄 Ресэмплинг: {self.audio_player.sample_rate} Hz → {optimal_config['sample_rate']} Hz[/yellow]")
                                        audio_data = resample_audio_for_device(
                                            audio_data, 
                                            self.audio_player.sample_rate, 
                                            optimal_config['sample_rate']
                                        )
                                        self.console.print(f"[green]✅ Ресэмплинг завершен: {len(audio_data)} сэмплов[/green]")
                                    
                                    self.audio_player.add_audio_data(audio_data)
                            elif response.HasField("end_message"):
                                self.console.print(f"[green]✅ {response.end_message}[/green]")
                                break
                            elif response.HasField("error_message"):
                                self.console.print(f"[red]❌ {response.error_message}[/red]")
                                break
                    
                        self.console.print("[green]✅ Команда обработана[/green]")
                    
                    except asyncio.CancelledError:
                        self.console.print("[red]🛑 gRPC стрим прерван пользователем[/red]")
                        raise
                    except Exception as e:
                        handle_network_error(e, "StateManager", "process_command", "gRPC стрим")
                        self.console.print(f"[red]❌ Ошибка gRPC стрима: {e}[/red]")
                    finally:
                        # Останавливаем воспроизведение после завершения стрима
                        if self.audio_player and self.audio_player._is_playing:
                            self.audio_player.stop_playback()
                    
                except Exception as e:
                    handle_network_error(e, "StateManager", "process_command", "Отправка на сервер")
                    self.console.print(f"[red]❌ Ошибка отправки на сервер: {e}[/red]")
            else:
                self.console.print("[yellow]⚠️ gRPC клиент недоступен[/yellow]")
            
        except Exception as e:
            handle_threading_error(e, "StateManager", "process_command", "Обработка команды")
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
                self.console.print("[red]🔇 Аудио прервано[/red]")
            except Exception as e:
                handle_audio_error(e, "StateManager", "stop_audio", "Остановка аудио")
                self.console.print(f"[yellow]⚠️ Ошибка остановки аудио: {e}[/yellow]")
        
        # ПРЕРЫВАЕМ gRPC СТРИМ
        if self.streaming_task and not self.streaming_task.done():
            self.streaming_task.cancel()
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

    def cleanup(self):
        """Очистка ресурсов при выходе"""
        try:
            # Останавливаем проверку обновлений
            if self.update_task:
                self.update_task.cancel()
            
            # Останавливаем STT
            if self.stt_recognizer:
                future = self.stt_recognizer.stop_recording_and_recognize()
                if future:
                    # Не ждем результат, просто останавливаем запись
                    pass
            
            # Очищаем другие ресурсы
            if self.audio_player:
                self.audio_player.shutdown()
            
            self.console.print("[dim]🧹 Ресурсы очищены[/dim]")
        except Exception as e:
            handle_memory_error(e, "StateManager", "cleanup", "Очистка ресурсов")
            self.console.print(f"[dim]⚠️ Ошибка очистки ресурсов: {e}[/dim]")

async def main():
    """Основная функция Nexy AI Voice Assistant"""
    
    # Инициализируем компоненты в правильном порядке
    console = Console()
    console.print("[bold blue]🔧 Инициализация компонентов...[/bold blue]")
    
    # 0. Сначала инициируем запросы системных разрешений (Screen, Mic, Accessibility, Apple Events)
    try:
        permission_manager = PermissionManager()
        permission_manager.check_all_permissions()
    except Exception:
        pass
    
    # Загружаем конфиг
    config_path = Path(__file__).parent / 'config' / 'app_config.yaml'
    config = {}
    try:
        # Загрузка конфигурации в фоновом потоке
        config_future = asyncio.get_event_loop().run_in_executor(
            None, lambda: yaml.safe_load(open(config_path, 'r')) or {}
        )
        config = await config_future
    except Exception as e:
        handle_config_error(e, "main", "load_config", "Загрузка конфигурации")
        console.print(f"[yellow]⚠️ Не удалось загрузить конфиг: {e}[/yellow]")

    # Добавляем настройки Sparkle в конфиг если их нет
    if 'sparkle' not in config:
        config['sparkle'] = {
            'enabled': True,
            'appcast_url': 'http://localhost:8080/appcast.xml',
            'auto_install': False,  # Отключаем для тестирования
            'check_interval': 30,  # Проверяем каждые 30 секунд
            'update_check_on_startup': True,
            'update_check_in_background': True,
            'accessibility': {
                'announce_updates': True,
                'announce_installation': True,
                'auto_install': False
            }
        }
        console.print("[green]✅ Настройки Sparkle добавлены в конфиг[/green]")

    audio_cfg = (config.get('audio') or {})
    audio_follow_default = bool(audio_cfg.get('follow_system_default', True))
    bt_policy = (audio_cfg.get('bluetooth_policy') or 'prefer_quality')
    settle_ms = int(audio_cfg.get('settle_ms', 400))
    retries = int(audio_cfg.get('retries', 3))
    preflush = bool(audio_cfg.get('preflush_on_switch', True))
    use_coreaudio_listeners = bool(audio_cfg.get('use_coreaudio_listeners', False))
    
    # Новая конфигурация AudioManagerDaemon
    device_manager_cfg = audio_cfg.get('device_manager', {})
    device_manager_enabled = bool(device_manager_cfg.get('enabled', True))
    device_manager_config = {
        'monitoring_interval': float(device_manager_cfg.get('monitoring_interval', 3.0)),
        'switch_cooldown': float(device_manager_cfg.get('switch_cooldown', 2.0)),
        'cache_timeout': float(device_manager_cfg.get('cache_timeout', 5.0))
    }
                                                                      
    # 1. STT будет инициализирован после создания StateManager
    
    # 2. Инициализируем улучшенный захват экрана
    console.print("[blue]📸 Инициализация Improved Screen Capture...[/blue]")
    try:
        screen_config = create_screen_config()
        screen_capture = create_improved_screen_capture(screen_config)
        console.print("[bold green]✅ Improved Screen Capture инициализирован[/bold green]")
    except Exception as e:
        handle_device_error(e, "main", "init_screen_capture", "Инициализация Improved Screen Capture")
        console.print(f"[bold yellow]⚠️ Improved Screen Capture недоступен: {e}[/bold yellow]")
        screen_capture = None

    # 3. Инициализируем Network Manager
    console.print("[blue]🌐 Инициализация Network Manager...[/blue]")
    try:
        network_config = create_network_config()
        network_manager = create_network_manager(network_config)
        console.print("[bold green]✅ Network Manager инициализирован[/bold green]")
    except Exception as e:
        handle_network_error(e, "main", "init_network_manager", "Инициализация Network Manager")
        console.print(f"[bold red]❌ Ошибка инициализации Network Manager: {e}[/bold red]")
        return

    # 4. Инициализируем улучшенный gRPC клиент
    console.print("[blue]🌐 Инициализация улучшенного gRPC клиента...[/blue]")
    try:
        grpc_config = create_grpc_config()
        grpc_client = create_improved_grpc_client(grpc_config)
        console.print("[bold green]✅ Улучшенный gRPC клиент инициализирован[/bold green]")
    except Exception as e:
        handle_network_error(e, "main", "init_grpc_client", "Инициализация gRPC клиента")
        console.print(f"[bold red]❌ Ошибка инициализации gRPC клиента: {e}[/bold red]")
        return

    # 5. Получаем Hardware ID
    console.print("[blue]🆔 Получение Hardware ID...[/blue]")
    try:
        hardware_id = get_hardware_id()
        hardware_info = get_hardware_info()
        console.print(f"[bold green]✅ Hardware ID: {hardware_id}[/bold green]")
        console.print(f"[dim]💻 Hardware Info: {hardware_info}[/dim]")
    except Exception as e:
        handle_device_error(e, "main", "get_hardware_id", "Получение Hardware ID")
        console.print(f"[bold red]❌ Ошибка получения Hardware ID: {e}[/bold red]")
        return

    # 6. Инициализируем упрощенную аудио систему
    console.print("[blue]🔊 Инициализация упрощенной аудио системы...[/blue]")
    try:
        # Инициализируем упрощенную аудио систему
        audio_system = get_global_simplified_audio_system()
        if not audio_system.initialize():
            raise Exception("Не удалось инициализировать SimplifiedAudioSystem")
        
        # Инициализируем упрощенный аудио плеер
        audio_player = get_global_thread_safe_audio_player()
        
        console.print("[bold green]✅ Упрощенная аудио система инициализирована[/bold green]")
    except Exception as e:
        handle_audio_error(e, "main", "init_audio_system", "Инициализация аудио системы")
        console.print(f"[bold red]❌ Ошибка инициализации аудио системы: {e}[/bold red]")
        return

    # 7. Инициализируем STT
    console.print("[blue]🎤 Инициализация распознавания речи...[/blue]")
    try:
        stt_recognizer = StreamRecognizer()
        console.print("[bold green]✅ STT инициализирован[/bold green]")
    except Exception as e:
        handle_audio_error(e, "main", "init_stt", "Инициализация STT")
        console.print(f"[bold red]❌ Ошибка инициализации STT: {e}[/bold red]")
        return

    # 8. Инициализируем Improved Input Handler
    console.print("[blue]⌨️ Инициализация Improved Input Handler...[/blue]")
    try:
        # Создаем очередь для событий
        input_queue = asyncio.Queue()
        input_config = create_input_config()
        input_handler = create_improved_input_handler(
            loop=asyncio.get_event_loop(), 
            queue=input_queue,
            config=input_config
        )
        input_handler.start()
        console.print("[bold green]✅ Improved Input Handler инициализирован[/bold green]")
    except Exception as e:
        handle_threading_error(e, "main", "init_input_handler", "Инициализация Improved Input Handler")
        console.print(f"[bold yellow]⚠️ Improved Input Handler недоступен: {e}[/bold yellow]")
        input_handler = None

    # 8. Инициализируем TrayController
    console.print("[blue]📱 Инициализация TrayController...[/blue]")
    try:
        tray_config = create_default_config()
        tray_controller = initialize_global_tray_controller(tray_config)
        console.print("[bold green]✅ TrayController инициализирован[/bold green]")
    except Exception as e:
        handle_permission_error(e, "main", "init_tray_controller", "Инициализация TrayController")
        console.print(f"[bold yellow]⚠️ TrayController недоступен: {e}[/bold yellow]")
        tray_controller = None

    # 9. Создаем StateManager с конфигом
    console.print("[blue]🧠 Инициализация StateManager...[/blue]")
    state_manager = StateManager(
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
    console.print("[bold green]✅ StateManager инициализирован[/bold green]")

    # 10. SPARKLE UPDATE MANAGER - Запуск системы обновлений
    console.print("[blue]🔄 Инициализация системы обновлений...[/blue]")
    if state_manager.update_manager and state_manager.update_manager.sparkle_path:
        await state_manager.start_update_checker()
        console.print("[bold green]✅ Система автообновлений активирована[/bold green]")
        
        # Показываем статус обновлений
        status = state_manager.get_update_status()
        console.print(f"[dim]📊 Статус обновлений: {status}[/dim]")
    else:
        console.print("[bold yellow]⚠️ Sparkle Framework не найден, автообновления отключены[/bold yellow]")

    # 10. Audio Device Manager теперь встроен в SimplifiedAudioSystem
    console.print("[dim]🎧 Audio Device Manager встроен в SimplifiedAudioSystem[/dim]")

    # 11. Основной цикл приложения
    console.print("[bold green]🚀 Nexy AI Voice Assistant запущен![/bold green]")
    console.print("[dim]Нажмите и удерживайте кнопку для активации...[/dim]")
    
    try:
        # Здесь был бы основной цикл приложения
        # Для демонстрации просто ждем некоторое время
        console.print("[blue]🔄 Запуск основного цикла...[/blue]")
        
        # Демонстрация работы системы обновлений
        if state_manager.update_manager:
            console.print("[blue]🧪 Тестирование системы обновлений...[/blue]")
            
            # Ждем немного для демонстрации
            await asyncio.sleep(5)
            
            # Проверяем статус обновлений
            status = state_manager.get_update_status()
            console.print(f"[green]📊 Статус обновлений: {status}[/green]")
            
            # Симулируем проверку обновлений
            console.print("[blue]🔍 Проверка обновлений...[/blue]")
            try:
                result = await state_manager.update_manager._check_via_http()
                if result and result.get('update_available'):
                    console.print(f"[green]🆕 Доступно обновление: {result.get('version')}[/green]")
                else:
                    console.print("[yellow]ℹ️ Обновления не найдены[/yellow]")
            except Exception as e:
                handle_network_error(e, "main", "check_updates", "Проверка обновлений")
                console.print(f"[red]❌ Ошибка проверки обновлений: {e}[/red]")
        
        # Основной цикл обработки событий
        console.print("[blue]⏳ Приложение работает... (нажмите ПРОБЕЛ для активации микрофона)[/blue]")
        
        # Запускаем обработку событий от InputHandler
        async def process_input_events():
            """Обрабатывает события от InputHandler"""
            while True:
                try:
                    # Ждем событие от InputHandler
                    event = await input_queue.get()
                    
                    if event == 'start_recording':
                        console.print("[green]🎤 Микрофон активирован (удерживайте ПРОБЕЛ)[/green]")
                        state_manager.start_listening()
                    elif event == 'deactivate_microphone':
                        console.print("[yellow]🎤 Микрофон деактивирован[/yellow]")
                        state_manager.stop_listening()
                    elif event == 'interrupt_or_cancel':
                        console.print("[red]🛑 Прерывание команды[/red]")
                        state_manager.sleep()
                    
                    input_queue.task_done()
                except Exception as e:
                    handle_threading_error(e, "main", "process_events", "Обработка события")
                    console.print(f"[red]❌ Ошибка обработки события: {e}[/red]")
        
        # Функция для обработки улучшенных событий ввода
        async def process_improved_input_events():
            """Обрабатывает улучшенные события ввода от ImprovedInputHandler"""
            while True:
                try:
                    # Ждем событие из очереди
                    event = await input_queue.get()
                    
                    # Обрабатываем событие через StateManager
                    if state_manager and hasattr(event, 'event_type'):
                        if event.event_type == InputEventType.KEY_PRESS:
                            console.print("[green]🎤 Микрофон активирован (удерживайте ПРОБЕЛ)[/green]")
                            state_manager.start_listening()
                        elif event.event_type == InputEventType.KEY_RELEASE:
                            console.print("[yellow]🎤 Микрофон деактивирован[/yellow]")
                            state_manager.stop_listening()
                        elif event.event_type == InputEventType.SHORT_PRESS:
                            # Короткое нажатие - быстрая команда
                            console.print("[blue]⚡ Быстрая команда[/blue]")
                            state_manager.start_listening()
                            await asyncio.sleep(0.1)  # Небольшая задержка
                            state_manager.stop_listening()
                        elif event.event_type == InputEventType.LONG_PRESS:
                            # Длительное нажатие - прерывание
                            console.print("[red]🛑 Прерывание команды[/red]")
                            state_manager.sleep()
                    
                    # Помечаем задачу как выполненную
                    input_queue.task_done()
                except Exception as e:
                    handle_threading_error(e, "main", "process_improved_input_events", "Обработка улучшенных событий ввода")
                    console.print(f"[red]❌ Ошибка обработки улучшенных событий ввода: {e}[/red]")
                    await asyncio.sleep(0.1)
        
        # Запускаем обработку событий в фоне
        if input_handler:
            event_task = asyncio.create_task(process_improved_input_events())
        
        # Ждем сигнала завершения
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            console.print("\n[yellow]🛑 Получен сигнал завершения...[/yellow]")
    
    except Exception as e:
        handle_threading_error(e, "main", "main", "Критическая ошибка")
        console.print(f"[bold red]❌ Критическая ошибка: {e}[/bold red]")
        raise
    finally:
        # Очистка ресурсов
        console.print("[blue]🧹 Очистка ресурсов...[/blue]")
        try:
            if state_manager:
                state_manager.cleanup()
            if input_handler:
                input_handler.stop()
            if network_manager:
                await network_manager.cleanup()
            if grpc_client:
                await grpc_client.cleanup()
            shutdown_global_tray_controller()
            console.print("[bold green]✅ Приложение завершено[/bold green]")
        except Exception as e:
            handle_memory_error(e, "main", "cleanup", "Очистка ресурсов")
            console.print(f"[dim]⚠️ Ошибка очистки ресурсов: {e}[/dim]")

if __name__ == "__main__":
    # Проверяем блокировку
    if not acquire_single_instance_lock():
        sys.exit(1)
    
    # Запускаем приложение
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 До свидания!")
    except Exception as e:
        handle_threading_error(e, "main", "main", "Критическая ошибка")
        print(f"❌ Критическая ошибка: {e}")
        sys.exit(1)
