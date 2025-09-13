#!/usr/bin/env python3
"""
Тестирование модуля interrupt_management
Проверяет правильность работы и реагирования на прерывания
"""

import asyncio
import logging
import time
import sys
import os
from typing import Dict, Any, Optional

# Добавляем путь к модулям
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from interrupt_management import (
    InterruptCoordinator, InterruptDependencies,
    InterruptEvent, InterruptType, InterruptPriority, InterruptStatus,
    InterruptConfig, InterruptMetrics,
    SpeechInterruptHandler, RecordingInterruptHandler,
    InterruptModuleConfig, DEFAULT_INTERRUPT_CONFIG
)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MockSpeechPlayer:
    """Мок для тестирования speech_player"""
    
    def __init__(self):
        self.is_playing = False
        self.is_paused = False
        self.stop_called = False
        self.pause_called = False
        self.resume_called = False
    
    def stop_playback(self) -> bool:
        """Останавливает воспроизведение"""
        self.stop_called = True
        self.is_playing = False
        self.is_paused = False
        logger.info("🎵 Mock: Воспроизведение остановлено")
        return True
    
    def pause_playback(self) -> bool:
        """Приостанавливает воспроизведение"""
        self.pause_called = True
        self.is_paused = True
        logger.info("⏸️ Mock: Воспроизведение приостановлено")
        return True
    
    def resume_playback(self) -> bool:
        """Возобновляет воспроизведение"""
        self.resume_called = True
        self.is_paused = False
        self.is_playing = True
        logger.info("▶️ Mock: Воспроизведение возобновлено")
        return True

class MockSpeechRecognizer:
    """Мок для тестирования speech_recognizer"""
    
    def __init__(self):
        self.is_recording = False
        self.stop_called = False
        self.start_called = False
        self.recognized_text = "Тестовый распознанный текст"
    
    async def stop_recording(self) -> Optional[str]:
        """Останавливает запись"""
        self.stop_called = True
        self.is_recording = False
        logger.info("🎤 Mock: Запись остановлена")
        return self.recognized_text
    
    async def start_recording(self) -> bool:
        """Начинает запись"""
        self.start_called = True
        self.is_recording = True
        logger.info("🎤 Mock: Запись начата")
        return True

class MockGrpcClient:
    """Мок для тестирования grpc_client"""
    
    def __init__(self):
        self.interrupt_called = False
        self.interrupt_count = 0
    
    async def interrupt_session(self):
        """Отправляет прерывание на сервер"""
        self.interrupt_called = True
        self.interrupt_count += 1
        logger.info("📡 Mock: Прерывание отправлено на сервер")

class InterruptManagementTester:
    """Тестер модуля interrupt_management"""
    
    def __init__(self):
        self.speech_player = MockSpeechPlayer()
        self.speech_recognizer = MockSpeechRecognizer()
        self.grpc_client = MockGrpcClient()
        self.coordinator = None
        self.test_results = {}
        
    async def setup(self):
        """Настройка тестового окружения"""
        logger.info("🔧 Настройка тестового окружения...")
        
        # Создаем координатор с тестовой конфигурацией
        config = InterruptConfig(
            max_concurrent_interrupts=3,
            interrupt_timeout=5.0,
            retry_attempts=2,
            retry_delay=0.5,
            enable_logging=True,
            enable_metrics=True
        )
        
        self.coordinator = InterruptCoordinator(config)
        
        # Настраиваем зависимости
        dependencies = InterruptDependencies(
            speech_player=self.speech_player,
            speech_recognizer=self.speech_recognizer,
            grpc_client=self.grpc_client,
            state_manager=None
        )
        
        self.coordinator.initialize(dependencies)
        
        # Регистрируем обработчики
        speech_handler = SpeechInterruptHandler(self.speech_player, self.grpc_client)
        recording_handler = RecordingInterruptHandler(self.speech_recognizer)
        
        # Создаем мок-обработчики с задержкой для тестирования лимитов
        async def mock_speech_stop_handler(event):
            await asyncio.sleep(0.1)  # Задержка для тестирования лимитов
            return await speech_handler.handle_speech_stop(event)
        
        async def mock_speech_pause_handler(event):
            await asyncio.sleep(0.05)
            return await speech_handler.handle_speech_pause(event)
        
        async def mock_recording_stop_handler(event):
            await asyncio.sleep(0.05)
            return await recording_handler.handle_recording_stop(event)
        
        self.coordinator.register_handler(InterruptType.SPEECH_STOP, mock_speech_stop_handler)
        self.coordinator.register_handler(InterruptType.SPEECH_PAUSE, mock_speech_pause_handler)
        self.coordinator.register_handler(InterruptType.RECORDING_STOP, mock_recording_stop_handler)
        
        logger.info("✅ Тестовое окружение настроено")
    
    async def test_basic_functionality(self):
        """Тест базовой функциональности"""
        logger.info("🧪 Тест 1: Базовая функциональность")
        
        try:
            # Создаем событие прерывания
            event = InterruptEvent(
                type=InterruptType.SPEECH_STOP,
                priority=InterruptPriority.HIGH,
                source="test",
                timestamp=time.time()
            )
            
            # Запускаем прерывание
            result = await self.coordinator.trigger_interrupt(event)
            
            # Проверяем результат
            assert result == True, "Прерывание должно быть выполнено успешно"
            assert event.status == InterruptStatus.COMPLETED, "Статус должен быть COMPLETED"
            assert self.speech_player.stop_called == True, "stop_playback должен быть вызван"
            assert self.grpc_client.interrupt_called == True, "interrupt_session должен быть вызван"
            
            self.test_results["basic_functionality"] = "✅ PASSED"
            logger.info("✅ Тест 1 пройден: Базовая функциональность работает")
            
        except Exception as e:
            self.test_results["basic_functionality"] = f"❌ FAILED: {e}"
            logger.error(f"❌ Тест 1 провален: {e}")
    
    async def test_multiple_interrupts(self):
        """Тест множественных прерываний"""
        logger.info("🧪 Тест 2: Множественные прерывания")
        
        try:
            # Сбрасываем счетчик grpc_client
            self.grpc_client.interrupt_count = 0
            
            # Создаем несколько событий
            events = []
            for i in range(3):
                event = InterruptEvent(
                    type=InterruptType.SPEECH_STOP,
                    priority=InterruptPriority.HIGH,
                    source=f"test_{i}",
                    timestamp=time.time()
                )
                events.append(event)
            
            # Запускаем все прерывания параллельно
            tasks = [self.coordinator.trigger_interrupt(event) for event in events]
            results = await asyncio.gather(*tasks)
            
            # Проверяем результаты
            assert all(results), "Все прерывания должны быть выполнены успешно"
            assert all(event.status == InterruptStatus.COMPLETED for event in events), "Все статусы должны быть COMPLETED"
            assert self.grpc_client.interrupt_count == 3, f"Должно быть 3 вызова interrupt_session, получено: {self.grpc_client.interrupt_count}"
            
            self.test_results["multiple_interrupts"] = "✅ PASSED"
            logger.info("✅ Тест 2 пройден: Множественные прерывания работают")
            
        except Exception as e:
            self.test_results["multiple_interrupts"] = f"❌ FAILED: {e}"
            logger.error(f"❌ Тест 2 провален: {e}")
    
    async def test_different_interrupt_types(self):
        """Тест разных типов прерываний"""
        logger.info("🧪 Тест 3: Разные типы прерываний")
        
        try:
            # Тест SPEECH_PAUSE
            pause_event = InterruptEvent(
                type=InterruptType.SPEECH_PAUSE,
                priority=InterruptPriority.NORMAL,
                source="test_pause",
                timestamp=time.time()
            )
            
            result = await self.coordinator.trigger_interrupt(pause_event)
            assert result == True, "SPEECH_PAUSE должен быть выполнен успешно"
            assert self.speech_player.pause_called == True, "pause_playback должен быть вызван"
            
            # Тест RECORDING_STOP
            recording_event = InterruptEvent(
                type=InterruptType.RECORDING_STOP,
                priority=InterruptPriority.NORMAL,
                source="test_recording",
                timestamp=time.time()
            )
            
            result = await self.coordinator.trigger_interrupt(recording_event)
            assert result == True, "RECORDING_STOP должен быть выполнен успешно"
            assert self.speech_recognizer.stop_called == True, "stop_recording должен быть вызван"
            assert recording_event.data["recognized_text"] == "Тестовый распознанный текст", "Должен быть сохранен распознанный текст"
            
            self.test_results["different_interrupt_types"] = "✅ PASSED"
            logger.info("✅ Тест 3 пройден: Разные типы прерываний работают")
            
        except Exception as e:
            self.test_results["different_interrupt_types"] = f"❌ FAILED: {e}"
            logger.error(f"❌ Тест 3 провален: {e}")
    
    async def test_concurrent_limit(self):
        """Тест лимита одновременных прерываний"""
        logger.info("🧪 Тест 4: Лимит одновременных прерываний")
        
        try:
            # Сбрасываем счетчик grpc_client
            self.grpc_client.interrupt_count = 0
            
            # Создаем больше событий, чем лимит
            events = []
            for i in range(5):  # Лимит = 3
                event = InterruptEvent(
                    type=InterruptType.SPEECH_STOP,
                    priority=InterruptPriority.HIGH,
                    source=f"test_limit_{i}",
                    timestamp=time.time()
                )
                events.append(event)
            
            # Запускаем все прерывания
            tasks = [self.coordinator.trigger_interrupt(event) for event in events]
            results = await asyncio.gather(*tasks)
            
            # Проверяем, что некоторые прерывания не выполнились
            successful_count = sum(1 for r in results if r)
            failed_count = sum(1 for r in results if not r)
            
            logger.info(f"📊 Результаты: успешных={successful_count}, проваленных={failed_count}")
            logger.info(f"📊 Вызовов grpc_client: {self.grpc_client.interrupt_count}")
            
            assert successful_count <= 3, f"Должно быть не более 3 успешных прерываний, получено: {successful_count}"
            assert failed_count >= 2, f"Должно быть не менее 2 проваленных прерываний, получено: {failed_count}"
            
            self.test_results["concurrent_limit"] = "✅ PASSED"
            logger.info("✅ Тест 4 пройден: Лимит одновременных прерываний работает")
            
        except Exception as e:
            self.test_results["concurrent_limit"] = f"❌ FAILED: {e}"
            logger.error(f"❌ Тест 4 провален: {e}")
    
    async def test_metrics(self):
        """Тест метрик"""
        logger.info("🧪 Тест 5: Метрики")
        
        try:
            metrics = self.coordinator.get_metrics()
            
            # Проверяем базовые метрики
            assert metrics.total_interrupts > 0, "Должно быть выполнено прерываний"
            assert metrics.successful_interrupts > 0, "Должны быть успешные прерывания"
            assert metrics.average_processing_time >= 0, "Среднее время обработки должно быть >= 0"
            
            # Проверяем метрики по типам
            assert InterruptType.SPEECH_STOP in metrics.interrupts_by_type, "Должны быть метрики для SPEECH_STOP"
            assert metrics.interrupts_by_type[InterruptType.SPEECH_STOP] > 0, "Должны быть прерывания SPEECH_STOP"
            
            # Проверяем метрики по приоритетам
            assert InterruptPriority.HIGH in metrics.interrupts_by_priority, "Должны быть метрики для HIGH приоритета"
            assert metrics.interrupts_by_priority[InterruptPriority.HIGH] > 0, "Должны быть прерывания HIGH приоритета"
            
            self.test_results["metrics"] = "✅ PASSED"
            logger.info("✅ Тест 5 пройден: Метрики работают корректно")
            
        except Exception as e:
            self.test_results["metrics"] = f"❌ FAILED: {e}"
            logger.error(f"❌ Тест 5 провален: {e}")
    
    async def test_status_and_history(self):
        """Тест статуса и истории"""
        logger.info("🧪 Тест 6: Статус и история")
        
        try:
            # Проверяем статус
            status = self.coordinator.get_status()
            assert "active_interrupts" in status, "Должен быть active_interrupts в статусе"
            assert "total_interrupts" in status, "Должен быть total_interrupts в статусе"
            assert "success_rate" in status, "Должен быть success_rate в статусе"
            assert status["success_rate"] >= 0, "Success rate должен быть >= 0"
            
            # Проверяем историю
            history = self.coordinator.get_interrupt_history(5)
            assert len(history) > 0, "Должна быть история прерываний"
            assert all(event.status in [InterruptStatus.COMPLETED, InterruptStatus.FAILED] for event in history), "Все события в истории должны быть завершены"
            
            # Проверяем активные прерывания
            active = self.coordinator.get_active_interrupts()
            assert len(active) == 0, "Не должно быть активных прерываний после завершения"
            
            self.test_results["status_and_history"] = "✅ PASSED"
            logger.info("✅ Тест 6 пройден: Статус и история работают корректно")
            
        except Exception as e:
            self.test_results["status_and_history"] = f"❌ FAILED: {e}"
            logger.error(f"❌ Тест 6 провален: {e}")
    
    async def test_error_handling(self):
        """Тест обработки ошибок"""
        logger.info("🧪 Тест 7: Обработка ошибок")
        
        try:
            # Создаем обработчик, который выбрасывает исключение
            async def failing_handler(event):
                raise Exception("Тестовая ошибка")
            
            # Регистрируем проблемный обработчик
            self.coordinator.register_handler(InterruptType.SESSION_CLEAR, failing_handler)
            
            # Создаем событие с проблемным обработчиком
            event = InterruptEvent(
                type=InterruptType.SESSION_CLEAR,
                priority=InterruptPriority.HIGH,
                source="test_error",
                timestamp=time.time()
            )
            
            # Запускаем прерывание
            result = await self.coordinator.trigger_interrupt(event)
            
            # Проверяем, что ошибка обработана корректно
            assert result == False, "Прерывание должно завершиться с ошибкой"
            assert event.status == InterruptStatus.FAILED, "Статус должен быть FAILED"
            assert event.error is not None, "Должна быть сохранена ошибка"
            assert "Тестовая ошибка" in event.error, "Должна быть сохранена правильная ошибка"
            
            self.test_results["error_handling"] = "✅ PASSED"
            logger.info("✅ Тест 7 пройден: Обработка ошибок работает корректно")
            
        except Exception as e:
            self.test_results["error_handling"] = f"❌ FAILED: {e}"
            logger.error(f"❌ Тест 7 провален: {e}")
    
    def print_results(self):
        """Выводит результаты тестирования"""
        logger.info("\n" + "="*60)
        logger.info("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ INTERRUPT_MANAGEMENT")
        logger.info("="*60)
        
        for test_name, result in self.test_results.items():
            logger.info(f"{test_name.replace('_', ' ').title()}: {result}")
        
        # Общая статистика
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result.startswith("✅"))
        failed_tests = total_tests - passed_tests
        
        logger.info("-"*60)
        logger.info(f"Всего тестов: {total_tests}")
        logger.info(f"Пройдено: {passed_tests}")
        logger.info(f"Провалено: {failed_tests}")
        logger.info(f"Успешность: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests == 0:
            logger.info("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        else:
            logger.warning(f"⚠️ {failed_tests} тестов провалено")
        
        logger.info("="*60)
    
    async def run_all_tests(self):
        """Запускает все тесты"""
        logger.info("🚀 Запуск тестирования модуля interrupt_management...")
        
        await self.setup()
        
        # Запускаем тесты последовательно
        await self.test_basic_functionality()
        await self.test_multiple_interrupts()
        await self.test_different_interrupt_types()
        await self.test_concurrent_limit()
        await self.test_metrics()
        await self.test_status_and_history()
        await self.test_error_handling()
        
        self.print_results()

async def main():
    """Главная функция"""
    tester = InterruptManagementTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
