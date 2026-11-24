"""
Shared combat constants, consumable specifications, and helper utilities
used by both CombatDamageCalculator and GearOptimizer.
"""

from typing import Dict, Any, Optional

# Consumable food specs: % of character max HP healed per 1 hunger unit
FOOD_SPECS: Dict[str, Dict[str, Any]] = {
    "cookedFish": {"name": "Смажена риба", "hp_pct": 0.20, "default_price": 7.74, "icon": "🐟", "food_multiplier": 3},
    "steak": {"name": "Стейк", "hp_pct": 0.15, "default_price": 3.03, "icon": "🥩", "food_multiplier": 2},
    "fish": {"name": "Сира риба", "hp_pct": 0.12, "default_price": 3.93, "icon": "🎣", "food_multiplier": 1.5},
    "bread": {"name": "Хліб", "hp_pct": 0.10, "default_price": 1.40, "icon": "🍞", "food_multiplier": 1},
}

# Scrap returned when item breaks (1/3 of craft requirement)
# Source: Warera Build Tool (intel.warera.wiki/builder) & Game Crafting Tables
SCRAP_RECOVERY_BY_TIER: Dict[int, int] = {
    0: 0,
    1: 2,    # Grey / Knife (craft: 6 scrap / 3)
    2: 6,    # Green / Gun (craft: 18 scrap / 3)
    3: 18,   # Blue / Rifle / T3 (craft: 54 scrap / 3)
    4: 54,   # Purple / Sniper / T4 (craft: 162 scrap / 3)
    5: 162,  # Gold / Tank / T5 (craft: 486 scrap / 3)
    6: 486,  # Red / Jet / T6 (craft: 1458 scrap / 3)
}

# Ammo specs: bonus attack % and live orderbook benchmark prices
AMMO_SPECS: Dict[str, Dict[str, Any]] = {
    "lightAmmo": {
        "name": "Зелені (Легкі)",
        "code": "lightAmmo",
        "icon": "🟢",
        "badge": "🟢 Зелені (+10%)",
        "bonus_pct": 10.0,
        "default_price": 0.20,
        "tier_affinity": [3, 4],
        "desc": "Найбільш економічні для Снайперки Т4 та щоденних боїв",
    },
    "ammo": {
        "name": "Сині (Стандартні)",
        "code": "ammo",
        "icon": "🔵",
        "badge": "🔵 Сині (+20%)",
        "bonus_pct": 20.0,
        "default_price": 0.83,
        "tier_affinity": [4.5, 5],
        "desc": "Оптимальні для Танка Т5 та збільшеного дамагу",
    },
    "heavyAmmo": {
        "name": "Фіолетові (Важкі)",
        "code": "heavyAmmo",
        "icon": "🟣",
        "badge": "🟣 Фіолетові (+40%)",
        "bonus_pct": 40.0,
        "default_price": 3.07,
        "tier_affinity": [6],
        "desc": "Максимальний урон для Літака Т6 та рекордних планок (7M-10M+)",
    },
}

# Fallback default prices for all gear items if market cache is empty
DEFAULT_MARKET_PRICES: Dict[str, float] = {
    "knife": 2.0, "helmet1": 2.0, "chest1": 2.0, "pants1": 2.0, "boots1": 2.0, "gloves1": 2.0,
    "gun": 7.0, "helmet2": 7.0, "chest2": 7.0, "pants2": 7.0, "boots2": 7.0, "gloves2": 7.0,
    "rifle": 13.6, "helmet3": 13.6, "chest3": 13.6, "pants3": 13.6, "boots3": 13.6, "gloves3": 13.6,
    "sniper": 42.0, "helmet4": 47.2, "chest4": 43.0, "pants4": 43.9, "boots4": 40.9, "gloves4": 42.4,
    "tank": 144.0, "helmet5": 122.0, "chest5": 122.0, "pants5": 122.5, "boots5": 160.0, "gloves5": 155.0,
    "jet": 446.0, "helmet6": 370.0, "chest6": 368.0, "pants6": 370.0, "boots6": 431.0, "gloves6": 415.0,
}

WEAPON_TIERS: Dict[int, Optional[str]] = {
    0: None,
    1: "knife",
    2: "gun",
    3: "rifle",
    4: "sniper",
    5: "tank",
    6: "jet",
}

TIER_NAMES: Dict[int, str] = {
    0: "Без спорядження",
    1: "Т1 Звичайний (Сірий)",
    2: "Т2 Незвичайний (Зелений)",
    3: "Т3 Поліпшений (Синій)",
    4: "Т4 Елітний (Фіолетовий)",
    5: "Т5 Легендарний (Золотий)",
    6: "Т6 Міфічний (Червоний)",
}


def merge_live_consumables(
    consumable_prices: Dict[str, Any],
    live_consumables: Optional[Dict[str, float]],
) -> Dict[str, Any]:
    """Merges positive live consumable market prices into the base price dict."""
    if live_consumables and isinstance(live_consumables, dict):
        for k, v in live_consumables.items():
            try:
                vf = float(v)
                if vf > 0:
                    consumable_prices[k] = round(vf, 3)
            except (ValueError, TypeError):
                pass
    return consumable_prices


def extract_player_combat_profile(
    player_member: Dict[str, Any],
    custom_rank_bonus: Optional[float] = None,
    custom_prestige: Optional[int] = None,
) -> Dict[str, Any]:
    """Extracts normalized player stats, pools, rank multiplier, and prestige SPs."""
    uname = player_member.get("username", "Боєць")
    lvl = int(player_member.get("level", 1))
    skills = player_member.get("skills") or {}

    if custom_prestige is not None:
        prestige_val = max(0, int(custom_prestige))
    else:
        prestige_val = int(
            player_member.get("prestige")
            or player_member.get("leveling", {}).get("prestige", 0)
        )

    if custom_rank_bonus is not None:
        rank_bonus_pct = max(0.0, float(custom_rank_bonus))
    else:
        rank_bonus_pct = float(
            player_member.get("rank_bonus_pct")
            or skills.get("attack", {}).get("militaryRankPercent", 0.0)
        )

    health_max = float(player_member.get("health_max") or skills.get("health", {}).get("total", 150))
    health_curr = float(player_member.get("health_curr") or skills.get("health", {}).get("currentBarValue", health_max))
    health_regen = float(player_member.get("health_regen") or skills.get("health", {}).get("hourlyBarRegen", 15.0))

    hunger_max = float(player_member.get("hunger_max") or skills.get("hunger", {}).get("total", 7))
    hunger_curr = float(player_member.get("hunger_curr") or skills.get("hunger", {}).get("currentBarValue", hunger_max))
    hunger_regen = float(player_member.get("hunger_regen") or skills.get("hunger", {}).get("hourlyBarRegen", 0.7))

    return {
        "username": uname,
        "level": lvl,
        "skills": skills,
        "prestige": prestige_val,
        "total_skill_points": lvl * 4 + prestige_val,
        "rank_bonus_pct": rank_bonus_pct,
        "rank_mult": 1.0 + (rank_bonus_pct / 100.0),
        "health_max": health_max,
        "health_curr": health_curr,
        "health_regen": health_regen,
        "hunger_max": hunger_max,
        "hunger_curr": hunger_curr,
        "hunger_regen": hunger_regen,
    }
