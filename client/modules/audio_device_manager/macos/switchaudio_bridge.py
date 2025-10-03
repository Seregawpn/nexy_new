"""
Мост для работы с switchaudio - утилитой переключения аудио устройств на macOS
"""

import asyncio
import logging
import subprocess
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Callable
from ..core.types import AudioDevice, DeviceType, DeviceStatus, DevicePriority

logger = logging.getLogger(__name__)

class SwitchAudioBridge:
    """Мост для работы с switchaudio и мониторинга устройств"""
    
    def __init__(self):
        self._is_monitoring = False
        self._device_listener: Optional[Callable] = None
        self._current_devices: Dict[str, AudioDevice] = {}
        self._monitoring_task: Optional[asyncio.Task] = None
        self._last_device_count = 0
    
    def _get_switchaudio_path(self) -> str:
        """
        Определяет путь к бинарнику SwitchAudioSource.
        
        Поддерживает:
        - PyInstaller onefile (sys._MEIPASS)
        - PyInstaller bundle (.app/Contents/Resources/)
        - Development/Homebrew (PATH)
        
        Returns:
            str: Полный путь к SwitchAudioSource или 'SwitchAudioSource' для PATH
        """
        # 1) PyInstaller onefile: проверяем sys._MEIPASS
        if hasattr(sys, "_MEIPASS"):
            path = Path(sys._MEIPASS) / "resources" / "audio" / "SwitchAudioSource"
            if path.exists():
                logger.debug(f"🔍 Найден SwitchAudioSource (onefile): {path}")
                return str(path)
        
        # 2) PyInstaller bundle: проверяем Contents/Resources/
        macos_dir = Path(sys.argv[0]).resolve().parent
        resources_path = macos_dir.parent / "Resources" / "resources" / "audio" / "SwitchAudioSource"
        if resources_path.exists():
            logger.debug(f"🔍 Найден SwitchAudioSource (bundle): {resources_path}")
            return str(resources_path)
        
        # 3) Fallback на PATH (Homebrew в dev режиме)
        logger.debug("🔍 Используем SwitchAudioSource из PATH")
        return 'SwitchAudioSource'
        
    async def start_monitoring(self, device_change_callback: Callable):
        """Запуск мониторинга изменений устройств"""
        if self._is_monitoring:
            logger.warning("⚠️ Мониторинг уже запущен")
            return
            
        self._device_listener = device_change_callback
        self._is_monitoring = True
        
        try:
            # Получаем начальный список устройств
            initial_devices = await self.get_available_devices()
            self._current_devices = {device.id: device for device in initial_devices}
            self._last_device_count = len(initial_devices)
            
            # Запускаем мониторинг через polling
            self._monitoring_task = asyncio.create_task(self._monitor_devices())
            
            logger.info(f"✅ SwitchAudio мониторинг запущен, найдено {len(initial_devices)} устройств")
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска мониторинга: {e}")
            self._is_monitoring = False
            raise
    
    async def stop_monitoring(self):
        """Остановка мониторинга"""
        if not self._is_monitoring:
            return
            
        try:
            self._is_monitoring = False
            self._device_listener = None
            self._current_devices.clear()
            
            if self._monitoring_task and not self._monitoring_task.done():
                self._monitoring_task.cancel()
                try:
                    await self._monitoring_task
                except asyncio.CancelledError:
                    pass
            
            logger.info("✅ SwitchAudio мониторинг остановлен")
            
        except Exception as e:
            logger.error(f"❌ Ошибка остановки мониторинга: {e}")
    
    async def _monitor_devices(self):
        """Мониторинг устройств через polling"""
        try:
            logger.info("🔄 Запуск мониторинга устройств через switchaudio...")
            logger.info("💡 Подключайте/отключайте наушники для тестирования")
            
            while self._is_monitoring:
                try:
                    # Получаем текущий список устройств
                    current_devices = await self.get_available_devices()
                    current_count = len(current_devices)
                    
                    # Проверяем изменения в количестве устройств
                    if current_count != self._last_device_count:
                        logger.info(f"🔄 Обнаружено изменение: {self._last_device_count} -> {current_count} устройств")
                        
                        # Определяем изменения
                        current_devices_dict = {device.id: device for device in current_devices}
                        old_devices = self._current_devices.copy()
                        self._current_devices = current_devices_dict
                        self._last_device_count = current_count
                        
                        # Создаем объект изменений
                        from ..core.types import DeviceChange
                        changes = DeviceChange(
                            added=[device for device in current_devices if device.id not in old_devices],
                            removed=[device for device_id, device in old_devices.items() if device_id not in current_devices_dict],
                            current_devices=current_devices_dict,
                            timestamp=datetime.now(),
                            change_type="device_change"
                        )
                        
                        # Уведомляем callback
                        if self._device_listener:
                            await self._device_listener(changes)
                    
                    # Ждем перед следующей проверкой
                    await asyncio.sleep(1)  # Проверяем каждую секунду
                    
                except Exception as e:
                    logger.error(f"❌ Ошибка в мониторинге устройств: {e}")
                    await asyncio.sleep(3)  # Ждем дольше при ошибке
                    
        except Exception as e:
            logger.error(f"❌ Ошибка в monitor_devices: {e}")
    
    async def get_available_devices(self) -> List[AudioDevice]:
        """Получение списка доступных аудио устройств через switchaudio"""
        try:
            # Используем switchaudio для получения списка устройств
            devices = await self._get_devices_from_switchaudio()
            
            # Сортируем по приоритету (меньшее значение = выше приоритет)
            devices.sort(key=lambda x: x.priority.value)
            
            return devices
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения устройств: {e}")
            return []
    
    async def _get_devices_from_switchaudio(self) -> List[AudioDevice]:
        """Получение устройств через switchaudio"""
        try:
            # Получаем путь к бинарнику и запускаем
            switchaudio_cmd = self._get_switchaudio_path()
            result = subprocess.run([
                switchaudio_cmd, '-a'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                logger.warning("⚠️ switchaudio недоступен, возвращаем пустой список")
                return []
            
            # Парсим вывод switchaudio
            devices = []
            lines = result.stdout.strip().split('\n')
            
            for line in lines:
                if line.strip():
                    device = await self._parse_switchaudio_line(line)
                    if device:
                        devices.append(device)
            
            # Если не нашли устройств, возвращаем пустой список
            if not devices:
                logger.info("ℹ️ Устройства не найдены через switchaudio")
                return []
            
            return devices
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения устройств через switchaudio: {e}")
            return []
    
    async def _parse_switchaudio_line(self, line: str) -> Optional[AudioDevice]:
        """Парсинг строки вывода switchaudio"""
        try:
            # Пример строки: "MacBook Air Speakers (Built-in Output)"
            # Или: "AirPods Pro (Bluetooth)"
            
            # Извлекаем имя устройства
            name_match = re.match(r'^(.+?)\s*\((.+?)\)', line)
            if not name_match:
                # Если нет скобок, используем всю строку как имя
                name = line.strip()
                device_type_str = "Unknown"
            else:
                name = name_match.group(1).strip()
                device_type_str = name_match.group(2).strip()
            
            # Создаем ID устройства
            device_id = str(hash(name))
            
            # Определяем тип устройства
            device_type = await self._detect_device_type(name, device_type_str)
            
            # Определяем количество каналов
            channels = await self._get_device_channels(name)
            
            # Определяем дополнительные свойства
            is_bluetooth = 'bluetooth' in device_type_str.lower() or 'bt' in device_type_str.lower()
            is_usb = 'usb' in device_type_str.lower()
            is_builtin = 'built-in' in device_type_str.lower() or 'internal' in device_type_str.lower()
            
            # Определяем приоритет на основе типа устройства и канальности
            if is_bluetooth and device_type == DeviceType.OUTPUT:
                priority = DevicePriority.HIGHEST  # Bluetooth наушники - высший приоритет
            elif device_type == DeviceType.OUTPUT and channels == 2 and not is_builtin:
                priority = DevicePriority.HIGH  # Двухканальные внешние устройства (наушники)
            elif device_type == DeviceType.OUTPUT and channels == 1 and is_builtin:
                priority = DevicePriority.LOWEST  # Одноканальные встроенные устройства
            elif is_builtin:
                priority = DevicePriority.LOWEST  # Встроенные устройства
            else:
                priority = DevicePriority.NORMAL  # Остальные устройства
            
            # Создаем объект устройства
            device = AudioDevice(
                id=device_id,
                name=name,
                type=device_type,
                status=DeviceStatus.AVAILABLE,
                channels=channels,
                priority=priority
            )
            
            return device
            
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга строки switchaudio: {e}")
            return None
    
    async def _detect_device_type(self, name: str, device_type_str: str) -> DeviceType:
        """Определение типа устройства по имени и типу"""
        try:
            name_lower = name.lower()
            type_lower = device_type_str.lower()
            
            # Ключевые слова для наушников
            headphone_keywords = [
                'headphone', 'headset', 'earphone', 'earbud', 'earpod',
                'airpod', 'beats', 'sony', 'bose', 'sennheiser', 'audio-technica',
                'bluetooth', 'wireless', 'наушник', 'гарнитур'
            ]
            
            # Ключевые слова для динамиков
            speaker_keywords = [
                'speaker', 'monitor', 'studio', 'desktop', 'external',
                'built-in', 'internal', 'macbook', 'imac', 'mac pro',
                'динамик', 'колонк', 'монитор', 'output'
            ]
            
            # Ключевые слова для микрофонов (исключаем из переключения)
            microphone_keywords = [
                'microphone', 'mic', 'input', 'вход', 'микрофон'
            ]
            
            # Проверяем на микрофоны (исключаем из переключения)
            if (any(keyword in name_lower for keyword in microphone_keywords) or
                any(keyword in type_lower for keyword in microphone_keywords)):
                return DeviceType.INPUT  # Микрофоны - это INPUT
            
            # Проверяем на наушники
            if (any(keyword in name_lower for keyword in headphone_keywords) or
                any(keyword in type_lower for keyword in headphone_keywords)):
                return DeviceType.OUTPUT  # Наушники - это OUTPUT
            
            # Проверяем на динамики
            if (any(keyword in name_lower for keyword in speaker_keywords) or
                any(keyword in type_lower for keyword in speaker_keywords)):
                return DeviceType.OUTPUT  # Динамики - это OUTPUT
            
            # По умолчанию считаем OUTPUT
            return DeviceType.OUTPUT
            
        except Exception as e:
            logger.error(f"❌ Ошибка определения типа устройства: {e}")
            return DeviceType.OUTPUT  # По умолчанию OUTPUT
    
    async def _get_device_channels(self, name: str) -> int:
        """Получение количества каналов устройства"""
        try:
            name_lower = name.lower()
            
            # Наушники обычно стерео (двухканальные)
            if any(keyword in name_lower for keyword in ['headphone', 'headset', 'earphone', 'earbud', 'airpod']):
                return 2
            
            # Встроенные динамики macOS обычно одноканальные
            if any(keyword in name_lower for keyword in ['built-in', 'internal', 'macbook', 'imac']):
                return 1
            
            # Микрофоны моно (одноканальные)
            if any(keyword in name_lower for keyword in ['microphone', 'mic']):
                return 1
            
            # По умолчанию стерео (двухканальные)
            return 2
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения каналов устройства: {e}")
            return 2
    
    async def _get_fallback_devices(self) -> List[AudioDevice]:
        """Fallback устройства если switchaudio недоступен"""
        try:
            devices = [
                AudioDevice(
                    id="builtin_speakers",
                    name="MacBook Air Speakers",
                    type=DeviceType.OUTPUT,
                    status=DeviceStatus.AVAILABLE,
                    channels=2,
                    priority=DevicePriority.LOWEST
                ),
                AudioDevice(
                    id="builtin_microphone",
                    name="MacBook Air Microphone",
                    type=DeviceType.INPUT,
                    status=DeviceStatus.AVAILABLE,
                    channels=1,
                    priority=DevicePriority.LOWEST
                )
            ]
            
            return devices
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания fallback устройств: {e}")
            return []
    
    async def get_default_output_device(self) -> Optional[AudioDevice]:
        """Получение устройства вывода по умолчанию"""
        try:
            devices = await self.get_available_devices()
            if devices:
                return devices[0]  # Возвращаем первое (с наивысшим приоритетом)
            return None
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения устройства по умолчанию: {e}")
            return None
    
    async def set_default_output_device(self, device_id: str) -> bool:
        """Установка устройства вывода по умолчанию через switchaudio"""
        try:
            # Находим устройство по ID
            devices = await self.get_available_devices()
            target_device = next((d for d in devices if d.id == device_id), None)
            
            if not target_device:
                logger.error(f"❌ Устройство с ID {device_id} не найдено")
                return False
            
            # Проверяем, что это не микрофон
            if target_device.type == DeviceType.INPUT:
                logger.warning(f"⚠️ Пропускаем переключение на микрофон: {target_device.name}")
                return False
            
            logger.info(f"🔄 Попытка переключения на: {target_device.name} (тип: {target_device.type.value})")
            
            # Получаем путь к бинарнику и используем SwitchAudioSource для переключения
            switchaudio_cmd = self._get_switchaudio_path()
            result = subprocess.run([
                switchaudio_cmd, '-t', 'output', '-s', target_device.name
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                logger.info(f"✅ Успешно переключились на: {target_device.name}")
                return True
            else:
                logger.error(f"❌ Ошибка переключения на {target_device.name}: {result.stderr}")
                
                # Пробуем альтернативный способ переключения
                logger.info("🔄 Пробуем альтернативный способ переключения...")
                return await self._try_alternative_switch(target_device)
            
        except Exception as e:
            logger.error(f"❌ Ошибка установки устройства по умолчанию: {e}")
            return False
    
    async def _try_alternative_switch(self, target_device: AudioDevice) -> bool:
        """Альтернативный способ переключения устройства"""
        try:
            # Получаем путь к бинарнику
            switchaudio_cmd = self._get_switchaudio_path()
            
            # Пробуем переключиться по части имени
            name_parts = target_device.name.split()
            for part in name_parts:
                if len(part) > 3:  # Игнорируем короткие части
                    logger.info(f"🔄 Пробуем переключиться по части имени: {part}")
                    result = subprocess.run([
                        switchaudio_cmd, '-t', 'output', '-s', part
                    ], capture_output=True, text=True, timeout=10)
                    
                    if result.returncode == 0:
                        logger.info(f"✅ Успешно переключились на: {part}")
                        return True
            
            # Если не получилось, пробуем переключиться на встроенные динамики
            logger.info("🔄 Переключаемся на встроенные динамики...")
            result = subprocess.run([
                switchaudio_cmd, '-t', 'output', '-s', 'MacBook Air Speakers'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                logger.info("✅ Успешно переключились на встроенные динамики")
                return True
            else:
                logger.error("❌ Не удалось переключиться даже на встроенные динамики")
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка альтернативного переключения: {e}")
            return False









































