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
        # Инициализируем компоненты памяти
        self.memory_analyzer = None
        self.db_manager = None
        
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
            
            # Инициализируем MemoryAnalyzer
            gemini_api_key = os.environ.get("GEMINI_API_KEY")
            if gemini_api_key:
                try:
                    from memory_analyzer import MemoryAnalyzer
                    self.memory_analyzer = MemoryAnalyzer(gemini_api_key)
                    logger.info(f"✅ MemoryAnalyzer инициализирован")
                except Exception as e:
                    logger.warning(f"⚠️ MemoryAnalyzer не инициализирован: {e}")
            
            logger.info(f"✅ TextProcessor с Gemini Live API инициализирован успешно")
            logger.info(f"🔍 Google Search tool создан")
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации TextProcessor: {e}", exc_info=True)
            self.client = None

    def set_database_manager(self, db_manager):
        """
        Устанавливает DatabaseManager для работы с памятью.
        
        Args:
            db_manager: Экземпляр DatabaseManager
        """
        self.db_manager = db_manager
        logger.info("✅ DatabaseManager установлен в TextProcessor")
    
    async def generate_response_stream(self, prompt: str, hardware_id: str = None, screenshot_base64: str = None, **kwargs) -> AsyncGenerator[str, None]:
        """
        Генерирует ответ с помощью Gemini Live API и стримит результат.
        """
        if not self.client:
            logger.error("Gemini клиент не инициализирован.")
            yield "Извините, произошла ошибка конфигурации ассистента."
            return

        logger.info(f"Запускаю Gemini Live API для: '{prompt[:50]}...'")
        
        # Получаем память пользователя (если доступна)
        memory_context = ""
        if hardware_id and self.db_manager:
            try:
                # Таймаут 2 секунды на получение памяти
                async with asyncio.timeout(2.0):
                    memory_data = await asyncio.to_thread(
                        self.db_manager.get_user_memory, 
                        hardware_id
                    )
                    if memory_data.get('short') or memory_data.get('long'):
                        memory_context = f"""
                        
                        Контекст из памяти:
                        Краткосрочная: {memory_data.get('short', 'Нет')}
                        Долгосрочная: {memory_data.get('long', 'Нет')}
                        """
                        logger.info(f"🧠 Получена память для {hardware_id}: краткосрочная ({len(memory_data.get('short', ''))} символов), долгосрочная ({len(memory_data.get('long', ''))} символов)")
                    else:
                        logger.info(f"🧠 Память для {hardware_id} пуста")
            except asyncio.TimeoutError:
                logger.warning(f"⏰ Таймаут получения памяти для {hardware_id}")
            except Exception as e:
                logger.warning(f"⚠️ Ошибка получения памяти: {e}")
        
        try:
            logger.info(f"🔌 Использую обычный Gemini API...")
            # Используем обычный Gemini API вместо Live API
            model = self.client.GenerativeModel('gemini-2.0-flash-exp')
            
            # Формируем системную инструкцию с учетом памяти
            base_system_instruction = (
                    "You are a friendly, caring AI assistant for blind and visually impaired users. "
                    "Be warm, conversational, and supportive while maintaining the highest standards of accuracy and safety.\n\n"
                    " When you give the answer, you need to give just answer short and clear and not too long And just important.\n\n"

                    "🎯 REQUEST ANALYSIS - READ THIS FIRST:\n"
                    "   You MUST analyze the user's request and respond accordingly and understand, which kind of question is it or which kind of request is it:\n\n"
                    
                    "1️⃣ Search: related to search information online, for example, news, sport news, or ticket important information, which you can get just online:\n this is example of questions requests"                    "   - 'What's the latest news?' → Search for current news\n"
                    "   - 'What happened today?' → Search for today's events\n"
                    "   - 'Weather today?' → Search for current weather\n"
                    "   - 'Current stock prices?' → Search for market data\n"
                    "   - ANY question about recent events, current time, or live information\n"
                    
                    
                    "2️⃣ SCREEN ANALYSIS → this kind of request which user asked about to tell what do you see on the screen or you need to qualify him? What is on the screen because he cannot see and you need to help him with:\n these are kind of requests"
                    "   - 'What do I see on screen?' → Analyze screenshot\n"
                    "   - 'What's on the right side?' → Analyze screenshot\n"
                    "   - 'Describe my desktop' → Analyze screenshot\n"
                    "   - 'What am I working on?' → Analyze screenshot\n"
                    
                    "3️⃣ conversation → you need to ask some question just to talk as a question or other questions which you don't need to use screenshot or you don't need to use search for example, if he asked to help with something to answer any question (NOT for recent events): these are kind of requests\n"
                    "   - 'How do computers work?' → Use your knowledge\n"
                    "   - 'What is gravity?' → Use your knowledge\n"
                    "   - 'How to cook pasta?' → Use your knowledge\n"
                    " calculation"
                    
                    
                    "🚨 CRITICAL RULES:\n"
                    "   - never mix them for example if user ask one category or request you need to answer exactly what you want. You cannot meet them."
                    
                    "💬 PERSONALITY:\n"
                    "   - Be warm, friendly, and supportive\n"
                    "   - Use encouraging language\n"
                    "   - Show genuine care and empathy\n\n"
                    
                    "🧠 MEMORY (OPTIONAL):\n"
                    "   - you need to use memory when it related to the topic to the request and if user ask you about some information which was talking about so use memory when it's really important to use and sense of topic"
                    
                    "⚠️ SAFETY:\n"
                    "   - Warn about suspicious content or dangerous websites or leads or emails messages whatever if something can be dangerous you need to tell about this that user I want to go one click because he's a Brian and he cannot see so you need to take care about it\n"

                )
                
                if memory_context:
                    system_instruction = base_system_instruction + memory_context
                    logger.info(f"🧠 Системная инструкция дополнена контекстом памяти")
                    logger.info(f"🧠 Контекст памяти: {memory_context[:200]}...")
                else:
                    system_instruction = base_system_instruction
                    logger.info(f"🧠 Системная инструкция без контекста памяти")
                
                # --- УМНАЯ ОБРАБОТКА СКРИНШОТА ---
                # Анализируем запрос и решаем, нужен ли скриншот
                content = [system_instruction, prompt]
                
                # Определяем, нужен ли скриншот для данного запроса
                needs_screenshot = self._should_analyze_screenshot(prompt)
                
                if screenshot_base64 and needs_screenshot:
                    try:
                        # Декодируем изображение
                        image_bytes = base64.b64decode(screenshot_base64)
                        
                        # Используем PIL для проверки и получения формата
                        img = Image.open(io.BytesIO(image_bytes))
                        
                        # Добавляем изображение в контент
                        content.append(img)
                        
                        logger.info(f"📸 Скриншот АНАЛИЗИРУЕТСЯ ({img.format}, {img.size}) - запрос требует анализа экрана")
                        
                    except Exception as img_error:
                        logger.warning(f"Не удалось обработать скриншот: {img_error}")
                elif screenshot_base64:
                    logger.info(f"📸 Скриншот ИГНОРИРУЕТСЯ - запрос не требует анализа экрана")
                else:
                    logger.info(f"📝 Скриншот не предоставлен")

                # Отправляем запрос (с изображением или без)
                logger.info(f"📤 Отправляю запрос в Gemini API...")
                
                try:
                    # Используем обычный Gemini API
                    response = model.generate_content(content)
                    logger.info(f"✅ Ответ получен от Gemini API!")
                    
                    if response.text:
                        accumulated_text = response.text
                        logger.info(f"📝 Получен текст: '{accumulated_text[:100]}...'")
                        
                        # Разбиваем на предложения и отправляем
                        sentences = self._split_into_sentences(accumulated_text)
                        
                        for sentence in sentences:
                            if sentence.strip():
                                logger.info(f"📤 Отправляю предложение: '{sentence[:100]}...'")
                                yield sentence.strip()
                        
                    else:
                        logger.warning("⚠️ Gemini API вернул пустой ответ")
                        yield "Извините, не удалось получить ответ от ассистента."
                        
                except Exception as api_error:
                    logger.error(f"❌ Ошибка Gemini API: {api_error}")
                    yield "Извините, произошла ошибка при получении ответа от ассистента."
                
                logger.info("✅ Gemini API ответ получен и обработан")
                
                # ФОНОВОЕ обновление памяти (НЕ БЛОКИРУЕТ) - только если есть ответ
                if 'response' in locals() and response.text and hardware_id and self.db_manager and self.memory_analyzer:
                    # Создаем задачу в фоне - НЕ ЖДЕМ завершения
                    asyncio.create_task(
                        self._update_memory_background(hardware_id, prompt, response.text)
                    )
                    logger.info(f"🔄 Задача обновления памяти запущена в фоне для {hardware_id}")
                elif hardware_id and self.db_manager:
                    logger.warning(f"⚠️ MemoryAnalyzer недоступен для {hardware_id}, память не будет обновлена")
                elif hardware_id:
                    logger.warning(f"⚠️ DatabaseManager недоступен для {hardware_id}, память не будет обновлена")

        except Exception as e:
            logger.error(f"Ошибка в Gemini Live API: {e}", exc_info=True)
            yield "Извините, произошла внутренняя ошибка при обработке вашего запроса."
    
    def clean_text(self, text: str) -> str:
        """Простая очистка текста."""
        text = re.sub(r'\s+', ' ', text).strip()
        text = text.replace('*', '')
        return text

    def _should_analyze_screenshot(self, prompt: str) -> bool:
        """
        Определяет, нужен ли анализ скриншота для данного запроса.
        Возвращает True только если пользователь явно просит проанализировать экран.
        """
        prompt_lower = prompt.lower().strip()
        
        # Ключевые фразы, которые ТРЕБУЮТ анализа экрана
        screen_analysis_keywords = [
            'what do i see', 'what is on screen', 'what is on the screen',
            'describe screen', 'describe my screen', 'what am i working on',
            'what is on the right', 'what is on the left', 'what is on top',
            'what is on bottom', 'describe desktop', 'describe my desktop',
            'what is visible', 'what can you see', 'tell me what you see',
            'analyze screen', 'analyze my screen', 'what does my screen show',
            'screen content', 'screen information', 'what is displayed',
            'что я вижу', 'что на экране', 'опиши экран', 'что я делаю',
            'что справа', 'что слева', 'что сверху', 'что снизу',
            'описать рабочий стол', 'что видно', 'что показывается'
        ]
        
        # Проверяем, содержит ли запрос ключевые фразы для анализа экрана
        for keyword in screen_analysis_keywords:
            if keyword in prompt_lower:
                logger.info(f"🔍 Запрос требует анализа экрана: '{keyword}' найдено в '{prompt}'")
                return True
        
        # Если это общий вопрос, новости, поиск - скриншот НЕ нужен
        general_keywords = [
            'how are you', 'hello', 'hi', 'good morning', 'good evening',
            'what is', 'how does', 'explain', 'tell me about', 'search for',
            'latest news', 'weather', 'current', 'today', 'now',
            'как дела', 'привет', 'доброе утро', 'добрый вечер',
            'что такое', 'как работает', 'объясни', 'расскажи про', 'найди',
            'последние новости', 'погода', 'текущий', 'сегодня', 'сейчас'
        ]
        
        for keyword in general_keywords:
            if keyword in prompt_lower:
                logger.info(f"🔍 Запрос НЕ требует анализа экрана: '{keyword}' найдено в '{prompt}'")
                return False
        
        # По умолчанию - скриншот НЕ нужен (безопасный выбор)
        logger.info(f"🔍 Запрос не содержит явных указаний на анализ экрана: '{prompt}'")
        return False

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
    
    async def _update_memory_background(self, hardware_id: str, prompt: str, response: str):
        """
        Фоновое обновление памяти пользователя.
        
        Args:
            hardware_id: Аппаратный ID пользователя
            prompt: Запрос пользователя
            response: Ответ ассистента
        """
        try:
            logger.debug(f"🔄 Начинаю фоновое обновление памяти для {hardware_id}")
            
            # Анализируем разговор для извлечения памяти
            short_memory, long_memory = await self.memory_analyzer.analyze_conversation(
                prompt, 
                response
            )
            
            # Если есть что сохранять
            if short_memory or long_memory:
                # Обновляем память в базе данных
                success = await asyncio.to_thread(
                    self.db_manager.update_user_memory,
                    hardware_id,
                    short_memory,
                    long_memory
                )
                
                if success:
                    logger.info(f"✅ Память для {hardware_id} обновлена: краткосрочная ({len(short_memory)} символов), долгосрочная ({len(long_memory)} символов)")
                else:
                    logger.warning(f"⚠️ Не удалось обновить память для {hardware_id}")
            else:
                logger.debug(f"🧠 Для {hardware_id} не найдено информации для запоминания")
                
        except Exception as e:
            logger.error(f"❌ Ошибка фонового обновления памяти для {hardware_id}: {e}")
            # НЕ поднимаем исключение - это фоновая задача