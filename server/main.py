import asyncio
import logging
from aiohttp import web
from grpc_server import serve

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
        "endpoints": {
            "health": "/health",
            "status": "/status",
            "grpc": "port 50051"
        }
    })

async def main():
    """Запуск HTTP и gRPC серверов одновременно"""
    logger.info("🚀 Запуск Voice Assistant Server...")
    
    # HTTP сервер для health checks (порт 80)
    app = web.Application()
    app.router.add_get('/health', health_handler)
    app.router.add_get('/', root_handler)
    app.router.add_get('/status', status_handler)
    
    # Запускаем HTTP сервер на порту 80
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 80)
    await site.start()
    
    logger.info("✅ HTTP сервер запущен на порту 80")
    logger.info("   - Health check: http://localhost:80/health")
    logger.info("   - Status: http://localhost:80/status")
    logger.info("   - Root: http://localhost:80/")
    
    # Запускаем gRPC сервер на порту 50051
    logger.info("🚀 Запускаю gRPC сервер на порту 50051...")
    await serve()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки, завершаю работу...")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        raise
