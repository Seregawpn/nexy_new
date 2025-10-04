"""
HTTP клиент для системы обновлений
Безопасные HTTPS запросы с проверкой сертификатов
"""

import urllib3
import os
import logging
from typing import Optional
import urllib3.exceptions

logger = logging.getLogger(__name__)

class UpdateHTTPClient:
    """HTTP клиент для обновлений с повышенной безопасностью"""
    
    def __init__(self, timeout: int = 30, retries: int = 3):
        """
        Инициализация HTTP клиента
        
        Args:
            timeout: Таймаут в секундах
            retries: Количество повторных попыток
        """
        # Отключаем предупреждения urllib3 для чистоты логов
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # Создаем отдельный HTTP клиент для обновлений
        self.http = urllib3.PoolManager(
            retries=urllib3.Retry(
                total=retries, 
                backoff_factor=0.5,
                status_forcelist=[500, 502, 503, 504]
            ),
            timeout=urllib3.Timeout(total=timeout)
        )
        
        logger.info(f"HTTP клиент инициализирован: timeout={timeout}s, retries={retries}")
    
    def get_manifest(self, url: str) -> dict:
        """
        Получение манифеста обновлений
        
        Args:
            url: URL манифеста (должен быть HTTPS)
            
        Returns:
            dict: Парсированный JSON манифест
            
        Raises:
            ValueError: Если URL не HTTPS
            RuntimeError: Если HTTP статус не 200
        """
        if not url.startswith('https://') and not url.startswith('http://localhost') and not url.startswith('http://20.151.51.172'):
            raise ValueError("URL должен использовать HTTPS для безопасности (кроме localhost и Azure VM для тестирования)")
        
        logger.info(f"Запрос манифеста: {url}")
        
        try:
            response = self.http.request("GET", url)
            
            if response.status != 200:
                raise RuntimeError(f"HTTP {response.status}: {response.reason}")
            
            # Парсим JSON
            import json
            manifest = json.loads(response.data.decode('utf-8'))
            
            logger.info(f"Манифест получен: версия {manifest.get('version', 'неизвестная')}")
            return manifest
            
        except urllib3.exceptions.HTTPError as e:
            logger.error(f"Ошибка HTTP запроса: {e}")
            raise RuntimeError(f"Ошибка HTTP запроса: {e}")
        except Exception as e:
            # Проверяем, является ли это ошибкой JSON
            if "json" in str(type(e)).lower() or "decode" in str(e).lower():
                logger.error(f"Ошибка парсинга JSON: {e}")
                raise RuntimeError(f"Неверный формат JSON: {e}")
            else:
                logger.error(f"Неожиданная ошибка: {e}")
                raise RuntimeError(f"Ошибка получения манифеста: {e}")
    
    def download_file(self, url: str, dest_path: str, expected_size: Optional[int] = None):
        """
        Скачивание файла с проверкой размера
        
        Args:
            url: URL файла (должен быть HTTPS)
            dest_path: Путь для сохранения
            expected_size: Ожидаемый размер файла в байтах
            
        Raises:
            ValueError: Если URL не HTTPS
            RuntimeError: Если размер файла не совпадает
        """
        if not url.startswith('https://') and not url.startswith('http://localhost') and not url.startswith('http://20.151.51.172'):
            raise ValueError("URL должен использовать HTTPS для безопасности (кроме localhost и Azure VM для тестирования)")
        
        logger.info(f"Скачивание файла: {url} -> {dest_path}")
        
        try:
            with self.http.request("GET", url, preload_content=False) as response:
                if response.status != 200:
                    raise RuntimeError(f"HTTP {response.status}: {response.reason}")
                
                # Создаем директорию если нужно
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                
                # Скачиваем файл по частям
                with open(dest_path, "wb") as f:
                    downloaded = 0
                    for chunk in response.stream(1024 * 1024):  # 1MB chunks
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Показываем прогресс каждые 10MB
                        if downloaded % (10 * 1024 * 1024) == 0:
                            mb_downloaded = downloaded / (1024 * 1024)
                            logger.info(f"Скачано: {mb_downloaded:.1f} MB")
            
            # Проверяем размер файла
            actual_size = os.path.getsize(dest_path)
            if expected_size and actual_size != expected_size:
                os.unlink(dest_path)  # Удаляем неполный файл
                raise RuntimeError(
                    f"Размер файла не совпадает: ожидалось {expected_size}, "
                    f"получено {actual_size} байт"
                )
            
            logger.info(f"Файл успешно скачан: {actual_size} байт")
            
        except urllib3.exceptions.HTTPError as e:
            logger.error(f"Ошибка HTTP запроса при скачивании: {e}")
            raise RuntimeError(f"Ошибка скачивания: {e}")
        except OSError as e:
            logger.error(f"Ошибка записи файла: {e}")
            raise RuntimeError(f"Ошибка записи файла: {e}")
    
    def test_connection(self, url: str) -> bool:
        """
        Тестирование соединения с сервером обновлений
        
        Args:
            url: URL для тестирования
            
        Returns:
            bool: True если соединение успешно
        """
        try:
            # Разрешаем https и http://localhost для локального тестового сервера,
            # чтобы поведение соответствовало get_manifest/download_file
            if not (url.startswith('https://') or url.startswith('http://localhost')):
                return False

            response = self.http.request("HEAD", url, timeout=10)
            return response.status == 200
            
        except Exception as e:
            logger.warning(f"Тест соединения неудачен: {e}")
            return False
