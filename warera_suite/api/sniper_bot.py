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
from battle_analyzer import get_shared_battle_analyzer, WarEraBattleAnalyzer
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
        contract_on = user_prefs.get("contract_alerts", False)
        subs_count = self.subscribers_db.count()

        user_th = self.subscribers_db.get_user_threshold(chat_id) if chat_id else getattr(config, "SNIPER_MAX_DAMAGE", 75000)
        formatted_max = f"{user_th:,}".replace(",", " ")

        return (
            f"🎯 <b>WarEra · Снайпер битв та Контракти на урон</b>\n\n"
            f"🎯 <b>Ваш особистий поріг:</b> ≤ <code>{formatted_max} dmg</code> (фіол)\n"
            f"🔔 <b>Сповіщення снайпера (фіол):</b> <b>{'🟢 УВІМКНЕНО' if sniper_on else '🔴 ВИМКНЕНО'}</b>\n"
            f"💰 <b>Сповіщення про контракти:</b> <b>{'🟢 УВІМКНЕНО' if contract_on else '🔴 ВИМКНЕНО'}</b>\n"
            f"📡 <b>Моніторинг:</b> 🟢 <b>АКТИВНИЙ (~50с цикл)</b>\n"
            f"👥 <b>Підписників бота:</b> <code>{subs_count} бійців</code>\n\n"
            f"⏳ <i>Снайпер сповіщає за 15–20 хв до кінця раунду (урон ≤ {formatted_max}).</i>\n"
            f"💵 <i>Контракти сповіщають миттєво, щойно з'являється оплата за 1k урону.</i>\n\n"
            f"<i>Скористайтеся кнопками нижче:</i>"
        )

    def _build_keyboard(self, chat_id: Optional[str] = None) -> dict:
        user_prefs = self.subscribers_db.get_user_prefs(chat_id) if chat_id else {}
        sniper_on = user_prefs.get("sniper_alerts", True)
        contract_on = user_prefs.get("contract_alerts", False)
        toggle_sniper_text = "🎯 Снайпер: 🟢 ВКЛ" if sniper_on else "🎯 Снайпер: 🔴 ВИКЛ"
        toggle_contract_text = "💰 Контракти: 🟢 ВКЛ" if contract_on else "💰 Контракти: 🔴 ВИКЛ"

        user_th = self.subscribers_db.get_user_threshold(chat_id) if chat_id else getattr(config, "SNIPER_MAX_DAMAGE", 75000)
        formatted_th = f"{user_th // 1000}k" if user_th < 1000000 else f"{user_th // 1000000}M"

        return {
            "inline_keyboard": [
                [
                    {"text": f"🎯 Снайпер (≤ {formatted_th})", "callback_data": "sniper_cmd_snipe"},
                    {"text": "⚔️ Битви з фіолом", "callback_data": "sniper_cmd_battles"},
                ],
                [
                    {"text": "💰 Контракти (Оплата за урон)", "callback_data": "sniper_cmd_contracts"},
                    {"text": f"⚙️ Поріг: {formatted_th}", "callback_data": "sniper_menu_threshold"},
                ],
                [
                    {"text": toggle_sniper_text, "callback_data": "sniper_toggle_alerts"},
                    {"text": toggle_contract_text, "callback_data": "sniper_toggle_contracts"},
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
            {"command": "contracts", "description": "💰 Виплати та контракти за урон"},
            {"command": "contracts_on", "description": "💰 Увімкнути пуші про контракти"},
            {"command": "contracts_off", "description": "🔕 Вимкнути пуші про контракти"},
            {"command": "snipe", "description": "🎯 Битви на фінішній прямі (15-20 хв)"},
            {"command": "battles", "description": "⚔️ Всі активні битви з фіолом"},
            {"command": "sniper_on", "description": "🔔 Увімкнути снайпер-сповіщення"},
            {"command": "sniper_off", "description": "🔕 Вимкнути снайпер-сповіщення"},
            {"command": "status", "description": "🔄 Статус моніторингу"},
            {"command": "help", "description": "ℹ️ Довідка та інструкція"}
        ]
        try:
            await client.post(url, json={"commands": commands})
        except Exception as e:
            logger.debug(f"Failed to set Sniper Bot Telegram commands: {e}")
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

    async def _get_battles_text(self, sniper_only: bool = False, chat_id: Optional[str] = None) -> str:
        try:
            analyzer = get_shared_battle_analyzer()
            battles = await analyzer.get_all_battles_intel()

            if not battles:
                # If cold start, brief pause and force retry once across API cluster
                await asyncio.sleep(0.6)
                battles = await analyzer.get_all_battles_intel(force_refresh=True)

            if not battles:
                return (
                    "⏳ <b>Оновлюю дані битв із серверів WarEra...</b>\n\n"
                    "Бот зараз синхронізує активні сутички. Будь ласка, спробуйте ще раз через кілька секунд."
                )

            max_dmg = self.subscribers_db.get_user_threshold(chat_id) if chat_id else getattr(config, "SNIPER_MAX_DAMAGE", 75000)
            formatted_max = f"{max_dmg:,}".replace(",", " ")

            if sniper_only:
                target_battles = [
                    b for b in battles
                    if b.get("timing", {}).get("isSniperWindow")
                    and b.get("roundCutoff", {}).get("has_purple")
                    and (b.get("roundCutoff", {}).get("min_damage_for_purple") or 0) <= max_dmg
                ]
                if not target_battles:
                    exceeded = [
                        b for b in battles
                        if b.get("timing", {}).get("isSniperWindow")
                        and b.get("roundCutoff", {}).get("has_purple")
                        and (b.get("roundCutoff", {}).get("min_damage_for_purple") or 0) > max_dmg
                    ]
                    active_only = [b for b in battles if b.get("timing", {}).get("minutesLeft", 0) > 0 and b.get("roundCutoff", {}).get("has_purple")]
                    sorted_by_time = sorted(active_only or battles, key=lambda x: x.get("timing", {}).get("minutesLeft", 999))
                    next_battle = sorted_by_time[0] if sorted_by_time else None
                    next_eta = next_battle['timing']['formattedEta'].lstrip("~") if next_battle else "—"
                    next_name = next_battle['region']['name'] if next_battle else "—"

                    exceeded_text = ""
                    if exceeded:
                        exceeded_list = [f"• {b['region']['name']}: <code>{b['roundCutoff']['min_damage_for_purple']:,} dmg</code> ({b['roundCutoff']['last_purple_item']['name']})".replace(",", " ") for b in exceeded[:3]]
                        exceeded_text = f"\n🚫 <b>Відсіяно через перевищення порогу ({formatted_max} dmg):</b>\n" + "\n".join(exceeded_list) + "\n"

                    return (
                        f"🎯 <b>Снайперське вікно (поріг ≤ {formatted_max} dmg):</b>\n\n"
                        f"⚠️ <i>Наразі немає битв у 15–20 хв вікні з уроном до {formatted_max} dmg.</i>\n"
                        f"{exceeded_text}\n"
                        f"⏳ Найбільш зрілий раунд: <b>{next_name}</b> (~{next_eta} до кінця).\n"
                        f"💡 <i>Всі битви, що вимагають більше {formatted_max} урону, автоматично відсіюються.</i>\n\n"
                        f"Щоб переглянути всі активні битви, надішліть /battles"
                    )
            else:
                target_battles = [
                    b for b in battles
                    if (b.get("roundCutoff", {}).get("has_purple") and (b.get("roundCutoff", {}).get("min_damage_for_purple") or 0) <= max_dmg)
                    or (b.get("battleCutoff", {}).get("has_purple") and (b.get("battleCutoff", {}).get("min_damage_for_purple") or 0) <= max_dmg)
                ]

            msg = f"🎯 <b>WarEra · Снайпер фіолетового дропу (≤ {formatted_max} dmg):</b>\n\n" if sniper_only else f"⚔️ <b>WarEra · Активні битви (поріг ≤ {formatted_max} dmg):</b>\n\n"
            if not target_battles:
                all_purple = [b for b in battles if b.get("roundCutoff", {}).get("has_purple") or b.get("battleCutoff", {}).get("has_purple")]
                if not all_purple:
                    return f"<i>Наразі в жодній битві ще немає сформованого фіолетового луту (мало загального дамагу).</i>"

                msg += f"⚠️ <i>Немає битв із потрібним уроном до {formatted_max} dmg.</i>\n"
                msg += f"<i>(Всі битви з вищим уроном відсіяно згідно з вашим налаштуванням).</i>\n\n"
                msg += f"📊 <b>Поточні битви з фіолом (перевищують {formatted_max} dmg):</b>\n"
                for idx, b in enumerate(all_purple[:4], 1):
                    reg = b["region"]["name"]
                    rc = b["roundCutoff"]
                    dmg_str = f"{rc['min_damage_for_purple']:,}".replace(",", " ") if rc.get("has_purple") else "—"
                    item_str = rc["last_purple_item"]["name"] if rc.get("has_purple") else "—"
                    eta_str = b.get("timing", {}).get("formattedEta", "—").lstrip("~")
                    msg += f"<b>{idx}. {reg}</b>: <code>{dmg_str} dmg</code> ({item_str}) • ~{eta_str} до кінця\n"
                msg += f"\n💡 <i>Змінити поріг можна командою /threshold &lt;урон&gt; або в меню бота.</i>"
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

    async def _get_contracts_text(self, chat_id: Optional[str] = None) -> str:
        try:
            analyzer = get_shared_battle_analyzer()
            contracts = await analyzer.get_active_contracts()
            if not contracts:
                return (
                    "💰 <b>WarEra · Активні контракти (виплати за урон):</b>\n\n"
                    "<i>Наразі немає битв з активними виплатами за урон або пул монет вичерпано.</i>"
                )

            msg = "💰 <b>WarEra · Активні контракти на урон (Bounties):</b>\n\n"
            msg += "<i>Заробляйте монети за кожну 1 000 нанесеного дамагу на стороні наймача:</i>\n\n"

            for idx, c in enumerate(contracts[:8], 1):
                reg = c['region']
                btype = "Війна" if c['type'] == 'war' else "Повстання"
                side_tag = "🔴 АТАКА" if c['side'] == 'attacker' else "🛡 ОБОРОНА"
                country = f"{c['flag']} {c['country']}"
                rate = c['ratePer1k']
                pool = c['pool']
                sniper_tag = " 🎯 [15-20 хв]" if c['isSniperWindow'] else ""

                msg += (
                    f"<b>{idx}. {reg}</b> (<i>{btype}</i>){sniper_tag}\n"
                    f"   Сторона: <b>{side_tag}</b> ({country})\n"
                    f"   💵 <b>Ставка:</b> <code>{rate} монет / 1k dmg</code>\n"
                    f"   🏦 <b>Залишок пулу:</b> <code>{pool:,} монет</code>\n"
                    f"   👉 <a href=\"{c['wareraUrl']}\">Перейти до битви ↗</a>\n\n"
                ).replace(",", " ")

            return msg
        except Exception as e:
            logger.error(f"Error in Sniper Bot get_contracts_text: {e}")
            return f"⚠️ <b>Помилка аналізу контрактів:</b> <code>{e}</code>"

    async def send_auth_prompt(self, chat_id: str):
        """Sends clan password prompt to unauthorized users."""
        text = (
            "🔒 <b>Доступ обмежено паролем</b>\n\n"
            "Цей снайпер-бот призначений виключно для бійців нашого клану.\n\n"
            "Щоб отримати доступ до снайпінгу та сповіщень, введіть пароль клану:\n"
            "• Надішліть: <code>/auth &lt;пароль&gt;</code>\n"
            "• Або просто напишіть пароль повідомленням у цей чат.\n\n"
            "<i>(Після разового введення пароля доступ надається назавжди).</i>"
        )
        await self.send_message(chat_id, text)

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

            # Security gate: require password authorization
            if not self.subscribers_db.is_authorized(chat_id):
                await self.answer_callback(cb_id, "🔒 Доступ обмежено паролем клану!", show_alert=True)
                await self.send_auth_prompt(chat_id)
                return

            if data == "sniper_toggle_alerts":
                curr = self.subscribers_db.get_user_prefs(chat_id).get("sniper_alerts", True)
                new_val = self.subscribers_db.set_sniper_alerts(chat_id, not curr)
                status_txt = "🟢 УВІМКНЕНО" if new_val else "🔴 ВИМКНЕНО"
                await self.answer_callback(cb_id, f"🎯 Снайпер: {status_txt}")
                if msg_id:
                    await self.edit_message(chat_id, msg_id, self._build_panel_text(chat_id), self._build_keyboard(chat_id))
                return

            elif data == "sniper_toggle_contracts":
                curr = self.subscribers_db.get_user_prefs(chat_id).get("contract_alerts", False)
                new_val = self.subscribers_db.set_contract_alerts(chat_id, not curr)
                status_txt = "🟢 УВІМКНЕНО" if new_val else "🔴 ВИМКНЕНО"
                await self.answer_callback(cb_id, f"💰 Контракти: {status_txt}")
                if msg_id:
                    await self.edit_message(chat_id, msg_id, self._build_panel_text(chat_id), self._build_keyboard(chat_id))
                return

            elif data == "sniper_cmd_snipe":
                await self.answer_callback(cb_id, "🎯 Шукаю битви у 15-20 хв вікні...")
                txt = await self._get_battles_text(sniper_only=True, chat_id=chat_id)
                await self.send_message(chat_id, txt)
                return

            elif data == "sniper_cmd_battles":
                await self.answer_callback(cb_id, "⚔️ Отримую активні битви...")
                txt = await self._get_battles_text(sniper_only=False, chat_id=chat_id)
                await self.send_message(chat_id, txt)
                return

            elif data == "sniper_cmd_contracts":
                await self.answer_callback(cb_id, "💰 Шукаю активні контракти...")
                txt = await self._get_contracts_text(chat_id=chat_id)
                await self.send_message(chat_id, txt)
                return

            elif data == "sniper_cmd_status":
                await self.answer_callback(cb_id, "Оновлено!")
                if msg_id:
                    await self.edit_message(chat_id, msg_id, self._build_panel_text(chat_id), self._build_keyboard(chat_id))
                return

            elif data == "sniper_menu_threshold":
                curr_th = self.subscribers_db.get_user_threshold(chat_id)
                th_text = (
                    f"⚙️ <b>Налаштування вашого особистого порогу</b>\n\n"
                    f"Ваш поточний поріг: <b>{curr_th:,} dmg</b>\n\n"
                    f"Бот відсіює битви особисто для вас і надсилає пуші лише тоді, коли для фіолетового дропу потрібно не більше цього значення.\n\n"
                    f"Оберіть бажаний поріг:"
                ).replace(",", " ")
                th_kb = {
                    "inline_keyboard": [
                        [
                            {"text": "50 000 dmg", "callback_data": "set_th_50000"},
                            {"text": "75 000 dmg (Дефолт)", "callback_data": "set_th_75000"},
                        ],
                        [
                            {"text": "100 000 dmg", "callback_data": "set_th_100000"},
                            {"text": "150 000 dmg", "callback_data": "set_th_150000"},
                        ],
                        [
                            {"text": "Без обмежень (Всі)", "callback_data": "set_th_999999999"},
                            {"text": "🔙 Назад", "callback_data": "sniper_cmd_status"},
                        ]
                    ]
                }
                if msg_id:
                    await self.edit_message(chat_id, msg_id, th_text, th_kb)
                return

            elif data.startswith("set_th_"):
                new_th = int(data.replace("set_th_", ""))
                self.subscribers_db.set_user_threshold(chat_id, new_th)
                th_display = "Без обмежень" if new_th > 10000000 else f"{new_th:,} dmg".replace(",", " ")
                await self.answer_callback(cb_id, f"Ваш особистий поріг: {th_display}")
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

            # Security gate: check if user is authorized or attempting to authenticate
            if not self.subscribers_db.is_authorized(chat_id):
                auth_success = False
                # 1. /start <password> deep link or /auth <password>
                if first_word in ("/start", "/auth", "/login", "/пароль", "/вхід") and len(words) > 1:
                    auth_success = self.subscribers_db.authorize_user(chat_id, words[1].strip())
                # 2. Plain password text
                elif text and not text.startswith("/"):
                    auth_success = self.subscribers_db.authorize_user(chat_id, text.strip())

                if auth_success:
                    await self.send_message(
                        chat_id,
                        "🎉 <b>Доступ надано!</b> Ласкаво просимо до Снайпера Клану WarEra ⚔️\n\n"
                        "Пароль успішно підтверджено. Тепер ви маєте повний доступ до снайпінгу битв."
                    )
                    await self.send_message(chat_id, self._build_panel_text(chat_id), self._build_keyboard(chat_id))
                    return
                else:
                    await self.send_auth_prompt(chat_id)
                    return

            if first_word in ("/start", "/menu", "/help") or clean_cmd in ("start", "menu", "help", "меню", "допомога"):
                await self.send_message(chat_id, self._build_panel_text(chat_id), self._build_keyboard(chat_id))

            elif first_word in ("/status", "/стан") or clean_cmd in ("status", "стан", "статус"):
                await self.send_message(chat_id, self._build_panel_text(chat_id), self._build_keyboard(chat_id))

            elif first_word in ("/battles", "/битви", "/purple", "/фіол") or clean_cmd in ("battles", "битви", "purple", "фіол"):
                await self.send_message(chat_id, "🔍 <i>Аналізую битви та шукаю фіолетовий дроп...</i>")
                txt = await self._get_battles_text(sniper_only=False, chat_id=chat_id)
                await self.send_message(chat_id, txt)

            elif first_word in ("/contracts", "/контракти", "/bounties", "/найманці") or clean_cmd in ("contracts", "контракти", "bounties", "найманці"):
                await self.send_message(chat_id, "💰 <i>Шукаю відкриті контракти з оплатою за урон...</i>")
                txt = await self._get_contracts_text(chat_id=chat_id)
                await self.send_message(chat_id, txt)

            elif first_word in ("/snipe", "/снайп", "/hot", "/гарячі") or clean_cmd in ("snipe", "снайп", "hot"):
                await self.send_message(chat_id, "🎯 <i>Шукаю битви на фінішній прямі (15–20 хв до кінця)...</i>")
                txt = await self._get_battles_text(sniper_only=True, chat_id=chat_id)
                await self.send_message(chat_id, txt)

            elif first_word in ("/threshold", "/поріг", "/dmg", "/урон") or clean_cmd in ("threshold", "поріг", "dmg", "урон"):
                if len(words) > 1:
                    raw_val = words[1].lower().replace("k", "000").replace("к", "000").replace("m", "000000").replace("м", "000000")
                    try:
                        val = int(raw_val)
                        self.subscribers_db.set_user_threshold(chat_id, val)
                        await self.send_message(chat_id, f"✅ <b>Ваш особистий поріг оновлено:</b> <code>{val:,} dmg</code>\nТепер ви отримуватимете пуші та результати /snipe тільки для битв до цього урону.".replace(",", " "))
                    except ValueError:
                        await self.send_message(chat_id, "⚠️ Будь ласка, вкажіть число, наприклад: <code>/threshold 75000</code> або <code>/threshold 75k</code>")
                else:
                    curr_th = self.subscribers_db.get_user_threshold(chat_id)
                    await self.send_message(chat_id, f"🎯 <b>Ваш особистий поріг снайпінгу:</b> <code>{curr_th:,} dmg</code>\nЩоб змінити, введіть: <code>/threshold 75000</code> або натисніть кнопку в меню.".replace(",", " "))

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

            elif first_word in ("/contracts_on", "/bounties_on") or clean_cmd in ("contracts_on", "bounties_on"):
                self.subscribers_db.set_contract_alerts(chat_id, True)
                await self.send_message(
                    chat_id,
                    "💰 <b>Контракти на урон:</b> Автосповіщення <b>УВІМКНЕНО 🟢</b>\n\n"
                    "Ви отримуватимете сповіщення в особисті повідомлення щойно з'явиться новий контракт з оплатою за урон у будь-якій битві."
                )

            elif first_word in ("/contracts_off", "/bounties_off") or clean_cmd in ("contracts_off", "bounties_off"):
                self.subscribers_db.set_contract_alerts(chat_id, False)
                await self.send_message(
                    chat_id,
                    "💰 <b>Контракти на урон:</b> Автосповіщення <b>ВИМКНЕНО 🔴</b>\n\n"
                    "Автоматичні пуші про контракти вимкнено. Ви можете перевірити активні контракти в будь-який час через /contracts."
                )

            elif first_word in ("/revoke", "/відкликати") and len(words) > 1:
                if not self._is_admin(from_user.get("id"), chat_id):
                    await self.send_message(chat_id, "⛔ Команда доступна лише адміністратору.")
                    return
                target_cid = words[1].strip()
                self.subscribers_db.revoke_user(target_cid)
                await self.send_message(chat_id, f"🔒 Доступ для користувача <code>{target_cid}</code> відкликано.")

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
                    c_ico = "💰" if u.get("contract_alerts", False) else "⚪"
                    sub_text += f"• <code>{cid}</code>: <b>{name}</b> ({uname}) [{s_ico} {c_ico}]\n"
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
