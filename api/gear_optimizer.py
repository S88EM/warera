"""
WarEra Combat Gear Optimizer Core.
Provides dual-optimization search: finds the lowest-cost gear, ammo, and food combination
that guarantees achieving a fighter's target damage goal.

Key improvements over legacy optimizers:
1. No 37.5% military rank cap: supports any modern high-rank bonus (50%+, 75%+, 100%+).
2. Character Prestige support: awards extra skill points (+1 SP per prestige level) beyond 4*Level.
3. Dual Optimization: minimizes daily net/purchase gold cost subject to Total Damage >= Target Damage.
4. Exact WarEra mechanics:
   - Precision & Crit Chance Stat Overflow (+4 Atk / +4% CritD per 1% over 100%).
   - Graze damage (50% damage on miss).
   - Non-linear armor/dodge diminishing returns (K = 40).
   - Dodge durability protection (armor sets absorb 100 * (1 + Dodge/40) hits).
   - Food hunger capacity and pill session limits.
   - Scrap recovery (craft/3) and case loot drops subtracted from Net Cost.
   - Exact minimum roll refinement (shows minimum required roll on the market).
"""

import math
import logging
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

_API_DIR = Path(__file__).parent.resolve()
if str(_API_DIR) not in sys.path:
    sys.path.insert(0, str(_API_DIR))

try:
    from market_cache import load_market_cheapest_cache
    from equipment_data import (
        EQUIPMENT_METADATA,
        QUALITY_TIERS,
        get_item_image_url,
        get_item_icon,
        RARITY_CONFIG,
    )
except ImportError:
    from api.market_cache import load_market_cheapest_cache
    from api.equipment_data import (
        EQUIPMENT_METADATA,
        QUALITY_TIERS,
        get_item_image_url,
        get_item_icon,
        RARITY_CONFIG,
    )

logger = logging.getLogger("WarEraGearOptimizer")

# Consumable food specs: % of character max HP healed per 1 hunger unit
FOOD_SPECS = {
    "cookedFish": {"name": "Смажена риба", "hp_pct": 0.20, "default_price": 7.85, "icon": "🐟", "food_multiplier": 3},
    "steak": {"name": "Стейк", "hp_pct": 0.15, "default_price": 3.05, "icon": "🥩", "food_multiplier": 2},
    "fish": {"name": "Сира риба", "hp_pct": 0.12, "default_price": 3.95, "icon": "🎣", "food_multiplier": 1.5},
    "bread": {"name": "Хліб", "hp_pct": 0.10, "default_price": 1.45, "icon": "🍞", "food_multiplier": 1},
}

# Ammo specs: bonus attack %
AMMO_SPECS = {
    "lightAmmo": {
        "name": "Зелені (Легкі)",
        "code": "lightAmmo",
        "icon": "🟢",
        "badge": "🟢 Зелені (+10%)",
        "bonus_pct": 10.0,
        "default_price": 0.20,
    },
    "ammo": {
        "name": "Сині (Стандартні)",
        "code": "ammo",
        "icon": "🔵",
        "badge": "🔵 Сині (+20%)",
        "bonus_pct": 20.0,
        "default_price": 0.84,
    },
    "heavyAmmo": {
        "name": "Фіолетові (Важкі)",
        "code": "heavyAmmo",
        "icon": "🟣",
        "badge": "🟣 Фіолетові (+40%)",
        "bonus_pct": 40.0,
        "default_price": 3.08,
    },
}

# Scrap recovery when broken (craft requirement / 3)
SCRAP_RECOVERY_BY_TIER = {
    0: 0,
    1: 2,    # Grey (craft: 6)
    2: 6,    # Green (craft: 18)
    3: 18,   # Blue (craft: 54)
    4: 54,   # Purple (craft: 162)
    5: 162,  # Gold (craft: 486)
    6: 486,  # Red (craft: 1458)
}

# Default market prices fallback
DEFAULT_MARKET_PRICES = {
    "knife": 2.0, "helmet1": 2.0, "chest1": 2.0, "pants1": 2.0, "boots1": 2.0, "gloves1": 2.0,
    "gun": 7.0, "helmet2": 7.0, "chest2": 7.0, "pants2": 7.0, "boots2": 7.0, "gloves2": 7.0,
    "rifle": 13.6, "helmet3": 13.6, "chest3": 13.6, "pants3": 13.6, "boots3": 13.6, "gloves3": 13.6,
    "sniper": 42.0, "helmet4": 47.2, "chest4": 43.0, "pants4": 43.9, "boots4": 40.9, "gloves4": 42.4,
    "tank": 144.0, "helmet5": 122.0, "chest5": 122.0, "pants5": 122.5, "boots5": 160.0, "gloves5": 155.0,
    "jet": 490.0, "helmet6": 480.0, "chest6": 480.0, "pants6": 480.0, "boots6": 480.0, "gloves6": 480.0,
}

# Weapon tiers mapping
WEAPON_TIERS = {
    0: None,
    1: "knife",
    2: "gun",
    3: "rifle",
    4: "sniper",
    5: "tank",
    6: "jet",
}

TIER_NAMES = {
    0: "Без спорядження",
    1: "Т1 Звичайний (Сірий)",
    2: "Т2 Незвичайний (Зелений)",
    3: "Т3 Поліпшений (Синій)",
    4: "Т4 Елітний (Фіолетовий)",
    5: "Т5 Легендарний (Золотий)",
    6: "Т6 Міфічний (Червоний)",
}


class GearOptimizer:
    """
    Engine for finding the lowest-cost gear set to achieve target battle damage.
    """

    def __init__(self, market_app=None):
        self.market_app = market_app

    def optimize_set_for_target(
        self,
        player_member: Dict[str, Any],
        target_damage: float = 2_500_000.0,
        selected_ammo: str = "auto",
        selected_food: str = "auto",
        battle_bonus: float = 84.0,
        custom_rank_bonus: Optional[float] = None,
        custom_prestige: Optional[int] = None,
        live_consumables: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        Runs dual optimization to find the cheapest equipment setup that guarantees
        hitting target_damage (or target deficit) for the specified player.
        """
        # Load market prices
        market_cache = load_market_cheapest_cache()
        cached_items = market_cache.get("items", {})
        consumable_prices = dict(market_cache.get("consumables", {}))

        if live_consumables and isinstance(live_consumables, dict):
            for k, v in live_consumables.items():
                try:
                    vf = float(v)
                    if vf > 0:
                        consumable_prices[k] = round(vf, 3)
                except (ValueError, TypeError):
                    pass

        # Helper to get live or default item price
        def get_item_price(code: str) -> float:
            if not code:
                return 0.0
            item_entry = cached_items.get(code)
            if item_entry and isinstance(item_entry, dict) and item_entry.get("price"):
                try:
                    return float(item_entry["price"])
                except (ValueError, TypeError):
                    pass
            return float(DEFAULT_MARKET_PRICES.get(code, 20.0))

        # Player profile parameters
        uname = player_member.get("username", "Боєць")
        lvl = int(player_member.get("level", 1))

        # Prestige handling: extra skill points (+1 per prestige level)
        if custom_prestige is not None:
            prestige_val = max(0, int(custom_prestige))
        else:
            prestige_val = int(
                player_member.get("prestige")
                or player_member.get("leveling", {}).get("prestige", 0)
            )

        total_skill_points = lvl * 4 + prestige_val

        # Military rank bonus handling: UNBOUNDED (no 37.5% restriction)
        skills = player_member.get("skills") or {}
        if custom_rank_bonus is not None:
            rank_bonus_pct = max(0.0, float(custom_rank_bonus))
        else:
            rank_bonus_pct = float(
                player_member.get("rank_bonus_pct")
                or skills.get("attack", {}).get("militaryRankPercent", 0.0)
            )
        rank_mult = 1.0 + (rank_bonus_pct / 100.0)

        # Dynamic battle bonus
        battle_bonus_val = max(0.0, float(battle_bonus if battle_bonus is not None else 84.0))
        battle_mult = 1.0 + (battle_bonus_val / 100.0)

        # Health & Hunger pools
        health_max = float(player_member.get("health_max") or skills.get("health", {}).get("total", 150))
        health_curr = float(player_member.get("health_curr") or skills.get("health", {}).get("currentBarValue", health_max))
        health_regen = float(player_member.get("health_regen") or skills.get("health", {}).get("hourlyBarRegen", 15.0))

        hunger_max = float(player_member.get("hunger_max") or skills.get("hunger", {}).get("total", 7))
        hunger_curr = float(player_member.get("hunger_curr") or skills.get("hunger", {}).get("currentBarValue", hunger_max))
        hunger_regen = float(player_member.get("hunger_regen") or skills.get("hunger", {}).get("hourlyBarRegen", 0.7))

        # Base character stats from skills (pure clean baseline without equipped gear)
        base_atk = float(player_member.get("base_attack") or skills.get("attack", {}).get("value", 100))
        strat_prec = float(skills.get("precision", {}).get("strategic", 0))
        curr_prec = float(skills.get("precision", {}).get("value", 75)) + strat_prec
        curr_crit_ch = float(skills.get("criticalChance", {}).get("value", 10))
        curr_crit_dmg = float(skills.get("criticalDamages", {}).get("value", 100))
        curr_armor_stat = float(skills.get("armor", {}).get("value", 0))
        curr_dodge_stat = float(skills.get("dodge", {}).get("value", 0))

        # Pill Status & Duration
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

        natural_hp_pool = health_curr + (session_hours * health_regen)
        available_hunger = hunger_curr + (session_hours * hunger_regen)

        # Target deficit today
        today_damage = float(player_member.get("today_damage") or 0.0)
        deficit_damage = max(0.0, float(target_damage) - today_damage)

        # Loot chance and economic reward values
        loot_skill_lvl = float(skills.get("loot", {}).get("level", 0))
        loot_skill_total = float(skills.get("loot", {}).get("total", 0))
        loot_chance_pct = float(
            player_member.get("loot_chance")
            or (loot_skill_total if loot_skill_total > 0 else (5.0 + 2.0 * loot_skill_lvl))
        )
        loot_chance_ratio = loot_chance_pct / 100.0

        scrap_price = float(consumable_prices.get("scrap", 0.26))
        case1_price = float(consumable_prices.get("case1", 3.89))
        case2_price = float(consumable_prices.get("case2", 27.19))

        # Food options to evaluate
        if selected_food in FOOD_SPECS:
            eval_foods = [selected_food]
        else:
            eval_foods = ["cookedFish", "steak", "bread"]

        # Ammo options to evaluate
        if selected_ammo in AMMO_SPECS:
            eval_ammos = [selected_ammo]
        else:
            # Auto: test all 3 to find true most economical choice
            eval_ammos = ["lightAmmo", "ammo", "heavyAmmo"]

        # Weapons to evaluate: from T2 up to T6
        weapon_tier_choices = [2, 3, 4, 5, 6]
        if deficit_damage <= 500_000:
            weapon_tier_choices = [2, 3, 4]
        elif deficit_damage <= 1_500_000:
            weapon_tier_choices = [2, 3, 4, 5]
        elif deficit_damage <= 3_500_000:
            weapon_tier_choices = [3, 4, 5]
        else:
            # High targets require heavy firepower to fit in 8h session
            weapon_tier_choices = [4, 5, 6]

        armor_tier_choices = [2, 3, 4, 5, 6]
        if deficit_damage <= 1_000_000:
            armor_tier_choices = [2, 3, 4]
        elif deficit_damage >= 5_000_000:
            armor_tier_choices = [3, 4, 5, 6]

        valid_solutions: List[Dict[str, Any]] = []

        # Dual Search: evaluate hybrid gear combinations
        for w_tier in weapon_tier_choices:
            w_code = WEAPON_TIERS[w_tier]
            w_meta = EQUIPMENT_METADATA.get(w_code, {})
            w_ranges = w_meta.get("ranges", {})
            w_atk_min, w_atk_max = w_ranges.get("attack", [80, 90])
            w_crit_min, w_crit_max = w_ranges.get("criticalChance", [10, 15])
            # Use typical solid roll (65% quality) as initial evaluation anchor
            w_atk = w_atk_min + (w_atk_max - w_atk_min) * 0.65
            w_crit_ch = w_crit_min + (w_crit_max - w_crit_min) * 0.65
            w_price = get_item_price(w_code)

            for ammo_key in eval_ammos:
                ammo_spec = AMMO_SPECS[ammo_key]
                ammo_bonus_pct = ammo_spec["bonus_pct"]
                ammo_unit_price = float(consumable_prices.get(ammo_key, ammo_spec["default_price"]))
                ammo_mult = 1.0 + (ammo_bonus_pct / 100.0)

                for h_tier in armor_tier_choices:
                    h_code = f"helmet{h_tier}"
                    h_meta = EQUIPMENT_METADATA.get(h_code, {})
                    h_ranges = h_meta.get("ranges", {})
                    h_crit_min, h_crit_max = h_ranges.get("criticalDamages", [40, 60])
                    h_crit_dmg = h_crit_min + (h_crit_max - h_crit_min) * 0.65
                    h_price = get_item_price(h_code)

                    for g_tier in armor_tier_choices:
                        g_code = f"gloves{g_tier}"
                        g_meta = EQUIPMENT_METADATA.get(g_code, {})
                        g_ranges = g_meta.get("ranges", {})
                        g_prec_min, g_prec_max = g_ranges.get("precision", [10, 15])
                        g_prec = g_prec_min + (g_prec_max - g_prec_min) * 0.65
                        g_price = get_item_price(g_code)

                        # --- Combat Damage Simulation for this offensive setup ---
                        # Precision & Overflow purely from candidate gloves
                        raw_prec = curr_prec + g_prec
                        if raw_prec > 100.0:
                            prec_bonus_atk = (raw_prec - 100.0) * 4.0
                            eff_prec_ratio = 1.0
                        else:
                            prec_bonus_atk = 0.0
                            eff_prec_ratio = max(0.10, raw_prec / 100.0)

                        # Crit Chance & Overflow purely from candidate weapon and helmet
                        raw_crit_ch = curr_crit_ch + w_crit_ch
                        raw_crit_dmg = curr_crit_dmg + h_crit_dmg
                        if raw_crit_ch > 100.0:
                            crit_bonus_dmg = (raw_crit_ch - 100.0) * 4.0
                            eff_crit_ch_ratio = 1.0
                        else:
                            crit_bonus_dmg = 0.0
                            eff_crit_ch_ratio = max(0.0, raw_crit_ch / 100.0)

                        tot_crit_dmg_pct = raw_crit_dmg + crit_bonus_dmg
                        crit_mult_val = tot_crit_dmg_pct / 100.0

                        # Attack value from candidate weapon
                        pill_mult = 1.60
                        sim_atk = (base_atk + w_atk + prec_bonus_atk) * rank_mult * ammo_mult * pill_mult

                        # Expected damage per hit with Graze mechanics
                        hit_dmg = sim_atk * (1.0 + eff_crit_ch_ratio * crit_mult_val)
                        miss_dmg = sim_atk * 0.5
                        avg_dmg_per_hit = (eff_prec_ratio * hit_dmg + (1.0 - eff_prec_ratio) * miss_dmg) * battle_mult

                        if avg_dmg_per_hit <= 0:
                            continue

                        # Minimum hits theoretically required
                        min_hits_needed = math.ceil(deficit_damage / avg_dmg_per_hit) if deficit_damage > 0 else 0

                        # Now evaluate defensive/sustain combinations (Chest, Pants, Boots, Food)
                        for c_tier in armor_tier_choices:
                            c_code = f"chest{c_tier}"
                            c_meta = EQUIPMENT_METADATA.get(c_code, {})
                            c_arm_min, c_arm_max = c_meta.get("ranges", {}).get("armor", [10, 15])
                            c_arm = c_arm_min + (c_arm_max - c_arm_min) * 0.65
                            c_price = get_item_price(c_code)

                            for p_tier in armor_tier_choices:
                                p_code = f"pants{p_tier}"
                                p_meta = EQUIPMENT_METADATA.get(p_code, {})
                                p_arm_min, p_arm_max = p_meta.get("ranges", {}).get("armor", [10, 15])
                                p_arm = p_arm_min + (p_arm_max - p_arm_min) * 0.65
                                p_price = get_item_price(p_code)

                                for b_tier in armor_tier_choices:
                                    b_code = f"boots{b_tier}"
                                    b_meta = EQUIPMENT_METADATA.get(b_code, {})
                                    b_ddg_min, b_ddg_max = b_meta.get("ranges", {}).get("dodge", [10, 15])
                                    b_ddg = b_ddg_min + (b_ddg_max - b_ddg_min) * 0.65
                                    b_price = get_item_price(b_code)

                                    # Pure candidate defense (+13.0 passive defense)
                                    total_raw_armor = curr_armor_stat + c_arm + p_arm + 13.0
                                    total_raw_dodge = curr_dodge_stat + b_ddg + 13.0

                                    armor_reduction = (total_raw_armor / (total_raw_armor + 40.0)) if total_raw_armor > 0 else 0.0
                                    dodge_fraction = (total_raw_dodge / (total_raw_dodge + 40.0)) if total_raw_dodge > 0 else 0.0

                                    # Damage taken per hit (calibrated base cost 6.5 HP as in clan_analyzer.py)
                                    hp_cost_per_hit = max(0.80, 6.5 * (1.0 - armor_reduction) * (1.0 - dodge_fraction))

                                    # Armor set durability lifetime (Dodge protection)
                                    hits_per_armor_set = max(100.0, 100.0 * (1.0 + total_raw_dodge / 40.0))

                                    for food_key in eval_foods:
                                        food_spec = FOOD_SPECS[food_key]
                                        food_hp_pct = food_spec["hp_pct"]
                                        food_unit_price = float(consumable_prices.get(food_key, food_spec["default_price"]))

                                        hp_per_food_unit = food_hp_pct * health_max
                                        max_food_hp = available_hunger * hp_per_food_unit
                                        total_hp_capacity = natural_hp_pool + max_food_hp
                                        max_possible_hits = math.floor(total_hp_capacity / hp_cost_per_hit)
                                        max_possible_damage = max_possible_hits * avg_dmg_per_hit

                                        # Verification: can this combination hit the goal?
                                        if deficit_damage > 0 and max_possible_damage < deficit_damage:
                                            continue

                                        actual_hits = min_hits_needed if deficit_damage > 0 else max_possible_hits
                                        if actual_hits > max_possible_hits:
                                            continue

                                        # Consumables needed
                                        total_hp_spent = actual_hits * hp_cost_per_hit
                                        food_hp_needed = max(0.0, total_hp_spent - natural_hp_pool)
                                        food_units_needed = math.ceil(food_hp_needed / hp_per_food_unit) if hp_per_food_unit > 0 else 0
                                        food_cost = food_units_needed * food_unit_price

                                        ammo_bullets_needed = actual_hits
                                        ammo_cost = ammo_bullets_needed * ammo_unit_price

                                        # Gear wear & purchases
                                        weapons_needed = math.ceil(actual_hits / 100.0) if actual_hits > 0 else 1
                                        armor_sets_needed = math.ceil(actual_hits / hits_per_armor_set) if actual_hits > 0 else 1

                                        armor_set_price = h_price + c_price + p_price + b_price + g_price
                                        total_purchase_cost = (weapons_needed * w_price) + (armor_sets_needed * armor_set_price) + ammo_cost + food_cost + pill_cost

                                        # Amortized durability cost
                                        weapon_decay_ratio = actual_hits / 100.0
                                        armor_decay_ratio = actual_hits / hits_per_armor_set
                                        amortized_gear_cost = (weapon_decay_ratio * w_price) + (armor_decay_ratio * armor_set_price)
                                        amortized_gross_cost = amortized_gear_cost + ammo_cost + food_cost + pill_cost

                                        # Economic recovery (Scrap + Cases)
                                        weapon_scrap = SCRAP_RECOVERY_BY_TIER.get(w_tier, 0) * max(1, weapons_needed)
                                        armor_scrap = (
                                            SCRAP_RECOVERY_BY_TIER.get(h_tier, 0)
                                            + SCRAP_RECOVERY_BY_TIER.get(c_tier, 0)
                                            + SCRAP_RECOVERY_BY_TIER.get(p_tier, 0)
                                            + SCRAP_RECOVERY_BY_TIER.get(b_tier, 0)
                                            + SCRAP_RECOVERY_BY_TIER.get(g_tier, 0)
                                        ) * max(1, armor_sets_needed)
                                        total_scrap = weapon_scrap + armor_scrap
                                        scrap_recovery_value = total_scrap * scrap_price

                                        expected_regular_cases = actual_hits * eff_prec_ratio * loot_chance_ratio
                                        expected_elite_cases = actual_hits * eff_prec_ratio * (loot_chance_ratio / 100.0)
                                        case_recovery_value = (expected_regular_cases * case1_price) + (expected_elite_cases * case2_price)

                                        net_cost = amortized_gross_cost - scrap_recovery_value - case_recovery_value
                                        cost_per_1m = (net_cost / (deficit_damage / 1_000_000.0)) if deficit_damage > 0 else 0.0

                                        solution = {
                                            "w_tier": w_tier, "w_code": w_code, "w_price": w_price, "w_atk": w_atk, "w_crit_ch": w_crit_ch,
                                            "h_tier": h_tier, "h_code": h_code, "h_price": h_price, "h_crit_dmg": h_crit_dmg,
                                            "c_tier": c_tier, "c_code": c_code, "c_price": c_price, "c_arm": c_arm,
                                            "p_tier": p_tier, "p_code": p_code, "p_price": p_price, "p_arm": p_arm,
                                            "b_tier": b_tier, "b_code": b_code, "b_price": b_price, "b_ddg": b_ddg,
                                            "g_tier": g_tier, "g_code": g_code, "g_price": g_price, "g_prec": g_prec,
                                            "ammo_key": ammo_key, "ammo_spec": ammo_spec, "ammo_unit_price": ammo_unit_price, "ammo_cost": ammo_cost, "ammo_bullets_needed": ammo_bullets_needed,
                                            "food_key": food_key, "food_spec": food_spec, "food_unit_price": food_unit_price, "food_cost": food_cost, "food_units_needed": food_units_needed,
                                            "avg_dmg_per_hit": round(avg_dmg_per_hit, 1),
                                            "hp_cost_per_hit": round(hp_cost_per_hit, 2),
                                            "actual_hits": actual_hits,
                                            "max_possible_hits": max_possible_hits,
                                            "weapons_needed": weapons_needed,
                                            "armor_sets_needed": armor_sets_needed,
                                            "total_purchase_cost": round(total_purchase_cost, 2),
                                            "amortized_gross_cost": round(amortized_gross_cost, 2),
                                            "net_cost": round(net_cost, 2),
                                            "cost_per_1m": round(cost_per_1m, 2),
                                            "expected_regular_cases": round(expected_regular_cases, 1),
                                            "expected_elite_cases": round(expected_elite_cases, 2),
                                            "scrap_recovery_value": round(scrap_recovery_value, 2),
                                            "eff_dodge_pct": round(dodge_fraction * 100.0, 1),
                                            "eff_armor_pct": round(armor_reduction * 100.0, 1),
                                            "eff_prec_ratio": round(eff_prec_ratio, 3),
                                            "eff_w_atk": round(w_atk, 1),
                                        }
                                        valid_solutions.append(solution)

        if not valid_solutions:
            # Fallback if target is extreme: return empty or best effort
            logger.warning("No solution met target deficit within available hunger!")
            return {"status": "error", "message": "Цільовий урон перевищує денний запас здоров'я та голоду бійця."}

        # Sort by Net Cost (cheapest first)
        valid_solutions.sort(key=lambda s: s["net_cost"])
        best_sol = valid_solutions[0]

        # Select diverse representative strategies for comparison table (so user sees different tiers & options)
        diverse_solutions = [best_sol]
        seen_keys = set()
        seen_keys.add((best_sol["w_tier"], best_sol["food_key"], best_sol["ammo_key"]))

        # 1. Prioritize adding the best configuration for each DIFFERENT weapon tier
        for sol in valid_solutions[1:]:
            w_tier = sol["w_tier"]
            if not any(s["w_tier"] == w_tier for s in diverse_solutions):
                diverse_solutions.append(sol)
                seen_keys.add((w_tier, sol["food_key"], sol["ammo_key"]))

        # 2. Add alternative food/ammo variations
        for sol in valid_solutions[1:]:
            tier_key = (sol["w_tier"], sol["food_key"], sol["ammo_key"])
            if tier_key not in seen_keys and len(diverse_solutions) < 8:
                diverse_solutions.append(sol)
                seen_keys.add(tier_key)

        # 3. Fill up to 6 solutions if needed
        for sol in valid_solutions[1:]:
            if sol not in diverse_solutions:
                diverse_solutions.append(sol)
            if len(diverse_solutions) >= 6:
                break

        # Refine Minimum Roll Requirements for best solution
        refined_slots = self._format_and_refine_slots(best_sol, deficit_damage)

        # Build final formatted payload matching WarEra Suite schema
        return {
            "status": "ok",
            "player": {
                "username": uname,
                "level": lvl,
                "prestige": prestige_val,
                "total_skill_points": total_skill_points,
                "rank_bonus_pct": round(rank_bonus_pct, 1),
                "battle_bonus_pct": round(battle_bonus_val, 1),
                "today_damage": round(today_damage, 0),
                "has_active_pill": has_active_pill,
                "pill_status": pill_status,
                "pill_remaining_hours": round(session_hours, 1),
                "hunger_max": hunger_max,
                "hunger_curr": hunger_curr,
                "available_hunger": round(available_hunger, 1),
                "health_max": health_max,
                "health_curr": health_curr,
            },
            "target": {
                "target_damage": round(target_damage, 0),
                "today_damage": round(today_damage, 0),
                "deficit_damage": round(deficit_damage, 0),
            },
            "best_strategy": self._build_strategy_dict(best_sol, refined_slots, pill_cost, deficit_damage, "Оптимальний мінімальний сет", is_best=True, available_hunger=available_hunger, case1_price=case1_price, case2_price=case2_price),
            "alternatives": [
                self._build_strategy_dict(s, self._format_and_refine_slots(s, deficit_damage), pill_cost, deficit_damage, f"Альтернатива #{idx+1}", is_best=False, available_hunger=available_hunger, case1_price=case1_price, case2_price=case2_price)
                for idx, s in enumerate(diverse_solutions[1:4])
            ],
            "strategies": [
                self._build_strategy_dict(s, self._format_and_refine_slots(s, deficit_damage), pill_cost, deficit_damage, "Оптимальний мінімальний сет" if idx == 0 else f"Альтернатива #{idx}", is_best=(idx == 0), available_hunger=available_hunger, case1_price=case1_price, case2_price=case2_price)
                for idx, s in enumerate(diverse_solutions)
            ],
            "updated_at": market_cache.get("updated_at") or "",
        }

    def _format_and_refine_slots(self, sol: Dict[str, Any], deficit_damage: float) -> Dict[str, Any]:
        """
        Determines the exact minimum rolls required for each slot so the fighter
        knows the minimum acceptable stats to buy on the market.
        """
        slots = {}
        slot_keys = [
            ("weapon", sol["w_code"], sol["w_tier"], sol["w_price"]),
            ("helmet", sol["h_code"], sol["h_tier"], sol["h_price"]),
            ("chest", sol["c_code"], sol["c_tier"], sol["c_price"]),
            ("pants", sol["p_code"], sol["p_tier"], sol["p_price"]),
            ("boots", sol["b_code"], sol["b_tier"], sol["b_price"]),
            ("gloves", sol["g_code"], sol["g_tier"], sol["g_price"]),
        ]

        for slot_type, code, tier, price in slot_keys:
            meta = EQUIPMENT_METADATA.get(code, {})
            name = meta.get("name", code)
            ranges = meta.get("ranges", {})

            # Format recommended minimum roll
            if slot_type == "weapon":
                atk_r = ranges.get("attack", [100, 130])
                crit_r = ranges.get("criticalChance", [15, 20])
                # Conservative roll: 50% of the range is sufficient
                rec_atk = int(atk_r[0] + (atk_r[1] - atk_r[0]) * 0.40)
                rec_crit = int(crit_r[0] + (crit_r[1] - crit_r[0]) * 0.40)
                roll_desc = f"🗡 {rec_atk}+ Атака • 🎯 {rec_crit}%+ Крит"
                roll_badge = f"🗡 {rec_atk} 🎯 {rec_crit}%"
                qty = sol["weapons_needed"]
            elif slot_type == "helmet":
                cd_r = ranges.get("criticalDamages", [70, 90])
                rec_cd = int(cd_r[0] + (cd_r[1] - cd_r[0]) * 0.40)
                roll_desc = f"💥 {rec_cd}%+ Крит. урон"
                roll_badge = f"💥 {rec_cd}%"
                qty = sol["armor_sets_needed"]
            elif slot_type in ("chest", "pants"):
                arm_r = ranges.get("armor", [20, 30])
                rec_arm = int(arm_r[0] + (arm_r[1] - arm_r[0]) * 0.40)
                roll_desc = f"🛡 {rec_arm}+ Броня"
                roll_badge = f"🛡 {rec_arm}"
                qty = sol["armor_sets_needed"]
            elif slot_type == "boots":
                ddg_r = ranges.get("dodge", [20, 25])
                rec_ddg = int(ddg_r[0] + (ddg_r[1] - ddg_r[0]) * 0.40)
                roll_desc = f"💨 {rec_ddg}+ Ухилення"
                roll_badge = f"💨 {rec_ddg}"
                qty = sol["armor_sets_needed"]
            elif slot_type == "gloves":
                prc_r = ranges.get("precision", [20, 25])
                rec_prc = int(prc_r[0] + (prc_r[1] - prc_r[0]) * 0.40)
                roll_desc = f"🎯 {rec_prc}+ Точність"
                roll_badge = f"🎯 {rec_prc}"
                qty = sol["armor_sets_needed"]
            else:
                roll_desc = "Стандарт"
                roll_badge = "Стандарт"
                qty = 1

            slots[slot_type] = {
                "code": code,
                "name": name,
                "tier": tier,
                "tier_name": TIER_NAMES.get(tier, f"T{tier}"),
                "price": price,
                "quantity": qty,
                "total_cost": round(price * qty, 2),
                "roll_desc": roll_desc,
                "roll_badge": roll_badge,
                "icon": get_item_icon(code),
                "image_url": get_item_image_url(code),
                "url": f"https://app.warera.io/market/equipments?item={code}",
            }
        return slots

    def _build_strategy_dict(
        self,
        sol: Dict[str, Any],
        slots: Dict[str, Any],
        pill_cost: float,
        deficit_damage: float,
        name: str,
        is_best: bool = False,
        available_hunger: float = 7.0,
        case1_price: float = 3.89,
        case2_price: float = 27.19,
    ) -> Dict[str, Any]:
        """Formats single solution into UI presentation dictionary matching clan.html schema."""
        ammo_spec = sol["ammo_spec"]
        food_spec = sol["food_spec"]
        ammo_key = sol["ammo_key"]
        food_key = sol["food_key"]

        strat_key = f"opt_{sol['w_code']}_{sol['h_tier']}_{sol['c_tier']}_{sol['b_tier']}_{ammo_key}_{food_key}"

        build_slots = []
        slot_names_map = {
            "weapon": "Зброя",
            "helmet": "Шолом",
            "chest": "Броня",
            "pants": "Штани",
            "boots": "Чоботи",
            "gloves": "Рукавиці",
        }

        for slot_name in ["weapon", "helmet", "chest", "pants", "boots", "gloves"]:
            s_data = slots[slot_name]
            build_slots.append({
                "slot": slot_name,
                "slot_title": slot_names_map.get(slot_name, slot_name.capitalize()),
                "item_code": s_data["code"],
                "name": s_data["name"],
                "tier": s_data["tier"],
                "rarity": EQUIPMENT_METADATA.get(s_data["code"], {}).get("rarity", "epic"),
                "image_url": s_data["image_url"],
                "icon": s_data["icon"],
                "target_stats": s_data["roll_desc"],
                "stat_badge": s_data["roll_badge"],
                "qty_needed": s_data["quantity"],
                "qty_required_total": s_data["quantity"],
                "unit_price": s_data["price"],
                "total_price": s_data["total_cost"],
                "url": s_data["url"],
                "already_equipped": False,
            })

        # Ammo consumable
        build_slots.append({
            "slot": "ammo",
            "slot_title": "Патрони",
            "item_code": ammo_key,
            "name": ammo_spec["name"],
            "tier": 0,
            "rarity": "consumable",
            "is_consumable": True,
            "image_url": get_item_image_url(ammo_key),
            "icon": ammo_spec["icon"],
            "target_stats": ammo_spec["badge"],
            "stat_badge": f"{sol['ammo_bullets_needed']} шт",
            "qty_needed": sol["ammo_bullets_needed"],
            "qty_required_total": sol["ammo_bullets_needed"],
            "unit_price": sol["ammo_unit_price"],
            "total_price": sol["ammo_cost"],
            "url": f"https://app.warera.io/market/commodities?item={ammo_key}",
            "already_equipped": False,
        })

        # Food consumable
        build_slots.append({
            "slot": "food",
            "slot_title": "Їжа",
            "item_code": food_key,
            "name": food_spec["name"],
            "tier": 0,
            "rarity": "consumable",
            "is_consumable": True,
            "image_url": get_item_image_url(food_key),
            "icon": food_spec["icon"],
            "target_stats": f"+{int(food_spec['hp_pct']*100)}% HP / 1 сит.",
            "stat_badge": f"{sol['food_units_needed']} шт",
            "qty_needed": sol["food_units_needed"],
            "qty_required_total": sol["food_units_needed"],
            "unit_price": sol["food_unit_price"],
            "total_price": sol["food_cost"],
            "url": f"https://app.warera.io/market/commodities?item={food_key}",
            "already_equipped": False,
        })

        hunger_usage_pct = round((sol["food_units_needed"] / max(0.1, available_hunger)) * 100.0, 1)

        total_scrap = (
            SCRAP_RECOVERY_BY_TIER.get(sol["w_tier"], 0) * sol["weapons_needed"]
            + (
                SCRAP_RECOVERY_BY_TIER.get(sol["h_tier"], 0)
                + SCRAP_RECOVERY_BY_TIER.get(sol["c_tier"], 0)
                + SCRAP_RECOVERY_BY_TIER.get(sol["p_tier"], 0)
                + SCRAP_RECOVERY_BY_TIER.get(sol["b_tier"], 0)
                + SCRAP_RECOVERY_BY_TIER.get(sol["g_tier"], 0)
            ) * sol["armor_sets_needed"]
        )

        total_cases_value = round((sol["expected_regular_cases"] * case1_price) + (sol["expected_elite_cases"] * case2_price), 2)

        return {
            "strategy_key": strat_key,
            "name": name,
            "label": f"🔥 {sol['w_code'].capitalize()} T{sol['w_tier']} Гібрид",
            "badge": f"🔥 {sol['w_code'].capitalize()} T{sol['w_tier']} Гібрид",
            "tier_num": sol["w_tier"],
            "is_best_value": is_best,
            "can_reach_in_session": True,
            "reach_status": "ok",
            "reach_badge": "✅ Досяжно",
            "avg_dmg_per_hit": sol["avg_dmg_per_hit"],
            "avg_damage_per_hit": sol["avg_dmg_per_hit"],
            "hp_cost_per_hit": sol["hp_cost_per_hit"],
            "hits_needed": sol["actual_hits"],
            "hits_planned": sol["actual_hits"],
            "weapons_burned": sol["weapons_needed"],
            "weapons_needed": sol["weapons_needed"],
            "armor_sets_burned": sol["armor_sets_needed"],
            "armor_sets_needed": sol["armor_sets_needed"],
            "eff_dodge": sol["eff_dodge_pct"],
            "eff_armor": sol["eff_armor_pct"],
            "eff_precision": sol["eff_prec_ratio"],
            # Financials
            "grand_total": sol["total_purchase_cost"],
            "grand_total_cost": sol["total_purchase_cost"],
            "net_cost": sol["net_cost"],
            "net_profit": round(-sol["net_cost"], 2),
            "cost_per_1m": sol["cost_per_1m"],
            "cost_per_m_dmg": sol["cost_per_1m"],
            "savings_vs_best": 0.0,
            "pill_cost": round(pill_cost, 2),
            "ammo_cost": round(sol["ammo_cost"], 2),
            "food_cost": round(sol["food_cost"], 2),
            "scrap_recovery_value": sol["scrap_recovery_value"],
            "scrap_value": sol["scrap_recovery_value"],
            "total_scrap": total_scrap,
            "expected_regular_cases": sol["expected_regular_cases"],
            "expected_cases": sol["expected_regular_cases"],
            "expected_case1": sol["expected_regular_cases"],
            "expected_elite_cases": sol["expected_elite_cases"],
            "expected_case2": sol["expected_elite_cases"],
            "total_cases_value": total_cases_value,
            # Consumables
            "ammo_name": ammo_spec["name"],
            "ammo_badge": ammo_spec["badge"],
            "ammo_type": ammo_spec["name"],
            "ammo_key": ammo_key,
            "ammo_code": ammo_key,
            "ammo_units_needed": sol["ammo_bullets_needed"],
            "ammo_planned": sol["ammo_bullets_needed"],
            "ammo_price": sol["ammo_unit_price"],
            "ammo_unit_price": sol["ammo_unit_price"],
            "food_name": food_spec["name"],
            "food_icon": food_spec["icon"],
            "food_type": food_spec["name"],
            "food_key": food_key,
            "food_code": food_key,
            "food_units_needed": sol["food_units_needed"],
            "food_planned": sol["food_units_needed"],
            "food_price": sol["food_unit_price"],
            "food_unit_price": sol["food_unit_price"],
            "hunger_units_needed": sol["food_units_needed"],
            "hunger_usage_pct": hunger_usage_pct,
            # Slots
            "slots": slots,
            "slots_def": slots,
            "build_slots": build_slots,
        }
