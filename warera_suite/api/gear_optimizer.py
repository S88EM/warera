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
    from combat_constants import (
        FOOD_SPECS,
        AMMO_SPECS,
        SCRAP_RECOVERY_BY_TIER,
        DEFAULT_MARKET_PRICES,
        WEAPON_TIERS,
        TIER_NAMES,
        merge_live_consumables,
        extract_player_combat_profile,
        extract_loot_chance_ratio,
        estimate_expected_cases,
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
    from api.combat_constants import (
        FOOD_SPECS,
        AMMO_SPECS,
        SCRAP_RECOVERY_BY_TIER,
        DEFAULT_MARKET_PRICES,
        WEAPON_TIERS,
        TIER_NAMES,
        merge_live_consumables,
        extract_player_combat_profile,
        extract_loot_chance_ratio,
        estimate_expected_cases,
    )

logger = logging.getLogger("WarEraGearOptimizer")


class GearOptimizer:
    """
    Engine for finding the lowest-cost gear set to achieve target battle damage.
    """

    DEFAULT_ROLL_QUALITY = 0.50

    def __init__(self, market_app=None):
        self.market_app = market_app

    @staticmethod
    def _roll_stat(rng: List[float], roll_q: float) -> float:
        return rng[0] + (rng[1] - rng[0]) * roll_q

    @staticmethod
    def _simulate_combat_metrics(
        base_atk: float,
        curr_prec: float,
        curr_crit_ch: float,
        curr_crit_dmg: float,
        curr_armor_stat: float,
        curr_dodge_stat: float,
        rank_mult: float,
        battle_mult: float,
        ammo_mult: float,
        w_atk: float,
        w_crit_ch: float,
        h_crit_dmg: float,
        g_prec: float,
        c_arm: float,
        p_arm: float,
        b_ddg: float,
        pill_mult: float = 1.60,
    ) -> Tuple[float, float, float, float, float, float]:
        """Computes (avg_dmg_per_hit, hp_cost_per_hit, hits_per_armor_set, dodge_fraction, armor_reduction, eff_prec_ratio)."""
        raw_prec = curr_prec + g_prec
        if raw_prec > 100.0:
            prec_bonus_atk = (raw_prec - 100.0) * 4.0
            eff_prec_ratio = 1.0
        else:
            prec_bonus_atk = 0.0
            eff_prec_ratio = max(0.10, raw_prec / 100.0)

        raw_crit_ch = curr_crit_ch + w_crit_ch
        raw_crit_dmg = curr_crit_dmg + h_crit_dmg
        if raw_crit_ch > 100.0:
            crit_bonus_dmg = (raw_crit_ch - 100.0) * 4.0
            eff_crit_ch_ratio = 1.0
        else:
            crit_bonus_dmg = 0.0
            eff_crit_ch_ratio = max(0.0, raw_crit_ch / 100.0)

        crit_mult_val = (raw_crit_dmg + crit_bonus_dmg) / 100.0
        sim_atk = (base_atk + w_atk + prec_bonus_atk) * rank_mult * ammo_mult * pill_mult
        hit_dmg = sim_atk * (1.0 + eff_crit_ch_ratio * crit_mult_val)
        miss_dmg = sim_atk * 0.5
        avg_dmg_per_hit = (eff_prec_ratio * hit_dmg + (1.0 - eff_prec_ratio) * miss_dmg) * battle_mult

        total_raw_armor = curr_armor_stat + c_arm + p_arm
        total_raw_dodge = curr_dodge_stat + b_ddg
        armor_reduction = (total_raw_armor / (total_raw_armor + 40.0)) if total_raw_armor > 0 else 0.0
        dodge_fraction = (total_raw_dodge / (total_raw_dodge + 40.0)) if total_raw_dodge > 0 else 0.0
        hp_cost_per_hit = max(0.50, 10.0 * (1.0 - armor_reduction) * (1.0 - dodge_fraction))
        hits_per_armor_set = max(100.0, 100.0 * (1.0 + total_raw_dodge / 40.0))

        return avg_dmg_per_hit, hp_cost_per_hit, hits_per_armor_set, dodge_fraction, armor_reduction, eff_prec_ratio

    def optimize_set_for_target(
        self,
        player_member: Dict[str, Any],
        target_damage: float = 2_500_000.0,
        selected_ammo: str = "auto",
        selected_food: str = "auto",
        selected_weapon: str = "auto",
        battle_bonus: float = 84.0,
        custom_rank_bonus: Optional[float] = None,
        custom_prestige: Optional[int] = None,
        live_consumables: Optional[Dict[str, float]] = None,
        saved_build: Optional[Dict[str, Any]] = None,
        is_build_locked: bool = False,
    ) -> Dict[str, Any]:
        """
        Runs dual optimization to find the cheapest equipment setup that guarantees
        hitting target_damage (or target deficit) for the specified player.
        """
        # Load market prices
        market_cache = load_market_cheapest_cache()
        cached_items = market_cache.get("items", {})
        consumable_prices = merge_live_consumables(
            dict(market_cache.get("consumables", {})),
            live_consumables,
        )

        # Helper to get live or default item price (optionally filtered by minimum roll stats)
        def get_item_price(code: str, min_stats: Optional[Dict[str, float]] = None) -> float:
            if not code:
                return 0.0

            def _extract_offer_skills(offer: Dict[str, Any]) -> Dict[str, Any]:
                item_obj = offer.get("item")
                if isinstance(item_obj, dict) and isinstance(item_obj.get("skills"), dict):
                    return item_obj["skills"]
                skills_obj = offer.get("skills")
                return skills_obj if isinstance(skills_obj, dict) else {}

            def _matches_min_stats(skills_dict: Dict[str, Any]) -> bool:
                if not min_stats:
                    return True
                for stat_k, min_v in min_stats.items():
                    try:
                        if float(skills_dict.get(stat_k, 0) or 0) < float(min_v):
                            return False
                    except (ValueError, TypeError):
                        return False
                return True

            def _pick_from_offers(offers_list: Any) -> Optional[float]:
                if not isinstance(offers_list, list) or not offers_list:
                    return None
                parsed: List[Tuple[float, Dict[str, Any]]] = []
                for o in offers_list:
                    if not isinstance(o, dict):
                        continue
                    raw_p = o.get("price") or o.get("money")
                    if raw_p is None:
                        continue
                    try:
                        p_val = float(raw_p)
                    except (ValueError, TypeError):
                        continue
                    if p_val > 0:
                        parsed.append((p_val, _extract_offer_skills(o)))
                if not parsed:
                    return None
                parsed.sort(key=lambda x: x[0])
                if min_stats:
                    for p_val, sk in parsed:
                        if _matches_min_stats(sk):
                            return p_val
                return parsed[0][0]

            # 1. Prefer live in-memory offers from running EquipmentScannerApp
            if self.market_app is not None:
                live_offers_map = getattr(self.market_app, "latest_market_offers", None)
                if isinstance(live_offers_map, dict):
                    live_price = _pick_from_offers(live_offers_map.get(code))
                    if live_price is not None:
                        return live_price

            # 2. Fall back to persistent market_cheapest_cache.json
            item_entry = cached_items.get(code)
            if item_entry and isinstance(item_entry, dict):
                cached_offer_price = _pick_from_offers(item_entry.get("offers"))
                if cached_offer_price is not None:
                    return cached_offer_price
                for price_key in ("cheapest_price", "price"):
                    raw_val = item_entry.get(price_key)
                    if raw_val:
                        try:
                            val = float(raw_val)
                            if val > 0:
                                return val
                        except (ValueError, TypeError):
                            pass

            return float(DEFAULT_MARKET_PRICES.get(code, 20.0))

        # Player profile parameters
        profile = extract_player_combat_profile(
            player_member,
            custom_rank_bonus=custom_rank_bonus,
            custom_prestige=custom_prestige,
        )
        uname = profile["username"]
        lvl = profile["level"]
        skills = profile["skills"]
        prestige_val = profile["prestige"]
        total_skill_points = profile["total_skill_points"]
        rank_bonus_pct = profile["rank_bonus_pct"]
        rank_mult = profile["rank_mult"]

        # Dynamic battle bonus
        battle_bonus_val = max(0.0, float(battle_bonus if battle_bonus is not None else 84.0))
        battle_mult = 1.0 + (battle_bonus_val / 100.0)

        # Health & Hunger pools
        health_max = profile["health_max"]
        health_curr = profile["health_curr"]
        health_regen = profile["health_regen"]
        hunger_max = profile["hunger_max"]
        hunger_curr = profile["hunger_curr"]
        hunger_regen = profile["hunger_regen"]

        # Base character stats from skills (pure clean baseline + strategic buffs, without equipped gear)
        def _skill_with_strat(skill_name: str, default_val: float) -> float:
            sk = skills.get(skill_name) or {}
            return float(sk.get("value", default_val)) + float(sk.get("strategic", 0))

        base_atk = float(player_member.get("base_attack") or skills.get("attack", {}).get("value", 100)) + float(
            (skills.get("attack") or {}).get("strategic", 0)
        )
        curr_prec = _skill_with_strat("precision", 75)
        curr_crit_ch = _skill_with_strat("criticalChance", 10)
        curr_crit_dmg = _skill_with_strat("criticalDamages", 100)
        curr_armor_stat = _skill_with_strat("armor", 0)
        curr_dodge_stat = _skill_with_strat("dodge", 0)

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
        loot_chance_ratio = extract_loot_chance_ratio(player_member)

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

        # Weapons and Armor to evaluate: full spectrum from T2 to T6 without hardcoded restrictions
        # If user explicitly selected a weapon, pin weapon search to that tier
        w_sel = (selected_weapon or "auto").strip().lower()
        if w_sel in ("sniper", "4", "t4"):
            weapon_tier_choices = [4]
        elif w_sel in ("tank", "5", "t5"):
            weapon_tier_choices = [5]
        elif w_sel in ("rifle", "3", "t3"):
            weapon_tier_choices = [3]
        elif w_sel in ("jet", "6", "t6"):
            weapon_tier_choices = [6]
        elif w_sel in ("gun", "2", "t2"):
            weapon_tier_choices = [2]
        else:
            weapon_tier_choices = [2, 3, 4, 5, 6]

        armor_tier_choices = [2, 3, 4, 5, 6]
        roll_q = self.DEFAULT_ROLL_QUALITY

        # Precompute minStats-filtered market prices for all candidate gear codes
        slot_price_cache: Dict[str, float] = {}
        for wt in weapon_tier_choices:
            wc = WEAPON_TIERS[wt]
            slot_price_cache[wc] = get_item_price(wc, min_stats=self._default_min_stats_for_slot("weapon", wc, roll_q))
        for at in armor_tier_choices:
            for s_name, prefix in (("helmet", "helmet"), ("chest", "chest"), ("pants", "pants"), ("boots", "boots"), ("gloves", "gloves")):
                ac = f"{prefix}{at}"
                slot_price_cache[ac] = get_item_price(ac, min_stats=self._default_min_stats_for_slot(s_name, ac, roll_q))

        valid_solutions: List[Dict[str, Any]] = []

        # Dual Search: evaluate hybrid gear combinations using consistent roll_q and minStats prices
        for w_tier in weapon_tier_choices:
            w_code = WEAPON_TIERS[w_tier]
            w_ranges = EQUIPMENT_METADATA.get(w_code, {}).get("ranges", {})
            w_atk = self._roll_stat(w_ranges.get("attack", [80, 90]), roll_q)
            w_crit_ch = self._roll_stat(w_ranges.get("criticalChance", [10, 15]), roll_q)
            w_price = slot_price_cache[w_code]

            for ammo_key in eval_ammos:
                ammo_spec = AMMO_SPECS[ammo_key]
                ammo_unit_price = float(consumable_prices.get(ammo_key, ammo_spec["default_price"]))
                ammo_mult = 1.0 + (ammo_spec["bonus_pct"] / 100.0)

                for h_tier in armor_tier_choices:
                    h_code = f"helmet{h_tier}"
                    h_ranges = EQUIPMENT_METADATA.get(h_code, {}).get("ranges", {})
                    h_crit_dmg = self._roll_stat(h_ranges.get("criticalDamages", [40, 60]), roll_q)
                    h_price = slot_price_cache[h_code]

                    for g_tier in armor_tier_choices:
                        g_code = f"gloves{g_tier}"
                        g_ranges = EQUIPMENT_METADATA.get(g_code, {}).get("ranges", {})
                        g_prec = self._roll_stat(g_ranges.get("precision", [10, 15]), roll_q)
                        g_price = slot_price_cache[g_code]

                        avg_dmg_per_hit, _, _, _, _, eff_prec_ratio = self._simulate_combat_metrics(
                            base_atk, curr_prec, curr_crit_ch, curr_crit_dmg, curr_armor_stat, curr_dodge_stat,
                            rank_mult, battle_mult, ammo_mult,
                            w_atk, w_crit_ch, h_crit_dmg, g_prec, 0.0, 0.0, 0.0,
                        )

                        if avg_dmg_per_hit <= 0:
                            continue

                        min_hits_needed = math.ceil(deficit_damage / avg_dmg_per_hit) if deficit_damage > 0 else 0

                        for c_tier in armor_tier_choices:
                            c_code = f"chest{c_tier}"
                            c_arm = self._roll_stat(EQUIPMENT_METADATA.get(c_code, {}).get("ranges", {}).get("armor", [10, 15]), roll_q)
                            c_price = slot_price_cache[c_code]

                            for p_tier in armor_tier_choices:
                                p_code = f"pants{p_tier}"
                                p_arm = self._roll_stat(EQUIPMENT_METADATA.get(p_code, {}).get("ranges", {}).get("armor", [10, 15]), roll_q)
                                p_price = slot_price_cache[p_code]

                                for b_tier in armor_tier_choices:
                                    b_code = f"boots{b_tier}"
                                    b_ddg = self._roll_stat(EQUIPMENT_METADATA.get(b_code, {}).get("ranges", {}).get("dodge", [10, 15]), roll_q)
                                    b_price = slot_price_cache[b_code]

                                    _, hp_cost_per_hit, hits_per_armor_set, dodge_fraction, armor_reduction, _ = self._simulate_combat_metrics(
                                        base_atk, curr_prec, curr_crit_ch, curr_crit_dmg, curr_armor_stat, curr_dodge_stat,
                                        rank_mult, battle_mult, ammo_mult,
                                        w_atk, w_crit_ch, h_crit_dmg, g_prec, c_arm, p_arm, b_ddg,
                                    )

                                    for food_key in eval_foods:
                                        food_spec = FOOD_SPECS[food_key]
                                        food_hp_pct = food_spec["hp_pct"]
                                        food_unit_price = float(consumable_prices.get(food_key, food_spec["default_price"]))

                                        hp_per_food_unit = food_hp_pct * health_max
                                        max_food_units = math.floor(available_hunger)
                                        max_food_hp = max_food_units * hp_per_food_unit
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
                                        if food_units_needed > max_food_units:
                                            continue
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

                                        expected_regular_cases, expected_elite_cases = estimate_expected_cases(
                                            actual_hits, loot_chance_ratio, eff_prec_ratio
                                        )
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

        # Sort by Real Purchase Budget (User Rule: no case deductions, optimize strictly by real market purchase budget)
        valid_solutions.sort(key=lambda s: (s["total_purchase_cost"], s["actual_hits"]))

        combat_ctx = {
            "base_atk": base_atk,
            "curr_prec": curr_prec,
            "curr_crit_ch": curr_crit_ch,
            "curr_crit_dmg": curr_crit_dmg,
            "curr_armor_stat": curr_armor_stat,
            "curr_dodge_stat": curr_dodge_stat,
            "rank_mult": rank_mult,
            "battle_mult": battle_mult,
            "today_damage": today_damage,
            "natural_hp_pool": natural_hp_pool,
            "health_max": health_max,
            "available_hunger": available_hunger,
            "pill_cost": pill_cost,
            "scrap_price": scrap_price,
            "case1_price": case1_price,
            "case2_price": case2_price,
            "loot_chance_ratio": loot_chance_ratio,
        }

        # Select diverse representative strategies and tune rolls near ceil(hits/100) wear boundaries
        diverse_solutions = [
            self._tune_roll_to_save_wear(s, deficit_damage, combat_ctx, get_item_price)
            for s in self._select_diverse_solutions(valid_solutions)
        ]
        diverse_solutions.sort(key=lambda s: (s["total_purchase_cost"], s["actual_hits"]))
        best_sol = diverse_solutions[0]

        # Refine Minimum Roll Requirements for best solution
        refined_slots = self._format_and_refine_slots(best_sol, deficit_damage, get_item_price_fn=get_item_price)

        if saved_build and is_build_locked:
            saved_strat = self._build_saved_strategy_dict(
                saved_build=saved_build,
                deficit_damage=deficit_damage,
                pill_cost=pill_cost,
                available_hunger=available_hunger,
                case1_price=case1_price,
                case2_price=case2_price,
                scrap_price=scrap_price,
                natural_hp_pool=natural_hp_pool,
                health_max=health_max,
                loot_chance_ratio=loot_chance_ratio,
                target_damage=target_damage,
                consumable_prices=consumable_prices,
                get_item_price_fn=get_item_price,
                combat_ctx=combat_ctx,
            )
            best_strat = saved_strat
            all_strats = [saved_strat] + [
                self._build_strategy_dict(
                    s,
                    self._format_and_refine_slots(s, deficit_damage, get_item_price_fn=get_item_price),
                    pill_cost,
                    deficit_damage,
                    f"Альтернатива #{idx+1}",
                    is_best=False,
                    available_hunger=available_hunger,
                    case1_price=case1_price,
                    case2_price=case2_price,
                )
                for idx, s in enumerate(diverse_solutions)
            ]
        else:
            best_strat = self._build_strategy_dict(
                best_sol,
                refined_slots,
                pill_cost,
                deficit_damage,
                "Оптимальний мінімальний сет",
                is_best=True,
                available_hunger=available_hunger,
                case1_price=case1_price,
                case2_price=case2_price,
            )
            all_strats = [
                self._build_strategy_dict(
                    s,
                    self._format_and_refine_slots(s, deficit_damage, get_item_price_fn=get_item_price),
                    pill_cost,
                    deficit_damage,
                    "Оптимальний мінімальний сет" if idx == 0 else f"Альтернатива #{idx}",
                    is_best=(idx == 0),
                    available_hunger=available_hunger,
                    case1_price=case1_price,
                    case2_price=case2_price,
                )
                for idx, s in enumerate(diverse_solutions)
            ]

        # Build final formatted payload matching WarEra Suite schema
        return {
            "status": "ok",
            "is_build_locked": bool(saved_build and is_build_locked),
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
            "best_strategy": best_strat,
            "alternatives": all_strats[1:4],
            "strategies": all_strats,
            "consumable_prices": consumable_prices,
            "updated_at": market_cache.get("updated_at") or "",
        }

    @staticmethod
    def _select_diverse_solutions(valid_solutions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Selects diverse representative strategies across weapon tiers, food, and ammo."""
        best_sol = valid_solutions[0]
        diverse_solutions = [best_sol]
        seen_keys = {(best_sol["w_tier"], best_sol["food_key"], best_sol["ammo_key"])}

        for sol in valid_solutions[1:]:
            w_tier = sol["w_tier"]
            if not any(s["w_tier"] == w_tier for s in diverse_solutions):
                diverse_solutions.append(sol)
                seen_keys.add((w_tier, sol["food_key"], sol["ammo_key"]))

        for sol in valid_solutions[1:]:
            tier_key = (sol["w_tier"], sol["food_key"], sol["ammo_key"])
            if tier_key not in seen_keys and len(diverse_solutions) < 8:
                diverse_solutions.append(sol)
                seen_keys.add(tier_key)

        for sol in valid_solutions[1:]:
            if sol not in diverse_solutions:
                diverse_solutions.append(sol)
            if len(diverse_solutions) >= 6:
                break

        return diverse_solutions

    def _tune_roll_to_save_wear(
        self,
        sol: Dict[str, Any],
        deficit_damage: float,
        combat_ctx: Dict[str, Any],
        get_item_price_fn,
    ) -> Dict[str, Any]:
        """
        Checks if raising roll quality (0.60..0.90) reduces weapons_needed or armor_sets_needed
        across ceil() wear boundaries and lowers total_purchase_cost.
        """
        if deficit_damage <= 0:
            return sol

        best = dict(sol)
        best.setdefault("roll_quality", self.DEFAULT_ROLL_QUALITY)
        ammo_spec = sol["ammo_spec"]
        ammo_mult = 1.0 + (ammo_spec["bonus_pct"] / 100.0)
        food_spec = sol["food_spec"]
        hp_per_food_unit = food_spec["hp_pct"] * combat_ctx["health_max"]
        max_food_units = math.floor(combat_ctx["available_hunger"])

        for cand_q in (0.60, 0.70, 0.80, 0.90):
            w_rng = EQUIPMENT_METADATA.get(sol["w_code"], {}).get("ranges", {})
            w_atk = self._roll_stat(w_rng.get("attack", [80, 90]), cand_q)
            w_crit = self._roll_stat(w_rng.get("criticalChance", [10, 15]), cand_q)
            h_cd = self._roll_stat(EQUIPMENT_METADATA.get(sol["h_code"], {}).get("ranges", {}).get("criticalDamages", [40, 60]), cand_q)
            g_prc = self._roll_stat(EQUIPMENT_METADATA.get(sol["g_code"], {}).get("ranges", {}).get("precision", [10, 15]), cand_q)
            c_arm = self._roll_stat(EQUIPMENT_METADATA.get(sol["c_code"], {}).get("ranges", {}).get("armor", [10, 15]), cand_q)
            p_arm = self._roll_stat(EQUIPMENT_METADATA.get(sol["p_code"], {}).get("ranges", {}).get("armor", [10, 15]), cand_q)
            b_ddg = self._roll_stat(EQUIPMENT_METADATA.get(sol["b_code"], {}).get("ranges", {}).get("dodge", [10, 15]), cand_q)

            avg_dmg, hp_cost, hits_per_armor, dodge_frac, arm_red, eff_prec = self._simulate_combat_metrics(
                combat_ctx["base_atk"], combat_ctx["curr_prec"], combat_ctx["curr_crit_ch"],
                combat_ctx["curr_crit_dmg"], combat_ctx["curr_armor_stat"], combat_ctx["curr_dodge_stat"],
                combat_ctx["rank_mult"], combat_ctx["battle_mult"], ammo_mult,
                w_atk, w_crit, h_cd, g_prc, c_arm, p_arm, b_ddg,
            )
            if avg_dmg <= 0:
                continue

            hits = math.ceil(deficit_damage / avg_dmg)
            weapons_needed = math.ceil(hits / 100.0)
            armor_sets_needed = math.ceil(hits / hits_per_armor)
            if weapons_needed >= best["weapons_needed"] and armor_sets_needed >= best["armor_sets_needed"]:
                continue

            food_hp_needed = max(0.0, hits * hp_cost - combat_ctx["natural_hp_pool"])
            food_units = math.ceil(food_hp_needed / hp_per_food_unit) if hp_per_food_unit > 0 else 0
            if food_units > max_food_units:
                continue

            w_p = get_item_price_fn(sol["w_code"], min_stats=self._default_min_stats_for_slot("weapon", sol["w_code"], cand_q))
            h_p = get_item_price_fn(sol["h_code"], min_stats=self._default_min_stats_for_slot("helmet", sol["h_code"], cand_q))
            c_p = get_item_price_fn(sol["c_code"], min_stats=self._default_min_stats_for_slot("chest", sol["c_code"], cand_q))
            p_p = get_item_price_fn(sol["p_code"], min_stats=self._default_min_stats_for_slot("pants", sol["p_code"], cand_q))
            b_p = get_item_price_fn(sol["b_code"], min_stats=self._default_min_stats_for_slot("boots", sol["b_code"], cand_q))
            g_p = get_item_price_fn(sol["g_code"], min_stats=self._default_min_stats_for_slot("gloves", sol["g_code"], cand_q))

            ammo_c = hits * sol["ammo_unit_price"]
            food_c = food_units * sol["food_unit_price"]
            armor_set_p = h_p + c_p + p_p + b_p + g_p
            total_cost = round((weapons_needed * w_p) + (armor_sets_needed * armor_set_p) + ammo_c + food_c + combat_ctx["pill_cost"], 2)

            if total_cost < best["total_purchase_cost"]:
                amort_gear = (hits / 100.0) * w_p + (hits / hits_per_armor) * armor_set_p
                amort_gross = amort_gear + ammo_c + food_c + combat_ctx["pill_cost"]
                scrap_val = (
                    SCRAP_RECOVERY_BY_TIER.get(sol["w_tier"], 0) * max(1, weapons_needed)
                    + sum(SCRAP_RECOVERY_BY_TIER.get(sol[k], 0) for k in ("h_tier", "c_tier", "p_tier", "b_tier", "g_tier")) * max(1, armor_sets_needed)
                ) * combat_ctx["scrap_price"]
                exp_c1, exp_c2 = estimate_expected_cases(hits, combat_ctx["loot_chance_ratio"], eff_prec)
                case_val = exp_c1 * combat_ctx["case1_price"] + exp_c2 * combat_ctx["case2_price"]
                net_c = amort_gross - scrap_val - case_val
                best.update({
                    "roll_quality": cand_q,
                    "w_price": w_p, "w_atk": w_atk, "w_crit_ch": w_crit,
                    "h_price": h_p, "h_crit_dmg": h_cd,
                    "c_price": c_p, "c_arm": c_arm,
                    "p_price": p_p, "p_arm": p_arm,
                    "b_price": b_p, "b_ddg": b_ddg,
                    "g_price": g_p, "g_prec": g_prc,
                    "ammo_cost": ammo_c, "ammo_bullets_needed": hits,
                    "food_cost": food_c, "food_units_needed": food_units,
                    "avg_dmg_per_hit": round(avg_dmg, 1),
                    "hp_cost_per_hit": round(hp_cost, 2),
                    "actual_hits": hits,
                    "weapons_needed": weapons_needed,
                    "armor_sets_needed": armor_sets_needed,
                    "total_purchase_cost": total_cost,
                    "amortized_gross_cost": round(amort_gross, 2),
                    "net_cost": round(net_c, 2),
                    "cost_per_1m": round(net_c / (deficit_damage / 1_000_000.0), 2),
                    "expected_regular_cases": round(exp_c1, 1),
                    "expected_elite_cases": round(exp_c2, 2),
                    "scrap_recovery_value": round(scrap_val, 2),
                    "eff_dodge_pct": round(dodge_frac * 100.0, 1),
                    "eff_armor_pct": round(arm_red * 100.0, 1),
                    "eff_prec_ratio": round(eff_prec, 3),
                    "eff_w_atk": round(w_atk, 1),
                })

        return best

    @staticmethod
    def _default_min_stats_for_slot(slot_type: str, code: str, roll_q: float = 0.50) -> Dict[str, float]:
        """Returns the recommended minimum stat thresholds for a gear slot at roll_q."""
        ranges = EQUIPMENT_METADATA.get(code, {}).get("ranges", {})
        if slot_type == "weapon":
            atk_r = ranges.get("attack", [100, 130])
            crit_r = ranges.get("criticalChance", [15, 20])
            return {
                "attack": int(atk_r[0] + (atk_r[1] - atk_r[0]) * roll_q),
                "criticalChance": int(crit_r[0] + (crit_r[1] - crit_r[0]) * roll_q),
            }
        if slot_type == "helmet":
            cd_r = ranges.get("criticalDamages", [70, 90])
            return {"criticalDamages": int(cd_r[0] + (cd_r[1] - cd_r[0]) * roll_q)}
        if slot_type in ("chest", "pants"):
            arm_r = ranges.get("armor", [20, 30])
            return {"armor": int(arm_r[0] + (arm_r[1] - arm_r[0]) * roll_q)}
        if slot_type == "boots":
            ddg_r = ranges.get("dodge", [20, 25])
            return {"dodge": int(ddg_r[0] + (ddg_r[1] - ddg_r[0]) * roll_q)}
        if slot_type == "gloves":
            prc_r = ranges.get("precision", [20, 25])
            return {"precision": int(prc_r[0] + (prc_r[1] - prc_r[0]) * roll_q)}
        return {}

    def _format_and_refine_slots(
        self,
        sol: Dict[str, Any],
        deficit_damage: float,
        get_item_price_fn=None,
    ) -> Dict[str, Any]:
        """
        Determines the exact minimum rolls required for each slot so the fighter
        knows the minimum acceptable stats to buy on the market.
        """
        slots = {}
        roll_q = float(sol.get("roll_quality", self.DEFAULT_ROLL_QUALITY))
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
            min_stats = self._default_min_stats_for_slot(slot_type, code, roll_q=roll_q)

            if get_item_price_fn is not None:
                price = get_item_price_fn(code, min_stats=min_stats)

            # Format recommended minimum roll
            if slot_type == "weapon":
                rec_atk = int(min_stats["attack"])
                rec_crit = int(min_stats["criticalChance"])
                roll_desc = f"🗡 {rec_atk}+ Атака • 🎯 {rec_crit}%+ Крит"
                roll_badge = f"🗡 {rec_atk} 🎯 {rec_crit}%"
                qty = sol["weapons_needed"]
            elif slot_type == "helmet":
                rec_cd = int(min_stats["criticalDamages"])
                roll_desc = f"💥 {rec_cd}%+ Крит. урон"
                roll_badge = f"💥 {rec_cd}%"
                qty = sol["armor_sets_needed"]
            elif slot_type in ("chest", "pants"):
                rec_arm = int(min_stats["armor"])
                roll_desc = f"🛡 {rec_arm}+ Броня"
                roll_badge = f"🛡 {rec_arm}"
                qty = sol["armor_sets_needed"]
            elif slot_type == "boots":
                rec_ddg = int(min_stats["dodge"])
                roll_desc = f"💨 {rec_ddg}+ Ухилення"
                roll_badge = f"💨 {rec_ddg}"
                qty = sol["armor_sets_needed"]
            elif slot_type == "gloves":
                rec_prc = int(min_stats["precision"])
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

        weapon_ukr_names = {
            "knife": "Ніж",
            "gun": "Пістолет",
            "rifle": "Гвинтівка",
            "sniper": "Снайперка",
            "tank": "Танк",
            "jet": "Літак",
        }
        w_label_ukr = weapon_ukr_names.get(sol["w_code"], sol["w_code"].capitalize())
        build_title = f"🔥 {w_label_ukr} T{sol['w_tier']} · Гібрид"

        return {
            "strategy_key": strat_key,
            "name": name,
            "label": build_title,
            "badge": build_title,
            "tier_num": sol["w_tier"],
            "roll_quality": sol.get("roll_quality", self.DEFAULT_ROLL_QUALITY),
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
            # Financials (keep grand_total synced with refined slot prices)
            "grand_total": round(sum(s["total_cost"] for s in slots.values()) + sol["ammo_cost"] + sol["food_cost"] + pill_cost, 2),
            "grand_total_cost": round(sum(s["total_cost"] for s in slots.values()) + sol["ammo_cost"] + sol["food_cost"] + pill_cost, 2),
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
            "available_hunger": round(available_hunger, 1),
            "hunger_units_needed": sol["food_units_needed"],
            "hunger_usage_pct": hunger_usage_pct,
            # Slots
            "slots": slots,
            "slots_def": slots,
            "build_slots": build_slots,
            "is_saved_build": False,
            "sol_meta": {
                "w_tier": sol["w_tier"], "w_code": sol["w_code"], "w_price": sol["w_price"],
                "h_tier": sol["h_tier"], "h_code": sol["h_code"], "h_price": sol["h_price"],
                "c_tier": sol["c_tier"], "c_code": sol["c_code"], "c_price": sol["c_price"],
                "p_tier": sol["p_tier"], "p_code": sol["p_code"], "p_price": sol["p_price"],
                "b_tier": sol["b_tier"], "b_code": sol["b_code"], "b_price": sol["b_price"],
                "g_tier": sol["g_tier"], "g_code": sol["g_code"], "g_price": sol["g_price"],
                "ammo_key": ammo_key, "food_key": food_key,
                "avg_dmg_per_hit": sol["avg_dmg_per_hit"],
                "hp_cost_per_hit": sol["hp_cost_per_hit"],
                "eff_dodge_pct": sol.get("eff_dodge_pct", 0),
                "eff_armor_pct": sol.get("eff_armor_pct", 0),
                "eff_prec_ratio": sol.get("eff_prec_ratio", 1.0),
                "weapons_needed": sol["weapons_needed"],
                "armor_sets_needed": sol["armor_sets_needed"],
            },
        }

    def _build_saved_strategy_dict(
        self,
        saved_build: Dict[str, Any],
        deficit_damage: float,
        pill_cost: float,
        available_hunger: float = 7.0,
        case1_price: float = 3.89,
        case2_price: float = 27.19,
        scrap_price: float = 0.26,
        natural_hp_pool: float = 150.0,
        health_max: float = 150.0,
        loot_chance_ratio: float = 0.05,
        target_damage: float = 2_500_000.0,
        consumable_prices: Optional[Dict[str, float]] = None,
        get_item_price_fn=None,
        combat_ctx: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Recalculates an existing locked/saved strategy for the active remaining deficit_damage.
        Preserves the EXACT gear slots (weapon, armor tiers, rolls, ammo, food) selected by the user,
        while recalculating avg_dmg_per_hit and hp_cost_per_hit for current battle_bonus/rank/prestige.
        """
        consumable_prices = consumable_prices or {}
        sol_meta = saved_build.get("sol_meta") or {}

        food_key = saved_build.get("food_key") or saved_build.get("food") or sol_meta.get("food_key") or "cookedFish"
        food_spec = FOOD_SPECS.get(food_key, FOOD_SPECS["cookedFish"])
        food_unit_price = float(consumable_prices.get(food_key) or saved_build.get("food_unit_price") or saved_build.get("food_price") or 10.0)

        ammo_key = saved_build.get("ammo_key") or saved_build.get("ammo") or sol_meta.get("ammo_key") or "lightAmmo"
        ammo_spec = AMMO_SPECS.get(ammo_key, AMMO_SPECS["lightAmmo"])
        ammo_unit_price = float(consumable_prices.get(ammo_key) or saved_build.get("ammo_unit_price") or saved_build.get("ammo_price") or 0.5)

        # Resolve gear codes from build_slots, sol_meta, or legacy top-level keys
        slot_codes: Dict[str, str] = {}
        for slot_item in saved_build.get("build_slots") or []:
            st = slot_item.get("slot")
            ic = slot_item.get("item_code")
            if st and ic:
                slot_codes[st] = ic
        w_code = slot_codes.get("weapon") or sol_meta.get("w_code") or saved_build.get("weapon")
        h_code = slot_codes.get("helmet") or sol_meta.get("h_code") or saved_build.get("helmet")
        c_code = slot_codes.get("chest") or sol_meta.get("c_code") or saved_build.get("chest")
        p_code = slot_codes.get("pants") or sol_meta.get("p_code") or saved_build.get("pants")
        b_code = slot_codes.get("boots") or sol_meta.get("b_code") or saved_build.get("boots")
        g_code = slot_codes.get("gloves") or sol_meta.get("g_code") or saved_build.get("gloves")

        roll_q = float(saved_build.get("roll_quality") or sol_meta.get("roll_quality") or self.DEFAULT_ROLL_QUALITY)
        if combat_ctx and w_code and h_code and c_code and p_code and b_code and g_code:
            w_rng = EQUIPMENT_METADATA.get(w_code, {}).get("ranges", {})
            w_atk = self._roll_stat(w_rng.get("attack", [80, 90]), roll_q)
            w_crit = self._roll_stat(w_rng.get("criticalChance", [10, 15]), roll_q)
            h_cd = self._roll_stat(EQUIPMENT_METADATA.get(h_code, {}).get("ranges", {}).get("criticalDamages", [40, 60]), roll_q)
            g_prc = self._roll_stat(EQUIPMENT_METADATA.get(g_code, {}).get("ranges", {}).get("precision", [10, 15]), roll_q)
            c_arm = self._roll_stat(EQUIPMENT_METADATA.get(c_code, {}).get("ranges", {}).get("armor", [10, 15]), roll_q)
            p_arm = self._roll_stat(EQUIPMENT_METADATA.get(p_code, {}).get("ranges", {}).get("armor", [10, 15]), roll_q)
            b_ddg = self._roll_stat(EQUIPMENT_METADATA.get(b_code, {}).get("ranges", {}).get("dodge", [10, 15]), roll_q)
            ammo_mult = 1.0 + (ammo_spec["bonus_pct"] / 100.0)
            sim_dmg, sim_hp, _, dodge_frac, arm_red, eff_prec_ratio = self._simulate_combat_metrics(
                combat_ctx["base_atk"], combat_ctx["curr_prec"], combat_ctx["curr_crit_ch"],
                combat_ctx["curr_crit_dmg"], combat_ctx["curr_armor_stat"], combat_ctx["curr_dodge_stat"],
                combat_ctx["rank_mult"], combat_ctx["battle_mult"], ammo_mult,
                w_atk, w_crit, h_cd, g_prc, c_arm, p_arm, b_ddg,
            )
            avg_dmg_per_hit = round(sim_dmg, 1)
            hp_cost_per_hit = round(sim_hp, 2)
            eff_dodge = round(dodge_frac * 100.0, 1)
            eff_armor = round(arm_red * 100.0, 1)
        else:
            avg_dmg_per_hit = float(saved_build.get("avg_dmg_per_hit") or sol_meta.get("avg_dmg_per_hit") or 7000.0)
            hp_cost_per_hit = float(saved_build.get("hp_cost_per_hit") or sol_meta.get("hp_cost_per_hit") or 35.0)
            eff_dodge = float(saved_build.get("eff_dodge") or sol_meta.get("eff_dodge_pct") or 50.0)
            eff_armor = float(saved_build.get("eff_armor") or sol_meta.get("eff_armor_pct") or 30.0)
            eff_prec_ratio = float(saved_build.get("eff_precision") or sol_meta.get("eff_prec_ratio") or 1.0)

        # Hits needed for remaining deficit
        if deficit_damage > 0:
            actual_hits = math.ceil(deficit_damage / max(1.0, avg_dmg_per_hit))
        else:
            actual_hits = 0

        ammo_bullets_needed = actual_hits
        ammo_cost = round(ammo_bullets_needed * ammo_unit_price, 2)

        hp_per_food_unit = food_spec["hp_pct"] * health_max
        total_hp_spent = actual_hits * hp_cost_per_hit
        food_hp_needed = max(0.0, total_hp_spent - natural_hp_pool)
        food_units_needed = math.ceil(food_hp_needed / hp_per_food_unit) if hp_per_food_unit > 0 else 0
        food_cost = round(food_units_needed * food_unit_price, 2)

        weapons_needed = math.ceil(actual_hits / 100.0) if actual_hits > 0 else (1 if deficit_damage > 0 else 0)
        hits_per_armor_set = 100.0 / max(0.05, 1.0 - (eff_dodge / 100.0))
        armor_sets_needed = math.ceil(actual_hits / hits_per_armor_set) if actual_hits > 0 else (1 if deficit_damage > 0 else 0)

        # Clone and update build_slots
        old_slots = saved_build.get("build_slots") or []
        updated_slots = []
        gear_purchase_cost = 0.0

        w_tier = sol_meta.get("w_tier") or saved_build.get("tier_num") or 5
        h_tier = sol_meta.get("h_tier", 4)
        c_tier = sol_meta.get("c_tier", 4)
        p_tier = sol_meta.get("p_tier", 4)
        b_tier = sol_meta.get("b_tier", 5)
        g_tier = sol_meta.get("g_tier", 5)

        refreshed_gear_unit_prices: Dict[str, float] = {}
        for slot_item in old_slots:
            item = dict(slot_item)
            s_type = item.get("slot")
            item_code = item.get("item_code")
            u_price = float(item.get("unit_price") or 0.0)
            if get_item_price_fn is not None and item_code and s_type in ("weapon", "helmet", "chest", "pants", "boots", "gloves"):
                min_stats = self._default_min_stats_for_slot(s_type, item_code, roll_q=roll_q)
                u_price = get_item_price_fn(item_code, min_stats=min_stats)
                item["unit_price"] = round(u_price, 2)
                refreshed_gear_unit_prices[s_type] = u_price

            if s_type == "weapon":
                item["qty_needed"] = weapons_needed
                item["total_price"] = round(weapons_needed * u_price, 2)
                item["stat_badge"] = f"{weapons_needed} шт"
                gear_purchase_cost += item["total_price"]
            elif s_type in ("helmet", "chest", "pants", "boots", "gloves"):
                item["qty_needed"] = armor_sets_needed
                item["total_price"] = round(armor_sets_needed * u_price, 2)
                gear_purchase_cost += item["total_price"]
            elif s_type == "ammo":
                item["qty_needed"] = ammo_bullets_needed
                item["total_price"] = ammo_cost
                item["unit_price"] = ammo_unit_price
                item["stat_badge"] = f"{ammo_bullets_needed} шт"
            elif s_type == "food":
                item["qty_needed"] = food_units_needed
                item["total_price"] = food_cost
                item["unit_price"] = food_unit_price
                item["stat_badge"] = f"{food_units_needed} шт"

            updated_slots.append(item)

        total_purchase_cost = round(gear_purchase_cost + ammo_cost + food_cost + pill_cost, 2)

        # Durability & Economic recovery for remaining deficit
        weapon_decay_ratio = actual_hits / 100.0
        armor_decay_ratio = actual_hits / hits_per_armor_set if hits_per_armor_set > 0 else 0
        weapon_price = refreshed_gear_unit_prices.get("weapon") or float(sol_meta.get("w_price") or 40.0)
        armor_slot_map = [("helmet", "h"), ("chest", "c"), ("pants", "p"), ("boots", "b"), ("gloves", "g")]
        armor_price = float(sum(
            refreshed_gear_unit_prices.get(s_name) or sol_meta.get(f"{k}_price", 20.0)
            for s_name, k in armor_slot_map
        ))
        amortized_gear_cost = (weapon_decay_ratio * weapon_price) + (armor_decay_ratio * armor_price)
        amortized_gross_cost = amortized_gear_cost + ammo_cost + food_cost + pill_cost

        weapon_scrap = SCRAP_RECOVERY_BY_TIER.get(w_tier, 0) * max(1, weapons_needed)
        armor_scrap = (
            SCRAP_RECOVERY_BY_TIER.get(h_tier, 0)
            + SCRAP_RECOVERY_BY_TIER.get(c_tier, 0)
            + SCRAP_RECOVERY_BY_TIER.get(p_tier, 0)
            + SCRAP_RECOVERY_BY_TIER.get(b_tier, 0)
            + SCRAP_RECOVERY_BY_TIER.get(g_tier, 0)
        ) * max(1, armor_sets_needed)
        total_scrap = weapon_scrap + armor_scrap
        scrap_recovery_value = round(total_scrap * scrap_price, 2)

        expected_regular_cases, expected_elite_cases = estimate_expected_cases(
            actual_hits, loot_chance_ratio, eff_prec_ratio
        )
        expected_regular_cases = round(expected_regular_cases, 1)
        expected_elite_cases = round(expected_elite_cases, 2)
        total_cases_value = round((expected_regular_cases * case1_price) + (expected_elite_cases * case2_price), 2)

        net_cost = round(amortized_gross_cost - scrap_recovery_value - total_cases_value, 2)
        cost_per_1m = round((net_cost / (deficit_damage / 1_000_000.0)), 2) if deficit_damage > 0 else 0.0

        hunger_usage_pct = round((food_units_needed / max(0.1, available_hunger)) * 100.0, 1)

        result_strat = dict(saved_build)
        # Normalize legacy English weapon labels in previously saved builds
        legacy_label = str(result_strat.get("label") or "")
        for eng, ukr in (("Sniper", "Снайперка"), ("Tank", "Танк"), ("Rifle", "Гвинтівка"), ("Gun", "Пістолет"), ("Knife", "Ніж"), ("Jet", "Літак")):
            if eng in legacy_label:
                legacy_label = legacy_label.replace(eng, ukr).replace(" Гібрид", " · Гібрид")
        if legacy_label:
            result_strat["label"] = legacy_label
            if result_strat.get("badge"):
                result_strat["badge"] = legacy_label

        init_target_dmg = float(saved_build.get("initial_target_damage") or target_damage)
        init_today_dmg = float(saved_build.get("initial_today_damage") or 0.0)
        curr_today_dmg = float((combat_ctx or {}).get("today_damage") or 0.0)
        build_planned_dmg = max(0.0, init_target_dmg - init_today_dmg)
        build_dealt_dmg = max(0.0, curr_today_dmg - init_today_dmg)
        build_progress_pct = round(min(100.0, (build_dealt_dmg / build_planned_dmg) * 100.0), 1) if build_planned_dmg > 0 else 100.0

        result_strat.update({
            "is_saved_build": True,
            "is_best_value": True,
            "avg_dmg_per_hit": avg_dmg_per_hit,
            "avg_damage_per_hit": avg_dmg_per_hit,
            "hp_cost_per_hit": hp_cost_per_hit,
            "eff_dodge": eff_dodge,
            "eff_armor": eff_armor,
            "eff_precision": eff_prec_ratio,
            "hits_needed": actual_hits,
            "hits_planned": actual_hits,
            "weapons_burned": weapons_needed,
            "weapons_needed": weapons_needed,
            "armor_sets_burned": armor_sets_needed,
            "armor_sets_needed": armor_sets_needed,
            "ammo_units_needed": ammo_bullets_needed,
            "ammo_planned": ammo_bullets_needed,
            "ammo_cost": ammo_cost,
            "ammo_price": ammo_unit_price,
            "ammo_unit_price": ammo_unit_price,
            "food_units_needed": food_units_needed,
            "food_planned": food_units_needed,
            "food_cost": food_cost,
            "food_price": food_unit_price,
            "food_unit_price": food_unit_price,
            "available_hunger": round(available_hunger, 1),
            "hunger_units_needed": food_units_needed,
            "hunger_usage_pct": hunger_usage_pct,
            "grand_total": total_purchase_cost,
            "grand_total_cost": total_purchase_cost,
            "net_cost": net_cost,
            "net_profit": round(-net_cost, 2),
            "cost_per_1m": cost_per_1m,
            "cost_per_m_dmg": cost_per_1m,
            "total_scrap": total_scrap,
            "scrap_recovery_value": scrap_recovery_value,
            "scrap_value": scrap_recovery_value,
            "expected_regular_cases": expected_regular_cases,
            "expected_case1": expected_regular_cases,
            "expected_elite_cases": expected_elite_cases,
            "expected_case2": expected_elite_cases,
            "total_cases_value": total_cases_value,
            "build_slots": updated_slots,
            "reach_status": "ok" if hunger_usage_pct <= 100 else "over_cap",
            "reach_badge": "✅ Досяжно" if hunger_usage_pct <= 100 else "❌ Переліміт голоду",
            "reach_note": "Вкладається в 1 сесію (8 год)" if hunger_usage_pct <= 100 else "Не вміститься в 1 сесію",
            "initial_target_damage": init_target_dmg,
            "initial_today_damage": init_today_dmg,
            "build_planned_damage": round(build_planned_dmg, 0),
            "build_dealt_damage": round(build_dealt_dmg, 0),
            "build_progress_pct": build_progress_pct,
            "initial_grand_total": saved_build.get("initial_grand_total") or saved_build.get("grand_total_cost"),
            "initial_hits": saved_build.get("initial_hits") or saved_build.get("hits_needed"),
        })
        return result_strat
