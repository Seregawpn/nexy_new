"""
Тесты для Hardware ID Provider
"""

import pytest
import asyncio
import os
import tempfile
from unittest.mock import patch, mock_open
from modules.session_management.providers.hardware_id_provider import HardwareIDProvider

class TestHardwareIDProvider:
    """Тесты для Hardware ID провайдера"""
    
    def test_provider_initialization(self):
        """Тест инициализации провайдера"""
        config = {
            'cache_file': 'test_cache.cache',
            'length': 24,
            'charset': 'abcdefghijklmnopqrstuvwxyz0123456789',
            'require_hardware_id': True
        }
        
        provider = HardwareIDProvider(config)
        
        assert provider.name == "hardware_id"
        assert provider.priority == 1
        assert provider.cache_file == 'test_cache.cache'
        assert provider.id_length == 24
        assert provider.charset == 'abcdefghijklmnopqrstuvwxyz0123456789'
        assert provider.require_hardware_id is True
        assert provider.cached_id is None
        assert provider.id_generated is False
    
    def test_provider_initialization_default_values(self):
        """Тест инициализации с значениями по умолчанию"""
        config = {}
        
        provider = HardwareIDProvider(config)
        
        assert provider.name == "hardware_id"
        assert provider.priority == 1
        assert provider.cache_file == 'hardware_id.cache'
        assert provider.id_length == 32
        assert len(provider.charset) == 62  # 26 + 26 + 10
        assert provider.require_hardware_id is True
    
    @pytest.mark.asyncio
    async def test_initialize_success_with_cache(self):
        """Тест успешной инициализации с кэшированным ID"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.cache') as temp_file:
            temp_file.write('abcdefghijklmnopqrstuvwxyz0123456789')
            temp_file.flush()
            
            config = {
                'cache_file': temp_file.name,
                'length': 32
            }
            
            provider = HardwareIDProvider(config)
            
            # Мокаем _generate_hardware_id чтобы не генерировать новый
            provider._generate_hardware_id = AsyncMock(return_value=None)
            
            result = await provider.initialize()
            
            assert result is True
            assert provider.is_initialized is True
            assert provider.cached_id == 'abcdefghijklmnopqrstuvwxyz0123456789'
            assert provider.id_generated is True
            
            # Очищаем временный файл
            os.unlink(temp_file.name)
    
    @pytest.mark.asyncio
    async def test_initialize_success_generate_new(self):
        """Тест успешной инициализации с генерацией нового ID"""
        config = {
            'cache_file': 'nonexistent.cache',
            'length': 16
        }
        
        provider = HardwareIDProvider(config)
        
        # Мокаем генерацию ID
        with patch.object(provider, '_generate_hardware_id', return_value='newgeneratedid1234'):
            with patch.object(provider, '_save_to_cache', return_value=True):
                result = await provider.initialize()
                
                assert result is True
                assert provider.is_initialized is True
                assert provider.cached_id == 'newgeneratedid1234'
                assert provider.id_generated is True
    
    @pytest.mark.asyncio
    async def test_initialize_failure_generate_failed(self):
        """Тест неудачной инициализации - генерация ID не удалась"""
        config = {
            'cache_file': 'nonexistent.cache'
        }
        
        provider = HardwareIDProvider(config)
        
        # Мокаем неудачную генерацию ID
        with patch.object(provider, '_generate_hardware_id', return_value=None):
            result = await provider.initialize()
            
            assert result is False
            assert provider.is_initialized is False
    
    @pytest.mark.asyncio
    async def test_process_success(self):
        """Тест успешного получения Hardware ID"""
        config = {
            'cache_file': 'test.cache'
        }
        
        provider = HardwareIDProvider(config)
        
        # Инициализируем провайдер
        provider.cached_id = 'testhardwareid12345678901234567890'
        provider.id_generated = True
        provider.is_initialized = True
        
        # Получаем Hardware ID
        results = []
        async for result in provider.process(None):
            results.append(result)
        
        assert len(results) == 1
        assert results[0] == 'testhardwareid12345678901234567890'
        assert provider.total_requests == 1
        assert provider.successful_requests == 1
    
    @pytest.mark.asyncio
    async def test_process_not_initialized(self):
        """Тест получения Hardware ID без инициализации"""
        config = {
            'cache_file': 'test.cache'
        }
        
        provider = HardwareIDProvider(config)
        
        # Не инициализируем провайдер
        
        with pytest.raises(Exception) as exc_info:
            results = []
            async for result in provider.process(None):
                results.append(result)
        
        assert "not initialized" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_process_no_cached_id(self):
        """Тест получения Hardware ID без кэшированного ID"""
        config = {
            'cache_file': 'test.cache'
        }
        
        provider = HardwareIDProvider(config)
        
        # Инициализируем провайдер без cached_id
        provider.is_initialized = True
        provider.cached_id = None
        
        with pytest.raises(Exception) as exc_info:
            results = []
            async for result in provider.process(None):
                results.append(result)
        
        assert "No Hardware ID available" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_cleanup(self):
        """Тест очистки ресурсов"""
        config = {
            'cache_file': 'test.cache'
        }
        
        provider = HardwareIDProvider(config)
        
        # Устанавливаем некоторые значения
        provider.cached_id = 'testid'
        provider.id_generated = True
        provider.is_initialized = True
        
        result = await provider.cleanup()
        
        assert result is True
        assert provider.cached_id is None
        assert provider.id_generated is False
        assert provider.is_initialized is False
    
    def test_collect_hardware_info(self):
        """Тест сбора аппаратной информации"""
        config = {
            'cache_file': 'test.cache'
        }
        
        provider = HardwareIDProvider(config)
        
        hardware_info = provider._collect_hardware_info()
        
        assert 'platform' in hardware_info
        assert 'system' in hardware_info
        assert 'machine' in hardware_info
        assert 'processor' in hardware_info
        assert 'mac_address' in hardware_info
        assert 'hostname' in hardware_info
        assert 'python_version' in hardware_info
    
    def test_create_hardware_hash(self):
        """Тест создания хэша аппаратной информации"""
        config = {
            'cache_file': 'test.cache'
        }
        
        provider = HardwareIDProvider(config)
        
        hardware_info = {
            'system': 'Darwin',
            'machine': 'x86_64',
            'platform': 'Darwin-20.6.0-x86_64-i386-64bit'
        }
        
        hardware_hash = provider._create_hardware_hash(hardware_info)
        
        assert len(hardware_hash) == 64  # SHA-256 hash length
        assert hardware_hash.isalnum()
        
        # Проверяем консистентность
        hash2 = provider._create_hardware_hash(hardware_info)
        assert hardware_hash == hash2
    
    def test_generate_unique_id(self):
        """Тест генерации уникального ID"""
        config = {
            'cache_file': 'test.cache',
            'length': 16,
            'charset': 'abcdefghijklmnopqrstuvwxyz'
        }
        
        provider = HardwareIDProvider(config)
        
        hardware_hash = 'abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890'
        unique_id = provider._generate_unique_id(hardware_hash)
        
        assert len(unique_id) == 16
        assert all(char in provider.charset for char in unique_id)
        
        # Проверяем консистентность
        unique_id2 = provider._generate_unique_id(hardware_hash)
        assert unique_id == unique_id2
    
    @pytest.mark.asyncio
    async def test_load_cached_id_success(self):
        """Тест успешной загрузки кэшированного ID"""
        config = {
            'cache_file': 'test.cache',
            'length': 16
        }
        
        provider = HardwareIDProvider(config)
        
        # Мокаем файл с кэшированным ID
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data='cachedhardwareid')):
                cached_id = await provider._load_cached_id()
                
                assert cached_id == 'cachedhardwareid'
    
    @pytest.mark.asyncio
    async def test_load_cached_id_file_not_exists(self):
        """Тест загрузки кэшированного ID - файл не существует"""
        config = {
            'cache_file': 'nonexistent.cache'
        }
        
        provider = HardwareIDProvider(config)
        
        cached_id = await provider._load_cached_id()
        
        assert cached_id is None
    
    @pytest.mark.asyncio
    async def test_load_cached_id_invalid_content(self):
        """Тест загрузки кэшированного ID - неверное содержимое"""
        config = {
            'cache_file': 'test.cache',
            'length': 16
        }
        
        provider = HardwareIDProvider(config)
        
        # Мокаем файл с неверным содержимым
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data='invalid_id')):
                cached_id = await provider._load_cached_id()
                
                assert cached_id is None
    
    @pytest.mark.asyncio
    async def test_save_to_cache(self):
        """Тест сохранения в кэш"""
        config = {
            'cache_file': 'test.cache'
        }
        
        provider = HardwareIDProvider(config)
        
        # Мокаем запись в файл
        with patch('builtins.open', mock_open()) as mock_file:
            result = await provider._save_to_cache('testhardwareid12345678901234567890')
            
            assert result is True
            mock_file.assert_called_once_with('test.cache', 'w', encoding='utf-8')
            mock_file().write.assert_called_once_with('testhardwareid12345678901234567890')
    
    @pytest.mark.asyncio
    async def test_health_check_healthy(self):
        """Тест проверки здоровья - здоровый провайдер"""
        config = {
            'cache_file': 'test.cache',
            'length': 16,
            'charset': 'abcdefghijklmnop'
        }
        
        provider = HardwareIDProvider(config)
        
        # Устанавливаем корректный cached_id
        provider.cached_id = 'abcdefghijklmnop'  # 16 символов, все из charset
        provider.is_initialized = True
        
        health = await provider.health_check()
        
        assert health is True
    
    @pytest.mark.asyncio
    async def test_health_check_no_cached_id(self):
        """Тест проверки здоровья - нет кэшированного ID"""
        config = {
            'cache_file': 'test.cache'
        }
        
        provider = HardwareIDProvider(config)
        
        # Не устанавливаем cached_id
        provider.is_initialized = True
        
        health = await provider.health_check()
        
        assert health is False
    
    @pytest.mark.asyncio
    async def test_health_check_wrong_length(self):
        """Тест проверки здоровья - неверная длина ID"""
        config = {
            'cache_file': 'test.cache',
            'length': 16
        }
        
        provider = HardwareIDProvider(config)
        
        # Устанавливаем ID неверной длины
        provider.cached_id = 'shortid'  # 7 символов вместо 16
        provider.is_initialized = True
        
        health = await provider.health_check()
        
        assert health is False
    
    @pytest.mark.asyncio
    async def test_health_check_invalid_chars(self):
        """Тест проверки здоровья - недопустимые символы"""
        config = {
            'cache_file': 'test.cache',
            'length': 16,
            'charset': 'abcdefghijklmnop'
        }
        
        provider = HardwareIDProvider(config)
        
        # Устанавливаем ID с недопустимыми символами
        provider.cached_id = 'abcdefghijklmnop'  # Все символы допустимы
        provider.cached_id = 'invalidchars123!'  # Символ ! недопустим
        provider.is_initialized = True
        
        health = await provider.health_check()
        
        assert health is False
    
    def test_get_hardware_id(self):
        """Тест получения Hardware ID"""
        config = {
            'cache_file': 'test.cache'
        }
        
        provider = HardwareIDProvider(config)
        
        # Не инициализирован
        assert provider.get_hardware_id() is None
        
        # Инициализирован с ID
        provider.is_initialized = True
        provider.cached_id = 'testhardwareid12345678901234567890'
        
        assert provider.get_hardware_id() == 'testhardwareid12345678901234567890'
    
    def test_regenerate_hardware_id(self):
        """Тест принудительной регенерации Hardware ID"""
        config = {
            'cache_file': 'test.cache'
        }
        
        provider = HardwareIDProvider(config)
        
        # Устанавливаем текущий ID
        provider.cached_id = 'oldid'
        provider.id_generated = True
        
        # Мокаем удаление файла
        with patch('os.path.exists', return_value=True):
            with patch('os.remove') as mock_remove:
                result = provider.regenerate_hardware_id()
                
                assert result is True
                assert provider.cached_id is None
                assert provider.id_generated is False
                mock_remove.assert_called_once_with('test.cache')
    
    def test_get_status(self):
        """Тест получения статуса провайдера"""
        config = {
            'cache_file': 'test.cache',
            'length': 24
        }
        
        provider = HardwareIDProvider(config)
        
        # Устанавливаем cached_id для тестирования
        provider.cached_id = 'testhardwareid123456789012'
        provider.id_generated = True
        
        status = provider.get_status()
        
        assert status["provider_type"] == "hardware_id"
        assert status["id_length"] == 24
        assert status["cache_file"] == "test.cache"
        assert status["id_generated"] is True
        assert status["has_cached_id"] is True
        assert status["cached_id_preview"] == "testhard...123456789012"
        assert status["require_hardware_id"] is True
        assert status["charset_length"] == 62
    
    def test_get_metrics(self):
        """Тест получения метрик провайдера"""
        config = {
            'cache_file': 'test.cache',
            'length': 16
        }
        
        provider = HardwareIDProvider(config)
        
        # Устанавливаем некоторые метрики
        provider.total_requests = 10
        provider.successful_requests = 9
        provider.cached_id = 'testhardwareid12'
        provider.id_generated = True
        
        metrics = provider.get_metrics()
        
        assert metrics["provider_type"] == "hardware_id"
        assert metrics["id_length"] == 16
        assert metrics["id_generated"] is True
        assert metrics["has_cached_id"] is True
        assert metrics["cache_file_exists"] is False  # Файл не существует в тесте

if __name__ == "__main__":
    pytest.main([__file__])
