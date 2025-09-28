"""
Основной менеджер разрешений
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Callable
from .types import (
    PermissionType, PermissionStatus, PermissionInfo, PermissionResult,
    PermissionEvent, PermissionConfig, PermissionManagerState
)
from .config import PermissionConfigManager
from ..macos.permission_handler import MacOSPermissionHandler

logger = logging.getLogger(__name__)

class PermissionManager:
    """Менеджер разрешений"""
    
    def __init__(self, config_path: str = "config/permissions_config.yaml"):
        self.config_manager = PermissionConfigManager(config_path)
        self.config: Optional[PermissionConfig] = None
        self.state = PermissionManagerState()
        self.macos_handler = MacOSPermissionHandler()
        self.is_initialized = False
        self.is_monitoring = False
        self._monitoring_task: Optional[asyncio.Task] = None
    
    async def initialize(self) -> bool:
        """Инициализация менеджера разрешений"""
        try:
            logger.info("🔧 Инициализация PermissionManager")
            
            # Загружаем конфигурацию
            self.config = self.config_manager.get_config()
            self.state.config = self.config
            
            # Инициализируем информацию о разрешениях
            await self._initialize_permissions()
            
            self.is_initialized = True
            logger.info("✅ PermissionManager инициализирован")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации PermissionManager: {e}")
            return False
    
    async def _initialize_permissions(self):
        """Инициализировать информацию о разрешениях"""
        descriptions = {
            PermissionType.MICROPHONE: "Доступ к микрофону для распознавания речи",
            PermissionType.SCREEN_CAPTURE: "Доступ к захвату экрана для скриншотов",
            PermissionType.CAMERA: "Доступ к камере для захвата экрана",
            PermissionType.NETWORK: "Доступ к сети для связи с сервером",
            PermissionType.NOTIFICATIONS: "Доступ к уведомлениям"
        }
        
        instructions = {
            PermissionType.MICROPHONE: "Откройте Системные настройки > Конфиденциальность > Микрофон",
            PermissionType.SCREEN_CAPTURE: "Откройте Системные настройки > Конфиденциальность > Захват экрана",
            PermissionType.CAMERA: "Откройте Системные настройки > Конфиденциальность > Камера",
            PermissionType.NETWORK: "Проверьте подключение к интернету",
            PermissionType.NOTIFICATIONS: "Откройте Системные настройки > Уведомления"
        }
        
        for perm_type in PermissionType:
            required = perm_type in self.config.required_permissions
            info = PermissionInfo(
                permission_type=perm_type,
                status=PermissionStatus.NOT_DETERMINED,
                granted=False,
                message=descriptions.get(perm_type, ""),
                last_checked=time.time()
            )
            self.state.set_permission(perm_type, info)
    
    async def check_permission(self, permission_type: PermissionType) -> PermissionResult:
        """Проверить конкретное разрешение"""
        try:
            logger.info(f"🔍 Проверка разрешения: {permission_type.value}")
            
            # Вызываем соответствующий метод проверки
            if permission_type == PermissionType.MICROPHONE:
                result = await self.macos_handler.check_microphone_permission()
            elif permission_type == PermissionType.SCREEN_CAPTURE:
                result = await self.macos_handler.check_screen_capture_permission()
            elif permission_type == PermissionType.CAMERA:
                result = await self.macos_handler.check_camera_permission()
            elif permission_type == PermissionType.NETWORK:
                result = await self.macos_handler.check_network_permission()
            elif permission_type == PermissionType.NOTIFICATIONS:
                result = await self.macos_handler.check_notifications_permission()
            else:
                result = PermissionResult(
                    success=False,
                    permission=permission_type,
                    status=PermissionStatus.ERROR,
                    message=f"Unknown permission type: {permission_type}"
                )
            
            # Обновляем состояние
            if result.success:
                await self._update_permission_status(permission_type, result.status)
            
            logger.info(f"✅ Результат проверки {permission_type.value}: {result.status.value}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка проверки разрешения {permission_type.value}: {e}")
            return PermissionResult(
                success=False,
                permission=permission_type,
                status=PermissionStatus.ERROR,
                message=f"Error checking permission: {e}",
                error=e
            )
    
    async def check_all_permissions(self) -> Dict[PermissionType, PermissionResult]:
        """Проверить все разрешения"""
        logger.info("🔍 Проверка всех разрешений")
        
        results = {}
        tasks = []
        
        # Создаем задачи для параллельной проверки
        for perm_type in PermissionType:
            task = asyncio.create_task(self.check_permission(perm_type))
            tasks.append((perm_type, task))
        
        # Ждем завершения всех задач
        for perm_type, task in tasks:
            try:
                result = await task
                results[perm_type] = result
            except Exception as e:
                logger.error(f"❌ Ошибка проверки {perm_type.value}: {e}")
                results[perm_type] = PermissionResult(
                    success=False,
                    permission=perm_type,
                    status=PermissionStatus.ERROR,
                    message=f"Error: {e}",
                    error=e
                )
        
        logger.info("✅ Проверка всех разрешений завершена")
        return results
    
    async def request_permission(self, permission_type: PermissionType) -> PermissionResult:
        """Запросить разрешение"""
        try:
            logger.info(f"📝 Запрос разрешения: {permission_type.value}")
            
            # Сначала проверяем текущий статус
            current_result = await self.check_permission(permission_type)
            
            if current_result.status == PermissionStatus.GRANTED:
                logger.info(f"✅ Разрешение {permission_type.value} уже предоставлено")
                return current_result
            
            # Если разрешение отклонено, показываем инструкции
            if current_result.status == PermissionStatus.DENIED:
                await self._show_permission_instructions(permission_type)
                return current_result
            
            # Если разрешение не определено, показываем диалог
            if current_result.status == PermissionStatus.NOT_DETERMINED:
                await self._show_permission_dialog(permission_type)
                
                # Ждем немного и проверяем снова
                await asyncio.sleep(2)
                return await self.check_permission(permission_type)
            
            return current_result
            
        except Exception as e:
            logger.error(f"❌ Ошибка запроса разрешения {permission_type.value}: {e}")
            return PermissionResult(
                success=False,
                permission=permission_type,
                status=PermissionStatus.ERROR,
                message=f"Error requesting permission: {e}",
                error=e
            )
    
    async def request_required_permissions(self) -> Dict[PermissionType, PermissionResult]:
        """Запросить обязательные разрешения"""
        logger.info("📝 Запрос обязательных разрешений")
        
        results = {}
        required_permissions = self.config.required_permissions
        
        for perm_type in required_permissions:
            result = await self.request_permission(perm_type)
            results[perm_type] = result
            
            # Если разрешение критично и не предоставлено, показываем инструкции
            if result.status != PermissionStatus.GRANTED:
                await self._show_permission_instructions(perm_type)
        
        return results
    
    async def _update_permission_status(self, permission_type: PermissionType, new_status: PermissionStatus):
        """Обновить статус разрешения"""
        try:
            current_info = self.state.get_permission(permission_type)
            if not current_info:
                return
            
            old_status = current_info.status
            
            # Обновляем статус
            current_info.status = new_status
            current_info.last_checked = time.time()
            
            # Создаем событие
            event = PermissionEvent(
                event_type="status_changed",
                permission=permission_type,
                status=new_status,
                message=f"Status changed from {old_status.value} to {new_status.value}",
                timestamp=time.time()
            )
            
            # Уведомляем callbacks
            await self.state.notify_callbacks(event)
            
            logger.info(f"🔄 Статус {permission_type.value}: {old_status.value} → {new_status.value}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка обновления статуса {permission_type.value}: {e}")
    
    async def _show_permission_instructions(self, permission_type: PermissionType):
        """Показать инструкции для разрешения"""
        try:
            info = self.state.get_permission(permission_type)
            if not info:
                return
            
            instructions = self.macos_handler.get_permission_instructions(permission_type)
            
            print(f"\n{'='*60}")
            print(f"🔐 РАЗРЕШЕНИЕ: {permission_type.value.upper()}")
            print(f"{'='*60}")
            print(instructions)
            print(f"{'='*60}\n")
            
            # НЕ открываем настройки автоматически - пользователь должен сделать это вручную
            # if self.config.auto_open_preferences:
            #     await self.macos_handler.open_privacy_preferences(permission_type)
            
        except Exception as e:
            logger.error(f"❌ Ошибка показа инструкций {permission_type.value}: {e}")
    
    async def _show_permission_dialog(self, permission_type: PermissionType):
        """Показать диалог запроса разрешения"""
        try:
            # Для macOS мы не можем программно показать диалог
            # Пользователь должен предоставить разрешение в настройках
            await self._show_permission_instructions(permission_type)
            
        except Exception as e:
            logger.error(f"❌ Ошибка показа диалога {permission_type.value}: {e}")
    
    async def start_monitoring(self):
        """Начать мониторинг разрешений"""
        if self.is_monitoring:
            logger.warning("Мониторинг уже запущен")
            return
        
        if not self.is_initialized:
            logger.error("PermissionManager не инициализирован")
            return
        
        logger.info("🔄 Запуск мониторинга разрешений")
        self.is_monitoring = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
    
    async def stop_monitoring(self):
        """Остановить мониторинг разрешений"""
        if not self.is_monitoring:
            return
        
        logger.info("⏹️ Остановка мониторинга разрешений")
        self.is_monitoring = False
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        self._monitoring_task = None
    
    async def _monitoring_loop(self):
        """Цикл мониторинга"""
        try:
            while self.is_monitoring:
                # Проверяем все разрешения
                await self.check_all_permissions()
                
                # Ждем следующую проверку
                await asyncio.sleep(self.config.check_interval)
                
        except asyncio.CancelledError:
            logger.info("Мониторинг разрешений остановлен")
        except Exception as e:
            logger.error(f"❌ Ошибка мониторинга разрешений: {e}")
    
    def add_callback(self, callback: Callable[[PermissionEvent], None]):
        """Добавить callback для событий"""
        self.state.add_callback(callback)
    
    def get_permission_status(self, permission_type: PermissionType) -> Optional[PermissionStatus]:
        """Получить статус разрешения"""
        info = self.state.get_permission(permission_type)
        return info.status if info else None
    
    def get_all_permissions_status(self) -> Dict[PermissionType, PermissionStatus]:
        """Получить статус всех разрешений"""
        return {
            perm_type: info.status 
            for perm_type, info in self.state.get_all_permissions().items()
        }
    
    def are_required_permissions_granted(self) -> bool:
        """Проверить, предоставлены ли обязательные разрешения"""
        return self.state.get_required_permissions_status()
    
    async def cleanup(self):
        """Очистка ресурсов"""
        try:
            await self.stop_monitoring()
            self.is_initialized = False
            logger.info("✅ PermissionManager очищен")
        except Exception as e:
            logger.error(f"❌ Ошибка очистки PermissionManager: {e}")










