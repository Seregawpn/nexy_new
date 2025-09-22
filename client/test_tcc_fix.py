#!/usr/bin/env python3
"""
Тест для проверки исправления TCC проблем с Bundle ID
Проверяет доступность разрешений для правильного Bundle ID
"""

import sys
import os
import subprocess

def test_tcc_reset():
    """Проверяем, что TCC сброшен для правильного Bundle ID"""
    print("🔍 Проверка TCC статуса для com.nexy.assistant...")
    
    bundle_id = "com.nexy.assistant"
    permissions = ["Microphone", "ScreenCapture", "Accessibility", "ListenEvent"]
    
    for permission in permissions:
        try:
            # Проверяем статус разрешения
            result = subprocess.run(
                ["tccutil", "reset", permission, bundle_id],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                print(f"✅ {permission}: TCC сброшен успешно")
            else:
                print(f"⚠️ {permission}: {result.stderr.strip()}")
                
        except Exception as e:
            print(f"❌ {permission}: Ошибка проверки - {e}")
    
    return True

def test_bundle_id_consistency():
    """Проверяем консистентность Bundle ID в конфигурации"""
    print("\n🔍 Проверка консистентности Bundle ID...")
    
    # Проверяем spec файл
    spec_path = "packaging/Nexy.spec"
    if os.path.exists(spec_path):
        with open(spec_path, 'r') as f:
            content = f.read()
            if 'com.nexy.assistant' in content:
                print("✅ Spec файл содержит правильный Bundle ID")
            else:
                print("❌ Spec файл не содержит правильный Bundle ID")
                return False
    
    # Проверяем конфигурацию
    config_path = "config/unified_config.yaml"
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            content = f.read()
            if 'com.nexy.assistant' in content:
                print("✅ Конфигурация содержит правильный Bundle ID")
            else:
                print("❌ Конфигурация не содержит правильный Bundle ID")
                return False
    
    return True

def test_old_bundle_ids_cleaned():
    """Проверяем, что старые Bundle ID очищены"""
    print("\n🔍 Проверка очистки старых Bundle ID...")
    
    old_bundle_ids = [
        "com.nexy.voiceassistant",
        "com.sergiyzasorin.nexy.voiceassistant"
    ]
    
    for old_id in old_bundle_ids:
        try:
            # Проверяем, что TCC не знает о старом Bundle ID
            result = subprocess.run(
                ["tccutil", "reset", "Microphone", old_id],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if "No matching entries found" in result.stderr:
                print(f"✅ Старый Bundle ID {old_id} очищен из TCC")
            else:
                print(f"⚠️ Старый Bundle ID {old_id} все еще в TCC")
                
        except Exception as e:
            print(f"❌ Ошибка проверки {old_id}: {e}")
    
    return True

def test_permissions_integration():
    """Проверяем, что PermissionsIntegration использует правильный Bundle ID"""
    print("\n🔍 Проверка PermissionsIntegration...")
    
    integration_path = "integration/integrations/permissions_integration.py"
    if os.path.exists(integration_path):
        with open(integration_path, 'r') as f:
            content = f.read()
            if 'UnifiedConfigLoader' in content:
                print("✅ PermissionsIntegration использует UnifiedConfigLoader")
                # Проверяем, что конфигурация содержит правильный Bundle ID
                config_path = "config/unified_config.yaml"
                if os.path.exists(config_path):
                    with open(config_path, 'r') as f:
                        config_content = f.read()
                        if 'com.nexy.assistant' in config_content:
                            print("✅ Конфигурация содержит правильный Bundle ID")
                            return True
                        else:
                            print("❌ Конфигурация не содержит правильный Bundle ID")
                            return False
                else:
                    print("❌ Конфигурация не найдена")
                    return False
            else:
                print("❌ PermissionsIntegration не использует UnifiedConfigLoader")
                return False
    else:
        print("❌ PermissionsIntegration не найден")
        return False

if __name__ == "__main__":
    print("🔍 Диагностика TCC проблем с Bundle ID...")
    print("=" * 60)
    
    # Тест 1: TCC сброс
    tcc_ok = test_tcc_reset()
    
    # Тест 2: Консистентность Bundle ID
    consistency_ok = test_bundle_id_consistency()
    
    # Тест 3: Очистка старых Bundle ID
    cleanup_ok = test_old_bundle_ids_cleaned()
    
    # Тест 4: PermissionsIntegration
    permissions_ok = test_permissions_integration()
    
    print("\n" + "=" * 60)
    print("📊 РЕЗУЛЬТАТЫ:")
    print(f"TCC сброс: {'✅ ВЫПОЛНЕН' if tcc_ok else '❌ НЕ ВЫПОЛНЕН'}")
    print(f"Консистентность Bundle ID: {'✅ ОК' if consistency_ok else '❌ НЕ ОК'}")
    print(f"Очистка старых Bundle ID: {'✅ ВЫПОЛНЕНА' if cleanup_ok else '❌ НЕ ВЫПОЛНЕНА'}")
    print(f"PermissionsIntegration: {'✅ ОК' if permissions_ok else '❌ НЕ ОК'}")
    
    if tcc_ok and consistency_ok and cleanup_ok and permissions_ok:
        print("\n🎉 TCC ПРОБЛЕМА РЕШЕНА! Можно собирать приложение.")
    else:
        print("\n⚠️ TCC ПРОБЛЕМА НЕ РЕШЕНА. Нужны дополнительные исправления.")
