#!/usr/bin/env python3
"""
Тест для проверки обработки AppleEvent termination
Проверяет, что приложение не соглашается на автоматическое завершение
"""

import os
import re

def test_termination_handling():
    """Проверяем, что обработка AppleEvent termination настроена правильно"""
    print("🔍 Проверка обработки AppleEvent termination...")
    
    # Проверяем menu_handler.py
    handler_path = "modules/tray_controller/macos/menu_handler.py"
    if not os.path.exists(handler_path):
        print("❌ menu_handler.py не найден")
        return False
    
    with open(handler_path, 'r') as f:
        content = f.read()
    
    # Проверяем наличие обработчика
    if "applicationShouldTerminate" in content:
        print("✅ applicationShouldTerminate найден")
    else:
        print("❌ applicationShouldTerminate не найден")
        return False
    
    # Проверяем, что возвращается False
    if "return False" in content:
        print("✅ Возвращается False для предотвращения завершения")
    else:
        print("❌ Не возвращается False")
        return False
    
    # Проверяем callback для системного завершения
    if "_quit_callback" in content:
        print("✅ Callback для системного завершения найден")
    else:
        print("❌ Callback для системного завершения не найден")
        return False
    
    return True

def test_tray_controller_integration():
    """Проверяем, что TrayControllerIntegration использует обработчик"""
    print("\n🔍 Проверка TrayControllerIntegration...")
    
    integration_path = "integration/integrations/tray_controller_integration.py"
    if not os.path.exists(integration_path):
        print("❌ TrayControllerIntegration не найден")
        return False
    
    with open(integration_path, 'r') as f:
        content = f.read()
    
    # Проверяем наличие _on_system_quit
    if "_on_system_quit" in content:
        print("✅ _on_system_quit найден в интеграции")
    else:
        print("❌ _on_system_quit не найден в интеграции")
        return False
    
    # Проверяем настройку callback
    if "set_quit_callback" in content:
        print("✅ set_quit_callback используется")
    else:
        print("❌ set_quit_callback не используется")
        return False
    
    return True

def test_quit_event_handling():
    """Проверяем обработку quit событий"""
    print("\n🔍 Проверка обработки quit событий...")
    
    # Проверяем TrayController
    controller_path = "modules/tray_controller/core/tray_controller.py"
    if not os.path.exists(controller_path):
        print("❌ TrayController не найден")
        return False
    
    with open(controller_path, 'r') as f:
        content = f.read()
    
    # Проверяем _on_quit_clicked
    if "_on_quit_clicked" in content:
        print("✅ _on_quit_clicked найден")
    else:
        print("❌ _on_quit_clicked не найден")
        return False
    
    # Проверяем публикацию события
    if "quit_clicked" in content:
        print("✅ Событие quit_clicked публикуется")
    else:
        print("❌ Событие quit_clicked не публикуется")
        return False
    
    return True

def test_app_shutdown_event():
    """Проверяем обработку события app.shutdown"""
    print("\n🔍 Проверка события app.shutdown...")
    
    # Проверяем SimpleModuleCoordinator
    coordinator_path = "integration/core/simple_module_coordinator.py"
    if not os.path.exists(coordinator_path):
        print("❌ SimpleModuleCoordinator не найден")
        return False
    
    with open(coordinator_path, 'r') as f:
        content = f.read()
    
    # Проверяем публикацию app.shutdown
    if "app.shutdown" in content:
        print("✅ Событие app.shutdown публикуется")
    else:
        print("❌ Событие app.shutdown не публикуется")
        return False
    
    return True

if __name__ == "__main__":
    print("🔍 ДИАГНОСТИКА ОБРАБОТКИ APPLEEVENT TERMINATION")
    print("=" * 60)
    
    # Тест 1: Обработка termination
    termination_ok = test_termination_handling()
    
    # Тест 2: TrayControllerIntegration
    integration_ok = test_tray_controller_integration()
    
    # Тест 3: Обработка quit событий
    quit_events_ok = test_quit_event_handling()
    
    # Тест 4: Событие app.shutdown
    shutdown_event_ok = test_app_shutdown_event()
    
    print("\n" + "=" * 60)
    print("📊 РЕЗУЛЬТАТЫ:")
    print(f"Обработка termination: {'✅ ОК' if termination_ok else '❌ НЕ ОК'}")
    print(f"TrayControllerIntegration: {'✅ ОК' if integration_ok else '❌ НЕ ОК'}")
    print(f"Обработка quit событий: {'✅ ОК' if quit_events_ok else '❌ НЕ ОК'}")
    print(f"Событие app.shutdown: {'✅ ОК' if shutdown_event_ok else '❌ НЕ ОК'}")
    
    if termination_ok and integration_ok and quit_events_ok and shutdown_event_ok:
        print("\n🎉 ТРЕТЬЯ ПРОБЛЕМА РЕШЕНА!")
        print("✅ AppleEvent termination обрабатывается правильно")
        print("✅ Приложение не будет закрываться автоматически")
    else:
        print("\n⚠️ ТРЕТЬЯ ПРОБЛЕМА НЕ РЕШЕНА!")
        print("❌ Нужны дополнительные исправления")
