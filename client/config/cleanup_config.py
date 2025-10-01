#!/usr/bin/env python3
"""
Скрипт очистки и проверки конфигурации перед сборкой
Удаляет дублирующиеся файлы и проверяет согласованность
"""

import os
import sys
import yaml
from pathlib import Path
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class ConfigCleanup:
    """Очистка и проверка конфигурации"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.config_dir = project_root / "config"
        self.issues_found = []
        
    def cleanup_duplicate_files(self):
        """Удаляет дублирующиеся конфигурационные файлы"""
        logger.info("🧹 Очистка дублирующихся файлов...")
        
        duplicate_patterns = [
            "logging_config 2.yaml",
            "network_config 2.yaml", 
            "tray_config 2.yaml",
            "*.bak",
            "*.backup",
            "*.old"
        ]
        
        removed_files = []
        for pattern in duplicate_patterns:
            for file_path in self.config_dir.glob(pattern):
                if file_path.exists():
                    try:
                        file_path.unlink()
                        removed_files.append(str(file_path))
                        logger.info(f"  ✅ Удален: {file_path.name}")
                    except Exception as e:
                        logger.error(f"  ❌ Ошибка удаления {file_path.name}: {e}")
                        self.issues_found.append(f"Не удалось удалить {file_path.name}")
        
        if removed_files:
            logger.info(f"🗑️ Удалено {len(removed_files)} дублирующихся файлов")
        else:
            logger.info("✨ Дублирующиеся файлы не найдены")
            
        return len(removed_files)
    
    def check_hardcoded_ips(self):
        """Проверяет хардкод IP-адресов в модулях"""
        logger.info("🔍 Проверка хардкода IP-адресов...")
        
        # Загружаем актуальную конфигурацию
        unified_config_path = self.config_dir / "unified_config.yaml"
        if not unified_config_path.exists():
            self.issues_found.append("unified_config.yaml не найден")
            return False
            
        with open(unified_config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # Получаем актуальные IP-адреса
        servers = config.get('servers', {}).get('grpc_servers', {})
        production_ip = servers.get('production', {}).get('host', '')
        local_ip = servers.get('local', {}).get('host', '')
        
        # Проверяем модули на хардкод
        modules_dir = self.project_root / "modules"
        hardcoded_files = []
        
        for py_file in modules_dir.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Ищем хардкод IP-адресов
                if production_ip in content and "АВТОМАТИЧЕСКИ СИНХРОНИЗИРУЕТСЯ" not in content:
                    hardcoded_files.append((str(py_file), production_ip))
                if local_ip in content and "АВТОМАТИЧЕСКИ СИНХРОНИЗИРУЕТСЯ" not in content:
                    hardcoded_files.append((str(py_file), local_ip))
                    
            except Exception as e:
                logger.warning(f"Не удалось проверить {py_file}: {e}")
        
        if hardcoded_files:
            logger.warning(f"⚠️ Найден хардкод IP-адресов в {len(hardcoded_files)} файлах:")
            for file_path, ip in hardcoded_files:
                logger.warning(f"  📄 {file_path}: {ip}")
                self.issues_found.append(f"Хардкод {ip} в {file_path}")
        else:
            logger.info("✅ Хардкод IP-адресов не найден")
            
        return len(hardcoded_files) == 0
    
    def verify_config_consistency(self):
        """Проверяет согласованность конфигурационных файлов"""
        logger.info("🔍 Проверка согласованности конфигурации...")
        
        # Проверяем unified_config.yaml
        unified_config_path = self.config_dir / "unified_config.yaml"
        if not unified_config_path.exists():
            self.issues_found.append("unified_config.yaml не найден")
            return False
            
        try:
            with open(unified_config_path, 'r', encoding='utf-8') as f:
                unified_config = yaml.safe_load(f)
        except Exception as e:
            self.issues_found.append(f"Ошибка загрузки unified_config.yaml: {e}")
            return False
        
        # Проверяем network_config.yaml
        network_config_path = self.config_dir / "network_config.yaml"
        if network_config_path.exists():
            try:
                with open(network_config_path, 'r', encoding='utf-8') as f:
                    network_config = yaml.safe_load(f)
                
                # Сравниваем серверы
                unified_servers = unified_config.get('servers', {}).get('grpc_servers', {})
                network_servers = network_config.get('grpc_servers', {})
                
                if unified_servers != network_servers:
                    logger.warning("⚠️ network_config.yaml не синхронизирован с unified_config.yaml")
                    self.issues_found.append("network_config.yaml не синхронизирован")
                    return False
                else:
                    logger.info("✅ network_config.yaml синхронизирован")
            except Exception as e:
                logger.warning(f"Ошибка проверки network_config.yaml: {e}")
        
        logger.info("✅ Конфигурация согласована")
        return True
    
    def check_build_readiness(self):
        """Проверяет готовность к сборке"""
        logger.info("🏗️ Проверка готовности к сборке...")
        
        # Проверяем наличие ключевых файлов
        required_files = [
            "unified_config.yaml",
            "unified_config_loader.py",
            "server_config_sync.py",
            "change_server.py"
        ]
        
        missing_files = []
        for file_name in required_files:
            file_path = self.config_dir / file_name
            if not file_path.exists():
                missing_files.append(file_name)
        
        if missing_files:
            logger.error(f"❌ Отсутствуют файлы: {', '.join(missing_files)}")
            self.issues_found.extend([f"Отсутствует {f}" for f in missing_files])
            return False
        
        # Проверяем синтаксис YAML
        try:
            with open(self.config_dir / "unified_config.yaml", 'r', encoding='utf-8') as f:
                yaml.safe_load(f)
            logger.info("✅ Синтаксис unified_config.yaml корректен")
        except Exception as e:
            logger.error(f"❌ Ошибка синтаксиса unified_config.yaml: {e}")
            self.issues_found.append(f"Ошибка синтаксиса unified_config.yaml: {e}")
            return False
        
        logger.info("✅ Готовность к сборке подтверждена")
        return True
    
    def run_full_cleanup(self):
        """Запускает полную очистку и проверку"""
        logger.info("🚀 Запуск полной очистки конфигурации...")
        
        results = {
            'duplicates_removed': self.cleanup_duplicate_files(),
            'hardcode_clean': self.check_hardcoded_ips(),
            'config_consistent': self.verify_config_consistency(),
            'build_ready': self.check_build_readiness()
        }
        
        # Итоговый отчет
        logger.info("\n" + "="*50)
        logger.info("📊 ИТОГОВЫЙ ОТЧЕТ")
        logger.info("="*50)
        
        if results['duplicates_removed'] > 0:
            logger.info(f"🗑️ Удалено дублирующихся файлов: {results['duplicates_removed']}")
        
        logger.info(f"🔍 Хардкод IP-адресов: {'✅ Чисто' if results['hardcode_clean'] else '❌ Найден'}")
        logger.info(f"🔍 Согласованность конфигурации: {'✅ OK' if results['config_consistent'] else '❌ Проблемы'}")
        logger.info(f"🏗️ Готовность к сборке: {'✅ Готово' if results['build_ready'] else '❌ Не готово'}")
        
        if self.issues_found:
            logger.warning(f"\n⚠️ НАЙДЕННЫЕ ПРОБЛЕМЫ ({len(self.issues_found)}):")
            for i, issue in enumerate(self.issues_found, 1):
                logger.warning(f"  {i}. {issue}")
        else:
            logger.info("\n🎉 Все проверки пройдены успешно!")
        
        return len(self.issues_found) == 0


def main():
    """Главная функция"""
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("""
Скрипт очистки и проверки конфигурации перед сборкой

Использование:
  python3 config/cleanup_config.py          # Полная очистка и проверка
  python3 config/cleanup_config.py --help   # Показать эту справку

Что делает:
  🧹 Удаляет дублирующиеся конфигурационные файлы
  🔍 Проверяет хардкод IP-адресов в модулях
  🔍 Проверяет согласованность конфигурации
  🏗️ Проверяет готовность к сборке
        """)
        return
    
    # Определяем корень проекта
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    # Запускаем очистку
    cleanup = ConfigCleanup(project_root)
    success = cleanup.run_full_cleanup()
    
    # Возвращаем код выхода
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
