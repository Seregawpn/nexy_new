#!/usr/bin/env python3
import re

# Читаем файл
with open('client/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Ищем и заменяем блокирующий цикл
old_pattern = r'while True:\s*# Проверяем статус каждые 100ms\s*await asyncio\.sleep\(0\.1\)\s*# Проверяем, завершилось ли аудио\s*if self\.audio_player\.wait_for_queue_empty\(\):\s*logger\.info\(f"   🎵 Аудио естественно завершено"\)\s*self\.console\.print\("\[green\]🎵 Аудио естественно завершено\[/green\]"\)\s*break\s*# Проверяем, не прервано ли воспроизведение\s*if not self\.audio_player\.is_playing:\s*logger\.info\(f"   🎵 Воспроизведение прервано"\)\s*self\.console\.print\("\[yellow\]🎵 Воспроизведение прервано\[/yellow\]"\)\s*break\s*# Проверяем, не было ли прерывания\s*if hasattr\(self, \'input_handler\'\) and self\.input_handler:\s*if self\.input_handler\.get_interrupt_status\(\):\s*logger\.info\(f"   🚨 Обнаружено прерывание во время ожидания аудио"\)\s*self\.console\.print\("\[red\]🚨 Прерывание во время ожидания аудио\[/red\]"\)\s*break'

new_code = '''# Просто проверяем статус один раз, не блокируем основной поток
                    if self.audio_player.wait_for_queue_empty():
                        logger.info(f"   🎵 Аудио уже завершено")
                        self.console.print("[green]🎵 Аудио уже завершено[/green]")
                    else:
                        logger.info(f"   🎵 Аудио продолжает воспроизводиться в фоне")
                        self.console.print("[blue]🎵 Аудио продолжает воспроизводиться в фоне[/blue]")'''

# Заменяем
new_content = re.sub(old_pattern, new_code, content, flags=re.DOTALL)

# Записываем
with open('client/main.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("✅ Исправление применено!")
