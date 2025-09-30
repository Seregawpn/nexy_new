"""
Основной API для захвата скриншотов на macOS
"""

import asyncio
import logging
import time
from typing import Optional, Tuple
from .types import ScreenshotResult, ScreenshotConfig, ScreenshotRegion, ScreenshotError, ScreenshotTimeoutError
from config.unified_config_loader import unified_config

logger = logging.getLogger(__name__)

class ScreenshotCapture:
    """Основной класс для захвата скриншотов на macOS"""
    
    def __init__(self, config: Optional[ScreenshotConfig] = None):
        """
        Инициализирует захватчик скриншотов
        
        Args:
            config: Конфигурация захвата (опциональная; если None, загружается из unified_config)
        """
        self.config = config or self._get_config_from_unified()
        self._bridge = None
        self._initialized = False
        
        # Инициализируем bridge
        self._initialize_bridge()
    
    def _get_config_from_unified(self) -> ScreenshotConfig:
        """Загружает конфигурацию из unified_config.yaml"""
        try:
            # Получаем конфигурацию screenshot_capture из unified_config
            config_data = unified_config._load_config()
            screenshot_config = config_data.get('screenshot_capture', {})
            
            return ScreenshotConfig(
                enabled=screenshot_config.get('enabled', True),
                auto_capture=screenshot_config.get('auto_capture', False),
                capture_delay=float(screenshot_config.get('capture_delay', 0.1)),
                capture_format=screenshot_config.get('capture_format', 'PNG'),
                capture_quality=int(screenshot_config.get('capture_quality', 85)),
                max_captures=int(screenshot_config.get('max_captures', 10)),
                save_path=screenshot_config.get('save_path', 'screenshots'),
                timeout=float(screenshot_config.get('timeout', 5.0))
            )
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки конфигурации screenshot_capture: {e}")
            # Возвращаем конфигурацию по умолчанию
            return ScreenshotConfig()
    
    def _initialize_bridge(self):
        """Инициализирует Core Graphics bridge"""
        try:
            # Пытаемся использовать полный bridge
            from ..macos.core_graphics_bridge import CoreGraphicsBridge
            self._bridge = CoreGraphicsBridge()
            self._initialized = True
            logger.info("✅ Core Graphics bridge инициализирован")
        except ImportError as e:
            logger.warning(f"⚠️ Полный bridge недоступен: {e}")
            try:
                # Используем упрощенный bridge
                from ..macos.simple_bridge import SimpleCoreGraphicsBridge
                self._bridge = SimpleCoreGraphicsBridge()
                self._initialized = True
                logger.info("✅ Simple Core Graphics bridge инициализирован")
            except ImportError as e2:
                logger.warning(f"⚠️ Simple bridge недоступен: {e2}")
                try:
                    # Используем тестовый bridge
                    from ..macos.test_bridge import TestCoreGraphicsBridge
                    self._bridge = TestCoreGraphicsBridge()
                    self._initialized = True
                    logger.info("✅ Test Core Graphics bridge инициализирован")
                except ImportError as e3:
                    logger.error(f"❌ Ошибка инициализации bridge: {e3}")
                    raise ScreenshotError(f"Ошибка инициализации bridge: {e3}")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации bridge: {e}")
            raise ScreenshotError(f"Ошибка инициализации bridge: {e}")
    
    async def capture_screenshot(self, config: ScreenshotConfig = None) -> ScreenshotResult:
        """
        Захватывает скриншот экрана
        
        Args:
            config: Конфигурация захвата (если None, используется текущая)
            
        Returns:
            ScreenshotResult: Результат захвата
        """
        if not self._initialized:
            raise ScreenshotError("ScreenshotCapture не инициализирован")
        
        capture_config = config or self.config
        
        try:
            # Выполняем захват в executor'е для неблокирующей работы
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                self._capture_sync, 
                capture_config
            )
            
            return result
            
        except asyncio.TimeoutError:
            logger.error("❌ Таймаут захвата скриншота")
            return ScreenshotResult(
                success=False,
                error="Таймаут захвата скриншота",
                capture_time=capture_config.timeout
            )
        except Exception as e:
            logger.error(f"❌ Ошибка захвата скриншота: {e}")
            return ScreenshotResult(
                success=False,
                error=f"Ошибка захвата скриншота: {e}"
            )
    
    def _capture_sync(self, config: ScreenshotConfig) -> ScreenshotResult:
        """Синхронный захват скриншота"""
        try:
            if config.region == ScreenshotRegion.FULL_SCREEN:
                return self._bridge.capture_full_screen(config)
            elif config.region == ScreenshotRegion.PRIMARY_MONITOR:
                return self._bridge.capture_full_screen(config)
            elif config.region == ScreenshotRegion.CUSTOM and config.custom_region:
                return self._bridge.capture_region(config.custom_region, config)
            else:
                # По умолчанию - весь экран
                return self._bridge.capture_full_screen(config)
                
        except Exception as e:
            logger.error(f"❌ Ошибка синхронного захвата: {e}")
            return ScreenshotResult(
                success=False,
                error=f"Ошибка синхронного захвата: {e}"
            )
    
    async def capture_region(self, region: Tuple[int, int, int, int], config: ScreenshotConfig = None) -> ScreenshotResult:
        """
        Захватывает указанную область экрана
        
        Args:
            region: Область (x, y, width, height)
            config: Конфигурация захвата
            
        Returns:
            ScreenshotResult: Результат захвата
        """
        if not self._initialized:
            raise ScreenshotError("ScreenshotCapture не инициализирован")
        
        capture_config = config or self.config
        
        try:
            # Выполняем захват в executor'е
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                self._capture_region_sync, 
                region, 
                capture_config
            )
            
            return result
            
        except asyncio.TimeoutError:
            logger.error("❌ Таймаут захвата области")
            return ScreenshotResult(
                success=False,
                error="Таймаут захвата области",
                capture_time=capture_config.timeout
            )
        except Exception as e:
            logger.error(f"❌ Ошибка захвата области: {e}")
            return ScreenshotResult(
                success=False,
                error=f"Ошибка захвата области: {e}"
            )
    
    def _capture_region_sync(self, region: Tuple[int, int, int, int], config: ScreenshotConfig) -> ScreenshotResult:
        """Синхронный захват области"""
        try:
            return self._bridge.capture_region(region, config)
        except Exception as e:
            logger.error(f"❌ Ошибка синхронного захвата области: {e}")
            return ScreenshotResult(
                success=False,
                error=f"Ошибка синхронного захвата области: {e}"
            )
    
    async def test_capture(self) -> bool:
        """
        Тестирует возможность захвата скриншота
        
        Returns:
            bool: True если захват возможен, False иначе
        """
        if not self._initialized:
            return False
        
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._bridge.test_capture)
            return result
        except Exception as e:
            logger.error(f"❌ Ошибка теста захвата: {e}")
            return False
    
    def get_screen_info(self):
        """Получает информацию об экране"""
        if not self._initialized:
            raise ScreenshotError("ScreenshotCapture не инициализирован")
        
        return self._bridge.get_screen_info()
    
    def update_config(self, config: ScreenshotConfig):
        """Обновляет конфигурацию"""
        self.config = config
        logger.info("✅ Конфигурация обновлена")
    
    def get_status(self) -> dict:
        """Получает статус модуля"""
        return {
            "initialized": self._initialized,
            "config": {
                "format": self.config.format.value,
                "quality": self.config.quality.value,
                "region": self.config.region.value,
                "max_width": self.config.max_width,
                "max_height": self.config.max_height,
                "timeout": self.config.timeout
            },
            "bridge_available": self._bridge is not None
        }
    
    def cleanup(self):
        """Очищает ресурсы"""
        self._bridge = None
        self._initialized = False
        logger.info("✅ Ресурсы очищены")

        
