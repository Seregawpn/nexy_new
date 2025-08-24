import base64
import io
import logging
from PIL import Image
import numpy as np
from Quartz import (
    CGDisplayBounds,
    CGMainDisplayID,
    CGWindowListCreateImage,
    kCGWindowListOptionOnScreenOnly,
    kCGNullWindowID,
    CGImageGetDataProvider,
    CGDataProviderCopyData,
    CGImageGetWidth,
    CGImageGetHeight,
    CGImageGetBytesPerRow,
    CGImageGetBitsPerPixel,
    CGImageGetColorSpace,
    CGColorSpaceGetModel,
    kCGColorSpaceModelRGB
)

logger = logging.getLogger(__name__)

class ScreenCapture:
    """Захват экрана macOS с конвертацией в WebP + Base64"""
    
    def __init__(self):
        self.main_display_id = CGMainDisplayID()
        self.display_bounds = CGDisplayBounds(self.main_display_id)
        
    def capture_screen(self, quality: int = 85) -> str:
        """
        Захватывает экран и возвращает Base64 строку WebP изображения
        
        Args:
            quality (int): Качество WebP (1-100)
            
        Returns:
            str: Base64 строка WebP изображения
        """
        try:
            logger.info("Начинаю захват экрана...")
            
            # Захватываем изображение экрана
            image = CGWindowListCreateImage(
                self.display_bounds,
                kCGWindowListOptionOnScreenOnly,
                kCGNullWindowID,
                kCGNullWindowID
            )
            
            if not image:
                logger.error("Не удалось захватить экран")
                return None
            
            # Получаем размеры изображения
            width = CGImageGetWidth(image)
            height = CGImageGetHeight(image)
            bytes_per_row = CGImageGetBytesPerRow(image)
            bits_per_pixel = CGImageGetBitsPerPixel(image)
            
            logger.info(f"Изображение: {width}x{height}, {bits_per_pixel} бит/пиксель, {bytes_per_row} байт/строка")
            
            # Получаем данные изображения
            data_provider = CGImageGetDataProvider(image)
            if not data_provider:
                logger.error("Не удалось получить data provider")
                return None
                
            raw_data = CGDataProviderCopyData(data_provider)
            if not raw_data:
                logger.error("Не удалось получить raw data")
                return None
            
            # Конвертируем в numpy array
            data_length = len(raw_data)
            logger.info(f"Получено {data_length} байт данных")
            
            # Определяем формат данных
            if bits_per_pixel == 32:
                # RGBA или BGRA
                if bytes_per_row == width * 4:
                    # Стандартный формат
                    array = np.frombuffer(raw_data, dtype=np.uint8)
                    array = array.reshape((height, width, 4))
                    
                    # Конвертируем BGRA в RGB
                    rgb_array = array[:, :, [2, 1, 0]]  # BGR -> RGB
                    
                else:
                    # Нестандартный формат, используем оригинальные размеры
                    array = np.frombuffer(raw_data, dtype=np.uint8)
                    array = array.reshape((height, bytes_per_row // 4, 4))
                    rgb_array = array[:, :width, [2, 1, 0]]
                    
            elif bits_per_pixel == 24:
                # RGB
                array = np.frombuffer(raw_data, dtype=np.uint8)
                array = array.reshape((height, width, 3))
                rgb_array = array
                
            else:
                logger.error(f"Неподдерживаемый формат: {bits_per_pixel} бит/пиксель")
                return None
            
            # Конвертируем в PIL Image
            pil_image = Image.fromarray(rgb_array)
            
            logger.info(f"Экран захвачен: {width}x{height} пикселей")
            
            # Конвертируем в WebP с указанным качеством
            webp_buffer = io.BytesIO()
            pil_image.save(
                webp_buffer,
                format='WEBP',
                quality=quality,
                method=6,  # Метод сжатия WebP (0-6, где 6 - лучшее качество)
                lossless=False  # Сжатие с потерями для лучшего размера
            )
            
            webp_data = webp_buffer.getvalue()
            webp_buffer.close()
            
            logger.info(f"WebP создан: {len(webp_data)} байт")
            
            # Конвертируем в Base64
            base64_string = base64.b64encode(webp_data).decode('utf-8')
            
            logger.info(f"Base64 создан: {len(base64_string)} символов")
            
            return base64_string
            
        except Exception as e:
            logger.error(f"Ошибка захвата экрана: {e}")
            return None
    
    def capture_active_window(self, quality: int = 85) -> str:
        """
        Захватывает активное окно (если возможно)
        
        Args:
            quality (int): Качество WebP (1-100)
            
        Returns:
            str: Base64 строка WebP изображения
        """
        try:
            logger.info("Начинаю захват активного окна...")
            
            # Пока что захватываем весь экран
            # TODO: Добавить логику определения активного окна
            return self.capture_screen(quality)
            
        except Exception as e:
            logger.error(f"Ошибка захвата активного окна: {e}")
            return None
    
    def get_screen_info(self) -> dict:
        """
        Возвращает информацию об экране
        
        Returns:
            dict: Информация об экране
        """
        try:
            width = int(self.display_bounds.size.width)
            height = int(self.display_bounds.size.height)
            
            return {
                'width': width,
                'height': height,
                'main_display_id': self.main_display_id,
                'bounds': {
                    'x': int(self.display_bounds.origin.x),
                    'y': int(self.display_bounds.origin.y),
                    'width': width,
                    'height': height
                }
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения информации об экране: {e}")
            return {}

if __name__ == "__main__":
    # Тест захвата экрана
    import logging
    logging.basicConfig(level=logging.INFO)
    
    capture = ScreenCapture()
    
    # Получаем информацию об экране
    info = capture.get_screen_info()
    print(f"Информация об экране: {info}")
    
    # Захватываем экран
    print("Захватываю экран...")
    base64_webp = capture.capture_screen(quality=80)
    
    if base64_webp:
        print(f"✅ Захват успешен!")
        print(f"Base64 длина: {len(base64_webp)} символов")
        print(f"Первые 100 символов: {base64_webp[:100]}...")
        
        # Сохраняем для проверки
        try:
            decoded = base64.b64decode(base64_webp)
            with open("test_screenshot.webp", "wb") as f:
                f.write(decoded)
            print("💾 Скриншот сохранен как test_screenshot.webp")
        except Exception as e:
            print(f"❌ Ошибка сохранения: {e}")
    else:
        print("❌ Захват не удался")
