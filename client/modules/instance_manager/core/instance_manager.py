"""
Основной класс для управления экземплярами приложения.
"""

import os
import fcntl
import time
import json
import psutil
from typing import Optional
from pathlib import Path

from .types import InstanceStatus, LockInfo, InstanceManagerConfig

class InstanceManager:
    """Менеджер экземпляров приложения с защитой от дублирования."""
    
    def __init__(self, config: InstanceManagerConfig):
        self.config = config
        self.lock_file = os.path.expanduser(config.lock_file)
        self.timeout_seconds = config.timeout_seconds
        self.pid_check = config.pid_check
        self.lock_fd = None
        
    async def check_single_instance(self) -> InstanceStatus:
        """Проверка на дублирование экземпляров с усиленной очисткой."""
        try:
            # Создаем директорию если не существует
            lock_dir = os.path.dirname(self.lock_file)
            os.makedirs(lock_dir, exist_ok=True)
            
            # Проверяем существующий lock
            if os.path.exists(self.lock_file):
                # УСИЛЕННАЯ ПРОВЕРКА: PID + имя процесса
                if await self._is_lock_valid():
                    return InstanceStatus.DUPLICATE
                else:
                    # Lock невалиден - очищаем
                    await self._cleanup_invalid_lock()
            
            return InstanceStatus.SINGLE
            
        except Exception as e:
            print(f"❌ Ошибка проверки дублирования: {e}")
            return InstanceStatus.ERROR
    
    async def acquire_lock(self) -> bool:
        """Захват блокировки с TOCTOU защитой."""
        try:
            # TOCTOU защита: O_CREAT | O_EXCL
            self.lock_fd = os.open(self.lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            fcntl.flock(self.lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            
            # Записываем информацию о процессе
            lock_info = {
                "pid": os.getpid(),
                "timestamp": time.time(),
                "bundle_id": "com.nexy.assistant",
                "process_name": "Nexy"
            }
            os.write(self.lock_fd, json.dumps(lock_info).encode())
            os.fsync(self.lock_fd)
            
            print("✅ Блокировка захвачена успешно")
            return True
            
        except FileExistsError:
            # Файл уже существует - проверяем валидность
            if await self._is_lock_valid():
                return False  # Дублирование обнаружено
            else:
                # Очищаем невалидный lock и пробуем снова
                await self._cleanup_invalid_lock()
                return await self.acquire_lock()
                
        except (OSError, IOError) as e:
            print(f"❌ Ошибка захвата блокировки: {e}")
            return False
    
    async def release_lock(self) -> bool:
        """Освобождение блокировки."""
        try:
            if self.lock_fd:
                fcntl.flock(self.lock_fd, fcntl.LOCK_UN)
                os.close(self.lock_fd)
                self.lock_fd = None
            
            if os.path.exists(self.lock_file):
                os.remove(self.lock_file)
            
            print("✅ Блокировка освобождена")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка освобождения блокировки: {e}")
            return False
    
    async def _is_lock_valid(self) -> bool:
        """УСИЛЕННАЯ проверка валидности блокировки."""
        try:
            if not os.path.exists(self.lock_file):
                return False
                
            # Проверяем время модификации файла
            mod_time = os.path.getmtime(self.lock_file)
            current_time = time.time()
            
            if (current_time - mod_time) > self.timeout_seconds:
                return False  # Устарел по времени
            
            # Проверяем содержимое файла
            try:
                with open(self.lock_file, 'r') as f:
                    lock_info = json.load(f)
            except (json.JSONDecodeError, IOError):
                return False  # Невалидный JSON
            
            # Проверяем PID процесса
            if self.pid_check and 'pid' in lock_info:
                pid = lock_info['pid']
                try:
                    # Проверяем что процесс существует и это наш процесс
                    process = psutil.Process(pid)
                    cmdline = ' '.join(process.cmdline())
                    
                    # Проверяем что это наш процесс
                    # Варианты: Nexy.app, python3 main.py, Python debug_script.py, Python test_script.py
                    is_nexy_app = process.name() == "Nexy"
                    is_python_main = process.name() in ["python3", "Python"] and "main.py" in cmdline
                    is_debug_script = process.name() in ["python3", "Python"] and "debug_lock_validation.py" in cmdline
                    is_test_script = process.name() in ["python3", "Python"] and "test_duplicate_detection.py" in cmdline
                    
                    if not (is_nexy_app or is_python_main or is_debug_script or is_test_script):
                        return False  # Не наш процесс
                        
                    # Дополнительная проверка через bundle_id или скрипты
                    cmdline_check = ('com.nexy.assistant' in cmdline or 'main.py' in cmdline or 
                                   'debug_lock_validation.py' in cmdline or 'test_duplicate_detection.py' in cmdline)
                    
                    if not cmdline_check:
                        return False  # Не наш процесс
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    return False  # Процесс не существует
            
            return True
            
        except Exception as e:
            print(f"⚠️ Ошибка проверки валидности lock: {e}")
            return False
    
    async def _cleanup_invalid_lock(self) -> bool:
        """Очистка невалидной блокировки."""
        try:
            if os.path.exists(self.lock_file):
                os.remove(self.lock_file)
            print("🧹 Невалидная блокировка очищена")
            return True
        except Exception as e:
            print(f"❌ Ошибка очистки невалидной блокировки: {e}")
            return False
    
    async def get_lock_info(self) -> Optional[dict]:
        """Получение информации о текущей блокировке."""
        try:
            if os.path.exists(self.lock_file):
                with open(self.lock_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"❌ Ошибка чтения информации о блокировке: {e}")
        return None
