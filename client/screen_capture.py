#!/usr/bin/env python3
"""
📸 РЕАЛЬНЫЙ ЗАХВАТ ЭКРАНА ЧЕРЕЗ MSS
🎯 Быстрый и надежный захват экрана только через mss

✅ ПРИОРИТЕТ: mss (быстрый, Windows/Linux/macOS)
"""

import base64
import io
import logging
from PIL import Image

logger = logging.getLogger(__name__)

class ScreenCapture:
    """Реальный захват экрана через mss"""
    
    def __init__(self):
        logger.info("📸 Инициализирую захват экрана через mss...")
        
        # Проверяем доступность mss
        self.mss_available = False
        
        try:
            import mss
            self.mss_available = True
            logger.info("✅ mss доступен для быстрого захвата экрана")
        except ImportError:
            logger.error("❌ mss не установлен - используйте: pip install mss")
            raise ImportError("mss не установлен. Установите: pip install mss")
    
    def capture_screen(self, quality: int = 85, max_size: int = 1024) -> str:
        """
        Захватывает реальный экран через mss
        
        Args:
            quality (int): Качество JPEG (1-100)
            max_size (int): Максимальный размер стороны изображения
            
        Returns:
            str: Base64 строка JPEG изображения
            
        Raises:
            RuntimeError: Если не удалось захватить экран
        """
        try:
            logger.info("📸 Захватываю реальный экран через mss...")
            
            if not self.mss_available:
                error_msg = "❌ mss недоступен для захвата экрана!"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            
            import mss
            with mss.mss() as sct:
                # Получаем основной монитор
                monitor = sct.monitors[1]  # Основной монитор
                logger.info(f"📱 Захватываю монитор: {monitor}")
                
                # Захватываем экран
                pil_image = sct.grab(monitor)
                
                # Конвертируем в PIL Image
                pil_image = Image.frombytes('RGB', pil_image.size, pil_image.bgra, 'raw', 'BGRX')
                
                logger.info(f"✅ Реальный экран захвачен: {pil_image.size[0]}x{pil_image.size[1]} пикселей")
                return self._convert_to_base64(pil_image, quality)
                
        except Exception as e:
            error_msg = f"❌ Критическая ошибка захвата экрана через mss: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def _convert_to_base64(self, pil_image: Image.Image, quality: int) -> str:
        """Конвертирует PIL изображение в Base64 JPEG"""
        try:
            # Конвертируем в JPEG с указанным качеством
            jpeg_buffer = io.BytesIO()
            pil_image.save(
                jpeg_buffer,
                format='JPEG',
                quality=quality,
                optimize=True
            )
            
            jpeg_data = jpeg_buffer.getvalue()
            jpeg_buffer.close()
            
            logger.info(f"💾 JPEG создан: {len(jpeg_data)} байт")
            
            # Конвертируем в Base64
            base64_string = base64.b64encode(jpeg_data).decode('utf-8')
            
            logger.info(f"🔤 Base64 создан: {len(base64_string)} символов")
            logger.info("✅ Реальный экран успешно захвачен и конвертирован в Base64!")
            
            return base64_string
                
        except Exception as e:
            error_msg = f"❌ Ошибка конвертации в Base64: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def capture_active_window(self, quality: int = 85, max_size: int = 1024) -> str:
        """
        Захватывает активное окно (через mss)
        
        Args:
            quality (int): Качество JPEG (1-100)
            max_size (int): Максимальный размер стороны изображения
            
        Returns:
            str: Base64 строка JPEG изображения
        """
        try:
            logger.info("🪟 Захватываю активное окно через mss...")
            
            # Через mss захватываем весь экран (активное окно будет видно)
            return self.capture_screen(quality, max_size)
                
        except Exception as e:
            error_msg = f"❌ Ошибка захвата активного окна: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def get_screen_info(self) -> dict:
        """
        Возвращает реальную информацию об экране через mss
        
        Returns:
            dict: Информация об экране
        """
        try:
            if not self.mss_available:
                logger.warning("⚠️ mss недоступен, возвращаю базовую информацию")
                return self._get_default_screen_info()
            
            import mss
            with mss.mss() as sct:
                monitor = sct.monitors[1]  # Основной монитор
                logger.info(f"📱 Реальная информация об экране через mss: {monitor}")
                return {
                    'width': monitor['width'],
                    'height': monitor['height'],
                    'main_display_id': 1,
                    'bounds': monitor
                }
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения информации об экране: {e}")
            return self._get_default_screen_info()
    
    def _get_default_screen_info(self) -> dict:
        """Возвращает базовую информацию об экране по умолчанию"""
        return {
            'width': 1920,
            'height': 1080,
            'main_display_id': 1,
            'bounds': {
                'x': 0,
                'y': 0,
                'width': 1920,
                'height': 1080
            }
        }

if __name__ == "__main__":
    # Настройка логирования
    logging.basicConfig(level=logging.INFO)
    
    # Тестируем реальный захват через mss
    capture = ScreenCapture()
    
    # Получаем информацию об экране
    info = capture.get_screen_info()
    print(f"📱 Информация об экране: {info}")
    
    # Создаем реальный скриншот
    print("📸 Захватываю реальный экран через mss...")
    try:
        screenshot_data = capture.capture_screen(quality=85, max_size=1024)
        if screenshot_data:
            print(f"✅ Реальный скриншот создан!")
            print(f"Base64 длина: {len(screenshot_data)} символов")
            print(f"Первые 100 символов: {screenshot_data[:100]}...")
            
            # Сохраняем для проверки
            try:
                jpeg_data = base64.b64decode(screenshot_data)
                with open("test_screenshot_mss.jpg", "wb") as f:
                    f.write(jpeg_data)
                print(f"💾 Реальный скриншот сохранен как test_screenshot_mss.jpg ({len(jpeg_data)} байт)")
            except Exception as e:
                print(f"❌ Ошибка сохранения: {e}")
        else:
            print("❌ Создание реального скриншота не удалось")
    except RuntimeError as e:
        print(f"❌ Ошибка захвата экрана: {e}")
