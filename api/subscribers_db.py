"""
WarEra Telegram Multi-User Subscribers Database
Manages individual subscriber preferences for push notifications (Market deals and Battle Sniping).
Allows up to hundreds of users to independently receive 1-on-1 private alerts without shared groups.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

import config

logger = logging.getLogger("WarEraSubscribersDB")

class SubscribersDB:
    def __init__(self, storage_path: Optional[str] = None):
        if storage_path:
            self.file_path = Path(storage_path)
        else:
            # Check Home Assistant /data first, fallback to api/bot_subscribers.json
            ha_data = Path("/data")
            if ha_data.exists():
                self.file_path = ha_data / "bot_subscribers.json"
            else:
                self.file_path = Path(__file__).parent / "bot_subscribers.json"

        self._subscribers: Dict[str, Dict[str, Any]] = {}
        self.load()

    def load(self):
        """Loads subscribers from persistent JSON storage and seeds initial chat IDs from config."""
        if self.file_path.exists():
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self._subscribers = data
            except Exception as e:
                logger.warning(f"Error loading subscribers from {self.file_path}: {e}")

        # Seed initial chat IDs from config if any
        seeded = False
        for cid in config.TELEGRAM_CHAT_IDS:
            s_cid = str(cid).strip()
            if s_cid and s_cid not in self._subscribers:
                self._subscribers[s_cid] = {
                    "chat_id": s_cid,
                    "username": "admin",
                    "first_name": "Admin",
                    "sniper_alerts": True,
                    "market_alerts": True,
                    "joined_at": datetime.now(timezone.utc).isoformat()
                }
                seeded = True

        if seeded or not self.file_path.exists():
            self.save()

    def save(self):
        """Persists subscribers dictionary to disk."""
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self._subscribers, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving subscribers to {self.file_path}: {e}")

    def is_admin(self, chat_id: str) -> bool:
        """Checks if chat_id belongs to the owner/admin defined in config."""
        cid = str(chat_id).strip()
        admin_cids = {str(c).strip() for c in config.TELEGRAM_CHAT_IDS}
        if not admin_cids:
            return True
        return cid in admin_cids

    def register_user(self, chat_id: str, username: Optional[str] = None, first_name: Optional[str] = None) -> Dict[str, Any]:
        """Registers a user or updates their profile when they send /start."""
        cid = str(chat_id).strip()
        now_str = datetime.now(timezone.utc).isoformat()
        admin = self.is_admin(cid)
        default_th = int(getattr(config, "SNIPER_MAX_DAMAGE", 75000))

        if cid in self._subscribers:
            user = self._subscribers[cid]
            if username:
                user["username"] = username
            if first_name:
                user["first_name"] = first_name
            if "damage_threshold" not in user:
                user["damage_threshold"] = default_th
            user["last_active"] = now_str
            # PRIVACY SHIELD: Non-admins can NEVER have market_alerts = True!
            if not admin:
                user["market_alerts"] = False
        else:
            user = {
                "chat_id": cid,
                "username": username or "Unknown",
                "first_name": first_name or "Fighter",
                "sniper_alerts": True,
                "market_alerts": True if admin else False,
                "damage_threshold": default_th,
                "joined_at": now_str,
                "last_active": now_str
            }
            self._subscribers[cid] = user

        self.save()
        return user

    def get_user_threshold(self, chat_id: str) -> int:
        """Returns the individual damage cutoff threshold for this user."""
        cid = str(chat_id).strip()
        user = self.get_user_prefs(cid)
        default_th = int(getattr(config, "SNIPER_MAX_DAMAGE", 75000))
        return int(user.get("damage_threshold") or default_th)

    def set_user_threshold(self, chat_id: str, threshold: int) -> int:
        """Sets the individual damage cutoff threshold for this specific user."""
        cid = str(chat_id).strip()
        if cid not in self._subscribers:
            self.register_user(cid)
        th = int(threshold)
        self._subscribers[cid]["damage_threshold"] = th
        self.save()
        return th

    def set_sniper_alerts(self, chat_id: str, enabled: bool) -> bool:
        cid = str(chat_id).strip()
        if cid not in self._subscribers:
            self.register_user(cid)
        self._subscribers[cid]["sniper_alerts"] = enabled
        self.save()
        return enabled

    def set_market_alerts(self, chat_id: str, enabled: bool) -> bool:
        cid = str(chat_id).strip()
        # PRIVACY SHIELD: Non-admins cannot enable market alerts under any circumstances!
        if not self.is_admin(cid):
            logger.warning(f"Unauthorized attempt by non-admin chat_id={cid} to enable market alerts!")
            return False
        if cid not in self._subscribers:
            self.register_user(cid)
        self._subscribers[cid]["market_alerts"] = enabled
        self.save()
        return enabled

    def get_user_prefs(self, chat_id: str) -> Dict[str, Any]:
        cid = str(chat_id).strip()
        if cid not in self._subscribers:
            return self.register_user(cid)
        return self._subscribers[cid]

    def get_sniper_chat_ids(self) -> List[str]:
        """Returns all chat IDs who have battle sniping alerts enabled."""
        res = []
        for cid, u in self._subscribers.items():
            if u.get("sniper_alerts", True):
                res.append(cid)
        return res

    def get_market_chat_ids(self) -> List[str]:
        """
        Returns ONLY the admin/owner chat IDs who have market gear alerts enabled.
        PRIVACY SHIELD: Regular users NEVER receive equipment alerts.
        """
        admin_cids = {str(cid).strip() for cid in config.TELEGRAM_CHAT_IDS}
        res = []
        for cid, u in self._subscribers.items():
            if admin_cids and cid not in admin_cids:
                continue
            if u.get("market_alerts", True):
                res.append(cid)

        # Fallback to configured admin chat IDs if none registered yet
        if not res and config.TELEGRAM_CHAT_IDS:
            return [str(cid).strip() for cid in config.TELEGRAM_CHAT_IDS]
        return res

    def get_all_subscribers(self) -> Dict[str, Dict[str, Any]]:
        return self._subscribers

    def count(self) -> int:
        return len(self._subscribers)
