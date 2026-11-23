"""
WarEra Battle & Combat Loot Intelligence Analyzer
Monitors active battles and calculates the minimum damage required to secure Purple (Epic T4) and higher drops.
Features:
- Precise round ETA calculation (ETA to round finish based on tick rate & points to win 300)
- Sniper Window detection (15-20 min before round finish for 100% reliable settled damage & drop data)
- Rate-limit handling, multi-node failover, connection pooling, and smart caching.
"""

import asyncio
import base64
from datetime import datetime, timezone
import json
import logging
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import httpx

import config
from data_manager import get_data_file
from warera_client import WarEraClient, get_warera_client

logger = logging.getLogger("WarEraBattleAnalyzer")

# Equipment and weapon tier definitions
PURPLE_ITEMS = {
    'helmet4', 'chest4', 'pants4', 'boots4', 'gloves4', 'sniper'
}
LEGENDARY_ITEMS = {
    'helmet5', 'chest5', 'pants5', 'boots5', 'gloves5', 'tank'
}
MYTHIC_ITEMS = {
    'helmet6', 'chest6', 'pants6', 'boots6', 'gloves6', 'jet'
}
RARE_ITEMS = {
    'helmet3', 'chest3', 'pants3', 'boots3', 'gloves3', 'rifle'
}
UNCOMMON_ITEMS = {
    'helmet2', 'chest2', 'pants2', 'boots2', 'gloves2', 'gun'
}
COMMON_ITEMS = {
    'helmet1', 'chest1', 'pants1', 'boots1', 'gloves1', 'knife'
}

ITEM_NAMES = {
    'helmet1': 'Шолом T1', 'chest1': 'Броня T1', 'pants1': 'Штани T1', 'boots1': 'Чоботи T1', 'gloves1': 'Рукавиці T1', 'knife': 'Ніж T1',
    'helmet2': 'Шолом T2', 'chest2': 'Броня T2', 'pants2': 'Штани T2', 'boots2': 'Чоботи T2', 'gloves2': 'Рукавиці T2', 'gun': 'Пістолет T2',
    'helmet3': 'Шолом T3', 'chest3': 'Броня T3', 'pants3': 'Штани T3', 'boots3': 'Чоботи T3', 'gloves3': 'Рукавиці T3', 'rifle': 'Гвинтівка T3',
    'helmet4': 'Шолом T4 (Фіол)', 'chest4': 'Броня T4 (Фіол)', 'pants4': 'Штани T4 (Фіол)', 'boots4': 'Чоботи T4 (Фіол)', 'gloves4': 'Рукавиці T4 (Фіол)', 'sniper': 'Снайперка T4 (Фіол)',
    'helmet5': 'Шолом T5 (Лега)', 'chest5': 'Броня T5 (Лега)', 'pants5': 'Штани T5 (Лега)', 'boots5': 'Чоботи T5 (Лега)', 'gloves5': 'Рукавиці T5 (Лега)', 'tank': 'Танк T5 (Лега)',
    'helmet6': 'Шолом T6 (Міфік)', 'chest6': 'Броня T6 (Міфік)', 'pants6': 'Штани T6 (Міфік)', 'boots6': 'Чоботи T6 (Міфік)', 'gloves6': 'Рукавиці T6 (Міфік)', 'jet': 'Винищувач T6 (Міфік)',
    'case1': 'Кейс 1 (Лега)', 'case2': 'Кейс 2 (Міфік)', 'woodenCase': 'Дерев\'яний кейс', 'toolbox': 'Ящик інструментів'
}

def get_item_tier_info(code: Optional[str]) -> Dict[str, Any]:
    if not code:
        return {'tier': 0, 'rarity': 'none', 'name': 'Немає дропу', 'color': '#6b7280', 'is_purple': False, 'is_purple_plus': False}
    c = code.lower()
    if c in MYTHIC_ITEMS:
        return {'tier': 6, 'rarity': 'mythic', 'name': ITEM_NAMES.get(c, c), 'color': '#ef4444', 'is_purple': False, 'is_purple_plus': True}
    if c in LEGENDARY_ITEMS:
        return {'tier': 5, 'rarity': 'legendary', 'name': ITEM_NAMES.get(c, c), 'color': '#f59e0b', 'is_purple': False, 'is_purple_plus': True}
    if c in PURPLE_ITEMS:
        return {'tier': 4, 'rarity': 'epic', 'name': ITEM_NAMES.get(c, c), 'color': '#c084fc', 'is_purple': True, 'is_purple_plus': True}
    if c in RARE_ITEMS:
        return {'tier': 3, 'rarity': 'rare', 'name': ITEM_NAMES.get(c, c), 'color': '#60a5fa', 'is_purple': False, 'is_purple_plus': False}
    if c in UNCOMMON_ITEMS:
        return {'tier': 2, 'rarity': 'uncommon', 'name': ITEM_NAMES.get(c, c), 'color': '#34d399', 'is_purple': False, 'is_purple_plus': False}
    return {'tier': 1, 'rarity': 'common', 'name': ITEM_NAMES.get(c, c), 'color': '#9ca3af', 'is_purple': False, 'is_purple_plus': False}


def get_tick_points(tick: int) -> int:
    """Returns points awarded per tick depending on round duration."""
    if tick >= 500: return 6
    if tick >= 400: return 5
    if tick >= 300: return 4
    if tick >= 200: return 3
    if tick >= 100: return 2
    return 1


def calculate_round_eta(current_tick: int, att_pts: int, def_pts: int, points_to_win: int = 300) -> Dict[str, Any]:
    """
    Calculates the exact remaining minutes until one side reaches 300 points and ends the round.
    Identifies if the battle is in the reliable Sniper Window (15-20 min before finish).
    """
    leading_pts = max(att_pts, def_pts)
    trailing_pts = min(att_pts, def_pts)
    needed = points_to_win - leading_pts

    if needed <= 0:
        return {
            "minutesLeft": 0,
            "minMinutesLeft": 0,
            "projectedMinutesLeft": 0,
            "formattedEta": "Завершується",
            "status": "finished",
            "statusLabel": "🏁 Раунд завершено",
            "isSniperWindow": False,
            "isReliable": True,
            "badgeColor": "gray"
        }

    # 1. Earliest finish: leading side wins every future tick without interruption
    sim_tick = current_tick
    sim_pts = leading_pts
    ticks_min = 0
    while sim_pts < points_to_win:
        sim_tick += 1
        pts = get_tick_points(sim_tick)
        sim_pts += pts
        ticks_min += 1
        if ticks_min > 600:
            break

    # 2. Projected finish: account for tick distribution between attacker and defender
    win_rate = leading_pts / max(1, current_tick)
    win_rate = max(0.35, min(1.0, win_rate))
    avg_future_pts = get_tick_points(current_tick + ticks_min // 2)
    ticks_projected = max(ticks_min, int(needed / (avg_future_pts * win_rate)))

    # Select representative minutes left
    # If dominant side is overwhelming (e.g. win_rate > 0.8), use ticks_min, else blend
    if win_rate >= 0.75:
        minutes_left = ticks_min
    else:
        minutes_left = int(ticks_min * 0.4 + ticks_projected * 0.6)

    # Format ETA string
    if minutes_left >= 60:
        hours = minutes_left // 60
        mins = minutes_left % 60
        formatted_eta = f"~{hours} год {mins} хв"
    else:
        formatted_eta = f"~{minutes_left} хв"

    # Stage categorization
    # Sniper window: 15-25 minutes before end (or urgent < 15 min)
    if 15 <= minutes_left <= 25:
        status = "sniper_window"
        status_label = "🎯 Снайперське вікно (15–20 хв)"
        is_sniper_window = True
        is_reliable = True
        badge_color = "emerald"
    elif minutes_left < 15:
        status = "urgent"
        status_label = "⚡ Фінішна пряма (<15 хв)"
        is_sniper_window = True
        is_reliable = True
        badge_color = "amber"
    elif minutes_left <= 35:
        status = "closing_soon"
        status_label = "⏳ Скоро завершення (<35 хв)"
        is_sniper_window = False
        is_reliable = False
        badge_color = "blue"
    else:
        status = "in_progress"
        status_label = "⏳ Ранній етап (>35 хв)"
        is_sniper_window = False
        is_reliable = False
        badge_color = "gray"

    return {
        "minutesLeft": minutes_left,
        "minMinutesLeft": ticks_min,
        "projectedMinutesLeft": ticks_projected,
        "formattedEta": formatted_eta,
        "status": status,
        "statusLabel": status_label,
        "isSniperWindow": is_sniper_window,
        "isReliable": is_reliable,
        "badgeColor": badge_color,
        "pointsNeeded": needed,
        "leadingPoints": leading_pts
    }


class WarEraBattleAnalyzer:
    def __init__(self, base_url: Optional[str] = None, client: Optional[WarEraClient] = None):
        self.client = client or get_warera_client()
        self.api_hosts = self.client.api_hosts
        self._current_host_idx = 0
        self._host_rate_limits = self.client._host_rate_limits
        self._ranks_cache = self.client._ranks_cache
        self._countries_cache = self.client._countries_cache
        self._regions_cache = self.client._regions_cache
        self._users_cache = self.client._users_cache
        self._meta_loaded = False

        # In-memory short-lived cache for complete intel report (8 seconds)
        self._cached_intel: Optional[List[Dict[str, Any]]] = None
        self._cached_intel_time: float = 0.0

    async def get_client(self) -> httpx.AsyncClient:
        return await self.client.get_client()

    async def close(self):
        await self.client.close()

    async def _call_trpc(self, endpoint: str, payload: Optional[Dict[str, Any]] = None) -> Any:
        return await self.client.call_trpc(endpoint, payload=payload)

    async def load_metadata(self, force: bool = False):
        await self.client.load_metadata(force=force)
        self._regions_cache = self.client._regions_cache
        self._countries_cache = self.client._countries_cache
        if self._regions_cache and self._countries_cache:
            self._meta_loaded = True

    async def get_username(self, user_id: str) -> str:
        return await self.client.get_user_name(user_id)

    async def fetch_active_battles(self) -> List[Dict[str, Any]]:
        all_battles = []
        cursor = None
        seen_ids = set()
        for _ in range(4):
            payload = {"limit": 100}
            if cursor:
                payload["cursor"] = cursor
            data = await self._call_trpc("battle.getBattles", payload)
            if not isinstance(data, dict):
                break
            items = data.get("items", [])
            if not items:
                break
            any_active_in_page = False
            for b in items:
                bid = b.get("_id")
                is_act = b.get("isActive", True) is True and not b.get("endedAt")
                if is_act:
                    any_active_in_page = True
                    # Completely exclude closed tournament matches from all searches and alerts
                    if b.get("type") != "tournament":
                        if bid and bid not in seen_ids:
                            seen_ids.add(bid)
                            all_battles.append(b)

            if not any_active_in_page:
                break
            cursor = data.get("nextCursor")
            if not cursor:
                break

        return all_battles

    def _make_cursor(self, offset: int) -> str:
        raw = json.dumps([{"t": "num", "v": offset}, {"t": "str", "v": "6afde6eeccf0b1e6a33f647e"}])
        return "v2." + base64.b64encode(raw.encode()).decode()

    async def fetch_ranking(self, target_id: str, is_round: bool = True, limit: int = 100) -> List[Dict[str, Any]]:
        if not target_id:
            return []
        now = time.time()
        if target_id in self._ranks_cache:
            c_time, c_items = self._ranks_cache[target_id]
            if (now - c_time) < 45.0:
                return c_items

        payload = {
            "dataType": "damage",
            "type": "user",
            "side": "merged",
            "limit": limit
        }
        if is_round:
            payload["roundId"] = target_id
        else:
            payload["battleId"] = target_id

        data = await self._call_trpc("battleRanking.getRanking", payload)
        if isinstance(data, dict):
            items = data.get("items", [])
            total_count = data.get("itemCount", len(items))

            # In large battles (like resistance revolts with 2000+ players),
            # purple loot drops can extend well beyond rank 100 (e.g. rank 1255).
            # If the 100th item is still purple, binary-search the exact boundary.
            if items and total_count > len(items):
                last_code = items[-1].get('lootItem', {}).get('code')
                if get_item_tier_info(last_code)['is_purple_plus']:
                    low = len(items)
                    high = total_count - 1
                    best_purple = items[-1]
                    next_below = None
                    probes = 0
                    while low <= high and probes < 7:
                        probes += 1
                        mid = (low + high) // 2
                        p_probe = dict(payload)
                        p_probe["limit"] = 2
                        p_probe["cursor"] = self._make_cursor(mid)
                        probe_data = await self._call_trpc("battleRanking.getRanking", p_probe)
                        if not isinstance(probe_data, dict):
                            break
                        probe_items = probe_data.get("items", [])
                        if not probe_items:
                            high = mid - 1
                            continue
                        p_item = probe_items[0]
                        p_code = p_item.get('lootItem', {}).get('code')
                        if get_item_tier_info(p_code)['is_purple_plus']:
                            best_purple = p_item
                            if len(probe_items) > 1 and not get_item_tier_info(probe_items[1].get('lootItem', {}).get('code'))['is_purple_plus']:
                                next_below = probe_items[1]
                                break
                            low = mid + 1
                        else:
                            next_below = p_item
                            high = mid - 1

                    if best_purple.get('rank') != items[-1].get('rank'):
                        items.append(best_purple)
                    if next_below:
                        items.append(next_below)

            self._ranks_cache[target_id] = (now, items)
            return items
        if target_id in self._ranks_cache:
            return self._ranks_cache[target_id][1]
        return []

    def _analyze_ranking_cutoff(self, ranks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyzes ranking list to extract:
        - All players with purple+ drops (T4 epic, T5 legendary, T6 mythic)
        - The exact cutoff threshold to get purple loot
        - The last purple holder and the next player below them
        """
        if not ranks:
            return {
                "has_purple": False,
                "min_damage_for_purple": None,
                "needed_damage_to_claim": 1,
                "cutoff_rank": None,
                "last_purple_player": None,
                "last_purple_item": None,
                "next_player_below": None,
                "gap_to_next": 0,
                "total_purple_plus_items": 0,
                "ranks_count": 0,
                "purple_items_summary": [],
                "full_ranks": []
            }

        purple_holders = []
        full_ranks = []
        for r in ranks:
            loot = r.get('lootItem')
            loot_code = loot.get('code') if loot else None
            tinfo = get_item_tier_info(loot_code)

            rank_entry = {
                "rank": r.get('rank'),
                "damage": r.get('value', 0),
                "user_id": r.get('user'),
                "item_code": loot_code,
                "item_info": tinfo,
                "skills": loot.get('skills', {}) if loot else {}
            }
            full_ranks.append(rank_entry)

            if tinfo['is_purple_plus']:
                purple_holders.append(rank_entry)

        if not purple_holders:
            return {
                "has_purple": False,
                "min_damage_for_purple": None,
                "needed_damage_to_claim": 1,
                "cutoff_rank": None,
                "last_purple_player": None,
                "last_purple_item": None,
                "next_player_below": None,
                "gap_to_next": 0,
                "total_purple_plus_items": 0,
                "ranks_count": len(ranks),
                "purple_items_summary": [],
                "full_ranks": full_ranks
            }

        last_holder = purple_holders[-1]
        last_rank = last_holder["rank"]
        min_damage = last_holder["damage"]

        # Find next player below last_rank
        next_player = None
        for r in ranks:
            if r.get('rank') > last_rank:
                next_code = r.get('lootItem', {}).get('code') if r.get('lootItem') else None
                next_player = {
                    "rank": r.get('rank'),
                    "damage": r.get('value', 0),
                    "user_id": r.get('user'),
                    "item_code": next_code,
                    "item_info": get_item_tier_info(next_code)
                }
                break

        gap = (min_damage - next_player["damage"]) if next_player else min_damage

        return {
            "has_purple": True,
            "min_damage_for_purple": min_damage,
            "needed_damage_to_claim": min_damage + 1,
            "cutoff_rank": last_rank,
            "last_purple_player": last_holder,
            "last_purple_item": last_holder["item_info"],
            "next_player_below": next_player,
            "gap_to_next": gap,
            "total_purple_plus_items": max(len(purple_holders), last_rank) if last_rank else len(purple_holders),
            "ranks_count": len(ranks),
            "purple_items_summary": [h["item_code"] for h in purple_holders],
            "full_ranks": full_ranks
        }

    async def get_all_battles_intel(self, user_id_filter: Optional[str] = None, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Master method: scans all active battles, computes timing and ETA,
        and produces complete combat intelligence report using high-speed parallel fetching.
        """
        now = time.time()
        if not force_refresh and self._cached_intel and (now - self._cached_intel_time) < 25.0:
            return self._cached_intel

        await self.load_metadata()
        raw_battles = await self.fetch_active_battles()
        if not raw_battles:
            if self._cached_intel:
                logger.info("fetch_active_battles empty, reusing existing cached intel")
                return self._cached_intel
            # If no cached intel yet, rotate node and retry once
            self._current_host_idx = (self._current_host_idx + 1) % len(self.api_hosts)
            raw_battles = await self.fetch_active_battles()
            if not raw_battles and self._cached_intel:
                return self._cached_intel

        # Prioritize ranking fetch to stay well within WarEra API limits (max 5-8 ranking calls)
        fetch_battle_ids = set()
        active_candidates = []
        for b in raw_battles:
            curr = b.get('currentRound', {})
            if not isinstance(curr, dict):
                curr = {}
            att_p = curr.get('attacker', {}).get('points', 0)
            def_p = curr.get('defender', {}).get('points', 0)
            ticks = curr.get('live', {}).get('ticksCount', 0)
            max_p = max(att_p, def_p)
            eta = calculate_round_eta(ticks, att_p, def_p, 300)
            mins = eta.get('minutesLeft', 999)
            is_sniper = eta.get('isSniperWindow', False)

            if max_p >= 300:
                continue

            prio = 3 if is_sniper else (2 if mins <= 45 else 1)
            active_candidates.append((prio, mins, b.get('_id')))

        active_candidates.sort(key=lambda x: (-x[0], x[1]))
        count = 0
        for prio, mins, bid in active_candidates:
            if prio == 3:
                fetch_battle_ids.add(bid)
                count += 1
            elif prio == 2 and count < 8:
                fetch_battle_ids.add(bid)
                count += 1
            elif count < 5:
                fetch_battle_ids.add(bid)
                count += 1

        sem = asyncio.Semaphore(4)

        async def _analyze_battle(b: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            async with sem:
                b_id = b.get('_id')
                b_type = b.get('type')
                current_round = b.get('currentRound', {})
                if not isinstance(current_round, dict):
                    current_round = {}
                round_id = current_round.get('_id')
                round_num = current_round.get('number', 1)

                raw_att = b.get('attacker', {})
                raw_def = b.get('defender', {})

                att_c_id = raw_att.get('country')
                def_c_id = raw_def.get('country')
                reg_id = raw_def.get('region')

                att_rate = raw_att.get('moneyPer1kDamages')
                att_pool = raw_att.get('moneyPool')
                att_bounty = None
                if att_rate and att_pool and att_pool > 0:
                    att_bounty = {
                        'ratePer1k': float(att_rate),
                        'pool': round(float(att_pool), 2),
                        'effectiveAt': raw_att.get('bountyEffectiveAt'),
                    }

                def_rate = raw_def.get('moneyPer1kDamages')
                def_pool = raw_def.get('moneyPool')
                def_bounty = None
                if def_rate and def_pool and def_pool > 0:
                    def_bounty = {
                        'ratePer1k': float(def_rate),
                        'pool': round(float(def_pool), 2),
                        'effectiveAt': raw_def.get('bountyEffectiveAt'),
                    }

                has_bounty = bool(att_bounty or def_bounty)
                max_bounty_rate = max(
                    att_bounty['ratePer1k'] if att_bounty else 0.0,
                    def_bounty['ratePer1k'] if def_bounty else 0.0,
                )

                att_country = self._countries_cache.get(att_c_id, {})
                def_country = self._countries_cache.get(def_c_id, {})
                region = self._regions_cache.get(reg_id, {})

                round_ranks = []
                if b_id in fetch_battle_ids and round_id:
                    round_ranks = await self.fetch_ranking(round_id, is_round=True)
                battle_ranks = []

                round_att = current_round.get('attacker', {})
                round_def = current_round.get('defender', {})
                att_round_dmg = round_att.get('damages', 0)
                def_round_dmg = round_def.get('damages', 0)
                att_round_pts = round_att.get('points', 0)
                def_round_pts = round_def.get('points', 0)
                total_round_dmg = att_round_dmg + def_round_dmg

                att_battle_dmg = b.get('attacker', {}).get('damages', 0)
                def_battle_dmg = b.get('defender', {}).get('damages', 0)
                total_battle_dmg = att_battle_dmg + def_battle_dmg

                points_to_win = 300
                rounds_to_win = b.get('roundsToWin', 2)
                att_won_rounds = b.get('attacker', {}).get('wonRoundsCount', 0)
                def_won_rounds = b.get('defender', {}).get('wonRoundsCount', 0)

                live_data = current_round.get('live', {})
                current_tick = live_data.get('ticksCount', 0)
                next_tick_at = live_data.get('nextTickAt')

                round_eta = calculate_round_eta(current_tick, att_round_pts, def_round_pts, points_to_win)

                round_intel = self._analyze_ranking_cutoff(round_ranks)
                battle_intel = self._analyze_ranking_cutoff(battle_ranks)

                user_round_pos = None
                user_battle_pos = None
                if user_id_filter:
                    for r in round_ranks:
                        if r.get('user') == user_id_filter:
                            user_round_pos = {
                                'rank': r.get('rank'),
                                'damage': r.get('value', 0),
                                'loot': r.get('lootItem')
                            }
                            break
                    for r in battle_ranks:
                        if r.get('user') == user_id_filter:
                            user_battle_pos = {
                                'rank': r.get('rank'),
                                'damage': r.get('value', 0),
                                'loot': r.get('lootItem')
                            }
                            break

                best_min_dmg = None
                best_scope = None
                if round_intel['has_purple'] and battle_intel['has_purple']:
                    if round_intel['min_damage_for_purple'] <= battle_intel['min_damage_for_purple']:
                        best_min_dmg = round_intel['min_damage_for_purple']
                        best_scope = 'round'
                    else:
                        best_min_dmg = battle_intel['min_damage_for_purple']
                        best_scope = 'battle'
                elif round_intel['has_purple']:
                    best_min_dmg = round_intel['min_damage_for_purple']
                    best_scope = 'round'
                elif battle_intel['has_purple']:
                    best_min_dmg = battle_intel['min_damage_for_purple']
                    best_scope = 'battle'

                user_tasks = []
                if round_intel.get('last_purple_player'):
                    uid = round_intel['last_purple_player']['user_id']
                    user_tasks.append((round_intel['last_purple_player'], self.get_username(uid)))
                if battle_intel.get('last_purple_player'):
                    uid = battle_intel['last_purple_player']['user_id']
                    user_tasks.append((battle_intel['last_purple_player'], self.get_username(uid)))
                if user_tasks:
                    unames = await asyncio.gather(*[ut[1] for ut in user_tasks], return_exceptions=True)
                    for (target_dict, _), uname in zip(user_tasks, unames):
                        target_dict['username'] = uname if isinstance(uname, str) else 'Unknown'

                if b_type == 'tournament':
                    reg_name = '🏆 Турнірна Арена'
                    att_name = 'Атакуюча команда'
                    att_code = 'TOURNAMENT'
                    att_flag = '🏆'
                    def_name = 'Захисна команда'
                    def_code = 'TOURNAMENT'
                    def_flag = '🏆'
                else:
                    reg_name = region.get('name', 'Невідомий регіон')
                    att_name = att_country.get('name', 'Атакуючі')
                    att_code = att_country.get('code', '??')
                    att_flag = att_country.get('flag', '🏳️')
                    def_name = def_country.get('name', 'Захисники')
                    def_code = def_country.get('code', '??')
                    def_flag = def_country.get('flag', '🏳️')

                return {
                    'battleId': b_id,
                    'type': b_type,
                    'region': {
                        'id': reg_id,
                        'name': reg_name
                    },
                    'attacker': {
                        'countryId': att_c_id,
                        'name': att_name,
                        'code': att_code,
                        'flag': att_flag,
                        'roundPoints': att_round_pts,
                        'roundDamage': att_round_dmg,
                        'wonRounds': att_won_rounds,
                        'bounty': att_bounty,
                    },
                    'defender': {
                        'countryId': def_c_id,
                        'name': def_name,
                        'code': def_code,
                        'flag': def_flag,
                        'roundPoints': def_round_pts,
                        'roundDamage': def_round_dmg,
                        'wonRounds': def_won_rounds,
                        'bounty': def_bounty,
                    },
                    'hasBounty': has_bounty,
                    'maxBountyRate': max_bounty_rate,
                    'round': {
                        'id': round_id,
                        'number': round_num,
                        'totalDamage': total_round_dmg,
                        'pointsToWin': points_to_win,
                        'currentTick': current_tick,
                        'nextTickAt': next_tick_at,
                        'leadingSide': 'attacker' if att_round_pts > def_round_pts else ('defender' if def_round_pts > att_round_pts else 'tied'),
                        'pointsDifference': abs(att_round_pts - def_round_pts),
                        'maxPoints': max(att_round_pts, def_round_pts)
                    },
                    'timing': round_eta,
                    'battle': {
                        'roundsToWin': rounds_to_win,
                        'totalDamage': total_battle_dmg
                    },
                    'roundCutoff': round_intel,
                    'battleCutoff': battle_intel,
                    'bestPurpleMinDamage': best_min_dmg,
                    'bestPurpleScope': best_scope,
                    'userPosition': {
                        'round': user_round_pos,
                        'battle': user_battle_pos
                    },
                    'isActive': bool(b.get('isActive', True) and not b.get('endedAt')),
                    'wareraUrl': f'https://app.warera.io/battle/{b_id}'
                }

        results = await asyncio.gather(*[_analyze_battle(b) for b in raw_battles], return_exceptions=True)
        analyzed_battles = [r for r in results if isinstance(r, dict)]

        def sort_key(b):
            is_sniper = 0 if b.get('timing', {}).get('isSniperWindow') else (1 if b.get('timing', {}).get('minutesLeft', 999) < 40 else 2)
            has_purple = 0 if (b.get('roundCutoff', {}).get('has_purple') or b.get('battleCutoff', {}).get('has_purple')) else 1
            dmg = b.get('bestPurpleMinDamage') or 999999999999
            return (is_sniper, has_purple, dmg)

        if analyzed_battles:
            analyzed_battles.sort(key=sort_key)
            self._cached_intel = analyzed_battles
            self._cached_intel_time = time.time()
            return analyzed_battles
        elif self._cached_intel:
            return self._cached_intel
        return []

    async def get_active_contracts(self) -> List[Dict[str, Any]]:
        """
        Returns all active battle contracts (bounties/hiring payouts) across all current battles,
        sorted by highest payment rate per 1k damage descending.
        """
        battles = await self.get_all_battles_intel()
        contracts = []
        for b in battles:
            b_id = b.get('battleId')
            reg = b.get('region', {})
            timing = b.get('timing', {})
            b_type = b.get('type', 'war')
            url = b.get('wareraUrl')

            round_info = b.get('round', {})
            r_id = round_info.get('id', '')
            r_num = round_info.get('number', 1)

            for side in ('attacker', 'defender'):
                side_info = b.get(side, {})
                bounty = side_info.get('bounty')
                if bounty:
                    contracts.append({
                        'battleId': b_id,
                        'roundId': r_id,
                        'roundNumber': r_num,
                        'type': b_type,
                        'region': reg.get('name', 'Unknown'),
                        'side': side,
                        'sideName': 'Атака' if side == 'attacker' else 'Оборона',
                        'country': side_info.get('name', 'Unknown'),
                        'flag': side_info.get('flag', '🏳️'),
                        'ratePer1k': bounty.get('ratePer1k', 0.0),
                        'pool': bounty.get('pool', 0.0),
                        'effectiveAt': bounty.get('effectiveAt'),
                        'isSniperWindow': timing.get('isSniperWindow', False),
                        'etaMinutes': timing.get('minutesLeft', 0),
                        'wareraUrl': url,
                    })
        # Sort by rate per 1k descending, then pool descending
        contracts.sort(key=lambda x: (x['ratePer1k'], x['pool']), reverse=True)
        return contracts

    async def get_active_contract_auctions(self) -> List[Dict[str, Any]]:
        """
        Fetches all active mercenary contract auctions from WarEra API,
        enriches them with battle region, country, side, and calculates time remaining.
        Sorted by contract budget descending, then rate descending.
        """
        battles = await self.get_all_battles_intel()
        battles_by_id = {b.get('battleId'): b for b in battles}

        try:
            data = await self._call_trpc('trpc/mercenaryContractAuction.getActiveAuctions', {'json': None})
            if not isinstance(data, dict):
                return []

            items = data.get('items', [])
            auctions = []
            now = datetime.now(timezone.utc)

            for a in items:
                b_id = a.get('battle')
                b_info = battles_by_id.get(b_id, {})
                side = a.get('forCountrySide', 'attacker')
                side_info = b_info.get(side, {})
                reg = b_info.get('region', {})

                created_at_str = a.get('createdAt', '')
                expires_at_str = a.get('expiresAt', '')

                time_remaining_sec = 0.0
                if expires_at_str:
                    try:
                        exp_dt = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
                        time_remaining_sec = max(0.0, (exp_dt - now).total_seconds())
                    except Exception:
                        pass

                budget = float(a.get('budget', 0.0) or 0.0)
                min_damage = int(a.get('minimumDamage', 0) or 0)
                rate = float(a.get('currentPerK') or a.get('initialPerK') or 0.0)

                auctions.append({
                    'auctionId': a.get('_id'),
                    'battleId': b_id,
                    'roundId': a.get('round'),
                    'roundNumber': a.get('roundNumber', 1),
                    'type': b_info.get('type', 'war'),
                    'region': reg.get('name', 'Unknown'),
                    'side': side,
                    'sideName': 'Атака' if side == 'attacker' else 'Оборона',
                    'country': side_info.get('name', 'Unknown'),
                    'flag': side_info.get('flag', '🏳️'),
                    'budget': budget,
                    'minimumDamage': min_damage,
                    'ratePer1k': rate,
                    'timeRemainingSec': time_remaining_sec,
                    'expiresAt': expires_at_str,
                    'createdAt': created_at_str,
                    'bidsCount': len(a.get('bids', [])),
                    'wareraUrl': b_info.get('wareraUrl', f"https://app.warera.io/battle/{b_id}"),
                })

            # Sort by budget descending, then rate descending
            auctions.sort(key=lambda x: (x['budget'], x['ratePer1k']), reverse=True)
            return auctions
        except Exception as e:
            logger.error(f"Error fetching contract auctions: {e}")
            return []

    async def get_active_battles_for_focus(self) -> List[Dict[str, Any]]:
        """
        Returns active battles prioritized for user focus selection:
        Battles with active bounties first (highest rate desc), then other active battles.
        """
        await self.load_metadata()
        raw_battles = await self.fetch_active_battles()
        active_raw = [b for b in raw_battles if b.get('isActive', True) is True and not b.get('endedAt')]
        active_list = []
        seen_bids = set()
        for b in active_raw:
            b_id = b.get('_id')
            if not b_id or b_id in seen_bids:
                continue
            seen_bids.add(b_id)
            curr = b.get('currentRound', {})
            r_num = curr.get('number', 1) if isinstance(curr, dict) else 1
            b_type = b.get('type', 'war')

            raw_att = b.get('attacker', {})
            raw_def = b.get('defender', {})
            att_c_id = raw_att.get('country')
            def_c_id = raw_def.get('country')
            reg_id = raw_def.get('region')

            region_name = self._regions_cache.get(reg_id, {}).get('name', 'Unknown')
            att_country = self._countries_cache.get(att_c_id, {}).get('name', 'Attacker')
            att_flag = self._countries_cache.get(att_c_id, {}).get('flag', '🏳️')
            def_country = self._countries_cache.get(def_c_id, {}).get('name', 'Defender')
            def_flag = self._countries_cache.get(def_c_id, {}).get('flag', '🏳️')

            att_pool = float(raw_att.get('moneyPool') or 0.0)
            def_pool = float(raw_def.get('moneyPool') or 0.0)
            att_rate = float(raw_att.get('moneyPer1kDamages') or 0.0) if att_pool > 0 else 0.0
            def_rate = float(raw_def.get('moneyPer1kDamages') or 0.0) if def_pool > 0 else 0.0
            max_rate = max(att_rate, def_rate)
            has_bounty = max_rate > 0

            active_list.append({
                'battleId': b_id,
                'regionName': region_name,
                'type': b_type,
                'roundNumber': r_num,
                'attackerCountry': att_country,
                'attackerFlag': att_flag,
                'defenderCountry': def_country,
                'defenderFlag': def_flag,
                'attackerRate': att_rate,
                'defenderRate': def_rate,
                'hasBounty': has_bounty,
                'maxBountyRate': max_rate,
                'wareraUrl': f'https://app.warera.io/battle/{b_id}'
            })

        active_list.sort(key=lambda x: (not x['hasBounty'], -x['maxBountyRate'], x['regionName']))
        return active_list


_SHARED_ANALYZER: Optional['WarEraBattleAnalyzer'] = None

def get_shared_battle_analyzer() -> 'WarEraBattleAnalyzer':
    global _SHARED_ANALYZER
    if _SHARED_ANALYZER is None:
        _SHARED_ANALYZER = WarEraBattleAnalyzer()
    return _SHARED_ANALYZER
