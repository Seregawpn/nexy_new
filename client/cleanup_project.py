"""
Скрипт для очистки проекта от дублирующихся и устаревших файлов

Анализирует проект и предлагает удалить:
1. Старые тестовые файлы
2. Дублирующиеся конфигурационные файлы
3. Старые версии аудио файлов
4. Устаревшую документацию
5. Дублирующиеся ресурсы

БЕЗОПАСНО: Сначала показывает что будет удалено, затем запрашивает подтверждение
"""

import sys
from pathlib import Path
from typing import List, Dict, Tuple

CLIENT_ROOT = Path(__file__).parent

# Категории файлов для удаления
CLEANUP_CATEGORIES = {
    "old_audio_tests": {
        "description": "Старые тестовые файлы для отладки аудио (больше не нужны)",
        "files": [
            "diagnose_audio.py",
            "test_audio_simple.py",
            "test_channel_conversion.py",
            "test_device_channels.py",
            "test_exact_playback.py",
            "test_playback_chain.py",
            "test_player_config.py",
        ]
    },
    
    "old_audio_files": {
        "description": "Старые версии аудио файлов приветствия (дубликаты)",
        "files": [
            "assets/audio/welcome_en_old.mp3",
            "assets/audio/welcome_en_new.aiff",
            # Аудио файлы приветствия удалены - теперь используется серверная генерация
        ]
    },
    
    "old_config_duplicates": {
        "description": "Дублирующиеся конфигурационные файлы (с ' 2' в имени)",
        "files": [
            "config/logging_config 2.yaml",
            "config/network_config 2.yaml",
            "config/tray_config 2.yaml",
        ]
    },
    
    "old_resource_duplicates": {
        "description": "Дублирующиеся ресурсы (старые версии иконок)",
        "files": [
            "assets/icons/app_icon 2.icns",
            "assets/icons/app_icon 3.icns",
            "assets/icons/app_icon 4.icns",
            "resources/logo 2.icns",
        ]
    },
    
    "old_documentation": {
        "description": "Устаревшая документация (заменена на WELCOME_SOUND_FIX.md)",
        "files": [
            "AUDIO_FIX_REPORT.md",
            "AUDIO_PATH_FIX.md",
        ]
    },
    
    "test_scripts": {
        "description": "Тестовые скрипты (можно оставить для отладки или удалить после успешной сборки)",
        "files": [
            "test_pyobjc_fix.py",
            "test_resource_path.py",
            "test_packaged_simulation.py",
            # test_all_before_packaging.py оставляем - это главный тест
        ],
        "optional": True  # Помечаем как опциональное для удаления
    },
}

def analyze_files() -> Dict[str, List[Tuple[Path, bool]]]:
    """
    Анализирует файлы для удаления
    
    Returns:
        Dict с категориями и списками (путь, существует_ли_файл)
    """
    results = {}
    
    for category, info in CLEANUP_CATEGORIES.items():
        files_info = []
        
        for file_path in info["files"]:
            full_path = CLIENT_ROOT / file_path
            exists = full_path.exists()
            files_info.append((full_path, exists))
        
        results[category] = {
            "description": info["description"],
            "files": files_info,
            "optional": info.get("optional", False)
        }
    
    return results

def print_analysis(results: Dict):
    """Выводит анализ файлов"""
    print("=" * 80)
    print("🔍 АНАЛИЗ ПРОЕКТА - Файлы для очистки")
    print("=" * 80)
    
    total_files = 0
    total_size = 0
    existing_files = 0
    
    for category, info in results.items():
        optional = " (ОПЦИОНАЛЬНО)" if info["optional"] else ""
        print(f"\n📁 {category.upper()}{optional}")
        print(f"   {info['description']}")
        print("-" * 80)
        
        for file_path, exists in info["files"]:
            if exists:
                size = file_path.stat().st_size
                size_kb = size / 1024
                status = f"✓ EXISTS ({size_kb:.1f} KB)"
                total_size += size
                existing_files += 1
            else:
                status = "✗ NOT FOUND"
            
            relative_path = file_path.relative_to(CLIENT_ROOT)
            print(f"   {status:25} {relative_path}")
            total_files += 1
    
    print("\n" + "=" * 80)
    print(f"📊 ИТОГО:")
    print(f"   • Всего файлов в списке: {total_files}")
    print(f"   • Существующих файлов: {existing_files}")
    print(f"   • Общий размер: {total_size / 1024:.1f} KB ({total_size / (1024*1024):.2f} MB)")
    print("=" * 80)

def delete_files(results: Dict, skip_optional: bool = True):
    """Удаляет файлы"""
    print("\n🗑️  УДАЛЕНИЕ ФАЙЛОВ...")
    print("-" * 80)
    
    deleted_count = 0
    failed_count = 0
    skipped_count = 0
    
    for category, info in results.items():
        if info["optional"] and skip_optional:
            print(f"\n⏭️  Пропускаю опциональную категорию: {category}")
            skipped_count += len([f for f, exists in info["files"] if exists])
            continue
        
        print(f"\n📁 {category}")
        
        for file_path, exists in info["files"]:
            if not exists:
                continue
            
            try:
                file_path.unlink()
                print(f"   ✅ Удалён: {file_path.relative_to(CLIENT_ROOT)}")
                deleted_count += 1
            except Exception as e:
                print(f"   ❌ Ошибка при удалении {file_path.name}: {e}")
                failed_count += 1
    
    print("\n" + "=" * 80)
    print(f"📊 РЕЗУЛЬТАТЫ:")
    print(f"   • Удалено: {deleted_count}")
    print(f"   • Ошибок: {failed_count}")
    print(f"   • Пропущено (опционально): {skipped_count}")
    print("=" * 80)
    
    return deleted_count > 0

def main():
    """Главная функция"""
    print("=" * 80)
    print("🧹 ОЧИСТКА ПРОЕКТА NEXY")
    print("=" * 80)
    print("\nЭтот скрипт поможет очистить проект от устаревших и дублирующихся файлов.")
    print("Все операции безопасны - сначала показывается анализ, затем запрашивается подтверждение.\n")
    
    # Анализ
    results = analyze_files()
    print_analysis(results)
    
    # Подтверждение
    print("\n❓ ЧТО ДЕЛАТЬ?")
    print("-" * 80)
    print("1. Удалить только обязательные файлы (рекомендуется)")
    print("2. Удалить ВСЕ файлы (включая тестовые скрипты)")
    print("3. Отмена (ничего не удалять)")
    print()
    
    try:
        choice = input("Выберите вариант (1/2/3): ").strip()
        
        if choice == "1":
            print("\n✅ Удаляю только обязательные файлы...")
            if delete_files(results, skip_optional=True):
                print("\n✅ ГОТОВО! Обязательные файлы удалены.")
                print("\n💡 Тестовые скрипты сохранены для будущей отладки.")
                print("   Их можно удалить вручную или запустить скрипт снова с опцией 2.")
            else:
                print("\n⚠️  Нечего удалять - все файлы уже отсутствуют.")
        
        elif choice == "2":
            print("\n⚠️  ВНИМАНИЕ! Будут удалены ВСЕ файлы, включая тестовые скрипты!")
            confirm = input("Вы уверены? (yes/no): ").strip().lower()
            
            if confirm == "yes":
                print("\n✅ Удаляю ВСЕ файлы...")
                if delete_files(results, skip_optional=False):
                    print("\n✅ ГОТОВО! Все файлы удалены.")
                else:
                    print("\n⚠️  Нечего удалять - все файлы уже отсутствуют.")
            else:
                print("\n❌ Отменено пользователем.")
        
        else:
            print("\n❌ Отменено. Файлы не удалены.")
        
    except KeyboardInterrupt:
        print("\n\n❌ Прервано пользователем. Файлы не удалены.")
        return 1
    
    print("\n" + "=" * 80)
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)





