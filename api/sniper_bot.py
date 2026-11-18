"""
WarEra Battle Sniper Dedicated Telegram Bot Controller
Manages 1-on-1 private notifications and interactive commands for clan members.
Zero market logic: 100% focused on Battle Sniping and purple drop monitoring.
"""

import asyncio
import logging
from typing import Optional, Any
import httpx

import config
from battle_analyzer import WarEraBattleAnalyzer
from subscribers_db import SubscribersDB

logger = logging.getLogger("WarEraSniperBot")

class SniperBotController:
    """
    Dedicated Telegram Bot for WarEra Battle Sniping.
    Allows 25+ clan members to receive private alerts and query battles without shared groups.
    """
    def __init__(self, token: Optional[str] = None):
        self.token = token or getattr(config, "TELEGRAM_SNIPER_BOT_TOKEN", None) or getattr(config, "TELEGRAM_BOT_TOKEN", None)
        self.subscribers_db = SubscribersDB()
        self.admin_chat_ids = set(getattr(config, "TELEGRAM_CHAT_IDS", []))
        self.offset = 0
        self.is_running = False
        self._http_client: Optional[httpx.AsyncClient] = None

    async def get_client(self) -> httpx.AsyncClient:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=35.0)
        return self._http_client

    async def close(self):
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()

    def _is_admin(self, user_id: Any, chat_id: Any = None) -> bool:
        if not self.admin_chat_ids:
            return True
        return str(user_id) in self.admin_chat_ids or (chat_id is not None and str(chat_id) in self.admin_chat_ids)

    def _build_panel_text(self, chat_id: Optional[str] = None) -> str:
        user_prefs = self.subscribers_db.get_user_prefs(chat_id) if chat_id else {}
        sniper_on = user_prefs.get("sniper_alerts", True)
        subs_count = self.subscribers_db.count()

        return (
            f"🎯 <b>WarEra · Снайпер фіолетового дропу (T4 Epic+)</b>\n\n"
            f"🔔 <b>Ваші сповіщення:</b> <b>{'🟢 УВІМКНЕНО' if sniper_on else '🔴 ВИМКНЕНО'}</b>\n"
            f"📡 <b>Статус моніторингу:</b> 🟢 <b>АКТИВНИЙ (перевірка щохвилини)</b>\n"
            f"👥 <b>Підписників бота:</b> <code>{subs_count} бійців</code>\n\n"
            f"⏳ <i>Сповіщення надсилаються автоматично за 15–20 хв до кінця раунду, "
            f"коли пул дропу зафіксовано і поріг шкоди стабільний.</i>\n\n"
            f"<i>Скористайтеся кнопками нижче для швидкого пошуку:</i>"
        )

    def _build_keyboard(self, chat_id: Optional[str] = None) -> dict:
        user_prefs = self.subscribers_db.get_user_prefs(chat_id) if chat_id else {}
        sniper_on = user_prefs.get("sniper_alerts", True)
        toggle_text = "🎯 Сповіщення: 🟢 ВКЛ" if sniper_on else "🎯 Сповіщення: 🔴 ВИКЛ"

        return {
            "inline_keyboard": [
                [
                    {"text": "🎯 Снайпер (15-20 хв)", "callback_data": "sniper_cmd_snipe"},
                    {"text": "⚔️ Битви з фіолом", "callback_data": "sniper_cmd_battles"},
                ],
                [
                    {"text": toggle_text, "callback_data": "sniper_toggle_alerts"},
                ],
                [
                    {"text": "🔄 Оновити меню", "callback_data": "sniper_cmd_status"}
                ]
            ]
        }

    async def register_commands(self):
        """Registers command menu in Telegram UI for the sniper bot."""
        if not self.token:
            return
        client = await self.get_client()
        url = f"https://api.telegram.org/bot{self.token}/setMyCommands"
        commands = [
            {"command": "start", "description": "🎯 Головне меню та налаштування"},
            {"command": "snipe", "description": "🎯 Битви на фінішній прямі (15-20 хв)"},
            {"command": "battles", "description": "⚔️ Всі активні битви з фіолом"},
            {"command": "sniper_on", "description": "🔔 Увімкнути пуш-сповіщення"},
            {"command": "sniper_off", "description": "🔕 Вимкнути пуш-сповіщення"},
            {"command": "status", "description": "🔄 Статус моніторингу"},
            {"command": "help", "description": "ℹ️ Довідка та інструкція"}
        ]
        try:
            await client.post(url, json={"commands": commands})
        except Exception as e:
            logger.debug(f"Failed to set Sniper Bot Telegram commands: {e}")

    async def send_message(self, chat_id: str, text: str, reply_markup: Optional[dict] = None) -> Optional[dict]:
        if not self.token:
            return None
        client = await self.get_client()
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup

        try:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                return resp.json().get("result")
            logger.error(f"Sniper Bot send error to {chat_id}: {resp.text}")
        except Exception as e:
            logger.error(f"Sniper Bot send exception to {chat_id}: {e}")
        return None

    async def edit_message(self, chat_id: str, message_id: int, text: str, reply_markup: Optional[dict] = None) -> bool:
        if not self.token:
            return False
        client = await self.get_client()
        url = f"https://api.telegram.org/bot{self.token}/editMessageText"
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup

        try:
            resp = await client.post(url, json=payload)
            return resp.status_code == 200
        except Exception:
            return False

    async def answer_callback(self, callback_query_id: str, text: Optional[str] = None):
        if not self.token:
            return
        client = await self.get_client()
        url = f"https://api.telegram.org/bot{self.token}/answerCallbackQuery"
        payload = {"callback_query_id": callback_query_id}
        if text:
            payload["text"] = text
            payload["show_alert"] = False
        try:
            await client.post(url, json=payload)
        except Exception:
            pass

    async def _get_battles_text(self, sniper_only: bool = False) -> str:
        try:
            analyzer = WarEraBattleAnalyzer()
            battles = await analyzer.get_all_battles_intel()
            await analyzer.close()

            if not battles:
                return "⚔️ <b>Немає активних битв або сервери WarEra недоступні.</b>"

            if sniper_only:
                target_battles = [b for b in battles if b.get("timing", {}).get("isSniperWindow")]
                if not target_battles:
                    sorted_by_time = sorted(battles, key=lambda x: x.get("timing", {}).get("minutesLeft", 999))
                    next_battle = sorted_by_time[0] if sorted_by_time else None
                    next_eta = next_battle['timing']['formattedEta'].lstrip("~") if next_battle else "—"
                    next_name = next_battle['region']['name'] if next_battle else "—"
                    return (
                        "🎯 <b>Снайперське вікно (15–20 хв до кінця):</b>\n\n"
                        "⚠️ <i>Наразі немає битв на завершальній стадії раунду.</i>\n\n"
                        f"⏳ Найбільш зрілий раунд зараз: <b>{next_name}</b> (~{next_eta} до кінця).\n"
                        "💡 <i>Снайпінг проводиться за 15-20 хв до кінця, коли поріг шкоди стабільний і точний.</i>\n\n"
                        "Щоб переглянути всі битви з попередніми оцінками, надішліть /battles"
                    )
            else:
                target_battles = [b for b in battles if b.get("roundCutoff", {}).get("has_purple") or b.get("battleCutoff", {}).get("has_purple")]

            msg = "🎯 <b>WarEra · Снайпер фіолетового дропу (T4 Epic+):</b>\n\n" if sniper_only else "⚔️ <b>WarEra · Активні битви з фіолетовим дропом:</b>\n\n"
            if not target_battles:
                msg += "<i>Наразі в жодній битві ще немає сформованого фіолетового луту (мало загального дамагу).</i>"
                return msg

            for idx, b in enumerate(target_battles[:6], 1):
                reg = b["region"]["name"]
                btype = "Війна" if b["type"] == "war" else "Повстання"
                r_num = b["round"]["number"]
                att = b["attacker"]["name"]
                dff = b["defender"]["name"]
                att_pts = b["attacker"]["roundPoints"]
                def_pts = b["defender"]["roundPoints"]

                rc = b["roundCutoff"]
                bc = b["battleCutoff"]
                tm = b.get("timing", {})
                eta_clean = tm.get("formattedEta", "—").lstrip("~").strip()
                is_sniper = tm.get("isSniperWindow", False)
                time_tag = f"🎯 {eta_clean} до кінця (Снайперське вікно)" if is_sniper else f"⏳ ~{eta_clean} до кінця"

                msg += f"<b>{idx}. {reg}</b> (<i>{btype}</i>)\n"
                msg += f"🏳️ {att} ({att_pts}) vs {dff} ({def_pts}) • Р#{r_num} / 300\n"
                msg += f"⏱ <b>Час:</b> <code>{time_tag}</code>\n"

                if rc.get("has_purple"):
                    dmg = f"{rc['min_damage_for_purple']:,}".replace(",", " ")
                    item = rc["last_purple_item"]["name"]
                    rank = rc["cutoff_rank"]
                    tag = " 🔥 <b>ТОП</b>" if rc["min_damage_for_purple"] < 100000 else ""
                    msg += f"🎯 <b>Раунд:</b> <code>{dmg} dmg</code> (#{rank} • {item}){tag}\n"
                else:
                    msg += f"🎯 <b>Раунд:</b> <i>Немає фіолу</i>\n"

                if bc.get("has_purple"):
                    b_dmg = f"{bc['min_damage_for_purple']:,}".replace(",", " ")
                    b_item = bc["last_purple_item"]["name"]
                    msg += f"🏆 <b>Битва:</b> <code>{b_dmg} dmg</code> (#{bc['cutoff_rank']} • {b_item})\n"

                msg += f"🔗 <a href=\"{b['wareraUrl']}\">Відкрити на WarEra ↗</a>\n\n"

            msg += "💡 <i>Порада: найточніші дані фіксуються за 15–20 хв до кінця раунду (/snipe).</i>"
            return msg
        except Exception as e:
            logger.error(f"Error in Sniper Bot get_battles_text: {e}")
            return f"⚠️ <b>Помилка аналізу битв:</b> <code>{e}</code>"

    async def handle_update(self, update: dict):
        # 1. Inline Buttons
        if "callback_query" in update:
            cb = update["callback_query"]
            cb_id = cb["id"]
            from_user = cb.get("from", {})
            message = cb.get("message", {})
            chat = message.get("chat", {})
            chat_id = str(chat.get("id"))
            msg_id = message.get("message_id")
            data = cb.get("data", "")

            self.subscribers_db.register_user(
                chat_id=chat_id,
                username=from_user.get("username"),
                first_name=from_user.get("first_name")
            )

            if data == "sniper_toggle_alerts":
                curr = self.subscribers_db.get_user_prefs(chat_id).get("sniper_alerts", True)
                new_val = self.subscribers_db.set_sniper_alerts(chat_id, not curr)
                status_txt = "🟢 УВІМКНЕНО" if new_val else "🔴 ВИМКНЕНО"
                await self.answer_callback(cb_id, f"🎯 Сповіщення: {status_txt}")
                if msg_id:
                    await self.edit_message(chat_id, msg_id, self._build_panel_text(chat_id), self._build_keyboard(chat_id))
                return

            elif data == "sniper_cmd_snipe":
                await self.answer_callback(cb_id, "🎯 Шукаю битви у 15-20 хв вікні...")
                txt = await self._get_battles_text(sniper_only=True)
                await self.send_message(chat_id, txt)
                return

            elif data == "sniper_cmd_battles":
                await self.answer_callback(cb_id, "⚔️ Отримую активні битви...")
                txt = await self._get_battles_text(sniper_only=False)
                await self.send_message(chat_id, txt)
                return

            elif data == "sniper_cmd_status":
                await self.answer_callback(cb_id, "Оновлено!")
                if msg_id:
                    await self.edit_message(chat_id, msg_id, self._build_panel_text(chat_id), self._build_keyboard(chat_id))
                return

        # 2. Text Commands
        if "message" in update:
            msg = update["message"]
            text = (msg.get("text") or "").strip()
            from_user = msg.get("from", {})
            chat = msg.get("chat", {})
            chat_id = str(chat.get("id"))

            self.subscribers_db.register_user(
                chat_id=chat_id,
                username=from_user.get("username"),
                first_name=from_user.get("first_name")
            )

            words = text.split()
            first_word = words[0].lower() if words else ""
            if "@" in first_word:
                first_word = first_word.split("@")[0]
            clean_cmd = first_word.lstrip("/")

            if first_word in ("/start", "/menu", "/help") or clean_cmd in ("start", "menu", "help", "меню", "допомога"):
                await self.send_message(chat_id, self._build_panel_text(chat_id), self._build_keyboard(chat_id))

            elif first_word in ("/status", "/стан") or clean_cmd in ("status", "стан", "статус"):
                await self.send_message(chat_id, self._build_panel_text(chat_id), self._build_keyboard(chat_id))

            elif first_word in ("/battles", "/битви", "/purple", "/фіол") or clean_cmd in ("battles", "битви", "purple", "фіол"):
                await self.send_message(chat_id, "🔍 <i>Аналізую битви та шукаю фіолетовий дроп...</i>")
                txt = await self._get_battles_text(sniper_only=False)
                await self.send_message(chat_id, txt)

            elif first_word in ("/snipe", "/снайп", "/hot", "/гарячі") or clean_cmd in ("snipe", "снайп", "hot"):
                await self.send_message(chat_id, "🎯 <i>Шукаю битви на фінішній прямі (15–20 хв до кінця)...</i>")
                txt = await self._get_battles_text(sniper_only=True)
                await self.send_message(chat_id, txt)

            elif first_word in ("/sniper_on",) or clean_cmd in ("sniper_on", "вкл"):
                self.subscribers_db.set_sniper_alerts(chat_id, True)
                await self.send_message(
                    chat_id,
                    "🎯 <b>Снайпінг битв:</b> Сповіщення за 15–20 хв до кінця раунду <b>УВІМКНЕНО 🟢</b>\n\n"
                    "Ви отримуватимете особисте повідомлення, щойно з'явиться бій на фінішній прямі з фіолетовим дропом."
                )

            elif first_word in ("/sniper_off",) or clean_cmd in ("sniper_off", "викл"):
                self.subscribers_db.set_sniper_alerts(chat_id, False)
                await self.send_message(
                    chat_id,
                    "🎯 <b>Снайпінг битв:</b> Сповіщення <b>ВИМКНЕНО 🔴</b>\n\n"
                    "Автоматичні пуші вимкнено. Ви завжди можете перевірити ситуацію вручну через /snipe."
                )

            elif first_word in ("/subscribers", "/users") or clean_cmd in ("subscribers", "users", "бійці"):
                if not self._is_admin(from_user.get("id"), chat_id):
                    await self.send_message(chat_id, "⛔ Список підписників доступний лише адміністратору.")
                    return
                all_subs = self.subscribers_db.get_all_subscribers()
                sub_text = f"👥 <b>Підписники снайпер-бота ({len(all_subs)} бійців):</b>\n\n"
                for cid, u in all_subs.items():
                    name = u.get("first_name", "Fighter")
                    uname = f"@{u['username']}" if u.get("username") and u['username'] != "Unknown" else "без юзернейму"
                    s_ico = "🎯" if u.get("sniper_alerts", True) else "⚪"
                    sub_text += f"• <code>{cid}</code>: <b>{name}</b> ({uname}) [{s_ico}]\n"
                await self.send_message(chat_id, sub_text)

    async def start_polling(self):
        """Continuously poll Telegram for updates on the Sniper Bot."""
        if not self.token:
            logger.info("Sniper Telegram Bot token not configured, skipping sniper bot listener.")
            return

        try:
            await self.register_commands()
        except Exception as e:
            logger.warning(f"Error registering Sniper Bot commands: {e}")

        self.is_running = True
        logger.info("WarEra Sniper Telegram Bot listener started.")

        client = await self.get_client()
        url = f"https://api.telegram.org/bot{self.token}/getUpdates"

        while self.is_running:
            try:
                params = {"offset": self.offset, "timeout": 20}
                resp = await client.get(url, params=params, timeout=30.0)
                if resp.status_code == 200:
                    data = resp.json()
                    for update in data.get("result", []):
                        self.offset = update["update_id"] + 1
                        try:
                            await self.handle_update(update)
                        except Exception as e:
                            logger.error(f"Error handling sniper update: {e}")
                elif resp.status_code == 409:
                    await asyncio.sleep(5)
                else:
                    await asyncio.sleep(2)
            except (httpx.TimeoutException, httpx.NetworkError):
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Sniper Bot polling error: {e}")
                await asyncio.sleep(3)
