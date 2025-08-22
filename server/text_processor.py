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
    
    🚨 ВАЖНО: System Prompt теперь правильно передается в конфигурации сессии,
    а не как обычное сообщение. Это обеспечивает корректное поведение ассистента.
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
    
    def cancel_generation(self):
        """
        МГНОВЕННО отменяет текущую генерацию LLM и очищает все процессы.
        Используется для принудительного прерывания.
        """
        try:
            logger.warning("🚨 МГНОВЕННАЯ отмена генерации LLM!")
            
            # КРИТИЧНО: отменяем текущую генерацию Gemini
            if hasattr(self, '_current_generation'):
                try:
                    if hasattr(self._current_generation, 'cancel'):
                        self._current_generation.cancel()
                        logger.warning("🚨 Gemini генерация МГНОВЕННО ОТМЕНЕНА!")
                except:
                    pass
                self._current_generation = None
            
            # КРИТИЧНО: очищаем все внутренние буферы
            if hasattr(self, '_text_buffer'):
                self._text_buffer.clear()
                logger.warning("🚨 Текстовые буферы МГНОВЕННО ОЧИЩЕНЫ!")
            
            # КРИТИЧНО: очищаем все временные переменные
            if hasattr(self, '_current_prompt'):
                self._current_prompt = None
                logger.warning("🚨 Текущий промпт МГНОВЕННО ОЧИЩЕН!")
            
            logger.warning("✅ Все процессы LLM МГНОВЕННО отменены!")
            
        except Exception as e:
            logger.error(f"❌ Ошибка отмены генерации LLM: {e}")
    
    def clear_buffers(self):
        """
        МГНОВЕННО очищает все буферы и отменяет генерацию.
        """
        self.cancel_generation()

    def set_database_manager(self, db_manager):
        """
        Устанавливает DatabaseManager для работы с памятью.
        
        Args:
            db_manager: Экземпляр DatabaseManager
        """
        self.db_manager = db_manager
        logger.info("✅ DatabaseManager установлен в TextProcessor")
    
    async def generate_response_stream(self, prompt: str, hardware_id: str = None, screenshot_base64: str = None, interrupt_checker=None, **kwargs) -> AsyncGenerator[str, None]:
        """
        Генерирует ответ с помощью Gemini Live API и стримит результат.
        interrupt_checker: функция для проверки необходимости прерывания
        """
        if not self.client:
            logger.error("Gemini клиент не инициализирован.")
            yield "Извините, произошла ошибка конфигурации ассистента."
            return

        logger.info(f"Запускаю Gemini Live API для: '{prompt[:50]}...'")
        
        # КРИТИЧНО: сохраняем функцию проверки прерывания
        self._interrupt_checker = interrupt_checker
        self._current_prompt = prompt
        
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
🧠 MEMORY CONTEXT (для контекста ответа):

📋 КРАТКОСРОЧНАЯ ПАМЯТЬ (текущая сессия):
{memory_data.get('short', 'Нет краткосрочной памяти')}

📚 ДОЛГОСРОЧНАЯ ПАМЯТЬ (информация о пользователе):
{memory_data.get('long', 'Нет долгосрочной памяти')}

💡 ИНСТРУКЦИИ ПО ИСПОЛЬЗОВАНИЮ ПАМЯТИ:
- Используй краткосрочную память для понимания текущего контекста разговора
- Используй долгосрочную память для персонализации ответов (имя, предпочтения, важные детали)
- Если память не релевантна текущему запросу - игнорируй её
- Память должна дополнять ответ, а не заменять его
- Приоритет: текущий запрос > краткосрочная память > долгосрочная память
"""
                        logger.info(f"🧠 Получена память для {hardware_id}: краткосрочная ({len(memory_data.get('short', ''))} символов), долгосрочная ({len(memory_data.get('long', ''))} символов)")
                    else:
                        logger.info(f"🧠 Память для {hardware_id} пуста")
            except asyncio.TimeoutError:
                logger.warning(f"⏰ Таймаут получения памяти для {hardware_id}")
            except Exception as e:
                logger.warning(f"⚠️ Ошибка получения памяти: {e}")
        
        try:
            # Формируем системную инструкцию с учетом памяти
            base_system_instruction = (
                "You are a helpful assistant for blind and visually impaired users. Respond naturally and directly - just give the information they need without extra explanations about what you're doing.\n\n"
                "TYPES OF REQUESTS:\n\n"

                "🔍 SEARCH REQUESTS - Use web search for:\n\n"
                "- Current news, weather, sports\n"
                "- Recent events, today's happenings  \n"
                "- Live information (stock prices, schedules)\n"
                "- Any question about current/recent events\n\n"

                "📱 SCREEN ANALYSIS - Take screenshot when user asks:\n\n"
                "- 'What's on my screen?'\n"
                "- 'What do you see?'\n"
                "- 'Describe what's here'\n"
                "- 'What's on the left/right side?'\n\n"

                "💭 CONVERSATION - Use your knowledge for:\n\n"
                "- General questions (how things work, definitions)\n"
                "- Cooking, calculations, explanations\n"
                "- Historical facts, science concepts\n\n"

                "RESPONSE STYLE:\n\n"
                "- Answer directly without saying 'Based on your request' or 'I understand'\n"
                "- Don't mention what category the request is\n"
                "- Be conversational but focused\n"
                "- Talk like a real person, be their friend\n\n"

                "🧠 MEMORY RULES:\n\n"
                "- Use memory when user specifically references previous conversations\n"
                "- Don't use memory for unrelated topics\n"
                "- Memory should enhance, not replace current context\n"
                "- Be selective about what to recall\n"
                "- If memory context is provided, use it to provide more relevant answers\n\n"

                "⚠️ SAFETY WARNINGS:\n\n"
                "- If you see suspicious websites, dangerous links, or harmful content on screen - warn them immediately\n"
                "- Alert about phishing emails, malicious downloads, or unsafe websites\n"
                "- Since they can't see, they depend on you to keep them safe from clicking dangerous things\n\n"

                "EXAMPLES:\n\n"
                "❌ Bad: 'I understand you want me to analyze your screen. Based on your request, I can see...'\n"
                "✅ Good: 'I can see your desktop with Chrome browser open and three folders...'\n\n"

                " ❌ Bad: 'Based on your search request for weather, let me find that information...'\n"
                "✅ Good: 'Today in Montreal it's 15°C and partly cloudy...'\n\n"

                "Just be helpful and direct - they want information, not explanations of your process. "
                           
            )
            
            # 🚨 ГИБРИДНЫЙ ПОДХОД: базовые правила в System Prompt, контекст в User Prompt
            if memory_context:
                # System Prompt остается базовым (правила памяти)
                system_instruction = base_system_instruction
                logger.info(f"🧠 System Prompt: базовые правила памяти + правила поведения")
                logger.info(f"🧠 Контекст памяти будет добавлен в User Prompt")
            else:
                system_instruction = base_system_instruction
                logger.info(f"🧠 System Prompt: базовые правила памяти + правила поведения")
                logger.info(f"🧠 Контекст памяти не предоставлен")
            
            # Создаем сессию Live API с System Prompt
            async with self.client.aio.live.connect(
                model="models/gemini-2.0-flash-live-001", 
                config=self.config,
                system_instruction=system_instruction  # 🚨 ПЕРЕДАЕМ КАК SYSTEM PROMPT!
            ) as session:
                
                # ✅ System Prompt теперь правильно установлен в конфигурации сессии!
                logger.info(f"🧠 System Prompt установлен: {len(system_instruction)} символов")
                logger.info(f"🧠 System Prompt: {system_instruction[:200]}...")
                
                # --- УМНАЯ ОБРАБОТКА СКРИНШОТА ---
                # Анализируем запрос и решаем, нужен ли скриншот
                
                # 🚨 ГИБРИДНЫЙ ПОДХОД: контекст памяти добавляется в User Prompt
                if memory_context:
                    # Формируем расширенный User Prompt с четким разделением памяти
                    enhanced_prompt = f"""{memory_context}

👤 USER REQUEST:
{prompt}

🎯 ЗАДАЧА:
Ответь на запрос пользователя, используя контекст памяти если он релевантен.
Если память не связана с текущим запросом - игнорируй её.
Приоритет: текущий запрос > краткосрочная память > долгосрочная память."""
                    content = [enhanced_prompt]
                    logger.info(f"🧠 User Prompt расширен контекстом памяти: {len(memory_context)} символов")
                    logger.info(f"🧠 Структура: Memory Context + User Request + Task")
                else:
                    content = [prompt]
                    logger.info(f"🧠 User Prompt без контекста памяти")
                
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

                # 📋 ЛОГИРУЕМ СТРУКТУРУ СООБЩЕНИЙ
                logger.info(f"📋 СТРУКТУРА СООБЩЕНИЙ:")
                logger.info(f"   🧠 System Prompt: {len(system_instruction)} символов (базовые правила + правила памяти)")
                if memory_context:
                    logger.info(f"   🧠 Memory Context: краткосрочная + долгосрочная память")
                    logger.info(f"   👤 User Prompt: расширен контекстом памяти + запрос + задача")
                else:
                    logger.info(f"   👤 User Prompt: только запрос пользователя")
                if len(content) > 1:
                    logger.info(f"   📸 Мультимодальный контент: текст + изображение")
                else:
                    logger.info(f"   📝 Только текстовый контент")
                
                # 🚨 ВАЖНО: Структура сообщений в Gemini Live API:
                # 
                # 1️⃣ SYSTEM PROMPT (system_instruction):
                #    - Передается в конфигурации сессии
                #    - Определяет поведение ассистента
                #    - Включает правила, стиль, безопасность
                #    - НЕ тратит токены на генерацию
                #
                # 2️⃣ USER PROMPT (content):
                #    - Отправляется через session.send()
                #    - Содержит: Memory Context + User Request + Task
                #    - Memory Context: краткосрочная + долгосрочная память
                #    - Может включать текст + изображение
                #    - Помечается как end_of_turn=True
                #
                # 3️⃣ ASSISTANT RESPONSE:
                #    - Получается через session.receive()
                #    - Стримится по частям
                #    - Обрабатывается и отправляется пользователю
                #
                # 🧠 MEMORY STRUCTURE:
                #    - Краткосрочная: текущий разговор, контекст сессии
                #    - Долгосрочная: информация о пользователе, предпочтения
                #    - Приоритет: запрос > краткосрочная > долгосрочная
                
                # Отправляем запрос (с изображением или без)
                await session.send(input=content, end_of_turn=True)
                if len(content) > 1:
                    logger.info("📝 Мультимодальный запрос (текст + изображение) отправлен")
                else:
                    logger.info("📝 Текстовый запрос отправлен")
                
                # Получаем ответ
                turn = session.receive()
                accumulated_text = ""
                
                # КРИТИЧНО: проверяем прерывание ПЕРЕД началом цикла
                if self._interrupt_checker and self._interrupt_checker():
                    logger.warning(f"🚨 ГЛОБАЛЬНЫЙ ФЛАГ ПРЕРЫВАНИЯ АКТИВЕН - МГНОВЕННО ПРЕРЫВАЮ ГЕНЕРАЦИЮ LLM!")
                    return
                
                async for response in turn:
                    # КРИТИЧНО: проверяем необходимость прерывания в КАЖДОЙ итерации
                    if self._interrupt_checker and self._interrupt_checker():
                        logger.warning(f"🚨 ГЛОБАЛЬНЫЙ ФЛАГ ПРЕРЫВАНИЯ АКТИВЕН - МГНОВЕННО ПРЕРЫВАЮ ГЕНЕРАЦИЮ LLM!")
                        return
                    
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
                                    # КРИТИЧНО: проверяем прерывание перед отправкой каждого предложения
                                    if self._interrupt_checker and self._interrupt_checker():
                                        logger.warning(f"🚨 ГЛОБАЛЬНЫЙ ФЛАГ ПРЕРЫВАНИЯ АКТИВЕН - МГНОВЕННО ПРЕРЫВАЮ ОТПРАВКУ ПРЕДЛОЖЕНИЯ!")
                                        return
                                    
                                    logger.info(f"📤 Отправляю предложение: '{sentence[:100]}...'")
                                    yield sentence.strip()
                            
                            # Оставляем последнее предложение для следующей итерации
                            accumulated_text = sentences[-1]
                        elif len(sentences) == 1 and self._is_complete_sentence(accumulated_text):
                            # Если получили одно полное предложение
                            sentence = sentences[0]
                            if sentence.strip():
                                # КРИТИЧНО: проверяем прерывание перед отправкой предложения
                                if self._interrupt_checker and self._interrupt_checker():
                                    logger.warning(f"🚨 ГЛОБАЛЬНЫЙ ФЛАГ ПРЕРЫВАНИЯ АКТИВЕН - МГНОВЕННО ПРЕРЫВАЮ ОТПРАВКУ ПРЕДЛОЖЕНИЯ!")
                                    return
                                
                                logger.info(f"📤 Отправляю предложение: '{sentence[:100]}...'")
                                yield sentence.strip()
                            accumulated_text = ""
                
                # Отправляем оставшийся текст, если он есть
                if accumulated_text.strip():
                    logger.info(f"📤 Отправляю оставшийся текст: '{accumulated_text[:100]}...'")
                    yield accumulated_text.strip()
                
                logger.info("✅ Gemini Live API ответ получен и обработан")
                
                # ФОНОВОЕ обновление памяти (НЕ БЛОКИРУЕТ)
                if hardware_id and self.db_manager and self.memory_analyzer:
                    # Создаем задачу в фоне - НЕ ЖДЕМ завершения
                    asyncio.create_task(
                        self._update_memory_background(hardware_id, prompt, accumulated_text)
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