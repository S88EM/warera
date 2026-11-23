"""
WarEra Combat Tracker & Durability Calibrator
Tracks a player's combat run in real-time or via before/after snapshots to empirically measure:
1. Exact damage dealt
2. Hits made
3. Durability wear per hit and per 100 hits
4. Exact armor longevity formula calibration
"""

import sys
import os
import json
import time
import argparse
import asyncio
from datetime import datetime
from pathlib import Path

# Add api to path
API_DIR = Path(__file__).resolve().parent.parent / "api"
sys.path.insert(0, str(API_DIR))

from warera_client import WarEraClient

SNAPSHOT_FILE = Path(__file__).resolve().parent.parent / "scratch" / "combat_tracker_snapshot.json"


async def fetch_player_state(client: WarEraClient, identifier: str) -> dict:
    # If 24-char hex id
    if len(identifier) == 24 and all(c in "0123456789abcdefABCDEF" for c in identifier):
        user = await client.get_user_by_id(identifier)
        if user:
            return user

    # Hardcoded known users
    KNOWN_PLAYERS = {
        "m1ph": "69aae9881f0663a58d045949",
        "miph": "69aae9881f0663a58d045949",
        "luc1fer": "69af3162a583a3b5f9941e71", # or similar
    }
    if identifier.lower() in KNOWN_PLAYERS:
        uid = KNOWN_PLAYERS[identifier.lower()]
        user = await client.get_user_by_id(uid)
        if user:
            return user

    # Try resolving from sqlite db
    db_path = API_DIR / "clan_history_db.sqlite"
    if db_path.exists():
        import sqlite3
        try:
            conn = sqlite3.connect(str(db_path))
            cur = conn.cursor()
            cur.execute("SELECT user_id FROM members WHERE LOWER(username) = LOWER(?) LIMIT 1", (identifier,))
            row = cur.fetchone()
            if row:
                user = await client.get_user_by_id(row[0])
                if user:
                    return user
        except Exception:
            pass

    # Try searching military unit members
    mu_id = getattr(client, "default_mu_id", "mu-69af3162a583a3b5f9941e71")
    members = await client.get_military_unit_members(mu_id)
    for m in members:
        if m.get("username", "").lower() == identifier.lower():
            uid = m.get("userId") or m.get("user") or m.get("_id")
            if uid:
                user = await client.get_user_by_id(uid)
                if user:
                    return user

    raise ValueError(f"Player '{identifier}' not found! Спробуйте вказати точний user_id (24 символи).")



def extract_key_metrics(user: dict) -> dict:
    stats = user.get("stats", {})
    skills = user.get("skills", {})
    equipment = user.get("equipment", {})
    health_skill = skills.get("health", {})
    hunger_skill = skills.get("hunger", {})
    return {
        "user_id": user.get("_id"),
        "username": user.get("username"),
        "timestamp": time.time(),
        "time_str": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "damagesCount": stats.get("damagesCount", 0),
        "health": health_skill.get("currentBarValue", 0),
        "health_max": health_skill.get("total", 100),
        "hunger": hunger_skill.get("currentBarValue", 0),
        "hunger_max": hunger_skill.get("total", 4),
        "equipment": equipment,
        "dodge": skills.get("dodge", {}).get("totalAfterSoftCap", 0),
        "armor": skills.get("armor", {}).get("totalAfterSoftCap", 0),
        "attack_total": skills.get("attack", {}).get("total", 0),
        "crit_chance": skills.get("criticalChance", {}).get("total", 0),
        "crit_damage": skills.get("criticalDamages", {}).get("equipment", 0),
    }


async def cmd_start(identifier: str):
    client = WarEraClient()
    user = await fetch_player_state(client, identifier)
    metrics = extract_key_metrics(user)
    
    SNAPSHOT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SNAPSHOT_FILE, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)
        
    print("=" * 60)
    print(f"🎯 СТАРТОВИЙ ЗНІМОК ЗАФІКСОВАНО: {metrics['username']} (ID: {metrics['user_id']})")
    print(f"⏰ Час: {metrics['time_str']}")
    print(f"❤️ HP: {metrics['health']:.1f}/{metrics['health_max']} | 🍖 Голод: {metrics['hunger']:.1f}/{metrics['hunger_max']}")
    print(f"🔥 Початковий загальний дамаг: {metrics['damagesCount']:,}".replace(",", " "))
    print(f"🛡️ Ухилення: {metrics['dodge']}% | Броня: {metrics['armor']}%")
    print(f"⚔️ Атака: {metrics['attack_total']} | Крит: {metrics['crit_chance']}%")
    print("📦 Спорядження:")
    for slot, item_id in metrics["equipment"].items():
        print(f"   - {slot}: {item_id}")
    print("=" * 60)
    print("👉 Тепер гравець може йти в бій і зливати HP та їжу.")
    print("👉 Після завершення бою запустіть:")
    print(f"   python scripts/track_player_combat.py finish {identifier} --durability-start 100 --durability-end <залишок_%>")


async def cmd_finish(identifier: str, dur_start: float, dur_end: float, hits_override: int = None):
    if not SNAPSHOT_FILE.exists():
        print("❌ Помилка: немає збереженого стартового знімка! Запустіть спочатку команду start.")
        return

    with open(SNAPSHOT_FILE, "r", encoding="utf-8") as f:
        start_m = json.load(f)

    client = WarEraClient()
    user = await fetch_player_state(client, identifier)
    end_m = extract_key_metrics(user)

    delta_damage = end_m["damagesCount"] - start_m["damagesCount"]
    dur_loss = dur_start - dur_end
    
    # Hits estimation or override
    hits = hits_override
    if not hits:
        # If user didn't specify hits, estimate from average damage
        # Or prompt/calculate
        avg_dmg_hit = max(1, end_m["attack_total"] * 3.5) # approximate
        hits = int(delta_damage / avg_dmg_hit) if delta_damage > 0 else 0

    print("=" * 65)
    print(f"📊 РЕЗУЛЬТАТИ БОЙОВОГО ЗАБІГУ: {end_m['username']}")
    print(f"⏱️ Тривалість: {int(end_m['timestamp'] - start_m['timestamp'])} сек")
    print(f"🔥 Нанесено шкоди за бій: +{delta_damage:,} урону".replace(",", " "))
    if hits_override:
        print(f"👆 Кількість ударів (фактична): {hits_override}")
        avg_actual = delta_damage / hits_override if hits_override > 0 else 0
        print(f"💥 Середній урон за удар: {avg_actual:,.1f}".replace(",", " "))
    print("-" * 65)
    print(f"🛡️ Міцність броні:")
    print(f"   - Було: {dur_start:.1f}%")
    print(f"   - Стало: {dur_end:.1f}%")
    print(f"   - Втрачено: {dur_loss:.1f}% міцності")
    
    if hits > 0 and dur_loss > 0:
        loss_per_hit = dur_loss / hits
        loss_per_100_hits = loss_per_hit * 100
        hits_until_break = 100.0 / loss_per_hit
        print("-" * 65)
        print("🧪 РОЗРАХУНОК ЗНОСУ (КАЛІБРУВАННЯ):")
        print(f"   - Знос броні за 1 удар: {loss_per_hit:.4f}%")
        print(f"   - Знос броні за 100 ударів: {loss_per_100_hits:.2f}%")
        print(f"   - Скільки ударів живе 1 комплект броні до 0%: ~{hits_until_break:.0f} ударів!")
        
        # Comparison with old formula
        old_sets = max(1, int((hits * (1.0 - start_m["dodge"] / 100.0)) / 100.0 + 0.99))
        real_sets = max(0.01, dur_loss / 100.0)
        print("-" * 65)
        print(f"⚠️ ПОРІВНЯННЯ З КАЛЬКУЛЯТОРОМ:")
        print(f"   - Старий калькулятор нарахував би: {old_sets} компл. броні ({old_sets * 5} речей)")
        print(f"   - Реально витрачено: {real_sets:.2f} компл. (лише {dur_loss:.1f}% від 1 комплекту!)")
    print("=" * 65)


async def cmd_live(identifier: str):
    client = WarEraClient()
    user = await fetch_player_state(client, identifier)
    prev = extract_key_metrics(user)
    
    print(f"🔴 Live моніторинг для {prev['username']}. Натисніть Ctrl+C для виходу.")
    print(f"Початковий урон: {prev['damagesCount']:,}".replace(",", " "))
    
    try:
        while True:
            await asyncio.sleep(3.0)
            curr_user = await fetch_player_state(client, identifier)
            curr = extract_key_metrics(curr_user)
            delta = curr["damagesCount"] - prev["damagesCount"]
            if delta > 0:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 💥 +{delta:,} урону! Всього за сесію: +{curr['damagesCount'] - prev['damagesCount']:,}".replace(",", " "))
            prev = curr
    except KeyboardInterrupt:
        print("\nЗупинено.")


def main():
    parser = argparse.ArgumentParser(description="WarEra Combat Wear Tracker")
    subparsers = parser.add_subparsers(dest="cmd")

    p_start = subparsers.add_parser("start", help="Зафіксувати стартовий стан")
    p_start.add_argument("player", help="Нік або User ID гравця")

    p_finish = subparsers.add_parser("finish", help="Зафіксувати фінішний стан та порахувати знос")
    p_finish.add_argument("player", help="Нік або User ID гравця")
    p_finish.add_argument("--durability-start", type=float, default=100.0, help="Міцність броні на старті (%)")
    p_finish.add_argument("--durability-end", type=float, required=True, help="Міцність броні на фініші (%)")
    p_finish.add_argument("--hits", type=int, default=None, help="Фактична кількість ударів (з інтерфейсу гри)")

    p_live = subparsers.add_parser("live", help="Live-стрім оновлення урону")
    p_live.add_argument("player", help="Нік або User ID гравця")

    args = parser.parse_args()
    if args.cmd == "start":
        asyncio.run(cmd_start(args.player))
    elif args.cmd == "finish":
        asyncio.run(cmd_finish(args.player, args.durability_start, args.durability_end, args.hits))
    elif args.cmd == "live":
        asyncio.run(cmd_live(args.player))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
