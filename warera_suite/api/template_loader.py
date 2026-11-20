"""
Template Loader for WarEra Web Dashboards.
Loads HTML templates from api/templates directory with memory caching.
"""

from pathlib import Path
from functools import lru_cache

TEMPLATES_DIR = Path(__file__).parent / "templates"


@lru_cache(maxsize=16)
def get_template(name: str) -> str:
    """Reads and caches HTML template file."""
    path = TEMPLATES_DIR / name
    if path.exists():
        return path.read_text(encoding="utf-8")

    # Fallbacks for Home Assistant container
    for alt_path in [
        Path("/app/api/templates") / name,
        Path("/app/templates") / name,
        Path(__file__).parent.parent / "templates" / name,
    ]:
        if alt_path.exists():
            return alt_path.read_text(encoding="utf-8")

    return f"<!-- Template {name} not found -->"
