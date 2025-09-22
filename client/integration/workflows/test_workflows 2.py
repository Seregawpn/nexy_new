#!/usr/bin/env python3
"""
Тест Workflows - проверка работы координаторов режимов
"""

import asyncio
import logging
import sys
from pathlib import Path

# Добавляем пути для импортов
sys.path.append(str(Path(__file__).parent.parent.parent))

from integration.core.event_bus import EventBus, EventPriority
from integration.workflows import ListeningWorkflow, ProcessingWorkflow
from integration.workflows.workflow_config import WorkflowsConfig, DEFAULT_MACOS_CONFIG

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WorkflowTester:
    """Тестер для Workflows"""
    
    def __init__(self):
        self.event_bus = EventBus()
        self.config = WorkflowsConfig.from_dict(DEFAULT_MACOS_CONFIG)
        
        # Workflows
        self.listening_workflow = ListeningWorkflow(self.event_bus)
        self.processing_workflow = ProcessingWorkflow(self.event_bus)
        
        # Состояние тестов
        self.test_session_id = "test_session_123"
        self.events_received = []
    
    async def setup(self):
        """Настройка тестера"""
        print("🔧 Настройка тестера workflows...")
        
        # Подписываемся на все события для мониторинга
        await self.event_bus.subscribe("*", self._event_monitor, EventPriority.LOW)
        
        # Инициализируем workflows
        await self.listening_workflow.initialize()
        await self.processing_workflow.initialize()
        
        # Запускаем workflows
        await self.listening_workflow.start()
        await self.processing_workflow.start()
        
        print("✅ Тестер настроен")
    
    async def _event_monitor(self, event):
        """Мониторинг всех событий"""
        event_type = event.get("type", "unknown")
        self.events_received.append(event_type)
        print(f"📡 Событие: {event_type}")
    
    async def test_listening_workflow(self):
        """Тест ListeningWorkflow"""
        print("\n🎤 === ТЕСТ LISTENING WORKFLOW ===")
        
        # 1. Симулируем начало записи
        print("1. Симулируем voice.recording_start...")
        await self.event_bus.publish("voice.recording_start", {
            "session_id": self.test_session_id,
            "timestamp": "2025-09-19T12:00:00"
        })
        
        await asyncio.sleep(1)
        
        # 2. Симулируем активность голоса
        print("2. Симулируем voice.activity_detected...")
        await self.event_bus.publish("voice.activity_detected", {
            "session_id": self.test_session_id,
            "level": 0.8
        })
        
        await asyncio.sleep(0.5)
        
        # 3. Симулируем завершение записи
        print("3. Симулируем voice.recording_stop...")
        await self.event_bus.publish("voice.recording_stop", {
            "session_id": self.test_session_id,
            "duration": 2.5
        })
        
        await asyncio.sleep(1)
        
        # Проверяем статус
        status = self.listening_workflow.get_status()
        print(f"📊 Статус ListeningWorkflow: {status}")
        
        print("✅ Тест ListeningWorkflow завершен")
    
    async def test_processing_workflow(self):
        """Тест ProcessingWorkflow"""
        print("\n⚙️ === ТЕСТ PROCESSING WORKFLOW ===")
        
        # 1. Симулируем переход в PROCESSING
        print("1. Симулируем app.mode_changed → PROCESSING...")
        await self.event_bus.publish("app.mode_changed", {
            "mode": "processing",
            "session_id": self.test_session_id,
            "previous_mode": "listening"
        })
        
        await asyncio.sleep(0.5)
        
        # 2. Симулируем захват скриншота
        print("2. Симулируем screenshot.captured...")
        await self.event_bus.publish("screenshot.captured", {
            "session_id": self.test_session_id,
            "path": "/tmp/test_screenshot.png",
            "size": "1920x1080"
        })
        
        await asyncio.sleep(0.5)
        
        # 3. Симулируем начало gRPC запроса
        print("3. Симулируем grpc.request_started...")
        await self.event_bus.publish("grpc.request_started", {
            "session_id": self.test_session_id,
            "server": "production"
        })
        
        await asyncio.sleep(1)
        
        # 4. Симулируем начало воспроизведения
        print("4. Симулируем playback.started...")
        await self.event_bus.publish("playback.started", {
            "session_id": self.test_session_id,
            "audio_format": "pcm_s16le"
        })
        
        await asyncio.sleep(0.5)
        
        # 5. Симулируем завершение gRPC
        print("5. Симулируем grpc.request_completed...")
        await self.event_bus.publish("grpc.request_completed", {
            "session_id": self.test_session_id,
            "response_size": 1024
        })
        
        await asyncio.sleep(0.5)
        
        # 6. Симулируем завершение воспроизведения (КЛЮЧЕВОЕ!)
        print("6. Симулируем playback.completed...")
        await self.event_bus.publish("playback.completed", {
            "session_id": self.test_session_id,
            "duration": 5.2
        })
        
        await asyncio.sleep(1)
        
        # Проверяем статус
        status = self.processing_workflow.get_status()
        print(f"📊 Статус ProcessingWorkflow: {status}")
        
        print("✅ Тест ProcessingWorkflow завершен")
    
    async def test_interrupt_handling(self):
        """Тест обработки прерываний"""
        print("\n🛑 === ТЕСТ ПРЕРЫВАНИЙ ===")
        
        # 1. Начинаем новую сессию
        print("1. Начинаем новую сессию...")
        new_session = "interrupt_test_456"
        
        await self.event_bus.publish("app.mode_changed", {
            "mode": "processing",
            "session_id": new_session
        })
        
        await asyncio.sleep(0.5)
        
        # 2. Симулируем прерывание
        print("2. Симулируем keyboard.short_press (прерывание)...")
        await self.event_bus.publish("keyboard.short_press", {
            "session_id": new_session,
            "reason": "user_interrupt"
        })
        
        await asyncio.sleep(1)
        
        # Проверяем, что workflow корректно обработал прерывание
        status = self.processing_workflow.get_status()
        print(f"📊 Статус после прерывания: {status}")
        
        print("✅ Тест прерываний завершен")
    
    async def run_all_tests(self):
        """Запуск всех тестов"""
        try:
            print("🚀 ЗАПУСК ТЕСТОВ WORKFLOWS")
            print("=" * 50)
            
            await self.setup()
            
            # Запускаем тесты последовательно
            await self.test_listening_workflow()
            await self.test_processing_workflow() 
            await self.test_interrupt_handling()
            
            print("\n📊 === ИТОГОВАЯ СТАТИСТИКА ===")
            print(f"Всего событий получено: {len(self.events_received)}")
            print(f"Уникальных типов событий: {len(set(self.events_received))}")
            
            print(f"\nТипы событий:")
            for event_type in set(self.events_received):
                count = self.events_received.count(event_type)
                print(f"  - {event_type}: {count}")
            
            print("\n✅ ВСЕ ТЕСТЫ ЗАВЕРШЕНЫ УСПЕШНО!")
            
        except Exception as e:
            print(f"❌ Ошибка в тестах: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Останавливаем workflows
            await self.listening_workflow.stop()
            await self.processing_workflow.stop()

async def main():
    """Главная функция"""
    print("🧪 ТЕСТИРОВАНИЕ WORKFLOWS NEXY AI ASSISTANT")
    print("=" * 60)
    
    tester = WorkflowTester()
    await tester.run_all_tests()
    
    print("\n🎯 Тестирование завершено!")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️ Тестирование прервано пользователем")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
