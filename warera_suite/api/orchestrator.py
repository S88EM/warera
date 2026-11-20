"""
WarEra Suite Task Orchestrator.
Central coordinator for background services:
- Market Scanner Service (EquipmentScannerApp)
- Battle Sniper Worker (Purple Loot Monitoring)
- Clan Tracker Service (Damage & Roster Snapshots)
- Telegram Market Admin Bot
- Telegram Clan Sniper Bot
"""

import asyncio
import logging
import signal
import sys
from typing import Optional, List, Dict, Any

from rich.console import Console

import config

console = Console()
logger = logging.getLogger("WarEraOrchestrator")


class TaskOrchestrator:
    def __init__(
        self,
        enable_market: bool = True,
        enable_sniper: bool = True,
        enable_clan_tracker: bool = True,
        enable_market_bot: bool = True,
        enable_sniper_bot: bool = True,
        enable_web: bool = True,
        web_host: str = "0.0.0.0",
        web_port: int = 8080,
    ):
        self.enable_market = enable_market
        self.enable_sniper = enable_sniper
        self.enable_clan_tracker = enable_clan_tracker
        self.enable_market_bot = enable_market_bot
        self.enable_sniper_bot = enable_sniper_bot
        self.enable_web = enable_web
        self.web_host = web_host
        self.web_port = web_port

        self.running = False
        self.market_app = None
        self.sniper_worker = None
        self.clan_tracker = None
        self.market_bot = None
        self.sniper_bot = None
        self.tasks: List[asyncio.Task] = []

    def stop(self, *args):
        """Stops all running services gracefully."""
        if not self.running:
            return
        console.print("\n[bold red]🛑 Отримано команду на зупинку комплексу WarEra Suite...[/bold red]")
        self.running = False

        if self.market_app:
            self.market_app.stop()

        if self.sniper_worker:
            try:
                self.sniper_worker.stop()
            except Exception:
                pass

        if self.clan_tracker:
            try:
                self.clan_tracker.stop()
            except Exception:
                pass

        if self.market_bot:
            try:
                self.market_bot.stop_polling()
            except Exception:
                pass

        if self.sniper_bot:
            try:
                self.sniper_bot.stop_polling()
            except Exception:
                pass

        for t in self.tasks:
            if not t.done():
                t.cancel()

    async def run(self):
        """Starts all enabled services and waits until stopped."""
        self.running = True
        loop = asyncio.get_running_loop()

        # Handle signals on Unix
        if sys.platform != "win32":
            try:
                for sig in (signal.SIGINT, signal.SIGTERM):
                    loop.add_signal_handler(sig, self.stop)
            except Exception:
                pass

        console.print("=" * 65)
        console.print(f"[bold cyan]🚀 Запуск комплексу WarEra Suite (v{getattr(config, 'APP_VERSION', '1.0')})[/bold cyan]")
        console.print("=" * 65)

        # 1. Initialize Market Scanner App
        if self.enable_market or self.enable_web:
            from equipment_scanner import EquipmentScannerApp
            self.market_app = EquipmentScannerApp()

        # 2. Start Web Dashboard if enabled
        if self.enable_web:
            try:
                import equipment_dashboard
                equipment_dashboard.start_dashboard(
                    host=self.web_host,
                    port=self.web_port,
                    app_instance=self.market_app,
                    loop=loop,
                )
                console.print(f"[green]✓ Веб-дашборд запущено на http://{self.web_host}:{self.web_port}[/green]")
            except Exception as e:
                console.print(f"[yellow]⚠️ Не вдалося запустити веб-дашборд: {e}[/yellow]")

        # 3. Market Scanner Task
        if self.enable_market and self.market_app:
            # Market scanner starts its own DB sync and internal loop
            market_coro = self.market_app.start(start_web=False)
            self.tasks.append(asyncio.create_task(market_coro, name="market_scanner"))
            console.print("[green]✓ Сервіс сканування ринку спорядження активовано.[/green]")

        # 4. Battle Sniper Worker (Purple Drop Monitoring)
        if self.enable_sniper:
            try:
                from battle_sniper_worker import get_sniper_worker
                self.sniper_worker = get_sniper_worker()
                self.tasks.append(asyncio.create_task(self.sniper_worker.start(), name="battle_sniper"))
                console.print("[green]✓ Сервіс Battle Sniper (моніторинг фіолетового дропу) активовано.[/green]")
            except Exception as e:
                console.print(f"[yellow]⚠️ Не вдалося запустити Battle Sniper: {e}[/yellow]")

        # 5. Clan Tracker Service (Damage & Roster Snapshots)
        if self.enable_clan_tracker:
            try:
                from clan_tracker import get_clan_tracker
                self.clan_tracker = get_clan_tracker()
                self.tasks.append(asyncio.create_task(self.clan_tracker.start(), name="clan_tracker"))
                console.print("[green]✓ Сервіс Clan Tracker (періодичний моніторинг клану) активовано.[/green]")
            except Exception as e:
                console.print(f"[yellow]⚠️ Не вдалося запустити Clan Tracker: {e}[/yellow]")

        # 6. Telegram Clan Sniper Bot (for clan members)
        sniper_token = getattr(config, "TELEGRAM_SNIPER_BOT_TOKEN", None)
        if self.enable_sniper_bot and sniper_token:
            try:
                from sniper_bot import SniperBotController
                self.sniper_bot = SniperBotController(token=sniper_token)
                self.tasks.append(asyncio.create_task(self.sniper_bot.start_polling(), name="sniper_bot"))
                console.print("[green]✓ Снайпер Telegram-бот для сокланівців активовано.[/green]")
            except Exception as e:
                console.print(f"[yellow]⚠️ Не вдалося запустити Sniper Bot: {e}[/yellow]")

        console.print("=" * 65 + "\n")

        # Keep running until cancelled or stopped
        try:
            while self.running:
                await asyncio.sleep(1)
        except (asyncio.CancelledError, KeyboardInterrupt):
            pass
        finally:
            self.stop()
            # Wait for tasks to terminate
            if self.tasks:
                await asyncio.gather(*[t for t in self.tasks if not t.done()], return_exceptions=True)
            console.print("[bold red]Роботу всіх сервісів WarEra Suite успішно завершено.[/bold red]")
