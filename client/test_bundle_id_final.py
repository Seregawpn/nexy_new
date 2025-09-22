#!/usr/bin/env python3
"""
Финальный тест Bundle ID
Проверяет, что везде используется правильный Bundle ID com.nexy.assistant
"""

import os
import re

def test_bundle_id_consistency():
    """Проверяем консистентность Bundle ID во всех файлах"""
    print("🔍 Финальная проверка Bundle ID...")
    
    # Правильный Bundle ID
    correct_bundle_id = "com.nexy.assistant"
    
    # Файлы для проверки
    critical_files = [
        "packaging/Nexy.spec",
        "config/unified_config.yaml", 
        "packaging/LaunchAgent/com.nexy.assistant.plist",
        "integration/integrations/autostart_manager_integration.py",
        "test_integrations_simple.py"
    ]
    
    all_correct = True
    
    for file_path in critical_files:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                content = f.read()
                
            # Ищем все Bundle ID в файле
            bundle_ids = re.findall(r'com\.nexy\.[a-zA-Z0-9._-]+', content)
            
            if bundle_ids:
                # Проверяем, что все Bundle ID правильные или являются расширениями
                wrong_ids = []
                for bid in bundle_ids:
                    # Разрешаем основные Bundle ID и их расширения
                    if (bid == correct_bundle_id or 
                        bid.startswith(correct_bundle_id + '.') or
                        bid.endswith('.plist') or
                        bid.endswith('.url')):
                        continue
                    else:
                        wrong_ids.append(bid)
                
                if wrong_ids:
                    print(f"❌ {file_path}: найдены неправильные Bundle ID: {wrong_ids}")
                    all_correct = False
                else:
                    print(f"✅ {file_path}: все Bundle ID правильные")
            else:
                print(f"⚠️ {file_path}: Bundle ID не найден")
        else:
            print(f"❌ {file_path}: файл не найден")
            all_correct = False
    
    return all_correct

def test_spec_file_bundle_id():
    """Проверяем Bundle ID в spec файле"""
    print("\n🔍 Проверка spec файла...")
    
    spec_path = "packaging/Nexy.spec"
    if not os.path.exists(spec_path):
        print("❌ Spec файл не найден")
        return False
    
    with open(spec_path, 'r') as f:
        content = f.read()
    
    # Проверяем bundle_identifier
    if "bundle_identifier='com.nexy.assistant'" in content:
        print("✅ bundle_identifier правильный")
    else:
        print("❌ bundle_identifier неправильный")
        return False
    
    # Проверяем CFBundleIdentifier
    if "'CFBundleIdentifier': 'com.nexy.assistant'" in content:
        print("✅ CFBundleIdentifier правильный")
    else:
        print("❌ CFBundleIdentifier неправильный")
        return False
    
    return True

def test_config_bundle_id():
    """Проверяем Bundle ID в конфигурации"""
    print("\n🔍 Проверка конфигурации...")
    
    config_path = "config/unified_config.yaml"
    if not os.path.exists(config_path):
        print("❌ Конфигурация не найдена")
        return False
    
    with open(config_path, 'r') as f:
        content = f.read()
    
    # Проверяем все bundle_id
    bundle_id_matches = re.findall(r'bundle_id:\s*["\']?com\.nexy\.[a-zA-Z0-9._-]+["\']?', content)
    
    if bundle_id_matches:
        wrong_ids = [match for match in bundle_id_matches if 'com.nexy.assistant' not in match]
        
        if wrong_ids:
            print(f"❌ Найдены неправильные bundle_id: {wrong_ids}")
            return False
        else:
            print(f"✅ Все bundle_id правильные: {bundle_id_matches}")
            return True
    else:
        print("❌ bundle_id не найден в конфигурации")
        return False

def test_launch_agent_bundle_id():
    """Проверяем Bundle ID в LaunchAgent"""
    print("\n🔍 Проверка LaunchAgent...")
    
    plist_path = "packaging/LaunchAgent/com.nexy.assistant.plist"
    if not os.path.exists(plist_path):
        print("❌ LaunchAgent не найден")
        return False
    
    with open(plist_path, 'r') as f:
        content = f.read()
    
    if "<string>com.nexy.assistant</string>" in content:
        print("✅ LaunchAgent содержит правильный Bundle ID")
        return True
    else:
        print("❌ LaunchAgent содержит неправильный Bundle ID")
        return False

if __name__ == "__main__":
    print("🎯 ФИНАЛЬНАЯ ПРОВЕРКА BUNDLE ID")
    print("=" * 50)
    
    # Тест 1: Общая консистентность
    consistency_ok = test_bundle_id_consistency()
    
    # Тест 2: Spec файл
    spec_ok = test_spec_file_bundle_id()
    
    # Тест 3: Конфигурация
    config_ok = test_config_bundle_id()
    
    # Тест 4: LaunchAgent
    launch_agent_ok = test_launch_agent_bundle_id()
    
    print("\n" + "=" * 50)
    print("📊 РЕЗУЛЬТАТЫ:")
    print(f"Консистентность: {'✅ ОК' if consistency_ok else '❌ НЕ ОК'}")
    print(f"Spec файл: {'✅ ОК' if spec_ok else '❌ НЕ ОК'}")
    print(f"Конфигурация: {'✅ ОК' if config_ok else '❌ НЕ ОК'}")
    print(f"LaunchAgent: {'✅ ОК' if launch_agent_ok else '❌ НЕ ОК'}")
    
    if consistency_ok and spec_ok and config_ok and launch_agent_ok:
        print("\n🎉 BUNDLE ID НАСТРОЕН ПРАВИЛЬНО!")
        print("✅ com.nexy.assistant используется везде")
        print("🚀 Можно собирать приложение")
    else:
        print("\n⚠️ BUNDLE ID НЕ НАСТРОЕН ПРАВИЛЬНО!")
        print("❌ Нужны исправления")
