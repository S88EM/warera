"""
WarEra Battle & Purple Loot CLI Monitor
Interactive terminal interface to track minimum damage required for purple drops across all active battles.
Highlights battles in the 15-20 min Sniper Window when settled damage and drop data are reliable.
"""

import asyncio
import sys
import time
from typing import Optional, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from battle_analyzer import WarEraBattleAnalyzer

console = Console()

def format_number(val: Optional[int]) -> str:
    if val is None:
        return "—"
    return f"{val:,}".replace(",", " ")

def generate_battles_table(battles: List[dict], user_nick: Optional[str] = None, sniper_only: bool = False) -> Table:
    title_suffix = " · [bold green]ТІЛЬКИ СНАЙПЕРСЬКЕ ВІКНО (15–20 хв до кінця)[/bold green]" if sniper_only else ""
    table = Table(
        title=f"⚔️ WarEra · Моніторинг фіолетових речей (Epic T4+){title_suffix}",
        title_style="bold magenta",
        header_style="bold cyan",
        border_style="blue",
        show_lines=True,
        expand=True
    )

    table.add_column("Регіон / Битва", style="white", ratio=3)
    table.add_column("Раунд & Очки", justify="center", ratio=2)
    table.add_column("⏳ Час до кінця", justify="center", ratio=2)
    table.add_column("🎯 Раунд: Мін. дамаг", justify="right", ratio=2)
    table.add_column("Предмет раунду", justify="left", ratio=3)
    table.add_column("🏆 Битва: Мін. дамаг", justify="right", ratio=2)
    table.add_column("Посилання", justify="center", ratio=1)

    for b in battles:
        reg_name = b["region"]["name"]
        b_type = "🔴 Війна" if b["type"] == "war" else "🛡️ Повстання"
        att = b["attacker"]["name"]
        dff = b["defender"]["name"]

        region_cell = f"[bold]{reg_name}[/bold]\n[dim]{b_type}: {att} vs {dff}[/dim]"

        # Round info
        r_num = b["round"]["number"]
        att_pts = b["attacker"]["roundPoints"]
        def_pts = b["defender"]["roundPoints"]
        leader = b["round"]["leadingSide"]

        if leader == "attacker":
            pts_str = f"[green]{att_pts}[/green] : [red]{def_pts}[/red]"
        elif leader == "defender":
            pts_str = f"[red]{att_pts}[/red] : [green]{def_pts}[/green]"
        else:
            pts_str = f"{att_pts} : {def_pts}"

        round_cell = f"Р#{r_num}\n{pts_str} [dim]/300[/dim]"

        # Timing & ETA
        timing = b.get("timing", {})
        eta_str = timing.get("formattedEta", "—")
        status = timing.get("status", "in_progress")

        if status == "sniper_window":
            time_cell = f"[bold green]{eta_str}[/bold green]\n[bold green]🎯 СНАЙПІНГ[/bold green]"
        elif status == "urgent":
            time_cell = f"[bold yellow]{eta_str}[/bold yellow]\n[yellow]⚡ ФІНІШ[/yellow]"
        elif status == "closing_soon":
            time_cell = f"[cyan]{eta_str}[/cyan]\n[dim]Скоро фінал[/dim]"
        else:
            time_cell = f"[dim]{eta_str}[/dim]\n[dim]Попередні дані[/dim]"

        # Round cutoff
        rc = b["roundCutoff"]
        if rc["has_purple"]:
            dmg = rc["min_damage_for_purple"]
            rank = rc["cutoff_rank"]
            item_name = rc["last_purple_item"]["name"]
            holder = rc["last_purple_player"]["username"]

            if dmg < 100_000:
                dmg_color = "bold green"
                tag = " [green]🔥 ТОП[/green]"
            elif dmg < 500_000:
                dmg_color = "bold yellow"
                tag = " [yellow]⚡[/yellow]"
            else:
                dmg_color = "bold red"
                tag = ""

            r_dmg_cell = f"[{dmg_color}]{format_number(dmg)}[/{dmg_color}]\n[dim]#{rank}[/dim]"
            r_item_cell = f"[magenta]{item_name}[/magenta]{tag}\n[dim]{holder}[/dim]"
        else:
            r_dmg_cell = "[dim]—[/dim]"
            r_item_cell = "[dim]Немає фіолу[/dim]"

        # Battle cutoff
        bc = b["battleCutoff"]
        if bc["has_purple"]:
            dmg = bc["min_damage_for_purple"]
            rank = bc["cutoff_rank"]
            item_name = bc["last_purple_item"]["name"]

            if dmg < 500_000:
                b_dmg_color = "bold green"
            elif dmg < 1_500_000:
                b_dmg_color = "bold yellow"
            else:
                b_dmg_color = "bold red"

            b_dmg_cell = f"[{b_dmg_color}]{format_number(dmg)}[/{b_dmg_color}]\n[dim]#{rank}[/dim]"
        else:
            b_dmg_cell = "[dim]—[/dim]"

        link_cell = f"[link={b['wareraUrl']}]🔗 Відкрити[/link]"

        table.add_row(
            region_cell,
            round_cell,
            time_cell,
            r_dmg_cell,
            r_item_cell,
            b_dmg_cell,
            link_cell
        )

    return table

async def run_once(user_nick: Optional[str] = None, sniper_only: bool = False):
    analyzer = WarEraBattleAnalyzer()
    try:
        with console.status("[bold green]Аналіз битв та розрахунок точного часу до закінчення раунду..."):
            battles = await analyzer.get_all_battles_intel()

        # Check for sniper window battles (15-25 min)
        sniper_battles = [b for b in battles if b.get("timing", {}).get("isSniperWindow")]

        if sniper_only:
            if sniper_battles:
                table = generate_battles_table(sniper_battles, user_nick=user_nick, sniper_only=True)
                console.print(table)
            else:
                # Find the earliest ending battle
                sorted_by_time = sorted(battles, key=lambda x: x.get("timing", {}).get("minutesLeft", 999))
                next_battle = sorted_by_time[0] if sorted_by_time else None
                next_info = f"Найближчий раунд ({next_battle['region']['name']}) завершиться через {next_battle['timing']['formattedEta']}." if next_battle else ""
                
                panel = Panel(
                    f"[yellow]⚠️ Наразі немає битв у снайперському вікні (15–25 хв до кінця раунду).[/yellow]\n"
                    f"[dim]{next_info}[/dim]\n\n"
                    f"Щоб переглянути всі активні битви з попередніми оцінками, запустіть:\n"
                    f"[bold cyan]python run.py --battles[/bold cyan]",
                    title="[bold yellow]🎯 Снайперське вікно 15–20 хв[/bold yellow]",
                    border_style="yellow"
                )
                console.print(panel)
            return

        # General mode: if there are sniper window battles, highlight them with an alert panel!
        if sniper_battles:
            panel = Panel(
                f"[bold green]🔥 ЗНАЙДЕНО {len(sniper_battles)} БИТВИ В СНАЙПЕРСЬКОМУ ВІКНІ (15–20 хв до кінця)![/bold green]\n"
                f"У цих битвах поріг шкоди майже зафіксований — найкращий час для захоплення фіолу:",
                title="[bold magenta]🎯 СНАЙПЕРСЬКА ТРИВОГА[/bold magenta]",
                border_style="green"
            )
            console.print(panel)
        else:
            sorted_by_time = sorted(battles, key=lambda x: x.get("timing", {}).get("minutesLeft", 999))
            next_battle = sorted_by_time[0] if sorted_by_time else None
            next_eta = next_battle['timing']['formattedEta'] if next_battle else "—"
            console.print(f"[dim]ℹ️ Найбільш зрілий раунд зараз: [bold]{next_battle['region']['name']}[/bold] ({next_eta} до кінця). Снайперське вікно настане ближче до фіналу.[/dim]\n")

        table = generate_battles_table(battles, user_nick=user_nick)
        console.print(table)

    finally:
        await analyzer.close()

async def run_watch(interval: int = 15, user_nick: Optional[str] = None, sniper_only: bool = False):
    analyzer = WarEraBattleAnalyzer()
    mode_text = "ТІЛЬКИ СНАЙПЕРСЬКЕ ВІКНО" if sniper_only else "ВСІ БИТВИ"
    console.print(f"[bold cyan]🚀 Живий моніторинг битв [{mode_text}] (кожні {interval} сек)... Ctrl+C для виходу.[/bold cyan]\n")
    try:
        while True:
            try:
                battles = await analyzer.get_all_battles_intel(force_refresh=True)
                console.clear()
                timestamp = time.strftime("%H:%M:%S")

                display_battles = battles
                if sniper_only:
                    display_battles = [b for b in battles if b.get("timing", {}).get("isSniperWindow")]

                console.print(f"[dim]Останнє оновлення: {timestamp} &bull; Режим: {mode_text}[/dim]")
                if not display_battles and sniper_only:
                    console.print("[yellow]Очікування настання снайперського вікна (15–20 хв до кінця раунду)...[/yellow]")
                else:
                    table = generate_battles_table(display_battles, user_nick=user_nick, sniper_only=sniper_only)
                    console.print(table)
            except Exception as e:
                console.print(f"[red]Помилка оновлення: {e}[/red]")
            await asyncio.sleep(interval)
    except KeyboardInterrupt:
        console.print("\n[yellow]Моніторинг зупинено.[/yellow]")
    finally:
        await analyzer.close()

if __name__ == "__main__":
    sniper_mode = "--sniper" in sys.argv or "--hot" in sys.argv
    if "--watch" in sys.argv:
        asyncio.run(run_watch(sniper_only=sniper_mode))
    else:
        asyncio.run(run_once(sniper_only=sniper_mode))
