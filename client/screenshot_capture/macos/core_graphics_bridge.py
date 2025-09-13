"""
Core Graphics bridge для захвата скриншотов на macOS
"""

import logging
import time
from typing import Optional, Tuple
from ..core.types import ScreenshotResult, ScreenshotData, ScreenshotConfig, ScreenshotFormat, ScreenshotQuality, ScreenInfo, ScreenshotError, ScreenshotPermissionError, ScreenshotCaptureError

logger = logging.getLogger(__name__)

try:
    # macOS специфичные импорты
    from AppKit import NSScreen, NSApplication, NSData
    from Foundation import NSData as FoundationNSData
    from Quartz import CGImageGetWidth, CGImageGetHeight, CGImageGetDataProvider, CGDataProviderCopyData
    from Quartz.CoreGraphics import CGImageRef, CGDisplayCreateImage, CGDisplayBounds, CGMainDisplayID, CGDisplayCreateImageForRect
    MACOS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠️ macOS модули недоступны: {e}")
    MACOS_AVAILABLE = False

class CoreGraphicsBridge:
    """Bridge для работы с Core Graphics API на macOS"""
    
    def __init__(self):
        """Инициализирует bridge"""
        if not MACOS_AVAILABLE:
            raise ImportError("macOS модули недоступны. Установите PyObjC.")
        
        self._check_permissions()
    
    def _check_permissions(self):
        """Проверяет права доступа к экрану"""
        try:
            # Пытаемся получить информацию об экране
            screen = NSScreen.mainScreen()
            if not screen:
                raise ScreenshotPermissionError("Нет доступа к экрану. Проверьте права Screen Recording в System Preferences.")
            
            logger.info("✅ Права доступа к экрану проверены")
        except Exception as e:
            raise ScreenshotPermissionError(f"Ошибка проверки прав доступа: {e}")
    
    def get_screen_info(self) -> ScreenInfo:
        """Получает информацию об экране"""
        try:
            screen = NSScreen.mainScreen()
            if not screen:
                raise ScreenshotCaptureError("Не удалось получить информацию об экране")
            
            frame = screen.frame()
            scale_factor = screen.backingScaleFactor()
            
            return ScreenInfo(
                width=int(frame.size.width),
                height=int(frame.size.height),
                scale_factor=scale_factor,
                color_depth=24,  # Стандартная глубина цвета
                refresh_rate=60,  # Стандартная частота обновления
                primary=True,
                monitor_name="Main Display"
            )
        except Exception as e:
            logger.error(f"❌ Ошибка получения информации об экране: {e}")
            raise ScreenshotCaptureError(f"Ошибка получения информации об экране: {e}")
    
    def capture_full_screen(self, config: ScreenshotConfig) -> ScreenshotResult:
        """Захватывает весь экран"""
        start_time = time.time()
        
        try:
            # Получаем информацию об экране
            screen_info = self.get_screen_info()
            
            # Получаем ID основного дисплея
            display_id = CGMainDisplayID()
            
            # Захватываем изображение
            image_ref = CGDisplayCreateImage(display_id)
            if not image_ref:
                raise ScreenshotCaptureError("Не удалось захватить изображение экрана")
            
            # Получаем размеры изображения
            width = CGImageGetWidth(image_ref)
            height = CGImageGetHeight(image_ref)
            
            # Применяем ограничения размера
            if config.max_width and width > config.max_width:
                height = int(height * config.max_width / width)
                width = config.max_width
            
            if config.max_height and height > config.max_height:
                width = int(width * config.max_height / height)
                height = config.max_height
            
            # Конвертируем в JPEG
            jpeg_data = self._convert_to_jpeg(image_ref, config)
            
            # Создаем Base64 строку
            base64_data = jpeg_data.base64EncodedStringWithOptions_(0)
            
            # Создаем результат
            screenshot_data = ScreenshotData(
                base64_data=base64_data,
                format=ScreenshotFormat.JPEG,
                width=width,
                height=height,
                size_bytes=len(base64_data),
                mime_type="image/jpeg",
                metadata={
                    "display_id": display_id,
                    "scale_factor": screen_info.scale_factor,
                    "capture_method": "core_graphics"
                }
            )
            
            capture_time = time.time() - start_time
            
            return ScreenshotResult(
                success=True,
                data=screenshot_data,
                screen_info=screen_info,
                capture_time=capture_time
            )
            
        except ScreenshotError:
            raise
        except Exception as e:
            logger.error(f"❌ Ошибка захвата экрана: {e}")
            return ScreenshotResult(
                success=False,
                error=f"Ошибка захвата экрана: {e}",
                capture_time=time.time() - start_time
            )
    
    def capture_region(self, region: Tuple[int, int, int, int], config: ScreenshotConfig) -> ScreenshotResult:
        """Захватывает указанную область экрана"""
        start_time = time.time()
        
        try:
            x, y, width, height = region
            
            # Получаем информацию об экране
            screen_info = self.get_screen_info()
            
            # Получаем ID основного дисплея
            display_id = CGMainDisplayID()
            
            # Создаем прямоугольник для захвата
            from CoreGraphics import CGRectMake
            rect = CGRectMake(x, y, width, height)
            
            # Захватываем изображение области
            image_ref = CGDisplayCreateImageForRect(display_id, rect)
            if not image_ref:
                raise ScreenshotCaptureError("Не удалось захватить изображение области")
            
            # Конвертируем в JPEG
            jpeg_data = self._convert_to_jpeg(image_ref, config)
            
            # Создаем Base64 строку
            base64_data = jpeg_data.base64EncodedStringWithOptions_(0)
            
            # Создаем результат
            screenshot_data = ScreenshotData(
                base64_data=base64_data,
                format=ScreenshotFormat.JPEG,
                width=width,
                height=height,
                size_bytes=len(base64_data),
                mime_type="image/jpeg",
                metadata={
                    "display_id": display_id,
                    "region": region,
                    "scale_factor": screen_info.scale_factor,
                    "capture_method": "core_graphics_region"
                }
            )
            
            capture_time = time.time() - start_time
            
            return ScreenshotResult(
                success=True,
                data=screenshot_data,
                screen_info=screen_info,
                capture_time=capture_time
            )
            
        except ScreenshotError:
            raise
        except Exception as e:
            logger.error(f"❌ Ошибка захвата области: {e}")
            return ScreenshotResult(
                success=False,
                error=f"Ошибка захвата области: {e}",
                capture_time=time.time() - start_time
            )
    
    def _convert_to_jpeg(self, image_ref: CGImageRef, config: ScreenshotConfig) -> NSData:
        """Конвертирует CGImage в JPEG NSData"""
        try:
            # Получаем размеры изображения
            width = CGImageGetWidth(image_ref)
            height = CGImageGetHeight(image_ref)
            
            # Создаем NSImage из CGImage
            from AppKit import NSImage, NSBitmapImageRep, NSJPEGFileType
            
            # Создаем NSImage
            ns_image = NSImage.alloc().initWithCGImage_size_(image_ref, (width, height))
            if not ns_image:
                raise ScreenshotCaptureError("Не удалось создать NSImage")
            
            # Создаем bitmap representation
            bitmap_rep = NSBitmapImageRep.alloc().initWithData_(ns_image.TIFFRepresentation())
            if not bitmap_rep:
                raise ScreenshotCaptureError("Не удалось создать bitmap representation")
            
            # Определяем качество JPEG (оптимизировано для меньшего размера)
            quality_map = {
                ScreenshotQuality.LOW: 0.3,      # 30% - очень быстро, маленький размер
                ScreenshotQuality.MEDIUM: 0.5,   # 50% - сбалансированно
                ScreenshotQuality.HIGH: 0.7,     # 70% - хорошее качество
                ScreenshotQuality.MAXIMUM: 0.9   # 90% - максимальное качество
            }
            
            quality = quality_map.get(config.quality, 0.8)  # 50% по умолчанию
            
            # Конвертируем в JPEG
            jpeg_data = bitmap_rep.representationUsingType_properties_(
                NSJPEGFileType,
                {"NSImageCompressionFactor": quality}
            )
            
            if not jpeg_data:
                raise ScreenshotCaptureError("Не удалось конвертировать в JPEG")
            
            return jpeg_data
            
        except Exception as e:
            logger.error(f"❌ Ошибка конвертации в JPEG: {e}")
            raise ScreenshotCaptureError(f"Ошибка конвертации в JPEG: {e}")
    
    def test_capture(self) -> bool:
        """Тестирует возможность захвата скриншота"""
        try:
            # Пытаемся захватить небольшой тестовый скриншот
            display_id = CGMainDisplayID()
            image_ref = CGDisplayCreateImage(display_id)
            
            if image_ref:
                logger.info("✅ Тест захвата скриншота успешен")
                return True
            else:
                logger.error("❌ Тест захвата скриншота неудачен")
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка теста захвата: {e}")
            return False
