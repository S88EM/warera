"""
Home Assistant Add-on Supervisor & Master Launcher for WarEra Suite.
Reads /data/options.json from Home Assistant OS, exports configuration,
and orchestrates background scanners and the Ingress web dashboard.
"""

import asyncio
import json
import os
import shutil
import signal
import sys
import time
from pathlib import Path
from threading import Thread
from dotenv import load_dotenv

# Ensure UTF-8 output
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add app paths to sys.path
BASE_DIR = Path(__file__).parent.resolve()
APP_DIR = BASE_DIR.parent.resolve()

for p in [str(BASE_DIR), str(BASE_DIR / "api"), str(APP_DIR), str(APP_DIR / "api")]:
    if p not in sys.path:
        sys.path.insert(0, p)

# Pre-load local .env files if present (fallbacks)
for env_file in [BASE_DIR / ".env", BASE_DIR / "api" / ".env", Path("/data/.env")]:
    if env_file.exists():
        load_dotenv(env_file, override=False)


def load_ha_options() -> dict:
    """
    Reads Home Assistant configuration from /data/options.json with multi-layer persistence:
    1. /data/options.json (HA Supervisor native storage)
    2. /data/saved_config.json (launcher persistent backup in /data)
    3. Environment / .env fallbacks
    """
    opts = {}
    options_file = Path("/data/options.json")
    backup_file = Path("/data/saved_config.json")

    # 1. Load backup first if present
    if backup_file.exists():
        try:
            with open(backup_file, "r", encoding="utf-8") as f:
                saved = json.load(f)
                if isinstance(saved, dict):
                    opts.update(saved)
                    print(f"[HA Launcher] 💾 Завантажено збережені налаштування з {backup_file}")
        except Exception:
            pass

    # 2. Merge with HA options.json
    if options_file.exists():
        try:
            with open(options_file, "r", encoding="utf-8") as f:
                ha_opts = json.load(f)
                if isinstance(ha_opts, dict):
                    for k, v in ha_opts.items():
                        if v not in (None, ""):
                            opts[k] = v
                        elif k not in opts:
                            opts[k] = v
                    print(f"[HA Launcher] Зчитано конфігурацію з /data/options.json ({len(ha_opts)} параметрів)")
        except Exception as e:
            print(f"[HA Launcher] Помилка зчитування /data/options.json: {e}")

    # 3. Fallback to default credentials from environment if fields are empty
    fallbacks = {
        "telegram_bot_token": os.getenv("TELEGRAM_BOT_TOKEN", ""),
        "telegram_sniper_bot_token": os.getenv("TELEGRAM_SNIPER_BOT_TOKEN", ""),
        "sniper_bot_password": os.getenv("SNIPER_BOT_PASSWORD", ""),
        "telegram_chat_id": os.getenv("TELEGRAM_CHAT_ID", ""),
        "warera_api_key": os.getenv("WARERA_API_KEY", ""),
        "warera_cookie": os.getenv("WARERA_COOKIE", ""),
        "warera_x_vid": os.getenv("WARERA_X_VID", ""),
        "warera_x_gr": os.getenv("WARERA_X_GR", ""),
    }

    for k, v in fallbacks.items():
        if v and not opts.get(k):
            opts[k] = v

    # 4. Save to persistent backup file in /data
    if Path("/data").exists():
        try:
            with open(backup_file, "w", encoding="utf-8") as f:
                json.dump(opts, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    return opts


def apply_configuration(opts: dict):
    """Maps Home Assistant options into environment variables."""
    mapping = {
        "warera_api_key": "WARERA_API_KEY",
        "warera_cookie": "WARERA_COOKIE",
        "warera_x_vid": "WARERA_X_VID",
        "warera_x_gr": "WARERA_X_GR",
        "telegram_bot_token": "TELEGRAM_BOT_TOKEN",
        "telegram_sniper_bot_token": "TELEGRAM_SNIPER_BOT_TOKEN",
        "sniper_bot_password": "SNIPER_BOT_PASSWORD",
        "telegram_chat_id": "TELEGRAM_CHAT_ID",
        "equipment_scan_interval": "EQUIPMENT_SCAN_INTERVAL",
        "pricing_mode": "PRICING_MODE",
        "min_discount_pct": "EQUIPMENT_MIN_DISCOUNT",
        "god_roll_threshold": "EQUIPMENT_GOD_ROLL_THRESHOLD",
        "sniper_max_damage": "SNIPER_MAX_DAMAGE",
    }

    for opt_key, env_key in mapping.items():
        if opt_key in opts and opts[opt_key] not in (None, ""):
            val = str(opts[opt_key]).strip()
            if val:
                os.environ[env_key] = val

    # Telegram alerts toggle
    enable_tg = opts.get("enable_telegram_alerts", True)
    os.environ["ENABLE_TELEGRAM_ALERTS"] = "true" if enable_tg else "false"

    # Equipment qualities toggles
    qualities = []
    if opts.get("monitor_mythic", True):
        qualities.append("mythic")
    if opts.get("monitor_legendary", True):
        qualities.append("legendary")
    if opts.get("monitor_epic", True):
        qualities.append("epic")
    if opts.get("monitor_rare", True):
        qualities.append("rare")
    if opts.get("monitor_uncommon", False):
        qualities.append("uncommon")
    if opts.get("monitor_common", False):
        qualities.append("common")
    if not qualities:
        qualities = ["mythic", "legendary", "epic", "rare"]

    os.environ["EQUIPMENT_QUALITIES"] = ",".join(qualities)
    try:
        from equipment_data import get_items_for_qualities
        items = get_items_for_qualities(qualities)
        os.environ["EQUIPMENT_TO_MONITOR"] = ",".join(items)
    except Exception:
        pass

    # Persistent database handling in /data
    data_dir = Path("/data")
    if data_dir.exists():
        target_db = data_dir / "market_history.db"
        bundled_db = BASE_DIR / "api" / "market_history.db"
        if not target_db.exists() and bundled_db.exists():
            try:
                shutil.copy2(bundled_db, target_db)
                print("[HA Launcher] 💾 Базу даних market_history.db успішно ініціалізовано в /data")
            except Exception as e:
                print(f"[HA Launcher] ⚠️ Не вдалося скопіювати базу в /data: {e}")

        if target_db.exists():
            os.environ["MARKET_DB_PATH"] = str(target_db)

    os.environ["WEB_DASHBOARD_HOST"] = "0.0.0.0"
    os.environ["WEB_DASHBOARD_PORT"] = "8080"


async def main():
    print("=" * 65)
    print("🚀 Запуск Home Assistant Add-on: WarEra Suite v1.3.2")
    print("=" * 65)

    opts = load_ha_options()
    apply_configuration(opts)

    enable_web = opts.get("enable_web_dashboard", True)
    enable_equip = opts.get("enable_equipment_scanner", True)
    enable_sniper = opts.get("enable_battle_sniper", True)
    enable_tg = opts.get("enable_telegram_alerts", True)
    pricing_mode = os.environ.get("PRICING_MODE", "live")
    equip_interval = os.environ.get("EQUIPMENT_SCAN_INTERVAL", "1")
    qualities_str = os.environ.get("EQUIPMENT_QUALITIES", "mythic,legendary,epic,rare")

    print(f"[HA Launcher] 🌐 Web Dashboard (Ingress): {'Увімкнено' if enable_web else 'Вимкнено'}")
    print(f"[HA Launcher] ⚔️ Сканер спорядження (Equipment Scanner): {'Увімкнено' if enable_equip else 'Вимкнено'} (режим {pricing_mode}, інтервал {equip_interval}с)")
    print(f"[HA Launcher] 💎 Активні якості: {qualities_str}")
    sniper_token = os.environ.get("TELEGRAM_SNIPER_BOT_TOKEN", "")
    max_dmg = os.environ.get("SNIPER_MAX_DAMAGE", "75000")
    print(f"[HA Launcher] 📱 Telegram сповіщення ринку: {'Увімкнено' if enable_tg else 'Вимкнено'}")
    print(f"[HA Launcher] 🎯 Sniper Telegram Bot (для клану): {'Увімкнено' if sniper_token else 'Очікує на токен'}")
    print(f"[HA Launcher] 🎯 Поріг снайпінгу фіолу: ≤ {max_dmg} dmg (відсіювання вище)")
    bot_pwd = os.environ.get("SNIPER_BOT_PASSWORD", "")
    print(f"[HA Launcher] 🔒 Захист снайпер-бота паролем: {'Увімкнено (пароль встановлено)' if bot_pwd else 'Вимкнено (вільний доступ)'}")
    print("-" * 65)

    import equipment_scanner
    import equipment_dashboard
    app = equipment_scanner.EquipmentScannerApp()

    # 1. Start Ingress Web Dashboard connected to live scanner
    if enable_web:
        try:
            loop = asyncio.get_running_loop()
            equipment_dashboard.start_dashboard(
                host="0.0.0.0",
                port=8080,
                app_instance=app,
                loop=loop,
            )
            print("[HA Launcher] ✅ Ingress Web Dashboard запущено на порті 8080")
        except Exception as e:
            print(f"[HA Launcher] ❌ Помилка старту Web Dashboard: {e}")

    tasks = []

    # 2. Start Equipment Scanner or standalone Battle Sniper
    if enable_equip:
        try:
            tasks.append(asyncio.create_task(app.start(start_web=False)))
            print("[HA Launcher] ✅ Сканер вигідних цін спорядження активовано")
        except Exception as e:
            print(f"[HA Launcher] ⚠️ Модуль equipment_scanner недоступний або має помилку: {e}")
    else:
        print("[HA Launcher] ℹ️ Сканер спорядження на ринку вимкнено.")
        # Start Battle Sniper and Bot autonomously even when market scanner is off!
        if enable_sniper:
            try:
                from battle_sniper_worker import get_sniper_worker
                tasks.append(asyncio.create_task(get_sniper_worker().start()))
                print("[HA Launcher] ✅ Автономний фоновий снайпер битв активовано")
            except Exception as e:
                print(f"[HA Launcher] ⚠️ Не вдалося запустити снайпер битв: {e}")

            if sniper_token:
                try:
                    from sniper_bot import SniperBotController
                    sniper_bot = SniperBotController(token=sniper_token)
                    tasks.append(asyncio.create_task(sniper_bot.start_polling()))
                    print("[HA Launcher] ✅ Снайпер Telegram-бот активовано")
                except Exception as e:
                    print(f"[HA Launcher] ⚠️ Не вдалося запустити Sniper Bot: {e}")

    if not tasks:
        print("[HA Launcher] ⚠️ Сканер спорядження вимкнено. Очікування запитів до Web UI...")
        while True:
            await asyncio.sleep(3600)

    # Run tasks until interrupted
    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        print("[HA Launcher] Отримано сигнал зупинки.")


if __name__ == "__main__":
    asyncio.run(main())
