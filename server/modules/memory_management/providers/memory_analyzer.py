"""
Memory Analyzer - анализ диалогов для извлечения памяти

Использует Gemini API для анализа разговоров и извлечения:
- Краткосрочной памяти (контекст текущего разговора)
- Долгосрочной памяти (важная информация о пользователе)

Этот класс заменяет отсутствующий memory_analyzer.py
"""

import asyncio
import logging
import re
from typing import Tuple

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None

logger = logging.getLogger(__name__)

class MemoryAnalyzer:
    """
    Анализатор диалогов для извлечения памяти пользователей.
    
    Использует Gemini API для анализа разговоров и извлечения важной информации
    для краткосрочной и долгосрочной памяти.
    """
    
    def __init__(self, gemini_api_key: str):
        """
        Инициализация MemoryAnalyzer.
        
        Args:
            gemini_api_key: API ключ для Gemini
        """
        if not GEMINI_AVAILABLE:
            raise ImportError("google.generativeai not available")
        
        self.api_key = gemini_api_key
        genai.configure(api_key=gemini_api_key)
        
        # Настройки модели
        self.model_name = "gemini-2.5-flash-lite"
        self.temperature = 0.3
        
        # Промпт для анализа памяти
        self.analysis_prompt_template = """
        Analyze this conversation between user and AI assistant to extract memory information.
        
        USER INPUT: {prompt}
        AI RESPONSE: {response}
        
        CRITICAL: You MUST respond ONLY in English. Never use any other language.
        If the conversation is in another language, understand it but respond in English.
        
        Extract and categorize information into:
        
        1. SHORT-TERM MEMORY (current conversation context):
           - Current topic being discussed
           - Recent context that helps understand the conversation flow
           - Temporary information relevant to this session
           - Keep it concise and relevant
        
        2. LONG-TERM MEMORY (important user information):
           - User's name, preferences, important details
           - Significant facts about the user
           - Important relationships or context
           - Information worth remembering for future conversations
           - Only include truly important information
        
        Rules:
        - If no important information is found, return empty strings
        - Keep memories concise and factual
        - Don't include generic information
        - Focus on what would be useful for future conversations
        - Separate short-term and long-term clearly
        - ALWAYS write memory in English, regardless of the original language
        
        Return in this format:
        SHORT_TERM: [extracted short-term memory or empty]
        LONG_TERM: [extracted long-term memory or empty]
        """
        
        logger.info("✅ MemoryAnalyzer initialized with Gemini API")
    
    async def analyze_conversation(self, prompt: str, response: str) -> Tuple[str, str]:
        """
        Анализирует диалог для извлечения памяти.
        
        Args:
            prompt: Запрос пользователя
            response: Ответ ассистента
            
        Returns:
            Кортеж (short_memory, long_memory)
        """
        try:
            # Формируем промпт для анализа
            analysis_prompt = self.analysis_prompt_template.format(
                prompt=prompt,
                response=response
            )
            
            # Создаем модель
            model = genai.GenerativeModel(
                model_name=self.model_name,
                generation_config=genai.types.GenerationConfig(
                    temperature=self.temperature,
                    max_output_tokens=1024,
                )
            )
            
            # Анализируем диалог
            logger.debug(f"🧠 Analyzing conversation for memory extraction...")
            
            # Выполняем анализ асинхронно
            response_obj = await asyncio.to_thread(
                model.generate_content,
                analysis_prompt
            )
            
            if not response_obj or not response_obj.text:
                logger.warning("⚠️ Empty response from Gemini for memory analysis")
                return "", ""
            
            # Парсим результат
            short_memory, long_memory = self._parse_analysis_response(response_obj.text)
            
            logger.info(f"🧠 Memory analysis completed: short-term ({len(short_memory)} chars), long-term ({len(long_memory)} chars)")
            
            return short_memory, long_memory
            
        except Exception as e:
            logger.error(f"❌ Error analyzing conversation for memory: {e}")
            return "", ""
    
    def _parse_analysis_response(self, response_text: str) -> Tuple[str, str]:
        """
        Парсит ответ от Gemini для извлечения краткосрочной и долгосрочной памяти.
        
        Args:
            response_text: Текст ответа от Gemini
            
        Returns:
            Кортеж (short_memory, long_memory)
        """
        try:
            # Ищем паттерны SHORT_TERM: и LONG_TERM:
            short_term_match = re.search(r'SHORT_TERM:\s*(.*?)(?=LONG_TERM:|$)', response_text, re.DOTALL | re.IGNORECASE)
            long_term_match = re.search(r'LONG_TERM:\s*(.*?)$', response_text, re.DOTALL | re.IGNORECASE)
            
            short_memory = ""
            long_memory = ""
            
            if short_term_match:
                short_memory = short_term_match.group(1).strip()
                # Убираем лишние пробелы и переносы строк
                short_memory = re.sub(r'\s+', ' ', short_memory)
            
            if long_term_match:
                long_memory = long_term_match.group(1).strip()
                # Убираем лишние пробелы и переносы строк
                long_memory = re.sub(r'\s+', ' ', long_memory)
            
            # Проверяем, что память не пустая и не содержит только служебные слова
            if short_memory.lower() in ['empty', 'none', 'no information', '']:
                short_memory = ""
            
            if long_memory.lower() in ['empty', 'none', 'no information', '']:
                long_memory = ""
            
            logger.debug(f"🧠 Parsed memory - Short: '{short_memory[:100]}...', Long: '{long_memory[:100]}...'")
            
            return short_memory, long_memory
            
        except Exception as e:
            logger.error(f"❌ Error parsing memory analysis response: {e}")
            return "", ""
    
    def is_available(self) -> bool:
        """
        Проверяет доступность анализатора.
        
        Returns:
            True если анализатор готов к работе
        """
        return GEMINI_AVAILABLE and self.api_key is not None
