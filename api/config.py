import os
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv

from equipment_data import get_items_for_qualities, DEFAULT_ACTIVE_QUALITIES, ALL_QUALITIES

# Load .env if present
load_dotenv()

BASE_DIR = Path(__file__).parent

# Application Versioning
APP_VERSION = "b.0001.58"

# Load API key from API_key.txt if present
def get_api_key() -> str:
    env_key = os.getenv("WARERA_API_KEY")
    if env_key:
        return env_key.strip()
    key_file = BASE_DIR / "API_key.txt"
    if key_file.exists():
        return key_file.read_text(encoding="utf-8").strip()
    return ""

API_KEY: str = get_api_key()
API_BASE_URL: str = os.getenv("WARERA_API_BASE_URL", "https://api2.warera.io/trpc")
SYNC_API_BASE_URL: str = os.getenv("WARERA_SYNC_API_BASE_URL", "https://api2.warera.io/trpc")

# Session authentication for Equipment & Weapon Market
DEFAULT_COOKIE = ''
WARERA_COOKIE: str = os.getenv("WARERA_COOKIE", DEFAULT_COOKIE)
WARERA_X_VID: str = os.getenv("WARERA_X_VID", "")
WARERA_X_GR: str = os.getenv("WARERA_X_GR", "")
WARERA_EQUIPMENT_API_URL: str = os.getenv("WARERA_EQUIPMENT_API_URL", "https://api6.warera.io/trpc")

# Equipment scanner settings
EQUIPMENT_SCAN_INTERVAL: int = int(os.getenv("EQUIPMENT_SCAN_INTERVAL", "1"))
EQUIPMENT_MIN_DISCOUNT: float = float(os.getenv("EQUIPMENT_MIN_DISCOUNT", "5.0"))
EQUIPMENT_GOD_ROLL_THRESHOLD: float = float(os.getenv("EQUIPMENT_GOD_ROLL_THRESHOLD", "80.0"))

# Web Dashboard settings (Ingress / Local UI)
WEB_DASHBOARD_HOST: str = os.getenv("WEB_DASHBOARD_HOST", "0.0.0.0")
WEB_DASHBOARD_PORT: int = int(os.getenv("WEB_DASHBOARD_PORT", "8080"))
ENABLE_WEB_DASHBOARD: bool = os.getenv("ENABLE_WEB_DASHBOARD", "true").lower() in ("true", "1", "yes")

# Pricing calculation mode: "live" (open orders) or "history" (3-day transaction history database)
PRICING_MODE: str = os.getenv("PRICING_MODE", "live").lower()

# Active equipment qualities / rarities to monitor
DEFAULT_EQUIPMENT_QUALITIES: List[str] = DEFAULT_ACTIVE_QUALITIES

def get_configured_qualities() -> List[str]:
    raw = os.getenv("EQUIPMENT_QUALITIES", "mythic,legendary,epic,rare")
    res = [q.strip().lower() for q in raw.split(",") if q.strip()]
    return res or DEFAULT_EQUIPMENT_QUALITIES

EQUIPMENT_QUALITIES: List[str] = get_configured_qualities()

def get_configured_equipment() -> List[str]:
    raw = os.getenv("EQUIPMENT_TO_MONITOR", "")
    if raw.strip():
        return [item.strip() for item in raw.split(",") if item.strip()]
    return get_items_for_qualities(EQUIPMENT_QUALITIES)

EQUIPMENT_TO_MONITOR: List[str] = get_configured_equipment()

# Notifications
def get_telegram_chat_ids() -> List[str]:
    raw = os.getenv("TELEGRAM_CHAT_ID", "")
    parts = raw.split(",")
    seen = set()
    result = []
    for p in parts:
        clean = p.strip()
        if clean and clean not in seen:
            seen.add(clean)
            result.append(clean)
    return result

ENABLE_TELEGRAM_ALERTS: bool = os.getenv("ENABLE_TELEGRAM_ALERTS", "true").lower() in ("true", "1", "yes")
TELEGRAM_BOT_TOKEN: Optional[str] = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_SNIPER_BOT_TOKEN: Optional[str] = os.getenv("TELEGRAM_SNIPER_BOT_TOKEN", os.getenv("SNIPER_BOT_TOKEN"))
TELEGRAM_CHAT_ID: Optional[str] = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_CHAT_IDS: List[str] = get_telegram_chat_ids()
DISCORD_WEBHOOK_URL: Optional[str] = os.getenv("DISCORD_WEBHOOK_URL")

# Battle Purple Sniper thresholds
SNIPER_MAX_DAMAGE: int = int(os.getenv("SNIPER_MAX_DAMAGE", "75000"))

SNIPER_BOT_PASSWORD: str = os.getenv("SNIPER_BOT_PASSWORD", "")
