import asyncio
import logging
import os
import re
from typing import AsyncGenerator, List

# Импортируем конфигурацию для загрузки переменных окружения
from config import Config
from utils.text_utils import split_into_sentences, clean_text, is_sentence_complete

# 🚀 НОВЫЙ: Gemini Live API (основной)
try:
    from google import genai
    from google.genai import types
    GEMINI_LIVE_AVAILABLE = True
except ImportError as e:
    GEMINI_LIVE_AVAILABLE = False

# 🔄 FALLBACK: LangChain + Google Gemini
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.messages import HumanMessage, SystemMessage
    LANGCHAIN_AVAILABLE = True
except ImportError as e:
    LANGCHAIN_AVAILABLE = False

# --- Загрузка конфигурации ---
# Проверка наличия необходимых ключей API
if not Config.GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found. Check config.env")

# Проверяем доступность хотя бы одного API
if not GEMINI_LIVE_AVAILABLE and not LANGCHAIN_AVAILABLE:
    raise ImportError("Neither Gemini Live API nor LangChain are available. Install required dependencies.")

logger = logging.getLogger(__name__)
logger.info(f"🔧 API Status: Live API={GEMINI_LIVE_AVAILABLE}, LangChain={LANGCHAIN_AVAILABLE}")

class TextProcessor:
    """
    Обрабатывает текстовые запросы с использованием Google Gemini Live API (основной)
    и LangChain + Google Gemini (fallback).
    
    🚀 ОСНОВНОЙ: Gemini Live API с поддержкой Google Search и инструментов
    🔄 FALLBACK: LangChain для случаев, когда Live API недоступен
    
    🚨 ВАЖНО: System Prompt передается в конфигурации сессии Live API
    """
    
    def __init__(self):
        # Инициализируем компоненты памяти
        self.memory_analyzer = None
        self.db_manager = None
        
        # ✅ System Prompt для обоих API
        self.base_system_instruction = (
            "Your name is Nexy."
            "You are a helpful assistant for blind and visually impaired users. "
            "IMPORTANT: ALWAYS respond in ENGLISH ONLY, regardless of the user's language. "
            "Answer on question, exactly what user wants to know or get. Be polite, friendly and funn, don't be rude and sad be very funny and happy. ALWAYS analyze screenshots when provided to help the user understand what's on their screen and derectly answer to the question without empty words.\n"
   
            
            "🎯 YOUR CAPABILITIES:\n\n"
            
            "💬 BASIC CONVERSATION - for:\n"
            "- General questions and explanations\n"
            "- How things work\n"
            "- Definitions and concepts\n"
            "- Historical facts\n"
            "- Scientific explanations\n"
            "- Simple advice and help\n\n"
            
            "📱 SCREEN ANALYSIS - ALWAYS when screenshot available:\n"
            "- ALWAYS analyze and describe what you see on the screen\n"
            "- DO NOT return JSON coordinates or technical image analysis\n"
            "- Simply describe what you see on screen in natural language\n"
            "- Focus on helping the user with their question\n"
            "- If you see any dangerous content, warn about it\n\n"
            "- Focus on elements, applications what is on screen, you need to help with navigation and current situation and position of elements on screen\n"
           
            
            "🔍 MANDATORY GOOGLE SEARCH - ALWAYS USE for:\n"
            "- Latest news, current events, breaking news\n"
            "- Weather forecasts and current conditions\n"
            "- Stock prices, cryptocurrency rates, financial data\n"
            "- Movie ratings, restaurant reviews, hotel reviews\n"
            "- Product prices, shopping information\n"
            "- ANY question requiring up-to-date information\n"
            "- NEVER say 'I can't provide current information' - ALWAYS SEARCH FIRST\n"
            "- ALWAYS cite sources when using search results\n\n"
            
            "📋 RESPONSE RULES:\n"
            "- Answer briefly and clearly\n"
            "- Be friendly and helpful\n"
            "- Don't over-explain\n"
            "- Focus on what the user needs\n"
            
            "REMEMBER: Keep it simple, helpful and Use memory just in case if you need to use, it's really helpful and user asks something about it but otherwise don't use it. Analyze a screenshot just when you were asking about about a screenshot of this kind of question otherwise you need to answer exactly on the question\n\n"
            "🚨 CRITICAL: For ANY question about news, current events, weather, prices, or recent information - you MUST use Google Search. Do NOT say you can't provide current information - search first!"
        )
        
        logger.info(f"✅ base_system_instruction created: {len(self.base_system_instruction)} characters")
        
        try:
            # 🚀 ИНИЦИАЛИЗАЦИЯ GEMINI LIVE API (основной)
            if GEMINI_LIVE_AVAILABLE:
                logger.info("🚀 Initializing Gemini Live API (primary)")
                
                # Создаем клиент Live API с правильными параметрами
                self.live_client = genai.Client(
                    http_options={"api_version": "v1beta"},
                    api_key=Config.GEMINI_API_KEY,
                )
                
                # 🔧 КОНФИГУРАЦИЯ Live API с правильными enum значениями
                self.live_config = types.LiveConnectConfig(
                    response_modalities=[types.Modality.TEXT],  # Используем enum
                    media_resolution=types.MediaResolution.MEDIA_RESOLUTION_MEDIUM,  # Используем enum
                    context_window_compression=types.ContextWindowCompressionConfig(
                        trigger_tokens=25600,
                        sliding_window=types.SlidingWindow(target_tokens=12800),
                    ),
                    # 🔧 System Prompt передается ТОЛЬКО в конфигурации
                    system_instruction=self.base_system_instruction,
                    # 🔧 ВОССТАНАВЛИВАЕМ Google Search
                    tools=[
                        types.Tool(
                            google_search=types.GoogleSearch()
                        )
                    ]
                )
                
                logger.info("✅ Google Search tool configured in Live API")
                
                # Модель Live API
                self.live_model = "models/gemini-2.5-flash-live-preview"
                
                # Флаг использования Live API
                self.use_live_api = True
                
                logger.info("✅ Gemini Live API initialized successfully")
                
            else:
                logger.warning("⚠️ Gemini Live API not available")
                self.live_client = None
                self.live_config = None
                self.live_model = None
                self.use_live_api = False
            
            # 🔄 ИНИЦИАЛИЗАЦИЯ LANGCHAIN (fallback)
            if LANGCHAIN_AVAILABLE:
                logger.info("🔄 Initializing LangChain (fallback)")
                
                self.llm = ChatGoogleGenerativeAI(
                    model="gemini-2.5-flash-lite",
                    google_api_key=Config.GEMINI_API_KEY,
                    temperature=0.7,
                    max_output_tokens=2048
                )
                
                logger.info("✅ LangChain initialized successfully (fallback)")
                
            else:
                logger.warning("⚠️ LangChain not available")
                self.llm = None
            
            # Проверяем, что хотя бы один API доступен
            if not self.use_live_api and not self.llm:
                raise RuntimeError("No LLM API available. Both Live API and LangChain failed to initialize.")
            
            # Инициализируем MemoryAnalyzer (если доступен)
            gemini_api_key = Config.GEMINI_API_KEY
            if gemini_api_key:
                try:
                    from memory_analyzer import MemoryAnalyzer
                    self.memory_analyzer = MemoryAnalyzer(gemini_api_key)
                    logger.info(f"✅ MemoryAnalyzer initialized")
                except ImportError as e:
                    logger.warning(f"⚠️ MemoryAnalyzer cannot be imported: {e}")
                    self.memory_analyzer = None
                except Exception as e:
                    logger.warning(f"⚠️ MemoryAnalyzer not initialized: {e}")
                    self.memory_analyzer = None
            
        except Exception as e:
            logger.error(f"❌ Error initializing TextProcessor: {e}", exc_info=True)
            self.live_client = None
            self.llm = None
            raise
    

    
    def cancel_generation(self):
        """
        МГНОВЕННО отменяет текущую генерацию LLM и очищает все процессы.
        Используется для принудительного прерывания.
        """
        try:
            logger.warning("🚨 IMMEDIATELY canceling LLM generation!")
            
            # КРИТИЧНО: отменяем текущую генерацию Gemini
            if hasattr(self, '_current_generation'):
                try:
                    if hasattr(self._current_generation, 'cancel'):
                        self._current_generation.cancel()
                        logger.warning("🚨 Gemini generation IMMEDIATELY CANCELLED!")
                except:
                    pass
                self._current_generation = None
            
            # КРИТИЧНО: очищаем все внутренние буферы
            if hasattr(self, '_text_buffer'):
                self._text_buffer.clear()
                logger.warning("🚨 Text buffers IMMEDIATELY CLEARED!")
            
            # КРИТИЧНО: очищаем все временные переменные
            if hasattr(self, '_current_prompt'):
                self._current_prompt = None
                logger.warning("🚨 Current prompt IMMEDIATELY CLEARED!")
            
            logger.warning("✅ All LLM processes IMMEDIATELY cancelled!")
            
        except Exception as e:
            logger.error(f"❌ Error canceling LLM generation: {e}")
    
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
        logger.info("✅ DatabaseManager set in TextProcessor")
    
    async def generate_response_stream(self, prompt: str, hardware_id: str = None, screenshot_base64: str = None, interrupt_checker=None, **kwargs) -> AsyncGenerator[str, None]:
        """
        🎯 ОСНОВНОЙ МЕТОД: Все запросы идут через Gemini Live API с fallback на LangChain
        """
        try:
            logger.info(f"🚀 Starting hybrid request processing: '{prompt[:100]}...'")
            
            # 🔍 ДЕТАЛЬНОЕ ЛОГИРОВАНИЕ ВХОДНЫХ ДАННЫХ
            logger.info(f"🖼️ Hybrid: Input screenshot_base64: {screenshot_base64[:100] if screenshot_base64 else 'None'}...")
            logger.info(f"🖼️ Hybrid: Input screenshot_base64 length: {len(screenshot_base64) if screenshot_base64 else 0}")
            logger.info(f"🖼️ Hybrid: Input hardware_id: {hardware_id}")
            
            # 🔧 ПОЛУЧАЕМ КОНТЕКСТ ПАМЯТИ (если доступен)
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
🧠 MEMORY CONTEXT (for response context):

📋 SHORT-TERM MEMORY (current session):
{memory_data.get('short', 'No short-term memory')}

📚 LONG-TERM MEMORY (user information):
{memory_data.get('long', 'No long-term memory')}

💡 MEMORY USAGE INSTRUCTIONS:
- Use short-term memory to understand current conversation context
- Use long-term memory for response personalization (name, preferences, important details)
- If memory is not relevant to current request - ignore it
- Memory should complement the answer, not replace it
- Priority: current request > short-term memory > long-term memory
                            """
                            logger.info(f"🧠 Memory obtained for {hardware_id}: short-term ({len(memory_data.get('short', ''))} chars), long-term ({len(memory_data.get('long', ''))} chars)")
                        else:
                            logger.info(f"🧠 Memory for {hardware_id} is empty")
                except asyncio.TimeoutError:
                    logger.warning(f"⏰ Timeout getting memory for {hardware_id}")
                except Exception as e:
                    logger.warning(f"⚠️ Error getting memory: {e}")
            
            # 🔧 ФОРМИРУЕМ КОНТЕНТ ДЛЯ ЗАПРОСА с памятью
            user_content = prompt
            if memory_context:
                user_content = f"Memory context: {memory_context}\n\n User command: {prompt}"
                logger.info(f"🧠 User content prepared with memory: {len(user_content)} chars")
            else:
                logger.info(f"📝 User content without memory: {len(user_content)} chars")
            
            # 🔧 ОПТИМИЗАЦИЯ: скриншот уже Base64 строка
            screenshot_data = None
            if screenshot_base64:
                logger.info("🖼️ Hybrid: Screenshot Base64 received directly")
                logger.info(f"🖼️ Hybrid: Base64 validation:")
                logger.info(f"   - Base64 length: {len(screenshot_base64)} chars")
                logger.info(f"   - Base64 starts with: {screenshot_base64[:50]}...")
                logger.info(f"   - Base64 ends with: ...{screenshot_base64[-20:]}")
                
                # Проверяем валидность Base64
                if len(screenshot_base64) < 100:
                    logger.warning("⚠️ Hybrid: Base64 string seems too short!")
                if not screenshot_base64.replace('+', '').replace('/', '').replace('=', '').isalnum():
                    logger.warning("⚠️ Hybrid: Base64 string may be corrupted!")
                
                # Создаем простой формат для LangChain
                screenshot_data = {
                    "mime_type": "image/jpeg",  # JPEG от клиента
                    "data": screenshot_base64,
                    "raw_bytes": None,  # Не нужны
                    "width": 0,
                    "height": 0,
                    "size_bytes": len(screenshot_base64)
                }
                logger.info(f"🖼️ Hybrid: Screenshot data prepared:")
                logger.info(f"   - MIME type: {screenshot_data['mime_type']}")
                logger.info(f"   - Base64 data: {len(screenshot_data['data'])} chars")
            else:
                logger.info("🖼️ Hybrid: No screenshot_base64 provided")
            
            # 🚀 ПРИОРИТЕТ 1: Все запросы идут через Gemini Live API (текст + аудио)
            if self.use_live_api and self.live_client:
                try:
                    logger.info("🚀 Main: Using Gemini Live API for ALL requests (text + audio generation)")
                    
                    # 🚀 ИСПОЛЬЗУЕМ Gemini Live API для генерации текста и аудио
                    async for chunk in self._call_live_api_directly(
                        user_content, hardware_id, screenshot_data, interrupt_checker, **kwargs
                    ):
                        yield chunk
                    return  # Успешно завершили с Live API
                    
                except Exception as e:
                    logger.warning(f"⚠️ Main: Live API failed, falling back to LangChain (TEXT ONLY): {e}")
                    # Продолжаем к fallback ТОЛЬКО при ошибке Live API
                    pass
            else:
                logger.info("🔄 Main: Live API not available, using LangChain fallback (TEXT ONLY)...")
            
            # 🔄 FALLBACK: Используем LangChain ТОЛЬКО для текста (без аудио)
            if self.llm:
                logger.info("🔄 Main: Using LangChain fallback (TEXT ONLY - no audio generation)...")
                try:
                    # 🔧 ПОДДЕРЖКА ИЗОБРАЖЕНИЙ В FALLBACK
                    if screenshot_base64:
                        logger.info("🖼️ Main: LangChain fallback - Screenshot detected")
                        
                        # Создаем мультимодальное сообщение с изображением
                        messages = [
                            SystemMessage(content=self.base_system_instruction),
                            HumanMessage(content=[
                                {
                                    "type": "text",
                                    "text": user_content  # 🔧 ИСПРАВЛЕНО: user_content вместо prompt
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{screenshot_base64}"  # 🔧 JPEG вместо WebP
                                    }
                                }
                            ])
                        ]
                        logger.info("✅ Main: LangChain fallback - Multimodal message created")
                    else:
                        # Только текст
                        messages = [
                            SystemMessage(content=self.base_system_instruction),
                            HumanMessage(content=user_content)  # 🔧 ИСПРАВЛЕНО: user_content вместо prompt
                        ]
                        logger.info("✅ Main: LangChain fallback - Text-only message created")
                    
                    # Прямой вызов LLM со стримингом
                    buffer = ""  # Буфер для накопления текста
                    full_response = ""  # Полный ответ для анализа памяти
                    
                    async for chunk in self.llm.astream(messages, config={
                        "cache": False,
                        "force_refresh": True
                    }):
                        # Извлекаем контент из чанка
                        if hasattr(chunk, 'content'):
                            content = chunk.content
                        elif hasattr(chunk, 'text'):
                            content = chunk.text
                        else:
                            content = str(chunk)
                        
                        # Накопление в буфере и полном ответе
                        if content:
                            buffer += content
                            full_response += content
                            
                            # УЛУЧШЕННАЯ логика стримминга по предложениям (LangChain)
                            sentences = self._split_into_sentences(buffer)
                            
                            # Отправляем предложения более агрессивно
                            if len(sentences) >= 1:
                                # Отправляем все полные предложения кроме последнего
                                for sentence in sentences[:-1]:
                                    if sentence.strip():
                                        # 🔄 LANGCHAIN FALLBACK: Добавляем маркер "TEXT_ONLY" для отключения аудио
                                        yield f"__LANGCHAIN_TEXT_ONLY__:{sentence.strip()}"
                                
                                # Если есть только одно предложение и оно завершено - отправляем его
                                if len(sentences) == 1 and is_sentence_complete(sentences[0]):
                                    # 🔄 LANGCHAIN FALLBACK: Добавляем маркер "TEXT_ONLY" для отключения аудио
                                    yield f"__LANGCHAIN_TEXT_ONLY__:{sentences[0].strip()}"
                                    buffer = ""  # Очищаем буфер
                                else:
                                    # Оставляем последнее предложение в буфере
                                    buffer = sentences[-1]
                            
                            # ДОПОЛНИТЕЛЬНО: отправляем предложения по мере накопления
                            # Если буфер стал слишком большим (>200 символов), принудительно разбиваем
                            if len(buffer) > 200:
                                # Принудительно разбиваем длинный буфер
                                forced_sentences = self._split_into_sentences(buffer)
                                if len(forced_sentences) > 1:
                                    # Отправляем все кроме последнего
                                    for sentence in forced_sentences[:-1]:
                                        if sentence.strip():
                                            # 🔄 LANGCHAIN FALLBACK: Добавляем маркер "TEXT_ONLY" для отключения аудио
                                            yield f"__LANGCHAIN_TEXT_ONLY__:{sentence.strip()}"
                                    buffer = forced_sentences[-1]
                                elif len(forced_sentences) == 1 and is_sentence_complete(forced_sentences[0]):
                                    # Отправляем единственное завершенное предложение
                                    # 🔄 LANGCHAIN FALLBACK: Добавляем маркер "TEXT_ONLY" для отключения аудио
                                    yield f"__LANGCHAIN_TEXT_ONLY__:{forced_sentences[0].strip()}"
                                    buffer = ""
                    
                    # Отправляем оставшийся текст в буфере
                    if buffer.strip():
                        # 🔄 LANGCHAIN FALLBACK: Добавляем маркер "TEXT_ONLY" для отключения аудио
                        yield f"__LANGCHAIN_TEXT_ONLY__:{buffer.strip()}"
                        full_response += buffer.strip()
                    
                    logger.info("✅ Main: LangChain fallback - Streaming completed successfully")
                    
                    # ФОНОВОЕ обновление памяти с РЕАЛЬНЫМ ответом
                    if hardware_id and self.db_manager and self.memory_analyzer:
                        asyncio.create_task(
                            self._update_memory_background(hardware_id, user_content, full_response)
                        )
                        logger.info(f"🔄 Main: Memory update task started in background for {hardware_id} with real response ({len(full_response)} chars)")
                    
                except Exception as e:
                    logger.error(f"❌ Main: LangChain fallback also failed: {e}")
                    yield f"Sorry, both Live API and LangChain failed. Error: {e}"
            else:
                logger.error("❌ Main: No LLM API available")
                yield "Sorry, no AI service is currently available."
                
        except Exception as e:
            logger.error(f"❌ Main: Error in main request processing: {e}", exc_info=True)
            yield "Sorry, an internal error occurred while processing your request."
    
    # clean_text method removed - using common utility function

    def _split_into_sentences(self, text: str) -> List[str]:
        """Разбивает текст на предложения для стриминга - использует общую утилиту"""
        return split_into_sentences(text)
    
    # _is_sentence_complete method removed - using common utility function
    
    async def _call_live_api_directly(self, user_content: str, hardware_id: str = None, screenshot_data: dict = None, interrupt_checker=None, **kwargs) -> AsyncGenerator[str, None]:
        """
        🚀 Прямой вызов Gemini Live API с правильной передачей изображений
        """
        try:
            logger.info(f"🚀 Live API Direct: Starting request: '{user_content[:100]}...'")
            logger.info(f"🔍 Live API Direct: Full user_content: '{user_content}'")
            logger.info(f"🔍 Live API Direct: Content length: {len(user_content)} characters")
            
            # 🔍 ДИАГНОСТИКА: Проверяем конфигурацию перед подключением
            logger.info(f"🔍 Live API Direct: Configuration check:")
            logger.info(f"   - Model: {self.live_model}")
            logger.info(f"   - API Key: {Config.GEMINI_API_KEY[:10] if Config.GEMINI_API_KEY else 'None'}...")
            logger.info(f"   - Tools configured: {len(self.live_config.tools) if hasattr(self.live_config, 'tools') else 0}")
            if hasattr(self.live_config, 'tools') and self.live_config.tools:
                for i, tool in enumerate(self.live_config.tools):
                    if hasattr(tool, 'google_search'):
                        logger.info(f"   - Tool {i+1}: Google Search ✅")
                    else:
                        logger.info(f"   - Tool {i+1}: {type(tool).__name__}")
            logger.info(f"   - Config: {self.live_config}")
            
            # Создаем Live API сессию
            async with self.live_client.aio.live.connect(model=self.live_model, config=self.live_config) as session:
                try:
                    # 🔧 System Prompt уже передан в конфигурации - НЕ отправляем как системное сообщение
                    logger.info("🚀 Live API Direct: System Prompt already in config - no need to send as system message")
                    
                    # 🔧 ОБРАБОТКА СКРИНШОТОВ (если есть)
                    parts = []
                    
                    # Добавляем текстовую часть
                    parts.append(types.Part.from_text(text=user_content))
                    
                    # Добавляем изображение, если есть
                    if screenshot_data and screenshot_data.get('data'):
                        try:
                            # Декодируем Base64 данные
                            import base64
                            image_data = base64.b64decode(screenshot_data['data'])
                            
                            # Создаем Part с изображением
                            image_part = types.Part.from_bytes(
                                data=image_data,
                                mime_type=screenshot_data.get('mime_type', 'image/jpeg')
                            )
                            parts.append(image_part)
                            
                            logger.info(f"🖼️ Live API Direct: Screenshot added - {len(image_data)} bytes, MIME: {screenshot_data.get('mime_type', 'image/jpeg')}")
                            
                        except Exception as e:
                            logger.error(f"❌ Live API Direct: Error processing screenshot: {e}")
                            logger.warning("⚠️ Live API Direct: Continuing with text-only mode")
                    
                    logger.info(f"🔍 Live API Direct: Sending content with {len(parts)} parts: '{user_content[:100]}...'")
                    
                    # 🔧 ОТПРАВЛЯЕМ КОНТЕНТ (текст + изображение если есть)
                    if len(parts) == 1:
                        # Только текст
                        await session.send(input=user_content, end_of_turn=True)
                    else:
                        # Текст + изображение - используем send_client_content
                        await session.send_client_content(
                            turns=types.Content(
                                role='user',
                                parts=parts
                            ),
                            turn_complete=True
                        )
                    
                    if len(parts) == 1:
                        logger.info("✅ Live API Direct: Text-only message sent successfully")
                    else:
                        logger.info(f"✅ Live API Direct: Multimodal message sent successfully ({len(parts)} parts)")
                    
                    # Получаем ответ с поддержкой инструментов
                    buffer = ""  # Буфер для накопления текста
                    full_response = ""  # Полный ответ для анализа памяти
                    
                    turn = session.receive()
                    async for response in turn:
                        # Извлекаем текстовый контент
                        if hasattr(response, 'text') and response.text:
                            content = response.text
                            
                            # Накопление в буфере и полном ответе
                            if content:
                                buffer += content
                                full_response += content
                                
                                # УЛУЧШЕННАЯ логика стримминга по предложениям
                                sentences = self._split_into_sentences(buffer)
                                
                                # Отправляем предложения более агрессивно
                                if len(sentences) >= 1:
                                    # Отправляем все полные предложения кроме последнего
                                    for sentence in sentences[:-1]:
                                        if sentence.strip():
                                            yield sentence.strip()
                                    
                                    # Если есть только одно предложение и оно завершено - отправляем его
                                    if len(sentences) == 1 and is_sentence_complete(sentences[0]):
                                        yield sentences[0].strip()
                                        buffer = ""  # Очищаем буфер
                                    else:
                                        # Оставляем последнее предложение в буфере
                                        buffer = sentences[-1]
                                
                                # ДОПОЛНИТЕЛЬНО: отправляем предложения по мере накопления
                                # Если буфер стал слишком большим (>200 символов), принудительно разбиваем
                                if len(buffer) > 200:
                                    # Принудительно разбиваем длинный буфер
                                    forced_sentences = self._split_into_sentences(buffer)
                                    if len(forced_sentences) > 1:
                                        # Отправляем все кроме последнего
                                        for sentence in forced_sentences[:-1]:
                                            if sentence.strip():
                                                yield sentence.strip()
                                        buffer = forced_sentences[-1]
                                    elif len(forced_sentences) == 1 and is_sentence_complete(forced_sentences[0]):
                                        # Отправляем единственное завершенное предложение
                                        yield forced_sentences[0].strip()
                                        buffer = ""
                        
                        # 🔧 ИСПРАВЛЕНО: Правильная обработка tool calls
                        if hasattr(response, 'tool_calls') and response.tool_calls:
                            for tool_call in response.tool_calls:
                                logger.info(f"🔍 Live API Direct: Tool call detected: {tool_call.function.name}")
                                if hasattr(tool_call, 'function') and tool_call.function.name == 'google_search':
                                    logger.info(f"🔍 Live API Direct: Google Search tool call detected!")
                                    # Инструменты выполняются автоматически Live API
                                    # Результаты придут в следующих response
                        
                        # 🔧 ИСПРАВЛЕНО: Правильная обработка результатов tool calls
                        if hasattr(response, 'tool_response') and response.tool_response:
                            logger.info(f"🔍 Live API Direct: Tool response received!")
                            logger.info(f"🔍 Live API Direct: Tool response type: {type(response.tool_response).__name__}")
                            logger.info(f"🔍 Live API Direct: Tool response attributes: {dir(response.tool_response)}")
                            
                            if hasattr(response.tool_response, 'google_search'):
                                logger.info(f"🔍 Live API Direct: Google Search results received!")
                                # Результаты поиска автоматически включаются в контекст
                            else:
                                logger.info(f"🔍 Live API Direct: Other tool response: {type(response.tool_response).__name__}")
                        
                        # 🔧 ДОПОЛНИТЕЛЬНО: Проверяем parts на наличие результатов поиска
                        if hasattr(response, 'parts') and response.parts:
                            for i, part in enumerate(response.parts):
                                if hasattr(part, 'text') and part.text:
                                    # Проверяем, содержит ли текст результаты поиска
                                    text_lower = part.text.lower()
                                    if any(keyword in text_lower for keyword in ['search results', 'google search', 'found information', 'according to']):
                                        logger.info(f"🔍 Live API Direct: Part {i} contains search results!")
                                elif hasattr(part, 'google_search'):
                                    logger.info(f"🔍 Live API Direct: Part {i} contains Google Search data!")
                            
                            # 🚫 ФИЛЬТРУЕМ executable_code - игнорируем генерацию кода
                            for part in response.parts:
                                if hasattr(part, 'executable_code') and part.executable_code:
                                    logger.info(f"🚫 Live API Direct: Executable code detected and IGNORED (we don't need code generation)")
                                    # Игнорируем код - нам нужен только текст
                                
                                if hasattr(part, 'code_execution_result') and part.code_execution_result:
                                    logger.info(f"🚫 Live API Direct: Code execution result detected and IGNORED (we don't need code execution)")
                                    # Игнорируем результат выполнения кода
                    
                    # Отправляем оставшийся текст в буфере
                    if buffer.strip():
                        yield buffer.strip()
                        full_response += buffer.strip()
                    
                    logger.info("✅ Live API Direct: Streaming completed successfully")
                    
                    # ФОНОВОЕ обновление памяти с РЕАЛЬНЫМ ответом
                    if hardware_id and self.db_manager and self.memory_analyzer:
                        asyncio.create_task(
                            self._update_memory_background(hardware_id, user_content, full_response)
                        )
                        logger.info(f"🔄 Live API Direct: Memory update task started in background for {hardware_id} with real response ({len(full_response)} chars)")
                    
                except Exception as e:
                    logger.error(f"❌ Live API Direct: Error in session: {e}")
                    raise
                    
        except Exception as e:
            logger.error(f"❌ Live API Direct: Error in request processing: {e}", exc_info=True)
            yield f"Sorry, an error occurred while processing your request with Live API: {e}"

    async def _update_memory_background(self, hardware_id: str, prompt: str, response: str):
        """
        Фоновое обновление памяти пользователя.
        
        Args:
            hardware_id: Аппаратный ID пользователя
            prompt: Запрос пользователя
            response: Ответ ассистента
        """
        try:
            logger.debug(f"🔄 Starting background memory update for {hardware_id}")
            
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
                    logger.info(f"✅ Memory for {hardware_id} updated: short-term ({len(short_memory)} chars), long-term ({len(long_memory)} chars)")
                else:
                    logger.warning(f"⚠️ Could not update memory for {hardware_id}")
            else:
                logger.debug(f"🧠 No information found for {hardware_id} to remember")
                
        except Exception as e:
            logger.error(f"❌ Error in background memory update for {hardware_id}: {e}")
            # НЕ поднимаем исключение - это фоновая задача