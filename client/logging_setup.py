#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Настройка логирования для macOS приложения
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path

def setup_logging_for_app():
    """Настраивает логирование для .app файла"""
    
    # Определяем, запущено ли приложение как .app
    if getattr(sys, 'frozen', False):
        # Приложение упаковано в .app
        app_name = "Nexy"
        log_dir = Path.home() / "Library" / "Logs" / app_name
    else:
        # Обычный запуск из Python
        app_name = "Nexy_Dev"
        log_dir = Path.cwd() / "logs"
    
    # Создаем директорию для логов
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Настройки логирования
    log_level = logging.INFO
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # Основной файл логов
    main_log_file = log_dir / "app.log"
    error_log_file = log_dir / "errors.log"
    
    # Создаем форматтер
    formatter = logging.Formatter(log_format, date_format)
    
    # Настраиваем корневой логгер
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Очищаем существующие обработчики
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 1. Файл логов (с ротацией)
    file_handler = logging.handlers.RotatingFileHandler(
        main_log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # 2. Файл ошибок (отдельно)
    error_handler = logging.handlers.RotatingFileHandler(
        error_log_file,
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)
    
    # 3. Консоль (только в режиме разработки)
    if not getattr(sys, 'frozen', False):
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # 4. Системный журнал macOS
    try:
        syslog_handler = logging.handlers.SysLogHandler(
            address='/var/run/syslog',
            facility=logging.handlers.SysLogHandler.LOG_USER
        )
        syslog_handler.setLevel(logging.WARNING)
        syslog_formatter = logging.Formatter('%(name)s: %(levelname)s - %(message)s')
        syslog_handler.setFormatter(syslog_formatter)
        root_logger.addHandler(syslog_handler)
    except Exception as e:
        # Системный журнал недоступен (обычно в .app)
        pass
    
    # Логируем информацию о настройке
    logger = logging.getLogger(__name__)
    logger.info(f"Логирование настроено для {app_name}")
    logger.info(f"Директория логов: {log_dir}")
    logger.info(f"Основной файл: {main_log_file}")
    logger.info(f"Файл ошибок: {error_log_file}")
    logger.info(f"Уровень логирования: {logging.getLevelName(log_level)}")
    
    return logger

def get_logger(name):
    """Получает логгер с указанным именем"""
    return logging.getLogger(name)

def test_logging():
    """Тестирует настройку логирования"""
    logger = setup_logging_for_app()
    
    logger.info("Тест информационного сообщения")
    logger.warning("Тест предупреждения")
    logger.error("Тест ошибки")
    
    # Тестируем разные модули
    test_logger = get_logger("test_module")
    test_logger.info("Тест из другого модуля")
    
    print("✅ Логирование протестировано!")
    print(f"📁 Логи находятся в: {Path.home() / 'Library' / 'Logs' / 'Nexy'}")
    
    return True

if __name__ == "__main__":
    test_logging()
