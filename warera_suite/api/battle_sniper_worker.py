"""
WarEra Battle Sniper Background Worker
Continuously monitors active battles for the 15-20 min Sniper Window (when round drop data is accurate and settled).
Sends push notifications to all subscribed users via Telegram Bot without colliding with market gear monitoring.
"""

import asyncio
import logging
import time
from typing import Optional, Set, Dict, Any, List
import httpx

import config
from battle_analyzer import get_shared_battle_analyzer, WarEraBattleAnalyzer
from subscribers_db import SubscribersDB

logger = logging.getLogger("WarEraBattleSniperWorker")

class BattleSniperWorker:
    def __init__(self, check_interval: int = 50):
        self.check_interval = check_interval
        self.is_running = False
        self.is_paused = False
        self.subscribers_db = SubscribersDB()
        self.analyzer = get_shared_battle_analyzer()
        self.max_damage = getattr(config, "SNIPER_MAX_DAMAGE", 75000)
        
        # Track alerted rounds per user so:
        # 1. A user is alerted only once per battle round.
        # 2. If an alert was skipped because damage exceeded personal threshold, and the user
        #    subsequently raises their threshold, they can still receive it while in the sniper window.
        self.alerted_user_rounds: Set[str] = set()
        self.cycle_count = 0
        self.total_alerts_sent = 0
        self.last_check_time: Optional[str] = None
        self._http_client: Optional[httpx.AsyncClient] = None

    async def get_client(self) -> httpx.AsyncClient:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=15.0)
        return self._http_client

    async def close(self):
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
        await self.analyzer.close()

    def format_dmg(self, val: Optional[int]) -> str:
        if val is None:
            return "—"
        return f"{val:,}".replace(",", " ")

    async def send_telegram_alert(self, chat_id: str, text: str, battle_url: str):
        token = config.TELEGRAM_SNIPER_BOT_TOKEN or config.TELEGRAM_BOT_TOKEN
        if not token:
            return
        client = await self.get_client()
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
            "reply_markup": {
                "inline_keyboard": [
                    [{"text": "⚔️ Відкрити битву на WarEra ↗", "url": battle_url}]
                ]
            }
        }
        try:
            r = await client.post(url, json=payload)
            if r.status_code == 200:
                self.total_alerts_sent += 1
            else:
                logger.error(f"Failed to send sniper alert to {chat_id}: {r.text}")
        except Exception as e:
            logger.error(f"Error sending sniper alert to {chat_id}: {e}")

    def build_alert_message(self, battle: Dict[str, Any]) -> str:
        reg = battle.get("region", {}).get("name", "Невідомий регіон")
        btype = "Війна" if battle.get("type") == "war" else "Повстання"
        r_num = battle.get("round", {}).get("number", 1)
        att = battle.get("attacker", {}).get("name", "Атакуючі")
        dff = battle.get("defender", {}).get("name", "Захисники")
        att_pts = battle.get("attacker", {}).get("roundPoints", 0)
        def_pts = battle.get("defender", {}).get("roundPoints", 0)
        
        tm = battle.get("timing", {})
        eta = tm.get("formattedEta", "15–20 хв")
        clean_eta = eta.replace("🎯", "").replace("до кінця", "").strip()
        mins = tm.get("minutesLeft", 18)
        
        rc = battle.get("roundCutoff") or {}
        if not rc.get("has_purple") and battle.get("battleCutoff", {}).get("has_purple"):
            rc = battle.get("battleCutoff") or {}

        min_dmg = rc.get("min_damage_for_purple") or 0
        cutoff_rank = rc.get("cutoff_rank") or "?"
        item_info = rc.get("last_purple_item") or {}
        item_name = item_info.get("name") or "Фіолетовий предмет (Epic+)"
        player_info = rc.get("last_purple_player") or {}
        holder = player_info.get("username") or "Вільний слот"
        gap = rc.get("gap_to_next", 0)
        total_purple = rc.get("total_purple_plus_items", 1)

        fire_tag = "🔥 <b>СУПЕР ЛОТ!</b> " if min_dmg < 100_000 else ""

        lines = [
            f"🎯 {fire_tag}<b>Шанс на фіол: {clean_eta} до кінця!</b>",
            f"",
            f"⚔️ <b>Битва:</b> {reg} (<i>{btype}</i>)",
            f"🏳️ <b>Раунд #{r_num}:</b> {att} (<b>{att_pts}</b>) vs {dff} (<b>{def_pts}</b>) / 300 очок",
            f"⏱ <b>До нагородження:</b> <b>~{mins} хвилин</b>",
            f"",
            f"🎁 <b>Мінімальний поріг для фіолу:</b> <code>{self.format_dmg(min_dmg)} dmg</code>",
            f"📦 <b>Предмет на кону:</b> <b>{item_name}</b> (Ранг #{cutoff_rank})",
            f"👤 <b>Останній слот тримає:</b> <code>{holder}</code>",
            f"",
            f"💡 <i>Порада: нанесіть від <b>{self.format_dmg(min_dmg + 1)} dmg</b> прямо зараз, щоб вибити цей слот і забрати фіол!</i>"
        ]
        return "\n".join(lines)

    async def check_battles_cycle(self):
        """Single check cycle of all active battles."""
        if self.is_paused:
            return

        self.last_check_time = time.strftime("%H:%M:%S")
        self.cycle_count += 1

        try:
            battles = await self.analyzer.get_all_battles_intel(force_refresh=True)
        except Exception as e:
            logger.error(f"Error fetching battles intel: {e}")
            return

        # Find all battles in the sniper window with purple drops (round or battle level)
        sniper_candidates = []
        active_round_keys = set()

        for b in battles:
            b_id = b.get("battleId")
            r_id = b.get("round", {}).get("id")
            if not b_id or not r_id:
                continue

            alert_key = f"{b_id}_{r_id}"
            active_round_keys.add(alert_key)

            tm = b.get("timing", {})
            rc = b.get("roundCutoff", {})
            bc = b.get("battleCutoff", {})
            has_purple = bool(rc.get("has_purple") or bc.get("has_purple"))

            # Must be in sniper window and have purple items
            if tm.get("isSniperWindow") and has_purple:
                sniper_candidates.append((alert_key, b))

        # Cleanup alerted_user_rounds for rounds that have finished
        self.alerted_user_rounds = {
            k for k in self.alerted_user_rounds 
            if any(k.startswith(f"{active_k}_") for active_k in active_round_keys)
        }

        if not sniper_candidates:
            return

        # Get subscribers who want battle sniper push alerts
        target_chat_ids = self.subscribers_db.get_sniper_chat_ids()
        if not target_chat_ids:
            return

        for alert_key, battle in sniper_candidates:
            rc = battle.get("roundCutoff") or {}
            if not rc.get("has_purple") and battle.get("battleCutoff", {}).get("has_purple"):
                rc = battle.get("battleCutoff") or {}
            min_dmg = rc.get("min_damage_for_purple") or 0
            url = battle.get("wareraUrl", f"https://app.warera.io/battle/{battle.get('battleId')}")
            cached_msg: Optional[str] = None

            for cid in target_chat_ids:
                user_alert_key = f"{alert_key}_{cid}"
                if user_alert_key in self.alerted_user_rounds:
                    continue

                user_th = self.subscribers_db.get_user_threshold(cid)
                if min_dmg <= user_th:
                    if cached_msg is None:
                        cached_msg = self.build_alert_message(battle)
                    logger.info(f"🚨 Firing sniper alert for {battle.get('region', {}).get('name', 'Battle')} to {cid} (min_dmg: {min_dmg} <= th: {user_th})")
                    try:
                        await self.send_telegram_alert(cid, cached_msg, url)
                        self.alerted_user_rounds.add(user_alert_key)
                        await asyncio.sleep(0.05)  # Telegram broadcast throttling
                    except Exception as e:
                        logger.error(f"Failed to deliver to {cid}: {e}")
                else:
                    logger.debug(f"Skipping alert for {cid}: min_dmg {min_dmg} > personal threshold {user_th}")

    async def start(self):
        """Main loop of the background sniper worker."""
        if self.is_running:
            return
        self.is_running = True
        logger.info(f"WarEra Battle Sniper Worker started (poll interval: {self.check_interval}s).")
        try:
            while self.is_running:
                try:
                    await self.check_battles_cycle()
                except Exception as e:
                    logger.error(f"Unexpected error in BattleSniperWorker loop: {e}")
                await asyncio.sleep(self.check_interval)
        except asyncio.CancelledError:
            logger.info("BattleSniperWorker cancelled.")
        finally:
            self.is_running = False
            await self.close()

    def stop(self):
        self.is_running = False


# Global singleton instance
_GLOBAL_SNIPER_WORKER: Optional[BattleSniperWorker] = None

def get_sniper_worker() -> BattleSniperWorker:
    global _GLOBAL_SNIPER_WORKER
    if _GLOBAL_SNIPER_WORKER is None:
        _GLOBAL_SNIPER_WORKER = BattleSniperWorker()
    return _GLOBAL_SNIPER_WORKER
