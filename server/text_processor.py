import asyncio
import logging
import os
import re
from typing import AsyncGenerator, List

from dotenv import load_dotenv
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_community.tools import GoogleSearchRun
from langchain_community.utilities import GoogleSearchAPIWrapper
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI

# --- Загрузка конфигурации ---
# Вместо прямого вызова Config, используем load_dotenv,
# так как TextProcessor не должен зависеть от всего server.config
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), 'config.env'))

# Проверка наличия всех необходимых ключей API
if not all(k in os.environ for k in ["GOOGLE_API_KEY", "GSEARCH_API_KEY", "GSEARCH_CSE_ID"]):
    raise ValueError("Не найдены необходимые ключи API. Проверьте config.env")

logger = logging.getLogger(__name__)

# --- Определение инструментов ---
# Этот инструмент можно вынести, если он будет использоваться где-то еще
@tool
def get_weather(city: str) -> str:
    """Gets the current weather for a given city. Use only when user asks about weather."""
    logger.info(f"--- Tool: get_weather called for city: {city} ---")
    # Здесь должна быть реальная логика получения погоды
    if "boston" in city.lower():
        return "It's currently sunny in Boston."
    elif "san francisco" in city.lower():
        return "It's currently foggy in San Francisco."
    else:
        return f"Weather data for {city} is not available."

class TextProcessor:
    """
    Обрабатывает текстовые запросы с использованием ИИ-агента,
    который может использовать инструменты (например, Google Search)
    и поддерживает стриминг финального ответа.
    """
    
    def __init__(self):
        try:
            # 1. Инициализация модели
            self.model = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash-lite",
                google_api_key=os.environ["GOOGLE_API_KEY"],
                temperature=0.7,
            )

            # 2. Создание и настройка инструментов
            search_wrapper = GoogleSearchAPIWrapper(
                google_api_key=os.environ["GSEARCH_API_KEY"],
                google_cse_id=os.environ["GSEARCH_CSE_ID"]
            )
            search_tool = GoogleSearchRun(api_wrapper=search_wrapper)
            self.tools = [search_tool, get_weather]

            # 3. Создание промпта для Агента
            prompt_template = ChatPromptTemplate.from_messages(
                [
                    ("system", """
                    You are a helpful voice assistant for macOS. You have access to tools like Google Search.

                    **YOUR CORE RULES:**
                    - For any question that requires current information (news, facts, weather, stock prices, match results), events after 2023, or any information that can change over time, you **MUST** use the `google_search` tool.
                    - **DO NOT** answer such questions from your memory. Always use the search tool first.
                    - If the user asks about the weather, use the `get_weather` tool.
                    - Answer in concise, informative Russian.
                    """),
                    ("human", "{input}"),
                    ("placeholder", "{agent_scratchpad}"),
                ]
            )

            # 4. Создание Агента и его Исполнителя (Executor)
            agent = create_tool_calling_agent(self.model, self.tools, prompt_template)
            self.agent_executor = AgentExecutor(agent=agent, tools=self.tools, verbose=True)
            
            logger.info("✅ TextProcessor с AgentExecutor инициализирован успешно")

        except Exception as e:
            logger.error(f"❌ Ошибка инициализации TextProcessor: {e}", exc_info=True)
            self.agent_executor = None

    async def generate_response_stream(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        """
        Генерирует ответ с помощью агента и стримит финальный результат.
        **kwargs используется для обратной совместимости, но не используется в этой реализации.
        """
        if not self.agent_executor:
            logger.error("AgentExecutor не инициализирован.")
            yield "Извините, произошла ошибка конфигурации ассистента."
            return

        logger.info(f"Запускаю AgentExecutor astream_events для: '{prompt[:50]}...'")
        
        buffer = ""
        sentence_endings = ['.', '!', '?', '...', '?!', '!?']
        is_final_answer_started = False
        
        try:
            # Используем astream_events для получения контроля над потоком
            async for event in self.agent_executor.astream_events({"input": prompt}, version="v1"):
                kind = event["event"]
                
                # Логируем все события для отладки
                logger.debug(f"📡 Событие: {kind} - {event.get('name', 'N/A')}")
                
                # Обрабатываем ответы от инструментов
                if kind == "on_tool_end":
                    tool_name = event.get("name", "unknown")
                    tool_output = event.get("data", {}).get("output", "")
                    logger.info(f"🔧 Инструмент {tool_name} завершил работу")
                    
                    # Если это Google Search, стримим результат
                    if tool_name == "google_search" and tool_output:
                        # Разбиваем результат поиска на предложения
                        sentences = self._split_into_sentences(tool_output)
                        for sentence in sentences:
                            if sentence.strip():
                                logger.info(f"📤 Отправляю результат поиска: '{sentence[:100]}...'")
                                yield sentence.strip()
                
                # Обрабатываем финальный ответ от модели
                elif kind == "on_chat_model_stream":
                    content = event["data"]["chunk"].content
                    if content:
                        buffer += content
                        
                        # Отдаем готовые предложения
                        while True:
                            sentence_end_pos = -1
                            for ending in sentence_endings:
                                pos = buffer.find(ending)
                                if pos != -1:
                                    if sentence_end_pos == -1 or pos < sentence_end_pos:
                                        sentence_end_pos = pos + len(ending)
                            
                            if sentence_end_pos != -1:
                                sentence = buffer[:sentence_end_pos].strip()
                                buffer = buffer[sentence_end_pos:]
                                if sentence:
                                    logger.info(f"📤 Отправляю готовое предложение: '{sentence}'")
                                    yield sentence
                            else:
                                break
            
            # Отправляем остаток из буфера
            if buffer.strip():
                logger.info(f"📤 Отправляю остаток из буфера: '{buffer.strip()}'")
                yield buffer.strip()

        except Exception as e:
            logger.error(f"Ошибка в AgentExecutor stream: {e}", exc_info=True)
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
        
        # Разбиваем на предложения
        sentences = []
        current_sentence = ""
        sentence_endings = ['.', '!', '?', '...', '?!', '!?']
        
        for char in text:
            current_sentence += char
            if char in sentence_endings:
                sentence = current_sentence.strip()
                if sentence:
                    sentences.append(sentence)
                current_sentence = ""
        
        # Добавляем последнее предложение, если оно есть
        if current_sentence.strip():
            sentences.append(current_sentence.strip())
        
        return sentences