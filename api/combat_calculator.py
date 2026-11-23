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
from equipment_data import EQUIPMENT_METADATA, QUALITY_TIERS

logger = logging.getLogger("WarEraCombatCalculator")

# Consumable food specs: % of character max HP healed per 1 hunger unit
FOOD_SPECS = {
    "cookedFish": {"name": "Смажена риба", "hp_pct": 0.20, "default_price": 7.74, "icon": "🐟"},
    "steak": {"name": "Стейк", "hp_pct": 0.15, "default_price": 3.03, "icon": "🥩"},
    "fish": {"name": "Сира риба", "hp_pct": 0.12, "default_price": 3.93, "icon": "🎣"},
    "bread": {"name": "Хліб", "hp_pct": 0.10, "default_price": 1.40, "icon": "🍞"},
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
    ) -> Dict[str, Any]:
        """
        Calculates all viable combat strategies (Current, T3, T4, Hybrid, T5, T6)
        taking into account:
        1. 100 hits per weapon burn.
        2. Armor durability loss attenuated by dodge chance (1 set = 200-250+ hits).
        3. Ammo type and consumption (1 ammo per hit).
        4. Food units vs character hunger capacity per session.
        5. Live market prices.
        """
        market_cache = load_market_cheapest_cache()
        cached_items = market_cache.get("items", {})
        consumable_prices = market_cache.get("consumables", {})

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

        # 3. Base Character Stats
        base_atk = float(player_member.get("base_attack") or skills.get("attack", {}).get("value", 100))
        rank_bonus_pct = float(player_member.get("rank_bonus_pct") or skills.get("attack", {}).get("militaryRankPercent", 0.0))
        rank_mult = 1.0 + (rank_bonus_pct / 100.0)

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

        # Helper: get price and item details from cache or fallback
        def get_item_quote(code: str) -> Dict[str, Any]:
            meta = EQUIPMENT_METADATA.get(code, {})
            c_info = cached_items.get(code, {})
            offers = c_info.get("offers", [])
            cheapest = offers[0] if offers else None
            price = cheapest.get("price") if cheapest else c_info.get("cheapest_price")
            if not price or float(price) <= 0:
                price = DEFAULT_MARKET_PRICES.get(code, 40.0)
            return {
                "item_code": code,
                "name": meta.get("name", code),
                "slot": meta.get("type", "weapon"),
                "tier": meta.get("tier", 4),
                "price": round(float(price), 2),
                "seller": cheapest.get("seller", "") if cheapest else "",
                "roll_quality": cheapest.get("roll_quality", 0) if cheapest else 0,
                "url": f"https://app.warera.io/market/equipments?item={code}",
            }

        # Helper to simulate combat hits and damage for any tier combination
        def simulate_tier_combat(
            w_atk: float, w_crit_ch: float,
            h_crit_dmg: float,
            c_armor: float, p_armor: float,
            b_dodge: float, g_prec: float,
            ammo_bonus_pct: float
        ) -> tuple[float, float, float]:
            # 1. Effective Armor & Dodge with game softcap curve
            curr_armor_stat = float(skills.get("armor", {}).get("value", 0))
            curr_dodge_stat = float(skills.get("dodge", {}).get("value", 0))

            eff_gear_armor = max(equipped_armor, c_armor + p_armor)
            eff_gear_dodge = max(equipped_dodge, b_dodge)

            total_raw_armor = curr_armor_stat + eff_gear_armor
            total_raw_dodge = curr_dodge_stat + eff_gear_dodge

            calc_armor = min(total_raw_armor + 13.0, 40.0) + max(0.0, total_raw_armor + 13.0 - 40.0) * 0.5
            calc_dodge = min(total_raw_dodge + 13.0, 40.0) + max(0.0, total_raw_dodge + 13.0 - 40.0) * 0.5

            eff_armor = max(float(skills.get("armor", {}).get("totalAfterSoftCap", 0)), calc_armor)
            eff_dodge = max(float(skills.get("dodge", {}).get("totalAfterSoftCap", 0)), calc_dodge)

            hp_cost = max(0.80, 6.5 * (1.0 - (eff_armor / 100.0)) * (1.0 - (eff_dodge / 100.0)))

            # 2. Attack per hit with weapon & ammo
            eff_w_atk = max(equipped_weapon_atk, w_atk)
            ammo_mult = 1.0 + (ammo_bonus_pct / 100.0)
            sim_atk = (base_atk + eff_w_atk) * rank_mult * ammo_mult * 1.60

            # 3. Precision & Crits
            curr_prec = float(skills.get("precision", {}).get("value", 75))
            eq_prec = float(skills.get("precision", {}).get("equipment", 0))
            tot_prec = min(100.0, max(float(skills.get("precision", {}).get("total", 0)), curr_prec + max(eq_prec, g_prec)))
            prec_ratio = tot_prec / 100.0

            curr_crit_ch = float(skills.get("criticalChance", {}).get("value", 10))
            curr_crit_dmg = float(skills.get("criticalDamages", {}).get("value", 100))
            eq_crit_ch = float(skills.get("criticalChance", {}).get("weapon", 0))
            eq_crit_dmg = float(skills.get("criticalDamages", {}).get("equipment", 0))

            tot_crit_ch = min(100.0, max(float(skills.get("criticalChance", {}).get("total", 0)), curr_crit_ch + max(eq_crit_ch, w_crit_ch)))
            tot_crit_dmg = max(float(skills.get("criticalDamages", {}).get("total", 0)), curr_crit_dmg + max(eq_crit_dmg, h_crit_dmg))

            crit_hit_mult = 1.0 + (tot_crit_dmg / 100.0)
            crit_ch_ratio = tot_crit_ch / 100.0
            crit_mult = (1.0 - prec_ratio) * 0.5 + prec_ratio * ((1.0 - crit_ch_ratio) * 1.0 + crit_ch_ratio * crit_hit_mult)

            avg_dmg = sim_atk * crit_mult * 1.50 # Standard clan battle bonus (+50%)
            return round(avg_dmg, 1), round(hp_cost, 2), round(eff_dodge, 1)

        # Resolve Ammo Selection
        def get_best_ammo_for_tier(tier_num: float) -> str:
            if selected_ammo in AMMO_SPECS:
                return selected_ammo
            # Smart sweet spot: if target >= 2.5M, use standard blue ammo to compress food without buying T5 gear
            if abs(tier_num - 4.2) < 0.05:
                if deficit_damage >= 2_500_000:
                    return "ammo"
                return "lightAmmo"
            # Auto-selection logic:
            if deficit_damage >= 7_000_000 or tier_num >= 6:
                return "heavyAmmo" # 🟣 Heavy for 7M-10M or Jet
            elif deficit_damage >= 3_500_000 or tier_num >= 4.5:
                return "ammo" # 🔵 Standard for 3.5M+ or Tank/Hybrid
            return "lightAmmo" # 🟢 Light for everyday economy

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
                "tier_num": 4.2,
                "is_current": False,
                "slots_def": {
                    "name": "Золота середина",
                    "weapon_code": "sniper" if deficit_damage <= 4_500_000 else "tank",
                    "weapon_name": "Снайперка IV" if deficit_damage <= 4_500_000 else "Танк V",
                    "weapon_atk": 120.0 if deficit_damage <= 4_500_000 else 155.0,
                    "weapon_crit_chance": 18.0 if deficit_damage <= 4_500_000 else 30.0,
                    "helmet_code": "helmet4",
                    "helmet_name": "Шолом IV",
                    "helmet_crit_dmg": 80.0,
                    "chest_code": "chest4",
                    "chest_name": "Броня IV",
                    "chest_armor": 26.0,
                    "pants_code": "pants4",
                    "pants_name": "Штани IV",
                    "pants_armor": 26.0,
                    "boots_code": "boots4",
                    "boots_name": "Чоботи IV (Ухил)",
                    "boots_dodge": 24.0,
                    "gloves_code": "gloves4",
                    "gloves_name": "Рукавиці IV",
                    "gloves_precision": 23.0,
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
            ammo_key = get_best_ammo_for_tier(t_num)
            ammo_spec = AMMO_SPECS[ammo_key]
            ammo_price = float(consumable_prices.get(ammo_key, ammo_spec["default_price"]))

            if strat.get("is_current"):
                if has_equipped_weapon:
                    # Simulate real equipped stats
                    sim_dmg, sim_hp_cost, eff_dodge = simulate_tier_combat(
                        w_atk=equipped_weapon_atk,
                        w_crit_ch=float(skills.get("criticalChance", {}).get("weapon", 0)),
                        h_crit_dmg=float(skills.get("criticalDamages", {}).get("equipment", 0)),
                        c_armor=equipped_armor / 2.0,
                        p_armor=equipped_armor / 2.0,
                        b_dodge=equipped_dodge,
                        g_prec=float(skills.get("precision", {}).get("equipment", 0)),
                        ammo_bonus_pct=ammo_spec["bonus_pct"],
                    )
                else:
                    # Naked / no weapon equipped
                    sim_dmg = 0.0
                    sim_hp_cost = 6.5
                    eff_dodge = float(skills.get("dodge", {}).get("totalAfterSoftCap", 0))
            else:
                s_def = strat["slots_def"]
                sim_dmg, sim_hp_cost, eff_dodge = simulate_tier_combat(
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

                # 2. Armor & Equipment durability burn (attenuated by dodge!)
                # Hits absorbed by armor = hits * (1 - dodge)
                armor_hits = hits_needed * (1.0 - (eff_dodge / 100.0))
                armor_sets_burned = max(1, math.ceil(armor_hits / 100.0)) if hits_needed > 0 else 1

                # 3. Ammo consumption (1 ammo per hit)
                ammo_units_needed = hits_needed
                ammo_cost = round(ammo_units_needed * ammo_price, 2)

                # 4. Shopping list & durability eco-advice for all 6 slots
                shopping_items = []
                gear_cost = 0.0

                if not strat.get("is_current"):
                    s_def = strat["slots_def"]
                    slots_to_quote = [
                        ("weapon", s_def["weapon_code"], weapons_burned, s_def["weapon_atk"]),
                        ("helmet", s_def["helmet_code"], armor_sets_burned, s_def["helmet_crit_dmg"]),
                        ("chest", s_def["chest_code"], armor_sets_burned, s_def["chest_armor"]),
                        ("pants", s_def["pants_code"], armor_sets_burned, s_def["pants_armor"]),
                        ("boots", s_def["boots_code"], armor_sets_burned, s_def["boots_dodge"]),
                        ("gloves", s_def["gloves_code"], armor_sets_burned, s_def["gloves_precision"]),
                    ]

                    for slot_name, item_code, qty_needed, tier_stat_val in slots_to_quote:
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
                                eco_note = f"✅ Вже надіто на тобі ({quote['name']}). Докупка не потрібна (0 ₴)!"
                            else:
                                total_item_p = round(unit_p * qty_to_buy, 2)
                                eco_status = "wear_replacement"
                                eco_note = f"🛡 1-й на тобі, докупити +{qty_to_buy} шт на зміну при зносі."
                        else:
                            qty_to_buy = qty_needed
                            total_item_p = round(unit_p * qty_to_buy, 2)
                            eco_status = "upgrade_needed"
                            eco_note = f"⚠️ Потрібно купити {quote['name']} ({qty_to_buy} шт) для закриття цілі."

                        item_entry = dict(quote)
                        item_entry["qty_needed"] = qty_to_buy
                        item_entry["qty_required_total"] = qty_needed
                        item_entry["total_price"] = total_item_p
                        item_entry["eco_status"] = eco_status
                        item_entry["eco_note"] = eco_note
                        shopping_items.append(item_entry)
                        gear_cost += total_item_p

                grand_total = round(gear_cost + ammo_cost + food_cost + pill_cost, 2)
                cost_per_m_dmg = round((grand_total / max(1.0, deficit_damage)) * 1_000_000, 1) if deficit_damage > 0 else 0.0

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
                    "shopping_items": shopping_items,
                    "shopping_count": len(shopping_items),
                    "is_best_value": False,
                }
                evaluated_options.append(opt_record)

        # Identify Best Value option (cheapest among reachable ones)
        feasible_opts = [o for o in evaluated_options if o["can_reach_in_session"]]
        if feasible_opts:
            feasible_opts.sort(key=lambda x: x["grand_total_cost"])
            best_opt = feasible_opts[0]
            best_opt["is_best_value"] = True
            cheapest_total = best_opt["grand_total_cost"]

            for o in evaluated_options:
                o["savings_vs_best"] = round(o["grand_total_cost"] - cheapest_total, 2)
        else:
            # If none can fully reach in 1 session, pick the one that gets closest to reaching (lowest hunger usage overflow)
            valid_non_naked = [o for o in evaluated_options if not o.get("is_naked")]
            if valid_non_naked:
                valid_non_naked.sort(key=lambda x: (x["hunger_usage_pct"], x["grand_total_cost"]))
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
            },
            "strategies": evaluated_options,
            "best_strategy": feasible_opts[0] if feasible_opts else evaluated_options[0],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
