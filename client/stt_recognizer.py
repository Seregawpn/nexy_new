import sounddevice as sd
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
        self.dtype = 'int16'
        
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

        # Открываем аудио поток через sounddevice
        self.stream = sd.InputStream(
            channels=self.channels,
            samplerate=self.sample_rate,
            dtype=self.dtype,
            blocksize=self.chunk_size,
            callback=_callback,
        )
        self.stream.start()

        console.print("[bold green]🎤 Запись началась...[/bold green]")
        
    def stop_recording_and_recognize(self):
        """Останавливает запись и распознает речь"""
        if not self.is_recording:
            return None
            
        self.is_recording = False
        
        # Останавливаем поток записи
        if self.stream:
            try:
                self.stream.stop()
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
