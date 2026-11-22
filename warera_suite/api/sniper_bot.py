"""
WarEra Battle Sniper Dedicated Telegram Bot Controller
Manages 1-on-1 private notifications and interactive commands for clan members.
Zero market logic: 100% focused on Battle Sniping and purple drop monitoring.
"""

import asyncio
import logging
from typing import Optional, Any, List, Dict, Tuple
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
        auction_on = user_prefs.get("auction_alerts", False)
        subs_count = self.subscribers_db.count()

        user_th = self.subscribers_db.get_user_threshold(chat_id) if chat_id else getattr(config, "SNIPER_MAX_DAMAGE", 75000)
        formatted_max = f"{user_th:,}".replace(",", " ")

        min_rate = self.subscribers_db.get_user_min_bounty_rate(chat_id) if chat_id else 0.0
        rate_display = f"≥ {min_rate} 🪙 / 1k" if min_rate > 0 else "Всі (від 0.01)"

        min_budget = self.subscribers_db.get_user_min_contract_budget(chat_id) if chat_id else 0.0
        budget_display = f"≥ {min_budget:g} 🪙" if min_budget > 0 else "Всі (від 0)"

        focused = self.subscribers_db.get_user_focused_battle(chat_id) if chat_id else None
        focus_line = f"🎯 <b>Фокус-битва:</b> <b>⚔️ {focused['battle_name']}</b> (тільки ця битва)\n" if focused else ""

        return (
            f"🎯 <b>WarEra · Центр бойової розвідки ⚔️</b>\n\n"
            f"🔔 <b>Снайпер фіолу:</b> <b>{'🟢 УВІМКНЕНО' if sniper_on else '🔴 ВИМКНЕНО'}</b> (поріг ≤ {formatted_max} dmg)\n"
            f"💰 <b>Баунті (урон):</b> <b>{'🟢 УВІМКНЕНО' if contract_on else '🔴 ВИМКНЕНО'}</b> ({rate_display})\n"
            f"{focus_line}"
            f"📜 <b>Контракти (аукціони):</b> <b>{'🟢 УВІМКНЕНО' if auction_on else '🔴 ВИМКНЕНО'}</b> ({budget_display})\n"
            f"📡 <b>Моніторинг:</b> 🟢 <b>АКТИВНИЙ (~50с цикл)</b>\n"
            f"👥 <b>Підписників бота:</b> <code>{subs_count} бійців</code>\n\n"
            f"<i>Оберіть потрібний розділ нижче для швидкого пошуку та налаштувань:</i>"
        )

    def _build_keyboard(self, chat_id: Optional[str] = None) -> dict:
        user_prefs = self.subscribers_db.get_user_prefs(chat_id) if chat_id else {}
        sniper_on = user_prefs.get("sniper_alerts", True)
        contract_on = user_prefs.get("contract_alerts", False)
        auction_on = user_prefs.get("auction_alerts", False)

        toggle_sniper_text = "🎯 Снайпер: 🟢 ВКЛ" if sniper_on else "🎯 Снайпер: 🔴 ВИКЛ"
        toggle_contract_text = "💰 Баунті: 🟢 ВКЛ" if contract_on else "💰 Баунті: 🔴 ВИКЛ"
        toggle_auction_text = "📜 Контракти: 🟢 ВКЛ" if auction_on else "📜 Контракти: 🔴 ВИКЛ"

        return {
            "inline_keyboard": [
                [
                    {"text": "🎯 Снайпер фіолу ➡️", "callback_data": "menu_sniper"},
                    {"text": "💰 Баунті (Виплати) ➡️", "callback_data": "menu_bounties"},
                ],
                [
                    {"text": "📜 Контракти (Аукціони) ➡️", "callback_data": "menu_auctions"},
                    {"text": "🔄 Оновити статус", "callback_data": "sniper_cmd_status"},
                ],
                [
                    {"text": toggle_sniper_text, "callback_data": "sniper_toggle_alerts"},
                    {"text": toggle_contract_text, "callback_data": "sniper_toggle_contracts"},
                ],
                [
                    {"text": toggle_auction_text, "callback_data": "sniper_toggle_auctions"},
                ]
            ]
        }

    def _build_sniper_menu_text(self, chat_id: Optional[str] = None) -> str:
        user_prefs = self.subscribers_db.get_user_prefs(chat_id) if chat_id else {}
        sniper_on = user_prefs.get("sniper_alerts", True)
        user_th = self.subscribers_db.get_user_threshold(chat_id) if chat_id else getattr(config, "SNIPER_MAX_DAMAGE", 75000)
        formatted_max = f"{user_th:,}".replace(",", " ")

        return (
            f"🎯 <b>Меню: Снайпер фіолетового дропу (T4 Epic+)</b>\n\n"
            f"⚙️ <b>Ваш особистий поріг:</b> ≤ <code>{formatted_max} dmg</code>\n"
            f"🔔 <b>Автосповіщення:</b> <b>{'🟢 УВІМКНЕНО' if sniper_on else '🔴 ВИМКНЕНО'}</b>\n\n"
            f"⏳ <i>Бот відслідковує битви на фінішній прямі (15–20 хв до кінця раунду), "
            f"де розраховано гарантований фіолетовий лут і потрібний дамаг не перевищує ваш поріг.</i>\n\n"
            f"<i>Скористайтеся кнопками нижче:</i>"
        )

    def _build_sniper_menu_keyboard(self, chat_id: Optional[str] = None) -> dict:
        user_th = self.subscribers_db.get_user_threshold(chat_id) if chat_id else getattr(config, "SNIPER_MAX_DAMAGE", 75000)
        formatted_th = f"{user_th // 1000}k" if user_th < 1000000 else f"{user_th // 1000000}M"

        return {
            "inline_keyboard": [
                [
                    {"text": f"🎯 Снайпер (15–20 хв)", "callback_data": "sniper_cmd_snipe"},
                    {"text": "⚔️ Всі битви з фіолом", "callback_data": "sniper_cmd_battles"},
                ],
                [
                    {"text": f"⚙️ Змінити поріг: ≤ {formatted_th}", "callback_data": "sniper_menu_threshold"},
                ],
                [
                    {"text": "🔙 Головне меню", "callback_data": "menu_main"}
                ]
            ]
        }

    def _build_bounties_menu_text(self, chat_id: Optional[str] = None) -> str:
        user_prefs = self.subscribers_db.get_user_prefs(chat_id) if chat_id else {}
        contract_on = user_prefs.get("contract_alerts", False)
        min_rate = self.subscribers_db.get_user_min_bounty_rate(chat_id) if chat_id else 0.0
        rate_display = f"≥ {min_rate} 🪙 / 1k" if min_rate > 0 else "Всі (без обмежень)"
        focused = self.subscribers_db.get_user_focused_battle(chat_id) if chat_id else None

        if focused:
            return (
                f"💰 <b>Меню: Баунті за урон (Bounties)</b>\n\n"
                f"🎯 <b>Фокус на битві:</b> <b>⚔️ {focused['battle_name']}</b>\n"
                f"🔔 <b>Режим відстеження:</b> Тільки ця битва (будь-яка ставка)\n"
                f"🔕 <b>Фільтр спаму:</b> Інші битви приховані\n"
                f"💵 <b>Ваш поріг ставки (загальний):</b> <code>{rate_display}</code>\n\n"
                f"🎯 <i>Ви стежите виключно за битвою <b>{focused['battle_name']}</b>. "
                f"Бот сповістить про <b>БУДЬ-ЯКЕ баунті</b> в ній та не спамитиме іншими битвами.\n\n"
                f"Фокус скинеться автоматично, коли битва закінчиться, або ви можете зняти його вручну нижче.</i>"
            )

        return (
            f"💰 <b>Меню: Баунті за урон (Bounties)</b>\n\n"
            f"💵 <b>Ваш поріг ставки:</b> <code>{rate_display}</code>\n"
            f"💰 <b>Автосповіщення:</b> <b>{'🟢 УВІМКНЕНО' if contract_on else '🔴 ВИМКНЕНО'}</b>\n\n"
            f"💵 <i>У цьому розділі ви можете переглянути актуальні битви з грошовими нагородами "
            f"за кожну 1 000 набитого дамагу на стороні наймача, налаштувати поріг ставки або "
            f"<b>увімкнути фокус на одну битву</b>, щоб відстежувати тільки її без спаму іншими.</i>\n\n"
            f"<i>Скористайтеся кнопками нижче:</i>"
        )

    def _build_bounties_menu_keyboard(self, chat_id: Optional[str] = None) -> dict:
        min_rate = self.subscribers_db.get_user_min_bounty_rate(chat_id) if chat_id else 0.0
        rate_btn = f"≥ {min_rate} 🪙" if min_rate > 0 else "Всі"
        focused = self.subscribers_db.get_user_focused_battle(chat_id) if chat_id else None

        rows = [
            [
                {"text": "💰 Список активних баунті", "callback_data": "sniper_cmd_contracts"},
            ]
        ]

        if focused:
            b_name = focused.get('battle_name', 'битви')
            rows.append([
                {"text": f"❌ Скинути фокус ({b_name[:16]})", "callback_data": "bounty_unfocus"},
            ])
            rows.append([
                {"text": "🎯 Змінити битву фокусу", "callback_data": "menu_bounty_focus_select"},
            ])
        else:
            rows.append([
                {"text": "🎯 Слідкувати за однією битвою", "callback_data": "menu_bounty_focus_select"},
            ])

        rows.append([
            {"text": f"💵 Змінити поріг ставки: {rate_btn}", "callback_data": "sniper_menu_bounty_rate"},
        ])
        rows.append([
            {"text": "🔙 Головне меню", "callback_data": "menu_main"}
        ])

        return {"inline_keyboard": rows}

    def _build_auctions_menu_text(self, chat_id: Optional[str] = None) -> str:
        user_prefs = self.subscribers_db.get_user_prefs(chat_id) if chat_id else {}
        auction_on = user_prefs.get("auction_alerts", False)
        min_budget = self.subscribers_db.get_user_min_contract_budget(chat_id) if chat_id else 0.0
        budget_str = f"≥ {min_budget:g} 🪙" if min_budget > 0 else "Всі (без обмежень)"

        return (
            f"📜 <b>Меню: Найманські аукціони контрактів</b>\n\n"
            f"💰 <b>Ваш поріг бюджету:</b> <code>{budget_str}</code>\n"
            f"🔔 <b>Автосповіщення:</b> <b>{'🟢 УВІМКНЕНО' if auction_on else '🔴 ВИМКНЕНО'}</b>\n\n"
            f"⏱ <i>Коли країна виставляє новий контракт на битву, починається аукціон (тривалістю кілька хвилин). "
            f"Військові підрозділи роблять ставки, щоб забрати цей контракт собі.</i>\n\n"
            f"<i>Скористайтеся кнопками нижче:</i>"
        )

    def _build_auctions_menu_keyboard(self, chat_id: Optional[str] = None) -> dict:
        min_budget = self.subscribers_db.get_user_min_contract_budget(chat_id) if chat_id else 0.0
        budget_btn = f"≥ {min_budget:g} 🪙" if min_budget > 0 else "Всі"

        return {
            "inline_keyboard": [
                [
                    {"text": "📜 Всі контракти (Аукціони)", "callback_data": "cmd_list_auctions"},
                ],
                [
                    {"text": f"💰 Змінити поріг бюджету: {budget_btn}", "callback_data": "menu_auction_budget"},
                ],
                [
                    {"text": "🔙 Головне меню", "callback_data": "menu_main"}
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
            {"command": "contracts", "description": "📜 Всі активні контракти (аукціони)"},
            {"command": "auctions", "description": "📜 Аукціони контрактів для підрозділів"},
            {"command": "contract_budget", "description": "💰 Поріг бюджету контракту"},
            {"command": "auctions_on", "description": "🔔 Увімкнути пуші про аукціони"},
            {"command": "auctions_off", "description": "🔕 Вимкнути пуші про аукціони"},
            {"command": "bounties", "description": "💰 Активні баунті за урон"},
            {"command": "focus", "description": "🎯 Слідкувати за однією битвою"},
            {"command": "unfocus", "description": "❌ Скинути фокус відстеження"},
            {"command": "bounty_rate", "description": "💵 Мінімальна ставка баунті"},
            {"command": "bounties_on", "description": "💰 Увімкнути пуші про баунті"},
            {"command": "bounties_off", "description": "🔕 Вимкнути пуші про баунті"},
            {"command": "snipe", "description": "🎯 Битви на фінішній прямі (15-20 хв)"},
            {"command": "battles", "description": "⚔️ Всі активні битви з фіолом"},
            {"command": "threshold", "description": "⚙️ Налаштувати поріг урону"},
            {"command": "sniper_on", "description": "🔔 Увімкнути снайпер-сповіщення"},
            {"command": "sniper_off", "description": "🔕 Вимкнути снайпер-сповіщення"},
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

    def _build_contracts_keyboard(self, contracts: List[Dict[str, Any]], chat_id: Optional[str] = None) -> dict:
        focused = self.subscribers_db.get_user_focused_battle(chat_id) if chat_id else None
        rows = []
        seen_bids = set()
        focus_btns = []
        for c in contracts[:6]:
            bid = c.get('battleId')
            if not bid or bid in seen_bids:
                continue
            seen_bids.add(bid)
            reg = c.get('region', 'Битва')
            is_cur = focused and focused.get('battle_id') == bid
            icon = "✅" if is_cur else "🎯"
            focus_btns.append({"text": f"{icon} Фокус: {reg[:13]}", "callback_data": f"focus_battle_{bid}"})
            if len(focus_btns) == 2:
                rows.append(focus_btns)
                focus_btns = []
        if focus_btns:
            rows.append(focus_btns)

        if focused:
            rows.append([
                {"text": f"❌ Скинути фокус ({focused['battle_name'][:16]})", "callback_data": "bounty_unfocus"}
            ])
        else:
            rows.append([
                {"text": "🎯 Слідкувати за іншою битвою", "callback_data": "menu_bounty_focus_select"}
            ])

        rows.append([
            {"text": "🔙 Меню Баунті", "callback_data": "menu_bounties"}
        ])
        return {"inline_keyboard": rows}

    async def _get_contracts_data(self, chat_id: Optional[str] = None) -> Tuple[str, dict]:
        try:
            analyzer = get_shared_battle_analyzer()
            contracts = await analyzer.get_active_contracts()
            if not contracts:
                text = (
                    "💰 <b>WarEra · Активні Баунті (виплати за урон):</b>\n\n"
                    "<i>Наразі немає битв з активними виплатами за урон або пул монет вичерпано.</i>\n\n"
                    "💡 <i>Ви можете обрати активну битву через кнопку нижче, щоб отримувати сповіщення, "
                    "щойно в ній з'явиться будь-яке нове баунті!</i>"
                )
                kb = {
                    "inline_keyboard": [
                        [{"text": "🎯 Слідкувати за битвою (фокус)", "callback_data": "menu_bounty_focus_select"}],
                        [{"text": "🔙 Меню Баунті", "callback_data": "menu_bounties"}]
                    ]
                }
                return text, kb

            user_min = self.subscribers_db.get_user_min_bounty_rate(chat_id) if chat_id else 0.0
            focused = self.subscribers_db.get_user_focused_battle(chat_id) if chat_id else None

            msg = "💰 <b>WarEra · Активні Баунті за урон (Bounties):</b>\n\n"
            if focused:
                msg += f"🎯 <i>Ваш поточний фокус: <b>{focused['battle_name']}</b> (сповіщення про всі баунті в ній)</i>\n\n"
            elif user_min > 0:
                msg += f"<i>(Ваш фільтр сповіщень: від ≥ {user_min} 🪙 / 1k dmg)</i>\n\n"

            for idx, c in enumerate(contracts[:8], 1):
                reg = c['region']
                btype = "Війна" if c['type'] == 'war' else "Повстання"
                side_tag = "🔴 АТАКА" if c['side'] == 'attacker' else "🛡 ОБОРОНА"
                country = f"{c['flag']} {c['country']}"
                rate = c['ratePer1k']
                pool = c['pool']
                sniper_tag = " 🎯 [15-20 хв]" if c['isSniperWindow'] else ""
                is_foc = focused and focused.get('battle_id') == c['battleId']
                focus_tag = " 🎯 [У ФОКУСІ]" if is_foc else ""

                msg += (
                    f"<b>{idx}. {reg}</b> (<i>{btype}</i>){sniper_tag}{focus_tag}\n"
                    f"   Сторона: <b>{side_tag}</b> ({country})\n"
                    f"   💵 <b>Ставка:</b> <code>{rate} монет / 1k dmg</code>\n"
                    f"   🏦 <b>Залишок пулу:</b> <code>{pool:,} монет</code>\n"
                    f"   👉 <a href=\"{c['wareraUrl']}\">Перейти до битви ↗</a>\n\n"
                ).replace(",", " ")

            kb = self._build_contracts_keyboard(contracts, chat_id=chat_id)
            return msg, kb
        except Exception as e:
            logger.error(f"Error in Sniper Bot get_contracts_data: {e}")
            return f"⚠️ <b>Помилка аналізу баунті:</b> <code>{e}</code>", {"inline_keyboard": [[{"text": "🔙 Меню Баунті", "callback_data": "menu_bounties"}]]}

    async def _get_contracts_text(self, chat_id: Optional[str] = None) -> str:
        txt, _ = await self._get_contracts_data(chat_id=chat_id)
        return txt

    async def _build_focus_select_screen(self, chat_id: Optional[str] = None, page: int = 0) -> Tuple[str, dict]:
        try:
            analyzer = get_shared_battle_analyzer()
            active_list = await analyzer.get_active_battles_for_focus()
        except Exception as e:
            logger.error(f"Error getting active battles for focus: {e}")
            active_list = []

        focused = self.subscribers_db.get_user_focused_battle(chat_id) if chat_id else None

        cur_focus_text = ""
        if focused:
            cur_focus_text = f"🎯 <b>Поточний фокус:</b> <b>⚔️ {focused['battle_name']}</b>\n\n"

        page_size = 10
        total_items = len(active_list)
        total_pages = max(1, (total_items + page_size - 1) // page_size)
        page = max(0, min(page, total_pages - 1))
        slice_start = page * page_size
        slice_end = slice_start + page_size
        page_battles = active_list[slice_start:slice_end]

        text = (
            f"🎯 <b>Вибір битви для відстеження Баунті (Всього: {total_items}):</b>\n\n"
            f"{cur_focus_text}"
            f"<i>Оберіть битву зі списку нижче (стор. {page + 1} з {total_pages}) або напишіть назву:</i>\n"
            f"<code>/focus &lt;назва або посилання&gt;</code> (наприклад: <code>/focus Agadez</code>)\n\n"
            f"🔔 <b>Особливості режиму фокусу:</b>\n"
            f"• Ви отримуватимете пуші про <b>БУДЬ-ЯКЕ баунті</b> у вибраній битві.\n"
            f"• Інші битви <b>не спамитимуть</b>.\n"
            f"• Щойно битва завершиться, фокус <b>автоматично зніметься</b>.\n"
            f"• Ви можете зняти фокус у будь-який момент кнопкою."
        )

        rows = []
        btn_row = []
        for b in page_battles:
            bid = b['battleId']
            rname = b['regionName']
            if b['hasBounty']:
                rate_str = f"{b['maxBountyRate']}🪙"
                label = f"💰 {rname[:13]} ({rate_str})"
            else:
                label = f"⚔️ {rname[:17]}"

            if focused and focused.get('battle_id') == bid:
                label = f"✅ {label}"

            btn_row.append({"text": label, "callback_data": f"focus_battle_{bid}"})
            if len(btn_row) == 2:
                rows.append(btn_row)
                btn_row = []
        if btn_row:
            rows.append(btn_row)

        # Pagination controls
        if total_pages > 1:
            nav_row = []
            if page > 0:
                nav_row.append({"text": "⬅️ Назад", "callback_data": f"menu_bounty_focus_p_{page - 1}"})
            nav_row.append({"text": f"📄 {page + 1}/{total_pages}", "callback_data": "noop"})
            if page < total_pages - 1:
                nav_row.append({"text": "Вперед ➡️", "callback_data": f"menu_bounty_focus_p_{page + 1}"})
            rows.append(nav_row)

        if focused:
            rows.append([
                {"text": f"❌ Скинути поточний фокус ({focused['battle_name'][:16]})", "callback_data": "bounty_unfocus"}
            ])

        rows.append([
            {"text": "🔄 Оновити", "callback_data": f"menu_bounty_focus_p_{page}"},
            {"text": "🔙 Назад до меню баунті", "callback_data": "menu_bounties"}
        ])

        return text, {"inline_keyboard": rows}

    async def _get_auctions_text(self, chat_id: Optional[str] = None) -> str:
        try:
            analyzer = get_shared_battle_analyzer()
            auctions = await analyzer.get_active_contract_auctions()
            if not auctions:
                return (
                    "📜 <b>WarEra · Активні Найманські Аукціони Контрактів:</b>\n\n"
                    "<i>Наразі немає відкритих аукціонів контрактів від країн.</i>\n\n"
                    "💡 <i>Коли країна виставляє контракт на битву, аукціон триває лише кілька хвилин! "
                    "Підрозділи змагаються ставками за право забрати контракт. Бот надішле сповіщення миттєво, щойно з'явиться новий лот.</i>"
                )

            user_min = self.subscribers_db.get_user_min_contract_budget(chat_id) if chat_id else 0.0

            msg = "📜 <b>WarEra · Активні Найманські Аукціони Контрактів:</b>\n\n"
            if user_min > 0:
                msg += f"<i>(Ваш фільтр бюджету: ≥ {user_min:g} 🪙)</i>\n\n"

            for idx, a in enumerate(auctions[:8], 1):
                reg = a['region']
                btype = "Війна" if a['type'] == 'war' else "Повстання"
                side_tag = "🔴 АТАКА" if a['side'] == 'attacker' else "🛡 ОБОРОНА"
                country = f"{a['flag']} {a['country']}"
                budget = a['budget']
                min_dmg = a['minimumDamage']
                rate = a['ratePer1k']
                r_num = a['roundNumber']
                bids = a['bidsCount']

                time_sec = int(a.get('timeRemainingSec', 0))
                if time_sec > 0:
                    mins = time_sec // 60
                    secs = time_sec % 60
                    time_str = f"{mins}хв {secs:02d}с"
                else:
                    time_str = "завершується"

                min_dmg_str = f"{min_dmg:,}".replace(",", " ") if min_dmg > 0 else "0"

                msg += (
                    f"<b>{idx}. {reg}</b> (<i>{btype}</i> • Р#{r_num})\n"
                    f"   Сторона: <b>{side_tag}</b> ({country})\n"
                    f"   💰 <b>Бюджет:</b> <code>{budget:g} монет</code>\n"
                    f"   ⚔️ <b>Мін. урон:</b> <code>{min_dmg_str} dmg</code>\n"
                    f"   💵 <b>Ставка:</b> <code>{rate} 🪙 / 1k dmg</code>\n"
                    f"   ⏱ <b>До кінця торгів:</b> <code>~{time_str}</code> (ставок: {bids})\n"
                    f"   👉 <a href=\"{a['wareraUrl']}\">Відкрити аукціон у грі ↗</a>\n\n"
                )

            msg += "💡 <i>Щоб ваш підрозділ взяв контракт, встигніть зробити ставку до завершення таймера!</i>"
            return msg
        except Exception as e:
            logger.error(f"Error in Sniper Bot get_auctions_text: {e}")
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

            if data == "menu_main" or data == "sniper_cmd_status":
                await self.answer_callback(cb_id, "Головне меню")
                if msg_id:
                    await self.edit_message(chat_id, msg_id, self._build_panel_text(chat_id), self._build_keyboard(chat_id))
                return

            elif data == "menu_sniper":
                await self.answer_callback(cb_id, "🎯 Розділ: Снайпер фіолу")
                if msg_id:
                    await self.edit_message(chat_id, msg_id, self._build_sniper_menu_text(chat_id), self._build_sniper_menu_keyboard(chat_id))
                return

            elif data == "menu_bounties":
                await self.answer_callback(cb_id, "💰 Розділ: Баунті")
                if msg_id:
                    await self.edit_message(chat_id, msg_id, self._build_bounties_menu_text(chat_id), self._build_bounties_menu_keyboard(chat_id))
                return

            elif data == "menu_auctions":
                await self.answer_callback(cb_id, "📜 Розділ: Контракти")
                if msg_id:
                    await self.edit_message(chat_id, msg_id, self._build_auctions_menu_text(chat_id), self._build_auctions_menu_keyboard(chat_id))
                return

            elif data == "cmd_list_auctions":
                await self.answer_callback(cb_id, "📜 Шукаю активні аукціони контрактів...")
                txt = await self._get_auctions_text(chat_id=chat_id)
                await self.send_message(chat_id, txt)
                return

            elif data == "sniper_toggle_alerts":
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
                await self.answer_callback(cb_id, f"💰 Баунті: {status_txt}")
                if msg_id:
                    await self.edit_message(chat_id, msg_id, self._build_panel_text(chat_id), self._build_keyboard(chat_id))
                return

            elif data == "sniper_toggle_auctions":
                curr = self.subscribers_db.get_user_prefs(chat_id).get("auction_alerts", False)
                new_val = self.subscribers_db.set_auction_alerts(chat_id, not curr)
                status_txt = "🟢 УВІМКНЕНО" if new_val else "🔴 ВИМКНЕНО"
                await self.answer_callback(cb_id, f"📜 Контракти: {status_txt}")
                if msg_id:
                    await self.edit_message(chat_id, msg_id, self._build_panel_text(chat_id), self._build_keyboard(chat_id))
                return

            elif data == "menu_auction_budget":
                curr_budget = self.subscribers_db.get_user_min_contract_budget(chat_id)
                budget_str = f"≥ {curr_budget:g} 🪙" if curr_budget > 0 else "Всі (без обмежень)"
                ab_text = (
                    f"💰 <b>Налаштування мінімального бюджету Контракту</b>\n\n"
                    f"Ваш поточний мінімальний поріг: <b>{budget_str}</b>\n\n"
                    f"Бот надсилатиме сповіщення лише про ті аукціони, бюджет яких не менший за цей поріг.\n\n"
                    f"Оберіть бажаний поріг або введіть команду вручну:\n"
                    f"• <code>/contract_budget 50</code>\n"
                    f"• <code>/cb 100</code>"
                )
                ab_kb = {
                    "inline_keyboard": [
                        [
                            {"text": "Всі (0 🪙)", "callback_data": "set_cb_0"},
                            {"text": "≥ 25 🪙", "callback_data": "set_cb_25"},
                            {"text": "≥ 50 🪙", "callback_data": "set_cb_50"},
                        ],
                        [
                            {"text": "≥ 100 🪙", "callback_data": "set_cb_100"},
                            {"text": "≥ 200 🪙", "callback_data": "set_cb_200"},
                            {"text": "≥ 500 🪙", "callback_data": "set_cb_500"},
                        ],
                        [
                            {"text": "🔙 Назад до меню контрактів", "callback_data": "menu_auctions"}
                        ]
                    ]
                }
                if msg_id:
                    await self.edit_message(chat_id, msg_id, ab_text, ab_kb)
                return

            elif data.startswith("set_cb_"):
                new_budget = float(data.replace("set_cb_", ""))
                self.subscribers_db.set_user_min_contract_budget(chat_id, new_budget)
                budget_disp = f"≥ {new_budget:g} 🪙" if new_budget > 0 else "Всі контракти"
                await self.answer_callback(cb_id, f"Поріг бюджету: {budget_disp}")
                if msg_id:
                    await self.edit_message(chat_id, msg_id, self._build_auctions_menu_text(chat_id), self._build_auctions_menu_keyboard(chat_id))
                return

            elif data == "sniper_menu_bounty_rate":
                curr_rate = self.subscribers_db.get_user_min_bounty_rate(chat_id)
                rate_str = f"≥ {curr_rate} 🪙 / 1k" if curr_rate > 0 else "Всі (без обмежень)"
                br_text = (
                    f"💵 <b>Налаштування мінімальної ставки Баунті</b>\n\n"
                    f"Ваш поточний мінімальний поріг: <b>{rate_str}</b>\n\n"
                    f"Бот надсилатиме сповіщення лише про ті битви, де виплата за 1 000 урону не менша за цей поріг.\n\n"
                    f"Оберіть бажаний поріг або введіть команду вручну:\n"
                    f"• <code>/bounty_rate 0.07</code>\n"
                    f"• <code>/rate 0.05</code>"
                )
                br_kb = {
                    "inline_keyboard": [
                        [
                            {"text": "≥ 0.02 🪙", "callback_data": "set_br_0.02"},
                            {"text": "≥ 0.03 🪙", "callback_data": "set_br_0.03"},
                            {"text": "≥ 0.05 🪙", "callback_data": "set_br_0.05"},
                        ],
                        [
                            {"text": "≥ 0.07 🪙", "callback_data": "set_br_0.07"},
                            {"text": "≥ 0.10 🪙", "callback_data": "set_br_0.10"},
                            {"text": "Всі (0.0)", "callback_data": "set_br_0.0"},
                        ],
                        [
                            {"text": "🔙 Назад до меню баунті", "callback_data": "menu_bounties"}
                        ]
                    ]
                }
                if msg_id:
                    await self.edit_message(chat_id, msg_id, br_text, br_kb)
                return

            elif data.startswith("set_br_"):
                new_rate = float(data.replace("set_br_", ""))
                self.subscribers_db.set_user_min_bounty_rate(chat_id, new_rate)
                rate_disp = f"≥ {new_rate} 🪙 / 1k" if new_rate > 0 else "Всі баунті"
                await self.answer_callback(cb_id, f"Поріг баунті: {rate_disp}")
                if msg_id:
                    await self.edit_message(chat_id, msg_id, self._build_bounties_menu_text(chat_id), self._build_bounties_menu_keyboard(chat_id))
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
                await self.answer_callback(cb_id, "💰 Шукаю активні баунті...")
                txt, kb = await self._get_contracts_data(chat_id=chat_id)
                await self.send_message(chat_id, txt, reply_markup=kb)
                return

            elif data == "menu_bounty_focus_select":
                await self.answer_callback(cb_id, "🎯 Завантажую активні битви...")
                text, kb = await self._build_focus_select_screen(chat_id=chat_id, page=0)
                if msg_id:
                    await self.edit_message(chat_id, msg_id, text, kb)
                else:
                    await self.send_message(chat_id, text, kb)
                return

            elif data.startswith("menu_bounty_focus_p_"):
                p_idx = int(data.replace("menu_bounty_focus_p_", "").strip())
                await self.answer_callback(cb_id)
                text, kb = await self._build_focus_select_screen(chat_id=chat_id, page=p_idx)
                if msg_id:
                    await self.edit_message(chat_id, msg_id, text, kb)
                else:
                    await self.send_message(chat_id, text, kb)
                return

            elif data == "noop":
                await self.answer_callback(cb_id)
                return

            elif data.startswith("focus_battle_"):
                b_id = data.replace("focus_battle_", "").strip()
                analyzer = get_shared_battle_analyzer()
                active_list = await analyzer.get_active_battles_for_focus()
                b_match = next((b for b in active_list if b.get('battleId') == b_id), None)
                reg_name = b_match.get('regionName', 'Битва') if b_match else "Битва"

                self.subscribers_db.set_user_focused_battle(chat_id, b_id, reg_name)
                await self.answer_callback(cb_id, f"🎯 Фокус: {reg_name}")

                bounty_info = ""
                if b_match and b_match.get('hasBounty'):
                    bounty_info = f"💵 <b>Поточна ставка:</b> <code>{b_match.get('maxBountyRate')} монет / 1k dmg</code>\n"

                confirm_text = (
                    f"✅ <b>Фокус на битву активовано!</b>\n\n"
                    f"⚔️ <b>Битва:</b> <b>{reg_name}</b>\n"
                    f"{bounty_info}"
                    f"🎯 <b>Режим відстеження:</b> Сповіщення про <b>БУДЬ-ЯКЕ баунті</b> у цій битві\n"
                    f"🔕 <b>Фільтр спаму:</b> Інші битви не надсилатимуться\n\n"
                    f"<i>Фокус автоматично скинеться, коли битва закінчиться, або ви можете скинути його вручну нижче.</i>"
                )
                confirm_kb = {
                    "inline_keyboard": [
                        [{"text": "💰 Меню Баунті", "callback_data": "menu_bounties"}],
                        [{"text": f"❌ Скинути фокус ({reg_name[:16]})", "callback_data": "bounty_unfocus"}],
                        [{"text": "⚔️ Відкрити битву на WarEra ↗", "url": f"https://app.warera.io/battle/{b_id}"}]
                    ]
                }
                if msg_id:
                    await self.edit_message(chat_id, msg_id, confirm_text, confirm_kb)
                else:
                    await self.send_message(chat_id, confirm_text, confirm_kb)
                return

            elif data == "bounty_unfocus":
                focused = self.subscribers_db.get_user_focused_battle(chat_id)
                prev_name = focused.get("battle_name") if focused else "битви"
                self.subscribers_db.clear_user_focused_battle(chat_id)
                await self.answer_callback(cb_id, "🎯 Фокус битви знято")
                if msg_id:
                    await self.edit_message(
                        chat_id,
                        msg_id,
                        self._build_bounties_menu_text(chat_id),
                        self._build_bounties_menu_keyboard(chat_id)
                    )
                else:
                    await self.send_message(
                        chat_id,
                        f"🎯 <b>Фокус знято!</b> Відстеження битви {prev_name} припинено. Відновлено стандартні налаштування сповіщень.",
                        self._build_bounties_menu_keyboard(chat_id)
                    )
                return

            elif data == "sniper_menu_threshold":
                curr_th = self.subscribers_db.get_user_threshold(chat_id)
                th_text = (
                    f"⚙️ <b>Налаштування вашого особистого порогу урону</b>\n\n"
                    f"Ваш поточний поріг: <b>{curr_th:,} dmg</b>\n\n"
                    f"Бот відсіює битви особисто для вас і надсилає пуші лише тоді, коли для фіолетового дропу потрібно не більше цього значення.\n\n"
                    f"Оберіть бажаний поріг або введіть <code>/threshold 75k</code>:"
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
                            {"text": "🔙 Назад до снайпера", "callback_data": "menu_sniper"},
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
                    await self.edit_message(chat_id, msg_id, self._build_sniper_menu_text(chat_id), self._build_sniper_menu_keyboard(chat_id))
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

            elif first_word in ("/bounties", "/баунті") or clean_cmd in ("bounties", "баунті"):
                await self.send_message(chat_id, "💰 <i>Шукаю відкриті баунті з оплатою за урон...</i>")
                txt, kb = await self._get_contracts_data(chat_id=chat_id)
                await self.send_message(chat_id, txt, reply_markup=kb)

            elif first_word in ("/contracts", "/контракти", "/auctions", "/аукціони") or clean_cmd in ("contracts", "контракти", "auctions", "аукціони"):
                await self.send_message(chat_id, "📜 <i>Шукаю активні найманські аукціони контрактів...</i>")
                txt = await self._get_auctions_text(chat_id=chat_id)
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

            elif first_word in ("/bounty_rate", "/rate", "/баунті_рейт", "/рейт") or clean_cmd in ("bounty_rate", "rate", "баунті_рейт", "рейт"):
                if len(words) > 1:
                    raw_val = words[1].replace(",", ".")
                    try:
                        val = float(raw_val)
                        if val < 0:
                            val = 0.0
                        self.subscribers_db.set_user_min_bounty_rate(chat_id, val)
                        disp = f"≥ {val} 🪙 / 1k" if val > 0 else "Всі (без обмежень)"
                        await self.send_message(
                            chat_id,
                            f"✅ <b>Ваш поріг баунті оновлено:</b> <code>{disp}</code>\n\n"
                            f"Тепер ви отримуватимете пуш-сповіщення тільки про баунті з виплатою від {val} монет за 1k урону."
                        )
                    except ValueError:
                        await self.send_message(chat_id, "⚠️ Будь ласка, вкажіть число, наприклад: <code>/bounty_rate 0.07</code> або <code>/rate 0.05</code>")
                else:
                    curr_rate = self.subscribers_db.get_user_min_bounty_rate(chat_id)
                    disp = f"≥ {curr_rate} 🪙 / 1k" if curr_rate > 0 else "Всі (без обмежень)"
                    await self.send_message(
                        chat_id,
                        f"💵 <b>Ваш поточний мінімальний поріг баунті:</b> <code>{disp}</code>\n\n"
                        f"Щоб змінити, введіть: <code>/bounty_rate 0.07</code> або оберіть значення в меню /start."
                    )

            elif first_word in ("/bounties_on", "/баунті_вкл") or clean_cmd in ("bounties_on", "баунті_вкл"):
                self.subscribers_db.set_contract_alerts(chat_id, True)
                curr_rate = self.subscribers_db.get_user_min_bounty_rate(chat_id)
                rate_disp = f"≥ {curr_rate} 🪙 / 1k" if curr_rate > 0 else "від 0.01 🪙"
                await self.send_message(
                    chat_id,
                    f"💰 <b>Баунті на урон:</b> Сповіщення <b>УВІМКНЕНО 🟢</b>\n\n"
                    f"🎯 <b>Ваш фільтр ставки:</b> <code>{rate_disp}</code>\n"
                    f"Ви отримуватимете особисте сповіщення, щойно з'явиться баунті з виплатою від {rate_disp}."
                )

            elif first_word in ("/bounties_off", "/баунті_викл") or clean_cmd in ("bounties_off", "баунті_викл"):
                self.subscribers_db.set_contract_alerts(chat_id, False)
                await self.send_message(
                    chat_id,
                    "💰 <b>Баунті на урон:</b> Сповіщення <b>ВИМКНЕНО 🔴</b>\n\n"
                    "Автоматичні пуші вимкнено. Ви можете перевірити активні виплати в будь-який час через /bounties."
                )

            elif first_word in ("/focus", "/bounty_focus", "/фокус") or clean_cmd in ("focus", "bounty_focus", "фокус"):
                if len(words) > 1:
                    raw_arg = " ".join(words[1:]).strip()
                    import re
                    url_match = re.search(r"battle/([a-f0-9]{24})", raw_arg)
                    target_bid = url_match.group(1) if url_match else None
                    if not target_bid and re.match(r"^[a-f0-9]{24}$", raw_arg):
                        target_bid = raw_arg

                    analyzer = get_shared_battle_analyzer()
                    active_list = await analyzer.get_active_battles_for_focus()

                    matched_battle = None
                    if target_bid:
                        matched_battle = next((b for b in active_list if b.get('battleId') == target_bid), None)
                        if not matched_battle:
                            raw_b = await analyzer.fetch_active_battles()
                            b_raw = next((b for b in raw_b if b.get('_id') == target_bid), None)
                            if b_raw:
                                reg_id = b_raw.get('defender', {}).get('region')
                                reg_name = analyzer._regions_cache.get(reg_id, {}).get('name', 'Битва')
                                matched_battle = {
                                    'battleId': target_bid,
                                    'regionName': reg_name,
                                    'hasBounty': False,
                                    'wareraUrl': f"https://app.warera.io/battle/{target_bid}"
                                }
                    else:
                        q = raw_arg.lower()
                        CYR_TO_LAT = {
                            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'ґ': 'g', 'д': 'd', 'е': 'e', 'є': 'ye',
                            'ж': 'zh', 'з': 'z', 'и': 'y', 'і': 'i', 'ї': 'yi', 'й': 'y', 'к': 'k', 'л': 'l',
                            'м': 'm', 'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
                            'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch', 'ь': '', 'ю': 'yu', 'я': 'ya'
                        }
                        q_lat = ''.join(CYR_TO_LAT.get(c, c) for c in q)

                        for b in active_list:
                            reg_l = b.get('regionName', '').lower()
                            att_l = b.get('attackerCountry', '').lower()
                            def_l = b.get('defenderCountry', '').lower()
                            if (q in reg_l or q_lat in reg_l or 
                                q in att_l or q_lat in att_l or 
                                q in def_l or q_lat in def_l):
                                matched_battle = b
                                break

                    if matched_battle:
                        bid = matched_battle['battleId']
                        bname = matched_battle['regionName']
                        self.subscribers_db.set_user_focused_battle(chat_id, bid, bname)
                        bounty_info = ""
                        if matched_battle.get('hasBounty'):
                            bounty_info = f"💵 <b>Поточна ставка:</b> <code>{matched_battle.get('maxBountyRate')} монет / 1k dmg</code>\n"

                        confirm_text = (
                            f"✅ <b>Фокус на битву активовано!</b>\n\n"
                            f"⚔️ <b>Битва:</b> <b>{bname}</b>\n"
                            f"{bounty_info}"
                            f"🎯 <b>Режим відстеження:</b> Сповіщення про <b>БУДЬ-ЯКЕ баунті</b> у цій битві\n"
                            f"🔕 <b>Фільтр спаму:</b> Інші битви не надсилатимуться\n\n"
                            f"<i>Фокус автоматично скинеться, коли битва закінчиться, або за командою /unfocus.</i>"
                        )
                        confirm_kb = {
                            "inline_keyboard": [
                                [{"text": "💰 Меню Баунті", "callback_data": "menu_bounties"}],
                                [{"text": f"❌ Скинути фокус ({bname[:16]})", "callback_data": "bounty_unfocus"}],
                                [{"text": "⚔️ Відкрити битву на WarEra ↗", "url": matched_battle['wareraUrl']}]
                            ]
                        }
                        await self.send_message(chat_id, confirm_text, confirm_kb)
                    else:
                        await self.send_message(
                            chat_id,
                            f"⚠️ Не вдалося знайти активну битву за запитом: <code>{raw_arg}</code>\n"
                            f"Оберіть битву зі списку нижче:",
                        )
                        text, kb = await self._build_focus_select_screen(chat_id=chat_id)
                        await self.send_message(chat_id, text, kb)
                else:
                    text, kb = await self._build_focus_select_screen(chat_id=chat_id)
                    await self.send_message(chat_id, text, kb)

            elif first_word in ("/unfocus", "/bounty_unfocus", "/розфокус") or clean_cmd in ("unfocus", "bounty_unfocus", "розфокус"):
                focused = self.subscribers_db.get_user_focused_battle(chat_id)
                prev_name = focused.get("battle_name") if focused else "битви"
                self.subscribers_db.clear_user_focused_battle(chat_id)
                await self.send_message(
                    chat_id,
                    f"🎯 <b>Фокус відстеження битви знято.</b>\n\n"
                    f"Більше не відстежуємо <b>{prev_name}</b>.\n"
                    f"Відновлено стандартні налаштування сповіщень про баунті.",
                    self._build_bounties_menu_keyboard(chat_id)
                )

            elif first_word in ("/contract_budget", "/cb", "/бюджет") or clean_cmd in ("contract_budget", "cb", "бюджет"):
                if len(words) > 1:
                    raw_val = words[1].replace(",", ".")
                    try:
                        val = float(raw_val)
                        if val < 0:
                            val = 0.0
                        self.subscribers_db.set_user_min_contract_budget(chat_id, val)
                        disp = f"≥ {val:g} 🪙" if val > 0 else "Всі (без обмежень)"
                        await self.send_message(
                            chat_id,
                            f"✅ <b>Ваш поріг бюджету контракту оновлено:</b> <code>{disp}</code>\n\n"
                            f"Тепер ви отримуватимете пуш-сповіщення тільки про аукціони з бюджетом від {val:g} монет."
                        )
                    except ValueError:
                        await self.send_message(chat_id, "⚠️ Будь ласка, вкажіть число, наприклад: <code>/contract_budget 50</code> або <code>/cb 100</code>")
                else:
                    curr_budget = self.subscribers_db.get_user_min_contract_budget(chat_id)
                    disp = f"≥ {curr_budget:g} 🪙" if curr_budget > 0 else "Всі (без обмежень)"
                    await self.send_message(
                        chat_id,
                        f"💰 <b>Ваш поточний мінімальний поріг бюджету контракту:</b> <code>{disp}</code>\n\n"
                        f"Щоб змінити, введіть: <code>/contract_budget 50</code> або оберіть значення в меню /start."
                    )

            elif first_word in ("/auctions_on", "/contracts_on", "/контракти_вкл") or clean_cmd in ("auctions_on", "contracts_on", "контракти_вкл"):
                self.subscribers_db.set_auction_alerts(chat_id, True)
                curr_budget = self.subscribers_db.get_user_min_contract_budget(chat_id)
                budget_disp = f"≥ {curr_budget:g} 🪙" if curr_budget > 0 else "від 0 🪙"
                await self.send_message(
                    chat_id,
                    f"📜 <b>Найманські аукціони контрактів:</b> Сповіщення <b>УВІМКНЕНО 🟢</b>\n\n"
                    f"💰 <b>Ваш фільтр бюджету:</b> <code>{budget_disp}</code>\n"
                    f"Ви отримуватимете особисте сповіщення, щойно країна виставить контракт на аукціон!"
                )

            elif first_word in ("/auctions_off", "/contracts_off", "/контракти_викл") or clean_cmd in ("auctions_off", "contracts_off", "контракти_викл"):
                self.subscribers_db.set_auction_alerts(chat_id, False)
                await self.send_message(
                    chat_id,
                    "📜 <b>Найманські аукціони контрактів:</b> Сповіщення <b>ВИМКНЕНО 🔴</b>\n\n"
                    "Автоматичні пуші вимкнено. Ви можете перевірити активні аукціони в будь-який час через /contracts."
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
                    a_ico = "📜" if u.get("auction_alerts", False) else "⚪"
                    sub_text += f"• <code>{cid}</code>: <b>{name}</b> ({uname}) [{s_ico} {c_ico} {a_ico}]\n"
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
