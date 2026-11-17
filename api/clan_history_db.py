"""
WarEra Clan Combat Damage History & Daily Rollover Tracker
Handles:
- Game day rollover at 02:00:00 Europe/Kyiv (00:00 UTC)
- Persistent SQLite storage in Home Assistant persistent volume (/data/clan_history.db) or local dir
- Recording snapshots of userDamages and weeklyUserDamages
- Computing actual damage dealt today (since 02:00) and yesterday
"""

import os
import sqlite3
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

def get_clan_db_path() -> Path:
    """Return persistent DB path in Home Assistant (/data) or local directory."""
    ha_data = Path("/data")
    if ha_data.exists() and ha_data.is_dir():
        return ha_data / "clan_history.db"
    return Path(__file__).parent / "clan_history.db"

class ClanHistoryDB:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or get_clan_db_path()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS clan_damage_snapshots (
                    user_id TEXT NOT NULL,
                    username TEXT,
                    game_date TEXT NOT NULL,
                    base_total_damage INTEGER NOT NULL,
                    latest_total_damage INTEGER NOT NULL,
                    base_weekly_damage INTEGER NOT NULL,
                    latest_weekly_damage INTEGER NOT NULL,
                    first_seen_at TEXT NOT NULL,
                    last_updated_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, game_date)
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS clan_mu_snapshots (
                    mu_id TEXT NOT NULL,
                    game_date TEXT NOT NULL,
                    base_total_damage INTEGER NOT NULL,
                    latest_total_damage INTEGER NOT NULL,
                    base_weekly_damage INTEGER NOT NULL,
                    latest_weekly_damage INTEGER NOT NULL,
                    first_seen_at TEXT NOT NULL,
                    last_updated_at TEXT NOT NULL,
                    PRIMARY KEY (mu_id, game_date)
                );
            """)
            conn.commit()

    @staticmethod
    def get_game_date(dt: Optional[datetime] = None) -> str:
        """
        Game day starts at 02:00:00 Kyiv time (Europe/Kyiv).
        Before 02:00 belongs to previous game date.
        """
        if dt is None:
            try:
                import zoneinfo
                tz = zoneinfo.ZoneInfo("Europe/Kyiv")
                now_kyiv = datetime.now(tz)
            except Exception:
                # Fallback UTC+2
                now_kyiv = datetime.now(timezone.utc) + timedelta(hours=2)
        else:
            now_kyiv = dt

        if now_kyiv.hour < 2:
            game_dt = now_kyiv - timedelta(days=1)
        else:
            game_dt = now_kyiv

        return game_dt.strftime("%Y-%m-%d")

    @staticmethod
    def get_yesterday_game_date(game_date: str) -> str:
        d = datetime.strptime(game_date, "%Y-%m-%d")
        return (d - timedelta(days=1)).strftime("%Y-%m-%d")

    def record_members_snapshot(self, members: List[Dict[str, Any]], game_date: Optional[str] = None):
        """
        Record current damage readings for clan members.
        If first time seen today: sets base_total_damage and latest_total_damage.
        If already seen today: updates latest_total_damage and last_updated_at.
        """
        if not members:
            return

        target_date = game_date or self.get_game_date()
        now_iso = datetime.now(timezone.utc).isoformat()

        with self._get_conn() as conn:
            for m in members:
                uid = str(m.get("user_id") or m.get("_id") or "")
                if not uid:
                    continue
                uname = m.get("username", "")
                total_dmg = int(m.get("total_damage", 0))
                weekly_dmg = int(m.get("weekly_damage", 0))

                # Check if record exists for this game date
                cur = conn.execute(
                    "SELECT base_total_damage FROM clan_damage_snapshots WHERE user_id = ? AND game_date = ?",
                    (uid, target_date)
                )
                row = cur.fetchone()

                if row is None:
                    # First reading of this game day -> establish base
                    conn.execute("""
                        INSERT INTO clan_damage_snapshots
                        (user_id, username, game_date, base_total_damage, latest_total_damage,
                         base_weekly_damage, latest_weekly_damage, first_seen_at, last_updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (uid, uname, target_date, total_dmg, total_dmg, weekly_dmg, weekly_dmg, now_iso, now_iso))
                else:
                    # Subsequent reading -> update latest values
                    conn.execute("""
                        UPDATE clan_damage_snapshots
                        SET username = ?,
                            latest_total_damage = ?,
                            latest_weekly_damage = ?,
                            last_updated_at = ?
                        WHERE user_id = ? AND game_date = ?
                    """, (uname, total_dmg, weekly_dmg, now_iso, uid, target_date))

            conn.commit()

    def get_damage_stats(self, user_id: str, current_total_dmg: int, current_weekly_dmg: int, game_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Returns:
        - today_damage: actual damage dealt in current game day (since 02:00)
        - yesterday_damage: actual damage dealt in previous game day (or None if no history)
        - has_yesterday_data: bool
        """
        target_date = game_date or self.get_game_date()
        yesterday_date = self.get_yesterday_game_date(target_date)

        with self._get_conn() as conn:
            # Current day base
            cur_today = conn.execute(
                "SELECT base_total_damage, latest_total_damage FROM clan_damage_snapshots WHERE user_id = ? AND game_date = ?",
                (user_id, target_date)
            ).fetchone()

            # Yesterday base & latest
            cur_yest = conn.execute(
                "SELECT base_total_damage, latest_total_damage FROM clan_damage_snapshots WHERE user_id = ? AND game_date = ?",
                (user_id, yesterday_date)
            ).fetchone()

        today_dmg = 0
        if cur_today:
            base_today = cur_today["base_total_damage"]
            today_dmg = max(0, current_total_dmg - base_today)
        else:
            today_dmg = 0

        yesterday_dmg = None
        has_yesterday = False
        if cur_yest:
            yest_base = cur_yest["base_total_damage"]
            # If we have today's base, yesterday ended at today's base
            if cur_today:
                yesterday_end = cur_today["base_total_damage"]
            else:
                yesterday_end = cur_yest["latest_total_damage"]
            yesterday_dmg = max(0, yesterday_end - yest_base)
            has_yesterday = True

        return {
            "today_damage": today_dmg,
            "yesterday_damage": yesterday_dmg,
            "has_yesterday": has_yesterday,
            "game_date": target_date,
            "yesterday_game_date": yesterday_date
        }

    def get_all_members_stats(self, game_date: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """Batch fetch stats for all members for efficiency."""
        target_date = game_date or self.get_game_date()
        yesterday_date = self.get_yesterday_game_date(target_date)

        with self._get_conn() as conn:
            today_rows = {
                r["user_id"]: r for r in conn.execute(
                    "SELECT user_id, base_total_damage, latest_total_damage FROM clan_damage_snapshots WHERE game_date = ?",
                    (target_date,)
                )
            }
            yesterday_rows = {
                r["user_id"]: r for r in conn.execute(
                    "SELECT user_id, base_total_damage, latest_total_damage FROM clan_damage_snapshots WHERE game_date = ?",
                    (yesterday_date,)
                )
            }

        res = {}
        all_uids = set(today_rows.keys()) | set(yesterday_rows.keys())
        for uid in all_uids:
            t_row = today_rows.get(uid)
            y_row = yesterday_rows.get(uid)

            yest_dmg = None
            has_yest = False
            if y_row:
                yest_base = y_row["base_total_damage"]
                yest_end = t_row["base_total_damage"] if t_row else y_row["latest_total_damage"]
                yest_dmg = max(0, yest_end - yest_base)
                has_yest = True

            res[uid] = {
                "base_today": t_row["base_total_damage"] if t_row else None,
                "latest_today": t_row["latest_total_damage"] if t_row else None,
                "yesterday_damage": yest_dmg,
                "has_yesterday": has_yest
            }

        return res
