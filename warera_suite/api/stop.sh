#!/bin/sh
# WarEra Scanner Background Stopper
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

STOPPED=0
if [ -f scanner.pid ]; then
    PID=$(cat scanner.pid)
    if kill -0 "$PID" 2>/dev/null; then
        kill "$PID" 2>/dev/null || kill -9 "$PID" 2>/dev/null
        echo "🛑 Надіслано сигнал зупинки процесу (PID: $PID)..."
        STOPPED=1
    fi
    rm -f scanner.pid
fi

# Also cleanup any orphaned equipment_scanner or old commodity processes
pkill -9 -f "equipment_scanner.py" 2>/dev/null && STOPPED=1
pkill -9 -f "main.py" 2>/dev/null && STOPPED=1
pkill -9 -f "analyzer.py" 2>/dev/null && STOPPED=1
rm -f main.py analyzer.py

if [ "$STOPPED" -eq 1 ]; then
    echo "✓ Сканер спорядження та всі старі процеси успішно зупинено."
else
    echo "ℹ️ Процесів сканера не знайдено."
fi
