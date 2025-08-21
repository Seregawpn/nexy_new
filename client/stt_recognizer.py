import pyaudio
import numpy as np
import speech_recognition as sr
import threading
import time
from rich.console import Console

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
        self.format = pyaudio.paInt16
        
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.is_recording = False
        self.audio_chunks = []
        self.recording_thread = None
        
        # Инициализируем распознаватель с оптимизированными параметрами
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 100  # Снижаем порог энергии для лучшего распознавания
        self.recognizer.dynamic_energy_threshold = True  # Динамический порог
        self.recognizer.pause_threshold = 0.5  # Уменьшаем порог паузы
        self.recognizer.phrase_threshold = 0.3  # Порог фразы
        self.recognizer.non_speaking_duration = 0.3  # Длительность не-речи
        
    def start_recording(self):
        """Начинает запись аудио при нажатии пробела"""
        # КРИТИЧНО: если уже записываем - сначала останавливаем предыдущую запись
        if self.is_recording:
            console.print("[yellow]⚠️ Запись уже идет - сначала останавливаю предыдущую...[/yellow]")
            self.stop_recording_and_recognize()
            # Небольшая задержка для стабилизации
            time.sleep(0.05)
            
        self.is_recording = True
        self.audio_chunks = []
        
        # Открываем аудиопоток с лучшими параметрами
        self.stream = self.audio.open(
            format=self.format,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.chunk_size,
            input_device_index=None  # Используем устройство по умолчанию
        )
        
        console.print("[bold green]🎤 Запись началась...[/bold green]")
        
        # Запускаем запись в отдельном потоке
        self.recording_thread = threading.Thread(target=self._record_audio)
        self.recording_thread.daemon = True
        self.recording_thread.start()
        
    def stop_recording_and_recognize(self):
        """Останавливает запись и распознает речь"""
        if not self.is_recording:
            return None
            
        self.is_recording = False
        
        # КРИТИЧНО: принудительно останавливаем поток записи
        if self.recording_thread and self.recording_thread.is_alive():
            # Даем время потоку записи завершиться
            self.recording_thread.join(timeout=0.5)  # Уменьшаем таймаут до 500ms
            
            # Если поток не завершился - принудительно прерываем
            if self.recording_thread.is_alive():
                console.print("[yellow]⚠️ Поток записи не завершился - принудительно прерываю...[/yellow]")
                # В Python нет прямого способа убить поток, но можно сбросить флаг
                self.is_recording = False
            
        # КРИТИЧНО: принудительно останавливаем аудиопоток
        if self.stream:
            try:
                if self.stream.is_active():
                    self.stream.stop_stream()
                self.stream.close()
                console.print("[blue]🔇 Аудиопоток остановлен и закрыт[/blue]")
            except Exception as e:
                console.print(f"[yellow]⚠️ Ошибка при остановке аудиопотока: {e}[/yellow]")
            finally:
                self.stream = None
            
        console.print("[bold blue]🔍 Распознавание речи...[/bold blue]")
        
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
            
            # Нормализуем аудио для лучшего качества
            audio_data = audio_data.astype(np.float32) / 32768.0  # Нормализация к [-1, 1]
            
            # Конвертируем в формат для SpeechRecognition
            audio_bytes = (audio_data * 32767).astype(np.int16).tobytes()
            
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
            
            # АЛЬТЕРНАТИВНЫЙ МЕТОД - прямой PyAudio
            console.print("[blue]🔄 Пробую альтернативный метод распознавания...[/blue]")
            try:
                # Создаем аудио данные напрямую из PyAudio
                raw_audio = b''.join([chunk.tobytes() for chunk in self.audio_chunks])
                alternative_audio = sr.AudioData(raw_audio, self.sample_rate, 2)
                
                # Пробуем распознать
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
        
        # КРИТИЧНО: принудительно останавливаем поток записи
        if self.recording_thread and self.recording_thread.is_alive():
            self.recording_thread.join(timeout=0.2)  # Быстрый таймаут для прерывания
            
        # КРИТИЧНО: принудительно останавливаем аудиопоток
        if self.stream:
            try:
                if self.stream.is_active():
                    self.stream.stop_stream()
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
        """Записывает аудио в отдельном потоке"""
        try:
            while self.is_recording:
                if self.stream and self.stream.is_active():
                    # Читаем чанк аудио
                    data = self.stream.read(self.chunk_size, exception_on_overflow=False)
                    
                    # Конвертируем в numpy array
                    audio_chunk = np.frombuffer(data, dtype=np.int16)
                    self.audio_chunks.append(audio_chunk)
                    
                    # Небольшая задержка для стабильности
                    time.sleep(0.01)
                    
        except Exception as e:
            console.print(f"[red]❌ Ошибка записи аудио: {e}[/red]")
            console.print(f"[red]Детали: {type(e).__name__}: {str(e)}[/red]")
            
    def cleanup(self):
        """Очищает ресурсы"""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.audio:
            self.audio.terminate()

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
