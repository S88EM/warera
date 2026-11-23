"""
Market Cheapest Gear & Consumables Cache Manager.
Maintains a persistent JSON cache of the top-3 cheapest active offers
for all combat equipment (T3-T6: rare, epic, legendary, mythic)
and benchmark prices for combat consumables (fish, steak, pills).
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

from data_manager import get_data_file
from equipment_data import (
    EQUIPMENT_METADATA,
    QUALITY_TIERS,
    calculate_roll_quality,
)

logger = logging.getLogger("WarEraMarketCache")
CACHE_FILE_NAME = "market_cheapest_cache.json"

# Monitored tiers for combat calculator: T3 (rare), T4 (epic), T5 (legendary), T6 (mythic)
TARGET_QUALITIES = ["rare", "epic", "legendary", "mythic"]

# Key combat consumables in WarEra
CONSUMABLE_KEYS = ["cookedFish", "fish", "steak", "bread", "cocain", "scrap", "case1", "case2"]
DEFAULT_CONSUMABLE_PRICES = {
    "cookedFish": 7.74,
    "fish": 3.93,
    "steak": 3.03,
    "bread": 1.40,
    "cocain": 34.80,
    "scrap": 0.26,
    "case1": 3.89,
    "case2": 27.19,
}


def get_cache_path() -> Path:
    """Returns the persistent path for market_cheapest_cache.json."""
    return get_data_file(CACHE_FILE_NAME, seed_bundled=False)


def save_market_cheapest_cache(
    offers_by_item: Dict[str, List[Dict[str, Any]]],
    consumable_prices: Optional[Dict[str, float]] = None,
    limit_per_item: int = 3,
) -> Path:
    """
    Extracts top-N cheapest active offers for all T3-T6 equipment slots
    and writes atomic JSON snapshot to persistent storage.
    """
    cache_path = get_cache_path()
    now_iso = datetime.now(timezone.utc).isoformat()

    # Load existing cache if available so we don't wipe items not scanned in this cycle
    existing = load_market_cheapest_cache()
    items_cache: Dict[str, Any] = existing.get("items", {})

    # Process all items in target qualities (T3..T6)
    for q_key in TARGET_QUALITIES:
        tier_info = QUALITY_TIERS.get(q_key, {})
        tier_num = tier_info.get("tier", 4)
        tier_items = tier_info.get("items", [])

        for item_code in tier_items:
            meta = EQUIPMENT_METADATA.get(item_code, {})
            slot = meta.get("type", "unknown")
            item_name = meta.get("name", item_code)

            raw_offers = offers_by_item.get(item_code)
            if raw_offers is None:
                # Keep existing cached offers if available
                continue

            valid_offers = []
            for o in raw_offers:
                if not isinstance(o, dict):
                    continue
                price = o.get("price") or o.get("money")
                if price is None:
                    continue
                try:
                    price_val = float(price)
                except (ValueError, TypeError):
                    continue
                if price_val <= 0:
                    continue

                item_obj = o.get("item", {}) if isinstance(o.get("item"), dict) else o
                skills = item_obj.get("skills", {})
                state = item_obj.get("state", 100)

                seller = o.get("seller") or o.get("user")
                seller_name = ""
                if isinstance(seller, dict):
                    seller_name = seller.get("name") or seller.get("username") or seller.get("_id", "")
                elif isinstance(seller, str):
                    seller_name = seller

                roll_q = calculate_roll_quality(item_code, skills)
                offer_id = o.get("_id") or o.get("id")

                valid_offers.append({
                    "id": offer_id,
                    "price": round(price_val, 2),
                    "state": state,
                    "skills": skills,
                    "roll_quality": round(roll_q, 1),
                    "seller": seller_name,
                    "url": f"https://app.warera.io/market/equipments?item={item_code}",
                })

            valid_offers.sort(key=lambda x: x["price"])
            top_offers = valid_offers[:limit_per_item]

            items_cache[item_code] = {
                "item_code": item_code,
                "name": item_name,
                "slot": slot,
                "tier": tier_num,
                "quality": q_key,
                "cheapest_price": top_offers[0]["price"] if top_offers else None,
                "offers": top_offers,
                "offers_count": len(valid_offers),
                "url": f"https://app.warera.io/market/equipments?item={item_code}",
            }

    # Process consumables
    consumables_cache = existing.get("consumables", dict(DEFAULT_CONSUMABLE_PRICES))
    if consumable_prices and isinstance(consumable_prices, dict):
        for c_key in CONSUMABLE_KEYS:
            if c_key in consumable_prices:
                try:
                    p = float(consumable_prices[c_key])
                    if p > 0:
                        consumables_cache[c_key] = round(p, 2)
                except (ValueError, TypeError):
                    pass

    payload = {
        "updated_at": now_iso,
        "items": items_cache,
        "consumables": consumables_cache,
    }

    # Atomic write via temp file
    temp_path = cache_path.with_suffix(".tmp")
    try:
        temp_path.parent.mkdir(parents=True, exist_ok=True)
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        temp_path.replace(cache_path)
    except Exception as e:
        logger.error(f"Error saving market cheapest cache: {e}")
        if temp_path.exists():
            temp_path.unlink()

    return cache_path


def load_market_cheapest_cache() -> Dict[str, Any]:
    """Safely loads and returns the current market cache from JSON."""
    cache_path = get_cache_path()
    if not cache_path.exists():
        return {
            "updated_at": None,
            "items": {},
            "consumables": dict(DEFAULT_CONSUMABLE_PRICES),
        }
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to read market cheapest cache: {e}")
        return {
            "updated_at": None,
            "items": {},
            "consumables": dict(DEFAULT_CONSUMABLE_PRICES),
        }


def get_gear_recommendation(
    tier: int = 4,
    slot_overrides: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Returns the recommended set of gear for a specified tier (T3, T4, T5, T6).
    Maps slots: weapon, helmet, chest, pants, boots, gloves.
    """
    cache = load_market_cheapest_cache()
    items_data = cache.get("items", {})

    quality_map = {3: "rare", 4: "epic", 5: "legendary", 6: "mythic"}
    q_key = quality_map.get(tier, "epic")
    tier_items = QUALITY_TIERS.get(q_key, {}).get("items", [])

    gear_slots = {}
    total_cost = 0.0

    for code in tier_items:
        meta = EQUIPMENT_METADATA.get(code, {})
        slot = meta.get("type", "unknown")

        cached_item = items_data.get(code, {})
        offers = cached_item.get("offers", [])
        cheapest_offer = offers[0] if offers else None
        price = cheapest_offer.get("price") if cheapest_offer else cached_item.get("cheapest_price")

        gear_slots[slot] = {
            "item_code": code,
            "name": meta.get("name", code),
            "tier": tier,
            "quality": q_key,
            "slot": slot,
            "price": price,
            "skills": cheapest_offer.get("skills", {}) if cheapest_offer else {},
            "roll_quality": cheapest_offer.get("roll_quality", 0) if cheapest_offer else 0,
            "seller": cheapest_offer.get("seller", "") if cheapest_offer else "",
            "offers": offers,
            "url": f"https://app.warera.io/market/equipments?item={code}",
        }
        if price:
            total_cost += float(price)

    return {
        "tier": tier,
        "quality": q_key,
        "total_gear_cost": round(total_cost, 2),
        "slots": gear_slots,
        "updated_at": cache.get("updated_at"),
    }
