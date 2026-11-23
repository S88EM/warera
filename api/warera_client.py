"""
Unified WarEra tRPC API Client.
Consolidates all network calls, HTTP/2 keep-alive connection pooling,
multi-node failover rotation, 429 rate limit backoff, and metadata caching.
Used across Clan Analyzer, Battle Analyzer, Equipment Scanner, and Telegram Bots.
"""

import asyncio
import json
import logging
import os
import sys
import time
from typing import Dict, Any, List, Optional, Tuple
import httpx

# Ensure UTF-8 output
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import config
from data_manager import get_data_file

logger = logging.getLogger("WarEraClient")

API_HOSTS = [
    "https://api2.warera.io/trpc",
    "https://api6.warera.io/trpc",
    "https://api3.warera.io/trpc",
    "https://api4.warera.io/trpc",
    "https://api5.warera.io/trpc",
]


class WarEraClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        custom_hosts: Optional[List[str]] = None,
    ):
        self.api_key = (api_key or config.get_api_key()).strip()
        self.base_url = (base_url or getattr(config, "API_BASE_URL", API_HOSTS[0])).rstrip("/")
        self.api_hosts = custom_hosts or list(API_HOSTS)
        if self.base_url not in self.api_hosts:
            self.api_hosts.insert(0, self.base_url)

        self._host_rate_limits: Dict[str, float] = {}
        self._current_host_idx = 0
        self._client: Optional[httpx.AsyncClient] = None
        self._equip_client: Optional[httpx.AsyncClient] = None
        self._semaphore = asyncio.Semaphore(4)

        # In-memory shared caches
        self._regions_cache: Dict[str, Dict[str, Any]] = {}
        self._countries_cache: Dict[str, Dict[str, Any]] = {}
        self._users_cache: Dict[str, str] = {}
        self._ranks_cache: Dict[str, Tuple[float, List[Dict[str, Any]]]] = {}
        self._cached_config: Optional[Dict[str, Any]] = None
        self._meta_loaded = False

    async def get_client(self) -> httpx.AsyncClient:
        """Returns standard pooled AsyncClient for tRPC queries."""
        if self._client is None or self._client.is_closed:
            headers = {
                "Accept": "application/json, text/plain, */*",
                "User-Agent": "WarEra-UnifiedClient/2.0",
            }
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            self._client = httpx.AsyncClient(
                headers=headers,
                timeout=15.0,
                follow_redirects=True,
                limits=httpx.Limits(max_keepalive_connections=30, max_connections=50),
            )
        return self._client

    async def get_equip_client(self) -> httpx.AsyncClient:
        """Returns session-authenticated AsyncClient for live equipment market offers."""
        if self._equip_client is None or self._equip_client.is_closed:
            session_headers = {
                "accept": "*/*",
                "content-type": "application/json",
                "cookie": getattr(config, "WARERA_COOKIE", ""),
                "origin": "https://app.warera.io",
                "referer": "https://app.warera.io/",
                "user-agent": "Mozilla/5.0 (Linux; Android 16; Pixel 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Mobile Safari/537.36",
                "x-vid": getattr(config, "WARERA_X_VID", ""),
                "x-gr": getattr(config, "WARERA_X_GR", ""),
            }
            self._equip_client = httpx.AsyncClient(
                headers=session_headers,
                timeout=12.0,
                follow_redirects=True,
                limits=httpx.Limits(max_keepalive_connections=30, max_connections=50),
            )
        return self._equip_client

    async def close(self):
        """Closes all underlying httpx clients."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
        if self._equip_client and not self._equip_client.is_closed:
            await self._equip_client.aclose()

    async def call_trpc(
        self,
        endpoint: str,
        payload: Optional[Dict[str, Any]] = None,
        key_override: Optional[str] = None,
        method: str = "GET",
    ) -> Any:
        """
        Executes a tRPC query with node rotation, automatic failover,
        and 429 rate limit backoff.
        """
        client = await self.get_client()
        input_param = "{}" if payload is None else json.dumps(payload, separators=(",", ":"))
        effective_key = key_override or self.api_key

        async with self._semaphore:
            # Pacing delay between requests to avoid burst rate limiting
            await asyncio.sleep(0.04)
            now = time.time()

            for _ in range(len(self.api_hosts)):
                host = self.api_hosts[self._current_host_idx]
                if now < self._host_rate_limits.get(host, 0.0):
                    # Host is currently in cooldown, rotate to next
                    self._current_host_idx = (self._current_host_idx + 1) % len(self.api_hosts)
                    continue

                url = f"{host}/{endpoint}"
                headers = {}
                if "api2.warera.io" in host and effective_key:
                    headers["x-api-key"] = effective_key
                    headers["Authorization"] = f"Bearer {effective_key}"
                elif effective_key:
                    headers["Authorization"] = f"Bearer {effective_key}"

                try:
                    if method.upper() == "GET":
                        r = await client.get(url, params={"input": input_param}, headers=headers)
                    else:
                        r = await client.post(url, json=payload or {}, headers=headers)

                    if r.status_code == 200:
                        data = r.json()
                        if "result" in data:
                            return data["result"].get("data")
                        return data

                    elif r.status_code == 429:
                        # Cooldown this specific host for 15s and rotate immediately
                        self._host_rate_limits[host] = time.time() + 15.0
                        self._current_host_idx = (self._current_host_idx + 1) % len(self.api_hosts)
                        logger.warning(f"Rate limit 429 on {host}/{endpoint}. Rotating node...")
                        continue

                    elif r.status_code in (401, 403):
                        # Token reject or forbidden on this node, rotate
                        self._current_host_idx = (self._current_host_idx + 1) % len(self.api_hosts)
                        continue

                    else:
                        self._current_host_idx = (self._current_host_idx + 1) % len(self.api_hosts)

                except Exception as e:
                    logger.debug(f"tRPC error on {url}: {e}")
                    self._current_host_idx = (self._current_host_idx + 1) % len(self.api_hosts)

        return None

    # =========================================================================
    # Metadata & Geographic Cache
    # =========================================================================

    async def load_metadata(self, force: bool = False):
        """Loads and caches country & region metadata from disk or API."""
        if self._regions_cache and self._countries_cache and not force:
            return

        reg_file = get_data_file("regions_cache.json")
        cnt_file = get_data_file("countries_cache.json")

        if reg_file.exists() and not self._regions_cache:
            try:
                self._regions_cache = json.loads(reg_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        if cnt_file.exists() and not self._countries_cache:
            try:
                self._countries_cache = json.loads(cnt_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        if not self._regions_cache or force:
            r_data = await self.call_trpc("region.getAllRegions")
            if isinstance(r_data, dict):
                self._regions_cache = r_data
                try:
                    reg_file.write_text(json.dumps(self._regions_cache, ensure_ascii=False), encoding="utf-8")
                except Exception:
                    pass

        if not self._countries_cache or force:
            c_data = await self.call_trpc("country.getAllCountries")
            if isinstance(c_data, list):
                self._countries_cache = {c["_id"]: c for c in c_data if isinstance(c, dict) and "_id" in c}
                try:
                    cnt_file.write_text(json.dumps(self._countries_cache, ensure_ascii=False), encoding="utf-8")
                except Exception:
                    pass

    async def get_regions(self) -> Dict[str, Dict[str, Any]]:
        if not self._regions_cache:
            await self.load_metadata()
        return self._regions_cache

    async def get_countries(self) -> Dict[str, Dict[str, Any]]:
        if not self._countries_cache:
            await self.load_metadata()
        return self._countries_cache

    async def get_user_name(self, user_id: str, fallback: str = "Unknown") -> str:
        """Resolves user nickname with in-memory caching."""
        if not user_id:
            return fallback
        if user_id in self._users_cache:
            return self._users_cache[user_id]

        res = await self.call_trpc("user.getUserById", {"userId": user_id})
        if res and isinstance(res, dict):
            name = res.get("user", {}).get("username") or res.get("username") or fallback
            self._users_cache[user_id] = name
            return name

        self._users_cache[user_id] = fallback
        return fallback

    async def get_game_config(self) -> Dict[str, Any]:
        """Fetches and caches game configuration."""
        if self._cached_config is None:
            cfg = await self.call_trpc("config.getConfig")
            self._cached_config = cfg or {}
        return self._cached_config

    # =========================================================================
    # Market & Equipment Methods
    # =========================================================================

    async def get_prices(self) -> Dict[str, float]:
        """Fetch benchmark market prices for all tradeable items."""
        data = await self.call_trpc("itemTrading.getPrices")
        return data if isinstance(data, dict) else {}

    async def get_top_orders(self, item_code: str, limit: int = 15) -> Dict[str, List[Dict[str, Any]]]:
        """Fetch top buy and sell orders for a specific item code."""
        data = await self.call_trpc("tradingOrder.getTopOrders", {"itemCode": item_code, "limit": limit})
        if isinstance(data, dict):
            return {
                "buyOrders": data.get("buyOrders", []),
                "sellOrders": data.get("sellOrders", []),
            }
        return {"buyOrders": [], "sellOrders": []}

    async def get_equipment_offers(
        self, item_code: str, limit: int = 12, pages: int = 1
    ) -> List[Dict[str, Any]]:
        """Fetch active market offers for equipment or weapons."""
        url = f"{getattr(config, 'WARERA_EQUIPMENT_API_URL', 'https://api6.warera.io/trpc')}/itemOffer.getItemOffers"
        client = await self.get_equip_client()

        all_offers: List[Dict[str, Any]] = []
        cursor = None

        for _ in range(max(1, pages)):
            payload: Dict[str, Any] = {
                "itemCode": item_code,
                "limit": limit,
                "direction": "forward",
            }
            if cursor:
                payload["cursor"] = cursor

            try:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json().get("result", {}).get("data", {})
                items = data.get("items", [])
                all_offers.extend(items)
                cursor = data.get("nextCursor")
                if not cursor or len(items) < limit:
                    break
            except Exception as e:
                logger.debug(f"Error fetching equipment offers for {item_code}: {e}")
                break

        return all_offers

    # =========================================================================
    # Battles & Contracts Methods
    # =========================================================================

    async def get_active_battles(self) -> List[Dict[str, Any]]:
        """Fetch all currently active battles."""
        data = await self.call_trpc("battle.getActiveBattles")
        return data if isinstance(data, list) else []

    async def get_battle_by_id(self, battle_id: str) -> Optional[Dict[str, Any]]:
        """Fetch battle details by battle ID."""
        data = await self.call_trpc("battle.getBattleById", {"battleId": battle_id})
        return data if isinstance(data, dict) else None

    async def get_battle_round_ranks(
        self, target_id: str, cache_ttl: float = 2.0
    ) -> List[Dict[str, Any]]:
        """Fetch round ranks / damage scoreboard for a battle round."""
        now = time.time()
        if target_id in self._ranks_cache:
            c_time, c_items = self._ranks_cache[target_id]
            if (now - c_time) < cache_ttl:
                return c_items

        data = await self.call_trpc("battle.getBattleRoundRanks", {"targetId": target_id})
        items = data if isinstance(data, list) else []
        self._ranks_cache[target_id] = (now, items)
        return items

    async def get_active_contracts(self) -> List[Dict[str, Any]]:
        """Fetch active military / mercenary contracts."""
        data = await self.call_trpc("contract.getActiveContracts")
        return data if isinstance(data, list) else []

    async def get_active_contract_auctions(self) -> List[Dict[str, Any]]:
        """Fetch active contract auctions."""
        data = await self.call_trpc("contract.getActiveContractAuctions")
        return data if isinstance(data, list) else []

    # =========================================================================
    # Military Unit (Clan) & User Methods
    # =========================================================================

    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        return await self.call_trpc("user.getUserById", {"userId": user_id})

    async def get_user_by_nick(self, nick: str) -> Optional[Dict[str, Any]]:
        return await self.call_trpc("user.getUserByNick", {"nick": nick})

    async def get_military_unit(self, mu_id: str) -> Optional[Dict[str, Any]]:
        return await self.call_trpc("militaryUnit.getMilitaryUnitById", {"militaryUnitId": mu_id})

    async def get_military_unit_members(self, mu_id: str) -> List[Dict[str, Any]]:
        data = await self.call_trpc("militaryUnit.getMilitaryUnitMembers", {"militaryUnitId": mu_id})
        return data if isinstance(data, list) else []

    async def get_user_equipped_items(self, user_id: str) -> List[Dict[str, Any]]:
        data = await self.call_trpc("inventory.getUserEquippedItems", {"userId": user_id})
        return data if isinstance(data, list) else []

    async def get_user_inventory_items(self, user_id: str) -> List[Dict[str, Any]]:
        data = await self.call_trpc("inventory.getUserInventoryItems", {"userId": user_id})
        return data if isinstance(data, list) else []

    async def get_user_skills(self, user_id: str) -> Dict[str, Any]:
        data = await self.call_trpc("user.getUserSkills", {"userId": user_id})
        return data if isinstance(data, dict) else {}

    async def get_user_work_details(self, user_id: str) -> Dict[str, Any]:
        data = await self.call_trpc("user.getUserWorkDetails", {"userId": user_id})
        return data if isinstance(data, dict) else {}

    async def get_user_buffs(self, user_id: str) -> Dict[str, Any]:
        data = await self.call_trpc("user.getUserBuffs", {"userId": user_id})
        return data if isinstance(data, dict) else {}


# Shared singleton instance
_shared_client: Optional[WarEraClient] = None


def get_warera_client(api_key: Optional[str] = None) -> WarEraClient:
    """Returns or creates the shared WarEraClient singleton."""
    global _shared_client
    if _shared_client is None or (api_key and _shared_client.api_key != api_key.strip()):
        _shared_client = WarEraClient(api_key=api_key)
    return _shared_client
