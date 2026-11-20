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
from data_manager import get_data_file

logger = logging.getLogger("WarEraSubscribersDB")

class SubscribersDB:
    def __init__(self, storage_path: Optional[str] = None):
        if storage_path:
            self.file_path = Path(storage_path)
        else:
            self.file_path = get_data_file("bot_subscribers.json")

        self._subscribers: Dict[str, Dict[str, Any]] = {}
        self._last_mtime: float = 0.0
        self.load()

    def _ensure_fresh(self):
        """Checks if bot_subscribers.json was modified on disk by another component/process and reloads it."""
        try:
            if self.file_path.exists():
                mtime = self.file_path.stat().st_mtime
                if mtime > getattr(self, "_last_mtime", 0.0):
                    self.load()
        except Exception as e:
            logger.debug(f"Error checking subscribers file freshness: {e}")

    def load(self):
        """Loads subscribers from persistent JSON storage and seeds initial chat IDs from config."""
        if self.file_path.exists():
            try:
                self._last_mtime = self.file_path.stat().st_mtime
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
            if self.file_path.exists():
                self._last_mtime = self.file_path.stat().st_mtime
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
            if "contract_alerts" not in user:
                user["contract_alerts"] = False
            if "min_bounty_rate" not in user:
                user["min_bounty_rate"] = 0.0
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
                "contract_alerts": False,
                "min_bounty_rate": 0.0,
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
        self._ensure_fresh()
        cid = str(chat_id).strip()
        user = self.get_user_prefs(cid)
        default_th = int(getattr(config, "SNIPER_MAX_DAMAGE", 75000))
        return int(user.get("damage_threshold") or default_th)

    def set_user_threshold(self, chat_id: str, threshold: int) -> int:
        """Sets the individual damage cutoff threshold for this specific user."""
        self._ensure_fresh()
        cid = str(chat_id).strip()
        if cid not in self._subscribers:
            self.register_user(cid)
        th = int(threshold)
        self._subscribers[cid]["damage_threshold"] = th
        self.save()
        return th

    def get_user_min_bounty_rate(self, chat_id: str) -> float:
        """Returns the individual minimum bounty rate per 1k damage for this user (default 0.0 = all)."""
        self._ensure_fresh()
        cid = str(chat_id).strip()
        user = self.get_user_prefs(cid)
        try:
            return float(user.get("min_bounty_rate", 0.0) or 0.0)
        except (ValueError, TypeError):
            return 0.0

    def set_user_min_bounty_rate(self, chat_id: str, rate: float) -> float:
        """Sets the individual minimum bounty rate per 1k damage for this specific user."""
        self._ensure_fresh()
        cid = str(chat_id).strip()
        if cid not in self._subscribers:
            self.register_user(cid)
        r = round(max(0.0, float(rate)), 4)
        self._subscribers[cid]["min_bounty_rate"] = r
        self.save()
        return r

    def is_authorized(self, chat_id: str) -> bool:
        """Checks if user is authorized. If no password set, all users are authorized."""
        self._ensure_fresh()
        required_pwd = str(getattr(config, "SNIPER_BOT_PASSWORD", "") or "").strip()
        if not required_pwd:
            return True
        cid = str(chat_id).strip()
        if self.is_admin(cid):
            return True
        user = self._subscribers.get(cid, {})
        return bool(user.get("authorized", False))

    def authorize_user(self, chat_id: str, password_attempt: str) -> bool:
        """Verifies password attempt and authorizes user if correct."""
        required_pwd = str(getattr(config, "SNIPER_BOT_PASSWORD", "") or "").strip()
        if not required_pwd:
            return True
        cid = str(chat_id).strip()
        if self.is_admin(cid):
            return True
        if str(password_attempt).strip() == required_pwd:
            if cid not in self._subscribers:
                self.register_user(cid)
            self._subscribers[cid]["authorized"] = True
            self.save()
            return True
        return False

    def revoke_user(self, chat_id: str) -> bool:
        """Revokes authorization for a user."""
        cid = str(chat_id).strip()
        if cid in self._subscribers:
            self._subscribers[cid]["authorized"] = False
            self.save()
            return True
        return False

    def set_sniper_alerts(self, chat_id: str, enabled: bool) -> bool:
        cid = str(chat_id).strip()
        if cid not in self._subscribers:
            self.register_user(cid)
        self._subscribers[cid]["sniper_alerts"] = enabled
        self.save()
        return enabled

    def set_contract_alerts(self, chat_id: str, enabled: bool) -> bool:
        cid = str(chat_id).strip()
        if cid not in self._subscribers:
            self.register_user(cid)
        self._subscribers[cid]["contract_alerts"] = enabled
        self.save()
        return enabled

    set_bounty_alerts = set_contract_alerts

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
        self._ensure_fresh()
        cid = str(chat_id).strip()
        if cid not in self._subscribers:
            return self.register_user(cid)
        return self._subscribers[cid]

    def get_sniper_chat_ids(self) -> List[str]:
        """Returns all chat IDs who have battle sniping alerts enabled AND are authorized."""
        self._ensure_fresh()
        res = []
        for cid, u in self._subscribers.items():
            if u.get("sniper_alerts", True) and self.is_authorized(cid):
                res.append(cid)
        return res

    def get_contract_chat_ids(self) -> List[str]:
        """Returns all chat IDs who have battle contract alerts enabled AND are authorized."""
        self._ensure_fresh()
        res = []
        for cid, u in self._subscribers.items():
            if u.get("contract_alerts", False) and self.is_authorized(cid):
                res.append(cid)
        return res

    get_bounty_chat_ids = get_contract_chat_ids

    def get_market_chat_ids(self) -> List[str]:
        """
        Returns ONLY the admin/owner chat IDs who have market gear alerts enabled.
        PRIVACY SHIELD: Regular users NEVER receive equipment alerts.
        """
        self._ensure_fresh()
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
        self._ensure_fresh()
        return self._subscribers

    def count(self) -> int:
        self._ensure_fresh()
        return len(self._subscribers)
