#!/usr/bin/env python3
"""
Скрипт для исправления проблемы с dtype в audio_player.py
"""

def fix_dtype_issues():
    """Исправляет все места где dtype используется как строка вместо np.int16"""
    
    file_path = "/Users/sergiyzasorin/Desktop/Development/Nexy/client/audio_player.py"
    
    # Читаем файл
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Исправления
    fixes = [
        # Основная проблема в кэшированной конфигурации (строка 1103)
        ("                config = {\n                    'channels': self.stream.channels,\n                    'samplerate': self.stream.samplerate,\n                    'dtype': 'int16'\n                }", 
         "                config = {\n                    'channels': self.stream.channels,\n                    'samplerate': self.stream.samplerate,\n                    'dtype': np.int16\n                }"),
        
        # В предзагрузке (строки 124, 130)
        ("                        'dtype': 'int16'", "                        'dtype': np.int16"),
        
        # В fallback конфигурации (строка 1499)
        ("                                                dtype='int16',", "                                                dtype=np.int16,"),
        
        # В совместимых параметрах - все случаи
        ("'dtype': 'int16'", "'dtype': np.int16"),
    ]
    
    # Применяем исправления
    for old, new in fixes:
        if old in content:
            content = content.replace(old, new)
            print(f"✅ Исправлено: {old[:50]}...")
        else:
            print(f"⚠️ Не найдено: {old[:50]}...")
    
    # Записываем исправленный файл
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("🎉 Исправления применены!")

if __name__ == "__main__":
    fix_dtype_issues()
