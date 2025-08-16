# MVP 1: Пошаговый план разработки
## "От простого к сложному - каждый шаг увеличивает ценность"

---

## 🎯 **Принцип разработки:**

**Каждый шаг = маленький MVP, который можно протестировать и показать**

**Цель:** Постепенно увеличивать ценность продукта, тестируя каждый этап

---

## 📋 **Общая структура проекта:**

```
assistant_app/
├── src/
│   ├── core/           # Основная логика
│   ├── services/       # Внешние сервисы
│   └── utils/          # Вспомогательные функции
├── tests/              # Тесты для каждого шага
├── config/             # Конфигурация
├── requirements.txt    # Зависимости
└── main.py            # Точка входа
```

---

## 🚀 **ПОШАГОВЫЙ ПЛАН РАЗРАБОТКИ**

---

### **ШАГ 1: Базовая структура и Event Tap (День 1-2)**
**Ценность:** Демонстрация работы с системными событиями macOS

#### **Что делаем:**
```python
# src/core/event_monitor.py
import Quartz
import time

class EventMonitor:
    def __init__(self):
        self.is_running = False
        
    def start_monitoring(self):
        """Запускает мониторинг событий"""
        print("🎯 Мониторинг событий запущен")
        print("📝 Нажмите любую клавишу для теста")
        
        # Создаём Event Tap для всех клавиш
        event_mask = Quartz.kCGEventKeyDown
        
        def callback(proxy, event_type, event, refcon):
            keycode = Quartz.CGEventGetKeycode(event)
            print(f"🔑 Нажата клавиша с кодом: {keycode}")
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
        Quartz.CGEventTapEnable(event_tap, True)
        
        # Держим программу запущенной
        run_loop = Quartz.CFRunLoopGetCurrent()
        Quartz.CFRunLoopRun()
```

#### **Тест:**
```bash
# Запуск
python src/core/event_monitor.py

# Ожидаемый результат:
# 🎯 Мониторинг событий запущен
# 📝 Нажмите любую клавишу для теста
# 🔑 Нажата клавиша с кодом: 49 (пробел)
# 🔑 Нажата клавиша с кодом: 0 (A)
```

#### **Риски:**
- ❌ **macOS разрешения** - Event Tap требует Accessibility
- ❌ **PyObjC установка** - может быть сложной
- ❌ **Права администратора** - для некоторых операций

#### **Результат:** 
✅ **Работающий Event Tap** - можем перехватывать нажатия клавиш

---

### **ШАГ 2: Управление пробелом (День 3-4)**
**Ценность:** Демонстрация умного управления через пробел

#### **Что делаем:**
```python
# src/core/space_controller.py
import Quartz
import time

class SpaceController:
    def __init__(self):
        self.press_start_time = 0
        self.long_press_threshold = 0.6  # 600мс
        self.is_active = False
        
    def start_monitoring(self):
        """Запускает мониторинг пробела"""
        print("🎯 Мониторинг пробела запущен")
        print("📝 Долгое нажатие пробела → активация")
        print("📝 Короткий пробел → перебивание")
        
        event_mask = Quartz.kCGEventKeyDown | Quartz.kCGEventKeyUp
        
        def callback(proxy, event_type, event, refcon):
            keycode = Quartz.CGEventGetKeycode(event)
            
            if keycode == 49:  # Пробел
                if event_type == Quartz.kCGEventKeyDown:
                    self.press_start_time = time.time()
                    print("🔽 Пробел нажат")
                elif event_type == Quartz.kCGEventKeyUp:
                    press_duration = time.time() - self.press_start_time
                    print(f"🔼 Пробел отпущен (длительность: {press_duration:.2f}с)")
                    
                    if press_duration >= self.long_press_threshold:
                        if not self.is_active:
                            self._activate()
                        else:
                            self._deactivate()
                    else:
                        if self.is_active:
                            self._interrupt()
                            
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
        
        Quartz.CGEventTapEnable(event_tap, True)
        run_loop = Quartz.CFRunLoopGetCurrent()
        Quartz.CFRunLoopRun()
        
    def _activate(self):
        """Активирует ассистента"""
        self.is_active = True
        print("🚀 Ассистент АКТИВИРОВАН!")
        
    def _deactivate(self):
        """Деактивирует ассистента"""
        self.is_active = False
        print("⏹️ Ассистент ВЫКЛЮЧЕН!")
        
    def _interrupt(self):
        """Перебивает ассистента"""
        print("⏸️ Ассистент ПЕРЕБИТ!")
```

#### **Тест:**
```bash
# Запуск
python src/core/space_controller.py

# Тестируем:
# 1. Долгое нажатие пробела (600мс+) → "Ассистент АКТИВИРОВАН!"
# 2. Короткий пробел → "Ассистент ПЕРЕБИТ!"
# 3. Ещё раз долгое нажатие → "Ассистент ВЫКЛЮЧЕН!"
```

#### **Риски:**
- ❌ **Точность таймера** - может быть неточным
- ❌ **Конфликт с текстом** - пробел в текстовых полях
- ❌ **VoiceOver** - может конфликтовать

#### **Результат:** 
✅ **Умное управление пробелом** - долгий/короткий нажим работают

---

### **ШАГ 3: Захват экрана (День 5-6)**
**Ценность:** Демонстрация возможности "видеть" что на экране

#### **Что делаем:**
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
            print("📸 Захватываю активное окно...")
            
            # Получаем активное окно
            windows = Quartz.CGWindowListCopyWindowInfo(
                Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements,
                Quartz.kCGNullWindowID
            )
            
            # Находим активное окно
            active_window = None
            for window in windows:
                if window.get(Quartz.kCGWindowLayer) == 0:
                    active_window = window
                    break
                    
            if not active_window:
                print("❌ Не удалось найти активное окно")
                return None, {}
                
            # Получаем информацию об окне
            app_name = active_window.get(Quartz.kCGWindowOwnerName, 'Unknown')
            window_title = active_window.get(Quartz.kCGWindowName, '')
            
            print(f"📱 Приложение: {app_name}")
            print(f"📝 Заголовок: {window_title}")
            
            # Захватываем изображение
            bounds = active_window.get(Quartz.kCGWindowBounds)
            image = Quartz.CGWindowListCreateImage(
                bounds,
                Quartz.kCGWindowListOptionIncludingWindow,
                active_window.get(Quartz.kCGWindowID),
                Quartz.kCGWindowImageBoundsIgnoreFraming
            )
            
            # Конвертируем в PIL Image
            width = Quartz.CGImageGetWidth(image)
            height = Quartz.CGImageGetHeight(image)
            
            print(f"🖼️ Размер окна: {width}x{height}")
            
            # Создаём контекст и получаем данные
            context = Quartz.CGBitmapContextCreate(
                None, width, height, 8, width * 4,
                Quartz.CGColorSpaceCreateDeviceRGB(),
                Quartz.kCGImageAlphaPremultipliedLast
            )
            
            Quartz.CGContextDrawImage(context, Quartz.CGRectMake(0, 0, width, height), image)
            data = Quartz.CGBitmapContextGetData(context)
            
            # Создаём PIL Image
            pil_image = Image.frombytes('RGBA', (width, height), data)
            
            # Изменяем размер если нужно
            if width > self.max_width:
                ratio = self.max_width / width
                new_height = int(height * ratio)
                pil_image = pil_image.resize((self.max_width, new_height), Image.Resampling.LANCZOS)
                print(f"🔄 Изменён размер до: {self.max_width}x{new_height}")
                
            # Конвертируем в WebP
            output = io.BytesIO()
            pil_image.save(output, format='WebP', quality=self.quality, optimize=True)
            image_bytes = output.getvalue()
            
            print(f"💾 Размер файла: {len(image_bytes)} байт")
            
            # Метаданные
            metadata = {
                'app_name': app_name,
                'window_title': window_title,
                'bounds': bounds,
                'timestamp': time.time(),
                'size_bytes': len(image_bytes)
            }
            
            print("✅ Захват экрана завершён успешно!")
            return image_bytes, metadata
            
        except Exception as e:
            print(f"❌ Ошибка захвата экрана: {e}")
            return None, {}
            
    def save_screenshot(self, image_bytes, filename="screenshot.webp"):
        """Сохраняет скриншот в файл"""
        try:
            with open(filename, 'wb') as f:
                f.write(image_bytes)
            print(f"💾 Скриншот сохранён: {filename}")
        except Exception as e:
            print(f"❌ Ошибка сохранения: {e}")
```

#### **Тест:**
```bash
# Запуск
python src/core/screen_capture.py

# Ожидаемый результат:
# 📸 Захватываю активное окно...
# 📱 Приложение: Safari
# 📝 Заголовок: Google - Safari
# 🖼️ Размер окна: 1440x900
# 🔄 Изменён размер до: 1024x640
# 💾 Размер файла: 45678 байт
# ✅ Захват экрана завершён успешно!
# 💾 Скриншот сохранён: screenshot.webp
```

#### **Риски:**
- ❌ **Screen Recording разрешение** - macOS требует
- ❌ **Права доступа** - к активным окнам
- ❌ **Размер изображения** - может быть очень большим

#### **Результат:** 
✅ **Работающий захват экрана** - можем "видеть" что на экране

---

### **ШАГ 4: Edge TTS (День 7-8)**
**Ценность:** Демонстрация "говорящего" ассистента

#### **Что делаем:**
```python
# src/services/edge_tts_engine.py
import edge_tts
import asyncio
import pygame
import io
import time

class EdgeTTSEngine:
    def __init__(self):
        self.voice = "ru-RU-SvetlanaNeural"
        self.rate = "+0%"
        self.volume = "+0%"
        self.is_speaking = False
        
    async def test_voices(self):
        """Тестирует доступные голоса"""
        print("🎤 Тестирую доступные голоса...")
        
        voices = ["ru-RU-SvetlanaNeural", "en-US-AriaNeural"]
        
        for voice in voices:
            print(f"🔊 Тестирую голос: {voice}")
            
            try:
                communicate = edge_tts.Communicate(
                    "Привет! Это тест голоса.", 
                    voice,
                    rate=self.rate,
                    volume=self.volume
                )
                
                # Собираем аудио
                audio_data = b""
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_data += chunk["data"]
                        
                print(f"✅ Голос {voice} работает! Размер: {len(audio_data)} байт")
                
                # Воспроизводим
                await self.play_audio(audio_data)
                
            except Exception as e:
                print(f"❌ Ошибка с голосом {voice}: {e}")
                
    async def play_audio(self, audio_bytes):
        """Воспроизводит аудио"""
        try:
            print("🔊 Воспроизвожу аудио...")
            
            # Инициализируем pygame
            pygame.mixer.init()
            
            # Создаём временный файл
            temp_file = io.BytesIO(audio_bytes)
            
            # Воспроизводим
            pygame.mixer.music.load(temp_file)
            pygame.mixer.music.play()
            
            self.is_speaking = True
            print("🎵 Аудио воспроизводится...")
            
            # Ждём окончания
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.1)
                
            self.is_speaking = False
            print("✅ Воспроизведение завершено")
            
        except Exception as e:
            print(f"❌ Ошибка воспроизведения: {e}")
            
    def stop_speaking(self):
        """Останавливает речь"""
        if self.is_speaking:
            pygame.mixer.music.stop()
            self.is_speaking = False
            print("⏹️ Воспроизведение остановлено")

async def main():
    """Тестируем TTS"""
    tts = EdgeTTSEngine()
    await tts.test_voices()

if __name__ == "__main__":
    asyncio.run(main())
```

#### **Тест:**
```bash
# Запуск
python src/services/edge_tts_engine.py

# Ожидаемый результат:
# 🎤 Тестирую доступные голоса...
# 🔊 Тестирую голос: ru-RU-SvetlanaNeural
# ✅ Голос ru-RU-SvetlanaNeural работает! Размер: 12345 байт
# 🔊 Воспроизвожу аудио...
# 🎵 Аудио воспроизводится...
# ✅ Воспроизведение завершено
# 🔊 Тестирую голос: en-US-AriaNeural
# ✅ Голос en-US-AriaNeural работает! Размер: 12345 байт
# 🔊 Воспроизвожу аудио...
# 🎵 Аудио воспроизводится...
# ✅ Воспроизведение завершено
```

#### **Риски:**
- ❌ **Интернет соединение** - Edge TTS требует сеть
- ❌ **PyAudio установка** - может быть сложной
- ❌ **Аудио драйверы** - проблемы с воспроизведением

#### **Результат:** 
✅ **Говорящий ассистент** - можем синтезировать речь

---

### **ШАГ 5: Распознавание речи (День 9-10)**
**Ценность:** Демонстрация "понимающего" ассистента

#### **Что делаем:**
```python
# src/services/speech_recognition.py
import speech_recognition as sr
import time

class SpeechRecognition:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        # Настройки
        self.recognizer.energy_threshold = 4000
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8
        
    def test_microphone(self):
        """Тестирует микрофон"""
        print("🎤 Тестирую микрофон...")
        
        try:
            with self.microphone as source:
                print("🔊 Подстраиваюсь под шум...")
                self.recognizer.adjust_for_ambient_noise(source, duration=2)
                
                print("✅ Микрофон готов!")
                print(f"📊 Порог энергии: {self.recognizer.energy_threshold}")
                
        except Exception as e:
            print(f"❌ Ошибка микрофона: {e}")
            
    def listen_for_command(self, timeout=10):
        """Слушает команду"""
        print("👂 Слушаю команду...")
        print("💬 Скажите что-нибудь!")
        
        try:
            with self.microphone as source:
                # Слушаем аудио
                audio = self.recognizer.listen(
                    source, 
                    timeout=timeout, 
                    phrase_time_limit=15
                )
                
                print("🎵 Аудио получено, распознаю...")
                
                # Распознаём через Google Speech API
                text = self.recognizer.recognize_google(
                    audio, 
                    language='ru-RU'
                )
                
                print(f"✅ Распознано: '{text}'")
                return text.lower()
                
        except sr.WaitTimeoutError:
            print("⏰ Таймаут ожидания речи")
            return "timeout"
        except sr.UnknownValueError:
            print("❓ Речь не распознана")
            return "unknown"
        except sr.RequestError as e:
            print(f"🌐 Ошибка API: {e}")
            return "error"
            
    def test_recognition(self):
        """Тестирует распознавание"""
        print("🧪 Тестирую распознавание речи...")
        
        # Тестируем микрофон
        self.test_microphone()
        
        # Тестируем распознавание
        print("\n🎯 Тест 1: Скажите 'Привет'")
        result1 = self.listen_for_command(15)
        
        print(f"\n🎯 Тест 2: Скажите 'Как дела'")
        result2 = self.listen_for_command(15)
        
        # Результаты
        print("\n📊 Результаты тестирования:")
        print(f"Тест 1: {result1}")
        print(f"Тест 2: {result2}")
        
        if result1 not in ["timeout", "unknown", "error"] and result2 not in ["timeout", "unknown", "error"]:
            print("🎉 Все тесты прошли успешно!")
        else:
            print("⚠️ Некоторые тесты не прошли")

def main():
    """Тестируем распознавание речи"""
    recognition = SpeechRecognition()
    recognition.test_recognition()

if __name__ == "__main__":
    main()
```

#### **Тест:**
```bash
# Запуск
python src/services/speech_recognition.py

# Ожидаемый результат:
# 🧪 Тестирую распознавание речи...
# 🎤 Тестирую микрофон...
# 🔊 Подстраиваюсь под шум...
# ✅ Микрофон готов!
# 📊 Порог энергии: 4000
# 
# 🎯 Тест 1: Скажите 'Привет'
# 👂 Слушаю команду...
# 💬 Скажите что-нибудь!
# 🎵 Аудио получено, распознаю...
# ✅ Распознано: 'привет'
# 
# 🎯 Тест 2: Скажите 'Как дела'
# 👂 Слушаю команду...
# 💬 Скажите что-нибудь!
# 🎵 Аудио получено, распознаю...
# ✅ Распознано: 'как дела'
# 
# 📊 Результаты тестирования:
# Тест 1: привет
# Тест 2: как дела
# 🎉 Все тесты прошли успешно!
```

#### **Риски:**
- ❌ **Микрофон разрешения** - macOS требует
- ❌ **Интернет соединение** - Google Speech API
- ❌ **Качество аудио** - шум, эхо

#### **Результат:** 
✅ **Понимающий ассистент** - можем распознавать речь

---

### **ШАГ 6: Gemini API (День 11-12)**
**Ценность:** Демонстрация "умного" анализа экранов

#### **Что делаем:**
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
        
    def test_connection(self):
        """Тестирует соединение с Gemini"""
        print("🧠 Тестирую соединение с Gemini...")
        
        try:
            # Простой тест
            response = self.model.generate_content("Скажи 'Привет' на русском")
            print(f"✅ Соединение работает! Ответ: {response.text}")
            return True
        except Exception as e:
            print(f"❌ Ошибка соединения: {e}")
            return False
            
    def analyze_screen(self, image_bytes: bytes, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Анализирует экран через Gemini"""
        try:
            print("🔍 Анализирую экран через Gemini...")
            
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
            
            print("📤 Отправляю запрос в Gemini...")
            
            # Отправляем запрос
            response = self.model.generate_content([
                prompt,
                {"mime_type": "image/webp", "data": image_base64}
            ])
            
            print("📥 Получен ответ от Gemini")
            
            # Парсим JSON ответ
            try:
                result = json.loads(response.text)
                print("✅ Анализ завершён успешно!")
                print(f"📝 Описание: {result.get('summary', 'N/A')}")
                print(f"🎯 Действия: {result.get('actions', [])}")
                return result
            except json.JSONDecodeError:
                print("⚠️ JSON не парсится, использую fallback")
                return {
                    "summary": "Не удалось проанализировать экран",
                    "actions": ["Попробуйте ещё раз"],
                    "confidence": 0.5,
                    "screen_type": "unknown"
                }
                
        except Exception as e:
            print(f"❌ Ошибка Gemini API: {e}")
            return {
                "summary": "Ошибка анализа экрана",
                "actions": ["Проверьте интернет соединение"],
                "confidence": 0.0,
                "screen_type": "error"
            }
            
    def test_with_screenshot(self, image_path: str):
        """Тестирует анализ с реальным скриншотом"""
        print(f"🧪 Тестирую анализ с файлом: {image_path}")
        
        try:
            # Читаем изображение
            with open(image_path, 'rb') as f:
                image_bytes = f.read()
                
            print(f"📸 Изображение загружено: {len(image_bytes)} байт")
            
            # Метаданные
            metadata = {
                'app_name': 'Test App',
                'window_title': 'Test Window'
            }
            
            # Анализируем
            result = self.analyze_screen(image_bytes, metadata)
            
            # Выводим результат
            print("\n📊 Результат анализа:")
            print(f"Описание: {result['summary']}")
            print(f"Действия: {result['actions']}")
            print(f"Уверенность: {result['confidence']}")
            print(f"Тип экрана: {result['screen_type']}")
            
        except Exception as e:
            print(f"❌ Ошибка тестирования: {e}")

def main():
    """Тестируем Gemini API"""
    import os
    
    # Проверяем API ключ
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("❌ Ошибка: не указан GEMINI_API_KEY")
        print("Установите: export GEMINI_API_KEY='your_key'")
        return
        
    client = GeminiClient(api_key)
    
    # Тестируем соединение
    if client.test_connection():
        print("\n🎯 Тестирую анализ экрана...")
        
        # Если есть скриншот для теста
        if os.path.exists('screenshot.webp'):
            client.test_with_screenshot('screenshot.webp')
        else:
            print("📸 Создайте скриншот командой:")
            print("python src/core/screen_capture.py")

if __name__ == "__main__":
    main()
```

#### **Тест:**
```bash
# Устанавливаем API ключ
export GEMINI_API_KEY='your_key_here'

# Запуск
python src/services/gemini_client.py

# Ожидаемый результат:
# 🧠 Тестирую соединение с Gemini...
# ✅ Соединение работает! Ответ: Привет
# 
# 🎯 Тестирую анализ экрана...
# 🧪 Тестирую анализ с файлом: screenshot.webp
# 📸 Изображение загружено: 45678 байт
# 🔍 Анализирую экран через Gemini...
# 📤 Отправляю запрос в Gemini...
# 📥 Получен ответ от Gemini
# ✅ Анализ завершён успешно!
# 📝 Описание: Страница поиска Google
# 🎯 Действия: ['ввести запрос', 'нажать поиск', 'выбрать результат']
# 
# 📊 Результат анализа:
# Описание: Страница поиска Google
# Действия: ['ввести запрос', 'нажать поиск', 'выбрать результат']
# Уверенность: 0.85
# Тип экрана: search_results
```

#### **Риски:**
- ❌ **API ключ** - нужно получить и настроить
- ❌ **Интернет соединение** - Gemini требует сеть
- ❌ **API лимиты** - может быть ограничений
- ❌ **Размер изображения** - может быть слишком большим

#### **Результат:** 
✅ **Умный анализ экранов** - можем понимать что на экране

---

### **ШАГ 7: Интеграция компонентов (День 13-14)**
**Ценность:** Демонстрация работающего ассистента

#### **Что делаем:**
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
        self.speech_recognition = SpeechRecognition()
        self.gemini_client = GeminiClient(config['gemini_api_key'])
        
        # Состояние
        self.state = 'inactive'
        self.is_speaking = False
        
        print("🚀 Голосовой ассистент инициализирован!")
        
    def start(self):
        """Запускает ассистента"""
        print("🎯 Запуск ассистента...")
        print("📝 Управление:")
        print("  🔽 Долгое нажатие пробела → активация")
        print("  🔽 Короткий пробел → перебивание")
        print("  🔽 Долгое нажатие (когда активен) → выключение")
        
        # Запускаем мониторинг пробела
        self.space_controller.start_monitoring()
        
    def _activate(self):
        """Активирует ассистента"""
        if self.state == 'inactive':
            self.state = 'active'
            print("🚀 Ассистент АКТИВИРОВАН!")
            
            # Анализируем экран
            asyncio.create_task(self._analyze_screen())
            
    def _deactivate(self):
        """Деактивирует ассистента"""
        if self.state != 'inactive':
            self.state = 'inactive'
            self.is_speaking = False
            self.tts_engine.stop_speaking()
            print("⏹️ Ассистент ВЫКЛЮЧЕН!")
            
    def _interrupt(self):
        """Перебивает ассистента"""
        if self.state == 'active' and self.is_speaking:
            self.state = 'interrupted'
            self.is_speaking = False
            self.tts_engine.stop_speaking()
            print("⏸️ Ассистент ПЕРЕБИТ!")
            
    async def _analyze_screen(self):
        """Анализирует экран"""
        try:
            print("📸 Захватываю экран...")
            
            # Захватываем экран
            image_bytes, metadata = self.screen_capture.capture_active_window()
            if not image_bytes:
                print("❌ Не удалось захватить экран")
                return
                
            print("🧠 Анализирую через Gemini...")
            
            # Анализируем через Gemini
            result = self.gemini_client.analyze_screen(image_bytes, metadata)
            
            print("🔊 Синтезирую речь...")
            
            # Синтезируем речь
            audio_bytes = await self.tts_engine.synthesize(result['summary'])
            
            print("🎵 Воспроизвожу ответ...")
            
            # Воспроизводим
            self.is_speaking = True
            await self.tts_engine.play_audio(audio_bytes)
            self.is_speaking = False
            
            print("✅ Анализ экрана завершён!")
            
        except Exception as e:
            print(f"❌ Ошибка анализа экрана: {e}")
```

#### **Тест:**
```bash
# Запуск
python src/core/assistant.py

# Ожидаемый результат:
# 🚀 Голосовой ассистент инициализирован!
# 🎯 Запуск ассистента...
# 📝 Управление:
#   🔽 Долгое нажатие пробела → активация
#   🔽 Короткий пробел → перебивание
#   🔽 Долгое нажатие (когда активен) → выключение
# 
# Тестируем:
# 1. Долгое нажатие пробела → "Ассистент АКТИВИРОВАН!"
# 2. Автоматически: "📸 Захватываю экран..."
# 3. "🧠 Анализирую через Gemini..."
# 4. "🔊 Синтезирую речь..."
# 5. "🎵 Воспроизводится ответ..."
# 6. "✅ Анализ экрана завершён!"
```

#### **Риски:**
- ❌ **Синхронизация компонентов** - могут работать не вместе
- ❌ **Обработка ошибок** - если один компонент падает
- ❌ **Производительность** - может быть медленно

#### **Результат:** 
✅ **Работающий ассистент** - все компоненты работают вместе

---

### **ШАГ 8: Финальная настройка и тестирование (День 15-18)**
**Ценность:** Готовое к использованию приложение

#### **Что делаем:**

##### **День 15: Конфигурация**
```python
# config.json
{
  "gemini_api_key": "YOUR_GEMINI_API_KEY",
  
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
  }
}
```

##### **День 16: Точка входа**
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

##### **Дни 17-18: Тестирование**
```python
# tests/test_assistant.py
import unittest
from unittest.mock import Mock, patch
from src.core.assistant import VoiceAssistant

class TestVoiceAssistant(unittest.TestCase):
    def setUp(self):
        self.config = {
            'gemini_api_key': 'test_key'
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

#### **Тест:**
```bash
# 1. Настройка
cp config.example.json config.json
# Редактируем config.json - добавляем GEMINI_API_KEY

# 2. Запуск
python main.py

# 3. Тестирование
python -m pytest tests/ -v

# 4. Финальный тест
# - Активация долгим нажатием пробела
# - Анализ экрана
# - Воспроизведение ответа
# - Перебивание коротким пробелом
# - Выключение долгим нажатием
```

#### **Риски:**
- ❌ **Конфигурация** - неправильные настройки
- ❌ **API ключи** - неверные или просроченные
- ❌ **Системные требования** - несовместимость

#### **Результат:** 
✅ **ГОТОВОЕ ПРИЛОЖЕНИЕ** - можно использовать!

---

## 📊 **Метрики успеха для каждого шага:**

### **ШАГ 1-2:** Event Tap работает
### **ШАГ 3:** Можем захватывать экраны
### **ШАГ 4:** Ассистент может говорить
### **ШАГ 5:** Ассистент может слушать
### **ШАГ 6:** Ассистент может анализировать
### **ШАГ 7:** Все компоненты работают вместе
### **ШАГ 8:** Готовое приложение

---

## 🎯 **Преимущества пошагового подхода:**

✅ **Каждый шаг можно протестировать**
✅ **Каждый шаг увеличивает ценность**
✅ **Легко найти и исправить проблемы**
✅ **Можно показать прогресс на каждом этапе**
✅ **Минимизация рисков**

---

## 🚀 **Готовы начинать с ШАГА 1?**

**Каждый шаг = маленький MVP, который можно протестировать и показать!**

**Начинаем с "Базовая структура и Event Tap"?** 🎯
