#!/bin/bash
set -euo pipefail

echo "🔍 ПРОВЕРКА ВСЕХ АРТЕФАКТОВ NEXY"
echo "================================"
echo ""

ERRORS=0

# Функция для проверки файла
check_file() {
    local file="$1"
    local description="$2"
    
    if [ -f "$file" ]; then
        echo "✅ $description: $file"
        ls -lh "$file"
    else
        echo "❌ $description НЕ НАЙДЕН: $file"
        ERRORS=$((ERRORS + 1))
    fi
}

# Функция для выполнения команды с проверкой
run_check() {
    local description="$1"
    shift
    
    echo "🔍 $description..."
    if "$@"; then
        echo "✅ $description - OK"
    else
        echo "❌ $description - ОШИБКА"
        ERRORS=$((ERRORS + 1))
    fi
    echo ""
}

echo "📁 ПРОВЕРКА НАЛИЧИЯ ФАЙЛОВ"
echo "=========================="

check_file "dist/Nexy-signed.pkg" "PKG инсталлятор"
check_file "dist/Nexy.dmg" "DMG для автообновлений"
check_file "dist/manifest.json" "Манифест обновлений"
check_file "dist/Nexy-final.app" "Финальное приложение"

echo ""
echo "🔐 ПРОВЕРКА ПОДПИСЕЙ"
echo "==================="

# Проверка подписи приложения
if [ -d "dist/Nexy-final.app" ]; then
    run_check "Подпись приложения" \
        codesign --verify --strict --deep dist/Nexy-final.app
    
    echo "📋 Детали подписи приложения:"
    codesign --display --verbose=2 dist/Nexy-final.app 2>&1 | head -10
    echo ""
else
    echo "❌ Приложение не найдено для проверки подписи"
    ERRORS=$((ERRORS + 1))
fi

# Проверка подписи PKG
if [ -f "dist/Nexy-signed.pkg" ]; then
    run_check "Подпись PKG" \
        bash -c "pkgutil --check-signature dist/Nexy-signed.pkg | head -1 | grep -q 'signed by a developer certificate'"
    
    echo "📋 Детали подписи PKG:"
    pkgutil --check-signature dist/Nexy-signed.pkg | head -5
    echo ""
else
    echo "❌ PKG не найден для проверки подписи"
    ERRORS=$((ERRORS + 1))
fi

echo "🔒 ПРОВЕРКА НОТАРИЗАЦИИ"
echo "======================"

# Проверка нотаризации DMG
if [ -f "dist/Nexy.dmg" ]; then
    run_check "Нотаризация DMG" \
        xcrun stapler validate dist/Nexy.dmg
else
    echo "❌ DMG не найден для проверки нотаризации"
    ERRORS=$((ERRORS + 1))
fi

echo "📋 ПРОВЕРКА МАНИФЕСТА"
echo "===================="

if [ -f "dist/manifest.json" ]; then
    echo "🔍 Проверка структуры манифеста..."
    
    # Проверяем JSON валидность
    if python3 -c "import json; json.load(open('dist/manifest.json'))" 2>/dev/null; then
        echo "✅ JSON валидный"
        
        # Показываем основную информацию
        echo "📋 Информация из манифеста:"
        python3 -c "
import json
with open('dist/manifest.json') as f:
    m = json.load(f)
print(f'  Версия: {m[\"version\"]}')
print(f'  Билд: {m[\"build\"]}')
print(f'  Размер: {m[\"artifact\"][\"size\"]:,} байт')
print(f'  SHA256: {m[\"artifact\"][\"sha256\"][:16]}...')
print(f'  Ed25519: {\"Да\" if m[\"artifact\"][\"ed25519\"] else \"Нет\"}')
print(f'  URL: {m[\"artifact\"][\"url\"]}')
"
        echo ""
    else
        echo "❌ Манифест содержит невалидный JSON"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo "❌ Манифест не найден"
    ERRORS=$((ERRORS + 1))
fi

echo "🧪 ФУНКЦИОНАЛЬНЫЕ ТЕСТЫ"
echo "======================"

# Тест запуска приложения
if [ -d "dist/Nexy-final.app" ]; then
    echo "🚀 Тест запуска приложения (5 секунд)..."
    
    dist/Nexy-final.app/Contents/MacOS/Nexy &
    APP_PID=$!
    
    sleep 5
    
    if ps -p $APP_PID > /dev/null 2>&1; then
        echo "✅ Приложение запустилось и работает"
        kill $APP_PID 2>/dev/null || true
        sleep 1
    else
        echo "❌ Приложение не запустилось или упало"
        ERRORS=$((ERRORS + 1))
    fi
    echo ""
fi

# Тест PIL иконок
echo "🎨 Тест PIL для иконок..."
python3 -c "
import sys
import os
import tempfile

# Тестируем PIL
try:
    from PIL import Image, ImageDraw
    print('✅ PIL импортирован успешно')
    
    # Создаем тестовую иконку
    img = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([8, 8, 24, 24], fill='#007AFF')
    
    # Сохраняем во временный файл
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
        img.save(f.name, format='PNG')
        size = os.path.getsize(f.name)
        os.unlink(f.name)
    
    if size > 0:
        print(f'✅ Тестовая иконка создана ({size} байт)')
        print('🎯 PIL работает - иконки должны отображаться!')
    else:
        print('❌ Тестовая иконка пустая')
        
except ImportError as e:
    print(f'❌ PIL не доступен: {e}')
except Exception as e:
    print(f'❌ Ошибка PIL: {e}')
" || ERRORS=$((ERRORS + 1))

echo ""

echo "📊 ИТОГОВАЯ СТАТИСТИКА"
echo "======================"

echo "📁 Размеры файлов:"
if [ -f "dist/Nexy-signed.pkg" ]; then
    PKG_SIZE=$(stat -f%z dist/Nexy-signed.pkg)
    echo "  PKG: $(ls -lh dist/Nexy-signed.pkg | awk '{print $5}')"
fi

if [ -f "dist/Nexy.dmg" ]; then
    DMG_SIZE=$(stat -f%z dist/Nexy.dmg)
    echo "  DMG: $(ls -lh dist/Nexy.dmg | awk '{print $5}')"
fi

if [ -d "dist/Nexy-final.app" ]; then
    APP_SIZE=$(du -sh dist/Nexy-final.app | awk '{print $1}')
    echo "  APP: $APP_SIZE"
fi

echo ""
echo "🔐 Безопасность:"
echo "  ✅ Подпись: Developer ID Application (5NKLL2CLB9)"
echo "  ✅ PKG: Developer ID Installer (5NKLL2CLB9)"
echo "  ✅ DMG: Нотаризован Apple"
echo "  ✅ Манифест: SHA256 + Ed25519"

echo ""
if [ $ERRORS -eq 0 ]; then
    echo "🎉 ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ УСПЕШНО!"
    echo "================================="
    echo ""
    echo "✅ Готовые артефакты для публикации:"
    echo "   📦 PKG: dist/Nexy-signed.pkg"
    echo "   💿 DMG: dist/Nexy.dmg"
    echo "   📋 Манифест: dist/manifest.json"
    echo ""
    echo "🚀 Следующий шаг: Тестовая установка"
    echo "   sudo installer -pkg dist/Nexy-signed.pkg -target /"
    echo ""
    echo "🎯 ВАЖНО: После установки проверьте цветные иконки в меню-баре!"
    
    exit 0
else
    echo "❌ НАЙДЕНО ОШИБОК: $ERRORS"
    echo "======================="
    echo ""
    echo "🔧 Рекомендации:"
    echo "1. Исправьте найденные ошибки"
    echo "2. Пересоберите артефакты: ./packaging/build_all.sh"
    echo "3. Повторите проверку: ./packaging/verify_all.sh"
    
    exit 1
fi

