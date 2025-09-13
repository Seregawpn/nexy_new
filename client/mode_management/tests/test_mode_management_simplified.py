#!/usr/bin/env python3
"""
Тестирование упрощенного модуля mode_management
Проверяет правильность переключения между 3 режимами: Sleeping, Processing, Listening
"""

import asyncio
import logging
import time
import sys
import os
from typing import Dict, Any, Optional

# Добавляем путь к модулям
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

from mode_management import (
    ModeController, AppMode, ModeTransition, ModeTransitionType, ModeStatus,
    ModeEvent, ModeConfig, ModeMetrics, SleepingMode, ProcessingMode, ListeningMode
)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MockSpeechRecognizer:
    """Мок для тестирования speech_recognizer"""
    
    def __init__(self):
        self.is_recording = False
        self.start_called = False
        self.stop_called = False
        self.recognized_text = "Тестовый распознанный текст"
    
    async def start_recording(self) -> bool:
        self.start_called = True
        self.is_recording = True
        logger.info("🎤 Mock: Прослушивание начато")
        return True
    
    async def stop_recording(self) -> Optional[str]:
        self.stop_called = True
        self.is_recording = False
        logger.info("🎤 Mock: Прослушивание остановлено")
        return self.recognized_text

class MockAudioDeviceManager:
    """Мок для тестирования audio_device_manager"""
    
    def __init__(self):
        self.switch_called = False
        self.current_device = "default"
    
    async def switch_to_best_device(self):
        self.switch_called = True
        self.current_device = "best_device"
        logger.info("🔊 Mock: Переключились на лучшее аудио устройство")

class MockGrpcClient:
    """Мок для тестирования grpc_client"""
    
    def __init__(self):
        self.process_called = False
        self.commands_processed = []
    
    async def process_command(self, command: str, data: Dict[str, Any] = None):
        self.process_called = True
        self.commands_processed.append(command)
        logger.info(f"📡 Mock: Команда обработана: {command}")
        return f"Response for {command}"

class MockStateManager:
    """Мок для тестирования state_manager"""
    
    def __init__(self):
        self.processing_state = False
        self.set_called = False
    
    async def set_processing_state(self, state: bool):
        self.set_called = True
        self.processing_state = state
        logger.info(f"📊 Mock: Состояние обработки установлено: {state}")

class SimplifiedModeManagementTester:
    """Тестер упрощенного модуля mode_management"""
    
    def __init__(self):
        self.speech_recognizer = MockSpeechRecognizer()
        self.audio_device_manager = MockAudioDeviceManager()
        self.grpc_client = MockGrpcClient()
        self.state_manager = MockStateManager()
        self.controller = None
        self.sleeping_mode = None
        self.processing_mode = None
        self.listening_mode = None
        self.test_results = {}
        self.mode_change_events = []
        
    async def setup(self):
        """Настройка тестового окружения"""
        logger.info("🔧 Настройка тестового окружения...")
        
        # Создаем контроллер с тестовой конфигурацией
        config = ModeConfig(
            default_mode=AppMode.SLEEPING,
            enable_automatic_transitions=True,
            transition_timeout=5.0,
            max_transition_attempts=3,
            enable_logging=True,
            enable_metrics=True
        )
        
        self.controller = ModeController(config)
        
        # Создаем режимы
        self.sleeping_mode = SleepingMode()
        self.processing_mode = ProcessingMode(self.grpc_client, self.state_manager)
        self.listening_mode = ListeningMode(self.speech_recognizer, self.audio_device_manager)
        
        # Регистрируем переходы между режимами
        self._register_transitions()
        
        # Регистрируем обработчики режимов
        self._register_mode_handlers()
        
        # Регистрируем callback для отслеживания смены режимов
        self.controller.register_mode_change_callback(self._on_mode_change)
        
        logger.info("✅ Тестовое окружение настроено")
    
    def _register_transitions(self):
        """Регистрирует переходы между режимами"""
        # SLEEPING -> LISTENING (пробуждение для прослушивания)
        transition = ModeTransition(
            from_mode=AppMode.SLEEPING,
            to_mode=AppMode.LISTENING,
            transition_type=ModeTransitionType.AUTOMATIC,
            priority=1,
            timeout=2.0
        )
        self.controller.register_transition(transition)
        
        # LISTENING -> PROCESSING (обработка распознанной речи)
        transition = ModeTransition(
            from_mode=AppMode.LISTENING,
            to_mode=AppMode.PROCESSING,
            transition_type=ModeTransitionType.AUTOMATIC,
            priority=1,
            timeout=3.0
        )
        self.controller.register_transition(transition)
        
        # PROCESSING -> SLEEPING (завершение обработки)
        transition = ModeTransition(
            from_mode=AppMode.PROCESSING,
            to_mode=AppMode.SLEEPING,
            transition_type=ModeTransitionType.AUTOMATIC,
            priority=1,
            timeout=2.0
        )
        self.controller.register_transition(transition)
        
        # Добавляем обратные переходы для тестирования
        # PROCESSING -> LISTENING (повторное прослушивание)
        transition = ModeTransition(
            from_mode=AppMode.PROCESSING,
            to_mode=AppMode.LISTENING,
            transition_type=ModeTransitionType.MANUAL,
            priority=2,
            timeout=2.0
        )
        self.controller.register_transition(transition)
        
        # LISTENING -> SLEEPING (прерывание прослушивания)
        transition = ModeTransition(
            from_mode=AppMode.LISTENING,
            to_mode=AppMode.SLEEPING,
            transition_type=ModeTransitionType.INTERRUPT,
            priority=1,
            timeout=1.0
        )
        self.controller.register_transition(transition)
    
    def _register_mode_handlers(self):
        """Регистрирует обработчики режимов"""
        async def sleeping_handler():
            logger.info("🔄 Обработчик режима SLEEPING")
            await self.sleeping_mode.enter_mode()
            
        async def processing_handler():
            logger.info("🔄 Обработчик режима PROCESSING")
            await self.processing_mode.enter_mode()
            
        async def listening_handler():
            logger.info("🔄 Обработчик режима LISTENING")
            await self.listening_mode.enter_mode()
            
        self.controller.register_mode_handler(AppMode.SLEEPING, sleeping_handler)
        self.controller.register_mode_handler(AppMode.PROCESSING, processing_handler)
        self.controller.register_mode_handler(AppMode.LISTENING, listening_handler)
    
    async def _on_mode_change(self, event: ModeEvent):
        """Callback для отслеживания смены режимов"""
        self.mode_change_events.append(event)
        logger.info(f"📢 Смена режима: {event.mode.value} (статус: {event.status.value})")
    
    async def test_basic_mode_switching(self):
        """Тест базового переключения режимов"""
        logger.info("🧪 Тест 1: Базовое переключение режимов")
        
        try:
            # Проверяем начальный режим
            assert self.controller.get_current_mode() == AppMode.SLEEPING, "Начальный режим должен быть SLEEPING"
            
            # Переключаемся в LISTENING
            result = await self.controller.switch_mode(AppMode.LISTENING)
            assert result == True, "Переключение в LISTENING должно быть успешным"
            assert self.controller.get_current_mode() == AppMode.LISTENING, "Текущий режим должен быть LISTENING"
            
            # Проверяем, что режим прослушивания активирован
            assert self.listening_mode.is_active == True, "Режим прослушивания должен быть активен"
            assert self.speech_recognizer.start_called == True, "start_recording должен быть вызван"
            assert self.audio_device_manager.switch_called == True, "switch_to_best_device должен быть вызван"
            
            self.test_results["basic_mode_switching"] = "✅ PASSED"
            logger.info("✅ Тест 1 пройден: Базовое переключение режимов работает")
            
        except Exception as e:
            self.test_results["basic_mode_switching"] = f"❌ FAILED: {e}"
            logger.error(f"❌ Тест 1 провален: {e}")
    
    async def test_full_mode_cycle(self):
        """Тест полного цикла режимов"""
        logger.info("🧪 Тест 2: Полный цикл режимов")
        
        try:
            # Сбрасываем состояние
            self.mode_change_events.clear()
            
            # Переключаемся в PROCESSING из LISTENING (текущий режим)
            result = await self.controller.switch_mode(AppMode.PROCESSING)
            assert result == True, "Переключение в PROCESSING должно быть успешным"
            assert self.controller.get_current_mode() == AppMode.PROCESSING, "Текущий режим должен быть PROCESSING"
            
            # Переключаемся в SLEEPING из PROCESSING
            result = await self.controller.switch_mode(AppMode.SLEEPING)
            assert result == True, "Переключение в SLEEPING должно быть успешным"
            assert self.controller.get_current_mode() == AppMode.SLEEPING, "Текущий режим должен быть SLEEPING"
            
            # Переключаемся в LISTENING из SLEEPING
            result = await self.controller.switch_mode(AppMode.LISTENING)
            assert result == True, "Переключение в LISTENING должно быть успешным"
            assert self.controller.get_current_mode() == AppMode.LISTENING, "Текущий режим должен быть LISTENING"
            
            # Проверяем, что все переходы были зафиксированы
            assert len(self.mode_change_events) == 3, f"Должно быть 3 события смены режима"
            
            # Проверяем, что режим обработки был активирован
            assert self.processing_mode.is_active == True, "Режим обработки должен быть активен"
            assert self.state_manager.set_called == True, "set_processing_state должен быть вызван"
            
            self.test_results["full_mode_cycle"] = "✅ PASSED"
            logger.info("✅ Тест 2 пройден: Полный цикл режимов работает")
            
        except Exception as e:
            self.test_results["full_mode_cycle"] = f"❌ FAILED: {e}"
            logger.error(f"❌ Тест 2 провален: {e}")
    
    async def test_mode_specific_functionality(self):
        """Тест специфичной функциональности режимов"""
        logger.info("🧪 Тест 3: Специфичная функциональность режимов")
        
        try:
            # Тест режима прослушивания
            await self.controller.switch_mode(AppMode.LISTENING)
            assert self.listening_mode.is_listening() == True, "is_listening должен возвращать True"
            assert self.listening_mode.get_recognized_text() is None, "Распознанный текст должен быть None до остановки"
            
            # Тест режима обработки
            await self.controller.switch_mode(AppMode.PROCESSING)
            response = await self.processing_mode.process_command("test_command", {"data": "test"})
            assert response is not None, "Обработка команды должна вернуть ответ"
            assert self.grpc_client.process_called == True, "process_command должен быть вызван"
            assert "test_command" in self.grpc_client.commands_processed, "Команда должна быть в списке обработанных"
            
            # Тест режима сна
            await self.controller.switch_mode(AppMode.SLEEPING)
            assert self.sleeping_mode.is_sleeping() == True, "is_sleeping должен возвращать True"
            
            self.test_results["mode_specific_functionality"] = "✅ PASSED"
            logger.info("✅ Тест 3 пройден: Специфичная функциональность режимов работает")
            
        except Exception as e:
            self.test_results["mode_specific_functionality"] = f"❌ FAILED: {e}"
            logger.error(f"❌ Тест 3 провален: {e}")
    
    async def test_mode_interrupts(self):
        """Тест прерываний режимов"""
        logger.info("🧪 Тест 4: Прерывания режимов")
        
        try:
            # Тест прерывания режима прослушивания
            await self.controller.switch_mode(AppMode.LISTENING)
            await self.listening_mode.handle_interrupt()
            assert self.speech_recognizer.stop_called == True, "stop_recording должен быть вызван"
            
            # Тест прерывания режима обработки
            await self.controller.switch_mode(AppMode.PROCESSING)
            await self.processing_mode.handle_interrupt()
            # Проверяем, что прерывание обработано (нет исключений)
            
            self.test_results["mode_interrupts"] = "✅ PASSED"
            logger.info("✅ Тест 4 пройден: Прерывания режимов работают")
            
        except Exception as e:
            self.test_results["mode_interrupts"] = f"❌ FAILED: {e}"
            logger.error(f"❌ Тест 4 провален: {e}")
    
    async def test_mode_metrics(self):
        """Тест метрик режимов"""
        logger.info("🧪 Тест 5: Метрики режимов")
        
        try:
            # Выполняем несколько переходов
            await self.controller.switch_mode(AppMode.LISTENING)
            await self.controller.switch_mode(AppMode.PROCESSING)
            await self.controller.switch_mode(AppMode.SLEEPING)
            
            # Получаем метрики
            metrics = self.controller.get_metrics()
            
            # Проверяем базовые метрики
            assert metrics.total_transitions > 0, "Должны быть выполнены переходы"
            assert metrics.successful_transitions > 0, "Должны быть успешные переходы"
            assert metrics.average_transition_time >= 0, "Среднее время перехода должно быть >= 0"
            
            # Проверяем метрики по типам переходов
            assert ModeTransitionType.MANUAL in metrics.transitions_by_type, "Должны быть метрики для MANUAL переходов"
            assert metrics.transitions_by_type[ModeTransitionType.MANUAL] > 0, "Должны быть MANUAL переходы"
            
            # Проверяем время в режимах
            assert AppMode.LISTENING in metrics.time_in_modes, "Должны быть метрики времени для LISTENING"
            assert metrics.time_in_modes[AppMode.LISTENING] > 0, "Время в режиме LISTENING должно быть > 0"
            
            self.test_results["mode_metrics"] = "✅ PASSED"
            logger.info("✅ Тест 5 пройден: Метрики режимов работают корректно")
            
        except Exception as e:
            self.test_results["mode_metrics"] = f"❌ FAILED: {e}"
            logger.error(f"❌ Тест 5 провален: {e}")
    
    async def test_mode_status(self):
        """Тест статуса режимов"""
        logger.info("🧪 Тест 6: Статус режимов")
        
        try:
            # Проверяем статус контроллера
            status = self.controller.get_status()
            
            assert "current_mode" in status, "Должен быть current_mode в статусе"
            assert "previous_mode" in status, "Должен быть previous_mode в статусе"
            assert "available_transitions" in status, "Должны быть available_transitions в статусе"
            assert "success_rate" in status, "Должен быть success_rate в статусе"
            assert status["success_rate"] >= 0, "Success rate должен быть >= 0"
            
            # Проверяем доступные переходы
            available = self.controller.get_available_transitions()
            assert isinstance(available, list), "Доступные переходы должны быть списком"
            
            # Проверяем статус режима прослушивания
            listening_status = self.listening_mode.get_status()
            assert "is_active" in listening_status, "Должен быть is_active в статусе прослушивания"
            assert "is_listening" in listening_status, "Должен быть is_listening в статусе прослушивания"
            
            # Проверяем статус режима обработки
            processing_status = self.processing_mode.get_status()
            assert "is_active" in processing_status, "Должен быть is_active в статусе обработки"
            assert "is_processing" in processing_status, "Должен быть is_processing в статусе обработки"
            
            # Проверяем статус режима сна
            sleeping_status = self.sleeping_mode.get_status()
            assert "is_active" in sleeping_status, "Должен быть is_active в статусе сна"
            assert "is_sleeping" in sleeping_status, "Должен быть is_sleeping в статусе сна"
            
            self.test_results["mode_status"] = "✅ PASSED"
            logger.info("✅ Тест 6 пройден: Статус режимов работает корректно")
            
        except Exception as e:
            self.test_results["mode_status"] = f"❌ FAILED: {e}"
            logger.error(f"❌ Тест 6 провален: {e}")
    
    def print_results(self):
        """Выводит результаты тестирования"""
        logger.info("\n" + "="*60)
        logger.info("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ УПРОЩЕННОГО MODE_MANAGEMENT")
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
        logger.info("🚀 Запуск тестирования упрощенного модуля mode_management...")
        
        await self.setup()
        
        # Запускаем тесты последовательно
        await self.test_basic_mode_switching()
        await self.test_full_mode_cycle()
        await self.test_mode_specific_functionality()
        await self.test_mode_interrupts()
        await self.test_mode_metrics()
        await self.test_mode_status()
        
        self.print_results()

async def main():
    """Главная функция"""
    tester = SimplifiedModeManagementTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
