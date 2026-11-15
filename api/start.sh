#!/bin/sh
# WarEra Scanner Background Runner
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

# Очищаємо будь-які старі процеси сканера та застарілий моніторинг ресурсів
pkill -9 -f "equipment_scanner.py" 2>/dev/null
pkill -9 -f "main.py" 2>/dev/null
pkill -9 -f "analyzer.py" 2>/dev/null
rm -f main.py analyzer.py scanner.pid
sleep 1

nohup .venv/bin/python equipment_scanner.py > scanner.log 2>&1 &
PID=$!
echo $PID > scanner.pid

echo "✅ Сканер WarEra успішно запущено у фоні (PID: $PID)!"
echo "📋 Дивитися логи в реальному часі: ./logs.sh"
echo "🛑 Зупинити: ./stop.sh"
