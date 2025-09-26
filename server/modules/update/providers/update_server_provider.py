"""
Update Server Provider - HTTP сервер обновлений
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from aiohttp import web, web_request, web_response

logger = logging.getLogger(__name__)


class UpdateServerProvider:
    """Провайдер HTTP сервера обновлений"""
    
    def __init__(self, config, manifest_provider, artifact_provider, version_provider):
        self.config = config
        self.manifest_provider = manifest_provider
        self.artifact_provider = artifact_provider
        self.version_provider = version_provider
        
        self.app = None
        self.runner = None
        self.site = None
        self.is_running = False
    
    async def initialize(self) -> bool:
        """Инициализация провайдера"""
        try:
            logger.info("🔧 Инициализация UpdateServerProvider...")
            
            # Создаем aiohttp приложение
            self.app = await self.create_app()
            
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации UpdateServerProvider: {e}")
            return False
    
    async def create_app(self) -> web.Application:
        """Создание aiohttp приложения"""
        app = web.Application()
        
        # CORS middleware
        if self.config.cors_enabled:
            @web.middleware
            async def cors_middleware(request: web_request.Request, handler) -> web_response.Response:
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
        app.router.add_get('/api/manifests', self.manifests_handler)
        app.router.add_get('/api/artifacts', self.artifacts_handler)
        app.router.add_get('/', self.index_handler)
        
        return app
    
    async def appcast_handler(self, request: web_request.Request) -> web_response.Response:
        """Обработчик AppCast XML для Sparkle"""
        try:
            # Получаем последний манифест
            latest_manifest = self.manifest_provider.get_latest_manifest()
            
            if not latest_manifest:
                logger.warning("⚠️ Манифесты не найдены")
                return web.Response(
                    text="No manifests available",
                    status=404,
                    content_type='text/plain'
                )
            
            # Генерируем AppCast XML
            appcast_xml = self._generate_appcast_xml(latest_manifest)
            
            if self.config.log_requests:
                logger.info("📄 AppCast XML запрошен")
            
            return web.Response(
                text=appcast_xml,
                content_type='application/xml',
                headers={
                    'Cache-Control': self.config.cache_control,
                    'Pragma': 'no-cache',
                    'Expires': '0'
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка генерации AppCast XML: {e}")
            return web.Response(
                text="Error generating AppCast XML",
                status=500,
                content_type='text/plain'
            )
    
    async def download_handler(self, request: web_request.Request) -> web_response.Response:
        """Обработчик загрузки артефактов"""
        try:
            filename = request.match_info['filename']
            file_path = Path(self.config.downloads_dir) / filename
            
            if not file_path.exists():
                logger.warning(f"⚠️ Файл не найден: {filename}")
                return web.Response(
                    text="File not found",
                    status=404,
                    content_type='text/plain'
                )
            
            if self.config.log_downloads:
                logger.info(f"📥 Загрузка файла: {filename}")
            
            return web.FileResponse(
                file_path,
                headers={
                    'Content-Type': 'application/octet-stream',
                    'Content-Disposition': f'attachment; filename="{filename}"'
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки файла {filename}: {e}")
            return web.Response(
                text="Error downloading file",
                status=500,
                content_type='text/plain'
            )
    
    async def health_handler(self, request: web_request.Request) -> web_response.Response:
        """Проверка здоровья сервера"""
        try:
            latest_manifest = self.manifest_provider.get_latest_manifest()
            artifacts = self.artifact_provider.list_artifacts()
            
            health_data = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "version": "1.0.0",
                "latest_version": latest_manifest.get("version") if latest_manifest else None,
                "latest_build": latest_manifest.get("build") if latest_manifest else None,
                "artifacts_available": len(artifacts),
                "downloads_dir": self.config.downloads_dir,
                "manifests_dir": self.config.manifests_dir
            }
            
            return web.json_response(health_data)
            
        except Exception as e:
            logger.error(f"❌ Ошибка health check: {e}")
            return web.json_response({
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }, status=500)
    
    async def versions_handler(self, request: web_request.Request) -> web_response.Response:
        """API для получения информации о версиях"""
        try:
            manifests = self.manifest_provider.get_all_manifests()
            
            versions_data = {
                "current": self.version_provider.get_default_version(),
                "latest": manifests[0].get("version") if manifests else self.version_provider.get_default_version(),
                "available": [manifest.get("version") for manifest in manifests],
                "manifests": manifests
            }
            
            return web.json_response(versions_data)
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения версий: {e}")
            return web.json_response({
                "error": str(e)
            }, status=500)
    
    async def manifests_handler(self, request: web_request.Request) -> web_response.Response:
        """API для получения всех манифестов"""
        try:
            manifests = self.manifest_provider.get_all_manifests()
            return web.json_response(manifests)
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения манифестов: {e}")
            return web.json_response({
                "error": str(e)
            }, status=500)
    
    async def artifacts_handler(self, request: web_request.Request) -> web_response.Response:
        """API для получения всех артефактов"""
        try:
            artifacts = self.artifact_provider.list_artifacts()
            return web.json_response(artifacts)
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения артефактов: {e}")
            return web.json_response({
                "error": str(e)
            }, status=500)
    
    async def index_handler(self, request: web_request.Request) -> web_response.Response:
        """Главная страница сервера"""
        try:
            latest_manifest = self.manifest_provider.get_latest_manifest()
            artifacts = self.artifact_provider.list_artifacts()
            
            html = self._generate_index_html(latest_manifest, artifacts)
            
            return web.Response(
                text=html,
                content_type='text/html'
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка генерации главной страницы: {e}")
            return web.Response(
                text="Error generating index page",
                status=500,
                content_type='text/plain'
            )
    
    def _generate_appcast_xml(self, manifest: Dict[str, Any]) -> str:
        """Генерация AppCast XML для Sparkle"""
        artifact = manifest.get("artifact", {})
        
        appcast_xml = f'''<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0" xmlns:sparkle="http://www.andymatuschak.org/xml-namespaces/sparkle">
    <channel>
        <title>Nexy Updates</title>
        <description>Updates for Nexy AI Assistant</description>
        <language>en</language>
        <item>
            <title>Version {manifest.get("version", "Unknown")}</title>
            <description>Update to version {manifest.get("version", "Unknown")}</description>
            <pubDate>{datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")}</pubDate>
            <enclosure 
                url="{artifact.get("url", "")}"
                sparkle:version="{manifest.get("build", 0)}"
                sparkle:shortVersionString="{manifest.get("version", "1.0.0")}"
                length="{artifact.get("size", 0)}"
                type="application/octet-stream"
                sparkle:dsaSignature="{artifact.get("ed25519", "")}"
                sparkle:minimumSystemVersion="{artifact.get("min_os", "11.0")}"
            />
        </item>
    </channel>
</rss>'''
        
        return appcast_xml
    
    def _generate_index_html(self, latest_manifest: Optional[Dict[str, Any]], artifacts: list) -> str:
        """Генерация HTML главной страницы"""
        latest_version = latest_manifest.get("version") if latest_manifest else "Unknown"
        latest_build = latest_manifest.get("build") if latest_manifest else 0
        artifacts_count = len(artifacts)
        
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
        .status {{ background: #d4edda; padding: 10px; margin: 10px 0; border-radius: 5px; }}
    </style>
</head>
<body>
    <h1>🔄 Nexy Update Server</h1>
    <p>Сервер обновлений для системы автообновлений Sparkle</p>
    
    <div class="status">
        <h3>📊 Статус сервера</h3>
        <p><strong>Порт:</strong> {self.config.port}</p>
        <p><strong>Статус:</strong> Работает</p>
        <p><strong>Последняя версия:</strong> {latest_version} (build {latest_build})</p>
        <p><strong>Артефактов доступно:</strong> {artifacts_count}</p>
    </div>
    
    <div class="info">
        <h3>📁 Директории</h3>
        <p><strong>Downloads:</strong> {self.config.downloads_dir}</p>
        <p><strong>Manifests:</strong> {self.config.manifests_dir}</p>
        <p><strong>Keys:</strong> {self.config.keys_dir}</p>
    </div>
    
    <h2>📡 Endpoints</h2>
    <div class="endpoint">
        <strong>AppCast XML:</strong> <a href="/appcast.xml">http://localhost:{self.config.port}/appcast.xml</a>
    </div>
    <div class="endpoint">
        <strong>Downloads:</strong> <a href="/downloads/">http://localhost:{self.config.port}/downloads/</a>
    </div>
    <div class="endpoint">
        <strong>Health Check:</strong> <a href="/health">http://localhost:{self.config.port}/health</a>
    </div>
    <div class="endpoint">
        <strong>Versions API:</strong> <a href="/api/versions">http://localhost:{self.config.port}/api/versions</a>
    </div>
    <div class="endpoint">
        <strong>Manifests API:</strong> <a href="/api/manifests">http://localhost:{self.config.port}/api/manifests</a>
    </div>
    <div class="endpoint">
        <strong>Artifacts API:</strong> <a href="/api/artifacts">http://localhost:{self.config.port}/api/artifacts</a>
    </div>
</body>
</html>'''
        
        return html
    
    async def start_server(self) -> bool:
        """Запуск HTTP сервера"""
        try:
            if self.is_running:
                logger.warning("⚠️ Сервер уже запущен")
                return True
            
            if not self.app:
                logger.error("❌ Приложение не инициализировано")
                return False
            
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            
            self.site = web.TCPSite(self.runner, self.config.host, self.config.port)
            await self.site.start()
            
            self.is_running = True
            
            logger.info("=" * 60)
            logger.info("🔄 СЕРВЕР ОБНОВЛЕНИЙ ЗАПУЩЕН")
            logger.info("=" * 60)
            logger.info(f"🌐 URL: http://{self.config.host}:{self.config.port}")
            logger.info(f"📡 AppCast: http://{self.config.host}:{self.config.port}/appcast.xml")
            logger.info(f"📁 Downloads: http://{self.config.host}:{self.config.port}/downloads/")
            logger.info(f"💚 Health: http://{self.config.host}:{self.config.port}/health")
            logger.info("=" * 60)
            logger.info("🎯 Готов для обслуживания обновлений!")
            logger.info("=" * 60)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска сервера: {e}")
            return False
    
    async def stop_server(self) -> bool:
        """Остановка HTTP сервера"""
        try:
            if not self.is_running:
                logger.info("ℹ️ Сервер уже остановлен")
                return True
            
            if self.site:
                await self.site.stop()
            if self.runner:
                await self.runner.cleanup()
            
            self.is_running = False
            logger.info("✅ Сервер обновлений остановлен")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка остановки сервера: {e}")
            return False
    
    async def stop(self) -> bool:
        """Остановка провайдера"""
        try:
            logger.info("🛑 Остановка UpdateServerProvider...")
            await self.stop_server()
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка остановки UpdateServerProvider: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Получение статуса провайдера"""
        return {
            "status": "running" if self.is_running else "stopped",
            "provider": "update_server",
            "host": self.config.host,
            "port": self.config.port,
            "is_running": self.is_running,
            "endpoints": {
                "appcast": f"http://{self.config.host}:{self.config.port}/appcast.xml",
                "downloads": f"http://{self.config.host}:{self.config.port}/downloads/",
                "health": f"http://{self.config.host}:{self.config.port}/health",
                "api_versions": f"http://{self.config.host}:{self.config.port}/api/versions"
            }
        }
