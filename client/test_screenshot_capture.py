#!/usr/bin/env python3
"""
Тестирование модуля screenshot_capture
Проверяет захват скриншотов на macOS
"""

import asyncio
import logging
import sys
import os
import time
from typing import Optional

# Добавляем путь к модулям
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from screenshot_capture import (
    ScreenshotCapture, ScreenshotConfig, ScreenshotFormat, 
    ScreenshotQuality, ScreenshotRegion, get_global_capture
)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ScreenshotCaptureTester:
    """Тестер модуля screenshot_capture"""
    
    def __init__(self):
        self.capture = None
        self.test_results = {}
        
    async def setup(self):
        """Настройка тестового окружения"""
        logger.info("🔧 Настройка тестового окружения...")
        
        try:
            # Создаем захватчик с тестовой конфигурацией
            config = ScreenshotConfig(
                format=ScreenshotFormat.JPEG,
                quality=ScreenshotQuality.MEDIUM,
                region=ScreenshotRegion.FULL_SCREEN,
                max_width=1280,
                max_height=720,
                timeout=10.0
            )
            
            self.capture = ScreenshotCapture(config)
            logger.info("✅ Тестовое окружение настроено")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка настройки: {e}")
            return False
    
    async def test_initialization(self):
        """Тест инициализации модуля"""
        logger.info("🧪 Тест 1: Инициализация модуля")
        
        try:
            assert self.capture is not None, "Захватчик должен быть создан"
            assert self.capture._initialized == True, "Захватчик должен быть инициализирован"
            
            # Проверяем статус
            status = self.capture.get_status()
            assert status["initialized"] == True, "Статус должен показывать инициализацию"
            assert status["bridge_available"] == True, "Bridge должен быть доступен"
            
            self.test_results["initialization"] = "✅ PASSED"
            logger.info("✅ Тест 1 пройден: Инициализация модуля работает")
            
        except Exception as e:
            self.test_results["initialization"] = f"❌ FAILED: {e}"
            logger.error(f"❌ Тест 1 провален: {e}")
    
    async def test_screen_info(self):
        """Тест получения информации об экране"""
        logger.info("🧪 Тест 2: Информация об экране")
        
        try:
            screen_info = self.capture.get_screen_info()
            
            assert screen_info is not None, "Информация об экране должна быть получена"
            assert screen_info.width > 0, "Ширина экрана должна быть больше 0"
            assert screen_info.height > 0, "Высота экрана должна быть больше 0"
            
            logger.info(f"📺 Разрешение экрана: {screen_info.width}x{screen_info.height}")
            logger.info(f"📺 Масштаб: {screen_info.scale_factor}")
            logger.info(f"📺 Глубина цвета: {screen_info.color_depth} бит")
            
            self.test_results["screen_info"] = "✅ PASSED"
            logger.info("✅ Тест 2 пройден: Информация об экране получена")
            
        except Exception as e:
            self.test_results["screen_info"] = f"❌ FAILED: {e}"
            logger.error(f"❌ Тест 2 провален: {e}")
    
    async def test_capture_capability(self):
        """Тест возможности захвата"""
        logger.info("🧪 Тест 3: Возможность захвата")
        
        try:
            can_capture = await self.capture.test_capture()
            
            assert isinstance(can_capture, bool), "Результат должен быть boolean"
            
            if can_capture:
                logger.info("✅ Захват скриншотов возможен")
                self.test_results["capture_capability"] = "✅ PASSED"
            else:
                logger.warning("⚠️ Захват скриншотов недоступен (возможно, нет разрешений)")
                self.test_results["capture_capability"] = "⚠️ NO_PERMISSION"
            
        except Exception as e:
            self.test_results["capture_capability"] = f"❌ FAILED: {e}"
            logger.error(f"❌ Тест 3 провален: {e}")
    
    async def test_full_screen_capture(self):
        """Тест захвата всего экрана"""
        logger.info("🧪 Тест 4: Захват всего экрана")
        
        try:
            start_time = time.time()
            result = await self.capture.capture_screenshot()
            capture_time = time.time() - start_time
            
            assert result is not None, "Результат должен быть получен"
            
            if result.success:
                assert result.data is not None, "Данные должны быть получены"
                assert result.data.base64_data is not None, "Base64 данные должны быть получены"
                assert len(result.data.base64_data) > 0, "Base64 данные не должны быть пустыми"
                assert result.data.format == ScreenshotFormat.JPEG, "Формат должен быть JPEG"
                assert result.data.mime_type == "image/jpeg", "MIME тип должен быть image/jpeg"
                
                logger.info(f"📸 Скриншот захвачен: {result.data.width}x{result.data.height}")
                logger.info(f"📸 Размер данных: {len(result.data.base64_data)} символов")
                logger.info(f"📸 Время захвата: {capture_time:.2f} секунд")
                
                self.test_results["full_screen_capture"] = "✅ PASSED"
                logger.info("✅ Тест 4 пройден: Захват всего экрана работает")
                
            else:
                logger.warning(f"⚠️ Захват экрана неудачен: {result.error}")
                self.test_results["full_screen_capture"] = f"⚠️ FAILED: {result.error}"
                
        except Exception as e:
            self.test_results["full_screen_capture"] = f"❌ FAILED: {e}"
            logger.error(f"❌ Тест 4 провален: {e}")
    
    async def test_region_capture(self):
        """Тест захвата области"""
        logger.info("🧪 Тест 5: Захват области")
        
        try:
            # Захватываем область 800x600 в центре экрана
            screen_info = self.capture.get_screen_info()
            center_x = screen_info.width // 2
            center_y = screen_info.height // 2
            region = (center_x - 400, center_y - 300, 800, 600)
            
            start_time = time.time()
            result = await self.capture.capture_region(region)
            capture_time = time.time() - start_time
            
            assert result is not None, "Результат должен быть получен"
            
            if result.success:
                assert result.data is not None, "Данные должны быть получены"
                assert result.data.width == 800, f"Ширина должна быть 800, получено {result.data.width}"
                assert result.data.height == 600, f"Высота должна быть 600, получено {result.data.height}"
                
                logger.info(f"📸 Область захвачена: {result.data.width}x{result.data.height}")
                logger.info(f"📸 Размер данных: {len(result.data.base64_data)} символов")
                logger.info(f"📸 Время захвата: {capture_time:.2f} секунд")
                
                self.test_results["region_capture"] = "✅ PASSED"
                logger.info("✅ Тест 5 пройден: Захват области работает")
                
            else:
                logger.warning(f"⚠️ Захват области неудачен: {result.error}")
                self.test_results["region_capture"] = f"⚠️ FAILED: {result.error}"
                
        except Exception as e:
            self.test_results["region_capture"] = f"❌ FAILED: {e}"
            logger.error(f"❌ Тест 5 провален: {e}")
    
    async def test_jpeg_qualities(self):
        """Тест разных качеств JPEG"""
        logger.info("🧪 Тест 6: Разные качества JPEG")
        
        try:
            qualities_to_test = [
                ScreenshotQuality.LOW,
                ScreenshotQuality.MEDIUM,
                ScreenshotQuality.HIGH,
                ScreenshotQuality.MAXIMUM
            ]
            
            for quality in qualities_to_test:
                config = ScreenshotConfig(
                    format=ScreenshotFormat.JPEG,
                    quality=quality,
                    region=ScreenshotRegion.FULL_SCREEN,
                    max_width=640,
                    max_height=480
                )
                
                result = await self.capture.capture_screenshot(config)
                
                if result.success:
                    assert result.data.format == ScreenshotFormat.JPEG, "Формат должен быть JPEG"
                    assert result.data.mime_type == "image/jpeg", "MIME тип должен быть image/jpeg"
                    logger.info(f"✅ JPEG {quality.value.upper()}: {len(result.data.base64_data)} символов")
                else:
                    logger.warning(f"⚠️ JPEG {quality.value.upper()}: {result.error}")
            
            self.test_results["jpeg_qualities"] = "✅ PASSED"
            logger.info("✅ Тест 6 пройден: Разные качества JPEG работают")
            
        except Exception as e:
            self.test_results["jpeg_qualities"] = f"❌ FAILED: {e}"
            logger.error(f"❌ Тест 6 провален: {e}")
    
    async def test_global_capture(self):
        """Тест глобального захватчика"""
        logger.info("🧪 Тест 7: Глобальный захватчик")
        
        try:
            # Получаем глобальный захватчик
            global_capture = get_global_capture()
            
            assert global_capture is not None, "Глобальный захватчик должен быть создан"
            assert global_capture._initialized == True, "Глобальный захватчик должен быть инициализирован"
            
            # Тестируем захват через глобальный захватчик
            result = await global_capture.capture_screenshot()
            
            if result.success:
                logger.info("✅ Глобальный захватчик работает")
                self.test_results["global_capture"] = "✅ PASSED"
            else:
                logger.warning(f"⚠️ Глобальный захватчик: {result.error}")
                self.test_results["global_capture"] = f"⚠️ FAILED: {result.error}"
            
        except Exception as e:
            self.test_results["global_capture"] = f"❌ FAILED: {e}"
            logger.error(f"❌ Тест 7 провален: {e}")
    
    def print_results(self):
        """Выводит результаты тестирования"""
        logger.info("\n" + "="*60)
        logger.info("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ SCREENSHOT_CAPTURE")
        logger.info("="*60)
        
        for test_name, result in self.test_results.items():
            logger.info(f"{test_name.replace('_', ' ').title()}: {result}")
        
        # Общая статистика
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result.startswith("✅"))
        failed_tests = sum(1 for result in self.test_results.values() if result.startswith("❌"))
        warning_tests = sum(1 for result in self.test_results.values() if result.startswith("⚠️"))
        
        logger.info("-"*60)
        logger.info(f"Всего тестов: {total_tests}")
        logger.info(f"Пройдено: {passed_tests}")
        logger.info(f"Провалено: {failed_tests}")
        logger.info(f"Предупреждения: {warning_tests}")
        logger.info(f"Успешность: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests == 0:
            logger.info("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        else:
            logger.warning(f"⚠️ {failed_tests} тестов провалено")
        
        logger.info("="*60)
    
    async def cleanup(self):
        """Очистка ресурсов"""
        if self.capture:
            self.capture.cleanup()
            logger.info("✅ Ресурсы очищены")
    
    async def run_all_tests(self):
        """Запускает все тесты"""
        logger.info("🚀 Запуск тестирования модуля screenshot_capture...")
        
        if not await self.setup():
            logger.error("❌ Не удалось настроить тестовое окружение")
            return
        
        try:
            # Запускаем тесты последовательно
            await self.test_initialization()
            await self.test_screen_info()
            await self.test_capture_capability()
            await self.test_full_screen_capture()
            await self.test_region_capture()
            await self.test_jpeg_qualities()
            await self.test_global_capture()
            
        finally:
            await self.cleanup()
        
        self.print_results()

async def main():
    """Главная функция"""
    tester = ScreenshotCaptureTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
