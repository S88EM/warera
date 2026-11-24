"""
WarEra Combat Damage & Gear Strategy Optimizer.
Calculates the most economical equipment, ammo, and food strategy for any clan member to reach a target damage goal:
- T3 (Rare/Blue), T4 (Epic/Purple), Hybrid T4/T5, T5 (Legendary/Yellow), T6 (Mythic/Red).
- Real durability burn: 1 weapon per 100 hits (no dodge protection); armor protected by dodge (lasts 200-250+ hits).
- Ammo mechanics: 🟢 Light (+10%), 🔵 Standard (+20%), 🟣 Heavy (+40%).
- Food & Hunger capacity limits per pill session.
- Live market prices & direct buy links from market_cheapest_cache.json.
- Identifies the lowest total gold cost option (Best Value).
"""

import math
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from market_cache import load_market_cheapest_cache
from equipment_data import EQUIPMENT_METADATA, QUALITY_TIERS, get_item_image_url, get_item_icon, RARITY_CONFIG

logger = logging.getLogger("WarEraCombatCalculator")

# Consumable food specs: % of character max HP healed per 1 hunger unit
FOOD_SPECS = {
    "cookedFish": {"name": "Смажена риба", "hp_pct": 0.20, "default_price": 7.74, "icon": "🐟"},
    "steak": {"name": "Стейк", "hp_pct": 0.15, "default_price": 3.03, "icon": "🥩"},
    "fish": {"name": "Сира риба", "hp_pct": 0.12, "default_price": 3.93, "icon": "🎣"},
    "bread": {"name": "Хліб", "hp_pct": 0.10, "default_price": 1.40, "icon": "🍞"},
}

# Scrap returned when item breaks (1/3 of craft requirement)
# Source: Warera Build Tool (intel.warera.wiki/builder) & Game Crafting Tables
SCRAP_RECOVERY_BY_TIER = {
    0: 0,
    1: 2,    # Grey / Knife (craft: 6 scrap / 3)
    2: 6,    # Green / Gun (craft: 18 scrap / 3)
    3: 18,   # Blue / Rifle / T3 (craft: 54 scrap / 3)
    4: 54,   # Purple / Sniper / T4 (craft: 162 scrap / 3)
    5: 162,  # Gold / Tank / T5 (craft: 486 scrap / 3)
    6: 486,  # Red / Jet / T6 (craft: 1458 scrap / 3)
}

# Ammo specs: bonus attack % and live orderbook benchmark prices
AMMO_SPECS = {
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
        "default_price": 0.825,
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

# Standard baseline roll values by tier for combat simulation
TIER_STAT_BENCHMARKS = {
    3: { # Rare / Blue
        "name": "Поліпшений (Т3)",
        "quality": "rare",
        "badge": "🔵 Т3 Синій (Економ)",
        "weapon_code": "rifle",
        "weapon_name": "Гвинтівка III",
        "weapon_atk": 80.0,
        "weapon_crit_chance": 13.0,
        "helmet_code": "helmet3",
        "helmet_name": "Шолом III",
        "helmet_crit_dmg": 40.0,
        "chest_code": "chest3",
        "chest_name": "Броня III",
        "chest_armor": 13.0,
        "pants_code": "pants3",
        "pants_name": "Штани III",
        "pants_armor": 13.0,
        "boots_code": "boots3",
        "boots_name": "Чоботи III",
        "boots_dodge": 13.0,
        "gloves_code": "gloves3",
        "gloves_name": "Рукавиці III",
        "gloves_precision": 13.0,
    },
    4: { # Epic / Purple
        "name": "Елітний (Т4)",
        "quality": "epic",
        "badge": "🟣 Т4 Фіолетовий (Стандарт)",
        "weapon_code": "sniper",
        "weapon_name": "Снайперка IV",
        "weapon_atk": 120.0,
        "weapon_crit_chance": 18.0,
        "helmet_code": "helmet4",
        "helmet_name": "Шолом IV",
        "helmet_crit_dmg": 80.0,
        "chest_code": "chest4",
        "chest_name": "Броня IV",
        "chest_armor": 25.0,
        "pants_code": "pants4",
        "pants_name": "Штани IV",
        "pants_armor": 25.0,
        "boots_code": "boots4",
        "boots_name": "Чоботи IV",
        "boots_dodge": 23.0,
        "gloves_code": "gloves4",
        "gloves_name": "Рукавиці IV",
        "gloves_precision": 23.0,
    },
    5: { # Legendary / Yellow
        "name": "Легендарний (Т5)",
        "quality": "legendary",
        "badge": "🟡 Т5 Легендарний (Топ)",
        "weapon_code": "tank",
        "weapon_name": "Танк V",
        "weapon_atk": 155.0,
        "weapon_crit_chance": 30.0,
        "helmet_code": "helmet5",
        "helmet_name": "Шолом V",
        "helmet_crit_dmg": 100.0,
        "chest_code": "chest5",
        "chest_name": "Броня V",
        "chest_armor": 43.0,
        "pants_code": "pants5",
        "pants_name": "Штани V",
        "pants_armor": 43.0,
        "boots_code": "boots5",
        "boots_name": "Чоботи V",
        "boots_dodge": 35.0,
        "gloves_code": "gloves5",
        "gloves_name": "Рукавиці V",
        "gloves_precision": 35.0,
    },
    6: { # Mythic / Red
        "name": "Міфічний (Т6)",
        "quality": "mythic",
        "badge": "🔴 Т6 Міфічний (Максимум)",
        "weapon_code": "jet",
        "weapon_name": "Винищувач VI",
        "weapon_atk": 260.0,
        "weapon_crit_chance": 45.0,
        "helmet_code": "helmet6",
        "helmet_name": "Шолом VI",
        "helmet_crit_dmg": 135.0,
        "chest_code": "chest6",
        "chest_name": "Броня VI",
        "chest_armor": 63.0,
        "pants_code": "pants6",
        "pants_name": "Штани VI",
        "pants_armor": 63.0,
        "boots_code": "boots6",
        "boots_name": "Чоботи VI",
        "boots_dodge": 55.0,
        "gloves_code": "gloves6",
        "gloves_name": "Рукавиці VI",
        "gloves_precision": 55.0,
    },
}

# Fallback default prices for all gear items if market cache is empty
DEFAULT_MARKET_PRICES = {
    "rifle": 13.6, "helmet3": 13.6, "chest3": 13.6, "pants3": 13.6, "boots3": 13.6, "gloves3": 13.6,
    "sniper": 42.0, "helmet4": 47.2, "chest4": 43.0, "pants4": 43.9, "boots4": 40.9, "gloves4": 42.4,
    "tank": 144.0, "helmet5": 122.0, "chest5": 122.0, "pants5": 122.5, "boots5": 160.0, "gloves5": 155.0,
    "jet": 446.0, "helmet6": 370.0, "chest6": 368.0, "pants6": 370.0, "boots6": 431.0, "gloves6": 415.0,
}


class CombatDamageCalculator:
    def __init__(self, market_app=None):
        self.market_app = market_app

    def calculate_all_strategies(
        self,
        player_member: Dict[str, Any],
        target_damage: float = 2_500_000.0,
        selected_ammo: str = "auto",
        custom_food_key: Optional[str] = None,
        battle_bonus: float = 50.0,
        custom_rank_bonus: Optional[float] = None,
        custom_prestige: Optional[int] = None,
        live_consumables: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        Calculates all viable combat strategies (Current, T3, T4, Hybrid, T5, T6)
        taking into account:
        1. 100 hits per weapon burn.
        2. Armor durability loss attenuated by dodge chance (1 set = 200-250+ hits).
        3. Ammo type and consumption (1 ammo per hit).
        4. Food units vs character hunger capacity per session.
        5. Live market prices for consumables (cases, food, ammo, pill).
        6. Dynamic battle bonus multiplier (e.g. +50%, +84%, +100%).
        7. Unbounded Military Rank bonus (>37.5%).
        8. Character Prestige (+1 SP / prestige point).
        """
        battle_bonus_val = max(0.0, float(battle_bonus if battle_bonus is not None else 50.0))
        battle_mult = 1.0 + (battle_bonus_val / 100.0)
        market_cache = load_market_cheapest_cache()
        cached_items = market_cache.get("items", {})
        consumable_prices = dict(market_cache.get("consumables", {}))

        # Merge live market prices if provided
        if live_consumables and isinstance(live_consumables, dict):
            for k, v in live_consumables.items():
                try:
                    vf = float(v)
                    if vf > 0:
                        consumable_prices[k] = round(vf, 3)
                except (ValueError, TypeError):
                    pass

        uname = player_member.get("username", "Боєць")
        lvl = player_member.get("level", 1)
        skills = player_member.get("skills") or {}

        # 1. Health & Regeneration
        health_max = float(player_member.get("health_max") or skills.get("health", {}).get("total", 150))
        health_curr = float(player_member.get("health_curr") or skills.get("health", {}).get("currentBarValue", health_max))
        health_regen = float(player_member.get("health_regen") or skills.get("health", {}).get("hourlyBarRegen", 15.0))

        # 2. Hunger & Regeneration
        hunger_max = float(player_member.get("hunger_max") or skills.get("hunger", {}).get("total", 7))
        hunger_curr = float(player_member.get("hunger_curr") or skills.get("hunger", {}).get("currentBarValue", hunger_max))
        hunger_regen = float(player_member.get("hunger_regen") or skills.get("hunger", {}).get("hourlyBarRegen", 0.7))

        # 3. Base Character Stats with unbounded Military Rank & Prestige
        base_atk = float(player_member.get("base_attack") or skills.get("attack", {}).get("value", 100))
        atk_overflow = float(skills.get("attack", {}).get("overflow", 0))

        if custom_rank_bonus is not None and float(custom_rank_bonus) >= 0:
            rank_bonus_pct = float(custom_rank_bonus)
        else:
            rank_bonus_pct = float(player_member.get("rank_bonus_pct") or skills.get("attack", {}).get("militaryRankPercent", 0.0))
        rank_mult = 1.0 + (rank_bonus_pct / 100.0)

        # Prestige: +1 SP per prestige point. If custom prestige exceeds base, add +5 attack per point
        member_prestige = int(player_member.get("prestige", 0) or 0)
        curr_prestige = int(custom_prestige) if custom_prestige is not None else member_prestige
        if curr_prestige > member_prestige:
            base_atk += (curr_prestige - member_prestige) * 5.0

        # 4. Pill Status and Session Duration
        pill_status = player_member.get("pill_status", "READY")
        pill_remaining_hours = float(player_member.get("pill_remaining_hours") or 0.0)

        if pill_status == "ACTIVE" and pill_remaining_hours > 0.1:
            session_hours = min(8.0, pill_remaining_hours)
            pill_cost = 0.0
            has_active_pill = True
        else:
            session_hours = 8.0
            pill_cost = float(consumable_prices.get("cocain", 34.80))
            has_active_pill = False

        # Natural resource recovery over the pill session duration
        natural_hp_pool = health_curr + (session_hours * health_regen)
        available_hunger = hunger_curr + (session_hours * hunger_regen)

        # 5. Damage deficit today
        today_damage = float(player_member.get("today_damage") or 0.0)
        deficit_damage = max(0.0, target_damage - today_damage)

        # 6. Player Loot Chance & Economy Benchmarks (Athena & Intel Builder engine)
        loot_skill_lvl = float(skills.get("loot", {}).get("level", 0))
        loot_skill_total = float(skills.get("loot", {}).get("total", 0))
        loot_chance_pct = float(player_member.get("loot_chance") or (loot_skill_total if loot_skill_total > 0 else (5.0 + 2.0 * loot_skill_lvl)))
        loot_chance_ratio = loot_chance_pct / 100.0

        scrap_price = float(consumable_prices.get("scrap", 0.26))
        case1_price = float(consumable_prices.get("case1", 3.89))
        case2_price = float(consumable_prices.get("case2", 27.19))

        # Current player combat parameters from analyzer
        curr_avg_dmg = float(player_member.get("avg_dmg_per_hit") or 1000.0)
        curr_hp_cost = float(player_member.get("hp_cost_per_hit") or 1.5)
        curr_dodge_pct = float(player_member.get("effective_dodge") or 50.0)

        # Player equipped gear stats for comparison
        equipped_weapon_atk = float(player_member.get("equipped_weapon_atk") or skills.get("attack", {}).get("weapon", 0))
        equipped_armor = float(player_member.get("equipped_armor") or skills.get("armor", {}).get("equipment", 0))
        equipped_dodge = float(player_member.get("equipped_dodge") or skills.get("dodge", {}).get("equipment", 0))

        has_equipped_weapon = equipped_weapon_atk > 0
        has_equipped_armor = (equipped_armor > 0 or equipped_dodge > 0)
        is_player_naked = (not has_equipped_weapon) and (not has_equipped_armor)

        # Helper: format recommended roll stats for market search
        def format_target_stats(code: str, slot: str) -> tuple[str, str]:
            meta = EQUIPMENT_METADATA.get(code, {})
            ranges = meta.get("ranges", {})
            if slot == "weapon":
                atk_r = ranges.get("attack", [70, 90])
                crit_r = ranges.get("criticalChance", [10, 15])
                rec_atk = int(atk_r[0] + (atk_r[1] - atk_r[0]) * 0.65)
                rec_crit = int(crit_r[0] + (crit_r[1] - crit_r[0]) * 0.65)
                return f"🗡 {rec_atk}+ Атака • 🎯 {rec_crit}%+ Крит", f"🗡 {rec_atk} 🎯 {rec_crit}%"
            elif slot == "helmet":
                cd_r = ranges.get("criticalDamages", [40, 80])
                rec_cd = int(cd_r[0] + (cd_r[1] - cd_r[0]) * 0.65)
                return f"💥 +{rec_cd}%+ Крит-урон", f"💥 +{rec_cd}%"
            elif slot in ("chest", "pants"):
                arm_r = ranges.get("armor", [15, 25])
                rec_arm = int(arm_r[0] + (arm_r[1] - arm_r[0]) * 0.60)
                return f"🛡 {rec_arm}–{arm_r[1]} Броня", f"🛡 {rec_arm}"
            elif slot == "boots":
                d_r = ranges.get("dodge", [15, 25])
                rec_d = int(d_r[0] + (d_r[1] - d_r[0]) * 0.65)
                return f"👟 +{rec_d}%+ Ухилення", f"👟 +{rec_d}%"
            elif slot == "gloves":
                p_r = ranges.get("precision", [15, 25])
                rec_p = int(p_r[0] + (p_r[1] - p_r[0]) * 0.65)
                return f"🎯 +{rec_p}%+ Влучність", f"🎯 +{rec_p}%"
            return "", ""

        # Helper: get price and item details from cache or fallback
        def get_item_quote(code: str) -> Dict[str, Any]:
            meta = EQUIPMENT_METADATA.get(code, {})
            c_info = cached_items.get(code, {})
            offers = c_info.get("offers", [])
            cheapest = offers[0] if offers else None
            price = cheapest.get("price") if cheapest else c_info.get("cheapest_price")
            if not price or float(price) <= 0:
                price = DEFAULT_MARKET_PRICES.get(code, 40.0)
            slot_type = meta.get("type", "weapon")
            target_stats, stat_badge = format_target_stats(code, slot_type)
            return {
                "item_code": code,
                "name": meta.get("name", code),
                "slot": slot_type,
                "tier": meta.get("tier", 4),
                "rarity": meta.get("rarity", "epic"),
                "image_url": get_item_image_url(code),
                "icon": get_item_icon(code),
                "target_stats": target_stats,
                "stat_badge": stat_badge,
                "price": round(float(price), 2),
                "seller": cheapest.get("seller", "") if cheapest else "",
                "roll_quality": cheapest.get("roll_quality", 0) if cheapest else 0,
                "url": f"https://app.warera.io/market/equipments?item={code}",
            }

        # Helper to simulate combat hits and damage for any tier combination using Athena & Intel Builder physics
        def simulate_tier_combat(
            w_atk: float, w_crit_ch: float,
            h_crit_dmg: float,
            c_armor: float, p_armor: float,
            b_dodge: float, g_prec: float,
            ammo_bonus_pct: float
        ) -> tuple[float, float, float, float, float, float]:
            # 1. Effective Armor & Dodge with exact Diminishing Returns (K = 40)
            curr_armor_stat = float(skills.get("armor", {}).get("value", 0))
            curr_dodge_stat = float(skills.get("dodge", {}).get("value", 0))

            eff_gear_armor = c_armor + p_armor
            eff_gear_dodge = b_dodge

            total_raw_armor = curr_armor_stat + eff_gear_armor
            total_raw_dodge = curr_dodge_stat + eff_gear_dodge

            armor_reduction = (total_raw_armor / (total_raw_armor + 40.0)) if total_raw_armor > 0 else 0.0
            dodge_fraction = (total_raw_dodge / (total_raw_dodge + 40.0)) if total_raw_dodge > 0 else 0.0

            # Exact HP Cost per hit: 10 * (1 - armor_red) * (1 - dodge_fraction)
            hp_cost = max(0.20, 10.0 * (1.0 - armor_reduction) * (1.0 - dodge_fraction))

            # Durability lifetime: 100 absorbed hits -> 100 * (1 + dodge / 40)
            hits_per_armor_set = max(100.0, 100.0 * (1.0 + total_raw_dodge / 40.0))

            eff_dodge_pct = round(dodge_fraction * 100.0, 1)
            eff_armor_pct = round(armor_reduction * 100.0, 1)

            # 2. Precision & Stat Overflow (+4 Attack per 1% Precision > 100%)
            curr_prec = float(skills.get("precision", {}).get("value", 75))
            raw_prec = curr_prec + g_prec

            if raw_prec > 100.0:
                prec_overflow = raw_prec - 100.0
                prec_bonus_atk = prec_overflow * 4.0
                eff_prec_ratio = 1.0
            else:
                prec_bonus_atk = 0.0
                eff_prec_ratio = max(0.10, raw_prec / 100.0)

            # 3. Critical Chance, Critical Damage & Stat Overflow (+4% Crit Dmg per 1% Crit Chance > 100%)
            curr_crit_ch = float(skills.get("criticalChance", {}).get("value", 10))
            curr_crit_dmg = float(skills.get("criticalDamages", {}).get("value", 100))

            raw_crit_ch = curr_crit_ch + w_crit_ch
            raw_crit_dmg = curr_crit_dmg + h_crit_dmg

            if raw_crit_ch > 100.0:
                crit_overflow = raw_crit_ch - 100.0
                crit_bonus_dmg = crit_overflow * 4.0
                eff_crit_ch_ratio = 1.0
            else:
                crit_bonus_dmg = 0.0
                eff_crit_ch_ratio = max(0.0, raw_crit_ch / 100.0)

            tot_crit_dmg_pct = raw_crit_dmg + crit_bonus_dmg
            crit_mult_val = tot_crit_dmg_pct / 100.0

            # 4. Attack with Weapon, Ammo, Pill (1.60), Military Rank
            eff_w_atk = w_atk
            ammo_mult = 1.0 + (ammo_bonus_pct / 100.0)
            pill_mult = 1.60
            sim_atk = (base_atk + eff_w_atk + atk_overflow + prec_bonus_atk) * rank_mult * ammo_mult * pill_mult

            # 5. Expected Damage per hit (Hit: 100% + crit, Miss: 50% damage) + Dynamic Battle Bonus
            hit_dmg = sim_atk * (1.0 + eff_crit_ch_ratio * crit_mult_val)
            miss_dmg = sim_atk * 0.5
            avg_base_dmg = eff_prec_ratio * hit_dmg + (1.0 - eff_prec_ratio) * miss_dmg
            avg_dmg = avg_base_dmg * battle_mult

            return (
                round(avg_dmg, 1),
                round(hp_cost, 2),
                eff_dodge_pct,
                eff_armor_pct,
                round(hits_per_armor_set, 1),
                round(eff_prec_ratio, 3)
            )

        # Resolve Ammo Selection: prioritize Green Light ammo (0.20 ₴) for maximum economy
        def get_best_ammo_for_tier(tier_num: float) -> str:
            if selected_ammo in AMMO_SPECS:
                return selected_ammo
            # Only use heavy/standard ammo if damage goal requires it to stay within hunger limits
            if deficit_damage >= 7_500_000:
                return "heavyAmmo" # 🟣 Heavy (+40%) only for extreme 7.5M-10M+
            elif deficit_damage >= 4_500_000 or tier_num >= 5.5:
                return "ammo" # 🔵 Standard (+20%) for large 4.5M+
            return "lightAmmo" # 🟢 Light (+10%) for everyday economy (≤4.5M)

        # Smart Sweet Spot configuration adapts dynamically to damage deficit:
        if deficit_damage <= 1_000_000:
            # Small goal (≤1M e.g. 500k): T3 Blue gear is the budget king!
            ss_slots = {
                "name": "Золота середина (Т3 Синій економ)",
                "weapon_code": "rifle", "weapon_name": "Гвинтівка III", "weapon_atk": 83.0, "weapon_crit_chance": 13.0,
                "helmet_code": "helmet3", "helmet_name": "Шолом III", "helmet_crit_dmg": 43.0,
                "chest_code": "chest3", "chest_name": "Броня III", "chest_armor": 13.0,
                "pants_code": "pants3", "pants_name": "Штани III", "pants_armor": 13.0,
                "boots_code": "boots3", "boots_name": "Чоботи III (Ухил)", "boots_dodge": 13.0,
                "gloves_code": "gloves3", "gloves_name": "Рукавиці III", "gloves_precision": 13.0,
            }
            ss_tier = 3.2
        elif deficit_damage <= 4_500_000:
            # Standard goal (1M-4.5M): Top-Efficiency Hybrid (Sniper IV + T5 Boots Dodge + T5 Gloves Prec Overflow)
            ss_slots = {
                "name": "Золота середина (Топ-Окупність: Снайперка IV + Т5 Чоботи)",
                "weapon_code": "sniper", "weapon_name": "Снайперка IV", "weapon_atk": 120.0, "weapon_crit_chance": 18.0,
                "helmet_code": "helmet4", "helmet_name": "Шолом IV", "helmet_crit_dmg": 80.0,
                "chest_code": "chest4", "chest_name": "Броня IV", "chest_armor": 26.0,
                "pants_code": "pants4", "pants_name": "Штани IV", "pants_armor": 26.0,
                "boots_code": "boots5", "boots_name": "Чоботи V (Ухил 35%)", "boots_dodge": 35.0,
                "gloves_code": "gloves5", "gloves_name": "Рукавиці V (Влучність 35%)", "gloves_precision": 35.0,
            }
            ss_tier = 4.4
        else:
            # Heavy goal (>4.5M): T5 Tank + T5 defense
            ss_slots = {
                "name": "Золота середина (Т5 Легендарний)",
                "weapon_code": "tank", "weapon_name": "Танк V", "weapon_atk": 155.0, "weapon_crit_chance": 30.0,
                "helmet_code": "helmet5", "helmet_name": "Шолом V", "helmet_crit_dmg": 100.0,
                "chest_code": "chest5", "chest_name": "Броня V", "chest_armor": 43.0,
                "pants_code": "pants5", "pants_name": "Штани V", "pants_armor": 43.0,
                "boots_code": "boots5", "boots_name": "Чоботи V (Ухил)", "boots_dodge": 35.0,
                "gloves_code": "gloves5", "gloves_name": "Рукавиці V", "gloves_precision": 35.0,
            }
            ss_tier = 4.8

        # Strategies definition
        strategies_config = [
            {
                "key": "current_gear",
                "label": "🛡 Поточний шмот (Економ)" if has_equipped_weapon else "🛡 Поточний шмот (Без зброї)",
                "tier_name": "Поточний",
                "tier_num": 0,
                "is_current": True,
                "sim_dmg": curr_avg_dmg,
                "sim_hp_cost": curr_hp_cost,
                "eff_dodge": curr_dodge_pct,
            },
            {
                "key": "smart_sweet_spot",
                "label": "⭐ Золота середина (Макс. окупність)",
                "tier_name": "Золота середина",
                "tier_num": ss_tier,
                "is_current": False,
                "slots_def": ss_slots,
            },
            {
                "key": "hybrid_t5_dodge",
                "label": "⚡ Топ-Гібрид (Т5 Чоботи+Рукавиці, Т4 Снайперка)",
                "tier_name": "Топ-Гібрид Т4/Т5",
                "tier_num": 4.4,
                "is_current": False,
                "slots_def": {
                    "name": "Топ-Гібрид (Т5 Чоботи+Рукавиці)",
                    "weapon_code": "sniper", "weapon_name": "Снайперка IV", "weapon_atk": 120.0, "weapon_crit_chance": 18.0,
                    "helmet_code": "helmet4", "helmet_name": "Шолом IV", "helmet_crit_dmg": 80.0,
                    "chest_code": "chest4", "chest_name": "Броня IV", "chest_armor": 26.0,
                    "pants_code": "pants4", "pants_name": "Штани IV", "pants_armor": 26.0,
                    "boots_code": "boots5", "boots_name": "Чоботи V (Ухил 35%)", "boots_dodge": 35.0,
                    "gloves_code": "gloves5", "gloves_name": "Рукавиці V (Влучність 35%)", "gloves_precision": 35.0,
                },
            },
            {
                "key": "t3_rare",
                "label": "🔵 Т3 Синій Економ (Рідкісний)",
                "tier_name": "Т3 Синій",
                "tier_num": 3,
                "is_current": False,
                "slots_def": TIER_STAT_BENCHMARKS[3],
            },
            {
                "key": "t4_epic",
                "label": "🟣 Т4 Фіолетовий (Елітний)",
                "tier_name": "Т4 Фіолетовий",
                "tier_num": 4,
                "is_current": False,
                "slots_def": TIER_STAT_BENCHMARKS[4],
            },
            {
                "key": "hybrid_t5_defense",
                "label": "👑 Гібрид (Т5 Броня+Штани, решта Т4)",
                "tier_name": "Гібрид Т4/Т5",
                "tier_num": 4.5,
                "is_current": False,
                "slots_def": {
                    "name": "Гібрид Т4/Т5",
                    "weapon_code": "sniper", "weapon_name": "Снайперка IV", "weapon_atk": 120.0, "weapon_crit_chance": 18.0,
                    "helmet_code": "helmet4", "helmet_name": "Шолом IV", "helmet_crit_dmg": 80.0,
                    "chest_code": "chest5", "chest_name": "Броня V (Легенда)", "chest_armor": 43.0,
                    "pants_code": "pants5", "pants_name": "Штани V (Легенда)", "pants_armor": 43.0,
                    "boots_code": "boots4", "boots_name": "Чоботи IV", "boots_dodge": 23.0,
                    "gloves_code": "gloves4", "gloves_name": "Рукавиці IV", "gloves_precision": 23.0,
                },
            },
            {
                "key": "t5_legendary",
                "label": "🟡 Т5 Легендарний (Топ-урон)",
                "tier_name": "Т5 Легендарний",
                "tier_num": 5,
                "is_current": False,
                "slots_def": TIER_STAT_BENCHMARKS[5],
            },
            {
                "key": "t6_mythic",
                "label": "🔴 Т6 Міфічний (Максимум)",
                "tier_name": "Т6 Міфічний",
                "tier_num": 6,
                "is_current": False,
                "slots_def": TIER_STAT_BENCHMARKS[6],
            },
        ]

        evaluated_options = []

        for strat in strategies_config:
            t_num = strat["tier_num"]
            if selected_ammo in AMMO_SPECS:
                candidate_ammos = [selected_ammo]
            else:
                candidate_ammos = ["lightAmmo"]
                if deficit_damage >= 1_500_000 or t_num >= 4.0:
                    candidate_ammos.append("ammo")
                if deficit_damage >= 6_000_000:
                    candidate_ammos.append("heavyAmmo")

            for ammo_key in candidate_ammos:
                ammo_spec = AMMO_SPECS[ammo_key]
                ammo_price = float(consumable_prices.get(ammo_key, ammo_spec["default_price"]))
                if strat.get("is_current"):
                    if has_equipped_weapon:
                        curr_armor_stat = float(skills.get("armor", {}).get("value", 0)) + equipped_armor
                        curr_dodge_stat = float(skills.get("dodge", {}).get("value", 0)) + equipped_dodge
                        armor_reduction = (curr_armor_stat / (curr_armor_stat + 40.0)) if curr_armor_stat > 0 else 0.0
                        dodge_fraction = (curr_dodge_stat / (curr_dodge_stat + 40.0)) if curr_dodge_stat > 0 else 0.0
                        sim_hp_cost = max(0.20, 10.0 * (1.0 - armor_reduction) * (1.0 - dodge_fraction))
                        hits_per_armor_set = max(100.0, 100.0 * (1.0 + curr_dodge_stat / 40.0))
                        eff_dodge = round(dodge_fraction * 100.0, 1)
                        eff_armor = round(armor_reduction * 100.0, 1)

                        curr_prec_stat = float(skills.get("precision", {}).get("value", 75)) + float(skills.get("precision", {}).get("equipment", 0))
                        if curr_prec_stat > 100.0:
                            p_over = curr_prec_stat - 100.0
                            p_atk_bonus = p_over * 4.0
                            eff_prec_ratio = 1.0
                        else:
                            p_atk_bonus = 0.0
                            eff_prec_ratio = max(0.10, curr_prec_stat / 100.0)

                        curr_crit_ch = float(skills.get("criticalChance", {}).get("value", 10)) + float(skills.get("criticalChance", {}).get("weapon", 0))
                        curr_crit_dmg = float(skills.get("criticalDamages", {}).get("value", 100)) + float(skills.get("criticalDamages", {}).get("equipment", 0))
                        if curr_crit_ch > 100.0:
                            c_over = curr_crit_ch - 100.0
                            tot_c_dmg = curr_crit_dmg + (c_over * 4.0)
                            eff_crit_ch_ratio = 1.0
                        else:
                            tot_c_dmg = curr_crit_dmg
                            eff_crit_ch_ratio = max(0.0, curr_crit_ch / 100.0)

                        crit_mult_val = tot_c_dmg / 100.0
                        ammo_mult = 1.0 + (ammo_spec["bonus_pct"] / 100.0)
                        pill_mult = 1.60
                        sim_atk = (base_atk + equipped_weapon_atk + atk_overflow + p_atk_bonus) * rank_mult * ammo_mult * pill_mult
                        hit_dmg = sim_atk * (1.0 + eff_crit_ch_ratio * crit_mult_val)
                        miss_dmg = sim_atk * 0.5
                        sim_dmg = round((eff_prec_ratio * hit_dmg + (1.0 - eff_prec_ratio) * miss_dmg) * battle_mult, 1)
                    else:
                        sim_dmg = 0.0
                        sim_hp_cost = 6.5
                        eff_dodge = float(skills.get("dodge", {}).get("totalAfterSoftCap", 0))
                        eff_armor = float(skills.get("armor", {}).get("totalAfterSoftCap", 0)) or 24.0
                        eff_prec_ratio = 0.5
                        hits_per_armor_set = 100.0
                else:
                    s_def = strat["slots_def"]
                    sim_dmg, sim_hp_cost, eff_dodge, eff_armor, hits_per_armor_set, eff_prec_ratio = simulate_tier_combat(
                        s_def["weapon_atk"], s_def["weapon_crit_chance"],
                        s_def["helmet_crit_dmg"],
                        s_def["chest_armor"], s_def["pants_armor"],
                        s_def["boots_dodge"], s_def["gloves_precision"],
                        ammo_spec["bonus_pct"]
                    )
                # Evaluate with food options (Steaks vs Fish)
                food_options = ["steak", "cookedFish"] if not custom_food_key else [custom_food_key]
    
                for f_key in food_options:
                    f_spec = FOOD_SPECS[f_key]
                    f_price = float(consumable_prices.get(f_key, f_spec["default_price"]))
    
                    # Calculate hits needed
                    if deficit_damage <= 0:
                        hits_needed = 0
                        total_hp_needed = 0.0
                        hp_deficit = 0.0
                        food_units_needed = 0
                    else:
                        hits_needed = math.ceil(deficit_damage / max(1.0, sim_dmg))
                        total_hp_needed = hits_needed * sim_hp_cost
                        hp_deficit = max(0.0, total_hp_needed - natural_hp_pool)
    
                        hp_per_food_unit = health_max * f_spec["hp_pct"]
                        food_units_needed = math.ceil(hp_deficit / hp_per_food_unit) if hp_per_food_unit > 0 else 0
    
                    food_cost = round(food_units_needed * f_price, 2)
                    hunger_usage_pct = round((food_units_needed / available_hunger) * 100.0, 1) if available_hunger > 0 else 100.0
    
                    # Hunger capacity check
                    if strat.get("is_current") and not has_equipped_weapon:
                        can_reach = False
                        reach_status = "no_weapon"
                        reach_badge = "⚠️ Без зброї"
                        reach_note = "На бійцеві немає зброї! Для бою потрібно екіпірувати або придбати зброю."
                    elif food_units_needed <= available_hunger:
                        can_reach = True
                        reach_status = "ok"
                        reach_badge = "✅ Досяжно"
                        reach_note = "Повністю вміщається в поточну сесію таблетки"
                    elif food_units_needed <= (available_hunger + 2.0):
                        # Soft cap: exceeds slightly, reachable with a brief wait
                        can_reach = True
                        reach_status = "soft_cap"
                        extra_h = round((food_units_needed - available_hunger) / max(0.4, hunger_regen), 1)
                        reach_badge = f"⏳ +{extra_h}г регену"
                        reach_note = f"Потребує +{extra_h}г регену голоду, але зберігає золото!"
                    else:
                        can_reach = False
                        reach_status = "exceeded"
                        reach_badge = f"❌ Ліміт голоду ({hunger_usage_pct}%)"
                        reach_note = "Перевищує ліміт голоду за сесію"
    
                    # 1. Weapon durability burn (1 weapon per 100 hits, no dodge protection)
                    weapons_burned = max(1, math.ceil(hits_needed / 100.0)) if hits_needed > 0 else 1
    
                    # 2. Armor & Equipment durability burn (attenuated by dodge absorption!)
                    # Exact game physics (Athena & Intel Builder): 1 set absorbs 100 non-dodged hits.
                    # hits_per_armor_set = 100 * (1 + dodge / 40)
                    armor_sets_burned = max(1, math.ceil(hits_needed / max(1.0, hits_per_armor_set))) if hits_needed > 0 else 1
    
                    # 3. Ammo consumption (1 ammo per hit)
                    ammo_units_needed = hits_needed
                    ammo_cost = round(ammo_units_needed * ammo_price, 2)
    
                    # 4. 8-Slot RPG Build Visualizer & Shopping list
                    build_slots = []
                    shopping_items = []
                    gear_cost = 0.0
    
                    if strat.get("is_current"):
                        # Slot 1: Weapon
                        if has_equipped_weapon:
                            w_crit = float(skills.get("criticalChance", {}).get("weapon", 0))
                            # Accurate detection: Sniper vs Tank vs Jet based on crit chance & attack
                            if w_crit >= 38 or equipped_weapon_atk >= 230:
                                w_tier = 6
                                w_code = "jet"
                                w_name = "Винищувач VI"
                                w_rarity = "mythic"
                            elif w_crit >= 25 or equipped_weapon_atk >= 165:
                                w_tier = 5
                                w_code = "tank"
                                w_name = "Танк V"
                                w_rarity = "legendary"
                            elif w_crit >= 15 or equipped_weapon_atk >= 95:
                                w_tier = 4
                                w_code = "sniper"
                                w_name = "Снайперка IV"
                                w_rarity = "epic"
                            elif w_crit >= 10 or equipped_weapon_atk >= 65:
                                w_tier = 3
                                w_code = "rifle"
                                w_name = "Гвинтівка III"
                                w_rarity = "rare"
                            else:
                                w_tier = 2
                                w_code = "gun"
                                w_name = "Пістолет II"
                                w_rarity = "uncommon"
    
                            # Formatted stats showing BOTH attack and critical chance
                            if w_crit > 0:
                                w_stats_str = f"🗡 {int(equipped_weapon_atk)} Атака • 🎯 {int(w_crit)}% Крит"
                                w_stat_badge = f"🗡 {int(equipped_weapon_atk)} 🎯 {int(w_crit)}%"
                            else:
                                w_stats_str = f"🗡 {int(equipped_weapon_atk)} Атака"
                                w_stat_badge = f"🗡 {int(equipped_weapon_atk)}"
    
                            build_slots.append({
                                "slot": "weapon",
                                "slot_title": "Зброя",
                                "item_code": w_code,
                                "name": w_name,
                                "tier": w_tier,
                                "rarity": w_rarity,
                                "image_url": get_item_image_url(w_code),
                                "icon": get_item_icon(w_code),
                                "target_stats": w_stats_str,
                                "stat_badge": w_stat_badge,
                                "qty_needed": 0,
                                "qty_required_total": 1,
                                "unit_price": 0.0,
                                "total_price": 0.0,
                                "already_equipped": True,
                                "eco_status": "already_equipped",
                                "eco_note": "✅ Вже надіто на бійцеві (0 ₴)",
                                "url": "https://app.warera.io/market/equipments",
                            })
                        else:
                            build_slots.append({
                                "slot": "weapon",
                                "slot_title": "Зброя",
                                "item_code": "knife",
                                "name": "⚠️ Зброю не одягнено",
                                "tier": 0,
                                "rarity": "common",
                                "image_url": get_item_image_url("knife"),
                                "icon": "⚠️",
                                "target_stats": "Немає зброї",
                                "stat_badge": "0 АТК",
                                "qty_needed": 1,
                                "qty_required_total": 1,
                                "unit_price": 0.0,
                                "total_price": 0.0,
                                "already_equipped": False,
                                "eco_status": "upgrade_needed",
                                "eco_note": "Одягніть зброю в грі або оберіть сет із покупкою!",
                                "url": "https://app.warera.io/market/equipments",
                            })
    
                        # Slot 2: Helmet
                        h_cd = float(skills.get("criticalDamages", {}).get("equipment", 0))
                        h_tier = 5 if h_cd >= 90 else (4 if h_cd >= 60 else (3 if h_cd > 0 else 0))
                        h_code = f"helmet{h_tier}" if h_tier in (3, 4, 5, 6) else "helmet4"
                        h_roman = ('I','II','III','IV','V','VI')[h_tier-1] if 1 <= h_tier <= 6 else "IV"
                        build_slots.append({
                            "slot": "helmet",
                            "slot_title": "Шолом",
                            "item_code": h_code,
                            "name": f"Шолом {h_roman}",
                            "tier": h_tier if h_tier > 0 else 4,
                            "rarity": "legendary" if h_tier == 5 else ("epic" if h_tier == 4 else ("rare" if h_tier == 3 else "common")),
                            "image_url": get_item_image_url(h_code),
                            "icon": get_item_icon(h_code),
                            "target_stats": f"💥 +{int(h_cd)}% Крит-урон" if h_cd > 0 else "Базовий захист",
                            "stat_badge": f"💥 +{int(h_cd)}%" if h_cd > 0 else "0%",
                            "qty_needed": 0,
                            "qty_required_total": 1,
                            "unit_price": 0.0,
                            "total_price": 0.0,
                            "already_equipped": (h_cd > 0 or has_equipped_armor),
                            "eco_status": "already_equipped",
                            "eco_note": "✅ Вже надіто на бійцеві (0 ₴)",
                            "url": f"https://app.warera.io/market/equipments?item={h_code}",
                        })
    
                        # Slot 3: Gloves
                        g_pr = float(skills.get("precision", {}).get("equipment", 0))
                        g_tier = 5 if g_pr >= 30 else (4 if g_pr >= 20 else (3 if g_pr > 0 else 0))
                        g_code = f"gloves{g_tier}" if g_tier in (3, 4, 5, 6) else "gloves4"
                        g_roman = ('I','II','III','IV','V','VI')[g_tier-1] if 1 <= g_tier <= 6 else "IV"
                        build_slots.append({
                            "slot": "gloves",
                            "slot_title": "Рукавиці",
                            "item_code": g_code,
                            "name": f"Рукавиці {g_roman}",
                            "tier": g_tier if g_tier > 0 else 4,
                            "rarity": "legendary" if g_tier == 5 else ("epic" if g_tier == 4 else ("rare" if g_tier == 3 else "common")),
                            "image_url": get_item_image_url(g_code),
                            "icon": get_item_icon(g_code),
                            "target_stats": f"🎯 +{int(g_pr)}% Влучність" if g_pr > 0 else "Базові рукавиці",
                            "stat_badge": f"🎯 +{int(g_pr)}%" if g_pr > 0 else "0%",
                            "qty_needed": 0,
                            "qty_required_total": 1,
                            "unit_price": 0.0,
                            "total_price": 0.0,
                            "already_equipped": (g_pr > 0 or has_equipped_armor),
                            "eco_status": "already_equipped",
                            "eco_note": "✅ Вже надіто на бійцеві (0 ₴)",
                            "url": f"https://app.warera.io/market/equipments?item={g_code}",
                        })
    
                        # Slot 4: Chest
                        c_arm = int(equipped_armor / 2.0)
                        c_tier = 5 if c_arm >= 35 else (4 if c_arm >= 20 else (3 if c_arm > 0 else 0))
                        c_code = f"chest{c_tier}" if c_tier in (3, 4, 5, 6) else "chest4"
                        c_roman = ('I','II','III','IV','V','VI')[c_tier-1] if 1 <= c_tier <= 6 else "IV"
                        build_slots.append({
                            "slot": "chest",
                            "slot_title": "Броня",
                            "item_code": c_code,
                            "name": f"Броня {c_roman}",
                            "tier": c_tier if c_tier > 0 else 4,
                            "rarity": "legendary" if c_tier == 5 else ("epic" if c_tier == 4 else ("rare" if c_tier == 3 else "common")),
                            "image_url": get_item_image_url(c_code),
                            "icon": get_item_icon(c_code),
                            "target_stats": f"🛡 {c_arm} Броня" if c_arm > 0 else "Немає броні",
                            "stat_badge": f"🛡 {c_arm}" if c_arm > 0 else "0",
                            "qty_needed": 0,
                            "qty_required_total": 1,
                            "unit_price": 0.0,
                            "total_price": 0.0,
                            "already_equipped": (c_arm > 0),
                            "eco_status": "already_equipped",
                            "eco_note": "✅ Вже надіто на бійцеві (0 ₴)",
                            "url": f"https://app.warera.io/market/equipments?item={c_code}",
                        })
    
                        # Slot 5: Pants
                        p_arm = int(equipped_armor / 2.0)
                        p_tier = 5 if p_arm >= 35 else (4 if p_arm >= 20 else (3 if p_arm > 0 else 0))
                        p_code = f"pants{p_tier}" if p_tier in (3, 4, 5, 6) else "pants4"
                        p_roman = ('I','II','III','IV','V','VI')[p_tier-1] if 1 <= p_tier <= 6 else "IV"
                        build_slots.append({
                            "slot": "pants",
                            "slot_title": "Штани",
                            "item_code": p_code,
                            "name": f"Штани {p_roman}",
                            "tier": p_tier if p_tier > 0 else 4,
                            "rarity": "legendary" if p_tier == 5 else ("epic" if p_tier == 4 else ("rare" if p_tier == 3 else "common")),
                            "image_url": get_item_image_url(p_code),
                            "icon": get_item_icon(p_code),
                            "target_stats": f"🛡 {p_arm} Броня" if p_arm > 0 else "Немає штанів",
                            "stat_badge": f"🛡 {p_arm}" if p_arm > 0 else "0",
                            "qty_needed": 0,
                            "qty_required_total": 1,
                            "unit_price": 0.0,
                            "total_price": 0.0,
                            "already_equipped": (p_arm > 0),
                            "eco_status": "already_equipped",
                            "eco_note": "✅ Вже надіто на бійцеві (0 ₴)",
                            "url": f"https://app.warera.io/market/equipments?item={p_code}",
                        })
    
                        # Slot 6: Boots
                        b_d = int(equipped_dodge)
                        b_tier = 5 if b_d >= 30 else (4 if b_d >= 20 else (3 if b_d > 0 else 0))
                        b_code = f"boots{b_tier}" if b_tier in (3, 4, 5, 6) else "boots4"
                        b_roman = ('I','II','III','IV','V','VI')[b_tier-1] if 1 <= b_tier <= 6 else "IV"
                        build_slots.append({
                            "slot": "boots",
                            "slot_title": "Чоботи",
                            "item_code": b_code,
                            "name": f"Чоботи {b_roman}",
                            "tier": b_tier if b_tier > 0 else 4,
                            "rarity": "legendary" if b_tier == 5 else ("epic" if b_tier == 4 else ("rare" if b_tier == 3 else "common")),
                            "image_url": get_item_image_url(b_code),
                            "icon": get_item_icon(b_code),
                            "target_stats": f"👟 +{b_d}% Ухилення" if b_d > 0 else "Базові чоботи",
                            "stat_badge": f"👟 +{b_d}%" if b_d > 0 else "0%",
                            "qty_needed": 0,
                            "qty_required_total": 1,
                            "unit_price": 0.0,
                            "total_price": 0.0,
                            "already_equipped": (b_d > 0),
                            "eco_status": "already_equipped",
                            "eco_note": "✅ Вже надіто на бійцеві (0 ₴)",
                            "url": f"https://app.warera.io/market/equipments?item={b_code}",
                        })
                    else:
                        s_def = strat["slots_def"]
                        slots_to_quote = [
                            ("weapon", "Зброя", s_def["weapon_code"], weapons_burned, s_def["weapon_atk"]),
                            ("helmet", "Шолом", s_def["helmet_code"], armor_sets_burned, s_def["helmet_crit_dmg"]),
                            ("gloves", "Рукавиці", s_def["gloves_code"], armor_sets_burned, s_def["gloves_precision"]),
                            ("chest", "Броня", s_def["chest_code"], armor_sets_burned, s_def["chest_armor"]),
                            ("pants", "Штани", s_def["pants_code"], armor_sets_burned, s_def["pants_armor"]),
                            ("boots", "Чоботи", s_def["boots_code"], armor_sets_burned, s_def["boots_dodge"]),
                        ]
    
                        for slot_name, slot_title, item_code, qty_needed, tier_stat_val in slots_to_quote:
                            quote = get_item_quote(item_code)
                            unit_p = quote["price"]
    
                            # Determine overkill / upgrade advice compared to player's current gear
                            player_equipped_val = 0.0
                            if slot_name == "weapon":
                                player_equipped_val = equipped_weapon_atk
                            elif slot_name in ("chest", "pants"):
                                player_equipped_val = equipped_armor / 2.0
                            elif slot_name == "boots":
                                player_equipped_val = equipped_dodge
                            elif slot_name == "helmet":
                                player_equipped_val = float(skills.get("criticalDamages", {}).get("equipment", 0))
                            elif slot_name == "gloves":
                                player_equipped_val = float(skills.get("precision", {}).get("equipment", 0))
    
                            # Smart deduction: If slot is already covered by equipped gear (>= 85% of tier benchmark),
                            # the first item is already in hand! Only buy replacements if durability runs out.
                            if player_equipped_val >= (tier_stat_val * 0.85):
                                qty_to_buy = max(0, qty_needed - 1)
                                if qty_to_buy == 0:
                                    total_item_p = 0.0
                                    eco_status = "already_equipped"
                                    eco_note = f"✅ Вже на тобі ({quote['name']}). Докупка не потрібна (0 ₴)!"
                                else:
                                    total_item_p = round(unit_p * qty_to_buy, 2)
                                    eco_status = "wear_replacement"
                                    eco_note = f"🛡 1-й на тобі, докупити +{qty_to_buy} шт на зміну при зносі."
                            else:
                                qty_to_buy = qty_needed
                                total_item_p = round(unit_p * qty_to_buy, 2)
                                eco_status = "upgrade_needed"
                                eco_note = f"⚠️ Купити {quote['name']} ({qty_to_buy} шт) на ринку."
    
                            item_entry = dict(quote)
                            item_entry["slot_title"] = slot_title
                            item_entry["qty_needed"] = qty_to_buy
                            item_entry["qty_required_total"] = qty_needed
                            item_entry["total_price"] = total_item_p
                            item_entry["already_equipped"] = (qty_to_buy == 0)
                            item_entry["eco_status"] = eco_status
                            item_entry["eco_note"] = eco_note
                            build_slots.append(item_entry)
    
                            if qty_to_buy > 0:
                                shopping_items.append(item_entry)
                            gear_cost += total_item_p
    
                    # Slot 7: Ammo
                    ammo_display_name = {
                        "lightAmmo": "Зелені патрони",
                        "ammo": "Сині патрони",
                        "heavyAmmo": "Фіолетові патрони",
                    }.get(ammo_key, ammo_spec["name"])
    
                    ammo_item = {
                        "slot": "ammo",
                        "slot_title": "Патрони",
                        "item_code": ammo_key,
                        "name": ammo_display_name,
                        "tier": 0,
                        "rarity": "consumable",
                        "is_consumable": True,
                        "image_url": get_item_image_url(ammo_key),
                        "icon": ammo_spec["icon"],
                        "target_stats": f"+{int(ammo_spec['bonus_pct'])}% Бонус атаки",
                        "stat_badge": f"+{int(ammo_spec['bonus_pct'])}% АТК",
                        "qty_needed": ammo_units_needed,
                        "qty_required_total": ammo_units_needed,
                        "unit_price": ammo_price,
                        "price": ammo_price,
                        "total_price": ammo_cost,
                        "already_equipped": False,
                        "eco_status": "buy",
                        "eco_note": f"{ammo_units_needed} пострілів на сесію",
                        "url": f"https://app.warera.io/market/commodities?item={ammo_key}",
                    }
                    build_slots.append(ammo_item)
    
                    # Slot 8: Food
                    food_item = {
                        "slot": "food",
                        "slot_title": "Їжа",
                        "item_code": f_key,
                        "name": f_spec["name"],
                        "tier": 0,
                        "rarity": "consumable",
                        "is_consumable": True,
                        "image_url": get_item_image_url(f_key),
                        "icon": f_spec["icon"],
                        "target_stats": f"+{int(f_spec['hp_pct']*100)}% HP / 1 сит.",
                        "stat_badge": f"{food_units_needed} шт",
                        "qty_needed": food_units_needed,
                        "qty_required_total": food_units_needed,
                        "unit_price": f_price,
                        "price": f_price,
                        "total_price": food_cost,
                        "already_equipped": False,
                        "eco_status": "buy",
                        "eco_note": f"{food_units_needed} од. ситості ({food_cost} ₴)",
                        "url": f"https://app.warera.io/market/commodities?item={f_key}",
                    }
                    build_slots.append(food_item)
    
                    grand_total = round(gear_cost + ammo_cost + food_cost + pill_cost, 2)
                    cost_per_m_dmg = round((grand_total / max(1.0, deficit_damage)) * 1_000_000, 1) if deficit_damage > 0 else 0.0

                    # Resolve item tiers for scrap recovery
                    if strat.get("is_current"):
                        if not has_equipped_weapon:
                            w_tier = 0
                    else:
                        s_def = strat["slots_def"]
                        w_tier = EQUIPMENT_METADATA.get(s_def.get("weapon_code", "sniper"), {}).get("tier", 4)
                        h_tier = EQUIPMENT_METADATA.get(s_def.get("helmet_code", "helmet4"), {}).get("tier", 4)
                        g_tier = EQUIPMENT_METADATA.get(s_def.get("gloves_code", "gloves4"), {}).get("tier", 4)
                        c_tier = EQUIPMENT_METADATA.get(s_def.get("chest_code", "chest4"), {}).get("tier", 4)
                        p_tier = EQUIPMENT_METADATA.get(s_def.get("pants_code", "pants4"), {}).get("tier", 4)
                        b_tier = EQUIPMENT_METADATA.get(s_def.get("boots_code", "boots4"), {}).get("tier", 4)

                    # --- Economic income & Net profit calculations (Athena & Intel Builder engine) ---
                    # 1. Expected Case Drops (Athena & Intel Builder: Drop = Hits * LootChance * Precision)
                    expected_case1 = round(hits_needed * loot_chance_ratio * eff_prec_ratio, 2) if hits_needed > 0 else 0.0
                    expected_case2 = round(hits_needed * (loot_chance_ratio / 100.0) * eff_prec_ratio, 3) if hits_needed > 0 else 0.0
                    case1_val = round(expected_case1 * case1_price, 2)
                    case2_val = round(expected_case2 * case2_price, 2)
                    total_cases_val = round(case1_val + case2_val, 2)

                    # 2. Scrap Recovery (1/3 of craft requirement returned on gear destruction)
                    if strat.get("is_current"):
                        # In current gear, player only wears 1 weapon and 1 armor set without new purchases
                        weapons_destroyed = min(1, weapons_burned) if has_equipped_weapon else 0
                        armor_sets_destroyed = min(1, armor_sets_burned) if has_equipped_armor else 0
                    else:
                        weapons_destroyed = weapons_burned
                        armor_sets_destroyed = armor_sets_burned

                    w_scrap = (weapons_destroyed * SCRAP_RECOVERY_BY_TIER.get(w_tier, 54)) if hits_needed > 0 else 0
                    armor_scrap_per_set = (
                        SCRAP_RECOVERY_BY_TIER.get(h_tier, 54) +
                        SCRAP_RECOVERY_BY_TIER.get(g_tier, 54) +
                        SCRAP_RECOVERY_BY_TIER.get(c_tier, 54) +
                        SCRAP_RECOVERY_BY_TIER.get(p_tier, 54) +
                        SCRAP_RECOVERY_BY_TIER.get(b_tier, 54)
                    )
                    a_scrap = (armor_sets_destroyed * armor_scrap_per_set) if hits_needed > 0 else 0
                    total_scrap_units = w_scrap + a_scrap
                    scrap_val = round(total_scrap_units * scrap_price, 2)

                    # 3. Net Profit / Net Cost (Operational combat returns: Cases + Scrap)
                    total_income = round(total_cases_val + scrap_val, 2)
                    net_cost = round(grand_total - total_income, 2)
                    net_profit = round(total_income - grand_total, 2)

                    opt_record = {
                        "strategy_key": f"{strat['key']}_{f_key}_{ammo_key}",
                        "base_key": strat["key"],
                        "label": strat["label"],
                        "tier_name": strat["tier_name"],
                        "tier_num": strat["tier_num"],
                        "food_key": f_key,
                        "food_name": f_spec["name"],
                        "food_icon": f_spec["icon"],
                        "ammo_key": ammo_key,
                        "ammo_name": ammo_spec["name"],
                        "ammo_badge": ammo_spec["badge"],
                        "ammo_icon": ammo_spec["icon"],
                        "ammo_bonus_pct": ammo_spec["bonus_pct"],
                        "ammo_price": ammo_price,
                        "ammo_units_needed": ammo_units_needed,
                        "ammo_cost": ammo_cost,
                        "avg_dmg_per_hit": sim_dmg,
                        "hp_cost_per_hit": sim_hp_cost,
                        "eff_dodge": eff_dodge,
                        "hits_needed": hits_needed,
                        "hp_needed": round(total_hp_needed, 0),
                        "food_units_needed": food_units_needed,
                        "available_hunger": round(available_hunger, 1),
                        "hunger_usage_pct": hunger_usage_pct,
                        "can_reach_in_session": can_reach,
                        "reach_badge": reach_badge,
                        "reach_status": reach_status,
                        "reach_note": reach_note,
                        "cost_per_m_dmg": cost_per_m_dmg,
                        "is_naked": is_player_naked if strat.get("is_current") else False,
                        "food_unit_price": f_price,
                        "food_cost": food_cost,
                        "weapons_burned": weapons_burned,
                        "armor_sets_burned": armor_sets_burned,
                        "gear_cost": round(gear_cost, 2),
                        "pill_cost": round(pill_cost, 2),
                        "grand_total_cost": grand_total,
                        "expected_case1": expected_case1,
                        "expected_case2": expected_case2,
                        "case1_value": case1_val,
                        "case2_value": case2_val,
                        "total_cases_value": total_cases_val,
                        "total_scrap": total_scrap_units,
                        "scrap_value": scrap_val,
                        "bounty_income": 0.0,
                        "total_income": total_income,
                        "net_cost": net_cost,
                        "net_profit": net_profit,
                        "build_slots": build_slots,
                        "shopping_items": shopping_items,
                        "shopping_count": len(shopping_items),
                        "is_best_value": False,
                    }
                    evaluated_options.append(opt_record)
    
        # Identify Best Value option (lowest net_cost among reachable green ammo builds)
        feasible_opts = [o for o in evaluated_options if o["can_reach_in_session"]]
        if feasible_opts:
            # User rule: "Завжди збираємо білд зеленими патронами, синіми тільки якщо не дотягуємо"
            # Prioritize reachable options using green ammo (lightAmmo) first!
            # Sort by lowest net_cost (best financial bottom line), then lowest hunger usage
            green_feasible = [o for o in feasible_opts if o["ammo_key"] == "lightAmmo"]
            if green_feasible:
                green_feasible.sort(key=lambda x: (x["net_cost"], x["hunger_usage_pct"]))
                best_opt = green_feasible[0]
            else:
                feasible_opts.sort(key=lambda x: (x["net_cost"], x["hunger_usage_pct"]))
                best_opt = feasible_opts[0]

            best_opt["is_best_value"] = True
            cheapest_net = best_opt["net_cost"]

            for o in evaluated_options:
                o["savings_vs_best"] = round(o["net_cost"] - cheapest_net, 2)
        else:
            # If none can fully reach in 1 session, pick the one that gets closest to reaching (lowest hunger usage overflow)
            valid_non_naked = [o for o in evaluated_options if not o.get("is_naked")]
            if valid_non_naked:
                valid_non_naked.sort(key=lambda x: (x["hunger_usage_pct"], x["net_cost"]))
                valid_non_naked[0]["is_best_value"] = True
            elif evaluated_options:
                evaluated_options[0]["is_best_value"] = True

        return {
            "player": {
                "username": uname,
                "level": lvl,
                "health_max": health_max,
                "health_curr": health_curr,
                "health_regen": health_regen,
                "hunger_max": hunger_max,
                "hunger_curr": hunger_curr,
                "hunger_regen": hunger_regen,
                "has_active_pill": has_active_pill,
                "pill_remaining_hours": round(session_hours, 2),
                "today_damage": round(today_damage, 0),
            },
            "target": {
                "target_damage": round(target_damage, 0),
                "deficit_damage": round(deficit_damage, 0),
                "session_hours": round(session_hours, 2),
                "selected_ammo": selected_ammo,
                "selected_food": custom_food_key or "auto",
                "battle_bonus": battle_bonus_val,
                "battle_multiplier": round(battle_mult, 3),
            },
            "consumable_prices": consumable_prices,
            "strategies": evaluated_options,
            "best_strategy": next((o for o in evaluated_options if o.get("is_best_value")), None) or (feasible_opts[0] if feasible_opts else evaluated_options[0]),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
