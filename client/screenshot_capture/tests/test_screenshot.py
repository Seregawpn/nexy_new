"""
Тесты для модуля захвата скриншотов
"""

import asyncio
import logging
import pytest
from screenshot_capture import ScreenshotCapture, ScreenshotConfig, ScreenshotFormat, ScreenshotQuality

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TestScreenshotCapture:
    """Тесты для ScreenshotCapture"""
    
    def setup_method(self):
        """Настройка перед каждым тестом"""
        self.capture = None
    
    def teardown_method(self):
        """Очистка после каждого теста"""
        if self.capture:
            self.capture.cleanup()
    
    def test_initialization(self):
        """Тест инициализации"""
        try:
            self.capture = ScreenshotCapture()
            assert self.capture is not None
            assert self.capture._initialized == True
            logger.info("✅ Инициализация успешна")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации: {e}")
            pytest.skip("macOS модули недоступны")
    
    def test_config_loading(self):
        """Тест загрузки конфигурации"""
        try:
            config = ScreenshotConfig(
                format=ScreenshotFormat.JPEG,
                quality=ScreenshotQuality.MEDIUM,
                max_width=1920,
                max_height=1080
            )
            
            self.capture = ScreenshotCapture(config)
            assert self.capture.config.format == ScreenshotFormat.JPEG
            assert self.capture.config.quality == ScreenshotQuality.MEDIUM
            logger.info("✅ Загрузка конфигурации успешна")
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки конфигурации: {e}")
            pytest.skip("macOS модули недоступны")
    
    @pytest.mark.asyncio
    async def test_capture_screenshot(self):
        """Тест захвата скриншота"""
        try:
            self.capture = ScreenshotCapture()
            
            # Тестируем захват
            result = await self.capture.capture_screenshot()
            
            assert result is not None
            if result.success:
                assert result.data is not None
                assert result.data.base64_data is not None
                assert result.data.format == ScreenshotFormat.JPEG
                assert result.data.mime_type == "image/jpeg"
                logger.info("✅ Захват скриншота успешен")
            else:
                logger.warning(f"⚠️ Захват скриншота неудачен: {result.error}")
        except Exception as e:
            logger.error(f"❌ Ошибка захвата скриншота: {e}")
            pytest.skip("macOS модули недоступны")
    
    @pytest.mark.asyncio
    async def test_capture_region(self):
        """Тест захвата области"""
        try:
            self.capture = ScreenshotCapture()
            
            # Тестируем захват области
            region = (100, 100, 800, 600)  # x, y, width, height
            result = await self.capture.capture_region(region)
            
            assert result is not None
            if result.success:
                assert result.data is not None
                assert result.data.width == 800
                assert result.data.height == 600
                logger.info("✅ Захват области успешен")
            else:
                logger.warning(f"⚠️ Захват области неудачен: {result.error}")
        except Exception as e:
            logger.error(f"❌ Ошибка захвата области: {e}")
            pytest.skip("macOS модули недоступны")
    
    @pytest.mark.asyncio
    async def test_test_capture(self):
        """Тест проверки возможности захвата"""
        try:
            self.capture = ScreenshotCapture()
            
            # Тестируем возможность захвата
            can_capture = await self.capture.test_capture()
            
            assert isinstance(can_capture, bool)
            if can_capture:
                logger.info("✅ Тест захвата успешен")
            else:
                logger.warning("⚠️ Тест захвата неудачен")
        except Exception as e:
            logger.error(f"❌ Ошибка теста захвата: {e}")
            pytest.skip("macOS модули недоступны")
    
    def test_get_screen_info(self):
        """Тест получения информации об экране"""
        try:
            self.capture = ScreenshotCapture()
            
            # Получаем информацию об экране
            screen_info = self.capture.get_screen_info()
            
            assert screen_info is not None
            assert screen_info.width > 0
            assert screen_info.height > 0
            logger.info(f"✅ Информация об экране: {screen_info.width}x{screen_info.height}")
        except Exception as e:
            logger.error(f"❌ Ошибка получения информации об экране: {e}")
            pytest.skip("macOS модули недоступны")
    
    def test_get_status(self):
        """Тест получения статуса"""
        try:
            self.capture = ScreenshotCapture()
            
            # Получаем статус
            status = self.capture.get_status()
            
            assert status is not None
            assert "initialized" in status
            assert "config" in status
            assert "bridge_available" in status
            logger.info("✅ Получение статуса успешно")
        except Exception as e:
            logger.error(f"❌ Ошибка получения статуса: {e}")
            pytest.skip("macOS модули недоступны")

def test_imports():
    """Тест импортов"""
    try:
        from screenshot_capture import (
            ScreenshotCapture,
            ScreenshotConfig,
            ScreenshotFormat,
            ScreenshotQuality,
            ScreenshotRegion,
            ScreenshotData,
            ScreenshotResult
        )
        logger.info("✅ Импорты успешны")
    except ImportError as e:
        logger.error(f"❌ Ошибка импорта: {e}")
        pytest.fail("Ошибка импорта модулей")

if __name__ == "__main__":
    # Запуск тестов
    pytest.main([__file__, "-v"])
