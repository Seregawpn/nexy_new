"""
Комплексное тестирование перед упаковкой приложения

Запускает все тесты по порядку:
1. PyObjC Fix (NSMakeRect проблема)
2. Resource Paths (пути к ресурсам)
3. Packaged Simulation (симуляция .app)
4. Welcome Player Integration (интеграционный тест)
"""

import sys
import asyncio
from pathlib import Path
import subprocess

# Добавляем пути
CLIENT_ROOT = Path(__file__).parent
sys.path.insert(0, str(CLIENT_ROOT))
sys.path.insert(0, str(CLIENT_ROOT / "modules"))
sys.path.insert(0, str(CLIENT_ROOT / "integration"))

def print_section(title, icon="🧪"):
    """Печатает красивый разделитель секции"""
    print("\n" + "=" * 80)
    print(f"{icon} {title}")
    print("=" * 80)

def run_test_script(script_name, description):
    """Запускает тестовый скрипт и возвращает результат"""
    print(f"\n▶️  Запуск: {description}")
    print("-" * 80)
    
    script_path = CLIENT_ROOT / script_name
    
    if not script_path.exists():
        print(f"❌ Скрипт не найден: {script_path}")
        return False
    
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Выводим результат
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        success = result.returncode == 0
        if success:
            print(f"✅ {description} - PASS")
        else:
            print(f"❌ {description} - FAIL (exit code: {result.returncode})")
        
        return success
        
    except subprocess.TimeoutExpired:
        print(f"❌ {description} - TIMEOUT (>30s)")
        return False
    except Exception as e:
        print(f"❌ {description} - ERROR: {e}")
        return False

async def test_welcome_player_integration():
    """Интеграционный тест Welcome Player с настоящей загрузкой аудио"""
    print_section("ТЕСТ 5: Welcome Player Integration", "🎵")
    
    try:
        # Импортируем необходимые модули
        from modules.welcome_message.core.types import WelcomeConfig
        from modules.welcome_message.core.welcome_player import WelcomePlayer
        
        print("📋 Проверка server-only конфигурации...")
        config = WelcomeConfig()
        print(f"   • enabled: {config.enabled}")
        print(f"   • use_server: {config.use_server}")
        if not config.use_server:
            print("❌ Конфигурация должна использовать серверную генерацию приветствия")
            return False

        print("\n🎵 Симулируем запуск без серверной поддержки (use_server=False)...")
        config_disabled = WelcomeConfig(
            enabled=True,
            text=config.text,
            delay_sec=config.delay_sec,
            volume=config.volume,
            voice=config.voice,
            sample_rate=config.sample_rate,
            channels=config.channels,
            bit_depth=config.bit_depth,
            use_server=False,
            server_timeout_sec=config.server_timeout_sec,
        )

        player = WelcomePlayer(config_disabled)
        result = await player.play_welcome()

        print(f"   • success: {result.success}")
        print(f"   • method: {result.method}")
        print(f"   • error: {result.error}")

        if result.success or result.method != "none":
            print("❌ Плеер не должен воспроизводить приветствие без сервера")
            return False

        if not result.error:
            print("❌ Ожидалось сообщение об ошибке при отключении сервера")
            return False

        print("\n✅ Welcome Player Integration (server-only check) - PASS")
        return True
        
    except Exception as e:
        print(f"\n❌ Welcome Player Integration - FAIL")
        print(f"   Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_ffmpeg_availability():
    """Проверяет доступность ffmpeg для pydub"""
    print_section("ТЕСТ 6: FFmpeg Availability", "🎬")
    
    try:
        from pydub import AudioSegment
        import os
        
        print("📋 Проверка настроек ffmpeg...")
        
        # Проверяем переменную окружения
        ffmpeg_binary = os.environ.get("FFMPEG_BINARY")
        if ffmpeg_binary:
            print(f"   • FFMPEG_BINARY env: {ffmpeg_binary}")
            print(f"   • Файл существует: {Path(ffmpeg_binary).exists()}")
        else:
            print("   • FFMPEG_BINARY env: не установлена")
        
        # Проверяем converter в AudioSegment
        if hasattr(AudioSegment, "converter"):
            print(f"   • AudioSegment.converter: {AudioSegment.converter}")
        
        # Создаем тестовый аудио файл для проверки
        test_audio_path = CLIENT_ROOT / "test_audio_temp.wav"
        
        # Создаем простой тестовый аудио файл
        from pydub.generators import Sine
        test_audio = Sine(440).to_audio_segment(duration=1000)  # 1 секунда 440Hz
        test_audio.export(str(test_audio_path), format="wav")
        
        print(f"\n🎵 Попытка загрузить: {test_audio_path.name}")
        
        audio = AudioSegment.from_file(str(test_audio_path))
        
        print(f"✅ Файл успешно загружен!")
        print(f"   • Длительность: {len(audio) / 1000:.2f} сек")
        print(f"   • Sample rate: {audio.frame_rate} Hz")
        print(f"   • Каналы: {audio.channels}")
        print(f"   • Sample width: {audio.sample_width} bytes")
        
        # Очищаем временный файл
        test_audio_path.unlink()
        
        return True
        
    except Exception as e:
        print(f"❌ FFmpeg Availability - FAIL")
        print(f"   Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Главная функция - запускает все тесты"""
    print_section("КОМПЛЕКСНОЕ ТЕСТИРОВАНИЕ ПЕРЕД УПАКОВКОЙ", "🚀")
    print("\nЭтот скрипт проверяет все критические компоненты")
    print("перед пересборкой упакованного приложения.\n")
    
    results = {}
    
    # Тест 1: PyObjC Fix
    results['pyobjc_fix'] = run_test_script(
        'test_pyobjc_fix.py',
        'PyObjC Fix (NSMakeRect)'
    )
    
    # Тест 2: Resource Paths
    results['resource_paths'] = run_test_script(
        'test_resource_path.py',
        'Resource Paths'
    )
    
    # Тест 3: Packaged Simulation
    results['packaged_simulation'] = run_test_script(
        'test_packaged_simulation.py',
        'Packaged Simulation'
    )
    
    # Тест 4: FFmpeg
    results['ffmpeg'] = test_ffmpeg_availability()
    
    # Тест 5: Welcome Player Integration
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        results['welcome_player'] = loop.run_until_complete(
            test_welcome_player_integration()
        )
        loop.close()
    except Exception as e:
        print(f"❌ Ошибка в Welcome Player Integration: {e}")
        results['welcome_player'] = False
    
    # Итоговая сводка
    print_section("ИТОГОВАЯ СВОДКА", "📊")
    
    print("\n📋 Результаты тестов:")
    print("-" * 80)
    
    all_passed = True
    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        test_display = test_name.replace('_', ' ').title()
        print(f"   {status} - {test_display}")
        if not success:
            all_passed = False
    
    print("-" * 80)
    
    if all_passed:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
        print("\n✅ Готово к упаковке:")
        print("   cd /Users/sergiyzasorin/Development/Nexy/client")
        print("   ./packaging/build_final.sh")
        print("\n💡 После установки .pkg проверьте:")
        print("   1. Приложение запускается (нет ошибки NSMakeRect)")
        print("   2. Звук приветствия воспроизводится корректно")
        print("   3. Проверьте логи: tail -f ~/Library/Logs/Nexy/nexy.log")
        
    else:
        print("\n⚠️  ЕСТЬ ПРОБЛЕМЫ!")
        print("\n❌ НЕ рекомендуется упаковывать приложение")
        print("\n💡 Исправьте ошибки выше и запустите тесты снова:")
        print("   python3 test_all_before_packaging.py")
    
    print("\n" + "=" * 80)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)



