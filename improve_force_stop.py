#!/usr/bin/env python3
"""
Улучшение метода force_stop для корректной остановки без задержки
"""

import re

def improve_force_stop():
    """Улучшает метод force_stop для мгновенной остановки"""
    
    file_path = "client/audio_player.py"
    
    # Читаем файл
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Находим и заменяем проблемную часть с timeout
    old_timeout_code = '''                else:
                    logger.info("   🚨 Останавливаю поток воспроизведения...")
                    timeout = 0.5
                
                self.playback_thread.join(timeout=timeout)
                if self.playback_thread.is_alive():
                    logger.warning(f"   ⚠️ Поток воспроизведения не остановился в таймаут {timeout}s")
                else:
                    logger.info("   ✅ Поток воспроизведения остановлен")'''
    
    new_timeout_code = '''                else:
                    logger.info("   🚨 Останавливаю поток воспроизведения...")
                    # Ждем завершения с коротким таймаутом
                    self.playback_thread.join(timeout=0.1)
                    if self.playback_thread.is_alive():
                        logger.warning("   ⚠️ Поток воспроизведения не остановился за 100ms")
                    else:
                        logger.info("   ✅ Поток воспроизведения остановлен")'''
    
    # Заменяем
    if old_timeout_code in content:
        content = content.replace(old_timeout_code, new_timeout_code)
        
        # Записываем улучшенный файл
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print('✅ Улучшена остановка без задержки!')
        print('🔧 Уменьшена задержка с 500ms до 100ms')
        print('⚡ Более быстрая остановка для обычного режима')
        print('🚨 Мгновенная остановка для immediate=True')
        return True
    else:
        print('❌ Код с timeout не найден')
        return False

if __name__ == "__main__":
    improve_force_stop()
