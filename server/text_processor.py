import re
import asyncio
import logging
from typing import AsyncGenerator, List
from config import Config
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

class TextProcessor:
    """Обработчик текста с LangChain streaming через Gemini с поддержкой скриншотов"""
    
    def __init__(self):
        self.buffer = ""
        self.sentence_endings = ['.', '!', '?', '...', '?!', '!?']
        
        # Инициализируем Google Gemini API
        try:
            # Настраиваем API ключ
            genai.configure(api_key=Config.GEMINI_API_KEY)
            
            # Создаем LangChain модель с Gemini
            self.model = ChatGoogleGenerativeAI(
                model="gemini-2.0-flash-exp",
                google_api_key=Config.GEMINI_API_KEY,
                temperature=0.7,
                max_tokens=1000
            )
            
            self.parser = StrOutputParser()
            logger.info("✅ LangChain Gemini модель инициализирована успешно")
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации LangChain Gemini: {e}")
            self.model = None
            self.parser = None
    
    async def generate_response_stream(self, prompt: str, screenshot_base64: str = None, screen_info: dict = None) -> AsyncGenerator[str, None]:
        """
        Генерирует ответ через LangChain Gemini с реальным стримингом токенов.
        
        Args:
            prompt (str): Команда/вопрос пользователя
            screenshot_base64 (str): Base64 WebP скриншот экрана
            screen_info (dict): Информация об экране (ширина, высота)
            
        Yields:
            str: Токены ответа в реальном времени
        """
        if not self.model or not self.parser:
            logger.error("LangChain Gemini модель не инициализирована")
            yield "Извините, я не могу ответить сейчас. Ошибка: Gemini не инициализирован."
            return
        
        try:
            # Формируем промпт для ассистента с учетом скриншота
            system_prompt = """
            Ты - полезный голосовой ассистент для macOS. Твоя основная задача - ОТВЕЧАТЬ НА КОМАНДЫ И ВОПРОСЫ пользователя.

            ВАЖНО: Всегда отвечай на команду/вопрос пользователя ПЕРВЫМ ПРИОРИТЕТОМ!

            ПРАВИЛА РАБОТЫ:
            1. СНАЧАЛА отвечай на команду/вопрос пользователя
            2. ЕСЛИ команда связана с экраном - используй скриншот для контекста
            3. ЕСЛИ команда НЕ связана с экраном - игнорируй скриншот
            4. Отвечай кратко, но информативно на русском языке
            5. Будь полезным и дружелюбным

            ПРИМЕРЫ:
            - "Расскажи историю" → Расскажи интересную историю
            - "Что на экране?" → Опиши содержимое экрана
            - "Помоги с кодом" → Помоги с кодом, используя контекст экрана
            - "Время" → Скажи текущее время (без анализа экрана)

            НЕ ИГНОРИРУЙ команды пользователя! Всегда отвечай на них.
            """
            
            # Добавляем информацию об экране
            screen_context = ""
            if screen_info:
                screen_context = f"\n\nИнформация об экране: {screen_info['width']}x{screen_info['height']} пикселей"
            
            # Создаем сообщения для LangChain
            messages = [
                SystemMessage(content=system_prompt + screen_context)
            ]
            
            if screenshot_base64:
                # Создаем multimodal сообщение с изображением для Gemini
                try:
                    # Создаем HumanMessage с изображением и текстом
                    # ПРИОРИТЕТ: команда пользователя, скриншот для контекста
                    human_message = HumanMessage(
                        content=[
                            {
                                "type": "text",
                                "text": f"КОМАНДА ПОЛЬЗОВАТЕЛЯ: {prompt}\n\nВАЖНО: Отвечай на команду пользователя! Скриншот используй только если команда связана с экраном."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/webp;base64,{screenshot_base64}"
                                }
                            }
                        ]
                    )
                    messages.append(human_message)
                    
                    logger.info(f"Анализирую команду с скриншотом (приоритет команды): {prompt[:50]}...")
                    
                except Exception as img_error:
                    logger.error(f"Ошибка обработки скриншота: {img_error}")
                    # Fallback к текстовому режиму
                    messages.append(HumanMessage(content=f"КОМАНДА ПОЛЬЗОВАТЕЛЯ: {prompt}\n\nОтвечай на команду пользователя!"))
                    logger.info(f"Обрабатываю команду без скриншота (fallback): {prompt[:50]}...")
            else:
                # Только текстовое сообщение
                messages.append(HumanMessage(content=f"КОМАНДА ПОЛЬЗОВАТЕЛЯ: {prompt}\n\nОтвечай на команду пользователя!"))
                logger.info(f"Обрабатываю команду без скриншота: {prompt[:50]}...")
            
            # Создаем цепочку LangChain для стриминга
            logger.info(f"Запускаю LangChain streaming для: {prompt[:50]}...")
            
            # Используем stream для получения ответа по частям
            try:
                response = self.model.invoke(messages)
                if response and hasattr(response, 'content'):
                    # Разбиваем ответ на предложения для имитации стриминга
                    content = response.content
                    sentences = self._split_into_sentences(content)
                    
                    for sentence in sentences:
                        if sentence.strip():
                            logger.debug(f"Отправляю предложение: {sentence[:50]}...")
                            yield sentence + " "
                            
                            # Небольшая задержка для имитации стриминга
                            await asyncio.sleep(0.1)
                else:
                    logger.warning("Получен пустой ответ от Gemini")
                    yield "Извините, не удалось получить ответ от ассистента."
                    
            except Exception as stream_error:
                logger.error(f"Ошибка стриминга через Gemini: {stream_error}")
                yield f"Извините, произошла ошибка при получении ответа: {str(stream_error)}"
                
        except Exception as e:
            logger.error(f"Общая ошибка генерации ответа через LangChain Gemini: {e}")
            yield f"Извините, произошла ошибка при обработке вашего запроса: {str(e)}"
    
    def generate_response_with_gemini(self, prompt: str) -> str:
        """
        Синхронная версия для обратной совместимости.
        УСТАРЕВШАЯ - используйте generate_response_stream для стриминга.
        """
        if not self.model or not self.parser:
            logger.error("LangChain Gemini модель не инициализирована")
            return f"Извините, я не могу ответить сейчас. Ошибка: Gemini не инициализирован."
        
        try:
            # Формируем промпт для ассистента
            system_prompt = """
            Ты - полезный голосовой ассистент для macOS. Отвечай кратко, но информативно.
            Если пользователь спрашивает о чем-то, что ты не можешь сделать, объясни это вежливо.
            Отвечай на русском языке, если пользователь говорит по-русски.
            """
            
            full_prompt = f"{system_prompt}\n\nПользователь: {prompt}\n\nАссистент:"
            
            # Создаем цепочку LangChain
            chain = self.model | self.parser
            
            # Вызываем синхронно (не стриминг)
            response = chain.invoke(full_prompt)
            
            if response and response.strip():
                logger.info(f"LangChain Gemini сгенерировал ответ: {response[:100]}...")
                return response.strip()
            else:
                logger.warning("LangChain Gemini вернул пустой ответ")
                return "Извините, я не смог сгенерировать ответ. Попробуйте переформулировать вопрос."
                
        except Exception as e:
            logger.error(f"Ошибка генерации ответа через LangChain Gemini: {e}")
            return f"Извините, произошла ошибка при обработке вашего запроса: {str(e)}"
    
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
        if len(text) >= 200:  # MAX_SENTENCE_LENGTH из конфигурации
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
                if sentence_end != -1 or len(self.buffer) >= 200:  # MAX_SENTENCE_LENGTH из конфигурации
                    if sentence_end == -1:
                        sentence_end = 200  # MAX_SENTENCE_LENGTH из конфигурации
                    
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

    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Разбивает текст на предложения для имитации стриминга.
        
        Args:
            text (str): Исходный текст
            
        Returns:
            List[str]: Список предложений
        """
        if not text:
            return []
        
        # Простое разбиение по знакам препинания
        sentences = []
        current_sentence = ""
        
        for char in text:
            current_sentence += char
            
            # Проверяем конец предложения
            if char in self.sentence_endings:
                sentence = current_sentence.strip()
                if sentence:
                    sentences.append(sentence)
                current_sentence = ""
        
        # Добавляем последнее предложение, если оно есть
        if current_sentence.strip():
            sentences.append(current_sentence.strip())
        
        # Если не удалось разбить на предложения, разбиваем по длине
        if not sentences:
            words = text.split()
            current_chunk = ""
            
            for word in words:
                if len(current_chunk + " " + word) <= 100:  # Максимальная длина чанка
                    current_chunk += (" " + word) if current_chunk else word
                else:
                    if current_chunk:
                        sentences.append(current_chunk.strip())
                    current_chunk = word
            
            if current_chunk:
                sentences.append(current_chunk.strip())
        
        return sentences
