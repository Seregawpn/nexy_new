"""
Демонстрация Tray Controller Module
Простой тест для проверки работоспособности
"""

import asyncio
import logging
import sys
import os

# Пути уже добавлены в main.py - не дублируем

from core.tray_controller import TrayController
from core.tray_types import TrayStatus

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def demo_tray_controller():
    """Демонстрация работы Tray Controller"""
    try:
        print("\n" + "="*60)
        print("NEXY AI - TRAY CONTROLLER DEMO")
        print("="*60)
        print("This demo shows the Tray Controller functionality")
        print("Look for the 'Nexy AI' icon in your menu bar")
        print("="*60 + "\n")
        
        # Создаем контроллер
        tray_controller = TrayController()
        
        # Инициализация
        logger.info("🔧 Initializing Tray Controller...")
        success = await tray_controller.initialize()
        if not success:
            logger.error("❌ Failed to initialize Tray Controller")
            return
        
        # Запуск
        logger.info("🚀 Starting Tray Controller...")
        success = await tray_controller.start()
        if not success:
            logger.error("❌ Failed to start Tray Controller")
            return
        
        # Получаем приложение для запуска в главном потоке
        app = tray_controller.get_app()
        if not app:
            logger.error("❌ Failed to get tray app")
            return
        
        print("✅ Tray Controller started successfully!")
        print("📱 Look for 'Nexy AI' icon in menu bar")
        print("🔄 Status will cycle through: Sleeping → Listening → Processing")
        print("⏹️  Press Ctrl+C to stop\n")
        
        # Демонстрация смены статусов
        async def status_demo():
            statuses = [
                (TrayStatus.SLEEPING, "Sleeping (Gray)"),
                (TrayStatus.LISTENING, "Listening (Blue)"),
                (TrayStatus.PROCESSING, "Processing (Orange)")
            ]
            
            for status, description in statuses:
                logger.info(f"🔄 Changing status to: {description}")
                await tray_controller.update_status(status)
                await asyncio.sleep(2)  # Пауза между сменами
        
        # Запускаем демонстрацию в фоне
        demo_task = asyncio.create_task(status_demo())
        
        # Запускаем приложение (блокирующий вызов)
        app.run()
        
    except KeyboardInterrupt:
        logger.info("⏹️ Stopping demo...")
    except Exception as e:
        logger.error(f"❌ Error in demo: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Очистка
        try:
            if 'tray_controller' in locals():
                await tray_controller.stop()
                logger.info("✅ Tray Controller stopped")
        except:
            pass

if __name__ == "__main__":
    asyncio.run(demo_tray_controller())










