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
    parser = argparse.ArgumentParser(description="WarEra Market & Combat Suite")
    parser.add_argument("--cli", action="store_true", help="Запустити тільки CLI сканер ринку спорядження")
    parser.add_argument("--web", action="store_true", help="Запустити веб-дашборд сканера спорядження")
    parser.add_argument("--battles", action="store_true", help="Запустити консольний моніторинг мінімального дамагу для фіолетових речей")
    parser.add_argument("--sniper", action="store_true", help="Фільтрувати тільки битви у снайперському вікні (15–20 хв до кінця раунду)")
    parser.add_argument("--battles-watch", action="store_true", help="Запустити живий консольний моніторинг битв (оновлення кожні 15 сек)")
    parser.add_argument("--battles-web", action="store_true", help="Запустити інтерактивний веб-дашборд моніторингу фіолетового дропу")
    parser.add_argument("--sniper-bot", action="store_true", help="Запустити тільки автономний Sniper Telegram Bot для сокланівців")
    parser.add_argument("--nick", type=str, default=None, help="Нікнейм гравця для аналізу робітників")
    parser.add_argument("--port", type=int, default=8080, help="Порт веб-дашборду (за замовчуванням: 8080 для маркету, 8086 для битв)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Хост веб-сервера (за замовчуванням: 0.0.0.0)")
    args = parser.parse_args()

    import config

    if args.battles or args.sniper:
        import battle_monitor
        asyncio.run(battle_monitor.run_once(user_nick=args.nick, sniper_only=args.sniper))
        return

    if args.battles_watch:
        import battle_monitor
        asyncio.run(battle_monitor.run_watch(user_nick=args.nick, sniper_only=args.sniper))
        return

    if args.battles_web:
        import battle_dashboard
        target_port = args.port if args.port != 8080 else 8086
        battle_dashboard.run_standalone(host=args.host, port=target_port)
        return

    if args.sniper_bot:
        import sniper_bot
        from battle_sniper_worker import get_sniper_worker
        bot = sniper_bot.SniperBotController()
        if not bot.token:
            print("❌ TELEGRAM_SNIPER_BOT_TOKEN не задано в .env або конфізі!")
            return
        print("🚀 Запуск автономного Sniper Telegram Bot та фонового моніторингу для клану...")
        async def run_sniper_all():
            worker = get_sniper_worker()
            await asyncio.gather(
                bot.start_polling(),
                worker.start(),
            )
        try:
            asyncio.run(run_sniper_all())
        except KeyboardInterrupt:
            print("\nSniper Bot зупинено.")
        return

    if args.web:
        import equipment_dashboard
        from equipment_scanner import EquipmentScannerApp
        scanner_app = EquipmentScannerApp()
        equipment_dashboard.run_standalone(host=args.host, port=args.port, app_instance=scanner_app)
        return

    from orchestrator import TaskOrchestrator

    start_web = not args.cli
    if start_web:
        config.WEB_DASHBOARD_HOST = args.host
        config.WEB_DASHBOARD_PORT = args.port
        config.ENABLE_WEB_DASHBOARD = True

    orchestrator = TaskOrchestrator(
        enable_market=True,
        enable_sniper=True,
        enable_clan_tracker=True,
        enable_market_bot=True,
        enable_sniper_bot=True,
        enable_web=start_web,
        web_host=args.host,
        web_port=args.port,
    )

    try:
        asyncio.run(orchestrator.run())
    except KeyboardInterrupt:
        print("\nРоботу завершено.")


if __name__ == "__main__":
    main()
