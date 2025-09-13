"""
Утилиты для работы с Base64
"""

import base64
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

class Base64Utils:
    """Утилиты для работы с Base64"""
    
    @staticmethod
    def encode_to_base64(data: bytes) -> str:
        """
        Кодирует данные в Base64
        
        Args:
            data: Бинарные данные
            
        Returns:
            str: Base64 строка
        """
        try:
            encoded = base64.b64encode(data)
            return encoded.decode('utf-8')
        except Exception as e:
            logger.error(f"❌ Ошибка кодирования Base64: {e}")
            raise
    
    @staticmethod
    def decode_from_base64(data: str) -> bytes:
        """
        Декодирует Base64 строку
        
        Args:
            data: Base64 строка
            
        Returns:
            bytes: Бинарные данные
        """
        try:
            return base64.b64decode(data)
        except Exception as e:
            logger.error(f"❌ Ошибка декодирования Base64: {e}")
            raise
    
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
            if not data:
                return False
            
            # Проверяем длину
            if len(data) < 100:
                return False
            
            # Проверяем символы
            valid_chars = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=')
            if not all(c in valid_chars for c in data):
                return False
            
            # Пытаемся декодировать
            base64.b64decode(data)
            return True
            
        except Exception:
            return False
    
    @staticmethod
    def get_base64_info(data: str) -> dict:
        """
        Получает информацию о Base64 строке
        
        Args:
            data: Base64 строка
            
        Returns:
            dict: Информация о строке
        """
        try:
            if not data:
                return {"valid": False, "error": "Пустая строка"}
            
            # Проверяем валидность
            if not Base64Utils.validate_base64(data):
                return {"valid": False, "error": "Невалидная Base64 строка"}
            
            # Декодируем для получения размера
            decoded = base64.b64decode(data)
            
            return {
                "valid": True,
                "length": len(data),
                "decoded_size": len(decoded),
                "compression_ratio": len(data) / len(decoded) if len(decoded) > 0 else 0,
                "starts_with": data[:20] + "..." if len(data) > 20 else data,
                "ends_with": "..." + data[-20:] if len(data) > 20 else data
            }
            
        except Exception as e:
            return {"valid": False, "error": str(e)}
    
    @staticmethod
    def estimate_original_size(base64_data: str) -> int:
        """
        Оценивает размер исходных данных по Base64
        
        Args:
            base64_data: Base64 строка
            
        Returns:
            int: Примерный размер исходных данных
        """
        try:
            # Base64 увеличивает размер на ~33%
            # Убираем padding символы для более точной оценки
            clean_data = base64_data.rstrip('=')
            estimated_size = int(len(clean_data) * 3 / 4)
            return estimated_size
        except Exception:
            return 0
    
    @staticmethod
    def is_likely_image(base64_data: str) -> bool:
        """
        Проверяет, похожа ли Base64 строка на изображение
        
        Args:
            base64_data: Base64 строка
            
        Returns:
            bool: True если похожа на изображение
        """
        try:
            if not base64_data:
                return False
            
            # Декодируем первые байты для проверки заголовка
            decoded = base64.b64decode(base64_data[:100])
            
            # Проверяем заголовки изображений
            if decoded.startswith(b'\xff\xd8\xff'):  # JPEG
                return True
            elif decoded.startswith(b'\x89PNG\r\n\x1a\n'):  # PNG
                return True
            elif decoded.startswith(b'RIFF') and b'WEBP' in decoded[:20]:  # WebP
                return True
            elif decoded.startswith(b'BM'):  # BMP
                return True
            
            return False
            
        except Exception:
            return False
    
    @staticmethod
    def detect_image_format(base64_data: str) -> Optional[str]:
        """
        Определяет формат изображения по Base64
        
        Args:
            base64_data: Base64 строка
            
        Returns:
            Optional[str]: Формат изображения или None
        """
        try:
            if not base64_data:
                return None
            
            # Декодируем первые байты
            decoded = base64.b64decode(base64_data[:100])
            
            # Проверяем заголовки
            if decoded.startswith(b'\xff\xd8\xff'):
                return "jpeg"
            elif decoded.startswith(b'\x89PNG\r\n\x1a\n'):
                return "png"
            elif decoded.startswith(b'RIFF') and b'WEBP' in decoded[:20]:
                return "webp"
            elif decoded.startswith(b'BM'):
                return "bmp"
            elif decoded.startswith(b'GIF87a') or decoded.startswith(b'GIF89a'):
                return "gif"
            
            return None
            
        except Exception:
            return None
