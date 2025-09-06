#!/usr/bin/env python3
"""
Text utilities for server components
Common functions for text processing across the server
"""

import re
from typing import List


def clean_text(text: str) -> str:
    """
    Cleans text by removing extra whitespace and normalizing
    ORIGINAL SPECIFIC CONDITIONS PRESERVED
    """
    if not text:
        return ""
    
    # Убираем лишние пробелы и переносы строк (ORIGINAL CONDITION)
    text = ' '.join(text.split())
    
    # Убираем специальные символы, которые могут мешать (ORIGINAL CONDITION)
    text = re.sub(r'[^\w\s\.\,\!\?\-\:\;\(\)\[\]\{\}\"\']', '', text)
    
    return text.strip()


def split_into_sentences(text: str) -> List[str]:
    """
    Splits text into sentences for streaming - ORIGINAL IMPROVED VERSION
    
    This is the unified function used by both TextProcessor and AudioGenerator
    ORIGINAL SPECIFIC CONDITIONS PRESERVED
    """
    if not text:
        return []
    
    # Очищаем текст (ORIGINAL CONDITION)
    text = clean_text(text)
    
    # 🎯 УЛУЧШЕННЫЙ ПАТТЕРН для разбиения на предложения (ORIGINAL CONDITIONS)
    # Учитываем больше случаев:
    # - Точки (.)
    # - Восклицательные знаки (!)
    # - Вопросительные знаки (?)
    # - Многоточие (...)
    # - Комбинации (!?, ?!)
    # - Предложения без пробелов после знаков препинания
    # - Предложения, начинающиеся с цифр
    
    # УЛУЧШЕННЫЙ паттерн для разбиения на предложения (ORIGINAL PATTERN)
    # 1. Основной паттерн: знак препинания + пробел + заглавная буква/цифра
    # 2. Дополнительный паттерн: знак препинания + конец строки
    # 3. Паттерн без пробела: знак препинания + заглавная буква/цифра
    sentence_pattern = r'(?<=[.!?])\s*(?=[A-ZА-Я0-9])|(?<=[.!?])\s*$'
    
    # Разбиваем по паттерну (ORIGINAL LOGIC)
    sentences = re.split(sentence_pattern, text)
    
    # Фильтруем и обрабатываем предложения (ORIGINAL LOGIC)
    result = []
    for i, sentence in enumerate(sentences):
        sentence = sentence.strip()
        if sentence:
            # Если это не последнее предложение, проверяем знак препинания (ORIGINAL CONDITION)
            if i < len(sentences) - 1:
                # Ищем знак препинания в конце (ORIGINAL CONDITION)
                if not any(sentence.endswith(ending) for ending in ['.', '!', '?', '...', '?!', '!?']):
                    sentence += '.'
            result.append(sentence)
    
    return result


def is_sentence_complete(text: str) -> bool:
    """
    Checks if a sentence is complete
    ORIGINAL SPECIFIC CONDITIONS PRESERVED
    """
    if not text or not text.strip():
        return False
    
    text = text.strip()
    # Проверяем, заканчивается ли текст знаком окончания предложения (ORIGINAL CONDITION)
    sentence_endings = ['.', '!', '?', '...', '?!', '!?']
    return any(text.endswith(ending) for ending in sentence_endings)
