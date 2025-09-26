#!/usr/bin/env python3
"""
ModuleCoordinatorIntegration - управляет жизненным циклом всех модулей
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class ModuleCoordinatorIntegration:
    """
    Управляет жизненным циклом всех модулей (start, stop, cleanup)
    """
    
    def __init__(self, modules: Optional[Dict[str, Any]] = None):
        """
        Инициализация ModuleCoordinatorIntegration
        
        Args:
            modules: Словарь модулей для управления
        """
        self.modules = modules or {}
        self.is_initialized = False
        self.modules_status = {}  # Отслеживание статуса модулей
        
        logger.info("ModuleCoordinatorIntegration создан")
    
    async def initialize(self) -> bool:
        """
        Инициализация интеграции
        
        Returns:
            True если инициализация успешна, False иначе
        """
        try:
            logger.info("Инициализация ModuleCoordinatorIntegration...")
            
            # Инициализируем все модули если они доступны
            if self.modules:
                logger.info(f"Найдено {len(self.modules)} модулей для инициализации")
                
                for module_name, module in self.modules.items():
                    try:
                        if hasattr(module, 'initialize'):
                            logger.debug(f"Инициализация модуля {module_name}")
                            await module.initialize()
                            self.modules_status[module_name] = 'initialized'
                            logger.debug(f"✅ Модуль {module_name} инициализирован")
                        else:
                            logger.warning(f"⚠️ Модуль {module_name} не имеет метода initialize")
                            self.modules_status[module_name] = 'no_initialize_method'
                    except Exception as e:
                        logger.error(f"❌ Ошибка инициализации модуля {module_name}: {e}")
                        self.modules_status[module_name] = f'initialization_error: {str(e)}'
            else:
                logger.warning("⚠️ Модули не предоставлены для координации")
            
            self.is_initialized = True
            logger.info("✅ ModuleCoordinatorIntegration инициализирован успешно")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации ModuleCoordinatorIntegration: {e}")
            return False
    
    async def start_all_modules(self) -> Dict[str, Any]:
        """
        Запуск всех модулей
        
        Returns:
            Результаты запуска модулей
        """
        if not self.is_initialized:
            logger.error("❌ ModuleCoordinatorIntegration не инициализирован")
            return {'success': False, 'error': 'Not initialized'}
        
        try:
            logger.info("Запуск всех модулей...")
            results = {}
            
            for module_name, module in self.modules.items():
                try:
                    if hasattr(module, 'start'):
                        logger.debug(f"Запуск модуля {module_name}")
                        await module.start()
                        results[module_name] = 'started'
                        self.modules_status[module_name] = 'running'
                        logger.debug(f"✅ Модуль {module_name} запущен")
                    else:
                        logger.warning(f"⚠️ Модуль {module_name} не имеет метода start")
                        results[module_name] = 'no_start_method'
                        self.modules_status[module_name] = 'no_start_method'
                except Exception as e:
                    logger.error(f"❌ Ошибка запуска модуля {module_name}: {e}")
                    results[module_name] = f'start_error: {str(e)}'
                    self.modules_status[module_name] = f'start_error: {str(e)}'
            
            logger.info(f"✅ Запуск модулей завершен: {len(results)} модулей обработано")
            return {
                'success': True,
                'results': results,
                'modules_status': self.modules_status.copy()
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска модулей: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def stop_all_modules(self) -> Dict[str, Any]:
        """
        Остановка всех модулей
        
        Returns:
            Результаты остановки модулей
        """
        if not self.is_initialized:
            logger.error("❌ ModuleCoordinatorIntegration не инициализирован")
            return {'success': False, 'error': 'Not initialized'}
        
        try:
            logger.info("Остановка всех модулей...")
            results = {}
            
            for module_name, module in self.modules.items():
                try:
                    if hasattr(module, 'stop'):
                        logger.debug(f"Остановка модуля {module_name}")
                        await module.stop()
                        results[module_name] = 'stopped'
                        self.modules_status[module_name] = 'stopped'
                        logger.debug(f"✅ Модуль {module_name} остановлен")
                    else:
                        logger.warning(f"⚠️ Модуль {module_name} не имеет метода stop")
                        results[module_name] = 'no_stop_method'
                        self.modules_status[module_name] = 'no_stop_method'
                except Exception as e:
                    logger.error(f"❌ Ошибка остановки модуля {module_name}: {e}")
                    results[module_name] = f'stop_error: {str(e)}'
                    self.modules_status[module_name] = f'stop_error: {str(e)}'
            
            logger.info(f"✅ Остановка модулей завершена: {len(results)} модулей обработано")
            return {
                'success': True,
                'results': results,
                'modules_status': self.modules_status.copy()
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка остановки модулей: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def cleanup_all_modules(self) -> Dict[str, Any]:
        """
        Очистка всех модулей
        
        Returns:
            Результаты очистки модулей
        """
        if not self.is_initialized:
            logger.error("❌ ModuleCoordinatorIntegration не инициализирован")
            return {'success': False, 'error': 'Not initialized'}
        
        try:
            logger.info("Очистка всех модулей...")
            results = {}
            
            for module_name, module in self.modules.items():
                try:
                    if hasattr(module, 'cleanup'):
                        logger.debug(f"Очистка модуля {module_name}")
                        await module.cleanup()
                        results[module_name] = 'cleaned'
                        self.modules_status[module_name] = 'cleaned'
                        logger.debug(f"✅ Модуль {module_name} очищен")
                    else:
                        logger.warning(f"⚠️ Модуль {module_name} не имеет метода cleanup")
                        results[module_name] = 'no_cleanup_method'
                        self.modules_status[module_name] = 'no_cleanup_method'
                except Exception as e:
                    logger.error(f"❌ Ошибка очистки модуля {module_name}: {e}")
                    results[module_name] = f'cleanup_error: {str(e)}'
                    self.modules_status[module_name] = f'cleanup_error: {str(e)}'
            
            logger.info(f"✅ Очистка модулей завершена: {len(results)} модулей обработано")
            return {
                'success': True,
                'results': results,
                'modules_status': self.modules_status.copy()
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка очистки модулей: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def add_module(self, name: str, module: Any) -> bool:
        """
        Добавление модуля для координации
        
        Args:
            name: Имя модуля
            module: Экземпляр модуля
            
        Returns:
            True если модуль добавлен, False иначе
        """
        try:
            self.modules[name] = module
            self.modules_status[name] = 'added'
            logger.info(f"✅ Модуль {name} добавлен для координации")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка добавления модуля {name}: {e}")
            return False
    
    def remove_module(self, name: str) -> bool:
        """
        Удаление модуля из координации
        
        Args:
            name: Имя модуля
            
        Returns:
            True если модуль удален, False иначе
        """
        try:
            if name in self.modules:
                del self.modules[name]
                if name in self.modules_status:
                    del self.modules_status[name]
                logger.info(f"✅ Модуль {name} удален из координации")
                return True
            else:
                logger.warning(f"⚠️ Модуль {name} не найден")
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка удаления модуля {name}: {e}")
            return False
    
    async def get_status(self) -> Dict[str, Any]:
        """
        Получение статуса координации
        
        Returns:
            Словарь со статусом
        """
        try:
            return {
                'initialized': self.is_initialized,
                'modules_count': len(self.modules),
                'modules_status': self.modules_status.copy(),
                'available_methods': {
                    'start': [name for name, module in self.modules.items() if hasattr(module, 'start')],
                    'stop': [name for name, module in self.modules.items() if hasattr(module, 'stop')],
                    'cleanup': [name for name, module in self.modules.items() if hasattr(module, 'cleanup')]
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения статуса: {e}")
            return {
                'initialized': False,
                'error': str(e)
            }
    
    async def cleanup(self):
        """Очистка ресурсов"""
        try:
            logger.info("Очистка ModuleCoordinatorIntegration...")
            
            # Очищаем все модули
            await self.cleanup_all_modules()
            
            # Очищаем внутренние структуры
            self.modules.clear()
            self.modules_status.clear()
            
            self.is_initialized = False
            logger.info("✅ ModuleCoordinatorIntegration очищен")
            
        except Exception as e:
            logger.error(f"❌ Ошибка очистки ModuleCoordinatorIntegration: {e}")
