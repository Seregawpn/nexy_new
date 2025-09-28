import asyncio
import logging
from aiohttp import web
from grpc_server import run_server as serve
from dotenv import load_dotenv

# Загружаем config.env
load_dotenv('config.env')

# Импорт системы обновлений
try:
    from update_server import start_update_server, stop_update_server  # type: ignore[reportMissingImports]
    UPDATE_SERVER_AVAILABLE = True
    print("✅ Update Server импортирован успешно")
except ImportError as e:
    print(f"⚠️ Update Server не найден: {e}")
    UPDATE_SERVER_AVAILABLE = False

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
 
async def health_handler(request):
    """Health check для Container Apps"""
    return web.Response(text="OK", status=200)

async def root_handler(request):
    """Корневой endpoint"""
    return web.Response(text="Voice Assistant Server is running!", status=200)

async def status_handler(request):
    """Статус сервера"""
    return web.json_response({
        "status": "running",
        "service": "voice-assistant",
        "version": "1.0.0",
        "update_server": "enabled" if UPDATE_SERVER_AVAILABLE else "disabled",
        "endpoints": {
            "health": "/health",
            "status": "/status",
            "grpc": "port 50051",
            "updates": "port 8081" if UPDATE_SERVER_AVAILABLE else "disabled"
        }
    })

async def main():
    """Запуск HTTP, gRPC и Update серверов одновременно"""
    logger.info("🚀 Запуск Voice Assistant Server с системой обновлений...")                               
    
    # HTTP сервер для health checks (порт 8080)
    app = web.Application()
    app.router.add_get('/health', health_handler)
    app.router.add_get('/', root_handler)
    app.router.add_get('/status', status_handler)
    
    # Запускаем HTTP сервер на порту 8080
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    
    logger.info("✅ HTTP сервер запущен на порту 8080")
    logger.info("   - Health check: http://localhost:8080/health")
    logger.info("   - Status: http://localhost:8080/status")
    logger.info("   - Root: http://localhost:8080/")
    
    # Запускаем сервер обновлений на порту 8081
    if UPDATE_SERVER_AVAILABLE:
        logger.info("🔄 Запуск сервера обновлений на порту 8081...")
        await start_update_server()
        logger.info("✅ Сервер обновлений запущен")
        logger.info("   - AppCast: http://localhost:8081/appcast.xml")
        logger.info("   - Downloads: http://localhost:8081/downloads/")
        logger.info("   - Health: http://localhost:8081/health")
    else:
        logger.warning("⚠️ Сервер обновлений недоступен")
    
    # Запускаем gRPC сервер на порту 50051
    logger.info("🚀 Запускаю gRPC сервер на порту 50051...")
    await serve()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки, завершаю работу...")
        if UPDATE_SERVER_AVAILABLE:
            asyncio.run(stop_update_server())
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        if UPDATE_SERVER_AVAILABLE:
            asyncio.run(stop_update_server())
        raise
