import re
import asyncio
import logging
from typing import AsyncGenerator, List
from config import Config

logger = logging.getLogger(__name__)

class TextProcessor:
    """Обработчик текста с фильтрацией и детекцией предложений"""
    
    def __init__(self):
        self.buffer = ""
        self.sentence_endings = ['.', '!', '?', '...', '?!', '!?']
        
    def clean_text(self, text: str) -> str:
        """Очищает текст от форматирования и артефактов"""
        # Убираем markdown разметку
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # **текст** -> текст
        text = re.sub(r'\*([^*]+)\*', r'\1', text)      # *текст* -> текст
        text = re.sub(r'###\s*', '', text)              # ### Заголовок -> Заголовок
        
        # Убираем лишние пробелы и переносы строк
        text = re.sub(r'\s+', ' ', text)                # Множественные пробелы -> один
        text = re.sub(r'\n\s*\n', '\n', text)          # Пустые строки -> одна
        text = text.strip()
        
        return text
    
    def is_sentence_complete(self, text: str) -> bool:
        """Проверяет, завершено ли предложение"""
        if not text:
            return False
            
        # Проверяем на знаки окончания предложения
        for ending in self.sentence_endings:
            if text.rstrip().endswith(ending):
                return True
        
        # Проверяем на максимальную длину
        if len(text) >= Config.MAX_SENTENCE_LENGTH:
            return True
            
        return False
    
    def split_into_sentences(self, text: str) -> List[str]:
        """Разбивает текст на предложения"""
        # Сначала очищаем текст
        clean_text = self.clean_text(text)
        
        # Простое разбиение по знакам препинания
        sentences = []
        current = ""
        
        for char in clean_text:
            current += char
            
            if char in ['.', '!', '?']:
                # Проверяем на многоточие
                if char == '.' and len(current) >= 3:
                    if current[-3:] == '...':
                        sentences.append(current.strip())
                        current = ""
                        continue
                
                sentences.append(current.strip())
                current = ""
        
        # Добавляем оставшийся текст если он есть
        if current.strip():
            sentences.append(current.strip())
        
        # Фильтруем пустые предложения
        return [s for s in sentences if s.strip()]
    
    async def process_stream(self, text_stream: AsyncGenerator[str, None]) -> AsyncGenerator[str, None]:
        """Обрабатывает поток текста и возвращает готовые предложения"""
        self.buffer = ""
        
        async for chunk in text_stream:
            if not chunk:
                continue
                
            # Добавляем чанк в буфер
            self.buffer += chunk
            
            # Проверяем, есть ли готовые предложения
            while self.buffer:
                # Ищем конец предложения
                sentence_end = -1
                for ending in self.sentence_endings:
                    pos = self.buffer.find(ending)
                    if pos != -1:
                        sentence_end = pos + len(ending)
                        break
                
                # Если нашли конец предложения или превысили длину
                if sentence_end != -1 or len(self.buffer) >= Config.MAX_SENTENCE_LENGTH:
                    if sentence_end == -1:
                        sentence_end = Config.MAX_SENTENCE_LENGTH
                    
                    # Извлекаем готовое предложение
                    sentence = self.buffer[:sentence_end].strip()
                    self.buffer = self.buffer[sentence_end:].strip()
                    
                    if sentence:
                        # Очищаем предложение
                        clean_sentence = self.clean_text(sentence)
                        if clean_sentence:
                            logger.info(f"Готово предложение: {clean_sentence[:50]}...")
                            yield clean_sentence
                else:
                    # Предложение не завершено, ждем дальше
                    break
        
        # Обрабатываем оставшийся текст в буфере
        if self.buffer.strip():
            clean_remaining = self.clean_text(self.buffer.strip())
            if clean_remaining:
                logger.info(f"Финальное предложение: {clean_remaining[:50]}...")
                yield clean_remaining
    
    async def process_text_chunks(self, chunks: List[str]) -> List[str]:
        """Обрабатывает список текстовых чанков и возвращает готовые предложения"""
        sentences = []
        
        for chunk in chunks:
            if not chunk:
                continue
            
            self.buffer += chunk
            
            # Ищем полные предложения в буфере
            while True:
                sentence_end_pos = -1
                
                # Находим ближайший конец предложения
                for ending in self.sentence_endings:
                    pos = self.buffer.find(ending)
                    if pos != -1:
                        if sentence_end_pos == -1 or pos < sentence_end_pos:
                            sentence_end_pos = pos + len(ending)
                
                if sentence_end_pos != -1:
                    sentence = self.buffer[:sentence_end_pos].strip()
                    self.buffer = self.buffer[sentence_end_pos:]
                    if sentence:
                        clean_sentence = self.clean_text(sentence)
                        if clean_sentence:
                            sentences.append(clean_sentence)
                else:
                    # Нет полных предложений, выходим из цикла
                    break
        
        return sentences

    def flush_buffer(self) -> List[str]:
        """
        Обрабатывает и возвращает любой оставшийся в буфере текст, затем очищает буфер.
        """
        sentences = []
        if self.buffer.strip():
            clean_text = self.clean_text(self.buffer)
            # Можно добавить более сложную логику разбиения, если нужно
            if clean_text:
                sentences.append(clean_text)
        
        self.buffer = ""
        return sentences
