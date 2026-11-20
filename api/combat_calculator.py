"""
WarEra Combat Damage & Gear Calculator Service.
Calculates resources and equipment upgrades required for a fighter to achieve a target damage goal:
- Target damage deficit
- Required combat hits and effective HP pool
- Consumables required (Cooked Fish / Steaks / Pills) based on natural regen + hunger restoration
- Real-time market equipment recommendations with cheapest active prices and direct purchase links
"""

import math
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger("WarEraCombatCalculator")

# Consumable food HP recovery rates (% of character max HP per hunger unit)
FOOD_SPECS = {
    "cookedFish": {"name": "Смажена риба", "hp_pct": 0.20, "default_price": 140.0},
    "fish": {"name": "Сира риба", "hp_pct": 0.12, "default_price": 90.0},
    "steak": {"name": "Стейк", "hp_pct": 0.15, "default_price": 110.0},
    "bread": {"name": "Хліб", "hp_pct": 0.10, "default_price": 50.0},
}

# Gear slots to consider for combat upgrades
COMBAT_GEAR_SLOTS = ["weapon", "helmet", "chest", "pants", "boots", "gloves"]


class CombatDamageCalculator:
    def __init__(self, market_app=None):
        self.market_app = market_app

    def calculate_plan(
        self,
        player_member: Dict[str, Any],
        target_damage: float = 5_000_000.0,
        use_pill: bool = True,
        use_fish: bool = True,
        gear_tier: str = "epic", # "current", "epic", "legendary"
        custom_fish_price: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Calculates the complete shopping list and action plan for a player to reach `target_damage`.
        """
        uname = player_member.get("username", "Боєць")
        lvl = player_member.get("level", 1)
        skills = player_member.get("skills", {})

        # Base player stats
        atk_skill = skills.get("attack", {})
        base_atk = float(atk_skill.get("value", 100))
        health_skill = skills.get("health", {})
        health_max = float(health_skill.get("total", 100))
        health_curr = float(health_skill.get("currentBarValue", health_max))
        health_regen = float(health_skill.get("hourlyBarRegen") or (health_max * 0.10))

        hunger_skill = skills.get("hunger", {})
        hunger_max = float(hunger_skill.get("total", 4))
        hunger_curr = float(hunger_skill.get("currentBarValue", hunger_max))
        hunger_regen = float(hunger_skill.get("hourlyBarRegen") or (hunger_max * 0.10))

        # 1. Gear stats (Current vs Upgraded)
        equipped_armor = float(skills.get("armor", {}).get("equipment", 0))
        equipped_dodge = float(skills.get("dodge", {}).get("equipment", 0))
        equipped_weapon_atk = float(atk_skill.get("weapon", 0))

        # Target baseline adjustments
        gear_bonus_atk = 150.0 if gear_tier in ("epic", "legendary") else equipped_weapon_atk
        gear_bonus_armor = 24.0 if gear_tier in ("epic", "legendary") else equipped_armor
        gear_bonus_dodge = 18.0 if gear_tier in ("epic", "legendary") else equipped_dodge

        curr_armor_stat = float(skills.get("armor", {}).get("value", 0))
        curr_dodge_stat = float(skills.get("dodge", {}).get("value", 0))

        total_armor = curr_armor_stat + max(equipped_armor, gear_bonus_armor)
        total_dodge = curr_dodge_stat + max(equipped_dodge, gear_bonus_dodge)

        # Softcap calculations (softcap at 40%, 50% above)
        eff_armor = min(total_armor, 40.0) + max(0.0, total_armor - 40.0) * 0.5
        eff_dodge = min(total_dodge, 40.0) + max(0.0, total_dodge - 40.0) * 0.5

        # 2. HP cost per hit
        base_hit_cost = 10.0
        hp_cost_per_hit = base_hit_cost * (1.0 - (eff_armor / 100.0)) * (1.0 - (eff_dodge / 100.0))
        hp_cost_per_hit = max(hp_cost_per_hit, 0.8)

        # 3. Damage per hit
        rank_bonus_pct = float(atk_skill.get("militaryRankPercent", 0.0))
        ammo_bonus_pct = float(atk_skill.get("ammoPercent", 20.0))
        pill_multiplier = 1.60 if use_pill else 1.0

        simulated_atk = (base_atk + max(equipped_weapon_atk, gear_bonus_atk)) * (1.0 + (rank_bonus_pct + ammo_bonus_pct) / 100.0) * pill_multiplier

        curr_crit_chance = float(skills.get("criticalChance", {}).get("value", 10))
        curr_crit_dmg = float(skills.get("criticalDamages", {}).get("value", 100))
        crit_multiplier = 1.0 + ((curr_crit_chance / 100.0) * (curr_crit_dmg / 100.0))

        mu_order_bonus = 1.10
        avg_dmg_per_hit = simulated_atk * crit_multiplier * mu_order_bonus

        # 4. Hits required to achieve target damage
        if avg_dmg_per_hit <= 0:
            avg_dmg_per_hit = 100.0
        total_hits_needed = math.ceil(target_damage / avg_dmg_per_hit)
        total_hp_needed = total_hits_needed * hp_cost_per_hit

        # 5. Natural HP generation (initial full bar + 24h natural regen)
        natural_hp_pool = health_max + (24.0 * health_regen)
        hp_deficit = max(0.0, total_hp_needed - natural_hp_pool)

        # 6. Food requirement (Cooked Fish or Steak)
        food_key = "cookedFish" if use_fish else "steak"
        food_spec = FOOD_SPECS[food_key]
        hp_per_food_unit = health_max * food_spec["hp_pct"]

        food_units_needed = math.ceil(hp_deficit / hp_per_food_unit) if hp_per_food_unit > 0 else 0
        fish_price = custom_fish_price if custom_fish_price is not None else food_spec["default_price"]
        food_total_cost = round(food_units_needed * fish_price, 2)

        # 7. Live Market Equipment Recommendations
        recommended_gear = []
        gear_total_cost = 0.0

        if self.market_app and gear_tier in ("epic", "legendary"):
            try:
                # Query cheapest items from market cache
                cheapest_items = self.market_app.get_cheapest_gear()
                # Filter for T4 epic or T5 legendary matching slots
                target_tier_num = "4" if gear_tier == "epic" else "5"
                for item in cheapest_items:
                    code = item.get("item_code", "")
                    if target_tier_num in code or (gear_tier == "epic" and code == "sniper"):
                        recommended_gear.append(item)
                        gear_total_cost += float(item.get("price", 0))
            except Exception as e:
                logger.warning(f"Error fetching live market gear: {e}")

        grand_total_cost = food_total_cost + gear_total_cost
        if use_pill:
            grand_total_cost += 3500.0  # standard market pill price estimate

        return {
            "player": {
                "username": uname,
                "level": lvl,
                "health_max": health_max,
                "base_atk": base_atk,
                "eff_armor": round(eff_armor, 1),
                "eff_dodge": round(eff_dodge, 1),
            },
            "target": {
                "damage_goal": target_damage,
                "use_pill": use_pill,
                "food_type": food_spec["name"],
                "gear_tier": gear_tier,
            },
            "combat_metrics": {
                "avg_dmg_per_hit": round(avg_dmg_per_hit, 1),
                "hp_cost_per_hit": round(hp_cost_per_hit, 2),
                "total_hits_needed": total_hits_needed,
                "total_hp_needed": round(total_hp_needed, 0),
                "natural_hp_pool": round(natural_hp_pool, 0),
                "hp_deficit": round(hp_deficit, 0),
            },
            "consumables": {
                "food_name": food_spec["name"],
                "units_needed": food_units_needed,
                "unit_price": fish_price,
                "total_cost": food_total_cost,
                "pill_recommended": use_pill,
                "pill_cost": 3500.0 if use_pill else 0.0,
            },
            "recommended_gear": recommended_gear,
            "gear_total_cost": round(gear_total_cost, 2),
            "grand_total_cost": round(grand_total_cost, 2),
        }
