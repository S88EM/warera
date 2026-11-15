#!/usr/bin/env python3
"""
Master launcher for WarEra Market Scanner Suite.
Runs equipment scanner, live Ingress/web dashboard, and Telegram bot.
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Add api directory to sys.path
BASE_DIR = Path(__file__).parent.resolve()
API_DIR = BASE_DIR / "api"
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

# Ensure UTF-8 output
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="WarEra Market Scanner Suite")
    parser.add_argument("--cli", action="store_true", help="Запустити тільки CLI сканер (без веб-панелі)")
    parser.add_argument("--web", action="store_true", help="Запустити тільки автономний Web Dashboard")
    parser.add_argument("--port", type=int, default=8080, help="Порт веб-дашборду (за замовчуванням: 8080)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Хост веб-сервера (за замовчуванням: 0.0.0.0)")
    args = parser.parse_args()

    import config

    if args.web:
        import equipment_dashboard
        from http.server import HTTPServer
        print(f"🚀 Запуск автономного веб-дашборду WarEra на http://{args.host}:{args.port}...")
        server = HTTPServer((args.host, args.port), equipment_dashboard.EquipmentDashboardHandler)
        try:
            print(f"Відкрийте у браузері: http://localhost:{args.port}")
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nВеб-дашборд зупинено.")
        return

    import equipment_scanner
    app = equipment_scanner.EquipmentScannerApp()

    start_web = not args.cli
    if start_web:
        config.WEB_DASHBOARD_HOST = args.host
        config.WEB_DASHBOARD_PORT = args.port
        config.ENABLE_WEB_DASHBOARD = True

    try:
        asyncio.run(app.start(start_web=start_web))
    except KeyboardInterrupt:
        print("\nРоботу завершено.")


if __name__ == "__main__":
    main()
