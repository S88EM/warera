import asyncio
import json
import httpx
from datetime import datetime, timezone, timedelta
from rich.console import Console
from rich.table import Table

import config
from price_history_db import MarketHistoryDB
from equipment_data import EQUIPMENT_METADATA

console = Console()

async def sync_item_history(client: httpx.AsyncClient, db: MarketHistoryDB, item_code: str, days: int = 3, max_pages: int = 15):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    cursor = None
    total_saved = 0

    for _ in range(max_pages):
        payload = {
            "limit": 100,
            "transactionType": "itemMarket",
            "itemCode": item_code
        }
        if cursor:
            payload["cursor"] = cursor

        try:
            sync_base = getattr(config, "SYNC_API_BASE_URL", "https://api2.warera.io/trpc")
            url = f"{sync_base}/transaction.getPaginatedTransactions"
            resp = await client.get(url, params={"input": json.dumps(payload)})
            if resp.status_code != 200:
                break

            data = resp.json().get("result", {}).get("data", {})
            items = data.get("items", [])
            if not items:
                break

            saved = db.save_transactions(items)
            total_saved += saved

            # If we didn't insert any or fewer than page size, we hit transactions already in DB
            if saved < len(items):
                break

            # Check if oldest item is older than cutoff
            oldest_dt_str = items[-1].get("createdAt")
            if oldest_dt_str:
                oldest_dt = datetime.fromisoformat(oldest_dt_str.replace("Z", "+00:00"))
                if oldest_dt < cutoff:
                    break

            cursor = data.get("nextCursor")
            if not cursor:
                break

        except Exception as e:
            break

    return item_code, total_saved

async def sync_all_history(days: int = 3, items: list = None, quiet: bool = False) -> int:
    db = MarketHistoryDB()
    items_to_sync = items or config.EQUIPMENT_TO_MONITOR
    
    headers = {
        "x-api-key": config.API_KEY,
        "Accept": "application/json"
    }

    if not quiet:
        console.print(f"\n[bold cyan]Синхронізація історії транзакцій за {days} дні для {len(items_to_sync)} предметів...[/bold cyan]")
    
    total_new = 0
    async with httpx.AsyncClient(headers=headers, timeout=15.0) as client:
        tasks = [sync_item_history(client, db, code, days=days) for code in items_to_sync]
        results = await asyncio.gather(*tasks)

        for code, count in results:
            total_new += count
            if not quiet:
                meta = EQUIPMENT_METADATA.get(code, {})
                name = meta.get("name", code)
                console.print(f"  • [green]{name}[/green] (`{code}`): додано {count} транзакцій")

    # Cleanup records older than 7 days
    db.cleanup_old_transactions(keep_days=7)

    if not quiet:
        console.print(f"[bold green]Синхронізацію завершено! Додано {total_new} нових угод.[/bold green]\n")

    return total_new

if __name__ == "__main__":
    asyncio.run(sync_all_history(days=3))

