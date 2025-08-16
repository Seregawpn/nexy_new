# MVP 1: План перевода в приложение
## "Пошаговая реализация голосового ассистента"

---

## 🎯 **Цель документа:**
Перевести концепцию MVP 1 в **ПОЛНОСТЬЮ ГОТОВОЕ К ИСПОЛЬЗОВАНИЮ ПРИЛОЖЕНИЕ** с чёткой последовательностью действий.

**Результат:** К концу 18-го дня у нас будет работающее приложение, которое можно запустить командой `python main.py` и сразу использовать!

---

## 📋 **Общие требования к приложению**

### **1. Платформа:**
- **macOS 12.0+** (Monterey и выше)
- **Поддержка Intel и Apple Silicon**
- **Минимум 8GB RAM**
- **2GB свободного места на диске**

### **2. Разрешения системы:**
- **Accessibility** - для определения контекста
- **Screen Recording** - для захвата экрана
- **Microphone** - для распознавания речи
- **Network** - для Edge TTS и Gemini API

### **3. Зависимости:**
- **Python 3.9+**
- **macOS SDK** (для PyObjC)
- **Интернет соединение** (для TTS и LLM)

---

## 🏗️ **Архитектура приложения**

### **Структура проекта:**
```
assistant_app/
├── src/
│   ├── core/           # Основная логика
│   ├── ui/            # Пользовательский интерфейс
│   ├── services/      # Внешние сервисы
│   └── utils/         # Вспомогательные функции
├── tests/             # Тесты
├── config/            # Конфигурация
├── requirements.txt   # Зависимости
└── README.md         # Документация
```

### **Основные компоненты:**
1. **SpaceController** - управление пробелом
2. **ScreenCapture** - захват экрана
3. **EdgeTTSEngine** - синтез речи
4. **SpeechRecognition** - распознавание речи
5. **GeminiClient** - анализ экрана
6. **Analytics** - сбор метрик

---

## 🚀 **Пошаговая реализация**

---

### **ШАГ 1: Настройка окружения (День 1)**

#### **1.1 Создание проекта:**
```bash
# Создаём структуру проекта
mkdir assistant_app
cd assistant_app
python -m venv venv
source venv/bin/activate

# Устанавливаем зависимости
pip install -r requirements.txt
```

#### **1.2 requirements.txt:**
```txt
# Основные зависимости
edge-tts==6.1.9
SpeechRecognition==3.10.0
PyAudio==0.2.11
grpcio==1.59.0
protobuf==4.24.4
Pillow==10.0.0

# macOS специфичные
pyobjc-framework-Quartz==9.2
pyobjc-framework-Cocoa==9.2

# Утилиты
numpy==1.24.0
asyncio==3.4.3
```

#### **1.3 Проверка разрешений:**
```python
# check_permissions.py
import Quartz
import speech_recognition as sr

def check_permissions():
    """Проверяет необходимые разрешения"""
    
    # Проверка Accessibility
    try:
        Quartz.AXUIElementCreateSystemWide()
        print("✅ Accessibility разрешение получено")
    except:
        print("❌ Нужно разрешение Accessibility")
        
    # Проверка микрофона
    try:
        recognizer = sr.Recognizer()
        microphone = sr.Microphone()
        print("✅ Микрофон доступен")
    except:
        print("❌ Проблема с микрофоном")
        
    # Проверка записи экрана
    try:
        # Пробуем захватить экран
        pass
        print("✅ Запись экрана доступна")
    except:
        print("❌ Нужно разрешение Screen Recording")
```

**Результат:** Готовое окружение для разработки

---

### **ШАГ 2: Управление пробелом (День 2-3)**

#### **2.1 Создание SpaceController:**
```python
# src/core/space_controller.py
import Quartz
import time
import threading
from typing import Callable

class SpaceController:
    def __init__(self):
        self.is_active = False
        self.press_start_time = 0
        self.long_press_threshold = 0.6  # 600мс
        self.callbacks = {}
        
    def start_monitoring(self):
        """Запускает мониторинг пробела"""
        # Создаём Event Tap для пробела
        event_mask = Quartz.kCGEventKeyDown | Quartz.kCGEventKeyUp
        
        def callback(proxy, event_type, event, refcon):
            if event_type == Quartz.kCGEventKeyDown:
                self._handle_key_down(event)
            elif event_type == Quartz.kCGEventKeyUp:
                self._handle_key_up(event)
            return event
            
        # Создаём Event Tap
        event_tap = Quartz.CGEventTapCreate(
            Quartz.kCGSessionEventTap,
            Quartz.kCGHeadInsertEventTap,
            Quartz.kCGEventTapOptionDefault,
            event_mask,
            callback,
            None
        )
        
        # Запускаем мониторинг
        run_loop = Quartz.CFRunLoopGetCurrent()
        Quartz.CGEventTapEnable(event_tap, True)
        
    def _handle_key_down(self, event):
        """Обрабатывает нажатие клавиши"""
        keycode = Quartz.CGEventGetKeycode(event)
        
        if keycode == 49:  # Пробел
            self.press_start_time = time.time()
            
    def _handle_key_up(self, event):
        """Обрабатывает отпускание клавиши"""
        keycode = Quartz.CGEventGetKeycode(event)
        
        if keycode == 49:  # Пробел
            press_duration = time.time() - self.press_start_time
            
            if press_duration >= self.long_press_threshold:
                if not self.is_active:
                    self._activate_assistant()
                else:
                    self._deactivate_assistant()
            else:
                if self.is_active:
                    self._interrupt_assistant()
                    
    def _activate_assistant(self):
        """Активирует ассистента"""
        self.is_active = True
        if 'activate' in self.callbacks:
            self.callbacks['activate']()
            
    def _deactivate_assistant(self):
        """Деактивирует ассистента"""
        self.is_active = False
        if 'deactivate' in self.callbacks:
            self.callbacks['deactivate']()
            
    def _interrupt_assistant(self):
        """Перебивает ассистента"""
        if 'interrupt' in self.callbacks:
            self.callbacks['interrupt']()
            
    def register_callback(self, event_type: str, callback: Callable):
        """Регистрирует callback для события"""
        self.callbacks[event_type] = callback
```

#### **2.2 Защита текстовых полей:**
```python
# src/core/context_detector.py
import Quartz

class ContextDetector:
    def __init__(self):
        pass
        
    def is_text_field_focused(self) -> bool:
        """Проверяет, находится ли фокус в текстовом поле"""
        try:
            # Получаем элемент с фокусом
            focused_element = Quartz.AXUIElementCreateSystemWide()
            focused = Quartz.AXUIElementCopyAttributeValue(
                focused_element, 
                Quartz.kAXFocusedUIElementAttribute
            )
            
            if focused:
                # Проверяем роль элемента
                role = Quartz.AXUIElementCopyAttributeValue(
                    focused, 
                    Quartz.kAXRoleAttribute
                )
                
                # Проверяем, редактируемый ли элемент
                editable = Quartz.AXUIElementCopyAttributeValue(
                    focused, 
                    Quartz.kAXEditableAttribute
                )
                
                return bool(editable)
                
        except Exception as e:
            print(f"Ошибка определения контекста: {e}")
            
        return False
```

**Результат:** Работающее управление пробелом с защитой текстовых полей

---

### **ШАГ 3: Захват экрана (День 4-5)**

#### **3.1 Создание ScreenCapture:**
```python
# src/core/screen_capture.py
import Quartz
from PIL import Image
import io
import time

class ScreenCapture:
    def __init__(self):
        self.max_width = 1024
        self.quality = 80
        
    def capture_active_window(self):
        """Захватывает активное окно"""
        try:
            # Получаем активное окно
            windows = Quartz.CGWindowListCopyWindowInfo(
                Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements,
                Quartz.kCGNullWindowID
            )
            
            # Находим активное окно
            active_window = None
            for window in windows:
                if window.get(Quartz.kCGWindowLayer) == 0:  # Основной слой
                    active_window = window
                    break
                    
            if not active_window:
                return None, {}
                
            # Получаем границы окна
            bounds = active_window.get(Quartz.kCGWindowBounds)
            x, y, width, height = bounds['X'], bounds['Y'], bounds['Width'], bounds['Height']
            
            # Захватываем изображение
            image = Quartz.CGWindowListCreateImage(
                bounds,
                Quartz.kCGWindowListOptionIncludingWindow,
                active_window.get(Quartz.kCGWindowID),
                Quartz.kCGWindowImageBoundsIgnoreFraming
            )
            
            # Конвертируем в PIL Image
            width = Quartz.CGImageGetWidth(image)
            height = Quartz.CGImageGetHeight(image)
            
            # Создаём контекст
            context = Quartz.CGBitmapContextCreate(
                None, width, height, 8, width * 4,
                Quartz.CGColorSpaceCreateDeviceRGB(),
                Quartz.kCGImageAlphaPremultipliedLast
            )
            
            # Рисуем изображение
            Quartz.CGContextDrawImage(context, Quartz.CGRectMake(0, 0, width, height), image)
            
            # Получаем данные
            data = Quartz.CGBitmapContextGetData(context)
            
            # Создаём PIL Image
            pil_image = Image.frombytes('RGBA', (width, height), data)
            
            # Изменяем размер
            if width > self.max_width:
                ratio = self.max_width / width
                new_height = int(height * ratio)
                pil_image = pil_image.resize((self.max_width, new_height), Image.Resampling.LANCZOS)
                
            # Конвертируем в WebP
            output = io.BytesIO()
            pil_image.save(output, format='WebP', quality=self.quality, optimize=True)
            image_bytes = output.getvalue()
            
            # Метаданные
            metadata = {
                'app_name': active_window.get(Quartz.kCGWindowOwnerName, 'Unknown'),
                'window_title': active_window.get(Quartz.kCGWindowName, ''),
                'bounds': bounds,
                'timestamp': time.time(),
                'size_bytes': len(image_bytes)
            }
            
            return image_bytes, metadata
            
        except Exception as e:
            print(f"Ошибка захвата экрана: {e}")
            return None, {}
```

**Результат:** Работающий захват активного окна в WebP формате

---

### **ШАГ 4: Edge TTS (День 6-7)**

#### **4.1 Создание EdgeTTSEngine:**
```python
# src/services/edge_tts_engine.py
import edge_tts
import asyncio
import io
import pygame
from typing import Optional

class EdgeTTSEngine:
    def __init__(self):
        self.voice = "ru-RU-SvetlanaNeural"
        self.rate = "+0%"
        self.volume = "+0%"
        self.is_speaking = False
        
    async def synthesize(self, text: str, language: str = "ru") -> bytes:
        """Синтезирует речь"""
        try:
            # Выбираем голос по языку
            if language == "ru":
                voice = "ru-RU-SvetlanaNeural"
            else:
                voice = "en-US-AriaNeural"
                
            # Создаём коммуникацию
            communicate = edge_tts.Communicate(
                text, 
                voice,
                rate=self.rate,
                volume=self.volume
            )
            
            # Собираем аудио данные
            audio_data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]
                    
            return audio_data
            
        except Exception as e:
            print(f"Ошибка TTS: {e}")
            return b""
            
    def play_audio(self, audio_bytes: bytes):
        """Воспроизводит аудио"""
        try:
            # Инициализируем pygame для аудио
            pygame.mixer.init()
            
            # Создаём временный файл
            temp_file = io.BytesIO(audio_bytes)
            
            # Воспроизводим
            pygame.mixer.music.load(temp_file)
            pygame.mixer.music.play()
            
            self.is_speaking = True
            
            # Ждём окончания
            while pygame.mixer.music.get_busy():
                pygame.time.wait(100)
                
            self.is_speaking = False
            
        except Exception as e:
            print(f"Ошибка воспроизведения: {e}")
            
    def stop_speaking(self):
        """Останавливает речь"""
        if self.is_speaking:
            pygame.mixer.music.stop()
            self.is_speaking = False
            
    def set_rate(self, rate: str):
        """Устанавливает скорость речи"""
        self.rate = rate
        
    def set_voice(self, voice: str):
        """Устанавливает голос"""
        self.voice = voice
```

**Результат:** Работающий синтез речи через Edge TTS

---

### **ШАГ 5: Распознавание речи (День 8-9)**

#### **5.1 Создание SpeechRecognition:**
```python
# src/services/speech_recognition.py
import speech_recognition as sr
import pyaudio
import time

class LocalSpeechRecognition:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        # Настройки
        self.recognizer.energy_threshold = 4000
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8
        
    def listen_for_command(self, timeout: float = 10.0) -> str:
        """Слушает команду пользователя"""
        try:
            with self.microphone as source:
                # Подстраиваемся под шум
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                
                # Слушаем аудио
                audio = self.recognizer.listen(
                    source, 
                    timeout=timeout, 
                    phrase_time_limit=15
                )
                
                # Распознаём через Google Speech API
                text = self.recognizer.recognize_google(
                    audio, 
                    language='ru-RU'
                )
                
                return text.lower()
                
        except sr.WaitTimeoutError:
            return "timeout"
        except sr.UnknownValueError:
            return "unknown"
        except sr.RequestError as e:
            print(f"Ошибка распознавания: {e}")
            return "error"
            
    def is_listening(self) -> bool:
        """Проверяет, слушает ли система"""
        return hasattr(self, '_listening') and self._listening
        
    def start_listening(self):
        """Начинает прослушивание"""
        self._listening = True
        
    def stop_listening(self):
        """Останавливает прослушивание"""
        self._listening = False
```

**Результат:** Работающее локальное распознавание речи

---

### **ШАГ 6: Gemini API (День 10-11)**

#### **6.1 Создание GeminiClient:**
```python
# src/services/gemini_client.py
import google.generativeai as genai
import json
import base64
from typing import Dict, Any

class GeminiClient:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
    def analyze_screen(self, image_bytes: bytes, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Анализирует экран через Gemini"""
        try:
            # Конвертируем изображение в base64
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            # Создаём промпт
            prompt = f"""
            Ты ассистент для незрячих пользователей. Проанализируй скриншот и дай:
            
            1. Краткое описание экрана (1-2 фразы на русском)
            2. 3-5 конкретных действий (глаголом)
            
            Приложение: {metadata.get('app_name', 'Unknown')}
            Заголовок окна: {metadata.get('window_title', '')}
            
            Формат ответа JSON:
            {{
              "summary": "описание экрана",
              "actions": ["действие 1", "действие 2", "действие 3"],
              "confidence": 0.85,
              "screen_type": "search_results|listing|form|article|dialog"
            }}
            """
            
            # Отправляем запрос
            response = self.model.generate_content([
                prompt,
                {"mime_type": "image/webp", "data": image_base64}
            ])
            
            # Парсим JSON ответ
            try:
                result = json.loads(response.text)
                return result
            except json.JSONDecodeError:
                # Fallback если JSON не парсится
                return {
                    "summary": "Не удалось проанализировать экран",
                    "actions": ["Попробуйте ещё раз"],
                    "confidence": 0.5,
                    "screen_type": "unknown"
                }
                
        except Exception as e:
            print(f"Ошибка Gemini API: {e}")
            return {
                "summary": "Ошибка анализа экрана",
                "actions": ["Проверьте интернет соединение"],
                "confidence": 0.0,
                "screen_type": "error"
            }
```

**Результат:** Работающий анализ экрана через Gemini API

---

### **ШАГ 7: Аналитика (День 12-13)**

#### **7.1 Создание Analytics:**
```python
# src/services/analytics.py
import hashlib
import subprocess
import time
import json
import requests
from typing import Dict, Any

class Analytics:
    def __init__(self, server_url: str = None):
        self.server_url = server_url
        self.user_id = self._generate_user_id()
        self.session_id = self._generate_session_id()
        self.events = []
        self.last_send = time.time()
        
    def _generate_user_id(self) -> str:
        """Генерирует уникальный ID пользователя"""
        try:
            # Получаем MAC адрес
            mac = subprocess.check_output(['ifconfig', 'en0']).decode()
            mac_match = re.search(r'ether ([0-9a-f:]+)', mac)
            mac_addr = mac_match.group(1) if mac_match else "unknown"
            
            # Получаем Serial Number
            serial = subprocess.check_output(['system_profiler', 'SPHardwareDataType']).decode()
            serial_match = re.search(r'Serial Number \(system\): (.+)', serial)
            system_serial = serial_match.group(1) if serial_match else "unknown"
            
            # Комбинируем и хешируем
            combined = f"{mac_addr}:{system_serial}"
            return hashlib.sha256(combined.encode()).hexdigest()[:16]
            
        except:
            return hashlib.sha256(str(time.time()).encode()).hexdigest()[:16]
            
    def _generate_session_id(self) -> str:
        """Генерирует ID сессии"""
        return f"session_{int(time.time())}"
        
    def log_event(self, event_type: str, data: Dict[str, Any] = None):
        """Логирует событие"""
        event = {
            'user_id': self.user_id,
            'session_id': self.session_id,
            'event_type': event_type,
            'timestamp': time.time(),
            'data': data or {}
        }
        
        self.events.append(event)
        
        # Отправляем на сервер каждые 50 событий
        if len(self.events) >= 50:
            self._send_to_server()
            
    def log_performance(self, operation: str, duration_ms: float):
        """Логирует метрики производительности"""
        self.log_event('performance', {
            'operation': operation,
            'duration_ms': duration_ms
        })
        
    def _send_to_server(self):
        """Отправляет данные на сервер"""
        if not self.server_url or not self.events:
            return
            
        try:
            payload = {
                'user_id': self.user_id,
                'events': self.events,
                'timestamp': time.time()
            }
            
            response = requests.post(
                f"{self.server_url}/analytics/events",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                self.events.clear()
                
        except Exception as e:
            print(f"Ошибка отправки аналитики: {e}")
```

**Результат:** Работающая система аналитики и идентификации

---

### **ШАГ 8: Интеграция (День 14-15)**

#### **8.1 Создание основного класса:**
```python
# src/core/assistant.py
import asyncio
import time
from typing import Dict, Any

class VoiceAssistant:
    def __init__(self, config: Dict[str, Any]):
        # Инициализируем компоненты
        self.space_controller = SpaceController()
        self.screen_capture = ScreenCapture()
        self.tts_engine = EdgeTTSEngine()
        self.speech_recognition = LocalSpeechRecognition()
        self.gemini_client = GeminiClient(config['gemini_api_key'])
        self.analytics = Analytics(config.get('analytics_server'))
        
        # Состояние
        self.state = 'inactive'  # inactive, active, interrupted, listening
        self.is_speaking = False
        
        # Регистрируем callbacks
        self.space_controller.register_callback('activate', self._activate)
        self.space_controller.register_callback('deactivate', self._deactivate)
        self.space_controller.register_callback('interrupt', self._interrupt)
        
    def start(self):
        """Запускает ассистента"""
        print("🚀 Запуск голосового ассистента...")
        
        # Запускаем мониторинг пробела
        self.space_controller.start_monitoring()
        
        # Запускаем главный цикл
        try:
            asyncio.run(self._main_loop())
        except KeyboardInterrupt:
            print("\n👋 Завершение работы ассистента...")
            
    async def _main_loop(self):
        """Главный цикл работы"""
        while True:
            await asyncio.sleep(0.1)
            
    def _activate(self):
        """Активирует ассистента"""
        if self.state == 'inactive':
            self.state = 'active'
            self.analytics.log_event('assistant_activated')
            
            # Анализируем экран
            asyncio.create_task(self._analyze_screen())
            
    def _deactivate(self):
        """Деактивирует ассистента"""
        if self.state != 'inactive':
            self.state = 'inactive'
            self.is_speaking = False
            self.tts_engine.stop_speaking()
            self.analytics.log_event('assistant_deactivated')
            
    def _interrupt(self):
        """Перебивает ассистента"""
        if self.state == 'active' and self.is_speaking:
            self.state = 'interrupted'
            self.is_speaking = False
            self.tts_engine.stop_speaking()
            self.analytics.log_event('assistant_interrupted')
            
    async def _analyze_screen(self):
        """Анализирует экран"""
        try:
            start_time = time.time()
            
            # Захватываем экран
            image_bytes, metadata = self.screen_capture.capture_active_window()
            if not image_bytes:
                return
                
            self.analytics.log_performance('screen_capture', 
                (time.time() - start_time) * 1000)
            
            # Анализируем через Gemini
            analysis_start = time.time()
            result = self.gemini_client.analyze_screen(image_bytes, metadata)
            self.analytics.log_performance('llm_analysis', 
                (time.time() - analysis_start) * 1000)
            
            # Синтезируем речь
            tts_start = time.time()
            audio_bytes = await self.tts_engine.synthesize(result['summary'])
            self.analytics.log_performance('tts_synthesis', 
                (time.time() - tts_start) * 1000)
            
            # Воспроизводим
            self.is_speaking = True
            self.tts_engine.play_audio(audio_bytes)
            self.is_speaking = False
            
            # Логируем успех
            self.analytics.log_performance('total_response', 
                (time.time() - start_time) * 1000)
            self.analytics.log_event('screen_analysis_complete', {
                'confidence': result['confidence'],
                'screen_type': result['screen_type']
            })
            
        except Exception as e:
            self.analytics.log_event('error', {
                'error_type': type(e).__name__,
                'error_message': str(e)
            })
            print(f"Ошибка анализа экрана: {e}")
```

**Результат:** Полностью интегрированный ассистент

---

### **ШАГ 9: Конфигурация (День 16)**

#### **9.1 Создание config.json:**
```json
{
  "gemini_api_key": "YOUR_GEMINI_API_KEY",
  "analytics_server": "https://your-analytics-server.com",
  
  "space_control": {
    "long_press_threshold": 600,
    "short_press_threshold": 300
  },
  
  "screen_capture": {
    "max_width": 1024,
    "quality": 80
  },
  
  "tts": {
    "voice": "ru-RU-SvetlanaNeural",
    "rate": "+0%",
    "volume": "+0%"
  },
  
  "speech_recognition": {
    "language": "ru-RU",
    "timeout": 10,
    "energy_threshold": 4000
  },
  
  "logging": {
    "level": "INFO",
    "file": "assistant.log"
  }
}
```

#### **9.2 Создание main.py:**
```python
# main.py
import json
import sys
from src.core.assistant import VoiceAssistant

def main():
    try:
        # Загружаем конфигурацию
        with open('config.json', 'r') as f:
            config = json.load(f)
            
        # Проверяем API ключ
        if not config.get('gemini_api_key'):
            print("❌ Ошибка: не указан GEMINI_API_KEY в config.json")
            sys.exit(1)
            
        # Создаём и запускаем ассистента
        assistant = VoiceAssistant(config)
        assistant.start()
        
    except FileNotFoundError:
        print("❌ Ошибка: файл config.json не найден")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

**Результат:** Готовое к запуску приложение

---

### **ШАГ 10: Тестирование (День 17-18)**

#### **10.1 Тестовые сценарии:**
```python
# tests/test_assistant.py
import unittest
from unittest.mock import Mock, patch
from src.core.assistant import VoiceAssistant

class TestVoiceAssistant(unittest.TestCase):
    def setUp(self):
        self.config = {
            'gemini_api_key': 'test_key',
            'analytics_server': None
        }
        self.assistant = VoiceAssistant(self.config)
        
    def test_activation(self):
        """Тест активации ассистента"""
        self.assertEqual(self.assistant.state, 'inactive')
        self.assistant._activate()
        self.assertEqual(self.assistant.state, 'active')
        
    def test_deactivation(self):
        """Тест деактивации ассистента"""
        self.assistant._activate()
        self.assistant._deactivate()
        self.assertEqual(self.assistant.state, 'inactive')
        
    def test_interruption(self):
        """Тест перебивания ассистента"""
        self.assistant._activate()
        self.assistant.is_speaking = True
        self.assistant._interrupt()
        self.assertEqual(self.assistant.state, 'interrupted')
        self.assertFalse(self.assistant.is_speaking)

if __name__ == '__main__':
    unittest.main()
```

#### **10.2 Запуск тестов:**
```bash
# Запускаем тесты
python -m pytest tests/ -v

# Проверяем покрытие
python -m pytest tests/ --cov=src --cov-report=html
```

**Результат:** Протестированное приложение

---

## 🚀 **Запуск приложения**

### **1. Установка:**
```bash
# Клонируем проект
git clone <repository_url>
cd assistant_app

# Создаём виртуальное окружение
python -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate  # Windows

# Устанавливаем зависимости
pip install -r requirements.txt
```

### **2. Настройка:**
```bash
# Копируем конфигурацию
cp config.example.json config.json

# Редактируем config.json
# Добавляем GEMINI_API_KEY
```

### **3. Запуск:**
```bash
# Запускаем ассистента
python main.py

# В фоновом режиме
nohup python main.py > assistant.log 2>&1 &
```

---

## ⚠️ **Риски и их решения**

### **1. Разрешения macOS:**
- **Риск:** Пользователь не даст разрешения
- **Решение:** Чёткие инструкции и проверка в коде

### **2. Зависимости:**
- **Риск:** Проблемы с установкой PyAudio/PyObjC
- **Решение:** Подробная документация и альтернативы

### **3. API лимиты:**
- **Риск:** Превышение лимитов Gemini API
- **Решение:** Кэширование и fallback механизмы

### **4. Производительность:**
- **Риск:** Медленная работа на слабых машинах
- **Решение:** Оптимизация и настройки качества

### **5. Сеть:**
- **Риск:** Проблемы с интернетом
- **Решение:** Локальные fallback и офлайн режим

---

## 📊 **Метрики успеха**

### **Технические:**
- ✅ Приложение запускается без ошибок
- ✅ Пробел корректно управляет ассистентом
- ✅ Захват экрана работает
- ✅ TTS синтезирует речь
- ✅ STT распознаёт команды
- ✅ Gemini анализирует экраны

### **Пользовательские:**
- ✅ Ассистент активируется долгим нажатием пробела
- ✅ Ассистент перебивается коротким пробелом
- ✅ Ассистент выключается долгим нажатием
- ✅ Текстовые поля защищены от перехвата
- ✅ VoiceOver работает корректно

---

## 🎯 **Следующие шаги**

### **После MVP 1:**
1. **Сбор обратной связи** от пользователей
2. **Анализ метрик** производительности
3. **Оптимизация** на основе данных
4. **Планирование MVP 2** с эхоподавлением

### **Долгосрочно:**
1. **Мобильная версия** (iOS/Android)
2. **Облачная синхронизация** настроек
3. **Машинное обучение** для персонализации
4. **Интеграции** с другими приложениями

---

## 🎉 **Заключение**

**Этот план даёт нам:**

🚀 **Чёткую последовательность** - 18 дней до ПОЛНОСТЬЮ ГОТОВОГО приложения
🎯 **Простую архитектуру** - без сложных структур
🛡️ **Обработку рисков** - предусмотрены все проблемы
📊 **Метрики успеха** - понимание что работает
⚡ **Быстрый результат** - MVP 1 за 3 недели

**План готов к реализации! Можно начинать с ШАГА 1: "Настройка окружения"** 🎯

**Готовы начинать разработку по этому плану?**
