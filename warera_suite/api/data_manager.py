"""
Data Directory & Persistence Manager for WarEra Suite.
Resolves persistent storage paths for:
- SQLite databases: market_history.db, clan_history.db
- User subscriptions: bot_subscribers.json
- Cache files: regions_cache.json, countries_cache.json
"""

import os
import shutil
from pathlib import Path
from typing import Optional


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

    # Local project root fallback: <api_dir>/../data
    base_dir = Path(__file__).parent.parent.resolve()
    local_data = base_dir / "data"
    local_data.mkdir(parents=True, exist_ok=True)
    return local_data


def get_data_file(filename: str, seed_bundled: bool = True) -> Path:
    """
    Returns the absolute path to a file inside the persistent data directory.
    If the file does not exist in data_dir, and seed_bundled is True,
    it automatically copies the initial/bundled version from api/ if available.
    """
    data_dir = get_data_dir()
    target_path = data_dir / filename

    if not target_path.exists() and seed_bundled:
        api_dir = Path(__file__).parent.resolve()
        candidates = [
            api_dir / filename,
            api_dir.parent / "api" / filename,
            Path("/app/api") / filename,
        ]
        for candidate in candidates:
            if candidate.exists() and candidate.is_file():
                try:
                    shutil.copy2(candidate, target_path)
                    break
                except Exception:
                    pass

    return target_path
