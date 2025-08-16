#!/usr/bin/env python3
"""
Демонстрационный скрипт для стриминговой системы
"""

import asyncio
import logging
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from config import Config
from text_processor import TextProcessor
from audio_generator import AudioGenerator
from audio_player import AudioPlayer

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
console = Console()

class StreamingDemo:
    """Демонстрация работы стриминговой системы"""
    
    def __init__(self):
        self.text_processor = TextProcessor()
        self.audio_generator = AudioGenerator()
        self.audio_player = AudioPlayer()
        
    async def demo_text_processing(self):
        """Демонстрирует обработку текста"""
        console.print(Panel(
            "[bold blue]Демонстрация обработки текста[/bold blue]\n"
            "Показываем как система обрабатывает и разбивает текст на предложения",
            title="Обработка текста"
        ))
        
        # Тестовые тексты
        test_texts = [
            "**Привет мир!** Это *первое* предложение. ### Заголовок",
            "Второе предложение с восклицательным знаком!",
            "Третье предложение с вопросом? И продолжение...",
            "Четвертое предложение без знаков препинания но очень длинное чтобы показать как система обрабатывает длинные фрагменты текста и разбивает их на логические части",
            "Пятое предложение. Шестое предложение! Седьмое предложение?"
        ]
        
        console.print(f"[cyan]Обрабатываем {len(test_texts)} текстовых фрагментов...[/cyan]")
        
        for i, text in enumerate(test_texts, 1):
            console.print(f"\n[blue]Фрагмент {i}:[/blue] {text}")
            
            # Очищаем текст
            clean_text = self.text_processor.clean_text(text)
            console.print(f"[green]Очищенный:[/green] {clean_text}")
            
            # Разбиваем на предложения
            sentences = self.text_processor.split_into_sentences(text)
            console.print(f"[yellow]Предложения ({len(sentences)}):[/yellow]")
            for j, sentence in enumerate(sentences, 1):
                console.print(f"  {j}. {sentence}")
        
        console.print("\n[green]✓ Демонстрация обработки текста завершена[/green]")
    
    async def demo_audio_generation(self):
        """Демонстрирует генерацию аудио"""
        console.print(Panel(
            "[bold blue]Демонстрация генерации аудио[/bold blue]\n"
            "Показываем как система генерирует аудио для текста",
            title="Генерация аудио"
        ))
        
        # Показываем доступные голоса
        voices = self.audio_generator.get_available_voices()
        table = Table(title="Доступные голоса")
        table.add_column("Ключ", style="cyan")
        table.add_column("Голос", style="green")
        for key, voice in voices.items():
            table.add_row(key, voice)
        console.print(table)
        
        # Информация о текущем голосе
        voice_info = await self.audio_generator.get_voice_info()
        console.print(f"\n[blue]Текущий голос:[/blue] {voice_info['voice']}")
        console.print(f"[blue]Статус:[/blue] {voice_info['status']}")
        
        # Тестовые предложения для озвучивания
        test_sentences = [
            "Привет! Это демонстрация системы.",
            "Система работает отлично!",
            "Генерация аудио происходит в реальном времени."
        ]
        
        console.print(f"\n[cyan]Генерируем аудио для {len(test_sentences)} предложений...[/cyan]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Генерация аудио...", total=len(test_sentences))
            
            for sentence in test_sentences:
                progress.update(task, description=f"Генерирую: {sentence[:30]}...")
                
                # Генерируем аудио
                audio_file = await self.audio_generator.generate_audio(sentence)
                
                if audio_file:
                    console.print(f"[green]✓ Сгенерировано:[/green] {sentence}")
                    console.print(f"[dim]Файл: {audio_file}[/dim]")
                else:
                    console.print(f"[red]✗ Ошибка генерации:[/red] {sentence}")
                
                progress.advance(task)
                await asyncio.sleep(0.5)  # Небольшая пауза для демонстрации
        
        console.print("\n[green]✓ Демонстрация генерации аудио завершена[/green]")
    
    async def demo_audio_playback(self):
        """Демонстрирует воспроизведение аудио"""
        console.print(Panel(
            "[bold blue]Демонстрация воспроизведения аудио[/bold blue]\n"
            "Показываем как система управляет очередью воспроизведения",
            title="Воспроизведение аудио"
        ))
        
        # Статус плеера
        status = self.audio_player.get_queue_status()
        console.print(f"[blue]Начальный статус плеера:[/blue] {status}")
        
        # Создаем тестовые аудио файлы (если их нет)
        test_sentences = [
            "Первое тестовое предложение для воспроизведения.",
            "Второе предложение в очереди.",
            "Третье и последнее предложение."
        ]
        
        console.print(f"\n[cyan]Создаем {len(test_sentences)} тестовых аудио файлов...[/cyan]")
        
        audio_files = []
        for sentence in test_sentences:
            audio_file = await self.audio_generator.generate_audio(sentence)
            if audio_file:
                audio_files.append(audio_file)
        
        if not audio_files:
            console.print("[red]Не удалось создать тестовые аудио файлы[/red]")
            return
        
        # Добавляем в очередь воспроизведения
        console.print(f"\n[cyan]Добавляем {len(audio_files)} файлов в очередь воспроизведения...[/cyan]")
        
        for audio_file in audio_files:
            await self.audio_player.add_to_queue(audio_file)
            console.print(f"[green]✓ Добавлен в очередь:[/green] {audio_file}")
        
        # Показываем статус очереди
        status = self.audio_player.get_queue_status()
        console.print(f"\n[blue]Статус после добавления:[/blue] {status}")
        
        # Статистика
        stats = self.audio_player.get_playback_stats()
        console.print(f"[blue]Статистика воспроизведения:[/blue] {stats}")
        
        console.print("\n[green]✓ Демонстрация воспроизведения аудио завершена[/green]")
        
        # Очищаем тестовые файлы
        await self.audio_generator.cleanup_temp_files(audio_files)
    
    async def demo_full_pipeline(self):
        """Демонстрирует полный пайплайн"""
        console.print(Panel(
            "[bold blue]Демонстрация полного пайплайна[/bold blue]\n"
            "Показываем как все компоненты работают вместе",
            title="Полный пайплайн"
        ))
        
        # Имитируем поток данных
        console.print("[cyan]Имитация потока данных через систему...[/cyan]")
        
        # Создаем очереди
        text_queue = asyncio.Queue()
        audio_queue = asyncio.Queue()
        
        # Тестовые данные
        test_chunks = [
            "Привет! Это демонстрация. ",
            "Система работает отлично! ",
            "Все компоненты синхронизированы."
        ]
        
        # Запускаем обработку
        console.print("\n[blue]1. Генерация текста (имитация)[/blue]")
        for chunk in test_chunks:
            await text_queue.put(chunk)
            console.print(f"[green]✓ Чанк добавлен:[/green] {chunk[:30]}...")
        
        # Сигнал завершения
        await text_queue.put(None)
        
        console.print("\n[blue]2. Обработка текста[/blue]")
        sentences = []
        while True:
            try:
                chunk = await asyncio.wait_for(text_queue.get(), timeout=0.1)
                if chunk is None:
                    break
                
                # Обрабатываем чанк
                sentences_from_chunk = await self.text_processor.process_text_chunks([chunk])
                for sentence in sentences_from_chunk:
                    if sentence:
                        sentences.append(sentence)
                        console.print(f"[green]✓ Предложение готово:[/green] {sentence}")
                        await audio_queue.put(sentence)
                
                text_queue.task_done()
                
            except asyncio.TimeoutError:
                break
        
        console.print(f"\n[blue]3. Генерация аудио для {len(sentences)} предложений[/blue]")
        audio_files = []
        for sentence in sentences:
            audio_file = await self.audio_generator.generate_audio(sentence)
            if audio_file:
                audio_files.append(audio_file)
                console.print(f"[green]✓ Аудио сгенерировано:[/green] {sentence[:30]}...")
        
        console.print(f"\n[blue]4. Добавление в очередь воспроизведения[/blue]")
        for audio_file in audio_files:
            await self.audio_player.add_to_queue(audio_file)
            console.print(f"[green]✓ Добавлено в очередь:[/green] {os.path.basename(audio_file)}")
        
        # Финальный статус
        status = self.audio_player.get_queue_status()
        console.print(f"\n[blue]Финальный статус:[/blue] {status}")
        
        console.print("\n[green]✓ Демонстрация полного пайплайна завершена[/green]")
        
        # Очистка
        await self.audio_generator.cleanup_temp_files(audio_files)
    
    async def run_demo(self):
        """Запускает все демонстрации"""
        console.print(Panel(
            "[bold green]Демонстрация стриминговой системы[/bold green]\n"
            "LangChain Gemini + Edge-TTS\n"
            "Показываем работу всех компонентов",
            title="Демонстрация системы"
        ))
        
        try:
            # Демонстрации
            await self.demo_text_processing()
            await asyncio.sleep(1)
            
            await self.demo_audio_generation()
            await asyncio.sleep(1)
            
            await self.demo_audio_playback()
            await asyncio.sleep(1)
            
            await self.demo_full_pipeline()
            
            console.print(Panel(
                "[bold green]Все демонстрации завершены успешно![/bold green]\n"
                "Система готова к работе.",
                title="Демонстрация завершена"
            ))
            
        except Exception as e:
            console.print(f"[red]Ошибка в демонстрации: {e}[/red]")
            raise

async def main():
    """Главная функция демонстрации"""
    try:
        # Проверяем конфигурацию
        Config.validate()
        
        # Создаем и запускаем демонстрацию
        demo = StreamingDemo()
        await demo.run_demo()
        
    except Exception as e:
        console.print(f"[red]Критическая ошибка: {e}[/red]")
        raise

if __name__ == "__main__":
    import os
    asyncio.run(main())
