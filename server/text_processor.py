import asyncio
import logging
import os
import re
import base64
import io
from typing import AsyncGenerator, List
from PIL import Image

from google import genai
from google.genai import types

# --- Загрузка конфигурации ---
# Проверка наличия необходимых ключей API
if not os.environ.get("GEMINI_API_KEY"):
    raise ValueError("Не найден GEMINI_API_KEY. Проверьте config.env")

logger = logging.getLogger(__name__)

class TextProcessor:
    """
    Обрабатывает текстовые запросы с использованием Google Gemini Live API,
    который может использовать инструменты (например, Google Search)
    и поддерживает стриминг финального ответа.
    """
    
    def __init__(self):
        try:
            # Инициализация Gemini Live API клиента
            self.client = genai.Client(
                http_options={"api_version": "v1beta"},
                api_key=os.environ.get("GEMINI_API_KEY"),
            )
            
            # Настройка инструментов
            self.tools = [
                types.Tool(google_search=types.GoogleSearch()),
            ]
            
            # Конфигурация для Live API
            self.config = types.LiveConnectConfig(
                response_modalities=["TEXT"],
                media_resolution="MEDIA_RESOLUTION_MEDIUM",
                context_window_compression=types.ContextWindowCompressionConfig(
                    trigger_tokens=25600,
                    sliding_window=types.SlidingWindow(target_tokens=12800),
                ),
                tools=self.tools,
            )
            
            logger.info(f"✅ TextProcessor с Gemini Live API инициализирован успешно")
            logger.info(f"🔍 Google Search tool создан")
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации TextProcessor: {e}", exc_info=True)
            self.client = None

    async def generate_response_stream(self, prompt: str, screenshot_base64: str = None, **kwargs) -> AsyncGenerator[str, None]:
        """
        Генерирует ответ с помощью Gemini Live API и стримит результат.
        """
        if not self.client:
            logger.error("Gemini клиент не инициализирован.")
            yield "Извините, произошла ошибка конфигурации ассистента."
            return

        logger.info(f"Запускаю Gemini Live API для: '{prompt[:50]}...'")
        
        try:
            # Создаем сессию Live API
            async with self.client.aio.live.connect(
                model="models/gemini-2.0-flash-live-001", 
                config=self.config
            ) as session:
                

                
                # Отправляем изображение и текст по отдельности (cookbook-style)
                if screenshot_base64:
                    try:
                        # Отправляем JPEG изображение напрямую (без конвертации)
                        await session.send(input={
                            "mime_type": "image/jpeg",
                            "data": screenshot_base64  # JPEG base64-строка
                        })
                        
                        # Небольшая пауза для обработки изображения
                        await asyncio.sleep(0.1)
                        
                        logger.info("📸 JPEG изображение отправлено")
                    except Exception as img_error:
                        logger.warning(f"Не удалось обработать скриншот: {img_error}")
                
                # Отправляем текстовый запрос
                await session.send(input=prompt, end_of_turn=True)
                logger.info("📝 Текст отправлен")
                
                # Получаем ответ
                turn = session.receive()
                accumulated_text = ""
                
                async for response in turn:
                    if response.text:
                        # Накапливаем текст
                        accumulated_text += response.text
                        logger.info(f"📝 Получен текст: '{response.text[:100]}...'")
                        
                        # Проверяем, есть ли полные предложения
                        sentences = self._split_into_sentences(accumulated_text)
                        
                        # Если есть полные предложения, отправляем их
                        if len(sentences) > 1:
                            # Отправляем все предложения кроме последнего (оно может быть неполным)
                            for sentence in sentences[:-1]:
                                if sentence.strip():
                                    logger.info(f"📤 Отправляю предложение: '{sentence[:100]}...'")
                                    yield sentence.strip()
                            
                            # Оставляем последнее предложение для следующей итерации
                            accumulated_text = sentences[-1]
                        elif len(sentences) == 1 and self._is_complete_sentence(accumulated_text):
                            # Если получили одно полное предложение
                            sentence = sentences[0]
                            if sentence.strip():
                                logger.info(f"📤 Отправляю предложение: '{sentence[:100]}...'")
                                yield sentence.strip()
                            accumulated_text = ""
                
                # Отправляем оставшийся текст, если он есть
                if accumulated_text.strip():
                    logger.info(f"📤 Отправляю оставшийся текст: '{accumulated_text[:100]}...'")
                    yield accumulated_text.strip()
                
                logger.info("✅ Gemini Live API ответ получен и обработан")

        except Exception as e:
            logger.error(f"Ошибка в Gemini Live API: {e}", exc_info=True)
            yield "Извините, произошла внутренняя ошибка при обработке вашего запроса."
    
    def clean_text(self, text: str) -> str:
        """Простая очистка текста."""
        text = re.sub(r'\s+', ' ', text).strip()
        text = text.replace('*', '')
        return text

    def _split_into_sentences(self, text: str) -> List[str]:
        """Разбивает текст на предложения для стриминга"""
        if not text:
            return []
        
        # Очищаем текст
        text = self.clean_text(text)
        
        # Используем более точное разбиение на предложения
        import re
        
        # Паттерн для разбиения на предложения
        # Учитываем точки, восклицательные и вопросительные знаки
        # Исключаем точки в сокращениях (например, "т.д.", "и т.п.")
        sentence_pattern = r'(?<=[.!?])\s+(?=[A-ZА-Я])'
        
        # Разбиваем по паттерну
        sentences = re.split(sentence_pattern, text)
        
        # Фильтруем пустые предложения и добавляем знаки препинания
        result = []
        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if sentence:
                # Если это не последнее предложение, добавляем знак препинания
                if i < len(sentences) - 1:
                    # Ищем знак препинания в конце
                    if not any(sentence.endswith(ending) for ending in ['.', '!', '?']):
                        sentence += '.'
                result.append(sentence)
        
        return result
    
    def _is_complete_sentence(self, text: str) -> bool:
        """Проверяет, является ли предложение полным"""
        if not text:
            return False
        
        # Очищаем текст
        text = self.clean_text(text)
        
        # Проверяем, заканчивается ли текст знаком окончания предложения
        sentence_endings = ['.', '!', '?', '...', '?!', '!?']
        return any(text.endswith(ending) for ending in sentence_endings)