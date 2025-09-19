#!/usr/bin/env python3
"""
Полный тест единого состояния прерываний аудио
Включает реальную SpeechPlaybackIntegration
"""

import asyncio
import logging
import sys
from pathlib import Path

# Добавляем пути для импортов
sys.path.append(str(Path(__file__).parent.parent.parent))

from integration.core.event_bus import EventBus, EventPriority
from integration.core.state_manager import ApplicationStateManager
from integration.core.error_handler import ErrorHandler
from integration.integrations.speech_playback_integration import SpeechPlaybackIntegration

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class UnifiedInterruptTester:
    """Полный тестер единого состояния прерываний"""
    
    def __init__(self):
        self.event_bus = EventBus()
        self.state_manager = ApplicationStateManager()
        self.error_handler = ErrorHandler(self.event_bus)
        
        # Реальная интеграция
        self.speech_integration = SpeechPlaybackIntegration(
            event_bus=self.event_bus,
            state_manager=self.state_manager,
            error_handler=self.error_handler
        )
        
        # Мониторинг
        self.unified_interrupts = []
        self.input_events = []
        
    async def setup(self):
        """Настройка тестера"""
        print("🔧 Настройка полного тестера прерываний...")
        
        # Инициализируем интеграцию
        await self.speech_integration.initialize()
        await self.speech_integration.start()
        
        # Мониторим ЕДИНЫЙ канал
        await self.event_bus.subscribe("playback.cancelled", self._on_unified_interrupt, EventPriority.LOW)
        
        # Мониторим входящие события
        await self.event_bus.subscribe("keyboard.short_press", self._on_input_event, EventPriority.LOW)
        await self.event_bus.subscribe("interrupt.request", self._on_input_event, EventPriority.LOW)
        
        print("✅ Полный тестер настроен")
    
    async def _on_unified_interrupt(self, event):
        """Мониторинг единого канала прерывания"""
        data = event.get("data", {})
        source = data.get("source", "unknown")
        reason = data.get("reason", "unknown")
        original = data.get("original_event", "direct")
        
        self.unified_interrupts.append({
            "source": source,
            "reason": reason,
            "original_event": original
        })
        
        print(f"✅ ЕДИНЫЙ канал: source={source}, reason={reason}, original={original}")
    
    async def _on_input_event(self, event):
        """Мониторинг входящих событий"""
        event_type = event.get("type", "unknown")
        self.input_events.append(event_type)
        print(f"📥 Входящее: {event_type}")
    
    async def test_keyboard_interrupt(self):
        """Тест прерывания клавиатурой"""
        print("\n🎹 === ТЕСТ КЛАВИАТУРНОГО ПРЕРЫВАНИЯ ===")
        
        # Очищаем счетчики
        self.unified_interrupts.clear()
        self.input_events.clear()
        
        # Симулируем прерывание
        print("Симулируем keyboard.short_press...")
        await self.event_bus.publish("keyboard.short_press", {
            "session_id": "keyboard_test",
            "reason": "user_interrupt"
        })
        
        await asyncio.sleep(0.2)  # Ждем обработки
        
        print(f"Входящих событий: {len(self.input_events)}")
        print(f"Единых прерываний: {len(self.unified_interrupts)}")
        
        return len(self.unified_interrupts) > 0
    
    async def test_general_interrupt(self):
        """Тест общего прерывания"""
        print("\n🛑 === ТЕСТ ОБЩЕГО ПРЕРЫВАНИЯ ===")
        
        # Очищаем счетчики
        self.unified_interrupts.clear()
        self.input_events.clear()
        
        # Симулируем прерывание
        print("Симулируем interrupt.request...")
        await self.event_bus.publish("interrupt.request", {
            "session_id": "general_test",
            "scope": "playback",
            "reason": "user_interrupt"
        })
        
        await asyncio.sleep(0.2)  # Ждем обработки
        
        print(f"Входящих событий: {len(self.input_events)}")
        print(f"Единых прерываний: {len(self.unified_interrupts)}")
        
        return len(self.unified_interrupts) > 0
    
    async def test_direct_interrupt(self):
        """Тест прямого прерывания"""
        print("\n⚙️ === ТЕСТ ПРЯМОГО ПРЕРЫВАНИЯ ===")
        
        # Очищаем счетчики
        self.unified_interrupts.clear()
        self.input_events.clear()
        
        # Симулируем прямое прерывание (от ProcessingWorkflow)
        print("Симулируем playback.cancelled напрямую...")
        await self.event_bus.publish("playback.cancelled", {
            "session_id": "direct_test",
            "reason": "user_interrupt",
            "source": "processing_workflow"
        })
        
        await asyncio.sleep(0.2)  # Ждем обработки
        
        print(f"Входящих событий: {len(self.input_events)}")
        print(f"Единых прерываний: {len(self.unified_interrupts)}")
        
        return len(self.unified_interrupts) > 0
    
    async def run_all_tests(self):
        """Запуск всех тестов"""
        try:
            print("🧪 ПОЛНОЕ ТЕСТИРОВАНИЕ ЕДИНЫХ ПРЕРЫВАНИЙ")
            print("=" * 60)
            
            await self.setup()
            
            # Запускаем тесты
            results = []
            results.append(await self.test_keyboard_interrupt())
            results.append(await self.test_general_interrupt())
            results.append(await self.test_direct_interrupt())
            
            print("\n📊 === ИТОГОВЫЙ АНАЛИЗ ===")
            print(f"Успешных тестов: {sum(results)}/{len(results)}")
            
            if all(results):
                print("\n🎉 ВСЕ ПРЕРЫВАНИЯ РАБОТАЮТ ЧЕРЕЗ ЕДИНЫЙ КАНАЛ!")
                print("✅ Единообразие достигнуто:")
                print("  - keyboard.short_press → playback.cancelled")
                print("  - interrupt.request → playback.cancelled") 
                print("  - прямые вызовы → playback.cancelled")
                return True
            else:
                print("\n❌ НЕ ВСЕ ПРЕРЫВАНИЯ РАБОТАЮТ ЕДИНООБРАЗНО!")
                print("Требуется доработка логики перенаправления.")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка в тестах: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            # Останавливаем интеграцию
            try:
                await self.speech_integration.stop()
            except:
                pass

async def main():
    """Главная функция"""
    print("🎧 ПОЛНОЕ ТЕСТИРОВАНИЕ ЕДИНЫХ ПРЕРЫВАНИЙ АУДИО")
    print("=" * 70)
    
    tester = UnifiedInterruptTester()
    success = await tester.run_all_tests()
    
    if success:
        print("\n🎯 Единое состояние прерываний работает корректно!")
        return True
    else:
        print("\n⚠️ Требуется доработка единого состояния!")
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
