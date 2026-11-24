"""
Data Directory & Persistence Manager for WarEra Suite.
Resolves persistent storage paths for:
- SQLite databases: market_history.db, clan_history.db
- User subscriptions: bot_subscribers.json
- Cache files: regions_cache.json, countries_cache.json
- Calibrations & telemetry: pill_tracking_*.json
"""

import logging
import os
import shutil
from pathlib import Path
from typing import Optional, List

logger = logging.getLogger("WarEraDataManager")


def get_data_dir() -> Path:
    """
    Returns the persistent data directory:
    1. WARERA_DATA_DIR environment variable if specified.
    2. /data if running inside Home Assistant OS container.
    3. <project_root>/data for local standalone development.
    """
    env_dir = os.getenv("WARERA_DATA_DIR")
    if env_dir:
        p = Path(env_dir).resolve()
        p.mkdir(parents=True, exist_ok=True)
        return p

    ha_data = Path("/data")
    if ha_data.exists() and ha_data.is_dir():
        return ha_data

    # Local project root fallback: <project_root>/data
    current_file = Path(__file__).resolve()
    # Check parent dirs for a 'data' folder or workspace root
    candidates = [
        current_file.parent.parent / "data",            # api/ -> root/data
        current_file.parent.parent.parent / "data",     # warera_suite/api/ -> root/data
        current_file.parent / "data",                   # local data/
    ]
    for c in candidates:
        if c.exists() and c.is_dir():
            return c.resolve()

    # Default to root data
    root_data = current_file.parent.parent / "data"
    root_data.mkdir(parents=True, exist_ok=True)
    return root_data.resolve()


def get_seed_candidates(filename: str) -> List[Path]:
    """Returns possible locations where pre-packaged seed files might be located."""
    current_file = Path(__file__).resolve()
    return [
        current_file.parent.parent / "data" / filename,           # root/data/
        current_file.parent.parent.parent / "data" / filename,    # parent root data/
        Path("/app/data") / filename,                             # HA container data/
        Path("/app/warera_suite/data") / filename,
        current_file.parent / "data" / filename,
        # Legacy fallback locations
        current_file.parent / filename,
        Path("/app/api") / filename,
    ]


def get_data_file(filename: str, seed_bundled: bool = True) -> Path:
    """
    Returns the absolute path to a file inside the persistent data directory.
    If the file does not exist in data_dir, and seed_bundled is True,
    it automatically copies the initial/bundled version from seed locations if available.
    """
    data_dir = get_data_dir()
    target_path = data_dir / filename

    if not target_path.exists() and seed_bundled:
        for candidate in get_seed_candidates(filename):
            if candidate.exists() and candidate.is_file():
                try:
                    data_dir.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(candidate, target_path)
                    break
                except Exception as e:
                    logger.warning(f"Failed to seed {candidate} -> {target_path}: {e}")

    return target_path
