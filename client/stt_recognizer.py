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
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.channels = channels
        self.format = pyaudio.paInt16
        
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.is_recording = False
        self.audio_chunks = []
        self.recording_thread = None
        
        # Инициализируем распознаватель
        self.recognizer = sr.Recognizer()
        
    def start_recording(self):
        """Начинает запись аудио при нажатии пробела"""
        if self.is_recording:
            return
            
        self.is_recording = True
        self.audio_chunks = []
        
        # Открываем аудиопоток
        self.stream = self.audio.open(
            format=self.format,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.chunk_size
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
        
        # Ждем завершения потока записи
        if self.recording_thread:
            self.recording_thread.join()
            
        # Останавливаем поток
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
            
        console.print("[bold blue]🔍 Распознавание речи...[/bold blue]")
        
        if not self.audio_chunks:
            console.print("[yellow]⚠️ Не записано аудио[/yellow]")
            return None
            
        try:
            # Объединяем все чанки в один аудиофрагмент
            audio_data = np.concatenate(self.audio_chunks)
            
            # Конвертируем в формат для SpeechRecognition
            audio_bytes = audio_data.tobytes()
            
            # Создаем AudioData объект для распознавания
            audio = sr.AudioData(audio_bytes, self.sample_rate, 2)  # 2 bytes per sample
            
            # Распознаем речь
            text = self.recognizer.recognize_google(audio, language='ru-RU')
            console.print(f"[bold magenta]✅ Распознано: {text}[/bold magenta]")
            return text
            
        except sr.UnknownValueError:
            console.print("[red]❌ Не удалось распознать речь[/red]")
            return None
        except sr.RequestError as e:
            console.print(f"[red]❌ Ошибка сервиса распознавания: {e}[/red]")
            return None
        except Exception as e:
            console.print(f"[red]❌ Ошибка распознавания: {e}[/red]")
            return None
            
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
                    
        except Exception as e:
            console.print(f"[red]❌ Ошибка записи аудио: {e}[/red]")
            
    def cleanup(self):
        """Очищает ресурсы"""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.audio:
            self.audio.terminate()

# Оставляем старую функцию для совместимости
def listen_for_command(lang: str = 'ru-RU') -> str | None:
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
