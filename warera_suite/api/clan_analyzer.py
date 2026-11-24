"""
WarEra Clan & Military Unit (MU) Combat Intelligence Analyzer
Calculates:
- Build classification: War Build (>=70%), Eco Build (>=70%), Hybrid (30-70%)
- Pill status ('cocain'): Active (+60%), Ready (clean/ready to take), Cooldown/Debuff (-60%)
- Theoretical expected daily damage:
  * Full Epic (Purple IV) gear baseline (or player's actual if higher)
  * Dodge % (zero HP loss on trigger)
  * Armor % (reduces HP cost per hit)
  * Effective HP cost per hit = 10 * (1 - Armor) * (1 - Dodge)
  * Hits per day from 24h health pool (base + hourly regen)
  * Expected damage per hit with Pill (+60%), Weapon (+150), Crit chance & Crit damage, MU order (+10%)
- Clan combat roster, AFK tracker, and shareable clan report.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
try:
    import zoneinfo
    tz_kyiv = zoneinfo.ZoneInfo("Europe/Kyiv")
except Exception:
    tz_kyiv = timezone(timedelta(hours=2))
import httpx
import config
from clan_history_db import ClanHistoryDB
from warera_client import WarEraClient, get_warera_client

logger = logging.getLogger("WarEraClanAnalyzer")

_CLAN_CACHE: Dict[str, Dict[str, Any]] = {}
_CLAN_CACHE_TIME: Dict[str, float] = {}

class WarEraClanAnalyzer:
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, client: Optional[WarEraClient] = None):
        self.user_api_key = (api_key or config.get_api_key()).strip()
        self.api_key = self.user_api_key
        self.client = client or WarEraClient(api_key=self.api_key, base_url=base_url)
        self.history_db = ClanHistoryDB()
        self.is_community_key = False

    async def get_client(self) -> httpx.AsyncClient:
        return await self.client.get_client()

    async def close(self):
        await self.client.close()

    async def _call_trpc(self, endpoint: str, payload: Optional[Dict[str, Any]] = None) -> Any:
        return await self.client.call_trpc(endpoint, payload=payload, key_override=self.api_key)

    async def get_game_config(self) -> Dict[str, Any]:
        return await self.client.get_game_config()

    async def resolve_user_by_name(self, nickname: str) -> Optional[Dict[str, Any]]:
        # If 24-char hex ID
        if len(nickname) == 24 and all(c in "0123456789abcdefABCDEF" for c in nickname):
            res = await self._call_trpc("user.getUserById", {"userId": nickname})
            if res:
                return res

        search_res = await self._call_trpc("user.searchUsers", {"query": nickname})
        user_ids = []
        if isinstance(search_res, list):
            user_ids = [u.get("_id") for u in search_res if isinstance(u, dict) and u.get("_id")]
        elif isinstance(search_res, dict):
            items = search_res.get("items", []) or search_res.get("users", [])
            user_ids = [u.get("_id") for u in items if isinstance(u, dict) and u.get("_id")]

        for uid in user_ids:
            u_data = await self._call_trpc("user.getUserById", {"userId": uid})
            if u_data and u_data.get("username", "").lower() == nickname.lower():
                return u_data

        if user_ids:
            return await self._call_trpc("user.getUserById", {"userId": user_ids[0]})
        return None

    async def get_owner_user(self) -> Optional[Dict[str, Any]]:
        owner_nick = getattr(config, "DEFAULT_CLAN_OWNER", "Luc1fer")
        return await self.resolve_user_by_name(owner_nick)

    def _format_relative_time(self, iso_str: Optional[str]) -> str:
        if not iso_str:
            return "Невідомо"
        try:
            # Handle timestamps with Z
            dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            diff = now - dt
            seconds = int(diff.total_seconds())
            if seconds < 0:
                return "Щойно"
            if seconds < 120:
                return "Щойно"
            minutes = seconds // 60
            if minutes < 60:
                return f"{minutes} хв тому"
            hours = minutes // 60
            if hours < 24:
                return f"{hours} год тому"
            days = hours // 24
            if days == 1:
                return "Вчора"
            if days < 30:
                return f"{days} дн. тому"
            return dt.strftime("%d.%m.%Y")
        except Exception:
            return iso_str[:10]

    async def _resolve_mu(self, mu_id_or_user: Optional[str]) -> tuple[Optional[str], Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """Resolves MU ID, MU data, and optional target_user from an MU ID, nickname, or config defaults."""
        mu_id = None
        mu_data = None
        target_user = None

        if mu_id_or_user:
            test_mu = await self._call_trpc("mu.getById", {"muId": mu_id_or_user})
            if test_mu and isinstance(test_mu, dict) and test_mu.get("name"):
                mu_id = mu_id_or_user
                mu_data = test_mu
            else:
                target_user = await self.resolve_user_by_name(mu_id_or_user)
                if target_user and target_user.get("mu"):
                    mu_id = target_user["mu"]

        if not mu_id:
            owner = await self.get_owner_user()
            if owner and owner.get("mu"):
                mu_id = owner["mu"]

        if not mu_id:
            mu_id = getattr(config, "DEFAULT_MU_ID", "69af3162a583a3b5f9941e71")

        if not mu_data:
            mu_data = await self._call_trpc("mu.getById", {"muId": mu_id})

        return mu_id, mu_data, target_user

    async def analyze_clan(self, mu_id_or_user: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyzes a clan / military unit (MU) and all its members.
        mu_id_or_user can be:
        - None: auto-detects from DEFAULT_CLAN_OWNER or DEFAULT_MU_ID
        - 24-hex MU ID (e.g. '69af3162a583a3b5f9941e71')
        - Player nickname or user ID (resolves user.mu)
        """
        global _CLAN_CACHE, _CLAN_CACHE_TIME
        import time

        cache_key = str(mu_id_or_user or "default").strip()
        now = time.time()

        # 1. Return fresh cache if available (< 20 seconds)
        if cache_key in _CLAN_CACHE and (now - _CLAN_CACHE_TIME.get(cache_key, 0)) < 20.0:
            return _CLAN_CACHE[cache_key]

        mu_id, mu_data, target_user = await self._resolve_mu(mu_id_or_user)

        if not mu_data or not isinstance(mu_data, dict):
            # Fallback to stale cache if API failed
            if cache_key in _CLAN_CACHE:
                logger.warning(f"Failed to fetch fresh data for MU {mu_id}, serving stale cache")
                return _CLAN_CACHE[cache_key]
            if "default" in _CLAN_CACHE:
                return _CLAN_CACHE["default"]

            return {
                "status": "error",
                "message": f"Не вдалося завантажити дані підрозділу (MU ID: {mu_id})"
            }

        member_ids = mu_data.get("members", [])
        roles = mu_data.get("roles", {})
        managers = set(roles.get("managers", []))
        commanders = set(roles.get("commanders", []))
        leader_id = mu_data.get("user")

        # Concurrently fetch all member profiles
        tasks = [self._call_trpc("user.getUserById", {"userId": mid}) for mid in member_ids]
        raw_members = await asyncio.gather(*tasks)
        valid_members = [m for m in raw_members if m and isinstance(m, dict)]

        analyzed_members = []
        now_utc = datetime.now(timezone.utc)
        now_kyiv = datetime.now(tz_kyiv)
        if now_kyiv.hour >= 2:
            next_reset_kyiv = (now_kyiv + timedelta(days=1)).replace(hour=2, minute=0, second=0, microsecond=0)
        else:
            next_reset_kyiv = now_kyiv.replace(hour=2, minute=0, second=0, microsecond=0)
        next_reset_utc = next_reset_kyiv.astimezone(timezone.utc)

        # Baseline Full Epic Set (Purple Tier IV) flat bonuses:
        # Chest4 (22% armor) + Pants4 (23% armor) = ~45% armor
        # Boots4 (22% dodge) = +22% dodge
        # Helmet4 (75% crit damage) = +75% crit damage
        # Gloves4 (22% precision) = +22% precision
        # Weapon4 (Epic sniper/rifle: ~137-150 atk with overflow, ~17-25% crit chance)
        EPIC_ARMOR_ADD = 45.0
        EPIC_DODGE_ADD = 22.0
        EPIC_CRIT_DMG_ADD = 75.0
        EPIC_CRIT_CHANCE_ADD = 17.0
        EPIC_PRECISION_ADD = 22.0
        EPIC_WEAPON_ATK = 137.0

        for m in valid_members:
            uid = m.get("_id")
            uname = m.get("username", "Unknown")
            lvl = m.get("leveling", {}).get("level", 1)
            prestige = int(m.get("leveling", {}).get("prestige") or m.get("leveling", {}).get("prestigeLevel") or m.get("prestige", 0) or 0)
            skills = m.get("skills", {})
            dates = m.get("dates", {})
            rankings = m.get("rankings", {})
            stats = m.get("stats", {})

            # Clan role
            if uid == leader_id:
                clan_role = "LEADER"
                role_label = "👑 Лідер"
            elif uid in managers:
                clan_role = "MANAGER"
                role_label = "💼 Менеджер"
            elif uid in commanders:
                clan_role = "COMMANDER"
                role_label = "⚔️ Командир"
            else:
                clan_role = "MEMBER"
                role_label = "🛡️ Боєць"

            # 1. Build Classification (War vs Eco)
            war_skill_keys = ['attack', 'health', 'armor', 'criticalChance', 'criticalDamages', 'precision', 'dodge']
            eco_skill_keys = ['companies', 'production', 'management']

            war_points = sum(skills.get(k, {}).get("level", 0) for k in war_skill_keys)
            eco_points = sum(skills.get(k, {}).get("level", 0) for k in eco_skill_keys)
            total_spec_points = war_points + eco_points

            if total_spec_points > 0:
                war_ratio = round((war_points / total_spec_points) * 100.0, 1)
                eco_ratio = round((eco_points / total_spec_points) * 100.0, 1)
            else:
                war_ratio = 50.0
                eco_ratio = 50.0

            if war_ratio >= 70.0:
                build_type = "WAR"
                build_label = f"⚔️ Вар ({war_ratio:.0f}%)"
                build_color = "emerald"
            elif eco_ratio >= 70.0:
                build_type = "ECO"
                build_label = f"🚜 Еко ({eco_ratio:.0f}%)"
                build_color = "amber"
            else:
                build_type = "HYBRID"
                build_label = f"⚖️ Гібрид ({war_ratio:.0f}/{eco_ratio:.0f}%)"
                build_color = "sky"

            # 2. Pill Status ('cocain') and Timers
            buffs = m.get("buffs") or {}
            buff_end_at = buffs.get("buffEndAt")
            debuff_end_at = buffs.get("debuffEndAt")

            atk_skill = skills.get("attack", {})
            buff_pct = float(atk_skill.get("buffsPercent", 0.0))
            debuff_pct = float(atk_skill.get("debuffsPercent", 0.0))

            pill_remaining_sec = 0
            pill_remaining_hours = 0.0
            pill_time_label = "—"
            pill_remaining_tip = ""
            can_drink_before_reset = False

            if build_type == "ECO":
                pill_status = "ECO_SUPPORT"
                pill_label = "🚜 Еко-тил"
                pill_color = "gray"
                pill_tip = "Економічний білд. Таблетка для боїв зазвичай не потрібна."
                pill_time_label = "еко-тил"
                can_drink_before_reset = False
            elif buff_pct >= 50.0 or (buffs and "cocain" in buffs.get("buffCodes", [])):
                pill_status = "ACTIVE"
                pill_label = "💊 Баф (+60%)"
                pill_color = "emerald"
                pill_tip = "Таблетка активна прямо зараз! Боєць під бафом (+60% атаки) на піку сили."
                can_drink_before_reset = False

                if buff_end_at:
                    try:
                        end_dt = datetime.fromisoformat(buff_end_at.replace("Z", "+00:00"))
                        pill_remaining_sec = max(0, int((end_dt - now_utc).total_seconds()))
                        pill_remaining_hours = pill_remaining_sec / 3600.0
                        hrs = pill_remaining_sec // 3600
                        mins = (pill_remaining_sec % 3600) // 60
                        pill_time_label = f"ще {hrs}г {mins:02d}хв"
                        end_kyiv = end_dt.astimezone(tz_kyiv)
                        pill_remaining_tip = f"Таблетка діє до {end_kyiv.strftime('%H:%M')} (залишилось {hrs}г {mins:02d}хв)"
                    except Exception:
                        pill_time_label = "активна"
                else:
                    pill_time_label = "активна"
            elif debuff_pct >= 50.0 or (buffs and "cocain" in buffs.get("debuffCodes", [])):
                pill_status = "COOLDOWN"
                pill_label = "⏳ Дебаф (-60%)"
                pill_color = "rose"

                if debuff_end_at:
                    try:
                        end_dt = datetime.fromisoformat(debuff_end_at.replace("Z", "+00:00"))
                        diff_sec = max(0, int((end_dt - now_utc).total_seconds()))
                        hrs = diff_sec // 3600
                        mins = (diff_sec % 3600) // 60
                        pill_time_label = f"ще {hrs}г {mins:02d}хв"
                        end_kyiv = end_dt.astimezone(tz_kyiv)
                        can_drink_before_reset = (end_dt < next_reset_utc)
                        if can_drink_before_reset:
                            pill_tip = f"Дія таблетки завершилась, діє дебаф (-60%). Дебаф спаде до 02:00 (о {end_kyiv.strftime('%H:%M')}). Боєць зможе прийняти вечірню таблетку!"
                            pill_remaining_tip = f"Дебаф завершиться о {end_kyiv.strftime('%H:%M')} (ще {hrs}г {mins:02d}хв). Встигає випити таблетку до 02:00!"
                        else:
                            pill_tip = f"Дія таблетки завершилась, діє дебаф (-60%). Дебаф спаде після 02:00 (о {end_kyiv.strftime('%H:%M')} {end_kyiv.strftime('%d.%m')}). Сьогодні відстрілявся, таблетку більше не прийме!"
                            pill_remaining_tip = f"Дебаф завершиться о {end_kyiv.strftime('%H:%M')} {end_kyiv.strftime('%d.%m')} (ще {hrs}г {mins:02d}хв). До 02:00 не встигає!"
                    except Exception:
                        pill_time_label = "дебаф"
                        pill_tip = "Дія таблетки завершилась, діє дебаф штрафу (-60% атаки). Урон під дебафом заблоковано."
                        can_drink_before_reset = False
                else:
                    pill_time_label = "дебаф"
                    pill_tip = "Дія таблетки завершилась, діє дебаф штрафу (-60% атаки). Урон під дебафом заблоковано."
                    can_drink_before_reset = False
            else:
                pill_status = "READY"
                pill_label = "⚪ Готовий пити"
                pill_color = "blue"
                pill_tip = "Чистий боєць! Таблетку ще не пив, готовий прийняти під наказ командира на повні 8 год."
                pill_time_label = "готовий (8 год)"
                pill_remaining_hours = 8.0
                can_drink_before_reset = True

            # 3. Combat Parameters with Full Epic Set Baseline & Full Drain of HP+Hunger
            base_atk = float(atk_skill.get("value", 100))
            health_skill = skills.get("health", {})
            health_curr = float(health_skill.get("currentBarValue", 100))
            health_max = float(health_skill.get("total", 100))
            # 10 HP = 1 regen/hour (10% of total HP per hour)
            health_regen = float(health_skill.get("hourlyBarRegen") or (health_max * 0.10))

            hunger_skill = skills.get("hunger", {})
            hunger_curr = float(hunger_skill.get("currentBarValue", 4))
            hunger_max = float(hunger_skill.get("total", 4))
            # 10 hunger = 1 regen/hour, 7 hunger = 0.7 regen/hour (10% of total hunger per hour)
            hunger_regen = float(hunger_skill.get("hourlyBarRegen") or (hunger_max * 0.10))

            # 24h health pool = current full bar + 24 hours of natural regen
            daily_hp_pool = health_max + (24.0 * health_regen)

            # Armor and Dodge computation: character stats + equipment with softcap
            curr_armor_stat = float(skills.get("armor", {}).get("value", 0))
            curr_dodge_stat = float(skills.get("dodge", {}).get("value", 0))

            equipped_armor = float(skills.get("armor", {}).get("equipment", 0))
            equipped_dodge = float(skills.get("dodge", {}).get("equipment", 0))

            effective_gear_armor = max(equipped_armor, EPIC_ARMOR_ADD)
            effective_gear_dodge = max(equipped_dodge, EPIC_DODGE_ADD)

            total_raw_armor = curr_armor_stat + effective_gear_armor
            total_raw_dodge = curr_dodge_stat + effective_gear_dodge

            # In-game softcap from API if already computed by game server for equipped gear
            game_armor_softcap = float(skills.get("armor", {}).get("totalAfterSoftCap", 0))
            game_dodge_softcap = float(skills.get("dodge", {}).get("totalAfterSoftCap", 0))

            # Exact WarEra diminishing returns (canonical formula from game client)
            armor_reduction = (total_raw_armor / (total_raw_armor + 40.0)) if total_raw_armor > 0 else 0.0
            dodge_fraction = (total_raw_dodge / (total_raw_dodge + 40.0)) if total_raw_dodge > 0 else 0.0

            eff_armor_pct = armor_reduction * 100.0
            eff_dodge_pct = dodge_fraction * 100.0

            # Effective HP cost per hit (canonical WarEra game formula: base 10.0 HP)
            base_hit_cost = 10.0
            hp_cost_per_hit = max(0.5, base_hit_cost * (1.0 - armor_reduction) * (1.0 - dodge_fraction))

            # Hits per day from natural HP pool
            hits_per_day_natural = daily_hp_pool / hp_cost_per_hit
            # If user also eats bread/steaks (+250 HP extra pool typical for active combat day)
            hits_per_day_with_food = (daily_hp_pool + 250.0) / hp_cost_per_hit

            # Attack per hit calculation:
            # Multiplicative formula verified by live game testing:
            # Attack = (Base + Weapon + Overflow) * (1 + Rank%) * (1 + Ammo%) * 1.60 [Pill]
            equipped_weapon = float(atk_skill.get("weapon", 0))
            equipped_overflow = float(atk_skill.get("overflow", 0))
            actual_weapon_atk = equipped_weapon + equipped_overflow

            effective_weapon_atk = max(actual_weapon_atk, EPIC_WEAPON_ATK)

            rank_bonus_pct = float(atk_skill.get("militaryRankPercent", 0.0))
            ammo_bonus_pct = float(atk_skill.get("ammoPercent") or 10.0)
            ammo_bonus_pct = max(ammo_bonus_pct, 10.0)

            rank_mult = 1.0 + (rank_bonus_pct / 100.0)
            ammo_mult = 1.0 + (ammo_bonus_pct / 100.0)

            # Base character attack with simulated/actual weapon (clean from temporary buff and debuff)
            base_unbuffed_atk = (base_atk + effective_weapon_atk) * rank_mult * ammo_mult

            # When pill is taken (+60% attack buff):
            # If player currently has active pill (+60%), server's exact live total attack takes precedence
            server_total_atk = float(atk_skill.get("total", 0.0))
            if buff_pct >= 50.0 and server_total_atk > 0:
                simulated_atk = max(server_total_atk, base_unbuffed_atk * 1.60)
            else:
                simulated_atk = base_unbuffed_atk * 1.60

            # Precision (Влучність): Miss deals 50% damage and cannot crit
            curr_precision = float(skills.get("precision", {}).get("value", 75))
            eq_precision = float(skills.get("precision", {}).get("equipment", 0))
            strat_precision = float(skills.get("precision", {}).get("strategic", 0))
            server_precision = float(skills.get("precision", {}).get("total", 0))
            total_precision = min(100.0, max(server_precision, curr_precision + max(eq_precision, EPIC_PRECISION_ADD) + strat_precision))
            precision_ratio = total_precision / 100.0

            # Critical Chance and Critical Damage with Epic/Legendary gear
            curr_crit_chance = float(skills.get("criticalChance", {}).get("value", 10))
            curr_crit_dmg = float(skills.get("criticalDamages", {}).get("value", 100))
            eq_crit_chance = float(skills.get("criticalChance", {}).get("weapon", 0))
            eq_crit_dmg = float(skills.get("criticalDamages", {}).get("equipment", 0))
            server_crit_chance = float(skills.get("criticalChance", {}).get("total", 0))
            server_crit_dmg = float(skills.get("criticalDamages", {}).get("total", 0))

            total_crit_chance = min(100.0, max(server_crit_chance, curr_crit_chance + max(eq_crit_chance, EPIC_CRIT_CHANCE_ADD)))
            total_crit_dmg = max(server_crit_dmg, curr_crit_dmg + max(eq_crit_dmg, EPIC_CRIT_DMG_ADD))

            # In WarEra (empirically confirmed by live battle video), crit deals (1 + CritDamage/100)x damage
            crit_hit_mult = 1.0 + (total_crit_dmg / 100.0)
            crit_chance_ratio = total_crit_chance / 100.0

            # Precision & Crit multiplier:
            # Expected hit factor = (1 - Precision) * 0.5 + Precision * [(1 - CritChance) * 1.0 + CritChance * CritMult]
            crit_multiplier = (1.0 - precision_ratio) * 0.5 + precision_ratio * ((1.0 - crit_chance_ratio) * 1.0 + crit_chance_ratio * crit_hit_mult)

            # Organized clan battle bonus (+50% standard: MU order 15% + Country order 15% + HQ 20%)
            battle_bonus = 1.50

            avg_dmg_per_hit = simulated_atk * crit_multiplier * battle_bonus

            # Pill Combat Capacity: 2 distinct waves as deployed in WarEra battles
            # Wave 1 (0:00 Start): Drink pill (+60%), drain 100% initial HP, eat all available Steaks, drain HP again
            # Wave 2 (7:30 Finish): Wait 7.5 hours under active pill, drain natural HP regen, eat regen Steaks, drain HP again
            # CRITICAL RULE: ECO warriors do NOT take pills and are strictly excluded from salvo!
            if build_type == "ECO":
                start_salvo_hp = 0
                start_salvo_hits = 0
                start_salvo_dmg = 0
                regen_salvo_hp = 0
                regen_salvo_hits = 0
                regen_salvo_dmg = 0
                full_pill_hp_pool = 0
                full_pill_hits = 0
                full_pill_dmg = 0
                full_pill_fish_hits = 0
                full_pill_fish_dmg = 0
                full_pill_siege_fish_dmg = 0
                current_pill_hits = 0
                current_pill_dmg = 0
                pill_instant_hits = 0
                pill_instant_dmg = 0
                pill_regen_hits = 0
                pill_regen_dmg = 0
                pill_instant_fish_hits = 0
                pill_instant_fish_dmg = 0
                pill_regen_fish_hits = 0
                pill_regen_fish_dmg = 0
                daily_theoretical_hits = 0
                daily_theoretical_dmg = 0
                theoretical_daily_dmg_min = 0
                theoretical_daily_dmg_max = 0
            else:
                # Food restores HP as a PERCENTAGE of character's total HP (health_max):
                # Bread = 10%, Steak = 15%, Cooked Fish = 20%
                FOOD_STEAK_PCT = 0.15 # Steak (15% of max HP per hunger unit)
                FOOD_FISH_PCT = 0.20  # Cooked Fish (20% of max HP per hunger unit)
                
                HP_PER_HUNGER = health_max * FOOD_STEAK_PCT # Standard combat ration (Steak 15%)
                HP_PER_HUNGER_FISH = health_max * FOOD_FISH_PCT # Elite ration (Cooked Fish 20%)

                full_pill_duration = 8.0
                regen_wait_hours = 7.5

                # Wave 1: Start salvo (initial HP bar + full initial hunger bar on steaks)
                start_salvo_hp = health_max + (hunger_max * HP_PER_HUNGER)
                start_salvo_hits = round(start_salvo_hp / hp_cost_per_hit)
                start_salvo_dmg = round(start_salvo_hits * avg_dmg_per_hit)

                # Wave 2: Regen salvo after 7.5h wait under active pill
                regen_salvo_hp = (regen_wait_hours * health_regen) + ((regen_wait_hours * hunger_regen) * HP_PER_HUNGER)
                regen_salvo_hits = round(regen_salvo_hp / hp_cost_per_hit)
                regen_salvo_dmg = round(regen_salvo_hits * avg_dmg_per_hit)

                # Full 8-Hour Pill Session (Wave 1 + Wave 2):
                full_pill_hp_pool = start_salvo_hp + regen_salvo_hp
                full_pill_hits = start_salvo_hits + regen_salvo_hits
                full_pill_dmg = start_salvo_dmg + regen_salvo_dmg

                # Cooked Fish (20%) ceiling comparison:
                fish_start_hp = health_max + (hunger_max * HP_PER_HUNGER_FISH)
                fish_regen_hp = (regen_wait_hours * health_regen) + ((regen_wait_hours * hunger_regen) * HP_PER_HUNGER_FISH)
                full_pill_fish_hits = round((fish_start_hp + fish_regen_hp) / hp_cost_per_hit)
                full_pill_fish_dmg = round(full_pill_fish_hits * avg_dmg_per_hit)

                # Full Siege Battle (+84.38% bonus: Alliance + MU + Country + HQ + Bunker) with Cooked Fish:
                avg_dmg_per_hit_siege = simulated_atk * crit_multiplier * 1.8438
                full_pill_siege_fish_dmg = round(full_pill_fish_hits * avg_dmg_per_hit_siege)

                # 2. Current remaining damage for active pill (or ready to drink):
                # Split cleanly into:
                # - Instant in-hands pool (current HP + food bar right now, can be dumped immediately)
                # - Future regen pool (natural HP + hunger regen matured over remaining pill hours)
                if pill_status == "ACTIVE":
                    rem_h = pill_remaining_hours

                    # Steak (15%)
                    pill_instant_hp = health_curr + (hunger_curr * HP_PER_HUNGER)
                    pill_instant_hits = round(pill_instant_hp / hp_cost_per_hit)
                    pill_instant_dmg = round(pill_instant_hits * avg_dmg_per_hit)

                    pill_regen_hp = (rem_h * health_regen) + (rem_h * hunger_regen * HP_PER_HUNGER)
                    pill_regen_hits = round(pill_regen_hp / hp_cost_per_hit)
                    pill_regen_dmg = round(pill_regen_hits * avg_dmg_per_hit)

                    # Cooked Fish (20%)
                    pill_instant_fish_hp = health_curr + (hunger_curr * HP_PER_HUNGER_FISH)
                    pill_instant_fish_hits = round(pill_instant_fish_hp / hp_cost_per_hit)
                    pill_instant_fish_dmg = round(pill_instant_fish_hits * avg_dmg_per_hit)

                    pill_regen_fish_hp = (rem_h * health_regen) + (rem_h * hunger_regen * HP_PER_HUNGER_FISH)
                    pill_regen_fish_hits = round(pill_regen_fish_hp / hp_cost_per_hit)
                    pill_regen_fish_dmg = round(pill_regen_fish_hits * avg_dmg_per_hit)

                    current_pill_hits = pill_instant_hits + pill_regen_hits
                    current_pill_dmg = pill_instant_dmg + pill_regen_dmg
                elif pill_status == "READY":
                    pill_instant_hits = start_salvo_hits
                    pill_instant_dmg = start_salvo_dmg
                    pill_regen_hits = regen_salvo_hits
                    pill_regen_dmg = regen_salvo_dmg

                    fish_start_hits = round(fish_start_hp / hp_cost_per_hit)
                    pill_instant_fish_hits = fish_start_hits
                    pill_instant_fish_dmg = round(fish_start_hits * avg_dmg_per_hit)
                    fish_regen_hits = round(fish_regen_hp / hp_cost_per_hit)
                    pill_regen_fish_hits = fish_regen_hits
                    pill_regen_fish_dmg = round(fish_regen_hits * avg_dmg_per_hit)

                    current_pill_hits = full_pill_hits
                    current_pill_dmg = full_pill_dmg
                else:
                    # Cooldown
                    pill_instant_hits = 0
                    pill_instant_dmg = 0
                    pill_regen_hits = 0
                    pill_regen_dmg = 0
                    pill_instant_fish_hits = 0
                    pill_instant_fish_dmg = 0
                    pill_regen_fish_hits = 0
                    pill_regen_fish_dmg = 0
                    current_pill_hits = 0
                    current_pill_dmg = 0

                # Full 24-Hour Day Capacity (Full pill 8h + remaining 16.5h of natural day regen and steaks):
                rest_day_hours = 24.0 - regen_wait_hours
                rest_hp_pool = (rest_day_hours * health_regen) + ((rest_day_hours * hunger_regen) * HP_PER_HUNGER)
                rest_hits = round(rest_hp_pool / hp_cost_per_hit)
                # Without pill buff during rest hours, average damage is normal (divided by 1.60)
                rest_dmg = round(rest_hits * (avg_dmg_per_hit / 1.60))

                daily_theoretical_hits = full_pill_hits + rest_hits
                daily_theoretical_dmg = full_pill_dmg + rest_dmg

                theoretical_daily_dmg_min = full_pill_dmg
                theoretical_daily_dmg_max = daily_theoretical_dmg

            # 4. Activity & Online
            last_conn_iso = dates.get("lastConnectionAt")
            relative_last_seen = self._format_relative_time(last_conn_iso)
            
            is_afk = False
            hours_offline = 0
            if last_conn_iso:
                try:
                    conn_dt = datetime.fromisoformat(last_conn_iso.replace("Z", "+00:00"))
                    diff_h = (now_utc - conn_dt).total_seconds() / 3600.0
                    hours_offline = int(diff_h)
                    if diff_h >= 24.0:
                        is_afk = True
                except Exception:
                    pass

            # In-game weekly damages & real-time total damage counter
            weekly_dmg = int(rankings.get("weeklyUserDamages", {}).get("value", 0))
            # stats.damagesCount updates instantly with every battle hit! rankings.userDamages lags behind by ~1 hour.
            total_dmg = int(stats.get("damagesCount") or rankings.get("userDamages", {}).get("value", 0))
            wealth_total = float(stats.get("wealth", {}).get("total", 0.0))

            analyzed_members.append({
                "user_id": uid,
                "username": uname,
                "level": lvl,
                "prestige": prestige,
                "avatar_url": m.get("avatarUrl", ""),
                "military_rank": m.get("militaryRank", 0),
                "clan_role": clan_role,
                "role_label": role_label,
                # Build
                "build_type": build_type,
                "build_label": build_label,
                "build_color": build_color,
                "war_points": war_points,
                "eco_points": eco_points,
                "war_ratio": war_ratio,
                "eco_ratio": eco_ratio,
                # Pill
                "pill_status": pill_status,
                "pill_label": pill_label,
                "pill_color": pill_color,
                "pill_tip": pill_tip,
                "buff_pct": buff_pct,
                "debuff_pct": debuff_pct,
                "pill_time_label": pill_time_label,
                "pill_remaining_hours": round(pill_remaining_hours, 2),
                "pill_remaining_tip": pill_remaining_tip,
                "can_drink_before_reset": can_drink_before_reset,
                "debuff_end_at": debuff_end_at,
                "pill_full_dmg": full_pill_dmg,
                "pill_full_hits": full_pill_hits,
                "pill_fish_dmg": full_pill_fish_dmg,
                "pill_fish_hits": full_pill_fish_hits,
                "pill_siege_fish_dmg": full_pill_siege_fish_dmg,
                "pill_current_dmg": current_pill_dmg,
                "pill_current_hits": current_pill_hits,
                "pill_instant_dmg": pill_instant_dmg,
                "pill_instant_hits": pill_instant_hits,
                "pill_regen_dmg": pill_regen_dmg,
                "pill_regen_hits": pill_regen_hits,
                "pill_instant_fish_dmg": pill_instant_fish_dmg,
                "pill_instant_fish_hits": pill_instant_fish_hits,
                "pill_regen_fish_dmg": pill_regen_fish_dmg,
                "pill_regen_fish_hits": pill_regen_fish_hits,
                "start_salvo_dmg": start_salvo_dmg,
                "start_salvo_hits": start_salvo_hits,
                "regen_salvo_dmg": regen_salvo_dmg,
                "regen_salvo_hits": regen_salvo_hits,
                "daily_theoretical_dmg": daily_theoretical_dmg,
                "daily_theoretical_hits": daily_theoretical_hits,
                # Gear & Combat Specs
                "effective_armor": round(eff_armor_pct, 1),
                "effective_dodge": round(eff_dodge_pct, 1),
                "hp_cost_per_hit": round(hp_cost_per_hit, 2),
                "hits_per_day_natural": full_pill_hits,
                "hits_per_day_max": daily_theoretical_hits,
                "avg_dmg_per_hit": round(avg_dmg_per_hit),
                "unbuffed_hit_dmg": round(simulated_atk * crit_multiplier),
                "theoretical_daily_dmg_min": full_pill_dmg,
                "theoretical_daily_dmg_max": daily_theoretical_dmg,
                "skills": skills,
                "health_max": round(health_max, 1),
                "health_curr": round(health_curr, 1),
                "health_regen": round(health_regen, 2),
                "hunger_max": round(hunger_max, 1),
                "hunger_curr": round(hunger_curr, 1),
                "hunger_regen": round(hunger_regen, 2),
                "base_attack": round(base_atk, 1),
                "rank_bonus_pct": round(rank_bonus_pct, 1),
                "equipped_weapon_atk": round(actual_weapon_atk, 1),
                "equipped_armor": round(equipped_armor, 1),
                "equipped_dodge": round(equipped_dodge, 1),
                # In-game stats
                "weekly_damage": weekly_dmg,
                "total_damage": total_dmg,
                "wealth_total": round(wealth_total, 2),
                # Activity
                "last_seen_iso": last_conn_iso,
                "last_seen_label": relative_last_seen,
                "hours_offline": hours_offline,
                "is_afk": is_afk,
            })

        # Save snapshot & calculate actual daily damage deltas
        game_date = self.history_db.get_game_date()
        yesterday_game_date = self.history_db.get_yesterday_game_date(game_date)
        try:
            self.history_db.record_members_snapshot(analyzed_members, game_date=game_date)
        except Exception as e:
            logger.warning(f"Failed to record clan snapshot: {e}")

        for m in analyzed_members:
            try:
                dmg_stats = self.history_db.get_damage_stats(
                    user_id=m["user_id"],
                    current_total_dmg=m["total_damage"],
                    current_weekly_dmg=m["weekly_damage"],
                    game_date=game_date
                )
                m["today_damage"] = dmg_stats["today_damage"]
                m["yesterday_damage"] = dmg_stats["yesterday_damage"]
                m["has_yesterday"] = dmg_stats["has_yesterday"]
            except Exception:
                m["today_damage"] = 0
                m["yesterday_damage"] = None
                m["has_yesterday"] = False

        # Attach active daily target damage goals and progress
        try:
            from clan_targets import get_daily_targets
            daily_targets = get_daily_targets(game_date=game_date)
            for m in analyzed_members:
                uname = m.get("username", "").lower()
                target_rec = daily_targets.get(uname)
                if target_rec and target_rec.get("target_damage", 0) > 0:
                    tg_dmg = float(target_rec["target_damage"])
                    m["target_damage"] = tg_dmg
                    m["target_gear_tier"] = target_rec.get("gear_tier", "epic")
                    m["target_use_pill"] = target_rec.get("use_pill", True)
                    m["target_use_fish"] = target_rec.get("use_fish", True)
                    today_val = float(m.get("today_damage", 0))
                    m["target_progress_pct"] = round(min(100.0, (today_val / tg_dmg) * 100.0), 1)
                    m["target_battle_bonus"] = target_rec.get("battle_bonus")
                    m["target_weapon"] = target_rec.get("weapon")
                    m["target_ammo"] = target_rec.get("ammo")
                    m["target_food"] = target_rec.get("food")
                    m["target_prestige"] = target_rec.get("prestige")
                    m["target_rank_bonus"] = target_rec.get("rank_bonus")
                    m["saved_strategy_key"] = target_rec.get("saved_strategy_key")
                    m["saved_strategy_label"] = target_rec.get("saved_strategy_label")
                    m["saved_build"] = target_rec.get("saved_build")
                    m["is_build_locked"] = bool(target_rec.get("is_build_locked", False))
                else:
                    m["target_damage"] = None
                    m["target_gear_tier"] = None
                    m["target_use_pill"] = None
                    m["target_use_fish"] = None
                    m["target_progress_pct"] = None
                    m["target_battle_bonus"] = None
                    m["target_weapon"] = None
                    m["target_ammo"] = None
                    m["target_food"] = None
                    m["target_prestige"] = None
                    m["target_rank_bonus"] = None
                    m["saved_strategy_key"] = None
                    m["saved_strategy_label"] = None
                    m["saved_build"] = None
                    m["is_build_locked"] = False
        except Exception as e:
            logger.warning(f"Error attaching daily clan targets: {e}")

        # Sort members: War builds first, then by today's damage (or theoretical max damage)
        analyzed_members.sort(key=lambda x: (x["build_type"] != "WAR", -x["theoretical_daily_dmg_max"], -x["today_damage"], -x["weekly_damage"]))

        # Aggregate clan metrics
        war_count = sum(1 for m in analyzed_members if m["build_type"] == "WAR")
        eco_count = sum(1 for m in analyzed_members if m["build_type"] == "ECO")
        hybrid_count = sum(1 for m in analyzed_members if m["build_type"] == "HYBRID")

        pill_active_count = sum(1 for m in analyzed_members if m["pill_status"] == "ACTIVE")
        pill_ready_count = sum(1 for m in analyzed_members if m["pill_status"] == "READY")
        pill_cooldown_count = sum(1 for m in analyzed_members if m["pill_status"] == "COOLDOWN")
        afk_count = sum(1 for m in analyzed_members if m["is_afk"])

        total_clan_daily_salvo_min = sum(m["theoretical_daily_dmg_min"] for m in analyzed_members if m["build_type"] in ("WAR", "HYBRID"))
        total_clan_daily_salvo_max = sum(m["theoretical_daily_dmg_max"] for m in analyzed_members if m["build_type"] in ("WAR", "HYBRID"))

        clan_pill_instant_salvo = sum(m["pill_instant_dmg"] for m in analyzed_members if m["pill_status"] == "ACTIVE")
        clan_pill_regen_salvo = sum(m["pill_regen_dmg"] for m in analyzed_members if m["pill_status"] == "ACTIVE")
        clan_pill_instant_fish_salvo = sum(m["pill_instant_fish_dmg"] for m in analyzed_members if m["pill_status"] == "ACTIVE")
        clan_pill_regen_fish_salvo = sum(m["pill_regen_fish_dmg"] for m in analyzed_members if m["pill_status"] == "ACTIVE")
        clan_pill_active_salvo = sum(m["pill_current_dmg"] for m in analyzed_members if m["pill_status"] == "ACTIVE")
        clan_pill_full_salvo = sum(m["pill_full_dmg"] for m in analyzed_members if m["build_type"] in ("WAR", "HYBRID"))
        clan_pill_ready_salvo = sum(m["pill_fish_dmg"] for m in analyzed_members if m["pill_status"] == "READY")
        clan_pill_ready_start_salvo = sum(m["start_salvo_dmg"] for m in analyzed_members if m["pill_status"] == "READY")

        # Realistic Available Salvo until 02:00 Kyiv reset:
        # - ACTIVE: remaining in-hands + remaining regen until current pill ends
        # - READY: clean fighters ready to drink a full pill
        # - COOLDOWN: only if debuff expires before 02:00 (evening session); if after 02:00, 0
        clan_pill_available_salvo = sum(
            (m["pill_instant_fish_dmg"] + m["pill_regen_fish_dmg"]) if m["pill_status"] == "ACTIVE"
            else (m["pill_fish_dmg"] if m["pill_status"] == "READY"
            else (m["pill_fish_dmg"] if m["pill_status"] == "COOLDOWN" and m.get("can_drink_before_reset")
            else 0))
            for m in analyzed_members if m["build_type"] in ("WAR", "HYBRID")
        )
        clan_pill_available_hits = sum(
            (m["pill_instant_fish_hits"] + m["pill_regen_fish_hits"]) if m["pill_status"] == "ACTIVE"
            else (m["pill_fish_hits"] if m["pill_status"] == "READY"
            else (m["pill_fish_hits"] if m["pill_status"] == "COOLDOWN" and m.get("can_drink_before_reset")
            else 0))
            for m in analyzed_members if m["build_type"] in ("WAR", "HYBRID")
        )
        pill_cooldown_can_drink_count = sum(1 for m in analyzed_members if m["pill_status"] == "COOLDOWN" and m.get("can_drink_before_reset"))
        pill_cooldown_blocked_count = sum(1 for m in analyzed_members if m["pill_status"] == "COOLDOWN" and not m.get("can_drink_before_reset"))

        total_clan_today_damage = sum(m["today_damage"] for m in analyzed_members)
        total_clan_target_damage = sum(m["target_damage"] for m in analyzed_members if m.get("target_damage"))
        has_any_yesterday = any(m["has_yesterday"] for m in analyzed_members)
        total_clan_yesterday_damage = sum(m["yesterday_damage"] or 0 for m in analyzed_members if m["has_yesterday"]) if has_any_yesterday else None

        result = {
            "status": "ok",
            "mu": {
                "mu_id": mu_id,
                "name": mu_data.get("name", "Black Mace"),
                "avatar_url": mu_data.get("avatarUrl", ""),
                "members_count": len(analyzed_members),
                "upgrades": mu_data.get("activeUpgradeLevels", {}),
                "headquarters_level": mu_data.get("activeUpgradeLevels", {}).get("headquarters", 0),
                "dormitories_level": mu_data.get("activeUpgradeLevels", {}).get("dormitories", 0),
                "rankings": mu_data.get("rankings", {}),
                "weekly_damage": mu_data.get("rankings", {}).get("muWeeklyDamages", {}).get("value", 0),
                "weekly_rank": mu_data.get("rankings", {}).get("muWeeklyDamages", {}).get("rank", 0),
                "weekly_tier": mu_data.get("rankings", {}).get("muWeeklyDamages", {}).get("tier", "platinum"),
                "total_damage": mu_data.get("rankings", {}).get("muDamages", {}).get("value", 0),
                "wealth": mu_data.get("rankings", {}).get("muWealth", {}).get("value", 0),
                "reputation": mu_data.get("rankings", {}).get("muReputation", {}).get("value", 0),
            },
            "summary": {
                "total_members": len(analyzed_members),
                "war_count": war_count,
                "eco_count": eco_count,
                "hybrid_count": hybrid_count,
                "pill_active_count": pill_active_count,
                "pill_ready_count": pill_ready_count,
                "pill_cooldown_count": pill_cooldown_count,
                "afk_count": afk_count,
                "clan_daily_salvo_min": total_clan_daily_salvo_min,
                "clan_daily_salvo_max": total_clan_daily_salvo_max,
                "clan_pill_active_salvo": clan_pill_active_salvo,
                "clan_pill_instant_salvo": clan_pill_instant_salvo,
                "clan_pill_regen_salvo": clan_pill_regen_salvo,
                "clan_pill_instant_fish_salvo": clan_pill_instant_fish_salvo,
                "clan_pill_regen_fish_salvo": clan_pill_regen_fish_salvo,
                "clan_pill_full_salvo": clan_pill_full_salvo,
                "clan_pill_available_salvo": clan_pill_available_salvo,
                "clan_pill_available_hits": clan_pill_available_hits,
                "pill_cooldown_can_drink_count": pill_cooldown_can_drink_count,
                "pill_cooldown_blocked_count": pill_cooldown_blocked_count,
                "next_reset_kyiv": next_reset_kyiv.strftime("%H:%M %d.%m.%Y"),
                "clan_pill_ready_salvo": clan_pill_ready_salvo,
                "clan_pill_ready_start_salvo": clan_pill_ready_start_salvo,
                "clan_today_damage": total_clan_today_damage,
                "clan_target_damage": total_clan_target_damage,
                "clan_yesterday_damage": total_clan_yesterday_damage,
                "game_date": game_date,
                "yesterday_game_date": yesterday_game_date,
            },
            "members": analyzed_members,
            "updated_at": now_utc.isoformat(),
        }

        _CLAN_CACHE[cache_key] = result
        _CLAN_CACHE["default"] = result
        _CLAN_CACHE_TIME[cache_key] = time.time()
        _CLAN_CACHE_TIME["default"] = time.time()
        return result
