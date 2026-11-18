"""
WarEra Battle & Combat Loot Intelligence Analyzer
Monitors active battles and calculates the minimum damage required to secure Purple (Epic T4) and higher drops.
Features:
- Precise round ETA calculation (ETA to round finish based on tick rate & points to win 300)
- Sniper Window detection (15-20 min before round finish for 100% reliable settled damage & drop data)
- Rate-limit handling, multi-node failover, connection pooling, and smart caching.
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, List, Optional, Tuple
import httpx

import config

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
    def __init__(self, base_url: Optional[str] = None):
        self.api_hosts = [
            "https://api2.warera.io/trpc",
            "https://api3.warera.io/trpc",
            "https://api4.warera.io/trpc",
            "https://api5.warera.io/trpc",
            "https://api6.warera.io/trpc",
        ]
        self._rate_limited_until: float = 0.0
        self._ranks_cache: Dict[str, Tuple[float, List[Dict[str, Any]]]] = {}
        self._current_host_idx = 0
        self._client: Optional[httpx.AsyncClient] = None
        self._semaphore = asyncio.Semaphore(4)

        self._countries_cache: Dict[str, Dict[str, Any]] = {}
        self._regions_cache: Dict[str, Dict[str, Any]] = {}
        self._users_cache: Dict[str, str] = {}
        self._meta_loaded = False

        # In-memory short-lived cache for complete intel report (8 seconds)
        self._cached_intel: Optional[List[Dict[str, Any]]] = None
        self._cached_intel_time: float = 0.0

    async def get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            headers = {
                "Accept": "application/json",
                "User-Agent": "WarEraBattleIntel/1.2",
            }
            # Pure Public Zero-Auth: All WarEra battle endpoints (getBattles, getRanking)
            # are open and require NO API key. We strictly DO NOT send the user's private key.
            self._client = httpx.AsyncClient(
                headers=headers,
                timeout=15.0,
                limits=httpx.Limits(max_keepalive_connections=20, max_connections=30)
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _call_trpc(self, endpoint: str, payload: Optional[Dict[str, Any]] = None) -> Any:
        now = time.time()
        if now < self._rate_limited_until:
            return None

        client = await self.get_client()
        input_param = "{}" if payload is None else json.dumps(payload, separators=(',', ':'))

        async with self._semaphore:
            # Pacing delay between requests to stay well below the 100 req/min limit
            await asyncio.sleep(0.06)
            for attempt in range(2):
                host = self.api_hosts[self._current_host_idx]
                url = f"{host}/{endpoint}"
                try:
                    r = await client.get(url, params={"input": input_param})
                    if r.status_code == 200:
                        data = r.json()
                        return data.get("result", {}).get("data")
                    elif r.status_code == 429:
                        # Instant backoff: do not execute blocking sleeps in loop!
                        self._rate_limited_until = time.time() + 25.0
                        self._current_host_idx = (self._current_host_idx + 1) % len(self.api_hosts)
                        logger.warning(f"Rate limit on {host}/{endpoint}. Backing off for 25s...")
                        return None
                    else:
                        self._current_host_idx = (self._current_host_idx + 1) % len(self.api_hosts)
                except Exception:
                    self._current_host_idx = (self._current_host_idx + 1) % len(self.api_hosts)

        return None

    async def load_metadata(self, force: bool = False):
        if self._meta_loaded and not force:
            return

        c_data = await self._call_trpc("country.getAllCountries", {})
        if isinstance(c_data, list):
            self._countries_cache = {c['_id']: c for c in c_data if isinstance(c, dict) and '_id' in c}

        r_data = await self._call_trpc("region.getRegionsObject", {})
        if isinstance(r_data, dict):
            self._regions_cache = r_data

        self._meta_loaded = True

    async def get_username(self, user_id: str) -> str:
        if not user_id:
            return "Unknown"
        if user_id in self._users_cache:
            return self._users_cache[user_id]

        fallback = user_id[:8]
        try:
            client = await self.get_client()
            param = json.dumps({"userId": user_id})
            host = self.api_hosts[self._current_host_idx]
            r = await client.get(f"{host}/user.getUserById?input={param}")
            if r.status_code == 200:
                u = r.json().get('result', {}).get('data', {})
                name = u.get('username') or fallback
                self._users_cache[user_id] = name
                return name
        except Exception:
            pass

        self._users_cache[user_id] = fallback
        return fallback

    async def fetch_active_battles(self) -> List[Dict[str, Any]]:
        data = await self._call_trpc("battle.getBattles", {})
        if isinstance(data, dict):
            return data.get("items", [])
        return []

    async def fetch_ranking(self, target_id: str, is_round: bool = True, limit: int = 50) -> List[Dict[str, Any]]:
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
            "total_purple_plus_items": len(purple_holders),
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

        sem = asyncio.Semaphore(6)

        async def _analyze_battle(b: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            async with sem:
                b_id = b.get('_id')
                b_type = b.get('type')
                current_round = b.get('currentRound', {})
                if not isinstance(current_round, dict):
                    current_round = {}
                round_id = current_round.get('_id')
                round_num = current_round.get('number', 1)

                att_c_id = b.get('attacker', {}).get('country')
                def_c_id = b.get('defender', {}).get('country')
                reg_id = b.get('defender', {}).get('region')

                att_country = self._countries_cache.get(att_c_id, {})
                def_country = self._countries_cache.get(def_c_id, {})
                region = self._regions_cache.get(reg_id, {})

                round_task = self.fetch_ranking(round_id, is_round=True) if round_id else asyncio.sleep(0)
                battle_task = self.fetch_ranking(b_id, is_round=False)
                ranks_res = await asyncio.gather(round_task, battle_task, return_exceptions=True)
                round_ranks = ranks_res[0] if isinstance(ranks_res[0], list) else []
                battle_ranks = ranks_res[1] if isinstance(ranks_res[1], list) else []

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

                return {
                    'battleId': b_id,
                    'type': b_type,
                    'region': {
                        'id': reg_id,
                        'name': region.get('name', 'Unknown Region')
                    },
                    'attacker': {
                        'countryId': att_c_id,
                        'name': att_country.get('name', 'Attacker'),
                        'code': att_country.get('code', '??'),
                        'flag': att_country.get('flag', '🏳️'),
                        'roundPoints': att_round_pts,
                        'roundDamage': att_round_dmg,
                        'wonRounds': att_won_rounds
                    },
                    'defender': {
                        'countryId': def_c_id,
                        'name': def_country.get('name', 'Defender'),
                        'code': def_country.get('code', '??'),
                        'flag': def_country.get('flag', '🏳️'),
                        'roundPoints': def_round_pts,
                        'roundDamage': def_round_dmg,
                        'wonRounds': def_won_rounds
                    },
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
                    'wareraUrl': f'https://app.warera.io/battle/{b_id}'
                }

        results = await asyncio.gather(*[_analyze_battle(b) for b in raw_battles], return_exceptions=True)
        analyzed_battles = [r for r in results if isinstance(r, dict)]

        def sort_key(b):
            is_sniper = 0 if b.get('timing', {}).get('isSniperWindow') else (1 if b.get('timing', {}).get('minutesLeft', 999) < 40 else 2)
            has_purple = 0 if (b.get('roundCutoff', {}).get('has_purple') or b.get('battleCutoff', {}).get('has_purple')) else 1
            dmg = b.get('bestPurpleMinDamage') or 999999999999
            return (is_sniper, has_purple, dmg)

        analyzed_battles.sort(key=sort_key)

        self._cached_intel = analyzed_battles
        self._cached_intel_time = time.time()
        return analyzed_battles


_SHARED_ANALYZER: Optional['WarEraBattleAnalyzer'] = None

def get_shared_battle_analyzer() -> 'WarEraBattleAnalyzer':
    global _SHARED_ANALYZER
    if _SHARED_ANALYZER is None:
        _SHARED_ANALYZER = WarEraBattleAnalyzer()
    return _SHARED_ANALYZER
