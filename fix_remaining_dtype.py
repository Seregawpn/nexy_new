#!/usr/bin/env python3
"""
Скрипт для исправления оставшихся строковых dtype
"""

def fix_remaining_dtype():
    """Исправляет оставшиеся места с строковым dtype"""
    
    file_path = "/Users/sergiyzasorin/Desktop/Development/Nexy/client/audio_player.py"
    
    # Читаем файл
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Исправления
    fixes = [
        # В конструкторе - оставляем как есть, это параметр по умолчанию
        # ("dtype='int16'", "dtype=np.int16"),  # НЕ ТРОГАЕМ - это параметр по умолчанию
        
        # В fallback конфигурации
        ("                                            self.dtype = 'int16'", "                                            self.dtype = np.int16"),
    ]
    
    # Применяем исправления
    for old, new in fixes:
        if old in content:
            content = content.replace(old, new)
            print(f"✅ Исправлено: {old}")
        else:
            print(f"⚠️ Не найдено: {old}")
    
    # Записываем исправленный файл
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("🎉 Оставшиеся исправления применены!")

if __name__ == "__main__":
    fix_remaining_dtype()
