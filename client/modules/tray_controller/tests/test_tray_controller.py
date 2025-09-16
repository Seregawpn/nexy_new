"""
Тесты для Tray Controller Module
"""

import asyncio
import pytest
import tempfile
import os
from unittest.mock import Mock, patch
from ..core.tray_controller import TrayController
from ..core.types import TrayStatus, TrayConfig
from ..core.config import TrayConfigManager

class TestTrayController:
    """Тесты для TrayController"""
    
    @pytest.fixture
    async def tray_controller(self):
        """Фикстура для создания TrayController"""
        config_manager = TrayConfigManager()
        controller = TrayController(config_manager)
        yield controller
        # Очистка после теста
        if controller.is_running:
            await controller.stop()
    
    @pytest.mark.asyncio
    async def test_initialization(self, tray_controller):
        """Тест инициализации"""
        assert not tray_controller.is_initialized()
        
        result = await tray_controller.initialize()
        assert result is True
        assert tray_controller.is_initialized()
        assert tray_controller.current_status == TrayStatus.SLEEPING
    
    @pytest.mark.asyncio
    async def test_start_stop(self, tray_controller):
        """Тест запуска и остановки"""
        # Инициализация
        await tray_controller.initialize()
        
        # Запуск
        result = await tray_controller.start()
        assert result is True
        assert tray_controller.is_running
        
        # Остановка
        result = await tray_controller.stop()
        assert result is True
        assert not tray_controller.is_running
    
    @pytest.mark.asyncio
    async def test_status_update(self, tray_controller):
        """Тест обновления статуса"""
        await tray_controller.initialize()
        await tray_controller.start()
        
        # Обновление статуса
        result = await tray_controller.update_status(TrayStatus.LISTENING)
        assert result is True
        assert tray_controller.current_status == TrayStatus.LISTENING
        
        # Еще одно обновление
        result = await tray_controller.update_status(TrayStatus.PROCESSING)
        assert result is True
        assert tray_controller.current_status == TrayStatus.PROCESSING
    
    @pytest.mark.asyncio
    async def test_event_callbacks(self, tray_controller):
        """Тест обработчиков событий"""
        await tray_controller.initialize()
        
        # Установка обработчиков
        status_callback = Mock()
        icon_callback = Mock()
        
        tray_controller.set_event_callback("status_changed", status_callback)
        tray_controller.set_event_callback("icon_clicked", icon_callback)
        
        # Запуск и обновление статуса
        await tray_controller.start()
        await tray_controller.update_status(TrayStatus.LISTENING)
        
        # Проверка вызова обработчика статуса
        status_callback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_notification(self, tray_controller):
        """Тест показа уведомлений"""
        await tray_controller.initialize()
        await tray_controller.start()
        
        # Показ уведомления
        await tray_controller.show_notification(
            title="Test",
            message="Test message",
            subtitle="Test subtitle"
        )
        
        # Проверяем, что не было исключений
        assert True
    
    @pytest.mark.asyncio
    async def test_double_start(self, tray_controller):
        """Тест двойного запуска"""
        await tray_controller.initialize()
        
        # Первый запуск
        result1 = await tray_controller.start()
        assert result1 is True
        
        # Второй запуск (должен вернуть True)
        result2 = await tray_controller.start()
        assert result2 is True
    
    @pytest.mark.asyncio
    async def test_stop_without_start(self, tray_controller):
        """Тест остановки без запуска"""
        await tray_controller.initialize()
        
        # Остановка без запуска
        result = await tray_controller.stop()
        assert result is True
    
    @pytest.mark.asyncio
    async def test_status_update_without_start(self, tray_controller):
        """Тест обновления статуса без запуска"""
        await tray_controller.initialize()
        
        # Обновление статуса без запуска
        result = await tray_controller.update_status(TrayStatus.LISTENING)
        assert result is False

class TestTrayConfigManager:
    """Тесты для TrayConfigManager"""
    
    def test_default_config(self):
        """Тест конфигурации по умолчанию"""
        config_manager = TrayConfigManager()
        config = config_manager.get_config()
        
        assert isinstance(config, TrayConfig)
        assert config.show_status is True
        assert config.show_menu is True
        assert config.icon_size == 16
    
    def test_config_update(self):
        """Тест обновления конфигурации"""
        config_manager = TrayConfigManager()
        
        # Обновление конфигурации
        result = config_manager.update_config(
            icon_size=20,
            enable_sound=True
        )
        assert result is True
        
        # Проверка обновления
        config = config_manager.get_config()
        assert config.icon_size == 20
        assert config.enable_sound is True
    
    def test_config_save_load(self):
        """Тест сохранения и загрузки конфигурации"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "test_config.yaml")
            config_manager = TrayConfigManager(config_path)
            
            # Обновление конфигурации
            config_manager.update_config(icon_size=24)
            
            # Создание нового менеджера
            new_config_manager = TrayConfigManager(config_path)
            new_config = new_config_manager.get_config()
            
            assert new_config.icon_size == 24

class TestTrayIconGenerator:
    """Тесты для TrayIconGenerator"""
    
    def test_create_circle_icon(self):
        """Тест создания иконки-кружка"""
        from ..core.types import TrayIconGenerator
        
        generator = TrayIconGenerator()
        
        # Создание иконки для каждого статуса
        for status in TrayStatus:
            icon = generator.create_circle_icon(status, 16)
            assert icon.status == status
            assert icon.size == 16
            assert icon.color is not None
    
    def test_create_svg_icon(self):
        """Тест создания SVG иконки"""
        from ..core.types import TrayIconGenerator
        
        generator = TrayIconGenerator()
        
        # Создание SVG для каждого статуса
        for status in TrayStatus:
            svg = generator.create_svg_icon(status, 16)
            assert isinstance(svg, str)
            assert "svg" in svg.lower()
            assert "circle" in svg.lower()

# Интеграционные тесты
class TestTrayIntegration:
    """Интеграционные тесты"""
    
    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """Тест полного workflow"""
        config_manager = TrayConfigManager()
        tray_controller = TrayController(config_manager)
        
        try:
            # Инициализация
            assert await tray_controller.initialize()
            
            # Запуск
            assert await tray_controller.start()
            
            # Тест всех статусов
            statuses = [
                TrayStatus.SLEEPING,
                TrayStatus.LISTENING,
                TrayStatus.PROCESSING
            ]
            
            for status in statuses:
                result = await tray_controller.update_status(status)
                assert result is True
                assert tray_controller.current_status == status
                await asyncio.sleep(0.1)  # Небольшая пауза
            
            # Остановка
            assert await tray_controller.stop()
            
        finally:
            # Очистка
            if tray_controller.is_running:
                await tray_controller.stop()

if __name__ == "__main__":
    # Запуск тестов
    pytest.main([__file__, "-v"])










