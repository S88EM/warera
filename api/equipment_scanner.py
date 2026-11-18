import asyncio
import signal
import sys
from datetime import datetime
from typing import Optional, List, Dict, Any
from rich.console import Console

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import config
from warera_api import WarEraAPI
from equipment_analyzer import EquipmentAnalyzer
from notifier import Notifier
from sync_history import sync_all_history
from telegram_bot import TelegramBotController
from equipment_data import get_items_for_qualities, ALL_QUALITIES, QUALITY_TIERS

console = Console()

class EquipmentScannerApp:
    def __init__(self):
        self.pricing_mode = config.PRICING_MODE
        self.api = WarEraAPI()
        self.analyzer = EquipmentAnalyzer(
            min_discount_pct=config.EQUIPMENT_MIN_DISCOUNT,
            god_roll_threshold=config.EQUIPMENT_GOD_ROLL_THRESHOLD,
            pricing_mode=self.pricing_mode
        )
        self.notifier = Notifier()
        self.running = True
        self.is_paused = False
        self.scan_interval = config.EQUIPMENT_SCAN_INTERVAL
        self.active_qualities = list(config.EQUIPMENT_QUALITIES)
        self.equipment_list = list(config.EQUIPMENT_TO_MONITOR)
        self.last_scan_time = None
        self.cycle_count = 0
        self.total_alerts_sent = 0
        self.wake_event = asyncio.Event()
        self.tg_bot = TelegramBotController(self) if config.TELEGRAM_BOT_TOKEN else None

        # Live Web Dashboard & Ingress state
        self.deals_history = []
        self.active_deals = {}
        self.latest_market_offers = {}
        self.event_loop = None
        self.web_started = False

    def set_pricing_mode(self, mode: str) -> str:
        clean = "history" if mode.lower() in ("history", "3d", "db", "історія") else "live"
        self.pricing_mode = clean
        self.analyzer.set_pricing_mode(clean)
        mode_label = "📜 3-денна історія (база)" if clean == "history" else "⚡ Реальний час (ордери)"
        console.print(f"[bold cyan]🔄 Режим оцінки ціни перемкнено на: {mode_label}[/bold cyan]")
        self.wake_event.set()

        if clean == "history":
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(sync_all_history(days=3, items=self.equipment_list, quiet=True))
            except RuntimeError:
                pass
        return clean

    def set_scan_interval(self, seconds: int):
        self.scan_interval = max(1, int(seconds))
        console.print(f"[bold cyan]⏱ Інтервал сканування змінено на {self.scan_interval} сек.[/bold cyan]")
        self.wake_event.set()

    def set_qualities(self, qualities: list):
        clean = [q for q in ALL_QUALITIES if q in qualities]
        if not clean:
            clean = ["mythic"]
        self.active_qualities = clean
        self.equipment_list = get_items_for_qualities(self.active_qualities)
        console.print(f"[bold cyan]💎 Активні якості оновлено: {', '.join(self.active_qualities)} ({len(self.equipment_list)} предметів)[/bold cyan]")
        self.wake_event.set()
        if self.pricing_mode == "history":
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(sync_all_history(days=3, items=self.equipment_list, quiet=True))
            except RuntimeError:
                pass

    def toggle_quality(self, quality: str) -> bool:
        quality = quality.lower()
        if quality in self.active_qualities:
            if len(self.active_qualities) <= 1:
                return True
            self.active_qualities.remove(quality)
            is_enabled = False
        else:
            self.active_qualities.append(quality)
            is_enabled = True

        self.equipment_list = get_items_for_qualities(self.active_qualities)
        console.print(f"[bold cyan]💎 Якість '{quality}' {'увімкнено 🟢' if is_enabled else 'вимкнено ⚪'}. Предметів у сканері: {len(self.equipment_list)}[/bold cyan]")
        self.wake_event.set()
        if is_enabled and self.pricing_mode == "history":
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(sync_all_history(days=3, items=self.equipment_list, quiet=True))
            except RuntimeError:
                pass
        return is_enabled

    def set_god_roll_threshold(self, threshold: float):
        self.analyzer.god_roll_threshold = float(threshold)
        console.print(f"[bold cyan]🌟 Поріг якості ролу змінено на {threshold}%[/bold cyan]")

    def set_min_discount_pct(self, threshold: float):
        self.analyzer.min_discount_pct = float(threshold)
        console.print(f"[bold cyan]🎯 Поріг знижки змінено на {threshold}%[/bold cyan]")
        self.wake_event.set()

    def clear_deals(self):
        self.deals_history.clear()
        self.active_deals.clear()
        console.print("[dim]🧹 Список знайдених лотів очищено.[/dim]")

    def get_status(self) -> dict:
        best_discount = 0.0
        best_deal_item = ""
        for d in self.deals_history:
            disc = float(d.get("discount_pct", 0))
            if disc > best_discount:
                best_discount = disc
                best_deal_item = d.get("item_name", "")

        return {
            "version": config.APP_VERSION,
            "running": self.running,
            "paused": self.is_paused,
            "scan_interval": self.scan_interval,
            "pricing_mode": self.pricing_mode,
            "cycle_count": self.cycle_count,
            "total_alerts": self.total_alerts_sent,
            "active_deals_count": len(self.active_deals),
            "history_deals_count": len(self.deals_history),
            "best_discount": round(best_discount, 1),
            "best_deal_item": best_deal_item,
            "last_scan_time": self.last_scan_time or "--:--:--",
            "active_qualities": self.active_qualities,
            "monitored_items_count": len(self.equipment_list),
            "min_discount": self.analyzer.min_discount_pct,
            "god_roll_threshold": self.analyzer.god_roll_threshold,
            "telegram_enabled": bool(config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID),
        }

    def get_deals(self, limit: int = 100) -> list:
        seen_ids = set()
        merged = []
        for d in self.active_deals.values():
            if d["id"] not in seen_ids:
                seen_ids.add(d["id"])
                item = dict(d)
                item["is_active"] = True
                merged.append(item)
        for d in self.deals_history:
            if d["id"] not in seen_ids:
                seen_ids.add(d["id"])
                item = dict(d)
                item["is_active"] = False
                merged.append(item)
        return merged[:limit]

    def get_market_offers(self, item_code: Optional[str] = None):
        if item_code:
            return self.latest_market_offers.get(item_code, [])
        return {k: len(v) for k, v in self.latest_market_offers.items()}

    def resume(self):
        self.is_paused = False
        self.wake_event.set()

    def pause(self):
        self.is_paused = True
        self.wake_event.set()

    def stop(self, *args):
        console.print("\n[bold red]Отримано сигнал зупинки сканера спорядження...[/bold red]")
        self.running = False
        self.wake_event.set()
        if self.tg_bot:
            self.tg_bot.stop_polling()

    async def trigger_manual_scan(self, notify_chat_id = None):
        """Trigger an immediate scan on demand."""
        console.print("[cyan]🔍 Запуск позачергового сканування ринку (запит з Telegram)...[/cyan]")
        found = await self.run_scan_cycle(self.cycle_count + 1)
        if notify_chat_id and self.tg_bot:
            mode_label = "⚡ Реальний час (ордери)" if self.pricing_mode == "live" else "📜 3-денна історія"
            res_text = (
                f"🔍 <b>Позачергове сканування завершено!</b>\n\n"
                f"📊 <b>Режим оцінки:</b> {mode_label}\n"
                f"📦 <b>Перевірено категорій:</b> <code>{len(self.equipment_list)}</code>\n"
                f"🎯 <b>Знайдено аномалій:</b> <b>{found}</b>"
            )
            await self.tg_bot.send_message(notify_chat_id, res_text)

    async def _background_db_sync(self):
        """Silently sync new completed transactions every 15 minutes when in history mode."""
        while self.running:
            for _ in range(900):  # 15 minutes
                if not self.running:
                    return
                await asyncio.sleep(1)

            if self.pricing_mode == "history":
                try:
                    new_tx = await sync_all_history(days=3, items=self.equipment_list, quiet=True)
                    if new_tx > 0:
                        now_str = datetime.now().strftime("%H:%M:%S")
                        console.print(f"[dim][{now_str}] 🔄 [Авто-оновлення бази історії]: додано {new_tx} нових угод.[/dim]")
                except Exception:
                    pass

    async def _background_clan_snapshot(self):
        """Silently snapshot clan damage every 15 minutes and at 02:00 rollover."""
        while self.running:
            try:
                from clan_analyzer import WarEraClanAnalyzer
                analyzer = WarEraClanAnalyzer()
                await analyzer.analyze_clan()
            except Exception:
                pass

            for _ in range(900):  # 15 minutes
                if not self.running:
                    return
                await asyncio.sleep(1)

    async def run_scan_cycle(self, cycle_num: int) -> int:
        now_str = datetime.now().strftime("%H:%M:%S")
        self.last_scan_time = now_str
        self.cycle_count = cycle_num
        items = self.equipment_list or config.EQUIPMENT_TO_MONITOR

        async def fetch_item(item_code):
            try:
                offers = await self.api.get_equipment_offers(item_code, limit=12)
                return item_code, offers, None
            except Exception as e:
                return item_code, None, str(e)

        tasks = [fetch_item(code) for code in items]
        results = await asyncio.gather(*tasks)

        found = 0
        new_active_deals = {}

        for item_code, offers, err in results:
            if err or not offers:
                continue

            self.latest_market_offers[item_code] = offers
            opps = self.analyzer.analyze_offers(item_code, offers)
            for opp in opps:
                deal_dict = {
                    "id": opp.offer_id,
                    "item_code": opp.item_code,
                    "item_name": opp.item_name,
                    "rarity": opp.rarity,
                    "tier": opp.tier,
                    "price": opp.price,
                    "reference_price": opp.reference_price,
                    "discount_pct": round(opp.discount_pct, 1),
                    "potential_profit": round(opp.potential_profit, 2),
                    "skills": opp.skills,
                    "roll_quality": round(opp.roll_quality, 1),
                    "is_god_roll": opp.roll_quality >= self.analyzer.god_roll_threshold,
                    "state": opp.state,
                    "notes": opp.notes,
                    "opp_type": opp.opp_type,
                    "url": f"https://app.warera.io/market/equipments?item={opp.item_code}",
                    "timestamp": now_str,
                    "time_iso": datetime.now().isoformat(),
                }
                new_active_deals[opp.offer_id] = deal_dict

                if not self.analyzer.is_offer_seen(opp.offer_id):
                    self.analyzer.mark_offer_seen(opp.offer_id)
                    found += 1
                    self.deals_history.insert(0, deal_dict)
                    if len(self.deals_history) > 200:
                        self.deals_history.pop()
                    await self.notifier.notify_equipment(opp)

        self.active_deals = new_active_deals
        self.total_alerts_sent += found
        status_msg = f"[dim][{now_str}][/dim] Спорядження #{cycle_num} ({len(items)} кат.):"
        if found > 0:
            status_msg += f" [bold green]Знайдено аномалій: {found}![/bold green]"
        else:
            status_msg += " [dim]Аномалій не виявлено.[/dim]"
        console.print(status_msg)
        return found

    async def start(self, start_web: bool = True):
        self.event_loop = asyncio.get_running_loop()

        # Start Web Dashboard (Ingress & local browser)
        if start_web and getattr(config, "ENABLE_WEB_DASHBOARD", True) and not self.web_started:
            try:
                import equipment_dashboard
                equipment_dashboard.start_dashboard(
                    host=getattr(config, "WEB_DASHBOARD_HOST", "0.0.0.0"),
                    port=getattr(config, "WEB_DASHBOARD_PORT", 8080),
                    app_instance=self,
                    loop=self.event_loop
                )
                self.web_started = True
            except Exception as e:
                console.print(f"[yellow]⚠️ Не вдалося запустити Web Dashboard: {e}[/yellow]")

        console.print("\n" + "=" * 65)
        console.print(f"[bold cyan]   WARERA EQUIPMENT SCANNER v{config.APP_VERSION}[/bold cyan]")
        console.print("=" * 65)
        
        mode_text = "[bold green]⚡ Реальний час (відкриті ордери ринку)[/bold green]" if self.pricing_mode == "live" else "[bold yellow]📜 3-денна історія угод (SQLite база)[/bold yellow]"
        tg_status = f"[green]Увімкнено (особисті повідомлення, {len(config.TELEGRAM_CHAT_IDS)} чат)[/green]" if config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_IDS else "[yellow]Вимкнено (лише консоль)[/yellow]"
        console.print(f"🔄 Режим оцінки ціни: {mode_text}")
        console.print(f"⏱ Інтервал сканування: [bold]{self.scan_interval} сек[/bold]")
        console.print(f"🎯 Поріг знижки/демпінгу: [bold]{config.EQUIPMENT_MIN_DISCOUNT}%[/bold]")
        console.print(f"🌟 Поріг топ-ролу (God Roll): [bold]{config.EQUIPMENT_GOD_ROLL_THRESHOLD}% якості[/bold]")
        console.print(f"📱 Telegram сповіщення: {tg_status}")
        
        items_str = ", ".join(config.EQUIPMENT_TO_MONITOR)
        console.print(f"⚔️ Категорії ({len(config.EQUIPMENT_TO_MONITOR)}): [bold]{items_str}[/bold]")
        console.print("=" * 65 + "\n")

        # Initial check for history mode
        if self.pricing_mode == "history":
            console.print("[dim]🔄 Перевірка та оновлення бази 3-денної історії цін...[/dim]")
            try:
                new_tx = await sync_all_history(days=3, quiet=True)
                console.print(f"[green]✓ Базу оновлено ({new_tx} свіжих угод додано).[/green]\n")
            except Exception as e:
                console.print(f"[yellow]⚠️ Не вдалося синхронізувати нові угоди ({e}), використовуємо наявну базу.[/yellow]\n")

        console.print("[bold green]Сканер спорядження запущено! Натисніть Ctrl+C для зупинки.[/bold green]\n")

        if sys.platform != "win32":
            try:
                loop = asyncio.get_running_loop()
                for sig in (signal.SIGINT, signal.SIGTERM):
                    loop.add_signal_handler(sig, self.stop)
            except Exception:
                pass

        # Start background sync task (active when in history mode)
        sync_task = asyncio.create_task(self._background_db_sync())

        # Start periodic clan damage tracker (snapshots every 15 min & 02:00 rollover)
        clan_task = asyncio.create_task(self._background_clan_snapshot())

        # Start background battle sniper worker (polls every 50s, pushes 15-20 min purple drops)
        sniper_task = None
        try:
            from battle_sniper_worker import get_sniper_worker
            sniper_task = asyncio.create_task(get_sniper_worker().start())
            console.print("[green]✓ Снайпер битв активовано (фоновий моніторинг фіолетового дропу за 15-20 хв до кінця раунду).[/green]\n")
        except Exception as e:
            console.print(f"[yellow]⚠️ Не вдалося запустити фоновий снайпер битв: {e}[/yellow]\n")

        # Start dedicated Sniper Telegram Bot controller (for clan members & battle sniper)
        sniper_tg_task = None
        sniper_token = getattr(config, "TELEGRAM_SNIPER_BOT_TOKEN", None)
        if sniper_token:
            try:
                from sniper_bot import SniperBotController
                sniper_bot = SniperBotController(token=sniper_token)
                sniper_tg_task = asyncio.create_task(sniper_bot.start_polling())
                console.print("[green]✓ Снайпер Telegram-бот активовано (окремий публічний бот для сокланівців).[/green]\n")
            except Exception as e:
                console.print(f"[yellow]⚠️ Не вдалося запустити Sniper Bot: {e}[/yellow]\n")

        # Start Telegram bot controller (Private Market Bot)
        tg_task = None
        if self.tg_bot:
            tg_task = asyncio.create_task(self.tg_bot.start_polling())
            console.print("[green]✓ Приватний ринковий Telegram-бот активовано (тільки для власника).[/green]\n")

        cycle = 0
        try:
            while self.running:
                if not self.is_paused:
                    cycle += 1
                    await self.run_scan_cycle(cycle)
                    for _ in range(self.scan_interval):
                        if not self.running or self.wake_event.is_set():
                            break
                        await asyncio.sleep(1)
                    self.wake_event.clear()
                else:
                    try:
                        await asyncio.wait_for(self.wake_event.wait(), timeout=2.0)
                    except asyncio.TimeoutError:
                        pass
                    self.wake_event.clear()
        except (asyncio.CancelledError, KeyboardInterrupt):
            pass
        finally:
            self.running = False
            sync_task.cancel()
            clan_task.cancel()
            if sniper_task:
                try:
                    from battle_sniper_worker import get_sniper_worker
                    get_sniper_worker().stop()
                    sniper_task.cancel()
                except Exception:
                    pass
            if tg_task:
                tg_task.cancel()
            if sniper_tg_task:
                sniper_tg_task.cancel()
            await self.notifier.close()
            await self.api.close()
            console.print("[bold red]Роботу сканера спорядження завершено.[/bold red]")

if __name__ == "__main__":
    app = EquipmentScannerApp()
    try:
        asyncio.run(app.start())
    except KeyboardInterrupt:
        pass
