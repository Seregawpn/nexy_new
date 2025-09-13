"""
Утилиты для работы с изображениями
"""

import base64
import logging
from typing import Optional, Tuple
from ..core.types import ScreenshotFormat, ScreenshotQuality

logger = logging.getLogger(__name__)

class ImageUtils:
    """Утилиты для работы с изображениями"""
    
    @staticmethod
    def validate_base64(data: str) -> bool:
        """
        Проверяет валидность Base64 строки
        
        Args:
            data: Base64 строка
            
        Returns:
            bool: True если валидна, False иначе
        """
        try:
            # Проверяем базовые требования
            if not data or len(data) < 100:
                return False
            
            # Проверяем символы Base64
            valid_chars = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=')
            if not all(c in valid_chars for c in data):
                return False
            
            # Пытаемся декодировать
            base64.b64decode(data)
            return True
            
        except Exception as e:
            logger.debug(f"Ошибка валидации Base64: {e}")
            return False
    
    @staticmethod
    def get_quality_value(quality: ScreenshotQuality) -> float:
        """
        Получает числовое значение качества
        
        Args:
            quality: Уровень качества
            
        Returns:
            float: Значение качества от 0.0 до 1.0
        """
        quality_map = {
            ScreenshotQuality.LOW: 0.5,
            ScreenshotQuality.MEDIUM: 0.75,
            ScreenshotQuality.HIGH: 0.9,
            ScreenshotQuality.MAXIMUM: 1.0
        }
        return quality_map.get(quality, 0.75)
    
    @staticmethod
    def get_mime_type(format_type: ScreenshotFormat) -> str:
        """
        Получает MIME тип для формата
        
        Args:
            format_type: Тип формата
            
        Returns:
            str: MIME тип
        """
        mime_map = {
            ScreenshotFormat.JPEG: "image/jpeg",
            ScreenshotFormat.PNG: "image/png"
        }
        return mime_map.get(format_type, "image/jpeg")
    
    @staticmethod
    def calculate_compressed_size(original_width: int, original_height: int, 
                                quality: ScreenshotQuality) -> int:
        """
        Оценивает размер сжатого изображения
        
        Args:
            original_width: Исходная ширина
            original_height: Исходная высота
            quality: Качество сжатия
            
        Returns:
            int: Примерный размер в байтах
        """
        # Базовый размер для JPEG (примерно)
        base_size = original_width * original_height * 3  # RGB
        
        # Коэффициент сжатия в зависимости от качества
        compression_ratio = ImageUtils.get_quality_value(quality)
        
        # Примерный размер после сжатия
        compressed_size = int(base_size * compression_ratio)
        
        return max(compressed_size, 1000)  # Минимум 1KB
    
    @staticmethod
    def resize_dimensions(width: int, height: int, max_width: int, max_height: int) -> Tuple[int, int]:
        """
        Изменяет размеры изображения с сохранением пропорций
        
        Args:
            width: Исходная ширина
            height: Исходная высота
            max_width: Максимальная ширина
            max_height: Максимальная высота
            
        Returns:
            Tuple[int, int]: Новые размеры (width, height)
        """
        if width <= max_width and height <= max_height:
            return width, height
        
        # Вычисляем коэффициент масштабирования
        width_ratio = max_width / width
        height_ratio = max_height / height
        scale_ratio = min(width_ratio, height_ratio)
        
        new_width = int(width * scale_ratio)
        new_height = int(height * scale_ratio)
        
        return new_width, new_height
    
    @staticmethod
    def validate_dimensions(width: int, height: int, max_width: int = None, max_height: int = None) -> bool:
        """
        Проверяет валидность размеров изображения
        
        Args:
            width: Ширина
            height: Высота
            max_width: Максимальная ширина
            max_height: Максимальная высота
            
        Returns:
            bool: True если размеры валидны, False иначе
        """
        # Проверяем базовые требования
        if width <= 0 or height <= 0:
            return False
        
        if width > 10000 or height > 10000:
            return False
        
        # Проверяем максимальные размеры
        if max_width and width > max_width:
            return False
        
        if max_height and height > max_height:
            return False
        
        return True
    
    @staticmethod
    def estimate_capture_time(width: int, height: int, quality: ScreenshotQuality) -> float:
        """
        Оценивает время захвата скриншота
        
        Args:
            width: Ширина
            height: Высота
            quality: Качество
            
        Returns:
            float: Примерное время в секундах
        """
        # Базовое время для захвата
        base_time = 0.1  # 100ms
        
        # Время зависит от размера изображения
        pixel_count = width * height
        size_factor = pixel_count / (1920 * 1080)  # Нормализация к Full HD
        
        # Время зависит от качества
        quality_factor = ImageUtils.get_quality_value(quality)
        
        # Общее время
        total_time = base_time + (size_factor * 0.2) + (quality_factor * 0.1)
        
        return min(total_time, 2.0)  # Максимум 2 секунды
