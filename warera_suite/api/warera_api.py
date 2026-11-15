import json
from typing import Dict, Any, List, Optional
import httpx
import config

class WarEraAPI:
    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        self.base_url = (base_url or getattr(config, "API_BASE_URL", "https://api6.warera.io/trpc")).rstrip("/")
        self.api_key = api_key if api_key is not None else getattr(config, "API_KEY", "")
        
        headers = {
            "Accept": "application/json",
            "User-Agent": "WarEraMarketBot/1.0",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            headers["x-api-key"] = self.api_key
            
        self._client: Optional[httpx.AsyncClient] = None
        self._equip_client: Optional[httpx.AsyncClient] = None
        self._headers = headers

    async def get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                headers=self._headers,
                timeout=15.0,
                follow_redirects=True
            )
        return self._client

    async def get_equip_client(self) -> httpx.AsyncClient:
        if self._equip_client is None or self._equip_client.is_closed:
            session_headers = {
                "accept": "*/*",
                "content-type": "application/json",
                "cookie": config.WARERA_COOKIE,
                "origin": "https://app.warera.io",
                "referer": "https://app.warera.io/",
                "user-agent": "Mozilla/5.0 (Linux; Android 16; Pixel 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Mobile Safari/537.36",
                "x-vid": config.WARERA_X_VID,
                "x-gr": config.WARERA_X_GR,
            }
            self._equip_client = httpx.AsyncClient(
                headers=session_headers,
                timeout=12.0,
                follow_redirects=True,
                limits=httpx.Limits(max_keepalive_connections=30, max_connections=50),
            )
        return self._equip_client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
        if self._equip_client and not self._equip_client.is_closed:
            await self._equip_client.aclose()

    async def get_prices(self) -> Dict[str, float]:
        """Fetch current benchmark market prices for all tradeable items."""
        client = await self.get_client()
        url = f"{self.base_url}/itemTrading.getPrices"
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()
        return data.get("result", {}).get("data", {})

    async def get_top_orders(self, item_code: str, limit: int = 15) -> Dict[str, List[Dict[str, Any]]]:
        """Fetch top buy and sell orders for a specific item code."""
        client = await self.get_client()
        url = f"{self.base_url}/tradingOrder.getTopOrders"
        param_json = json.dumps({"itemCode": item_code, "limit": limit})
        resp = await client.get(url, params={"input": param_json})
        resp.raise_for_status()
        data = resp.json()
        result_data = data.get("result", {}).get("data", {})
        return {
            "buyOrders": result_data.get("buyOrders", []),
            "sellOrders": result_data.get("sellOrders", []),
        }

    async def get_equipment_offers(self, item_code: str, limit: int = 12, pages: int = 1) -> List[Dict[str, Any]]:
        """Fetch active market offers for a specific equipment or weapon."""
        url = f"{config.WARERA_EQUIPMENT_API_URL}/itemOffer.getItemOffers"
        client = await self.get_equip_client()
        
        all_offers: List[Dict[str, Any]] = []
        cursor = None

        for _ in range(max(1, pages)):
            payload: Dict[str, Any] = {
                "itemCode": item_code,
                "limit": limit,
                "direction": "forward"
            }
            if cursor:
                payload["cursor"] = cursor

            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json().get("result", {}).get("data", {})
            items = data.get("items", [])
            all_offers.extend(items)

            cursor = data.get("nextCursor")
            if not cursor or len(items) < limit:
                break

        return all_offers
