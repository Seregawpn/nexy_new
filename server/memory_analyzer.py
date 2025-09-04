"""
MemoryAnalyzer - AI-анализ разговоров для извлечения памяти (ИСПРАВЛЕННАЯ ВЕРСИЯ)

Этот модуль отвечает за анализ диалогов между пользователем и ассистентом
для определения, какую информацию следует сохранить в краткосрочной и
долгосрочной памяти пользователя.
"""

import asyncio
import logging
from typing import Dict, Optional, Tuple
from google import genai

logger = logging.getLogger(__name__)


class MemoryAnalyzer:
    """
    Анализатор памяти для извлечения важной информации из разговоров.
    
    Использует Google Gemini API для анализа диалогов и определения,
    какую информацию следует сохранить в памяти пользователя.
    """
    
    def __init__(self, gemini_api_key: str, model_name: str = "models/gemini-2.5-flash"):
        """
        Инициализация анализатора памяти.
        
        Args:
            gemini_api_key: API ключ для Google Gemini
            model_name: Название модели Gemini для использования (по умолчанию gemini-2.5-flash-lite)
        """
        self.gemini_api_key = gemini_api_key
        self.model_name = model_name
        self.client = None
        
        # Инициализируем Gemini (новый SDK google-genai)
        try:
            self.client = genai.Client(
                http_options={"api_version": "v1beta"},
                api_key=gemini_api_key,
            )
            logger.info(f"✅ MemoryAnalyzer initialized with model {model_name}")
        except Exception as e:
            logger.error(f"❌ MemoryAnalyzer initialization error: {e}")
            self.client = None
    
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
        if not self.client:
            logger.warning("⚠️ Gemini model is not available, returning empty memory")
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
            logger.info(f"🧠 Memory analysis completed:")
            logger.info(f"   Short Memory: {len(short_memory)} characters")
            logger.info(f"   Long Memory: {len(long_memory)} characters")
            
            return short_memory, long_memory
            
        except Exception as e:
            logger.error(f"❌ Conversation analysis error: {e}")
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
            context_part = f"\n\nConversation context:\n{conversation_context}"
        
        return f"""**You are an assistant responsible for managing memory. You have two types of memory: Short Memory and Long Memory.**

**CRITICAL: You MUST ALWAYS respond in this EXACT format:**
```
SHORT MEMORY: [content to save to short memory or "none"]
LONG MEMORY: [content to save to long memory or "none"]
```

**Short Memory** is temporary memory that stores information about the current conversation and recent interactions. It is updated frequently and can be cleared after a period of inactivity.

**Long Memory** is long-term memory that stores only important information about the user, their preferences, habits, and key events.

**You are provided with:**
1. **User's request** — the current request sent by the user.
2. **LLM's response** — the response generated based on the user's request.

**Your task:**
1. Analyze the user's request and the LLM's response.
2. Determine if there is any information that needs to be added to Short Memory and/or Long Memory.
3. **ALWAYS respond in the exact format above.**

**Rules for adding information to memory:**

- **Short Memory:**
  - Current conversation context, temporary preferences, ongoing tasks.
  - Example: "User introduced themselves as Sergei, developer from Moscow"

- **Long Memory:**
  - **Personal data**: Name, surname, nickname, profession, location.
  - **Preferences and habits**: Important likes/dislikes, regular habits.
  - **Important events**: Birthdays, anniversaries, future plans.
  - **Professional data**: Job, skills, work preferences.

**Examples of what goes to Long Memory:**
- "User's name is Sergei"
- "User is a developer from Moscow"
- "User prefers quiet working environments"
- **ALWAYS save personal information like names, professions, locations**
- **ALWAYS save when user introduces themselves**

**What is NOT added to Long Memory:**
- Temporary information (e.g., "Today I want pizza")
- One-time mentions without importance
- General information unrelated to the user

**IMPORTANT: When a user introduces themselves (name, profession, location), this information MUST go to Long Memory as it's essential for personalization!**

**EXAMPLE ANALYSIS:**
If user says "Меня зовут Сергей, я разработчик из Москвы", you MUST respond:
```
SHORT MEMORY: User introduced themselves in Russian
LONG MEMORY: User's name is Sergei, they are a developer from Moscow
```

**REMEMBER: ALWAYS use the exact format with SHORT MEMORY: and LONG MEMORY: labels!**

---

**ACTUAL CONVERSATION TO ANALYZE:**

**User's request:**
{user_prompt}

**LLM's response:**
{assistant_response}

**Now analyze this conversation and respond in the required format.**"""
    
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
                    self.client.models.generate_content,
                    model=self.model_name,
                    contents=analysis_prompt,
                )

                text = getattr(response, "text", None)
                if text:
                    logger.info(f"🧠 Received response from Gemini: {text[:200]}...")
                    return self._extract_memory_from_response(text)
                else:
                    logger.warning("⚠️ Gemini returned empty response")
                    return "", ""

        except asyncio.TimeoutError:
            logger.warning("⏰ Memory analysis timeout (10 sec)")
            return "", ""
        except Exception as e:
            logger.error(f"❌ Gemini call error: {e}")
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
            
            logger.info(f"🧠 Analyzing Gemini response: {len(lines)} lines")
            logger.debug(f"🧠 Full response: {response_text[:500]}...")
            
            for line in lines:
                line = line.strip()
                logger.debug(f"🧠 Line: '{line}'")
                
                # 🔧 Улучшенный парсинг с поддержкой разных форматов
                if line.startswith("SHORT MEMORY:"):
                    short_memory = line.replace("SHORT MEMORY:", "").strip()
                    logger.info(f"🧠 Found short memory: '{short_memory}'")
                elif line.startswith("LONG MEMORY:"):
                    long_memory = line.replace("LONG MEMORY:", "").strip()
                    logger.info(f"🧠 Found long memory: '{long_memory}'")
                # 🔧 Fallback: ищем без двоеточия
                elif line.startswith("SHORT MEMORY"):
                    short_memory = line.replace("SHORT MEMORY", "").strip()
                    if short_memory.startswith(":"):
                        short_memory = short_memory[1:].strip()
                    logger.info(f"🧠 Found short memory (fallback): '{short_memory}'")
                elif line.startswith("LONG MEMORY"):
                    long_memory = line.replace("LONG MEMORY", "").strip()
                    if long_memory.startswith(":"):
                        long_memory = long_memory[1:].strip()
                    logger.info(f"🧠 Found long memory (fallback): '{long_memory}'")
            
            # 🔧 Обработка "none" значений
            if short_memory.lower() == "none":
                short_memory = ""
            if long_memory.lower() == "none":
                long_memory = ""
            
            # Ограничиваем размер памяти
            short_memory = short_memory[:200] if short_memory else ""
            long_memory = long_memory[:500] if long_memory else ""
            
            logger.info(f"🧠 Final memory: short ({len(short_memory)} characters), long ({len(long_memory)} characters)")
            
            return short_memory, long_memory
            
        except Exception as e:
            logger.error(f"❌ Error extracting memory from response: {e}")
            return "", ""
    
    async def is_available(self) -> bool:
        """
        Проверяет доступность анализатора памяти.
        
        Returns:
            bool: True если анализатор доступен
        """
        if not self.client:
            return False
        
        try:
            # Простой тест доступности
            async with asyncio.timeout(5.0):
                test_response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.model_name,
                    contents="Test availability",
                )
                return getattr(test_response, "text", None) is not None
        except Exception:
            return False
    
    def get_status(self) -> Dict[str, any]:
        """
        Возвращает статус анализатора памяти.
        
        Returns:
            Dict: Статус анализатора
        """
        return {
            "available": self.client is not None,
            "model_name": self.model_name,
            "gemini_configured": bool(self.gemini_api_key)
        }


# Пример использования
if __name__ == "__main__":
    import os
    
    # Запуск теста
    # Проверяем доступность API ключа
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY is not set")
    else:
        print("✅ MemoryAnalyzer is ready for real conversation analysis")
        print("📝 Use analyze_conversation() method with actual user prompts and responses")
