"""
MemoryAnalyzer - AI-анализ разговоров для извлечения памяти (ИСПРАВЛЕННАЯ ВЕРСИЯ)

Этот модуль отвечает за анализ диалогов между пользователем и ассистентом
для определения, какую информацию следует сохранить в краткосрочной и
долгосрочной памяти пользователя.
"""

import asyncio
import logging
from typing import Dict, Optional, Tuple
import google.generativeai as genai
from google.generativeai.types import GenerateContentResponse

logger = logging.getLogger(__name__)


class MemoryAnalyzer:
    """
    Анализатор памяти для извлечения важной информации из разговоров.
    
    Использует Google Gemini API для анализа диалогов и определения,
    какую информацию следует сохранить в памяти пользователя.
    """
    
    def __init__(self, gemini_api_key: str, model_name: str = "gemini-2.0-flash-exp"):
        """
        Инициализация анализатора памяти.
        
        Args:
            gemini_api_key: API ключ для Google Gemini
            model_name: Название модели Gemini для использования
        """
        self.gemini_api_key = gemini_api_key
        self.model_name = model_name
        self.model = None
        
        # Инициализируем Gemini
        try:
            genai.configure(api_key=gemini_api_key)
            self.model = genai.GenerativeModel(model_name)
            logger.info(f"✅ MemoryAnalyzer инициализирован с моделью {model_name}")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации MemoryAnalyzer: {e}")
            self.model = None
    
    async def analyze_conversation(
        self, 
        user_prompt: str, 
        assistant_response: str,
        conversation_context: Optional[str] = None
    ) -> Tuple[str, str]:
        """
        Анализирует разговор и извлекает краткосрочную и долгосрочную память.
        
        Args:
            user_prompt: Запрос пользователя
            assistant_response: Ответ ассистента
            conversation_context: Дополнительный контекст разговора
            
        Returns:
            Tuple[str, str]: (краткосрочная_память, долгосрочная_память)
        """
        if not self.model:
            logger.warning("⚠️ Gemini модель недоступна, возвращаем пустую память")
            return "", ""
        
        try:
            # Формируем промпт для анализа
            analysis_prompt = self._create_analysis_prompt(
                user_prompt, 
                assistant_response, 
                conversation_context
            )
            
            # Вызываем Gemini для анализа
            short_memory, long_memory = await self._call_gemini_analysis(analysis_prompt)
            
            # Логируем результат
            logger.info(f"🧠 Анализ памяти завершен:")
            logger.info(f"   Краткосрочная: {len(short_memory)} символов")
            logger.info(f"   Долгосрочная: {len(long_memory)} символов")
            
            return short_memory, long_memory
            
        except Exception as e:
            logger.error(f"❌ Ошибка анализа разговора: {e}")
            return "", ""
    
    def _create_analysis_prompt(
        self, 
        user_prompt: str, 
        assistant_response: str,
        conversation_context: Optional[str] = None
    ) -> str:
        """
        Создает промпт для анализа разговора.
        
        Args:
            user_prompt: Запрос пользователя
            assistant_response: Ответ ассистента
            conversation_context: Дополнительный контекст разговора
            
        Returns:
            str: Промпт для Gemini
        """
        context_part = ""
        if conversation_context:
            context_part = f"\n\nКонтекст разговора:\n{conversation_context}"
        
        return f"""**You are an assistant responsible for managing memory. You have two types of memory: Short Memory and Long Memory.**\n\n**Short Memory** is temporary memory that stores information about the current conversation and recent interactions. It is updated frequently and can be cleared after a period of inactivity.\n\n**Long Memory** is long-term memory that stores only important information about the user, their preferences, habits, and key events. This information must be explicitly marked as important by the user, repeated multiple times, or be contextually significant.\n\n---\n\n**You are provided with the following information:**\n1. **User''s request** — the current request sent by the user.\n2. **LLM''s response** — the response generated based on the user''s request.\n3. **Current summarization of Short Memory and Long Memory** — the general information already stored in memory.\n\n---\n\n**Your task:**\n1. Analyze the user''s request and the LLM''s response.\n2. Determine if there is any information that needs to be added to **Short Memory** and/or **Long Memory**.\n3. If the information requires addition, update the corresponding memory (Short Memory or Long Memory) and return the updated summarization.\n4. If the information does not require addition, return the response in the format:\n   - **Short Memory: none**\n   - **Long Memory: none**\n\n---\n\n**Rules for adding information to memory:**\n\n- **Short Memory**:\n  - Add in summary content that relates to the current conversation or recent interactions while not repeating if the conversation is repetitive.\n  - Example: current conversation context, temporary preferences, ongoing tasks.\n\n- **Long Memory**:\n  - **Explicit importance**:\n    - If the user explicitly says \"remember\" or \"save,\" the information is added to Long Memory. For example:\n      - \"Remember that my birthday is on May 15th.\"\n      - \"Save that I don't like spicy food.\"\n  - **Contextual importance**:\n    - If the context of the conversation makes it clear that the information is important to the user, it is also added to Long Memory. For example:\n      - \"My birthday is on May 15th, and it's important to me.\"\n      - \"I don't like noisy places, and it's important to keep that in mind.\"\n  - **Personal data**:\n    - Name, surname, nickname.\n    - Contact information (if provided by the user).\n    - Important dates (birthday, anniversaries).\n    - Place of residence or work (if provided by the user).\n  - **Professional data**:      - professional information or requests.\n  - **Preferences and habits**:\n    - Favorite activities (hobbies, sports, travel).\n    - Preferences in food, drinks, music, movies, etc.\n    - Regular habits (e.g., \"I always drink coffee in the morning\").\n    - Communication preferences (e.g., \"I don't like noisy places\").\n  - **Important events**:\n    - Birthdays, anniversaries, holidays.\n    - Important meetings or events (e.g., \"I have a presentation tomorrow\").\n    - Future plans (e.g., \"I'm planning a trip to Paris next month\").\n  - **Repetition**:\n    - Information must be either explicitly marked as important by the user or repeated multiple times in different conversations. For example:\n      - The user mentions several times that they love traveling.\n      - The user mentions several times that they dislike noisy places.\n  - **Usefulness for personalization**:\n    - Information should be useful for personalizing future interactions. For example:\n      - Personal data can be used to address the user.\n      - Preferences and habits can be used for recommendations.\n      - Important events can be used for reminders or congratulations.\n\n---\n\n**What is NOT added to Long Memory:**\n\n1. **Temporary information**:\n   - Information that relates only to the current conversation or temporary preferences. For example:\n     - \"Today I want pizza.\"\n     - \"I'm looking for a pasta recipe right now.\"\n\n2. **One-time mentions**:\n   - If the user mentions something once, and it is not related to key preferences or important events, it is not added to Long Memory. For example:\n     - \"Yesterday I went to the cinema.\"\n     - \"I watched a movie about space.\"\n\n3. **General information unrelated to the user**:\n   - Information that is not directly related to the user or their preferences."""
    
    async def _call_gemini_analysis(self, analysis_prompt: str) -> Tuple[str, str]:
        """
        Вызывает Gemini API для анализа разговора.
        
        Args:
            analysis_prompt: Промпт для анализа
            
        Returns:
            Tuple[str, str]: (краткосрочная_память, долгосрочная_память)
        """
        try:
            # Устанавливаем таймаут 10 секунд
            async with asyncio.timeout(10.0):
                response = await asyncio.to_thread(
                    self.model.generate_content,
                    analysis_prompt
                )
                
                if response and response.text:
                    logger.info(f"🧠 Получен ответ от Gemini: {response.text[:200]}...")
                    return self._extract_memory_from_response(response.text)
                else:
                    logger.warning("⚠️ Gemini вернул пустой ответ")
                    return "", ""
                    
        except asyncio.TimeoutError:
            logger.warning("⏰ Таймаут анализа памяти (10 сек)")
            return "", ""
        except Exception as e:
            logger.error(f"❌ Ошибка вызова Gemini: {e}")
            return "", ""
    
    def _extract_memory_from_response(self, response_text: str) -> Tuple[str, str]:
        """
        Извлекает краткосрочную и долгосрочную память из ответа Gemini.
        
        Args:
            response_text: Текст ответа от Gemini
            
        Returns:
            Tuple[str, str]: (краткосрочная_память, долгосрочная_память)
        """
        try:
            lines = response_text.strip().split('\n')
            short_memory = ""
            long_memory = ""
            
            logger.info(f"🧠 Анализирую ответ Gemini: {len(lines)} строк")
            
            for line in lines:
                line = line.strip()
                logger.debug(f"🧠 Строка: '{line}'")
                
                if line.startswith("КРАТКОСРОЧНАЯ:"):
                    short_memory = line.replace("КРАТКОСРОЧНАЯ:", "").strip()
                    logger.info(f"🧠 Найдена краткосрочная память: '{short_memory}'")
                elif line.startswith("ДОЛГОСРОЧНАЯ:"):
                    long_memory = line.replace("ДОЛГОСРОЧНАЯ:", "").strip()
                    logger.info(f"🧠 Найдена долгосрочная память: '{long_memory}'")
            
            # Ограничиваем размер памяти
            short_memory = short_memory[:200] if short_memory else ""
            long_memory = long_memory[:500] if long_memory else ""
            
            logger.info(f"🧠 Итоговая память: краткосрочная ({len(short_memory)} символов), долгосрочная ({len(long_memory)} символов)")
            
            return short_memory, long_memory
            
        except Exception as e:
            logger.error(f"❌ Ошибка извлечения памяти из ответа: {e}")
            return "", ""
    
    async def is_available(self) -> bool:
        """
        Проверяет доступность анализатора памяти.
        
        Returns:
            bool: True если анализатор доступен
        """
        if not self.model:
            return False
        
        try:
            # Простой тест доступности
            async with asyncio.timeout(5.0):
                test_response = await asyncio.to_thread(
                    self.model.generate_content,
                    "Тест доступности"
                )
                return test_response is not None
        except Exception:
            return False
    
    def get_status(self) -> Dict[str, any]:
        """
        Возвращает статус анализатора памяти.
        
        Returns:
            Dict: Статус анализатора
        """
        return {
            "available": self.model is not None,
            "model_name": self.model_name,
            "gemini_configured": bool(self.gemini_api_key)
        }


# Пример использования
if __name__ == "__main__":
    import os
    
    # Тестовый пример
    async def test_memory_analyzer():
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("❌ GEMINI_API_KEY не установлен")
            return
        
        analyzer = MemoryAnalyzer(api_key)
        
        # Тестовый разговор
        user_prompt = "Привет! Меня зовут Сергей, я разработчик на Python. Мне нравится работать с AI и машинным обучением."
        assistant_response = "Привет, Сергей! Очень приятно познакомиться. Python и AI - отличная комбинация! Чем конкретно занимаешься в области машинного обучения?"
        
        short_memory, long_memory = await analyzer.analyze_conversation(
            user_prompt, 
            assistant_response
        )
        
        print(f"🧠 Краткосрочная память: {short_memory}")
        print(f"🧠 Долгосрочная память: {long_memory}")
    
    # Запуск теста
    asyncio.run(test_memory_analyzer())
