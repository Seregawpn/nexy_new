"""
Простой bridge для захвата скриншотов через системную утилиту screencapture
Использует CLI команды вместо PyObjC для быстрой реализации
"""

import asyncio
import logging
import tempfile
import subprocess
import shlex
import time
import base64
from pathlib import Path
from typing import Tuple, Optional, Dict, Any

from ..core.types import ScreenshotResult, ScreenshotConfig, ScreenshotData, ScreenshotFormat

logger = logging.getLogger(__name__)


class SimpleCoreGraphicsBridge:
    """Простой bridge использующий системную утилиту screencapture"""
    
    def __init__(self):
        """Инициализация bridge"""
        self.initialized = True
        logger.info("✅ SimpleCoreGraphicsBridge инициализирован")
    
    def capture_full_screen(self, config: ScreenshotConfig) -> ScreenshotResult:
        """
        Захват полного экрана через screencapture
        
        Args:
            config: Конфигурация захвата
            
        Returns:
            ScreenshotResult: Результат захвата
        """
        try:
            start_time = time.time()
            
            # Создаем временный файл
            temp_dir = Path(tempfile.gettempdir()) / "nexy_screenshots"
            temp_dir.mkdir(parents=True, exist_ok=True)
            timestamp = int(time.time() * 1000)
            temp_file = temp_dir / f"screenshot_{timestamp}.jpg"
            
            # Команда захвата экрана (без звука, JPEG формат)
            cmd = f"screencapture -x -t jpg {shlex.quote(str(temp_file))}"
            
            # Выполняем команду
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=config.timeout
            )
            
            if result.returncode != 0:
                error_msg = f"screencapture failed: {result.stderr.strip()}"
                logger.error(f"❌ {error_msg}")
                return ScreenshotResult(
                    success=False,
                    error=error_msg,
                    capture_time=time.time() - start_time
                )
            
            if not temp_file.exists():
                error_msg = "Screenshot file was not created"
                logger.error(f"❌ {error_msg}")
                return ScreenshotResult(
                    success=False,
                    error=error_msg,
                    capture_time=time.time() - start_time
                )
            
            # Применяем ограничения размера если нужно
            self._resize_if_needed(temp_file, config)
            
            # Оптимизируем качество JPEG для уменьшения размера файла
            self._optimize_jpeg_quality(temp_file, config)
            
            # Получаем информацию о файле
            width, height = self._get_image_dimensions(temp_file)
            file_size = temp_file.stat().st_size
            
            # Читаем файл и кодируем в base64
            with open(temp_file, 'rb') as f:
                image_data = f.read()
            
            base64_data = base64.b64encode(image_data).decode('utf-8')
            
            # Удаляем временный файл
            temp_file.unlink()
            
            # Создаем результат
            screenshot_data = ScreenshotData(
                base64_data=base64_data,
                width=width,
                height=height,
                format=ScreenshotFormat.JPEG,
                size_bytes=file_size,
                mime_type="image/jpeg",
                metadata={
                    "bridge_type": "simple_cli",
                    "capture_method": "screencapture",
                    "timestamp": time.time()
                }
            )
            
            capture_time = time.time() - start_time
            logger.info(f"✅ Скриншот захвачен: {width}x{height}, {file_size} bytes, {capture_time:.3f}s")
            
            return ScreenshotResult(
                success=True,
                data=screenshot_data,
                capture_time=capture_time
            )
            
        except subprocess.TimeoutExpired:
            error_msg = f"Screenshot capture timeout ({config.timeout}s)"
            logger.error(f"❌ {error_msg}")
            return ScreenshotResult(
                success=False,
                error=error_msg,
                capture_time=config.timeout
            )
        except Exception as e:
            error_msg = f"Screenshot capture error: {e}"
            logger.error(f"❌ {error_msg}")
            return ScreenshotResult(
                success=False,
                error=error_msg,
                capture_time=time.time() - start_time if 'start_time' in locals() else 0.0
            )
    
    def capture_region(self, region: Tuple[int, int, int, int], config: ScreenshotConfig) -> ScreenshotResult:
        """
        Захват области экрана
        
        Args:
            region: Область (x, y, width, height)
            config: Конфигурация захвата
            
        Returns:
            ScreenshotResult: Результат захвата
        """
        try:
            start_time = time.time()
            x, y, width, height = region
            
            # Создаем временный файл
            temp_dir = Path(tempfile.gettempdir()) / "nexy_screenshots"
            temp_dir.mkdir(parents=True, exist_ok=True)
            timestamp = int(time.time() * 1000)
            temp_file = temp_dir / f"screenshot_region_{timestamp}.jpg"
            
            # Команда захвата области экрана
            cmd = f"screencapture -x -t jpg -R {x},{y},{width},{height} {shlex.quote(str(temp_file))}"
            
            # Выполняем команду
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=config.timeout
            )
            
            if result.returncode != 0:
                error_msg = f"screencapture region failed: {result.stderr.strip()}"
                logger.error(f"❌ {error_msg}")
                return ScreenshotResult(
                    success=False,
                    error=error_msg,
                    capture_time=time.time() - start_time
                )
            
            if not temp_file.exists():
                error_msg = "Screenshot region file was not created"
                logger.error(f"❌ {error_msg}")
                return ScreenshotResult(
                    success=False,
                    error=error_msg,
                    capture_time=time.time() - start_time
                )
            
            # Получаем информацию о файле
            actual_width, actual_height = self._get_image_dimensions(temp_file)
            file_size = temp_file.stat().st_size
            
            # Читаем файл и кодируем в base64
            with open(temp_file, 'rb') as f:
                image_data = f.read()
            
            base64_data = base64.b64encode(image_data).decode('utf-8')
            
            # Удаляем временный файл
            temp_file.unlink()
            
            # Создаем результат
            screenshot_data = ScreenshotData(
                base64_data=base64_data,
                width=actual_width,
                height=actual_height,
                format=ScreenshotFormat.JPEG,
                size_bytes=file_size,
                mime_type="image/jpeg",
                metadata={
                    "bridge_type": "simple_cli",
                    "capture_method": "screencapture_region",
                    "region": region,
                    "timestamp": time.time()
                }
            )
            
            capture_time = time.time() - start_time
            logger.info(f"✅ Область захвачена: {actual_width}x{actual_height}, {file_size} bytes, {capture_time:.3f}s")
            
            return ScreenshotResult(
                success=True,
                data=screenshot_data,
                capture_time=capture_time
            )
            
        except subprocess.TimeoutExpired:
            error_msg = f"Screenshot region capture timeout ({config.timeout}s)"
            logger.error(f"❌ {error_msg}")
            return ScreenshotResult(
                success=False,
                error=error_msg,
                capture_time=config.timeout
            )
        except Exception as e:
            error_msg = f"Screenshot region capture error: {e}"
            logger.error(f"❌ {error_msg}")
            return ScreenshotResult(
                success=False,
                error=error_msg,
                capture_time=time.time() - start_time if 'start_time' in locals() else 0.0
            )
    
    def test_capture(self) -> bool:
        """
        Тестирует возможность захвата скриншота
        
        Returns:
            bool: True если захват возможен
        """
        try:
            # Проверяем доступность команды screencapture
            result = subprocess.run(
                ["which", "screencapture"],
                capture_output=True,
                text=True,
                timeout=5.0
            )
            
            if result.returncode != 0:
                logger.warning("⚠️ screencapture command not found")
                return False
            
            # Пробуем сделать тестовый снимок
            temp_dir = Path(tempfile.gettempdir()) / "nexy_screenshots"
            temp_dir.mkdir(parents=True, exist_ok=True)
            test_file = temp_dir / "test_screenshot.jpg"
            
            cmd = f"screencapture -x -t jpg {shlex.quote(str(test_file))}"
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10.0
            )
            
            success = result.returncode == 0 and test_file.exists()
            
            # Удаляем тестовый файл
            if test_file.exists():
                test_file.unlink()
            
            if success:
                logger.info("✅ Screenshot capture test passed")
            else:
                logger.warning(f"⚠️ Screenshot capture test failed: {result.stderr.strip()}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Screenshot test error: {e}")
            return False
    
    def get_screen_info(self) -> Dict[str, Any]:
        """
        Получает информацию об экране
        
        Returns:
            dict: Информация об экране
        """
        try:
            # Используем system_profiler для получения информации о дисплее
            result = subprocess.run(
                ["system_profiler", "SPDisplaysDataType", "-json"],
                capture_output=True,
                text=True,
                timeout=10.0
            )
            
            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)
                
                # Извлекаем информацию о первом дисплее
                displays = data.get("SPDisplaysDataType", [])
                if displays and len(displays) > 0:
                    display = displays[0]
                    return {
                        "displays": displays,
                        "primary_display": display,
                        "resolution": display.get("_spdisplays_resolution", "Unknown"),
                        "pixel_depth": display.get("_spdisplays_pixeldepth", "Unknown"),
                        "main_display": display.get("_spdisplays_main", "Unknown")
                    }
            
            # Fallback - простая информация
            return {
                "displays": [],
                "primary_display": None,
                "resolution": "Unknown",
                "pixel_depth": "Unknown",
                "main_display": "Unknown",
                "bridge_type": "simple_cli"
            }
            
        except Exception as e:
            logger.debug(f"Failed to get screen info: {e}")
            return {
                "displays": [],
                "error": str(e),
                "bridge_type": "simple_cli"
            }
    
    def _resize_if_needed(self, image_path: Path, config: ScreenshotConfig):
        """Изменяет размер изображения если нужно с пропорциональным масштабированием"""
        try:
            if config.max_width <= 0 and config.max_height <= 0:
                return
            
            # Получаем текущие размеры изображения
            current_width, current_height = self._get_image_dimensions(image_path)
            if current_width <= 0 or current_height <= 0:
                return
            
            # Вычисляем коэффициент масштабирования для пропорционального изменения
            scale_width = config.max_width / current_width if config.max_width > 0 else 1.0
            scale_height = config.max_height / current_height if config.max_height > 0 else 1.0
            scale_factor = min(scale_width, scale_height, 1.0)  # Не увеличиваем, только уменьшаем
            
            if scale_factor >= 1.0:
                logger.debug(f"Resize not needed: current={current_width}x{current_height}, scale={scale_factor:.2f}")
                return
            
            # Вычисляем новые размеры
            new_width = int(current_width * scale_factor)
            new_height = int(current_height * scale_factor)
            
            logger.info(f"📐 Изменяем размер: {current_width}x{current_height} → {new_width}x{new_height} (scale={scale_factor:.2f})")
            
            # Используем sips для пропорционального изменения размера
            cmd = f"sips -z {new_height} {new_width} {shlex.quote(str(image_path))}"
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10.0
            )
            
            if result.returncode == 0:
                logger.info(f"✅ Размер изменен успешно: {new_width}x{new_height}")
            else:
                logger.warning(f"⚠️ Ошибка изменения размера: {result.stderr.strip()}")
            
        except Exception as e:
            logger.debug(f"Failed to resize image: {e}")
    
    def _optimize_jpeg_quality(self, image_path: Path, config: ScreenshotConfig):
        """Оптимизирует качество JPEG для уменьшения размера файла"""
        try:
            # Маппинг качества из enum в проценты
            quality_map = {
                "low": 50,
                "medium": 75, 
                "high": 85,
                "maximum": 95
            }
            
            # Получаем качество из конфигурации
            quality_str = str(config.quality.value) if hasattr(config.quality, 'value') else str(config.quality)
            jpeg_quality = quality_map.get(quality_str.lower(), 75)
            
            logger.debug(f"Оптимизируем JPEG качество: {quality_str} → {jpeg_quality}%")
            
            # Используем sips для сжатия JPEG
            cmd = f"sips -s formatOptions {jpeg_quality} {shlex.quote(str(image_path))}"
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10.0
            )
            
            if result.returncode == 0:
                logger.debug(f"✅ JPEG оптимизирован с качеством {jpeg_quality}%")
            else:
                logger.debug(f"⚠️ Не удалось оптимизировать JPEG: {result.stderr.strip()}")
                
        except Exception as e:
            logger.debug(f"Failed to optimize JPEG quality: {e}")
    
    def _get_image_dimensions(self, image_path: Path) -> Tuple[int, int]:
        """Получает размеры изображения"""
        try:
            # Используем sips для получения размеров
            cmd = f"sips -g pixelWidth -g pixelHeight {shlex.quote(str(image_path))}"
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=5.0
            )
            
            if result.returncode == 0:
                width = height = None
                for line in result.stdout.splitlines():
                    if "pixelWidth:" in line:
                        try:
                            width = int(line.split(":")[-1].strip())
                        except ValueError:
                            pass
                    elif "pixelHeight:" in line:
                        try:
                            height = int(line.split(":")[-1].strip())
                        except ValueError:
                            pass
                
                if width and height:
                    return width, height
            
            # Fallback - возвращаем размеры по умолчанию
            return 1920, 1080
            
        except Exception as e:
            logger.debug(f"Failed to get image dimensions: {e}")
            return 1920, 1080
