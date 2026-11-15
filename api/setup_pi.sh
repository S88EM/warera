#!/bin/bash
set -e

echo "=== Встановлення WarEra Market Scanner на Raspberry Pi ==="

sudo apt update
sudo apt install -y python3 python3-venv python3-pip

if [ ! -d ".venv" ]; then
    echo "Створення .venv..."
    python3 -m venv .venv
fi

echo "Встановлення залежностей..."
./.venv/bin/pip install --upgrade pip
./.venv/bin/pip install -r requirements.txt

if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "Створено файл .env. Не забудьте вказати TELEGRAM_BOT_TOKEN та TELEGRAM_CHAT_ID!"
fi

echo "=== Встановлення успішно завершено! ==="
echo "Для запуску: ./start.sh"
