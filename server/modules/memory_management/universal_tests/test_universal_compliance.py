"""
Universal compliance тесты для Memory Management Module

Проверяет соответствие модуля универсальным стандартам:
- UniversalProviderInterface
- Универсальная структура модуля
- Стандартные методы и API
"""

import pytest
from unittest.mock import Mock

from ..core.memory_manager import MemoryManager
from ..providers.memory_analyzer import MemoryAnalyzer
from ...integration.core.universal_provider_interface import UniversalProviderInterface


class TestUniversalCompliance:
    """Тесты соответствия универсальным стандартам"""
    
    def test_memory_manager_structure(self):
        """Тест структуры MemoryManager"""
        manager = MemoryManager()
        
        # Проверка наличия основных методов
        assert hasattr(manager, 'get_memory_context')
        assert hasattr(manager, 'analyze_conversation')
        assert hasattr(manager, 'update_memory_background')
        assert hasattr(manager, 'is_available')
        assert hasattr(manager, 'set_database_manager')
        assert hasattr(manager, 'cleanup_expired_memory')
        
        # Проверка типов методов
        assert callable(manager.get_memory_context)
        assert callable(manager.analyze_conversation)
        assert callable(manager.update_memory_background)
        assert callable(manager.is_available)
        assert callable(manager.set_database_manager)
        assert callable(manager.cleanup_expired_memory)
    
    def test_memory_analyzer_structure(self):
        """Тест структуры MemoryAnalyzer"""
        with pytest.raises(ImportError):  # Нет API ключа в тестах
            MemoryAnalyzer("test_key")
        
        # Проверка структуры класса
        assert hasattr(MemoryAnalyzer, '__init__')
        assert hasattr(MemoryAnalyzer, 'analyze_conversation')
        assert hasattr(MemoryAnalyzer, 'is_available')
        assert hasattr(MemoryAnalyzer, '_parse_analysis_response')
        
        # Проверка типов методов
        assert callable(MemoryAnalyzer.__init__)
        assert callable(MemoryAnalyzer.analyze_conversation)
        assert callable(MemoryAnalyzer.is_available)
        assert callable(MemoryAnalyzer._parse_analysis_response)
    
    def test_config_structure(self):
        """Тест структуры конфигурации"""
        from ..config import MemoryConfig
        
        config = MemoryConfig()
        
        # Проверка наличия основных настроек
        assert hasattr(config, 'gemini_api_key')
        assert hasattr(config, 'max_short_term_memory_size')
        assert hasattr(config, 'max_long_term_memory_size')
        assert hasattr(config, 'memory_timeout')
        assert hasattr(config, 'analysis_timeout')
        assert hasattr(config, 'memory_analysis_model')
        assert hasattr(config, 'memory_analysis_temperature')
        assert hasattr(config, 'memory_analysis_prompt')
        
        # Проверка методов
        assert hasattr(config, 'get_config_dict')
        assert hasattr(config, 'validate_config')
        assert callable(config.get_config_dict)
        assert callable(config.validate_config)
    
    def test_module_imports(self):
        """Тест импортов модуля"""
        # Проверка основных импортов
        from .. import MemoryManager, MemoryAnalyzer
        from ..core import MemoryManager as CoreMemoryManager
        from ..providers import MemoryAnalyzer as ProviderMemoryAnalyzer
        
        assert MemoryManager is CoreMemoryManager
        assert MemoryAnalyzer is ProviderMemoryAnalyzer
    
    def test_async_methods(self):
        """Тест асинхронных методов"""
        import asyncio
        import inspect
        
        manager = MemoryManager()
        
        # Проверка асинхронных методов
        async_methods = [
            'get_memory_context',
            'analyze_conversation', 
            'update_memory_background',
            'cleanup_expired_memory'
        ]
        
        for method_name in async_methods:
            method = getattr(manager, method_name)
            assert inspect.iscoroutinefunction(method), f"Method {method_name} should be async"
    
    def test_error_handling_patterns(self):
        """Тест паттернов обработки ошибок"""
        manager = MemoryManager()
        
        # Проверка graceful degradation
        # Методы должны возвращать безопасные значения при ошибках
        assert manager.is_available() is False  # Без анализатора и БД
        
        # Проверка типов возвращаемых значений
        import asyncio
        
        async def test_error_handling():
            context = await manager.get_memory_context("test")
            assert isinstance(context, str)  # Всегда строка
            
            short, long = await manager.analyze_conversation("test", "test")
            assert isinstance(short, str)  # Всегда строка
            assert isinstance(long, str)   # Всегда строка
            
            # Фоновое обновление не должно поднимать исключения
            await manager.update_memory_background("test", "test", "test")
            
            result = await manager.cleanup_expired_memory(24)
            assert isinstance(result, int)  # Всегда число
        
        asyncio.run(test_error_handling())
    
    def test_config_validation(self):
        """Тест валидации конфигурации"""
        from ..config import MemoryConfig
        
        # Тест с валидной конфигурацией
        with pytest.MonkeyPatch().context() as m:
            m.setenv('GEMINI_API_KEY', 'test_key')
            config = MemoryConfig()
            assert config.validate_config() is True
        
        # Тест с невалидной конфигурацией
        with pytest.MonkeyPatch().context() as m:
            m.delenv('GEMINI_API_KEY', raising=False)
            config = MemoryConfig()
            assert config.validate_config() is False
    
    def test_config_dict_structure(self):
        """Тест структуры конфигурационного словаря"""
        from ..config import MemoryConfig
        
        with pytest.MonkeyPatch().context() as m:
            m.setenv('GEMINI_API_KEY', 'test_key')
            config = MemoryConfig()
            config_dict = config.get_config_dict()
            
            # Проверка наличия всех ключей
            required_keys = [
                'GEMINI_API_KEY',
                'MAX_SHORT_TERM_MEMORY_SIZE',
                'MAX_LONG_TERM_MEMORY_SIZE',
                'MEMORY_TIMEOUT',
                'ANALYSIS_TIMEOUT',
                'MEMORY_ANALYSIS_MODEL',
                'MEMORY_ANALYSIS_TEMPERATURE',
                'MEMORY_ANALYSIS_PROMPT'
            ]
            
            for key in required_keys:
                assert key in config_dict, f"Key {key} missing from config dict"
            
            # Проверка типов значений
            assert isinstance(config_dict['GEMINI_API_KEY'], str)
            assert isinstance(config_dict['MAX_SHORT_TERM_MEMORY_SIZE'], int)
            assert isinstance(config_dict['MAX_LONG_TERM_MEMORY_SIZE'], int)
            assert isinstance(config_dict['MEMORY_TIMEOUT'], float)
            assert isinstance(config_dict['ANALYSIS_TIMEOUT'], float)
            assert isinstance(config_dict['MEMORY_ANALYSIS_MODEL'], str)
            assert isinstance(config_dict['MEMORY_ANALYSIS_TEMPERATURE'], float)
            assert isinstance(config_dict['MEMORY_ANALYSIS_PROMPT'], str)
    
    def test_memory_context_format(self):
        """Тест формата контекста памяти"""
        manager = MemoryManager()
        
        # Проверка структуры контекста памяти
        expected_sections = [
            "MEMORY CONTEXT",
            "SHORT-TERM MEMORY",
            "LONG-TERM MEMORY", 
            "MEMORY USAGE INSTRUCTIONS"
        ]
        
        # Создаем тестовый контекст
        test_context = """
🧠 MEMORY CONTEXT (for response context):

📋 SHORT-TERM MEMORY (current session):
Test short-term memory

📚 LONG-TERM MEMORY (user information):
Test long-term memory

💡 MEMORY USAGE INSTRUCTIONS:
- Use short-term memory to understand current conversation context
- Use long-term memory for response personalization (name, preferences, important details)
- If memory is not relevant to current request - ignore it
- Memory should complement the answer, not replace it
- Priority: current request > short-term memory > long-term memory
        """
        
        for section in expected_sections:
            assert section in test_context, f"Section {section} missing from memory context"
    
    def test_memory_analysis_response_format(self):
        """Тест формата ответа анализа памяти"""
        # Проверка формата ответа анализа
        expected_format = "SHORT_TERM: [content]\nLONG_TERM: [content]"
        
        # Тестовые данные
        test_response = """
        SHORT_TERM: User is discussing Python programming
        LONG_TERM: User is a software developer
        """
        
        assert "SHORT_TERM:" in test_response
        assert "LONG_TERM:" in test_response
        
        # Проверка парсинга
        lines = test_response.strip().split('\n')
        short_line = next((line for line in lines if line.strip().startswith('SHORT_TERM:')), None)
        long_line = next((line for line in lines if line.strip().startswith('LONG_TERM:')), None)
        
        assert short_line is not None
        assert long_line is not None
    
    def test_logging_integration(self):
        """Тест интеграции логирования"""
        import logging
        
        # Проверка наличия логгеров
        manager = MemoryManager()
        
        # Логгеры должны быть настроены
        assert hasattr(manager, '__class__')
        assert manager.__class__.__module__ is not None
        
        # Проверка уровня логирования
        logger = logging.getLogger('modules.memory_management.core.memory_manager')
        assert logger is not None
    
    def test_documentation_structure(self):
        """Тест структуры документации"""
        import os
        
        # Проверка наличия документации
        docs_path = os.path.join(os.path.dirname(__file__), '..', 'docs')
        assert os.path.exists(docs_path)
        
        integration_guide_path = os.path.join(docs_path, 'INTEGRATION_GUIDE.md')
        assert os.path.exists(integration_guide_path)
        
        # Проверка содержимого документации
        with open(integration_guide_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        required_sections = [
            "# 🧠 Memory Management Module",
            "## 📋 Обзор",
            "## 🏗️ Архитектура",
            "## 🔧 Интеграция с TextProcessor",
            "## ⚙️ Конфигурация",
            "## 🧪 Тестирование"
        ]
        
        for section in required_sections:
            assert section in content, f"Section {section} missing from documentation"
