import sounddevice as sd
import numpy as np
import speech_recognition as sr
import threading
import time
import os
from rich.console import Console

# Настройка FLAC для Apple Silicon
os.environ['FLAC_PATH'] = '/opt/homebrew/bin/flac'

console = Console()

class StreamRecognizer:
    """
    Распознаватель речи с push-to-talk логикой.
    Записывает аудио только при удержании пробела.
    """
    
    def __init__(self, sample_rate=16000, chunk_size=1024, channels=1):
        self.sample_rate = sample_rate  # 16kHz - оптимально для распознавания речи
        self.chunk_size = chunk_size
        self.channels = channels
        self.dtype = 'int16'
        
        self.stream = None
        self.is_recording = False
        self.audio_chunks = []
        self.recording_thread = None
        # Безопасная работа со стримом и слежение за устройством
        self.stream_lock = threading.Lock()
        self.current_input_device = None
        self.device_monitor_thread = None
        self.stop_device_monitor = threading.Event()
        
        # Инициализируем распознаватель с оптимизированными параметрами
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 100  # Снижаем порог энергии для лучшего распознавания
        self.recognizer.dynamic_energy_threshold = True  # Динамический порог
        self.recognizer.pause_threshold = 0.5  # Уменьшаем порог паузы
        self.recognizer.phrase_threshold = 0.3  # Порог фразы
        self.recognizer.non_speaking_duration = 0.3  # Длительность не-речи
        
        # Ссылка на аудио плеер (инжектируется извне)
        self.audio_player = None
        
        # Кэширование для быстрого перезапуска
        self._cached_stream_config = None
        self._stream_cache_valid = False
        self._cache_lock = threading.Lock()

    def set_audio_player(self, audio_player):
        """Устанавливает ссылку на AudioPlayer для координации записи/воспроизведения."""
        self.audio_player = audio_player
    
    def _get_cached_stream_config(self):
        """Получает закэшированную конфигурацию STT потока"""
        with self._cache_lock:
            if self._stream_cache_valid and self._cached_stream_config:
                return self._cached_stream_config.copy()
            return None
    
    def _cache_stream_config(self, config):
        """Кэширует конфигурацию STT потока"""
        with self._cache_lock:
            self._cached_stream_config = config.copy()
            self._stream_cache_valid = True
    
    def _invalidate_stream_cache(self):
        """Инвалидирует кэш STT конфигурации"""
        with self._cache_lock:
            self._stream_cache_valid = False
            self._cached_stream_config = None
    
    def _start_recording_with_config(self, config):
        """Быстрый запуск записи с закэшированной конфигурацией"""
        try:
            # Создаем поток с кэшированными параметрами
            with self.stream_lock:
                self.stream = sd.InputStream(
                    device=config.get('device'),
                    channels=config.get('channels', self.channels),
                    samplerate=config.get('samplerate', self.sample_rate),
                    dtype=config.get('dtype', self.dtype),
                    callback=lambda indata, frames, time_info, status: self._input_callback_proxy(indata, frames, status),
                    blocksize=self.chunk_size
                )
                self.stream.start()
            
            console.print(f"[dim]⚡ STT запись запущена с кэшированной конфигурацией[/dim]")
            console.print(f"[dim]🎙️ start_recording: input={config.get('device_name', 'Unknown')} (index={config.get('device')})[/dim]")
            
        except Exception as e:
            console.print(f"[red]❌ Ошибка быстрого запуска STT: {e}[/red]")
            raise
    
    def prepare_for_recording(self):
        """Умная подготовка к записи - останавливаем только если действительно играет."""
        try:
            ap = getattr(self, 'audio_player', None)
            if ap and hasattr(ap, 'is_playing') and ap.is_playing:
                # Останавливаем только если действительно играет
                logger.info("🎤 Останавливаю воспроизведение для записи")
                ap.stop_playback()
            else:
                logger.debug("🎤 Плеер уже неактивен, пропускаю остановку")
        except Exception as e:
            logger.warning(f"⚠️ Ошибка подготовки к записи: {e}")
        
    def start_recording(self):
        """Начинает запись аудио при нажатии пробела с оптимизацией кэширования"""
        # КРИТИЧНО: если уже записываем - сначала останавливаем предыдущую запись
        if self.is_recording:
            console.print("[yellow]⚠️ Запись уже идет - сначала останавливаю предыдущую...[/yellow]")
            self.stop_recording_and_recognize()
            # Небольшая задержка для стабилизации
            time.sleep(0.05)
            
        self.is_recording = True
        self.audio_chunks = []
        
        # Проверяем кэш для быстрого перезапуска
        cached_config = self._get_cached_stream_config()
        if cached_config:
            console.print("[dim]⚡ Использую закэшированную конфигурацию STT для быстрого запуска[/dim]")
            try:
                self._start_recording_with_config(cached_config)
                return
            except Exception as e:
                console.print(f"[yellow]⚠️ Ошибка с кэшированной конфигурацией STT: {e}[/yellow]")
                self._invalidate_stream_cache()
        
        # Диагностика: снимок CoreAudio (default + количество устройств)
        try:
            import sounddevice as _sd
            hostapis = _sd.query_hostapis()
            core_idx = next((i for i,a in enumerate(hostapis) if 'core' in (a.get('name','').lower())), 0)
            api = _sd.query_hostapis(core_idx)
            din = api.get('default_input_device', -1)
            dout = api.get('default_output_device', -1)
            devs = _sd.query_devices()
            devs_count = sum(1 for d in devs if (d.get('max_input_channels',0)>0 or d.get('max_output_channels',0)>0))
            console.print(f"[dim]🧪 Snapshot @start_recording: din={None if din==-1 else din} dout={None if dout==-1 else dout} devices={devs_count}[/dim]")
        except Exception:
            pass

        # Определяем входное устройство: ТОЛЬКО системный default
        # Учитываем конфигурацию bluetooth_policy и follow_system_default
        settle_ms = int(getattr(self, 'config', {}).get('settle_ms', 400))
        retries = int(getattr(self, 'config', {}).get('retries', 3))
        bt_policy = getattr(self, 'config', {}).get('bluetooth_policy', 'prefer_quality')

        # ПРИНУДИТЕЛЬНО обновляем список устройств перед определением input
        console.print("[dim]🔄 Принудительно обновляю список аудио устройств для микрофона...[/dim]")
        try:
            # Останавливаем все потоки для "чистого" состояния
            sd.stop()
            time.sleep(0.1)
            
            # Принудительно обновляем список устройств
            devices = sd.query_devices()
            hostapis = sd.query_hostapis()
            core_idx = next((i for i, a in enumerate(hostapis) if 'core' in (a.get('name','').lower())), 0)
            api = sd.query_hostapis(core_idx)
            current_default_in = api.get('default_input_device', -1)
            
            console.print(f"[dim]📱 Обновленный список устройств: {len(devices)} устройств[/dim]")
            console.print(f"[dim]🎙️ Текущий default input: {current_default_in}[/dim]")
            
            # Показываем ВСЕ устройства (не только input)
            for i, dev in enumerate(devices):
                name = dev.get('name', 'Unknown')
                in_ch = dev.get('max_input_channels', 0)
                out_ch = dev.get('max_output_channels', 0)
                if in_ch > 0 or out_ch > 0:
                    console.print(f"[dim]  📱 {i}: {name} (in:{in_ch} out:{out_ch})[/dim]")
            
            # Проверяем, что дефолты корректны
            if current_default_in != -1 and current_default_in < len(devices):
                default_in_name = devices[current_default_in].get('name', 'Unknown')
                console.print(f"[dim]🎙️ Default input: {current_default_in} — {default_in_name}[/dim]")
            else:
                console.print(f"[yellow]⚠️ Некорректный default input: {current_default_in}[/yellow]")
                
        except Exception as e:
            console.print(f"[yellow]⚠️ Не удалось обновить список устройств: {e}[/yellow]")

        # Если есть listener с кэшем — используем его
        input_device = None
        try:
            ca_listener = getattr(self, 'default_listener', None)
            if ca_listener is not None and hasattr(ca_listener, 'get_default_input'):
                input_device = ca_listener.get_default_input()
        except Exception:
            input_device = None
        if input_device is None:
            input_device = self._resolve_input_device()
        # Если политика качества и default output = AirPods, форсируем встроенный микрофон
        if bt_policy == 'prefer_quality':
            try:
                default = sd.default.device
                if isinstance(default, (list, tuple)) and len(default) >= 2:
                    out_idx = default[1]
                    if out_idx is not None and out_idx != -1:
                        info_out = sd.query_devices(out_idx)
                        name_out = (info_out.get('name') or '').lower()
                        if 'airpods' in name_out:
                            # Ищем Built-in Microphone
                            for idx, dev in enumerate(sd.query_devices()):
                                if dev.get('max_input_channels', 0) > 0 and 'built-in' in (dev.get('name','').lower()):
                                    input_device = idx
                                    break
            except Exception:
                pass
        elif bt_policy == 'strict_default':
            # Ничего не делаем — всегда берём системный default input (включая AirPods)
            pass
        self.current_input_device = input_device

        # Callback для буферизации аудио чанков
        def _callback(indata, frames, time_info, status):
            if status:
                console.print(f"[yellow]⚠️ Sounddevice status: {status}[/yellow]")
            if self.is_recording:
                if self.channels == 1:
                    chunk = indata.copy().reshape(-1)
                else:
                    # Берем первый канал, если многоканально
                    chunk = indata.copy()[:, 0]
                self.audio_chunks.append(chunk.astype(np.int16))

        # Открываем аудио поток через sounddevice с ретраями (на случай BT-переключений)
        # Предочистка, чтобы CoreAudio корректно применил новый default
        try:
            if bool(getattr(self, 'config', {}).get('preflush_on_switch', True)):
                if self.stream:
                    try:
                        self.stream.stop()
                        self.stream.close()
                    except Exception:
                        pass
                    self.stream = None
                sd.stop()
                time.sleep(max(0.05, settle_ms/1000.0))
        except Exception:
            pass

        # Во время записи запрещаем переключение выходного устройства и останавливаем воспроизведение,
        # если аудиоплеер доступен у main/state_manager (лениво через import и getattr)
        try:
            ap = getattr(self, 'audio_player', None)
            # СНАЧАЛА только мягко останавливаем воспроизведение (без принудительных переключений устройств)
            if ap and hasattr(ap, 'is_playing') and ap.is_playing and hasattr(ap, 'stop_playback'):
                ap.stop_playback()
        except Exception:
            pass

        last_err = None
        # Попробуем сначала с device info и его дефолтной частотой
        def_sr = None
        try:
            if input_device is not None:
                def_sr = int(round(sd.query_devices(input_device).get('default_samplerate')))
        except Exception:
            def_sr = None

        # Формируем список частот с учётом HFP у входного устройства (AirPods и т.п.)
        sample_rates = []
        hfp_in = False
        try:
            if input_device is not None:
                in_info = sd.query_devices(input_device)
                name_l = (in_info.get('name') or '').lower()
                max_in_ch = int(in_info.get('max_input_channels') or 0)
                def_sr_in = int(round(in_info.get('default_samplerate') or 0))
                if any(t in name_l for t in ['airpods', 'hands-free', 'handsfree', 'hfp', 'hsp']) or max_in_ch <= 1 or def_sr_in <= 16000:
                    hfp_in = True
        except Exception:
            pass

        # При HFP сначала пробуем 16000/8000
        if hfp_in:
            for sr in [16000, 8000]:
                if sr not in sample_rates:
                    sample_rates.append(sr)

        if def_sr and def_sr not in sample_rates:
            sample_rates.append(def_sr)
        for sr in [self.sample_rate, 48000, 44100, 32000, 22050, 16000, 12000, 11025, 8000]:
            if sr not in sample_rates:
                sample_rates.append(sr)

        # Ещё раз пересчитываем CoreAudio default input прямо перед открытием
        try:
            hostapis = sd.query_hostapis()
            core_idx = next((i for i,a in enumerate(hostapis) if 'core' in (a.get('name','').lower())), 0)
            api = sd.query_hostapis(core_idx)
            din = api.get('default_input_device', -1)
            dout = api.get('default_output_device', -1)
            if din is not None and din != -1:
                input_device = din
            # Диагностика: выбор input
            try:
                info_in = sd.query_devices(input_device) if input_device not in (None, -1) else None
                console.print(f"[blue]🎙️ start_recording: input={info_in['name'] if info_in else 'System Default'} (index={input_device})[/blue]")
            except Exception:
                pass
        except Exception:
            pass

        for attempt in range(max(1, retries)):
            # 1) Пытаемся с указанием девайса
            for sr in sample_rates:
                try:
                    with self.stream_lock:
                        self.stream = sd.InputStream(
                            channels=self.channels,
                            samplerate=sr,
                            dtype=self.dtype,
                            blocksize=self.chunk_size,
                            device=input_device,
                            callback=_callback,
                        )
                        self.stream.start()
                    last_err = None
                    self.sample_rate = sr
                    break
                except Exception as e:
                    last_err = e
            if last_err is None:
                break
            # 2) Пробуем без указания устройства (пусть CoreAudio выберет default)
            for sr in sample_rates:
                try:
                    with self.stream_lock:
                        self.stream = sd.InputStream(
            channels=self.channels,
                            samplerate=sr,
                            dtype=self.dtype,
                            blocksize=self.chunk_size,
                            device=None,
                            callback=_callback,
                        )
                        self.stream.start()
                    last_err = None
                    self.sample_rate = sr
                    break
                except Exception as e:
                    last_err = e
            if last_err is None:
                break

            time.sleep(max(0.1, settle_ms/1000.0))
            # Переопределяем default input между попытками
            input_device = self._resolve_input_device()

        if last_err is not None:
            # Строгий режим: не делаем fallback. Сообщаем об ошибке и завершаем запись
            self.is_recording = False
            console.print(f"[red]❌ Не удалось открыть InputStream на системном default: {last_err}[/red]")
            return
        
        console.print("[bold green]🎤 Запись началась...[/bold green]")
        
        # Кэшируем успешную конфигурацию для быстрого перезапуска
        if self.stream and hasattr(self.stream, 'channels') and hasattr(self.stream, 'samplerate'):
            config = {
                'device': input_device,
                'channels': self.stream.channels,
                'samplerate': self.stream.samplerate,
                'dtype': self.dtype,
                'device_name': info_in['name'] if info_in else 'System Default'
            }
            self._cache_stream_config(config)
        
        # Больше НЕ мониторим смену входного устройства во время записи
        # Выбираем default один раз при старте записи
        
    def stop_recording_and_recognize(self):
        """Останавливает запись и распознает речь"""
        if not self.is_recording:
            return None
            
        self.is_recording = False
        
        # Мониторинг входного устройства не запускаем — ничего останавливать не нужно
        
        # Останавливаем поток записи
        if self.stream:
            try:
                with self.stream_lock:
                    if self.stream:
                        self.stream.stop()
                        self.stream.close()
                        self.stream = None
                console.print("[blue]🔇 Аудиопоток остановлен и закрыт[/blue]")
            except Exception as e:
                console.print(f"[yellow]⚠️ Ошибка при остановке аудиопотока: {e}[/yellow]")
            
        console.print("[bold blue]🔍 Распознавание речи...[/bold blue]")

        # После записи ничего не переключаем вручную — выводом управляет событийный listener
        
        if not self.audio_chunks:
            console.print("[yellow]⚠️ Не записано аудио[/yellow]")
            return None
            
        try:
            # Объединяем все чанки в один аудиофрагмент
            audio_data = np.concatenate(self.audio_chunks)
            
            # Проверяем длительность аудио
            duration = len(audio_data) / self.sample_rate
            console.print(f"[blue]📊 Длительность аудио: {duration:.2f} секунд[/blue]")
            
            if duration < 0.5:  # Минимум 0.5 секунды
                console.print("[yellow]⚠️ Аудио слишком короткое для распознавания[/yellow]")
                return None
            
            # Конвертируем в формат для SpeechRecognition (int16 -> bytes)
            audio_data = audio_data.astype(np.int16)
            audio_bytes = audio_data.tobytes()
            
            # ДОПОЛНИТЕЛЬНАЯ ДИАГНОСТИКА АУДИО
            console.print(f"[blue]🔍 Размер аудио данных: {len(audio_data)} сэмплов[/blue]")
            console.print(f"[blue]🔍 Диапазон значений: {audio_data.min():.4f} до {audio_data.max():.4f}[/blue]")
            console.print(f"[blue]🔍 Среднее значение: {np.mean(np.abs(audio_data)):.4f}[/blue]")
            console.print(f"[blue]🔍 Размер байтов: {len(audio_bytes)} байт[/blue]")
            
            # Создаем AudioData объект для распознавания
            # paInt16 = 16 бит = 2 байта на сэмпл
            audio = sr.AudioData(audio_bytes, self.sample_rate, 2)  # 2 bytes per sample
            
            # Пробуем разные языки для распознавания (английский в приоритете)
            languages = ['en-US', 'en-GB', 'ru-RU']
            
            for lang in languages:
                try:
                    console.print(f"[blue]🌐 Пробую язык: {lang}[/blue]")
                    text = self.recognizer.recognize_google(audio, language=lang)
                    console.print(f"[bold magenta]✅ Распознано ({lang}): {text}[/bold magenta]")
                    return text
                except sr.UnknownValueError:
                    console.print(f"[yellow]⚠️ Не удалось распознать речь на {lang}[/yellow]")
                    continue
                except sr.RequestError as e:
                    console.print(f"[red]❌ Ошибка сервиса распознавания на {lang}: {e}[/red]")
                    continue
            
            # Альтернативный метод (тот же буфер как raw)
            console.print("[blue]🔄 Пробую альтернативный метод распознавания...[/blue]")
            try:
                raw_audio = b''.join([chunk.astype(np.int16).tobytes() for chunk in self.audio_chunks])
                alternative_audio = sr.AudioData(raw_audio, self.sample_rate, 2)
                for lang in languages:
                    try:
                        console.print(f"[blue]🔄 Альтернативный метод, язык: {lang}[/blue]")
                        text = self.recognizer.recognize_google(alternative_audio, language=lang)
                        console.print(f"[bold magenta]✅ Распознано альтернативным методом ({lang}): {text}[/bold magenta]")
                        return text
                    except sr.UnknownValueError:
                        continue
                    except sr.RequestError:
                        continue
            except Exception as e:
                console.print(f"[yellow]⚠️ Альтернативный метод не сработал: {e}[/yellow]")
            
            # Если все языки не сработали
            console.print("[red]❌ Не удалось распознать речь ни на одном языке[/red]")
            return None
            
        except Exception as e:
            console.print(f"[red]❌ Ошибка распознавания: {e}[/red]")
            console.print(f"[red]Детали: {type(e).__name__}: {str(e)}[/red]")
            return None
    
    def force_stop_recording(self):
        """
        ПРИНУДИТЕЛЬНО останавливает запись БЕЗ распознавания.
        Используется для прерывания/отмены.
        """
        if not self.is_recording:
            return
            
        console.print("[bold red]🚨 ПРИНУДИТЕЛЬНАЯ остановка записи![/bold red]")
        self.is_recording = False
        
        # Останавливаем аудио поток
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
                console.print("[bold red]🚨 Аудиопоток ПРИНУДИТЕЛЬНО остановлен![/bold red]")
            except Exception as e:
                console.print(f"[yellow]⚠️ Ошибка при принудительной остановке: {e}[/yellow]")
            finally:
                self.stream = None
        
        # Очищаем буферы
        self.audio_chunks = []
        console.print("[bold green]✅ Запись ПРИНУДИТЕЛЬНО остановлена![/bold green]")
            
    def _record_audio(self):
        """Совместимость: больше не используется (поток не требуется с sounddevice)."""
        pass

    def _resolve_input_device(self):
        """Возвращает актуальный input: системный default или ближайший резерв (встроенный/любой доступный)."""
        try:
            # 1) sd.default.device[0]
            default = sd.default.device  # (input, output)
            if isinstance(default, (list, tuple)) and len(default) >= 1:
                default_in = default[0]
                if default_in is not None and default_in != -1:
                    try:
                        info = sd.query_devices(default_in)
                        if info.get('max_input_channels', 0) > 0:
                            console.print(f"[dim]🎙️ Default input (sd.default): {info.get('name')}[/dim]")
                            return default_in
                    except Exception:
                        pass

            # 2) CoreAudio hostapi default input
            try:
                hostapis = sd.query_hostapis()
                core_audio_idx = None
                for i, api in enumerate(hostapis):
                    if 'core' in (api.get('name','').lower()):
                        core_audio_idx = i
                        break
                if core_audio_idx is None:
                    core_audio_idx = 0
                api = sd.query_hostapis(core_audio_idx)
                d = api.get('default_input_device', -1)
                if d is not None and d != -1:
                    info = sd.query_devices(d)
                    if info.get('max_input_channels', 0) > 0:
                        console.print(f"[dim]🎙️ Default input (CoreAudio): {info.get('name')}[/dim]")
                        return d
            except Exception:
                pass

            # 3) Резерв: ищем встроенный микрофон/подходящее устройство
            try:
                devices = sd.query_devices()
                keywords_preferred = ['built-in', 'macbook', 'internal', 'встро', 'микрофон', 'microphone']
                # Сначала предпочитаем встроенные
                for idx, dev in enumerate(devices):
                    try:
                        if dev.get('max_input_channels', 0) > 0:
                            name_l = (dev.get('name','') or '').lower()
                            if any(k in name_l for k in keywords_preferred):
                                console.print(f"[yellow]⚠️ Default input недоступен — резерв: {dev.get('name')}[/yellow]")
                                return idx
                    except Exception:
                        continue
                # Затем любое доступное input-устройство
                for idx, dev in enumerate(devices):
                    try:
                        if dev.get('max_input_channels', 0) > 0:
                            console.print(f"[yellow]⚠️ Использую ближайший доступный input: {dev.get('name')}[/yellow]")
                            return idx
                    except Exception:
                        continue
            except Exception:
                pass

            console.print("[yellow]⚠️ Default input не определён — используем системное по умолчанию[/yellow]")
            return None
        except Exception as e:
            console.print(f"[yellow]⚠️ Не удалось определить input: {e} — используем None[/yellow]")
            return None

    def _monitor_input_device_changes(self):
        """Следит за изменениями входного устройства и безопасно переключает поток при смене."""
        try:
            while self.is_recording and not self.stop_device_monitor.is_set():
                try:
                    new_device = self._resolve_input_device()
                    if new_device != self.current_input_device:
                        old_device = self.current_input_device
                        if self._restart_input_stream(new_device):
                            self.current_input_device = new_device
                            console.print(f"[blue]🔄 Переключил входное устройство: {old_device} → {new_device}[/blue]")
                except Exception:
                    pass
                time.sleep(0.5)
        except Exception:
            pass

    def _restart_input_stream(self, new_device) -> bool:
        """Останавливает текущий InputStream и запускает новый с указанным устройством."""
        try:
            with self.stream_lock:
                # Закрываем старый поток, если есть
                if self.stream:
                    try:
                        self.stream.stop()
                        self.stream.close()
                    except Exception:
                        pass
                    self.stream = None

                # Создаем новый поток
                self.stream = sd.InputStream(
                    channels=self.channels,
                    samplerate=self.sample_rate,
                    dtype=self.dtype,
                    blocksize=self.chunk_size,
                    device=new_device,
                    callback=lambda indata, frames, time_info, status: self._input_callback_proxy(indata, frames, status),
                )
                self.stream.start()
            return True
        except Exception as e:
            console.print(f"[yellow]⚠️ Не удалось переключить входное устройство: {e}[/yellow]")
            return False

    def _input_callback_proxy(self, indata, frames, status):
        """Callback при перезапуске потока — добавляет чанки аналогично основному callback."""
        if status:
            console.print(f"[yellow]⚠️ Sounddevice status: {status}[/yellow]")
        if self.is_recording:
            if self.channels == 1:
                chunk = indata.copy().reshape(-1)
            else:
                chunk = indata.copy()[:, 0]
            self.audio_chunks.append(chunk.astype(np.int16))
            
    def cleanup(self):
        """Очищает ресурсы"""
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass

# Оставляем старую функцию для совместимости
def listen_for_command(lang: str = 'en-US') -> str | None:
    """
    Захватывает аудио с микрофона, распознает речь и возвращает текст.
    УСТАРЕВШАЯ ФУНКЦИЯ - используйте StreamRecognizer для push-to-talk.
    """
    r = sr.Recognizer()
    with sr.Microphone() as source:
        console.print("[bold cyan]Калибровка под окружающий шум...[/bold cyan]")
        r.adjust_for_ambient_noise(source, duration=1)
        
        console.print("[bold green]Слушаю...[/bold green]")
        try:
            audio = r.listen(source, timeout=5, phrase_time_limit=15)
        except sr.WaitTimeoutError:
            console.print("[yellow]Не было произнесено ни одной фразы.[/yellow]")
            return None

    try:
        console.print("[bold blue]Распознавание...[/bold blue]")
        text = r.recognize_google(audio, language=lang)
        console.print(f"[bold magenta]Вы сказали:[/bold magenta] {text}")
        return text
    except sr.UnknownValueError:
        console.print("[red]Не удалось распознать речь[/red]")
        return None
    except sr.RequestError as e:
        console.print(f"[red]Ошибка сервиса распознавания; {e}[/red]")
        return None
    except Exception as e:
        console.print(f"[red]Произошла непредвиденная ошибка: {e}[/red]")
        return None

if __name__ == '__main__':
    # Тест нового StreamRecognizer
    recognizer = StreamRecognizer()
    
    try:
        console.print("[bold green]🎤 Тест push-to-talk распознавания[/bold green]")
        console.print("[yellow]Нажмите и удерживайте пробел для записи...[/yellow]")
        
        # Симуляция нажатия пробела
        recognizer.start_recording()
        time.sleep(3)  # Записываем 3 секунды
        
        # Симуляция отпускания пробела
        text = recognizer.stop_recording_and_recognize()
        
        if text:
            console.print(f"[bold green]✅ Тест успешен! Распознано: {text}[/bold green]")
        else:
            console.print("[yellow]⚠️ Тест завершен без распознавания[/yellow]")
            
    finally:
        recognizer.cleanup()
