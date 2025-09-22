"""
Nexy AI Assistant - Главный файл приложения
Только точка входа и инициализация SimpleModuleCoordinator
"""

import asyncio
import logging
import sys
from pathlib import Path

# Добавляем путь к модулям
sys.path.append(str(Path(__file__).parent))

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Главная функция"""
    try:
        # Импортируем SimpleModuleCoordinator
        from integration.core.simple_module_coordinator import SimpleModuleCoordinator
        
        # Создаем координатор
        coordinator = SimpleModuleCoordinator()
        
        # Запускаем (run() сам вызовет initialize() и проверку дублирования)
        await coordinator.run()                               
        
    except Exception as e:
        print(f"💥 Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Создаем новый event loop для главного потока
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("\n⏹️ Приложение прервано пользователем")
    finally:
        loop.close()



                                                                                                 