"""
Тестовый bridge для разработки и отладки
Генерирует фиктивные скриншоты для тестирования интеграции
"""

import time
import base64
import logging
from typing import Tuple, Dict, Any
from pathlib import Path

from ..core.types import ScreenshotResult, ScreenshotConfig, ScreenshotData, ScreenshotFormat

logger = logging.getLogger(__name__)


class TestCoreGraphicsBridge:
    """Тестовый bridge для разработки"""
    
    def __init__(self):
        """Инициализация тестового bridge"""
        self.initialized = True
        logger.info("✅ TestCoreGraphicsBridge инициализирован")
    
    def capture_full_screen(self, config: ScreenshotConfig) -> ScreenshotResult:
        """
        Имитирует захват полного экрана
        
        Args:
            config: Конфигурация захвата
            
        Returns:
            ScreenshotResult: Фиктивный результат захвата
        """
        try:
            start_time = time.time()
            
            # Имитируем время захвата
            time.sleep(0.1)
            
            # Создаем фиктивное изображение (1x1 пиксель JPEG)
            # Это минимальный валидный JPEG файл
            fake_jpeg_data = bytes([
                0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46,
                0x49, 0x46, 0x00, 0x01, 0x01, 0x01, 0x00, 0x48,
                0x00, 0x48, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
                0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08,
                0x07, 0x07, 0x07, 0x09, 0x09, 0x08, 0x0A, 0x0C,
                0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12,
                0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D,
                0x1A, 0x1C, 0x1C, 0x20, 0x24, 0x2E, 0x27, 0x20,
                0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29,
                0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27,
                0x39, 0x3D, 0x38, 0x32, 0x3C, 0x2E, 0x33, 0x34,
                0x32, 0xFF, 0xC0, 0x00, 0x11, 0x08, 0x00, 0x01,
                0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0x02, 0x11,
                0x01, 0x03, 0x11, 0x01, 0xFF, 0xC4, 0x00, 0x14,
                0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                0x00, 0x08, 0xFF, 0xC4, 0x00, 0x14, 0x10, 0x01,
                0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                0xFF, 0xDA, 0x00, 0x0C, 0x03, 0x01, 0x00, 0x02,
                0x11, 0x03, 0x11, 0x00, 0x3F, 0x00, 0x2A, 0xFF, 0xD9
            ])
            
            base64_data = base64.b64encode(fake_jpeg_data).decode('utf-8')
            
            # Применяем размеры из конфигурации или используем по умолчанию
            width = min(config.max_width, 1920) if config.max_width > 0 else 1920
            height = min(config.max_height, 1080) if config.max_height > 0 else 1080
            
            screenshot_data = ScreenshotData(
                base64_data=base64_data,
                width=width,
                height=height,
                format=ScreenshotFormat.JPEG,
                size_bytes=len(fake_jpeg_data),
                mime_type="image/jpeg",
                metadata={
                    "bridge_type": "test",
                    "capture_method": "fake_generation",
                    "timestamp": time.time()
                }
            )
            
            capture_time = time.time() - start_time
            logger.info(f"✅ Тестовый скриншот создан: {width}x{height}, {len(fake_jpeg_data)} bytes, {capture_time:.3f}s")
            
            return ScreenshotResult(
                success=True,
                data=screenshot_data,
                capture_time=capture_time
            )
            
        except Exception as e:
            error_msg = f"Test screenshot generation error: {e}"
            logger.error(f"❌ {error_msg}")
            return ScreenshotResult(
                success=False,
                error=error_msg,
                capture_time=time.time() - start_time if 'start_time' in locals() else 0.0
            )
    
    def capture_region(self, region: Tuple[int, int, int, int], config: ScreenshotConfig) -> ScreenshotResult:
        """
        Имитирует захват области экрана
        
        Args:
            region: Область (x, y, width, height)
            config: Конфигурация захвата
            
        Returns:
            ScreenshotResult: Фиктивный результат захвата области
        """
        try:
            start_time = time.time()
            x, y, width, height = region
            
            # Имитируем время захвата
            time.sleep(0.05)
            
            # Используем тот же фиктивный JPEG
            fake_jpeg_data = bytes([
                0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46,
                0x49, 0x46, 0x00, 0x01, 0x01, 0x01, 0x00, 0x48,
                0x00, 0x48, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
                0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08,
                0x07, 0x07, 0x07, 0x09, 0x09, 0x08, 0x0A, 0x0C,
                0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12,
                0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D,
                0x1A, 0x1C, 0x1C, 0x20, 0x24, 0x2E, 0x27, 0x20,
                0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29,
                0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27,
                0x39, 0x3D, 0x38, 0x32, 0x3C, 0x2E, 0x33, 0x34,
                0x32, 0xFF, 0xC0, 0x00, 0x11, 0x08, 0x00, 0x01,
                0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0x02, 0x11,
                0x01, 0x03, 0x11, 0x01, 0xFF, 0xC4, 0x00, 0x14,
                0x00, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                0x00, 0x08, 0xFF, 0xC4, 0x00, 0x14, 0x10, 0x01,
                0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                0xFF, 0xDA, 0x00, 0x0C, 0x03, 0x01, 0x00, 0x02,
                0x11, 0x03, 0x11, 0x00, 0x3F, 0x00, 0x2A, 0xFF, 0xD9
            ])
            
            base64_data = base64.b64encode(fake_jpeg_data).decode('utf-8')
            
            screenshot_data = ScreenshotData(
                base64_data=base64_data,
                width=width,
                height=height,
                format=ScreenshotFormat.JPEG,
                size_bytes=len(fake_jpeg_data),
                mime_type="image/jpeg",
                metadata={
                    "bridge_type": "test",
                    "capture_method": "fake_generation",
                    "timestamp": time.time()
                }
            )
            
            capture_time = time.time() - start_time
            logger.info(f"✅ Тестовая область захвачена: {width}x{height}, {len(fake_jpeg_data)} bytes, {capture_time:.3f}s")
            
            return ScreenshotResult(
                success=True,
                data=screenshot_data,
                capture_time=capture_time
            )
            
        except Exception as e:
            error_msg = f"Test region capture error: {e}"
            logger.error(f"❌ {error_msg}")
            return ScreenshotResult(
                success=False,
                error=error_msg,
                capture_time=time.time() - start_time if 'start_time' in locals() else 0.0
            )
    
    def test_capture(self) -> bool:
        """
        Тестирует возможность захвата (всегда возвращает True для тестового bridge)
        
        Returns:
            bool: True (тестовый bridge всегда доступен)
        """
        logger.info("✅ Test bridge capture test passed")
        return True
    
    def get_screen_info(self) -> Dict[str, Any]:
        """
        Возвращает фиктивную информацию об экране
        
        Returns:
            dict: Тестовая информация об экране
        """
        return {
            "displays": [
                {
                    "_name": "Test Display",
                    "_spdisplays_resolution": "1920 x 1080",
                    "_spdisplays_pixeldepth": "32-Bit Color",
                    "_spdisplays_main": "spdisplays_yes"
                }
            ],
            "primary_display": {
                "_name": "Test Display",
                "_spdisplays_resolution": "1920 x 1080",
                "_spdisplays_pixeldepth": "32-Bit Color",
                "_spdisplays_main": "spdisplays_yes"
            },
            "resolution": "1920 x 1080",
            "pixel_depth": "32-Bit Color",
            "main_display": "spdisplays_yes",
            "bridge_type": "test"
        }
