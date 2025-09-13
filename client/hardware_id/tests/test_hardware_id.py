"""
Тесты для модуля hardware_id
Упрощенная версия - только Hardware UUID для macOS
"""

import unittest
import tempfile
import os
import json
from unittest.mock import patch, MagicMock
from hardware_id.core.hardware_identifier import HardwareIdentifier
from hardware_id.core.types import HardwareIdResult, HardwareIdStatus, HardwareIdConfig
from hardware_id.macos.hardware_detector import HardwareDetector
from hardware_id.utils.caching import HardwareIdCache
from hardware_id.utils.validation import HardwareIdValidator


class TestHardwareIdValidator(unittest.TestCase):
    """Тесты для HardwareIdValidator"""
    
    def setUp(self):
        self.validator = HardwareIdValidator()
    
    def test_validate_uuid_valid(self):
        """Тест валидации корректного UUID"""
        valid_uuids = [
            "12345678-1234-1234-1234-123456789012",  # Версия 1
            "ABCDEFAB-1234-5678-9ABC-DEF012345678",  # Версия 5
            "E03D2455-8EF1-5270-AA03-13B5771C7CB2"   # Реальный Hardware UUID (версия 5)
        ]
        
        for uuid_str in valid_uuids:
            with self.subTest(uuid=uuid_str):
                self.assertTrue(self.validator.validate_uuid(uuid_str))
    
    def test_validate_uuid_invalid(self):
        """Тест валидации некорректного UUID"""
        invalid_uuids = [
            "",
            "invalid",
            "12345678-1234-1234-1234-12345678901",  # Слишком короткий
            "12345678-1234-1234-1234-1234567890123",  # Слишком длинный
            "12345678-1234-1234-1234-12345678901G",  # Недопустимый символ
            "12345678_1234_1234_1234_123456789012",  # Неверный разделитель
        ]
        
        for uuid_str in invalid_uuids:
            with self.subTest(uuid=uuid_str):
                self.assertFalse(self.validator.validate_uuid(uuid_str))
    
    def test_validate_uuid_random(self):
        """Тест определения случайного UUID"""
        # UUID версии 4 (случайный)
        random_uuid = "12345678-1234-4234-1234-123456789012"
        self.assertTrue(self.validator._is_random_uuid(random_uuid))
        
        # UUID версии 1 (не случайный)
        non_random_uuid = "12345678-1234-1234-1234-123456789012"
        self.assertFalse(self.validator._is_random_uuid(non_random_uuid))


class TestHardwareIdCache(unittest.TestCase):
    """Тесты для HardwareIdCache"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.cache_file = os.path.join(self.temp_dir, "test_cache.json")
        self.cache = HardwareIdCache(self.cache_file, ttl_seconds=3600)
    
    def tearDown(self):
        # Очищаем временные файлы
        if os.path.exists(self.cache_file):
            os.remove(self.cache_file)
        os.rmdir(self.temp_dir)
    
    def test_save_and_load_uuid(self):
        """Тест сохранения и загрузки UUID"""
        test_uuid = "12345678-1234-1234-1234-123456789012"
        test_metadata = {"test": "data"}
        
        # Сохраняем
        self.assertTrue(self.cache.save_uuid_to_cache(test_uuid, test_metadata))
        
        # Загружаем
        result = self.cache.get_cached_uuid()
        self.assertIsNotNone(result)
        self.assertEqual(result.uuid, test_uuid)
        self.assertEqual(result.status, HardwareIdStatus.CACHED)
        self.assertTrue(result.cached)
    
    def test_cache_validation(self):
        """Тест валидации кэша"""
        from datetime import datetime
        
        # Создаем валидный кэш с текущей датой
        valid_cache = {
            'uuid': '12345678-1234-1234-1234-123456789012',
            'cached_at': datetime.now().isoformat(),
            'ttl_seconds': 3600,
            'version': '1.0',
            'metadata': {}
        }
        
        self.assertTrue(self.cache._is_cache_valid(valid_cache))
        
        # Создаем невалидный кэш
        invalid_cache = {
            'uuid': 'invalid',
            'cached_at': 'invalid',
            'ttl_seconds': 3600,
            'version': '2.0'  # Неверная версия
        }
        
        self.assertFalse(self.cache._is_cache_valid(invalid_cache))
    
    def test_clear_cache(self):
        """Тест очистки кэша"""
        # Сохраняем данные
        self.cache.save_uuid_to_cache("test-uuid")
        
        # Проверяем, что кэш существует
        self.assertTrue(os.path.exists(self.cache_file))
        
        # Очищаем кэш
        self.assertTrue(self.cache.clear_cache())
        
        # Проверяем, что кэш удален
        self.assertFalse(os.path.exists(self.cache_file))


class TestHardwareDetector(unittest.TestCase):
    """Тесты для HardwareDetector"""
    
    def setUp(self):
        self.detector = HardwareDetector()
    
    def test_is_macos(self):
        """Тест определения macOS"""
        # Этот тест может быть нестабильным на разных системах
        # но мы можем проверить, что метод не падает
        result = self.detector.is_macos()
        self.assertIsInstance(result, bool)
    
    def test_validate_hardware_uuid(self):
        """Тест валидации Hardware UUID"""
        valid_uuid = "12345678-1234-1234-1234-123456789012"
        invalid_uuid = "invalid-uuid"
        
        self.assertTrue(self.detector.validate_hardware_uuid(valid_uuid))
        self.assertFalse(self.detector.validate_hardware_uuid(invalid_uuid))
    
    @patch('subprocess.run')
    def test_detect_hardware_uuid_success(self, mock_run):
        """Тест успешного обнаружения Hardware UUID"""
        # Мокаем успешный вывод system_profiler
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = """
Hardware Overview:
  Model Name: MacBook Pro
  Model Identifier: MacBookPro18,1
  Hardware UUID: 12345678-1234-1234-1234-123456789012
  Serial Number (system): ABC123DEF456
"""
        
        result = self.detector.detect_hardware_uuid()
        
        self.assertEqual(result.status, HardwareIdStatus.SUCCESS)
        self.assertEqual(result.uuid, "12345678-1234-1234-1234-123456789012")
        self.assertEqual(result.source, "system_profiler")
    
    @patch('subprocess.run')
    def test_detect_hardware_uuid_not_found(self, mock_run):
        """Тест случая, когда Hardware UUID не найден"""
        # Мокаем вывод system_profiler без Hardware UUID
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = """
Hardware Overview:
  Model Name: MacBook Pro
  Model Identifier: MacBookPro18,1
  Serial Number (system): ABC123DEF456
"""
        
        result = self.detector.detect_hardware_uuid()
        
        self.assertEqual(result.status, HardwareIdStatus.NOT_FOUND)
        self.assertEqual(result.uuid, "")
        self.assertEqual(result.source, "system_profiler")


class TestHardwareIdentifier(unittest.TestCase):
    """Тесты для HardwareIdentifier"""
    
    def setUp(self):
        # Создаем временную конфигурацию
        self.temp_dir = tempfile.mkdtemp()
        self.cache_file = os.path.join(self.temp_dir, "test_cache.json")
        
        self.config = HardwareIdConfig(
            cache_enabled=True,
            cache_file_path=self.cache_file,
            cache_ttl_seconds=3600,
            system_profiler_timeout=5,
            validate_uuid_format=True,
            fallback_to_random=False
        )
        
        self.identifier = HardwareIdentifier(self.config)
    
    def tearDown(self):
        # Очищаем временные файлы
        if os.path.exists(self.cache_file):
            os.remove(self.cache_file)
        os.rmdir(self.temp_dir)
    
    def test_initialization(self):
        """Тест инициализации"""
        self.assertIsNotNone(self.identifier.config)
        self.assertIsNotNone(self.identifier.detector)
        self.assertIsNotNone(self.identifier.cache)
        self.assertIsNotNone(self.identifier.validator)
    
    @patch.object(HardwareDetector, 'detect_hardware_uuid')
    def test_get_hardware_id_success(self, mock_detect):
        """Тест успешного получения Hardware ID"""
        # Мокаем успешное обнаружение
        mock_detect.return_value = HardwareIdResult(
            uuid="12345678-1234-1234-1234-123456789012",
            status=HardwareIdStatus.SUCCESS,
            source="system_profiler",
            cached=False
        )
        
        result = self.identifier.get_hardware_id()
        
        self.assertEqual(result.status, HardwareIdStatus.SUCCESS)
        self.assertEqual(result.uuid, "12345678-1234-1234-1234-123456789012")
        self.assertEqual(result.source, "system_profiler")
    
    @patch.object(HardwareDetector, 'detect_hardware_uuid')
    def test_get_hardware_id_cached(self, mock_detect):
        """Тест получения Hardware ID из кэша"""
        # Сначала сохраняем в кэш
        test_uuid = "12345678-1234-1234-1234-123456789012"
        self.identifier.cache.save_uuid_to_cache(test_uuid)
        
        # Получаем из кэша
        result = self.identifier.get_hardware_id()
        
        self.assertEqual(result.status, HardwareIdStatus.CACHED)
        self.assertEqual(result.uuid, test_uuid)
        self.assertTrue(result.cached)
        
        # Мокаем не должен вызываться
        mock_detect.assert_not_called()
    
    def test_clear_cache(self):
        """Тест очистки кэша"""
        # Сохраняем данные в кэш
        test_uuid = "12345678-1234-1234-1234-123456789012"
        self.identifier.cache.save_uuid_to_cache(test_uuid)
        
        # Проверяем, что кэш существует
        self.assertTrue(os.path.exists(self.cache_file))
        
        # Очищаем кэш
        self.assertTrue(self.identifier.clear_cache())
        
        # Проверяем, что кэш удален
        self.assertFalse(os.path.exists(self.cache_file))
    
    def test_validate_hardware_id(self):
        """Тест валидации Hardware ID"""
        valid_uuid = "12345678-1234-1234-1234-123456789012"
        invalid_uuid = "invalid-uuid"
        
        self.assertTrue(self.identifier.validate_hardware_id(valid_uuid))
        self.assertFalse(self.identifier.validate_hardware_id(invalid_uuid))


class TestIntegration(unittest.TestCase):
    """Интеграционные тесты"""
    
    def test_full_workflow(self):
        """Тест полного рабочего процесса"""
        # Создаем временную конфигурацию
        temp_dir = tempfile.mkdtemp()
        cache_file = os.path.join(temp_dir, "integration_test_cache.json")
        
        try:
            config = HardwareIdConfig(
                cache_enabled=True,
                cache_file_path=cache_file,
                cache_ttl_seconds=3600,
                system_profiler_timeout=5,
                validate_uuid_format=True,
                fallback_to_random=True
            )
            
            identifier = HardwareIdentifier(config)
            
            # Проверяем доступность
            is_available = identifier.is_available()
            self.assertIsInstance(is_available, bool)
            
            # Получаем информацию о кэше
            cache_info = identifier.get_cache_info()
            self.assertIsInstance(cache_info, dict)
            self.assertIn('exists', cache_info)
            
            # Получаем информацию об оборудовании
            hardware_info = identifier.get_hardware_info()
            self.assertIsInstance(hardware_info, dict)
            
        finally:
            # Очищаем временные файлы
            if os.path.exists(cache_file):
                os.remove(cache_file)
            os.rmdir(temp_dir)


if __name__ == '__main__':
    # Настройка логирования для тестов
    import logging
    logging.basicConfig(level=logging.WARNING)
    
    # Запуск тестов
    unittest.main(verbosity=2)
