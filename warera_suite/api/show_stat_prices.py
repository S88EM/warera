import sys
import argparse
import asyncio
from datetime import datetime
from typing import Optional, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import config
from price_history_db import MarketHistoryDB
from equipment_data import EQUIPMENT_METADATA, calculate_roll_quality
from sync_history import sync_all_history
from warera_api import WarEraAPI

console = Console()

def display_equipment_stat_table(db: MarketHistoryDB, item_code: str, days: int = 3):
    meta = EQUIPMENT_METADATA.get(item_code, {})
    name = meta.get("name", item_code)
    rarity = meta.get("rarity", "unknown")
    item_type = meta.get("type", "equipment")

    summary = db.get_stat_price_summary(item_code, days=days)
    if not summary:
        console.print(f"[yellow]⚠️ Немає даних транзакцій за останні {days} дні для {name} (`{item_code}`)[/yellow]")
        return

    table = Table(
        title=f"📊 [bold cyan]{name}[/bold cyan] (`{item_code}`) — 3-денна історія цін за характеристиками (Рідкість: {rarity})",
        header_style="bold magenta",
        border_style="cyan"
    )

    table.add_column("Характеристика (Стат)", justify="center", style="bold")
    table.add_column("Якість ролу", justify="center")
    table.add_column("К-сть угод", justify="right")
    table.add_column("Медіана", justify="right", style="bold green")
    table.add_column("Середня", justify="right")
    table.add_column("Мін. ціна", justify="right", style="dim")
    table.add_column("Макс. ціна", justify="right", style="dim")

    stat_name = "stat"
    if item_type == "boots":
        stat_name = "dodge"
    elif item_type in ("chest", "pants"):
        stat_name = "armor"
    elif item_type == "helmet":
        stat_name = "criticalDamages"
    elif item_type == "gloves":
        stat_name = "precision"
    elif item_type == "weapon":
        stat_name = "attack"

    sorted_stats = sorted(summary.keys())
    for stat_val in sorted_stats:
        data = summary[stat_val]
        quality = calculate_roll_quality(item_code, {stat_name: stat_val})
        q_color = "bold green" if quality >= 80 else ("yellow" if quality >= 40 else "white")
        
        stat_label = f"{stat_name} {int(stat_val)}"
        if stat_val == sorted_stats[-1]:
            stat_label += " [bold gold1](MAX)[/bold gold1]"
        elif stat_val == sorted_stats[0]:
            stat_label += " [dim](MIN)[/dim]"

        table.add_row(
            stat_label,
            f"[{q_color}]{quality:.0f}%[/{q_color}]",
            str(data["count"]),
            f"{data['median']:.2f}",
            f"{data['mean']:.2f}",
            f"{data['min']:.2f}",
            f"{data['max']:.2f}",
        )

    console.print(table)
    console.print()

async def check_live_market(item_code: str, days: int = 3):
    api = WarEraAPI()
    db = MarketHistoryDB()
    meta = EQUIPMENT_METADATA.get(item_code, {})
    name = meta.get("name", item_code)

    console.print(f"\n🔍 [bold cyan]Отримання актуальних пропозицій з ринку для {name} (`{item_code}`)...[/bold cyan]")
    try:
        offers = await api.get_equipment_offers(item_code, limit=12)
    except Exception as e:
        console.print(f"[bold red]Помилка запиту до ринку: {e}[/bold red]")
        await api.close()
        return

    await api.close()

    if not offers:
        console.print("[yellow]На ринку зараз немає активних пропозицій для цього предмета.[/yellow]\n")
        return

    table = Table(
        title=f"🛒 Актуальні лоти на ринку: [bold cyan]{name}[/bold cyan] (Порівняння з 3-денною медіаною)",
        header_style="bold magenta",
        border_style="green"
    )

    table.add_column("#", justify="center", style="dim")
    table.add_column("Ціна лота", justify="right", style="bold")
    table.add_column("Характеристики", justify="left")
    table.add_column("Якість", justify="center")
    table.add_column("Міцність", justify="center")
    table.add_column("3-денний орієнтир", justify="right", style="bold cyan")
    table.add_column("Різниця", justify="right")
    table.add_column("Вердикт", justify="center", style="bold")

    for idx, off in enumerate(offers, 1):
        price = float(off.get("price", 0.0))
        item_obj = off.get("item", {})
        skills = item_obj.get("skills", {})
        state = item_obj.get("state", 100)
        quality = calculate_roll_quality(item_code, skills)

        eval_res = db.get_stat_evaluation(item_code, skills, current_price=price, days=days)
        skills_str = ", ".join(f"{k}: {v}" for k, v in skills.items())

        if eval_res:
            exp_price = f"{eval_res['expected_price']:.2f}"
            diff_pct = eval_res['discount_pct']
            diff_str = f"+{diff_pct:.1f}%" if diff_pct > 0 else f"{diff_pct:.1f}%"
            diff_color = "bold green" if diff_pct >= 5.0 else ("red" if diff_pct <= -5.0 else "white")
            verdict = eval_res['verdict']
        else:
            exp_price = "-"
            diff_str = "-"
            diff_color = "white"
            verdict = "❓ Немає даних"

        q_color = "bold green" if quality >= 80 else ("yellow" if quality >= 40 else "white")

        table.add_row(
            str(idx),
            f"{price:.2f}",
            skills_str,
            f"[{q_color}]{quality:.0f}%[/{q_color}]",
            f"{state}/100",
            exp_price,
            f"[{diff_color}]{diff_str}[/{diff_color}]",
            verdict,
        )

    console.print(table)
    console.print()

def main():
    parser = argparse.ArgumentParser(description="WarEra 3-Day Equipment & Weapon Stat Price Analyzer")
    parser.add_argument("item", nargs="?", default=None, help="Item code to inspect (e.g. boots4, sniper, tank, helmet4)")
    parser.add_argument("-s", "--sync", action="store_true", help="Sync latest 3-day transactions before showing")
    parser.add_argument("-c", "--check", action="store_true", help="Fetch live market offers and check if they are cheap")
    parser.add_argument("-d", "--days", type=int, default=3, help="Number of days for historical baseline (default: 3)")
    args = parser.parse_args()

    if args.sync:
        items_to_sync = [args.item] if args.item else config.EQUIPMENT_TO_MONITOR
        asyncio.run(sync_all_history(days=args.days, items=items_to_sync))

    db = MarketHistoryDB()

    if args.check:
        items_to_check = [args.item] if args.item else config.EQUIPMENT_TO_MONITOR
        for item_code in items_to_check:
            asyncio.run(check_live_market(item_code, days=args.days))
        return

    if args.item:
        display_equipment_stat_table(db, args.item, days=args.days)
    else:
        console.print(Panel(
            "[bold cyan]ЗВІТ: 3-ДЕННІ МЕДІАННІ ЦІНИ СПОРЯДЖЕННЯ ТА ЗБРОЇ ЗА СТАТАМИ[/bold cyan]\n"
            "[dim]Ціни розраховані на основі реальних завершених угод на ринку WarEra.[/dim]",
            border_style="cyan"
        ))
        
        # Show key armor and weapons
        priority_items = [
            "boots4", "boots5", "boots6",
            "helmet4", "helmet5", "helmet6",
            "chest4", "chest5", "chest6",
            "pants4", "pants5", "pants6",
            "gloves4", "gloves5", "gloves6",
            "sniper", "rifle", "tank", "jet"
        ]
        
        for item_code in priority_items:
            display_equipment_stat_table(db, item_code, days=args.days)

if __name__ == "__main__":
    main()
