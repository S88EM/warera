import os
import sqlite3
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
import statistics

DEFAULT_DB_PATH = Path(__file__).parent / "market_history.db"
DB_PATH = Path(os.getenv("MARKET_DB_PATH", str(DEFAULT_DB_PATH)))

class MarketHistoryDB:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS item_transactions (
                    id TEXT PRIMARY KEY,
                    item_code TEXT NOT NULL,
                    price REAL NOT NULL,
                    primary_stat_name TEXT,
                    primary_stat_val REAL,
                    secondary_stat_name TEXT,
                    secondary_stat_val REAL,
                    state INTEGER DEFAULT 100,
                    created_at TIMESTAMP NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_code_date ON item_transactions (item_code, created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_code_stat ON item_transactions (item_code, primary_stat_val)")

    def save_transactions(self, transactions: List[Dict[str, Any]]) -> int:
        """Insert transactions, ignoring already existing ones."""
        inserted = 0
        rows = []
        for tx in transactions:
            tx_id = tx.get("_id")
            if not tx_id:
                continue
            item_code = tx.get("itemCode") or tx.get("item", {}).get("code")
            price = tx.get("money")
            created_at = tx.get("createdAt")
            if not item_code or price is None or not created_at:
                continue

            item_obj = tx.get("item", {})
            skills = item_obj.get("skills", {})
            state = item_obj.get("state", 100)

            # Extract primary and secondary stats
            primary_name, primary_val = None, None
            secondary_name, secondary_val = None, None

            # For weapons: attack (primary), criticalChance (secondary)
            if "attack" in skills:
                primary_name, primary_val = "attack", float(skills["attack"])
                if "criticalChance" in skills:
                    secondary_name, secondary_val = "criticalChance", float(skills["criticalChance"])
            elif "dodge" in skills:
                primary_name, primary_val = "dodge", float(skills["dodge"])
            elif "armor" in skills:
                primary_name, primary_val = "armor", float(skills["armor"])
            elif "precision" in skills:
                primary_name, primary_val = "precision", float(skills["precision"])
            elif "criticalDamages" in skills:
                primary_name, primary_val = "criticalDamages", float(skills["criticalDamages"])

            rows.append((
                tx_id,
                item_code,
                float(price),
                primary_name,
                primary_val,
                secondary_name,
                secondary_val,
                state,
                created_at,
            ))

        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.executemany("""
                INSERT OR IGNORE INTO item_transactions (
                    id, item_code, price, primary_stat_name, primary_stat_val,
                    secondary_stat_name, secondary_stat_val, state, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, rows)
            inserted = cursor.rowcount

        return inserted

    def cleanup_old_transactions(self, keep_days: int = 7) -> int:
        """Remove transactions older than keep_days to keep database lightweight."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=keep_days)).isoformat()
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM item_transactions WHERE created_at < ?", (cutoff,))
            deleted = cursor.rowcount
        return deleted

    def get_stat_price_summary(self, item_code: str, days: int = 3) -> Dict[float, Dict[str, Any]]:
        """
        Get median, min, max, count price for each primary stat value over the last N days.
        """
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT primary_stat_val, price
                FROM item_transactions
                WHERE item_code = ? AND created_at >= ? AND primary_stat_val IS NOT NULL
                ORDER BY primary_stat_val ASC
            """, (item_code, cutoff)).fetchall()

        by_stat = {}
        for r in rows:
            stat_val = r["primary_stat_val"]
            by_stat.setdefault(stat_val, []).append(r["price"])

        summary = {}
        for stat_val, prices in by_stat.items():
            summary[stat_val] = {
                "count": len(prices),
                "median": round(statistics.median(prices), 2),
                "mean": round(statistics.mean(prices), 2),
                "min": round(min(prices), 2),
                "max": round(max(prices), 2),
            }

        return summary

    def get_estimated_price_for_item(self, item_code: str, skills: Dict[str, Any], days: int = 3) -> Optional[float]:
        """
        Estimate the expected market price for an item with specific skills based on 3-day history.
        Uses exact stat pair for weapons if sufficient data exists, or exact/interpolated primary stat median.
        """
        eval_res = self.get_stat_evaluation(item_code, skills, current_price=0.0, days=days)
        if eval_res:
            return eval_res["expected_price"]
        return None

    def get_stat_evaluation(self, item_code: str, skills: Dict[str, Any], current_price: float, days: int = 3) -> Optional[Dict[str, Any]]:
        """
        Evaluate if current_price is cheap, fair, or expensive compared to 3-day history
        accounting for the item's specific dynamic stats.
        """
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        
        stat_name = None
        stat_val = None
        sec_name = None
        sec_val = None

        if "attack" in skills:
            stat_name = "attack"
            stat_val = float(skills["attack"])
            if "criticalChance" in skills:
                sec_name = "criticalChance"
                sec_val = float(skills["criticalChance"])
        elif "dodge" in skills:
            stat_name = "dodge"
            stat_val = float(skills["dodge"])
        elif "armor" in skills:
            stat_name = "armor"
            stat_val = float(skills["armor"])
        elif "precision" in skills:
            stat_name = "precision"
            stat_val = float(skills["precision"])
        elif "criticalDamages" in skills:
            stat_name = "criticalDamages"
            stat_val = float(skills["criticalDamages"])

        expected_price = None
        sample_count = 0
        stat_desc = ""

        # 1. For weapons with attack + criticalChance, check exact pair in DB
        if stat_name == "attack" and sec_name == "criticalChance" and sec_val is not None:
            with self._get_conn() as conn:
                pair_rows = conn.execute("""
                    SELECT price FROM item_transactions
                    WHERE item_code = ? AND created_at >= ?
                      AND primary_stat_val = ? AND secondary_stat_val = ?
                """, (item_code, cutoff, stat_val, sec_val)).fetchall()
            
            if len(pair_rows) >= 3:
                prices = [r["price"] for r in pair_rows]
                expected_price = round(statistics.median(prices), 2)
                sample_count = len(prices)
                stat_desc = f"Atk {int(stat_val)}, Crit {int(sec_val)}%"

        # 2. Single stat or fallback to primary stat summary
        if expected_price is None and stat_val is not None:
            summary = self.get_stat_price_summary(item_code, days=days)
            if stat_val in summary:
                expected_price = summary[stat_val]["median"]
                sample_count = summary[stat_val]["count"]
                stat_desc = f"{stat_name} {int(stat_val)}"
                if sec_val is not None:
                    stat_desc += f" (Crit {int(sec_val)}%)"
            elif summary:
                known_stats = sorted(summary.keys())
                if stat_val <= known_stats[0]:
                    expected_price = summary[known_stats[0]]["median"]
                elif stat_val >= known_stats[-1]:
                    expected_price = summary[known_stats[-1]]["median"]
                else:
                    lower_stat = max(s for s in known_stats if s < stat_val)
                    higher_stat = min(s for s in known_stats if s > stat_val)
                    lower_price = summary[lower_stat]["median"]
                    higher_price = summary[higher_stat]["median"]
                    ratio = (stat_val - lower_stat) / (higher_stat - lower_stat)
                    expected_price = round(lower_price + ratio * (higher_price - lower_price), 2)
                sample_count = sum(v["count"] for v in summary.values())
                stat_desc = f"{stat_name} ~{int(stat_val)}"
                if sec_val is not None:
                    stat_desc += f" (Crit {int(sec_val)}%)"

        if expected_price is None:
            return None

        diff = expected_price - current_price
        discount_pct = (diff / expected_price) * 100.0 if expected_price > 0 else 0.0

        if discount_pct >= 15.0:
            verdict = "🔥 ДУЖЕ ДЕШЕВО"
            is_cheap = True
        elif discount_pct >= 5.0:
            verdict = "💎 ДЕШЕВО"
            is_cheap = True
        elif discount_pct <= -15.0:
            verdict = "❌ ДУЖЕ ДОРОГО"
            is_cheap = False
        elif discount_pct <= -5.0:
            verdict = "📈 ДОРОГО"
            is_cheap = False
        else:
            verdict = "⚖️ НОРМА"
            is_cheap = False

        return {
            "item_code": item_code,
            "current_price": round(current_price, 2),
            "expected_price": round(expected_price, 2),
            "discount_pct": round(discount_pct, 1),
            "profit": round(diff, 2),
            "verdict": verdict,
            "is_cheap": is_cheap,
            "stat_name": stat_name,
            "stat_val": stat_val,
            "secondary_name": sec_name,
            "secondary_val": sec_val,
            "stat_desc": stat_desc,
            "sample_count": sample_count,
        }

