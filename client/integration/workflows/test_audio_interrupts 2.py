#!/usr/bin/env python3
"""
Тест единого состояния прерываний аудио
Проверяет, что все способы прерывания ведут к одинаковому результату
"""

import asyncio
import logging
import sys
from pathlib import Path

# Добавляем пути для импортов
sys.path.append(str(Path(__file__).parent.parent.parent))

from integration.core.event_bus import EventBus, EventPriority

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AudioInterruptTester:
    """Тестер единого состояния прерываний аудио"""
    
    def __init__(self):
        self.event_bus = EventBus()
        self.events_received = []
        self.interrupt_methods = []
        
    async def setup(self):
        """Настройка тестера"""
        print("🔧 Настройка тестера прерываний аудио...")
        
        # Подписываемся на ЕДИНЫЙ канал прерываний для мониторинга
        await self.event_bus.subscribe("playback.cancelled", self._on_unified_interrupt, EventPriority.HIGH)
        
        # Мониторим входящие события (до обработки)
        await self.event_bus.subscribe("keyboard.short_press", self._on_input_event, EventPriority.LOW)
        await self.event_bus.subscribe("interrupt.request", self._on_input_event, EventPriority.LOW)
        
        print("✅ Тестер настроен")
    
    async def _on_unified_interrupt(self, event):
        """Мониторинг ЕДИНОГО канала прерывания"""
        data = event.get("data", {})
        source = data.get("source", "unknown")
        reason = data.get("reason", "unknown")
        
        self.events_received.append("playback.cancelled")
        print(f"✅ ЕДИНЫЙ канал: playback.cancelled (source={source}, reason={reason})")
    
    async def _on_input_event(self, event):
        """Мониторинг входящих событий"""
        event_type = event.get("type", "unknown")
        print(f"📥 Входящее событие: {event_type}")
    
    async def test_keyboard_interrupt(self):
        """Тест прерывания через клавиатуру"""
        print("\n🎹 === ТЕСТ ПРЕРЫВАНИЯ ЧЕРЕЗ КЛАВИАТУРУ ===")
        
        # Симулируем воспроизведение
        print("1. Симулируем начало воспроизведения...")
        await self.event_bus.publish("playback.started", {
            "session_id": "keyboard_test",
            "audio_format": "pcm_s16le"
        })
        
        await asyncio.sleep(0.1)
        
        # Симулируем прерывание клавиатурой
        print("2. Симулируем keyboard.short_press...")
        await self.event_bus.publish("keyboard.short_press", {
            "session_id": "keyboard_test",
            "reason": "user_interrupt"
        })
        
        await asyncio.sleep(0.1)
        
        self.interrupt_methods.append({
            "method": "keyboard.short_press", 
            "events": self.events_received.copy()
        })
        self.events_received.clear()
        
        print("✅ Тест клавиатурного прерывания завершен")
    
    async def test_workflow_interrupt(self):
        """Тест прерывания через ProcessingWorkflow"""
        print("\n⚙️ === ТЕСТ ПРЕРЫВАНИЯ ЧЕРЕЗ WORKFLOW ===")
        
        # Симулируем воспроизведение
        print("1. Симулируем начало воспроизведения...")
        await self.event_bus.publish("playback.started", {
            "session_id": "workflow_test",
            "audio_format": "pcm_s16le"
        })
        
        await asyncio.sleep(0.1)
        
        # Симулируем прерывание от ProcessingWorkflow (через единый канал)
        print("2. Симулируем playback.cancelled от ProcessingWorkflow...")
        await self.event_bus.publish("playback.cancelled", {
            "session_id": "workflow_test",
            "reason": "user_interrupt",
            "source": "processing_workflow"
        })
        
        await asyncio.sleep(0.1)
        
        self.interrupt_methods.append({
            "method": "processing_workflow",
            "events": self.events_received.copy()
        })
        self.events_received.clear()
        
        print("✅ Тест workflow прерывания завершен")
    
    async def test_general_interrupt(self):
        """Тест общего прерывания"""
        print("\n🛑 === ТЕСТ ОБЩЕГО ПРЕРЫВАНИЯ ===")
        
        # Симулируем воспроизведение
        print("1. Симулируем начало воспроизведения...")
        await self.event_bus.publish("playback.started", {
            "session_id": "general_test",
            "audio_format": "pcm_s16le"
        })
        
        await asyncio.sleep(0.1)
        
        # Симулируем общее прерывание
        print("2. Симулируем interrupt.request...")
        await self.event_bus.publish("interrupt.request", {
            "session_id": "general_test",
            "scope": "playback",
            "reason": "user_interrupt"
        })
        
        await asyncio.sleep(0.1)
        
        self.interrupt_methods.append({
            "method": "interrupt.request",
            "events": self.events_received.copy()
        })
        self.events_received.clear()
        
        print("✅ Тест общего прерывания завершен")
    
    async def analyze_consistency(self):
        """Анализ единообразия прерываний"""
        print("\n📊 === АНАЛИЗ ЕДИНООБРАЗИЯ ПРЕРЫВАНИЙ ===")
        
        if not self.interrupt_methods:
            print("❌ Нет данных для анализа")
            return False
        
        # Проверяем, что все методы приводят к одинаковому результату
        first_result = self.interrupt_methods[0]["events"]
        consistent = True
        
        print(f"Эталонный результат ({self.interrupt_methods[0]['method']}):")
        for event in first_result:
            print(f"  - {event}")
        
        print("\nСравнение с другими методами:")
        for method_data in self.interrupt_methods[1:]:
            method_name = method_data["method"]
            method_events = method_data["events"]
            
            print(f"\n{method_name}:")
            for event in method_events:
                print(f"  - {event}")
            
            if set(method_events) != set(first_result):
                print(f"  ❌ НЕСООТВЕТСТВИЕ с эталоном!")
                consistent = False
            else:
                print(f"  ✅ Соответствует эталону")
        
        print(f"\n{'✅ ЕДИНООБРАЗИЕ ДОСТИГНУТО' if consistent else '❌ ЕДИНООБРАЗИЕ НЕ ДОСТИГНУТО'}")
        return consistent
    
    async def run_all_tests(self):
        """Запуск всех тестов"""
        try:
            print("🧪 ТЕСТИРОВАНИЕ ЕДИНОГО СОСТОЯНИЯ ПРЕРЫВАНИЙ АУДИО")
            print("=" * 60)
            
            await self.setup()
            
            # Запускаем тесты разных способов прерывания
            await self.test_keyboard_interrupt()
            await self.test_workflow_interrupt()
            await self.test_general_interrupt()
            
            # Анализируем единообразие
            consistent = await self.analyze_consistency()
            
            print("\n📋 === ИТОГОВЫЙ ОТЧЕТ ===")
            print(f"Протестировано методов прерывания: {len(self.interrupt_methods)}")
            print(f"Единообразие результатов: {'✅ ДА' if consistent else '❌ НЕТ'}")
            
            if consistent:
                print("\n🎉 ВСЕ ПРЕРЫВАНИЯ РАБОТАЮТ ЕДИНООБРАЗНО!")
                print("Пользователь получит одинаковый опыт независимо от способа прерывания.")
            else:
                print("\n⚠️ ОБНАРУЖЕНЫ РАЗЛИЧИЯ В ПРЕРЫВАНИЯХ!")
                print("Необходимо унифицировать обработку прерываний.")
            
            return consistent
            
        except Exception as e:
            print(f"❌ Ошибка в тестах: {e}")
            import traceback
            traceback.print_exc()
            return False

async def main():
    """Главная функция"""
    print("🎧 ТЕСТИРОВАНИЕ ЕДИНОГО СОСТОЯНИЯ ПРЕРЫВАНИЙ АУДИО")
    print("=" * 70)
    
    tester = AudioInterruptTester()
    success = await tester.run_all_tests()
    
    if success:
        print("\n🎯 Прерывания аудио работают единообразно!")
        return True
    else:
        print("\n⚠️ Требуется доработка единообразия прерываний!")
        return False

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n⚠️ Тестирование прервано пользователем")
        exit(1)
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
