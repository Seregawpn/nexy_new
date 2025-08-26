#!/usr/bin/env python3
"""
Тест для проверки локального запуска HTTP и gRPC серверов
"""

import asyncio
import aiohttp
import time

async def test_http_server():
    """Тестируем HTTP сервер на порту 80"""
    print("🧪 Тестируем HTTP сервер...")
    
    # Ждем запуска сервера
    await asyncio.sleep(2)
    
    try:
        async with aiohttp.ClientSession() as session:
            # Тест health endpoint
            async with session.get('http://localhost:80/health') as response:
                if response.status == 200:
                    text = await response.text()
                    print(f"✅ Health check: {text}")
                else:
                    print(f"❌ Health check failed: {response.status}")
            
            # Тест root endpoint
            async with session.get('http://localhost:80/') as response:
                if response.status == 200:
                    text = await response.text()
                    print(f"✅ Root endpoint: {text}")
                else:
                    print(f"❌ Root endpoint failed: {response.status}")
                    
            # Тест status endpoint
            async with session.get('http://localhost:80/status') as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Status endpoint: {data}")
                else:
                    print(f"❌ Status endpoint failed: {response.status}")
                    
    except Exception as e:
        print(f"❌ HTTP тест не прошел: {e}")

async def main():
    """Основная функция тестирования"""
    print("🚀 Запуск тестов...")
    
    # Тестируем HTTP сервер
    await test_http_server()
    
    print("✅ Тесты завершены!")

if __name__ == "__main__":
    asyncio.run(main())
