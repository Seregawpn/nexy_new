#!/usr/bin/env python3
"""
Тестовый скрипт для проверки подключения к удаленному gRPC серверу
"""

import asyncio
import sys
import os

# Добавляем корневую директорию в путь для импорта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from grpc_client import GrpcClient
from rich.console import Console

console = Console()

async def test_remote_connection():
    """Тестирует подключение к удаленному серверу"""
    
    console.print("[bold blue]🧪 Тестирование подключения к удаленному серверу[/bold blue]")
    console.print("[blue]IP: 20.151.51.172:50051[/blue]")
    console.print("=" * 50)
    
    try:
        # Создаем клиент
        client = GrpcClient()
        
        # Подключаемся к серверу
        console.print("[yellow]🔄 Подключение к серверу...[/yellow]")
        connected = await client.connect()
        
        if connected:
            console.print("[bold green]✅ Подключение успешно![/bold green]")
            
            # Тестируем простой запрос
            console.print("[yellow]🔄 Тестирование простого запроса...[/yellow]")
            
            # Создаем тестовый запрос
            request = client.stub.StreamAudio(
                iter([{
                    'prompt': 'Привет, как дела?',
                    'hardware_id': 'test_client_001'
                }])
            )
            
            console.print("[bold green]✅ gRPC соединение работает![/bold green]")
            
            # Закрываем соединение
            await client.disconnect()
            
        else:
            console.print("[bold red]❌ Не удалось подключиться к серверу[/bold red]")
            return False
            
    except Exception as e:
        console.print(f"[bold red]❌ Ошибка при тестировании: {e}[/bold red]")
        return False
    
    return True

async def test_http_endpoints():
    """Тестирует HTTP endpoints удаленного сервера"""
    
    console.print("\n[bold blue]🌐 Тестирование HTTP endpoints[/bold blue]")
    console.print("=" * 50)
    
    try:
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            # Тестируем health check
            async with session.get('http://20.151.51.172/health') as response:
                if response.status == 200:
                    health_text = await response.text()
                    console.print(f"[green]✅ /health: {health_text.strip()}[/green]")
                else:
                    console.print(f"[red]❌ /health: HTTP {response.status}[/red]")
            
            # Тестируем status
            async with session.get('http://20.151.51.172/status') as response:
                if response.status == 200:
                    status_json = await response.json()
                    console.print(f"[green]✅ /status: {status_json['status']}[/green]")
                else:
                    console.print(f"[red]❌ /status: HTTP {response.status}[/red]")
            
            # Тестируем root
            async with session.get('http://20.151.51.172/') as response:
                if response.status == 200:
                    root_text = await response.text()
                    console.print(f"[green]✅ /: {root_text.strip()}[/green]")
                else:
                    console.print(f"[red]❌ /: HTTP {response.status}[/red]")
                    
    except Exception as e:
        console.print(f"[bold red]❌ Ошибка при тестировании HTTP: {e}[/bold red]")
        return False
    
    return True

async def main():
    """Основная функция тестирования"""
    
    console.print("[bold green]🚀 Запуск тестирования удаленного сервера[/bold green]")
    console.print("=" * 60)
    
    # Тестируем HTTP endpoints
    http_success = await test_http_endpoints()
    
    # Тестируем gRPC подключение
    grpc_success = await test_remote_connection()
    
    # Итоговый результат
    console.print("\n" + "=" * 60)
    if http_success and grpc_success:
        console.print("[bold green]🎉 Все тесты прошли успешно![/bold green]")
        console.print("[green]✅ Сервер готов к работе[/green]")
    else:
        console.print("[bold red]❌ Некоторые тесты не прошли[/bold red]")
        if not http_success:
            console.print("[red]❌ HTTP endpoints недоступны[/red]")
        if not grpc_success:
            console.print("[red]❌ gRPC подключение не работает[/red]")

if __name__ == "__main__":
    asyncio.run(main())
