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
from datetime import datetime, timezone
import httpx
import config
from clan_history_db import ClanHistoryDB

logger = logging.getLogger("WarEraClanAnalyzer")

class WarEraClanAnalyzer:
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.user_api_key = (api_key or config.get_api_key()).strip()
        self.base_url = (base_url or getattr(config, "API_BASE_URL", "https://api2.warera.io").replace("/trpc", "")).rstrip("/")
        self.proxy_url = "https://arcana.warera.wiki/api/proxy"
        self._client: Optional[httpx.AsyncClient] = None
        self.history_db = ClanHistoryDB()
        self._cached_config: Optional[Dict[str, Any]] = None
        self.is_community_key = False
        self.api_key = self.user_api_key

    def _get_headers(self, key_override: Optional[str] = None) -> Dict[str, str]:
        key = key_override or self.api_key
        headers = {
            "Accept": "application/json, text/plain, */*",
            "User-Agent": "WarEra-Clan-Intelligence/1.4.0",
        }
        if key:
            headers["Authorization"] = f"Bearer {key}"
        return headers

    async def get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=10.0)
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _call_trpc(self, endpoint: str, payload: Optional[Dict[str, Any]] = None) -> Any:
        client = await self.get_client()
        input_param = "{}"
        if payload is not None:
            import json
            input_param = json.dumps(payload, separators=(',', ':'))

        primary_url = f"{self.base_url}/trpc/{endpoint}"
        proxy_url = f"{self.proxy_url}/trpc/{endpoint}"
        headers = self._get_headers()

        # Try primary
        try:
            r = await client.get(primary_url, params={"input": input_param}, headers=headers)
            if r.status_code == 200:
                data = r.json()
                if "result" in data:
                    return data["result"].get("data")
        except Exception:
            pass

        # Try proxy
        try:
            r2 = await client.get(proxy_url, params={"input": input_param}, headers=headers)
            if r2.status_code == 200:
                data = r2.json()
                if "result" in data:
                    return data["result"].get("data")
        except Exception:
            pass

        return None

    async def get_game_config(self) -> Dict[str, Any]:
        if self._cached_config is None:
            cfg = await self._call_trpc("config.getConfig")
            self._cached_config = cfg or {}
        return self._cached_config

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
        workforce = await self._call_trpc("user.getWorkforce")
        if workforce and isinstance(workforce, dict):
            employees = workforce.get("employees", [])
            if employees:
                owner_id = employees[0].get("user")
                if owner_id:
                    return await self._call_trpc("user.getUserById", {"userId": owner_id})
        return None

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

    async def analyze_clan(self, mu_id_or_user: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyzes a clan / military unit (MU) and all its members.
        mu_id_or_user can be:
        - None: auto-detects from API key owner or 'Luc1fer'
        - 24-hex MU ID (e.g. '69af3162a583a3b5f9941e71')
        - Player nickname or user ID (resolves user.mu)
        """
        mu_id = None
        target_user = None

        if mu_id_or_user:
            # Check if it's already an MU ID
            test_mu = await self._call_trpc("mu.getById", {"muId": mu_id_or_user})
            if test_mu and isinstance(test_mu, dict) and test_mu.get("name"):
                mu_id = mu_id_or_user
                mu_data = test_mu
            else:
                target_user = await self.resolve_user_by_name(mu_id_or_user)
                if target_user and target_user.get("mu"):
                    mu_id = target_user["mu"]
        
        if not mu_id:
            # Fallback to key owner or 'Luc1fer'
            owner = await self.get_owner_user()
            if owner and owner.get("mu"):
                mu_id = owner["mu"]
            else:
                luc = await self.resolve_user_by_name("Luc1fer")
                if luc and luc.get("mu"):
                    mu_id = luc["mu"]

        if not mu_id:
            # Final fallback to Black Mace MU ID
            mu_id = "69af3162a583a3b5f9941e71"

        mu_data = await self._call_trpc("mu.getById", {"muId": mu_id})
        if not mu_data or not isinstance(mu_data, dict):
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

        # Baseline Full Epic Set (Purple Tier IV) flat bonuses:
        # Chest4 (21% armor) + Pants4 (21% armor) = +42% armor
        # Boots4 (21% dodge) = +21% dodge
        # Helmet4 (71% crit damage) = +71% crit damage
        # Gloves4 (21% precision) = +21% precision
        # Weapon4 (Epic sniper/rifle: 150 atk, 25% crit chance)
        EPIC_ARMOR_ADD = 42.0
        EPIC_DODGE_ADD = 21.0
        EPIC_CRIT_DMG_ADD = 71.0
        EPIC_CRIT_CHANCE_ADD = 25.0
        EPIC_WEAPON_ATK = 150.0

        for m in valid_members:
            uid = m.get("_id")
            uname = m.get("username", "Unknown")
            lvl = m.get("leveling", {}).get("level", 1)
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

            # 2. Pill Status ('cocain')
            atk_skill = skills.get("attack", {})
            buff_pct = float(atk_skill.get("buffsPercent", 0.0))
            debuff_pct = float(atk_skill.get("debuffsPercent", 0.0))

            if build_type == "ECO":
                pill_status = "ECO_SUPPORT"
                pill_label = "🚜 Еко-тил"
                pill_color = "gray"
                pill_tip = "Економічний білд. Таблетка для боїв зазвичай не потрібна."
            elif buff_pct >= 50.0:
                pill_status = "ACTIVE"
                pill_label = "💊 П'є зараз (+60%)"
                pill_color = "emerald"
                pill_tip = "Таблетка активна прямо зараз! Боєць на піку бойової атаки."
            elif debuff_pct >= 50.0:
                pill_status = "COOLDOWN"
                pill_label = "⏳ Відкат (-60%)"
                pill_color = "rose"
                pill_tip = "Дія таблетки завершилась, зараз діє дебафф штрафу. Повний дамаг тимчасово заблоковано."
            else:
                pill_status = "READY"
                pill_label = "⚪ Готовий пити"
                pill_color = "blue"
                pill_tip = "Чистий боєць! Таблетку ще не пив, готовий прийняти під наказ командира."

            # 3. Combat Parameters with Full Epic Set Baseline
            base_atk = float(atk_skill.get("value", 100))
            health_skill = skills.get("health", {})
            health_max = float(health_skill.get("total", 100))
            health_regen = float(health_skill.get("hourlyBarRegen", 10))

            # 24h health pool = current full bar + 24 hours of natural regen
            daily_hp_pool = health_max + (24.0 * health_regen)

            # Armor and Dodge computation with Epic Set guarantee
            curr_armor_stat = float(skills.get("armor", {}).get("value", 0))
            curr_dodge_stat = float(skills.get("dodge", {}).get("value", 0))

            # If user has equipment armor/dodge, take max of equipped vs epic standard
            equipped_armor = float(skills.get("armor", {}).get("equipment", 0))
            equipped_dodge = float(skills.get("dodge", {}).get("equipment", 0))

            effective_gear_armor = max(equipped_armor, EPIC_ARMOR_ADD)
            effective_gear_dodge = max(equipped_dodge, EPIC_DODGE_ADD)

            total_raw_armor = curr_armor_stat + effective_gear_armor
            total_raw_dodge = curr_dodge_stat + effective_gear_dodge

            # Apply WarEra soft cap curve (soft cap at 40%, 50% efficiency above 40%)
            eff_armor_pct = min(total_raw_armor, 40.0) + max(0.0, total_raw_armor - 40.0) * 0.5
            eff_dodge_pct = min(total_raw_dodge, 40.0) + max(0.0, total_raw_dodge - 40.0) * 0.5

            # Effective HP cost per hit
            # Armor reduces damage, Dodge has (1 - dodge%) chance of taking 0 HP cost
            base_hit_cost = 10.0 # game constant
            hp_cost_per_hit = base_hit_cost * (1.0 - (eff_armor_pct / 100.0)) * (1.0 - (eff_dodge_pct / 100.0))
            hp_cost_per_hit = max(hp_cost_per_hit, 1.0) # at least 1 HP cost

            # Hits per day from natural HP pool
            hits_per_day_natural = daily_hp_pool / hp_cost_per_hit
            # If user also eats bread/steaks (+250 HP extra pool typical for active combat day)
            hits_per_day_with_food = (daily_hp_pool + 250.0) / hp_cost_per_hit

            # Attack per hit under Pill (+60%)
            equipped_weapon_atk = float(atk_skill.get("weapon", 0))
            effective_weapon_atk = max(equipped_weapon_atk, EPIC_WEAPON_ATK)
            # Rank bonus %
            rank_bonus_pct = float(atk_skill.get("militaryRankPercent", 0.0))
            ammo_bonus_pct = float(atk_skill.get("ammoPercent", 20.0))

            # When pill is taken (+60% attack buff)
            simulated_atk = (base_atk + effective_weapon_atk) * (1.0 + (rank_bonus_pct + ammo_bonus_pct) / 100.0) * 1.60

            # Critical Chance and Critical Damage with Epic Set
            curr_crit_chance = float(skills.get("criticalChance", {}).get("value", 10))
            curr_crit_dmg = float(skills.get("criticalDamages", {}).get("value", 100))
            eq_crit_chance = float(skills.get("criticalChance", {}).get("weapon", 0))
            eq_crit_dmg = float(skills.get("criticalDamages", {}).get("equipment", 0))

            total_crit_chance = curr_crit_chance + max(eq_crit_chance, EPIC_CRIT_CHANCE_ADD)
            total_crit_dmg = curr_crit_dmg + max(eq_crit_dmg, EPIC_CRIT_DMG_ADD)
            crit_multiplier = 1.0 + ((total_crit_chance / 100.0) * (total_crit_dmg / 100.0))

            # MU Order bonus (+10%)
            mu_order_bonus = 1.10

            avg_dmg_per_hit = simulated_atk * crit_multiplier * mu_order_bonus

            # Daily theoretical expected damage (Min: Natural regen, Max: Natural + standard food/booster)
            theoretical_daily_dmg_min = round(hits_per_day_natural * avg_dmg_per_hit)
            theoretical_daily_dmg_max = round(hits_per_day_with_food * avg_dmg_per_hit)

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

            # In-game weekly damages
            weekly_dmg = int(rankings.get("weeklyUserDamages", {}).get("value", 0))
            total_dmg = int(rankings.get("userDamages", {}).get("value", 0))
            wealth_total = float(stats.get("wealth", {}).get("total", 0.0))

            analyzed_members.append({
                "user_id": uid,
                "username": uname,
                "level": lvl,
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
                # Gear & Combat Specs
                "effective_armor": round(eff_armor_pct, 1),
                "effective_dodge": round(eff_dodge_pct, 1),
                "hp_cost_per_hit": round(hp_cost_per_hit, 2),
                "hits_per_day_natural": round(hits_per_day_natural),
                "hits_per_day_max": round(hits_per_day_with_food),
                "avg_dmg_per_hit": round(avg_dmg_per_hit),
                "theoretical_daily_dmg_min": theoretical_daily_dmg_min,
                "theoretical_daily_dmg_max": theoretical_daily_dmg_max,
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

        total_clan_today_damage = sum(m["today_damage"] for m in analyzed_members)
        has_any_yesterday = any(m["has_yesterday"] for m in analyzed_members)
        total_clan_yesterday_damage = sum(m["yesterday_damage"] or 0 for m in analyzed_members if m["has_yesterday"]) if has_any_yesterday else None

        return {
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
                "clan_today_damage": total_clan_today_damage,
                "clan_yesterday_damage": total_clan_yesterday_damage,
                "game_date": game_date,
                "yesterday_game_date": yesterday_game_date,
            },
            "members": analyzed_members,
            "updated_at": now_utc.isoformat(),
        }
