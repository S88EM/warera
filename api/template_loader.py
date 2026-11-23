"""
Template Loader for WarEra Web Dashboards.
Loads HTML templates from api/templates directory with memory caching.
Supports modular inclusions: <!-- INCLUDE: filename.js --> or <!-- INCLUDE: filename.html -->.
"""

import re
from pathlib import Path
from functools import lru_cache

TEMPLATES_DIR = Path(__file__).parent / "templates"


def _resolve_template_path(name: str) -> Path:
    candidates = [
        TEMPLATES_DIR / name,
        Path("/app/api/templates") / name,
        Path("/app/templates") / name,
        Path(__file__).parent.parent / "templates" / name,
    ]
    for c in candidates:
        if c.exists():
            return c
    return TEMPLATES_DIR / name


@lru_cache(maxsize=32)
def get_template(name: str) -> str:
    """Reads, caches, and processes HTML template file with inclusion support."""
    path = _resolve_template_path(name)
    if not path.exists():
        return f"<!-- Template {name} not found -->"

    raw = path.read_text(encoding="utf-8")

    def _replace_include(match):
        inc_name = match.group(1).strip()
        inc_path = _resolve_template_path(inc_name)
        if inc_path.exists():
            content = inc_path.read_text(encoding="utf-8")
            if inc_name.endswith(".js"):
                return f"<script>\n{content}\n</script>"
            elif inc_name.endswith(".css"):
                return f"<style>\n{content}\n</style>"
            return content
        return f"<!-- Include {inc_name} not found -->"

    # Support <!-- INCLUDE: filename -->
    processed = re.sub(r"<!--\s*INCLUDE:\s*([a-zA-Z0-9_\-\.]+)\s*-->", _replace_include, raw)
    return processed
