#!/usr/bin/env python3
"""
Сервер обновлений для системы автообновлений Sparkle
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from aiohttp import web

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class UpdateServer:
    def __init__(self, updates_dir=None, port=8081):
        # Определяем абсолютный путь к директории updates
        if updates_dir is None:
            # Получаем путь к директории, где находится этот файл
            current_file_dir = Path(__file__).parent
            self.updates_dir = current_file_dir / "updates"
        else:
            self.updates_dir = Path(updates_dir)
        
        self.port = port
        self.app = None
        self.runner = None
        self.site = None
        
        # Создаем директории
        self.downloads_dir = self.updates_dir / "downloads"
        self.keys_dir = self.updates_dir / "keys"
        self.downloads_dir.mkdir(parents=True, exist_ok=True)
        self.keys_dir.mkdir(parents=True, exist_ok=True)
        
        # Путь к AppCast XML файлу
        self.appcast_file = self.updates_dir / "appcast.xml"
        
    async def create_app(self):
        """Создание aiohttp приложения"""
        app = web.Application()
        
        # CORS middleware
        @web.middleware
        async def cors_middleware(request, handler):
            response = await handler(request)
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            return response
        
        app.middlewares.append(cors_middleware)
        
        # Routes
        app.router.add_get('/appcast.xml', self.appcast_handler)
        app.router.add_get('/downloads/{filename}', self.download_handler)
        app.router.add_get('/health', self.health_handler)
        app.router.add_get('/api/versions', self.versions_handler)
        app.router.add_get('/', self.index_handler)
        
        return app
    
    async def appcast_handler(self, request):
        """Обработчик AppCast XML - читает из файла"""
        try:
            if self.appcast_file.exists():
                # Читаем XML из файла
                with open(self.appcast_file, 'r', encoding='utf-8') as f:
                    appcast_xml = f.read()
                
                logger.info("📄 AppCast XML загружен из файла")
                return web.Response(
                    text=appcast_xml,
                    content_type='application/xml',
                    headers={
                        'Cache-Control': 'no-cache, no-store, must-revalidate',
                        'Pragma': 'no-cache',
                        'Expires': '0'
                    }
                )
            else:
                logger.error("❌ AppCast XML файл не найден")
                return web.Response(
                    text="AppCast XML file not found",
                    status=404
                )
        except Exception as e:
            logger.error(f"❌ Ошибка чтения AppCast XML: {e}")
            return web.Response(
                text="Error reading AppCast XML",
                status=500
            )
    
    async def download_handler(self, request):
        """Обработчик загрузки PKG файлов"""
        filename = request.match_info['filename']
        pkg_path = self.downloads_dir / filename
        
        if pkg_path.exists():
            logger.info(f"📥 Загрузка PKG файла: {filename}")
            return web.FileResponse(
                pkg_path,
                headers={
                    'Content-Type': 'application/octet-stream',
                    'Content-Disposition': f'attachment; filename="{filename}"'
                }
            )
        else:
            logger.warning(f"⚠️ PKG файл не найден: {filename}")
            return web.Response(
                text="File not found",
                status=404
            )
    
    async def health_handler(self, request):
        """Проверка здоровья сервера"""
        return web.json_response({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "appcast_file": str(self.appcast_file),
            "appcast_exists": self.appcast_file.exists(),
            "downloads_available": len(list(self.downloads_dir.glob("*.pkg")))
        })
    
    async def versions_handler(self, request):
        """API для получения версий"""
        return web.json_response({
            "current": "1.70.0",
            "latest": "1.71.0",
            "available": ["1.70.0", "1.71.0", "1.72.0", "1.73.0"]
        })
    
    async def index_handler(self, request):
        """Главная страница"""
        html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Nexy Update Server</title>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .endpoint {{ background: #f5f5f5; padding: 10px; margin: 10px 0; border-radius: 5px; }}
                .info {{ background: #e8f4fd; padding: 10px; margin: 10px 0; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <h1>🔄 Nexy Update Server</h1>
            <p>Сервер обновлений для системы автообновлений Sparkle</p>
            
            <div class="info">
                <h3>📊 Информация о сервере</h3>
                <p><strong>Порт:</strong> {self.port}</p>
                <p><strong>Статус:</strong> Работает</p>
                <p><strong>AppCast файл:</strong> {self.appcast_file}</p>
                <p><strong>AppCast существует:</strong> {'Да' if self.appcast_file.exists() else 'Нет'}</p>
            </div>
            
            <h2>📡 Endpoints</h2>
            <div class="endpoint">
                <strong>AppCast XML:</strong> <a href="/appcast.xml">http://localhost:{self.port}/appcast.xml</a>
            </div>
            <div class="endpoint">
                <strong>Downloads:</strong> <a href="/downloads/">http://localhost:{self.port}/downloads/</a>
            </div>
            <div class="endpoint">
                <strong>Health Check:</strong> <a href="/health">http://localhost:{self.port}/health</a>
            </div>
            <div class="endpoint">
                <strong>Versions API:</strong> <a href="/api/versions">http://localhost:{self.port}/api/versions</a>
            </div>
        </body>
        </html>
        '''
        
        return web.Response(text=html, content_type='text/html')
    
    async def start_server(self):
        """Запуск сервера обновлений"""
        self.app = await self.create_app()
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        
        self.site = web.TCPSite(self.runner, '0.0.0.0', self.port)
        await self.site.start()
        
        logger.info("=" * 60)
        logger.info("🔄 СЕРВЕР ОБНОВЛЕНИЙ ЗАПУЩЕН")
        logger.info("=" * 60)
        logger.info(f"🌐 URL: http://localhost:{self.port}")
        logger.info(f"📡 AppCast: http://localhost:{self.port}/appcast.xml")
        logger.info(f"📁 Downloads: http://localhost:{self.port}/downloads/")
        logger.info(f"💚 Health: http://localhost:{self.port}/health")
        logger.info("=" * 60)
        logger.info("🎯 Готов для обслуживания обновлений!")
        logger.info("=" * 60)
        
    async def stop_server(self):
        """Остановка сервера обновлений"""
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
        logger.info("✅ Сервер обновлений остановлен")

# Глобальный экземпляр сервера обновлений
update_server = None

async def start_update_server():
    """Запуск сервера обновлений"""
    global update_server
    update_server = UpdateServer()
    await update_server.start_server()

async def stop_update_server():
    """Остановка сервера обновлений"""
    global update_server
    if update_server:
        await update_server.stop_server()

if __name__ == "__main__":
    async def main():
        server = UpdateServer()
        try:
            await server.start_server()
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("🛑 Получен сигнал остановки...")
        finally:
            await server.stop_server()
    
    asyncio.run(main())
