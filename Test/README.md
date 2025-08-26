# 🤖 Gemini Live API Ассистент

## 🎯 **Описание проекта**

Этот ассистент использует **Google Gemini Live API** для создания интеллектуального помощника, который может:
- 📸 **Анализировать скриншоты экрана** в реальном времени
- 🔍 **Выполнять онлайн поиск** через Google Search
- 💬 **Обрабатывать текстовые запросы** с поддержкой контекста
- 🚀 **Автоматически выбирать режим работы** в зависимости от запроса

## 🚀 **Быстрый старт**

### **1. Установка зависимостей**
```bash
pip install -r requirements.txt
```

### **2. Настройка API ключа**
```bash
export GEMINI_API_KEY="your_api_key_here"
```

### **3. Запуск**
```bash
./run.sh
# или
python main.py
```

## 🔧 **Как это работает**

### **Автоматический выбор режима:**
- **"новости" или "поиск"** → Google Search (без скриншота)
- **Остальные запросы** → Скриншот + анализ изображения

### **Примеры использования:**
```
"расскажи последние новости"           → Google Search
"что происходит в мире сегодня"         → Google Search
"опиши что на экране"                  → Скриншот + анализ
"что я вижу на мониторе"               → Скриншот + анализ
```

## 📋 **Структура проекта**

```
Test/
├── main.py              # Основной файл ассистента
├── requirements.txt     # Зависимости
├── run.sh              # Скрипт запуска
├── README.md           # Эта документация
└── STATUS.md           # Статус проекта
```

## 🔍 **Функциональность**

### **Google Search:**
- Автоматически активируется при упоминании ключевых слов
- Получает актуальную информацию в реальном времени
- Поддерживает любые поисковые запросы

### **Анализ скриншотов:**
- Автоматический захват экрана
- Оптимизация размера и качества изображения
- Отправка в Gemini API для анализа

### **Умная обработка:**
- Автоматическое определение типа запроса
- Fallback стратегии при ошибках
- Асинхронная обработка для высокой производительности

## ⚠️ **Требования**

- **Python 3.8+**
- **GEMINI_API_KEY** - API ключ Google Gemini
- **Зависимости:** `google-genai`, `pillow`, `mss`

## 🚨 **Устранение неполадок**

### **Ошибка "GEMINI_API_KEY not found":**
```bash
export GEMINI_API_KEY="your_api_key_here"
```

### **Ошибка "Object not JSON serializable":**
- Проверьте, что используете `raw_bytes` для изображений
- Убедитесь в правильном формате `types.Part.from_bytes()`

### **Медленная работа:**
- Скриншоты: ~100-500ms
- API вызовы: ~1-3 секунды
- Google Search: ~2-5 секунд

## 🔮 **Возможности расширения**

- **Дополнительные инструменты** (Calendar, Gmail, Drive API)
- **Мультимодальность** (аудио, видео, документы)
- **Интеграции** (Slack, Discord, Telegram, веб-интерфейс)

## 🔌 **Интеграция в другие проекты**

### **1. Минимальная интеграция**
```python
from google import genai
from google.genai import types

# Конфигурация
config = types.LiveConnectConfig(
    response_modalities=["TEXT"],
    tools=[types.Tool(google_search=types.GoogleSearch())]
)

# Клиент
client = genai.Client(
    http_options={"api_version": "v1beta"},
    api_key=os.environ.get("GEMINI_API_KEY"),
)

# Использование
async with client.aio.live.connect(model="models/gemini-2.5-flash-live-preview", config=config) as session:
    # Ваш код здесь
```

### **2. Добавление в существующий проект**
```bash
# 1. Установить зависимости
pip install google-genai pillow mss

# 2. Добавить переменную окружения
export GEMINI_API_KEY="your_key"

# 3. Импортировать и использовать
from main import ScreenAssistant

assistant = ScreenAssistant()
# Ваша логика
```

### **3. Готовые примеры интеграции**

#### **Flask Web API:**
```python
from flask import Flask, request, jsonify
import asyncio
from main import ScreenAssistant

app = Flask(__name__)

@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.json
    query = data.get('query', '')
    
    result = asyncio.run(analyze_with_gemini(query))
    return jsonify({'result': result})

async def analyze_with_gemini(query):
    assistant = ScreenAssistant()
    await assistant.connect()
    await assistant.send_message_with_screenshot(query)
    response = await assistant.receive_response()
    await assistant.close()
    return response
```

#### **Discord Bot:**
```python
import discord
from discord.ext import commands
from main import ScreenAssistant

bot = commands.Bot(command_prefix='!', intents=discord.Intents.default())

@bot.command()
async def analyze(ctx, *, query):
    await ctx.send("🔍 Анализирую...")
    assistant = ScreenAssistant()
    await assistant.connect()
    await assistant.send_message_with_screenshot(query)
    response = await assistant.receive_response()
    await ctx.send(f"📊 Результат:\n{response}")
    await assistant.close()

bot.run('YOUR_TOKEN')
```

#### **CLI Tool:**
```python
#!/usr/bin/env python3
import asyncio
from main import ScreenAssistant

async def main():
    query = input("Введите запрос: ")
    assistant = ScreenAssistant()
    await assistant.connect()
    await assistant.send_message_with_screenshot(query)
    response = await assistant.receive_response()
    print(f"Результат: {response}")
    await assistant.close()

if __name__ == "__main__":
    asyncio.run(main())
```

### **4. Кастомные инструменты**
```python
# Добавление своих инструментов
tools=[
    types.Tool(google_search=types.GoogleSearch()),
    types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name="custom_function",
                description="Описание функции",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "param1": types.Schema(type=types.Type.STRING)
                    }
                )
            )
        ]
    )
]
```

### **5. Обработка ошибок и fallback**
```python
class GeminiErrorHandler:
    @staticmethod
    async def send_with_fallback(session, query, screenshot=None):
        try:
            if screenshot:
                # Пытаемся отправить скриншот + текст
                await session.send_client_content(...)
            else:
                # Fallback на текстовый режим
                await session.send_client_content(...)
        except Exception as e:
            print(f"Ошибка: {e}")
            # Переключаемся на текстовый режим
            await session.send_client_content(...)
```

### **6. Чек-лист интеграции**
- [ ] **Установлены зависимости** (`google-genai`, `pillow`, `mss`)
- [ ] **Настроен API ключ** (`GEMINI_API_KEY`)
- [ ] **Скопирован базовый код** конфигурации
- [ ] **Добавлен захват скриншотов** (если нужно)
- [ ] **Реализована обработка ошибок**
- [ ] **Протестировано подключение**
- [ ] **Добавлен в ваш проект**

### **7. Частые ошибки и решения**

| Ошибка | Решение |
|--------|---------|
| `GEMINI_API_KEY not found` | `export GEMINI_API_KEY="your_key"` |
| `Object not JSON serializable` | Используйте `raw_bytes`, не `base64` |
| `Model not found` | Используйте `models/gemini-2.5-flash-live-preview` |
| `Invalid input` | Проверьте формат `types.Content` |

## 📚 **Дополнительная информация**

Подробная техническая документация и примеры интеграции доступны в файле `STATUS.md`.

## 🎉 **Готово к использованию!**

Ваш ассистент полностью функционален и готов к работе. Используйте его для анализа экрана и поиска информации!
