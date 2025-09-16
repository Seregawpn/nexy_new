#!/usr/bin/env python3
"""
Тестовый скрипт для проверки VoiceRecognitionIntegration и push-to-talk логики
"""

import asyncio
import time
import sys
from pathlib import Path

# Добавляем путь к модулям
sys.path.append(str(Path(__file__).parent / "client"))

from integration.core.event_bus import EventBus
from integration.core.state_manager import ApplicationStateManager, AppMode
from integration.core.error_handler import ErrorHandler
from integration.integrations.voice_recognition_integration import VoiceRecognitionIntegration, VoiceRecognitionIntegrationConfig

async def test_voice_recognition():
    """Тест VoiceRecognitionIntegration"""
    print("🧪 Тестирование VoiceRecognitionIntegration...")
    
    # Создаем компоненты
    event_bus = EventBus()
    state_manager = ApplicationStateManager()
    error_handler = ErrorHandler()
    
    # Создаем VoiceRecognitionIntegration
    config = VoiceRecognitionIntegrationConfig(
        enabled=True,
        simulation_mode=True,
        simulation_delay=2.0,  # 2 секунды задержки
        simulation_success_rate=1.0,  # 100% успешных распознаваний
        language="en-US"
    )
    
    voice_integration = VoiceRecognitionIntegration(
        event_bus=event_bus,
        state_manager=state_manager,
        error_handler=error_handler,
        config=config
    )
    
    # Инициализируем
    print("🔧 Инициализация...")
    success = await voice_integration.initialize()
    if not success:
        print("❌ Ошибка инициализации")
        return False
    
    # Запускаем
    print("🚀 Запуск...")
    success = await voice_integration.start()
    if not success:
        print("❌ Ошибка запуска")
        return False
    
    print("✅ VoiceRecognitionIntegration запущен")
    
    # Тестируем симуляцию распознавания
    print("\n🎭 Тест 1: Симуляция распознавания")
    session_id = "test-session-001"
    
    # Публикуем событие начала записи
    await event_bus.publish("voice.recording_start", {
        "session_id": session_id,
        "source": "keyboard",
        "timestamp": time.time()
    })
    
    print(f"📤 Отправлено voice.recording_start (сессия: {session_id})")
    print("⏳ Ожидание результата распознавания...")
    
    # Ждем результат
    await asyncio.sleep(3.0)
    
    # Публикуем событие остановки записи
    await event_bus.publish("voice.recording_stop", {
        "session_id": session_id,
        "source": "keyboard",
        "timestamp": time.time()
    })
    
    print(f"📤 Отправлено voice.recording_stop (сессия: {session_id})")
    
    # Ждем еще немного
    await asyncio.sleep(1.0)
    
    # Проверяем статус
    status = voice_integration.get_status()
    print(f"\n📊 Статус: {status}")
    
    # Останавливаем
    print("\n🛑 Остановка...")
    await voice_integration.stop()
    
    print("✅ Тест завершен")
    return True

async def test_push_to_talk_flow():
    """Тест полного push-to-talk цикла"""
    print("\n🧪 Тестирование полного push-to-talk цикла...")
    
    # Создаем компоненты
    event_bus = EventBus()
    state_manager = ApplicationStateManager()
    error_handler = ErrorHandler()
    
    # Создаем VoiceRecognitionIntegration
    config = VoiceRecognitionIntegrationConfig(
        enabled=True,
        simulation_mode=True,
        simulation_delay=1.5,
        simulation_success_rate=0.8,
        language="en-US"
    )
    
    voice_integration = VoiceRecognitionIntegration(
        event_bus=event_bus,
        state_manager=state_manager,
        error_handler=error_handler,
        config=config
    )
    
    # Инициализируем и запускаем
    await voice_integration.initialize()
    await voice_integration.start()
    
    # Подписываемся на события для мониторинга
    events_received = []
    
    async def on_mode_changed(event):
        data = event.get("data", {})
        old_mode = data.get("old_mode")
        new_mode = data.get("new_mode")
        events_received.append(f"mode_changed: {old_mode} -> {new_mode}")
        print(f"🔄 Режим изменен: {old_mode} -> {new_mode}")
    
    async def on_recognition_completed(event):
        data = event.get("data", {})
        session_id = data.get("session_id")
        text = data.get("text")
        events_received.append(f"recognition_completed: {session_id} - '{text}'")
        print(f"✅ Распознавание завершено: {session_id} - '{text}'")
    
    async def on_recognition_failed(event):
        data = event.get("data", {})
        session_id = data.get("session_id")
        error = data.get("error")
        events_received.append(f"recognition_failed: {session_id} - {error}")
        print(f"❌ Распознавание неуспешно: {session_id} - {error}")
    
    # Подписываемся на события
    await event_bus.subscribe("app.mode_changed", on_mode_changed)
    await event_bus.subscribe("voice.recognition_completed", on_recognition_completed)
    await event_bus.subscribe("voice.recognition_failed", on_recognition_failed)
    
    # Симулируем push-to-talk
    print("\n🎯 Симуляция push-to-talk:")
    print("1. Нажатие пробела (PRESS) -> LISTENING")
    
    # Начальное состояние
    state_manager.set_mode(AppMode.SLEEPING)
    print(f"   Начальное состояние: {state_manager.get_current_mode()}")
    
    # Нажатие пробела
    session_id = "ptt-test-001"
    await event_bus.publish("voice.recording_start", {
        "session_id": session_id,
        "source": "keyboard",
        "timestamp": time.time()
    })
    
    # Переключаем в LISTENING
    state_manager.set_mode(AppMode.LISTENING)
    print(f"   После нажатия: {state_manager.get_current_mode()}")
    
    # Ждем распознавание
    print("2. Ожидание распознавания...")
    await asyncio.sleep(2.0)
    
    # Отпускание пробела
    print("3. Отпускание пробела (RELEASE)")
    await event_bus.publish("voice.recording_stop", {
        "session_id": session_id,
        "source": "keyboard",
        "timestamp": time.time()
    })
    
    # Ждем финальное состояние
    print("4. Ожидание финального состояния...")
    await asyncio.sleep(1.0)
    
    print(f"   Финальное состояние: {state_manager.get_current_mode()}")
    
    # Выводим все события
    print("\n📋 Полученные события:")
    for event in events_received:
        print(f"   - {event}")
    
    # Останавливаем
    await voice_integration.stop()
    
    print("✅ Push-to-talk тест завершен")
    return True

async def main():
    """Главная функция тестирования"""
    print("🚀 Запуск тестов VoiceRecognitionIntegration\n")
    
    try:
        # Тест 1: Базовая функциональность
        success1 = await test_voice_recognition()
        
        # Тест 2: Push-to-talk цикл
        success2 = await test_push_to_talk_flow()
        
        if success1 and success2:
            print("\n🎉 Все тесты прошли успешно!")
            return True
        else:
            print("\n❌ Некоторые тесты не прошли")
            return False
            
    except Exception as e:
        print(f"\n💥 Ошибка во время тестирования: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(main())
