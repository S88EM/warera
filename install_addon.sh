#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

echo "=========================================================="
echo " Встановлення додатку WarEra Suite у Home Assistant"
echo "=========================================================="

DEST="/addons/warera_suite"
if [ ! -d "/addons" ]; then
    echo "Створення каталогу /addons..."
    sudo mkdir -p /addons 2>/dev/null || mkdir -p /addons 2>/dev/null || true
fi

if [ -d "$DIR/warera_suite" ]; then
    SOURCE="$DIR/warera_suite"
else
    echo "❌ Помилка: папку warera_suite не знайдено!"
    exit 1
fi

echo "Копіювання warera_suite у /addons/..."
sudo cp -rf "$SOURCE" /addons/ 2>/dev/null || cp -rf "$SOURCE" /addons/

echo ""
echo "✅ Успішно встановлено у /addons/warera_suite!"
echo ""
echo "Тепер у Home Assistant:"
echo "1. Відкрийте: Налаштування -> Додатки -> Магазин додатків (Add-on Store)"
echo "2. Натисніть три крапки (⋮) у верхньому правому кутку -> «Перевірити оновлення»"
echo "3. Вгорі у розділі «Локальні додатки» з'явиться «WarEra Suite»"
echo "4. Натисніть «Встановити», налаштуйте опції в меню та натисніть «Запустити»!"
echo "=========================================================="
