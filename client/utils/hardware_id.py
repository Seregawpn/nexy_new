import subprocess
import hashlib
import logging
import json
import os
from typing import Optional
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

class HardwareIdentifier:
    """Генератор уникального Hardware ID для macOS с кэшированием"""
    
    def __init__(self):
        self._hardware_id = None
        self._salt = "voice_assistant_2025"  # Соль для хеширования
        self._cache_file = Path.home() / ".voice_assistant" / "hardware_id_cache.json"
        self._cache_dir = self._cache_file.parent
        
        # Создаем директорию для кэша если её нет
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        
    def _load_cached_id(self) -> Optional[str]:
        """Загружаем Hardware ID из кэша"""
        try:
            if self._cache_file.exists():
                with open(self._cache_file, 'r') as f:
                    cache_data = json.load(f)
                    
                # Проверяем валидность кэша
                if self._validate_cache(cache_data):
                    cached_id = cache_data.get('hardware_id')
                    logger.info(f"✅ Hardware ID загружен из кэша: {cached_id[:16]}...")
                    return cached_id
                else:
                    logger.warning("⚠️ Кэш устарел, пересоздаем...")
                    
        except Exception as e:
            logger.warning(f"⚠️ Ошибка загрузки кэша: {e}")
            
        return None
    
    def _save_to_cache(self, hardware_id: str, hardware_info: dict):
        """Сохраняем Hardware ID в кэш"""
        try:
            cache_data = {
                'hardware_id': hardware_id,
                'hardware_info': hardware_info,
                'cached_at': str(datetime.now()),
                'version': '1.0'
            }
            
            with open(self._cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
                
            logger.info(f"✅ Hardware ID сохранен в кэш: {hardware_id[:16]}...")
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения в кэш: {e}")
    
    def _validate_cache(self, cache_data: dict) -> bool:
        """Проверяем валидность кэша"""
        try:
            # Проверяем обязательные поля
            required_fields = ['hardware_id', 'hardware_info', 'cached_at', 'version']
            if not all(field in cache_data for field in required_fields):
                return False
            
            # Проверяем версию кэша
            if cache_data.get('version') != '1.0':
                return False
            
            # Проверяем формат Hardware ID (64 символа hex)
            hardware_id = cache_data.get('hardware_id', '')
            if len(hardware_id) != 64 or not all(c in '0123456789abcdef' for c in hardware_id):
                return False
            
            # TODO: Можно добавить проверку по времени (например, кэш действителен 30 дней)
            # from datetime import datetime, timedelta
            # cached_time = datetime.fromisoformat(cache_data['cached_at'])
            # if datetime.now() - cached_time > timedelta(days=30):
            #     return False
            
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ Ошибка валидации кэша: {e}")
            return False
    
    def get_hardware_uuid(self) -> Optional[str]:
        """Получение Hardware UUID через system_profiler"""
        try:
            result = subprocess.run(
                ["system_profiler", "SPHardwareDataType"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'Hardware UUID:' in line:
                        uuid = line.split(':')[1].strip()
                        logger.info(f"✅ Hardware UUID получен: {uuid}")
                        return uuid
                        
            logger.warning("⚠️ Hardware UUID не найден в system_profiler")
            return None
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения Hardware UUID: {e}")
            return None
    
    def get_serial_number(self) -> Optional[str]:
        """Получение Serial Number через system_profiler"""
        try:
            result = subprocess.run(
                ["system_profiler", "SPHardwareDataType"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'Serial Number (system):' in line:
                        serial = line.split(':')[1].strip()
                        logger.info(f"✅ Serial Number получен: {serial}")
                        return serial
                        
            logger.warning("⚠️ Serial Number не найден в system_profiler")
            return None
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения Serial Number: {e}")
            return None
    
    def get_mac_address(self) -> Optional[str]:
        """Получение MAC адреса основной сетевой карты"""
        try:
            result = subprocess.run(
                ["ifconfig", "en0"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'ether' in line:
                        mac = line.split()[1].strip()
                        logger.info(f"✅ MAC Address получен: {mac}")
                        return mac
                        
            logger.warning("⚠️ MAC Address не найден в ifconfig")
            return None
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения MAC Address: {e}")
            return None
    
    def generate_hardware_id(self, force_regenerate: bool = False) -> str:
        """
        Генерация уникального Hardware ID с кэшированием
        
        Args:
            force_regenerate: Принудительно пересоздать ID (игнорировать кэш)
        """
        # Если не принудительная регенерация, пробуем загрузить из кэша
        if not force_regenerate and self._hardware_id is None:
            cached_id = self._load_cached_id()
            if cached_id:
                self._hardware_id = cached_id
                return self._hardware_id
        
        # Если кэш не сработал, генерируем новый ID
        if self._hardware_id is None or force_regenerate:
            # 1. Пытаемся получить Hardware UUID
            hardware_uuid = self.get_hardware_uuid()
            if hardware_uuid:
                self._hardware_id = self._hash_identifier(hardware_uuid)
                logger.info(f"✅ Hardware ID сгенерирован из UUID: {self._hardware_id[:16]}...")
                
                # Сохраняем в кэш
                hardware_info = self.get_hardware_info()
                self._save_to_cache(self._hardware_id, hardware_info)
                
                return self._hardware_id
            
            # 2. Fallback на Serial Number
            serial_number = self.get_serial_number()
            if serial_number:
                self._hardware_id = self._hash_identifier(serial_number)
                logger.info(f"✅ Hardware ID сгенерирован из Serial Number: {self._hardware_id[:16]}...")
                
                # Сохраняем в кэш
                hardware_info = self.get_hardware_info()
                self._save_to_cache(self._hardware_id, hardware_info)
                
                return self._hardware_id
            
            # 3. Fallback на MAC Address
            mac_address = self.get_mac_address()
            if mac_address:
                self._hardware_id = self._hash_identifier(mac_address)
                logger.info(f"✅ Hardware ID сгенерирован из MAC Address: {self._hardware_id[:16]}...")
                
                # Сохраняем в кэш
                hardware_info = self.get_hardware_info()
                self._save_to_cache(self._hardware_id, hardware_info)
                
                return self._hardware_id
            
            # 4. Генерируем случайный ID (fallback)
            import uuid
            random_id = str(uuid.uuid4())
            self._hardware_id = self._hash_identifier(random_id)
            logger.warning(f"⚠️ Hardware ID сгенерирован случайно: {self._hardware_id[:16]}...")
            
            # Сохраняем в кэш
            hardware_info = self.get_hardware_info()
            self._save_to_cache(self._hardware_id, hardware_info)
        
        return self._hardware_id
    
    def clear_cache(self):
        """Очищает кэш Hardware ID"""
        try:
            if self._cache_file.exists():
                self._cache_file.unlink()
                logger.info("✅ Кэш Hardware ID очищен")
            self._hardware_id = None
        except Exception as e:
            logger.error(f"❌ Ошибка очистки кэша: {e}")
    
    def get_cache_info(self) -> dict:
        """Получает информацию о кэше"""
        try:
            if self._cache_file.exists():
                with open(self._cache_file, 'r') as f:
                    cache_data = json.load(f)
                return {
                    'exists': True,
                    'size': self._cache_file.stat().st_size,
                    'modified': self._cache_file.stat().st_mtime,
                    'data': cache_data
                }
            else:
                return {'exists': False}
        except Exception as e:
            return {'exists': False, 'error': str(e)}
    
    def _hash_identifier(self, identifier: str) -> str:
        """Хеширование идентификатора с солью"""
        combined = identifier + self._salt
        return hashlib.sha256(combined.encode()).hexdigest()
    
    def get_hardware_info(self) -> dict:
        """Получение полной информации об оборудовании"""
        return {
            "hardware_uuid": self.get_hardware_uuid(),
            "serial_number": self.get_serial_number(),
            "mac_address": self.get_mac_address(),
            "hardware_id_hash": self.generate_hardware_id()
        }

# Глобальный экземпляр для переиспользования
_hardware_identifier = None

def get_hardware_id(force_regenerate: bool = False) -> str:
    """Получение Hardware ID (синглтон) с кэшированием"""
    global _hardware_identifier
    if _hardware_identifier is None:
        _hardware_identifier = HardwareIdentifier()
    return _hardware_identifier.generate_hardware_id(force_regenerate)

def get_hardware_info() -> dict:
    """Получение информации об оборудовании (синглтон)"""
    global _hardware_identifier
    if _hardware_identifier is None:
        _hardware_identifier = HardwareIdentifier()
    return _hardware_identifier.get_hardware_info()

def clear_hardware_id_cache():
    """Очищает кэш Hardware ID"""
    global _hardware_identifier
    if _hardware_identifier:
        _hardware_identifier.clear_cache()

def get_cache_info() -> dict:
    """Получает информацию о кэше Hardware ID"""
    global _hardware_identifier
    if _hardware_identifier is None:
        _hardware_identifier = HardwareIdentifier()
    return _hardware_identifier.get_cache_info()

# =====================================================
# ТЕСТИРОВАНИЕ
# =====================================================

if __name__ == "__main__":
    # Настройка логирования
    logging.basicConfig(level=logging.INFO)
    
    print("🧪 Тест генерации Hardware ID с кэшированием")
    print("=" * 60)
    
    # Создаем экземпляр
    identifier = HardwareIdentifier()
    
    # Первый запуск - генерируем ID
    print("\n🔄 ПЕРВЫЙ ЗАПУСК:")
    hardware_info = identifier.get_hardware_info()
    hardware_id = identifier.generate_hardware_id()
    
    print(f"🆔 Hardware UUID: {hardware_info['hardware_uuid']}")
    print(f"📱 Serial Number: {hardware_info['serial_number']}")
    print(f"🌐 MAC Address: {hardware_info['mac_address']}")
    print(f"🔐 Hardware ID Hash: {hardware_id[:32]}...")
    
    # Проверяем кэш
    print(f"\n💾 ИНФОРМАЦИЯ О КЭШЕ:")
    cache_info = identifier.get_cache_info()
    if cache_info['exists']:
        print(f"✅ Кэш создан: {cache_info['size']} байт")
        print(f"📅 Модифицирован: {cache_info['modified']}")
    else:
        print("❌ Кэш не найден")
    
    # Второй запуск - загружаем из кэша
    print("\n🔄 ВТОРОЙ ЗАПУСК (из кэша):")
    cached_id = identifier.generate_hardware_id()
    print(f"🔐 Hardware ID из кэша: {cached_id[:32]}...")
    
    # Проверяем, что ID одинаковые
    if hardware_id == cached_id:
        print("✅ Кэширование работает - ID одинаковые!")
    else:
        print("❌ Ошибка кэширования - ID разные!")
    
    print("\n✅ Тест завершен успешно!")
