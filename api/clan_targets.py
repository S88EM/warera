"""
Clan Member Target Damage & Goal Persistence Manager.
Tracks daily damage targets set by clan members:
- Scoped by WarEra game date (rollover at 02:00:00 Europe/Kyiv).
- Stored persistently in data/clan_targets.json.
- Integrates with clan dashboard for progress bar tracking and gear planning.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

from data_manager import get_data_file
from clan_history_db import ClanHistoryDB

logger = logging.getLogger("WarEraClanTargets")
TARGETS_FILE_NAME = "clan_targets.json"


def get_targets_file_path() -> Path:
    return get_data_file(TARGETS_FILE_NAME, seed_bundled=False)


def load_all_targets_data() -> Dict[str, Any]:
    """Loads raw targets JSON file."""
    path = get_targets_file_path()
    if not path.exists():
        return {"dates": {}}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return {"dates": {}}
            if "dates" not in data:
                data = {"dates": {}}
            return data
    except Exception as e:
        logger.warning(f"Failed to read clan targets JSON: {e}")
        return {"dates": {}}


def save_all_targets_data(data: Dict[str, Any]) -> bool:
    """Atomic write for clan targets data."""
    path = get_targets_file_path()
    temp_path = path.with_suffix(".tmp")
    try:
        temp_path.parent.mkdir(parents=True, exist_ok=True)
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        temp_path.replace(path)
        return True
    except Exception as e:
        logger.error(f"Failed to save clan targets: {e}")
        if temp_path.exists():
            temp_path.unlink()
        return False


def get_daily_targets(game_date: Optional[str] = None) -> Dict[str, Any]:
    """
    Returns the target dictionary for the given game date (default: today since 02:00 Kyiv).
    Keys are lowercased usernames for easy matching.
    """
    target_date = game_date or ClanHistoryDB.get_game_date()
    all_data = load_all_targets_data()
    return all_data.get("dates", {}).get(target_date, {})


def set_member_target(
    username: str,
    target_damage: float,
    user_id: Optional[str] = None,
    gear_tier: str = "epic",
    use_pill: bool = True,
    use_fish: bool = True,
    game_date: Optional[str] = None,
    battle_bonus: Optional[float] = None,
    weapon: Optional[str] = None,
    ammo: Optional[str] = None,
    food: Optional[str] = None,
    prestige: Optional[int] = None,
    rank_bonus: Optional[float] = None,
    saved_strategy_key: Optional[str] = None,
    saved_strategy_label: Optional[str] = None,
    saved_build: Optional[Dict[str, Any]] = None,
    is_build_locked: bool = True,
) -> Dict[str, Any]:
    """
    Saves or updates a target goal and pinned combat build for a clan member for the active game date.
    """
    target_date = game_date or ClanHistoryDB.get_game_date()
    all_data = load_all_targets_data()
    dates_dict = all_data.setdefault("dates", {})
    day_targets = dates_dict.setdefault(target_date, {})

    clean_nick = (username or "").strip()
    if not clean_nick:
        raise ValueError("Username cannot be empty")

    now_iso = datetime.now(timezone.utc).isoformat()
    record = {
        "username": clean_nick,
        "user_id": user_id or "",
        "target_damage": max(0.0, float(target_damage)),
        "gear_tier": gear_tier.lower() if gear_tier else "epic",
        "use_pill": bool(use_pill),
        "use_fish": bool(use_fish),
        "game_date": target_date,
        "updated_at": now_iso,
        "battle_bonus": float(battle_bonus) if battle_bonus is not None else None,
        "weapon": weapon,
        "ammo": ammo,
        "food": food,
        "prestige": int(prestige) if prestige is not None else None,
        "rank_bonus": float(rank_bonus) if rank_bonus is not None else None,
        "saved_strategy_key": saved_strategy_key,
        "saved_strategy_label": saved_strategy_label,
        "saved_build": saved_build,
        "is_build_locked": bool(is_build_locked),
    }

    # Store with lowercased key for case-insensitive lookup
    day_targets[clean_nick.lower()] = record
    save_all_targets_data(all_data)
    return record


def clear_member_build(username: str, game_date: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Unlocks/clears the saved build for a member while retaining the damage target.
    """
    target_date = game_date or ClanHistoryDB.get_game_date()
    all_data = load_all_targets_data()
    day_targets = all_data.get("dates", {}).get(target_date, {})
    clean_nick = (username or "").strip().lower()
    if clean_nick in day_targets:
        rec = day_targets[clean_nick]
        rec["is_build_locked"] = False
        rec["saved_build"] = None
        rec["saved_strategy_key"] = None
        rec["saved_strategy_label"] = None
        rec["updated_at"] = datetime.now(timezone.utc).isoformat()
        save_all_targets_data(all_data)
        return rec
    return None
