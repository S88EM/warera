#!/bin/sh
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

if [ ! -f scanner.log ]; then
    touch scanner.log
fi

echo "📋 Перегляд логів сканера (натисніть Ctrl+C для виходу):"
tail -n 30 -f scanner.log
