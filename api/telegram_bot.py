import asyncio
import logging
from typing import Optional, List, Dict, Any
import httpx

import config
from equipment_data import QUALITY_TIERS, ALL_QUALITIES, normalize_quality_key, EQUIPMENT_METADATA
from subscribers_db import SubscribersDB
from telegram_base import BaseTelegramBot

logger = logging.getLogger("WarEraTelegramBot")

class TelegramBotController(BaseTelegramBot):
    """
    Handles interactive Telegram Bot commands and callback queries for WarEra Scanner and Battle Sniper.
    Allows up to hundreds of users to independently receive private 1-on-1 alerts (Market deals & Battle Sniping)
    and configure their notification preferences without any shared groups.
    """
    def __init__(self, scanner_app):
        super().__init__(token=config.TELEGRAM_BOT_TOKEN)
        self.scanner = scanner_app
        self.allowed_chat_ids = set(config.TELEGRAM_CHAT_IDS)
        self.subscribers_db = SubscribersDB()
        self.offset = 0
        self.is_running = False

    def _is_admin(self, user_id: Any, chat_id: Any = None) -> bool:
        """Checks if user has administrative rights to change scanner global parameters."""
        if not self.allowed_chat_ids:
            return True
        return str(user_id) in self.allowed_chat_ids or (chat_id is not None and str(chat_id) in self.allowed_chat_ids)

    def _is_authorized(self, user_id: Any, chat_id: Any) -> bool:
        if not self.allowed_chat_ids:
            return True
        return str(user_id) in self.allowed_chat_ids or str(chat_id) in self.allowed_chat_ids

    def _build_control_panel_text(self, chat_id: Optional[str] = None) -> str:
        is_paused = getattr(self.scanner, "is_paused", False)
        status_emoji = "⏸" if is_paused else "🟢"
        status_text = "ПАУЗА (Зупинено)" if is_paused else "АКТИВНИЙ (Сканує)"
        last_scan = getattr(self.scanner, "last_scan_time", None) or "ще не проводилося"
        cycles = getattr(self.scanner, "cycle_count", 0)
        alerts = getattr(self.scanner, "total_alerts_sent", 0)
        items_count = len(getattr(self.scanner, "equipment_list", config.EQUIPMENT_TO_MONITOR))
        interval = getattr(self.scanner, "scan_interval", config.EQUIPMENT_SCAN_INTERVAL)
        qualities = getattr(self.scanner, "active_qualities", config.EQUIPMENT_QUALITIES)
        q_emojis = " ".join(f"{QUALITY_TIERS[q]['emoji']}" for q in ALL_QUALITIES if q in qualities)
        roll_threshold = getattr(self.scanner.analyzer, "god_roll_threshold", config.EQUIPMENT_GOD_ROLL_THRESHOLD)

        pricing_mode = getattr(self.scanner, "pricing_mode", config.PRICING_MODE)
        mode_label = "⚡ Реальний час (ордери)" if pricing_mode == "live" else "📜 3-денна історія (база)"

        return (
            f"🤖 <b>Панель сканера спорядження WarEra</b> (<code>v{config.APP_VERSION}</code>)\n\n"
            f"📡 <b>Стан сканера:</b> {status_emoji} <b>{status_text}</b>\n"
            f"🔄 <b>Режим оцінки:</b> <b>{mode_label}</b>\n"
            f"⏱ <b>Інтервал перевірки:</b> <code>{interval} сек</code>\n"
            f"💎 <b>Активні якості:</b> {q_emojis} <i>({len(qualities)} з 6)</i>\n"
            f"📦 <b>Предметів на моніторингу:</b> <code>{items_count} шт.</code>\n"
            f"🎯 <b>Поріг вигоди:</b> <code>{config.EQUIPMENT_MIN_DISCOUNT}%</code>\n"
            f"🌟 <b>Поріг топ-ролу:</b> <code>{roll_threshold}%</code>\n"
            f"⏰ <b>Останнє сканування:</b> <code>{last_scan}</code> (цикл #{cycles})\n"
            f"🔔 <b>Виявлено пропозицій:</b> <code>{alerts}</code>\n\n"
            f"<i>Керуйте сканером ринку за допомогою кнопок нижче:</i>"
        )

    def _build_keyboard(self, chat_id: Optional[str] = None, is_admin: Optional[bool] = None) -> dict:
        is_paused = getattr(self.scanner, "is_paused", False)
        if is_paused:
            toggle_btn = {"text": "▶️ Запустити сканер", "callback_data": "cmd_start"}
        else:
            toggle_btn = {"text": "⏸ Зупинити сканер", "callback_data": "cmd_stop"}

        pricing_mode = getattr(self.scanner, "pricing_mode", config.PRICING_MODE)
        mode_btn_text = "🔄 Режим: ⚡ Live" if pricing_mode == "live" else "🔄 Режим: 📜 Історія"

        return {
            "inline_keyboard": [
                [toggle_btn],
                [
                    {"text": mode_btn_text, "callback_data": "cmd_mode_menu"},
                    {"text": "⏱ Змінити частоту", "callback_data": "cmd_interval_menu"}
                ],
                [
                    {"text": "💎 Якість предметів", "callback_data": "cmd_quality_menu"},
                    {"text": "🧹 Очистити чат", "callback_data": "cmd_clear"}
                ],
                [
                    {"text": "🔍 Сканувати зараз", "callback_data": "cmd_scan"},
                    {"text": "🔄 Оновити статус", "callback_data": "cmd_status"}
                ],
                [
                    {"text": "📊 Статистика", "callback_data": "cmd_stats"}
                ]
            ]
        }

    def _build_mode_menu_text(self) -> str:
        pricing_mode = getattr(self.scanner, "pricing_mode", config.PRICING_MODE)
        mode_label = "⚡ Реальний час (ордери)" if pricing_mode == "live" else "📜 3-денна історія (база)"
        return (
            f"⚙️ <b>Налаштування способу розрахунку вартості та вигоди</b>\n\n"
            f"Поточний активний режим: <b>{mode_label}</b>\n\n"
            f"Оберіть метод оцінки вигідності пропозицій:\n\n"
            f"• <b>⚡ Реальний час (Live Order Book):</b>\n"
            f"  Оцінює ціну за поточними відкритими ордерами на ринку прямо зараз. Порівнює предмет з іншими лотами з ідентичними або схожими характеристиками (Atk/Crit/Armor/Dodge). Миттєво виявляє свіжий демпінг.\n\n"
            f"• <b>📜 3-денна історія (History DB):</b>\n"
            f"  Оцінює ціну за медіаною завершених угод за останні 3 дні з локальної бази SQLite (20 000+ угод). Оновлює базу кожні 15 хвилин.\n\n"
            f"<i>Оберіть потрібний режим кнопкою нижче:</i>"
        )

    def _build_mode_keyboard(self) -> dict:
        pricing_mode = getattr(self.scanner, "pricing_mode", config.PRICING_MODE)
        live_check = "✓ " if pricing_mode == "live" else ""
        hist_check = "✓ " if pricing_mode == "history" else ""
        return {
            "inline_keyboard": [
                [
                    {"text": f"{live_check}⚡ Реальний час (Live)", "callback_data": "set_mode_live"},
                ],
                [
                    {"text": f"{hist_check}📜 3-денна історія (History)", "callback_data": "set_mode_history"},
                ],
                [
                    {"text": "🔙 Назад до панелі", "callback_data": "cmd_status"}
                ]
            ]
        }

    def _build_quality_menu_text(self) -> str:
        qualities = getattr(self.scanner, "active_qualities", config.EQUIPMENT_QUALITIES)
        items_count = len(getattr(self.scanner, "equipment_list", config.EQUIPMENT_TO_MONITOR))
        roll_threshold = getattr(self.scanner.analyzer, "god_roll_threshold", config.EQUIPMENT_GOD_ROLL_THRESHOLD)

        lines = [
            "💎 <b>Керування якістю (рідкістю) спорядження</b>\n",
            "Оберіть, які категорії якості предметів сканувати:\n"
        ]
        for q_key in ALL_QUALITIES:
            q_info = QUALITY_TIERS[q_key]
            active = q_key in qualities
            status = "🟢 Увімкнено" if active else "⚪ Вимкнено"
            item_samples = ", ".join(EQUIPMENT_METADATA.get(code, {}).get("name", code).split(" ")[0] for code in q_info["items"][:3])
            lines.append(f"{q_info['emoji']} <b>{q_info['label']}:</b> {status} <i>({item_samples}...)</i>")

        lines.append(f"\n📦 <b>Всього на моніторингу:</b> <code>{items_count} предметів</code>")
        lines.append(f"🌟 <b>Поріг якості ролу:</b> <code>{roll_threshold}%</code>\n")
        lines.append("<i>Натискайте кнопки нижче, щоб увімкнути або вимкнути якість:</i>")
        return "\n".join(lines)

    def _build_quality_keyboard(self) -> dict:
        qualities = getattr(self.scanner, "active_qualities", config.EQUIPMENT_QUALITIES)
        roll_threshold = getattr(self.scanner.analyzer, "god_roll_threshold", config.EQUIPMENT_GOD_ROLL_THRESHOLD)

        def btn(q_key):
            q_info = QUALITY_TIERS[q_key]
            active = q_key in qualities
            icon = "🟢" if active else "⚪"
            return {
                "text": f"{q_info['emoji']} {q_info['name']} {icon}",
                "callback_data": f"toggle_q_{q_key}"
            }

        return {
            "inline_keyboard": [
                [btn("mythic"), btn("legendary")],
                [btn("epic"), btn("rare")],
                [btn("uncommon"), btn("common")],
                [
                    {"text": "🏆 Топ (Т4-Т6)", "callback_data": "preset_q_top"},
                    {"text": "⚡ Всі якості (Т1-Т6)", "callback_data": "preset_q_all"}
                ],
                [
                    {"text": f"🌟 Поріг ролу ({roll_threshold}%)", "callback_data": "cmd_roll_menu"}
                ],
                [
                    {"text": "🔙 Назад до панелі", "callback_data": "cmd_status"}
                ]
            ]
        }

    def _build_roll_menu_text(self) -> str:
        curr = getattr(self.scanner.analyzer, "god_roll_threshold", config.EQUIPMENT_GOD_ROLL_THRESHOLD)
        return (
            f"🌟 <b>Налаштування порогу якості ролу (статів)</b>\n\n"
            f"Поточний поріг: <b>{curr}%</b>\n\n"
            f"Сканер вираховує якість кожної речі від 0% до 100% за діапазоном її характеристик.\n"
            f"Коли якість перевищує цей поріг, бот маркує предмет особливою відміткою 🌟 <b>ТОП РОЛ</b>.\n\n"
            f"Оберіть бажаний поріг:"
        )

    def _build_roll_keyboard(self) -> dict:
        curr = getattr(self.scanner.analyzer, "god_roll_threshold", config.EQUIPMENT_GOD_ROLL_THRESHOLD)
        def label(val):
            check = "✓ " if abs(curr - val) < 0.1 else ""
            return f"{check}{int(val)}%"

        return {
            "inline_keyboard": [
                [
                    {"text": label(50.0), "callback_data": "set_roll_50"},
                    {"text": label(60.0), "callback_data": "set_roll_60"},
                    {"text": label(70.0), "callback_data": "set_roll_70"},
                ],
                [
                    {"text": label(80.0), "callback_data": "set_roll_80"},
                    {"text": label(85.0), "callback_data": "set_roll_85"},
                    {"text": label(90.0), "callback_data": "set_roll_90"},
                ],
                [
                    {"text": "🔙 Назад до якостей", "callback_data": "cmd_quality_menu"}
                ]
            ]
        }

    def _build_interval_menu_text(self) -> str:
        curr = getattr(self.scanner, "scan_interval", config.EQUIPMENT_SCAN_INTERVAL)
        return (
            f"⏱ <b>Налаштування частоти сканування</b>\n\n"
            f"Поточний інтервал: <b>{curr} сек</b>\n\n"
            f"Оберіть бажану частоту перевірки ринку:\n"
            f"• <i>1 сек:</i> миттєва турбо-швидкість (за замовчуванням)\n"
            f"• <i>2 сек:</i> швидкий режим\n"
            f"• <i>3 сек:</i> помірний режим\n"
            f"• <i>5 сек:</i> стандартний режим\n\n"
            f"<i>Ви також можете надіслати точне число від 1 сек, наприклад:</i> <code>/interval 1</code>"
        )

    def _build_interval_keyboard(self) -> dict:
        curr = getattr(self.scanner, "scan_interval", config.EQUIPMENT_SCAN_INTERVAL)
        def label(sec):
            check = "✓ " if curr == sec else ""
            return f"{check}{sec} сек"

        return {
            "inline_keyboard": [
                [
                    {"text": f"⚡ {label(1)}", "callback_data": "set_int_1"},
                    {"text": f"⚡ {label(2)}", "callback_data": "set_int_2"},
                ],
                [
                    {"text": f"⏱ {label(3)}", "callback_data": "set_int_3"},
                    {"text": f"⏱ {label(5)}", "callback_data": "set_int_5"},
                ],
                [
                    {"text": f"⏱ {label(10)}", "callback_data": "set_int_10"},
                    {"text": f"⏱ {label(15)}", "callback_data": "set_int_15"},
                    {"text": f"⏱ {label(20)}", "callback_data": "set_int_20"},
                ],
                [
                    {"text": f"⏱ {label(25)}", "callback_data": "set_int_25"},
                    {"text": f"⏱ {label(30)}", "callback_data": "set_int_30"},
                ],
                [
                    {"text": "🔙 Назад до панелі", "callback_data": "cmd_status"}
                ]
            ]
        }

    def _update_env_key(self, key: str, value: str):
        """Persist key=value setting in .env file."""
        try:
            env_file = config.BASE_DIR / ".env"
            if not env_file.exists():
                return
            content = env_file.read_text(encoding="utf-8")
            lines = content.splitlines()
            found = False
            new_lines = []
            for line in lines:
                if line.strip().startswith(f"{key}="):
                    new_lines.append(f"{key}={value}")
                    found = True
                else:
                    new_lines.append(line)
            if not found:
                new_lines.append(f"{key}={value}")
            env_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to update .env key {key}: {e}")

    async def register_commands(self):
        """Register command menu in Telegram UI for the Market Bot."""
        if not self.token:
            return
        client = await self.get_client()
        url = f"https://api.telegram.org/bot{self.token}/setMyCommands"
        commands = [
            {"command": "start", "description": "Головна панель керування ринком"},
            {"command": "mode", "description": "🔄 Режим оцінки (Live / Історія)"},
            {"command": "interval", "description": "⏱ Змінити частоту (від 1 сек)"},
            {"command": "quality", "description": "💎 Налаштування якості спорядження"},
            {"command": "scan", "description": "🔍 Сканувати ринок зараз"},
            {"command": "stats", "description": "📊 Статистика бази угод"},
            {"command": "stop", "description": "⏸ Призупинити сканер"},
            {"command": "run", "description": "▶️ Запустити сканер"},
            {"command": "status", "description": "🔄 Поточний стан сканера"},
            {"command": "clear", "description": "🧹 Очистити чат від повідомлень"},
            {"command": "version", "description": "ℹ️ Поточна версія та історія"}
        ]
        try:
            await client.post(url, json={"commands": commands})
        except Exception as e:
            logger.debug(f"Failed to set Market Bot Telegram commands: {e}")

    async def clear_chat_messages(self, chat_id: str, from_msg_id: int, count: int = 100) -> int:
        """
        Deletes recent messages in the chat up to from_msg_id.
        Uses Telegram deleteMessages (in batches of up to 100) or deleteMessage fallback.
        """
        if not self.token or not from_msg_id:
            return 0
        client = await self.get_client()
        url_batch = f"https://api.telegram.org/bot{self.token}/deleteMessages"
        url_single = f"https://api.telegram.org/bot{self.token}/deleteMessage"

        start_id = max(1, from_msg_id - count + 1)
        ids = list(range(start_id, from_msg_id + 1))
        deleted_count = 0

        # Batch deletion (up to 100 per request)
        for i in range(0, len(ids), 100):
            chunk = ids[i:i + 100]
            try:
                resp = await client.post(url_batch, json={"chat_id": chat_id, "message_ids": chunk})
                if resp.status_code == 200 and resp.json().get("ok"):
                    deleted_count += len(chunk)
                    continue
            except Exception:
                pass

            # Fallback to single message delete
            for mid in reversed(chunk):
                try:
                    resp = await client.post(url_single, json={"chat_id": chat_id, "message_id": mid})
                    if resp.status_code == 200 and resp.json().get("ok"):
                        deleted_count += 1
                except Exception:
                    pass

        return deleted_count

    def _get_db_stats_text(self) -> str:
        cycles = getattr(self.scanner, "cycle_count", 0)
        alerts = getattr(self.scanner, "total_alerts_sent", 0)
        items_count = len(getattr(self.scanner, "equipment_list", config.EQUIPMENT_TO_MONITOR))
        interval = getattr(self.scanner, "scan_interval", config.EQUIPMENT_SCAN_INTERVAL)
        last_scan = getattr(self.scanner, "last_scan_time", None) or "немає"
        pricing_mode = getattr(self.scanner, "pricing_mode", config.PRICING_MODE)
        mode_label = "⚡ Реальний час (ордери)" if pricing_mode == "live" else "📜 3-денна історія (база)"

        return (
            f"📊 <b>Статистика сканера WarEra:</b>\n\n"
            f"🔄 <b>Режим оцінки ціни:</b> <b>{mode_label}</b>\n"
            f"🎯 <b>Аналіз вигоди:</b> Порівняння схожих та точних характеристик\n"
            f"📦 <b>Предметів на моніторингу:</b> <code>{items_count} шт.</code>\n"
            f"⏱ <b>Інтервал сканування:</b> <code>{interval} сек</code>\n"
            f"🔄 <b>Завершено циклів:</b> <code>{cycles}</code>\n"
            f"🔔 <b>Виявлено вигідних угод:</b> <code>{alerts}</code>\n"
            f"⏰ <b>Останнє сканування:</b> <code>{last_scan}</code>"
        )

    async def handle_update(self, update: dict):
        # 1. Handle Inline Button Clicks (Callback Queries)
        if "callback_query" in update:
            cb = update["callback_query"]
            cb_id = cb["id"]
            from_user = cb.get("from", {})
            user_id = from_user.get("id")
            message = cb.get("message", {})
            chat = message.get("chat", {})
            chat_id = str(chat.get("id"))
            msg_id = message.get("message_id")
            data = cb.get("data", "")

            if not self._is_authorized(user_id, chat_id):
                await self.answer_callback(cb_id, "⛔ Доступ дозволено лише власнику.")
                return

            if data == "cmd_status":
                await self.answer_callback(cb_id, "Статус оновлено!")
                if msg_id:
                    await self.edit_message(chat_id, msg_id, self._build_control_panel_text(), self._build_keyboard())
                return

            if data == "cmd_stop":
                if hasattr(self.scanner, "pause"):
                    self.scanner.pause()
                else:
                    self.scanner.is_paused = True
                await self.answer_callback(cb_id, "⏸ Сканер призупинено!")
                if msg_id:
                    await self.edit_message(chat_id, msg_id, self._build_control_panel_text(chat_id), self._build_keyboard(chat_id, is_admin))

            elif data == "cmd_start":
                if hasattr(self.scanner, "resume"):
                    self.scanner.resume()
                else:
                    self.scanner.is_paused = False
                await self.answer_callback(cb_id, "▶️ Сканер запущено!")
                if msg_id:
                    await self.edit_message(chat_id, msg_id, self._build_control_panel_text(chat_id), self._build_keyboard(chat_id, is_admin))

            elif data == "cmd_scan":
                await self.answer_callback(cb_id, "🔍 Запуск позачергового сканування...")
                asyncio.create_task(self.scanner.trigger_manual_scan(chat_id))

            elif data == "cmd_stats":
                stats_text = self._get_db_stats_text()
                await self.answer_callback(cb_id)
                await self.send_message(chat_id, stats_text)

            elif data == "cmd_mode_menu":
                await self.answer_callback(cb_id)
                if msg_id:
                    await self.edit_message(chat_id, msg_id, self._build_mode_menu_text(), self._build_mode_keyboard())

            elif data == "set_mode_live":
                if hasattr(self.scanner, "set_pricing_mode"):
                    self.scanner.set_pricing_mode("live")
                self._update_env_key("PRICING_MODE", "live")
                await self.answer_callback(cb_id, "⚡ Оцінку перемкнено на Реальний час (Live)!")
                if msg_id:
                    await self.edit_message(chat_id, msg_id, self._build_control_panel_text(chat_id), self._build_keyboard(chat_id, is_admin))

            elif data == "set_mode_history":
                if hasattr(self.scanner, "set_pricing_mode"):
                    self.scanner.set_pricing_mode("history")
                self._update_env_key("PRICING_MODE", "history")
                await self.answer_callback(cb_id, "📜 Оцінку перемкнено на 3-денну історію угод!")
                if msg_id:
                    await self.edit_message(chat_id, msg_id, self._build_control_panel_text(chat_id), self._build_keyboard(chat_id, is_admin))

            elif data == "cmd_clear":
                await self.answer_callback(cb_id, "🧹 Очищення чату...")
                deleted = await self.clear_chat_messages(chat_id, from_msg_id=msg_id, count=100)
                await self.send_message(
                    chat_id,
                    f"🧹 <b>Чат очищено!</b> (видалено ~{deleted} повідомлень)\n\n"
                    + self._build_control_panel_text(chat_id),
                    self._build_keyboard(chat_id, is_admin)
                )

            elif data == "cmd_interval_menu":
                await self.answer_callback(cb_id)
                if msg_id:
                    await self.edit_message(chat_id, msg_id, self._build_interval_menu_text(), self._build_interval_keyboard())

            elif data.startswith("set_int_"):
                sec_str = data.replace("set_int_", "")
                if sec_str.isdigit():
                    sec = int(sec_str)
                    if hasattr(self.scanner, "set_scan_interval"):
                        self.scanner.set_scan_interval(sec)
                    else:
                        self.scanner.scan_interval = sec
                    self._update_env_key("EQUIPMENT_SCAN_INTERVAL", str(sec))
                    await self.answer_callback(cb_id, f"⏱ Інтервал змінено на {sec} сек!")
                    if msg_id:
                        await self.edit_message(chat_id, msg_id, self._build_control_panel_text(chat_id), self._build_keyboard(chat_id, is_admin))

            elif data == "cmd_quality_menu":
                await self.answer_callback(cb_id)
                if msg_id:
                    await self.edit_message(chat_id, msg_id, self._build_quality_menu_text(), self._build_quality_keyboard())

            elif data.startswith("toggle_q_"):
                q_key = data.replace("toggle_q_", "")
                if hasattr(self.scanner, "toggle_quality"):
                    is_enabled = self.scanner.toggle_quality(q_key)
                    self._update_env_key("EQUIPMENT_QUALITIES", ",".join(self.scanner.active_qualities))
                    self._update_env_key("EQUIPMENT_TO_MONITOR", ",".join(self.scanner.equipment_list))
                    q_info = QUALITY_TIERS.get(q_key, {})
                    label = q_info.get("label", q_key)
                    msg_toast = f"{q_info.get('emoji', '')} {label}: {'увімкнено 🟢' if is_enabled else 'вимкнено ⚪'}"
                    await self.answer_callback(cb_id, msg_toast)
                    if msg_id:
                        await self.edit_message(chat_id, msg_id, self._build_quality_menu_text(), self._build_quality_keyboard())

            elif data == "preset_q_top":
                if hasattr(self.scanner, "set_qualities"):
                    self.scanner.set_qualities(["mythic", "legendary", "epic"])
                    self._update_env_key("EQUIPMENT_QUALITIES", ",".join(self.scanner.active_qualities))
                    self._update_env_key("EQUIPMENT_TO_MONITOR", ",".join(self.scanner.equipment_list))
                    await self.answer_callback(cb_id, "🏆 Встановлено пресет Топ (Т4-Т6)!")
                    if msg_id:
                        await self.edit_message(chat_id, msg_id, self._build_quality_menu_text(), self._build_quality_keyboard())

            elif data == "preset_q_all":
                if hasattr(self.scanner, "set_qualities"):
                    self.scanner.set_qualities(ALL_QUALITIES)
                    self._update_env_key("EQUIPMENT_QUALITIES", ",".join(self.scanner.active_qualities))
                    self._update_env_key("EQUIPMENT_TO_MONITOR", ",".join(self.scanner.equipment_list))
                    await self.answer_callback(cb_id, "⚡ Увімкнено всі якості (Т1-Т6)!")
                    if msg_id:
                        await self.edit_message(chat_id, msg_id, self._build_quality_menu_text(), self._build_quality_keyboard())

            elif data == "cmd_roll_menu":
                await self.answer_callback(cb_id)
                if msg_id:
                    await self.edit_message(chat_id, msg_id, self._build_roll_menu_text(), self._build_roll_keyboard())

            elif data.startswith("set_roll_"):
                val_str = data.replace("set_roll_", "")
                try:
                    val = float(val_str)
                    if hasattr(self.scanner, "set_god_roll_threshold"):
                        self.scanner.set_god_roll_threshold(val)
                    self._update_env_key("EQUIPMENT_GOD_ROLL_THRESHOLD", str(val))
                    await self.answer_callback(cb_id, f"🌟 Поріг ролу змінено на {int(val)}%!")
                    if msg_id:
                        await self.edit_message(chat_id, msg_id, self._build_quality_menu_text(), self._build_quality_keyboard())
                except Exception:
                    await self.answer_callback(cb_id, "Помилка встановлення порогу")

            return

        # 2. Handle Text Messages & Commands
        if "message" in update:
            msg = update["message"]
            text = (msg.get("text") or "").strip()
            from_user = msg.get("from", {})
            user_id = from_user.get("id")
            chat = msg.get("chat", {})
            chat_id = str(chat.get("id"))

            if not self._is_authorized(user_id, chat_id):
                if text.startswith("/"):
                    await self.send_message(chat_id, "⛔ Цей бот призначений виключно для приватного керування ринком спорядження.")
                return

            words = text.split()
            first_word = words[0].lower() if words else ""
            if "@" in first_word:
                first_word = first_word.split("@")[0]
            clean_cmd = first_word.lstrip("/")

            logger.info(f"Market Bot command: '{text}' from user {user_id}")

            if first_word in ("/start", "/menu", "/help") or clean_cmd in ("start", "menu", "help", "меню", "допомога"):
                await self.send_message(chat_id, self._build_control_panel_text(), self._build_keyboard())

            elif first_word in ("/status", "/стан") or clean_cmd in ("status", "стан", "статус"):
                await self.send_message(chat_id, self._build_control_panel_text(), self._build_keyboard())

            # --- Administrative Commands (Restricted to Admin) ---
            elif first_word in ("/stop", "/pause") or clean_cmd in ("stop", "pause", "стоп", "пауза", "зупинити", "зупинка"):
                if not is_admin:
                    await self.send_message(chat_id, "⛔ Зупинка або запуск спільного сканера доступні лише адміністратору.")
                    return
                if hasattr(self.scanner, "pause"):
                    self.scanner.pause()
                else:
                    self.scanner.is_paused = True
                    if hasattr(self.scanner, "wake_event"):
                        self.scanner.wake_event.set()
                reply = (
                    "⏸ <b>Сканер WarEra призупинено!</b>\n\n"
                    "Бот не надсилатиме нові сповіщення, доки ви його не ввімкнете знову.\n"
                    "Натисніть кнопку нижче або /run, щоб відновити роботу."
                )
                keyboard = {
                    "inline_keyboard": [[{"text": "▶️ Запустити сканер", "callback_data": "cmd_start"}]]
                }
                await self.send_message(chat_id, reply, keyboard)

            elif first_word in ("/run", "/resume") or clean_cmd in ("run", "resume", "старт", "пуск", "відновити", "запуск"):
                if not is_admin:
                    await self.send_message(chat_id, "⛔ Зупинка або запуск спільного сканера доступні лише адміністратору.")
                    return
                if hasattr(self.scanner, "resume"):
                    self.scanner.resume()
                else:
                    self.scanner.is_paused = False
                    if hasattr(self.scanner, "wake_event"):
                        self.scanner.wake_event.set()
                reply = (
                    "▶️ <b>Сканер WarEra запущено!</b>\n\n"
                    f"Моніторинг {len(config.EQUIPMENT_TO_MONITOR)} категорій активний кожні {getattr(self.scanner, 'scan_interval', config.EQUIPMENT_SCAN_INTERVAL)} секунд."
                )
                keyboard = {
                    "inline_keyboard": [[{"text": "⏸ Зупинити сканер", "callback_data": "cmd_stop"}]]
                }
                await self.send_message(chat_id, reply, keyboard)

            elif first_word in ("/scan", "/скан") or clean_cmd in ("scan", "скан"):
                if not is_admin:
                    await self.send_message(chat_id, "⛔ Примусовий запуск сканування ринку доступний лише адміністратору.")
                    return
                await self.send_message(chat_id, "🔍 <i>Запускаю позачергове сканування ринку...</i>")
                await self.scanner.trigger_manual_scan(chat_id)

            elif first_word in ("/stats", "/стат") or clean_cmd in ("stats", "статистика", "стат"):
                await self.send_message(chat_id, self._get_db_stats_text())

            elif first_word in ("/interval", "/інтервал") or clean_cmd in ("interval", "інтервал", "частота"):
                if not is_admin:
                    await self.send_message(chat_id, "⛔ Зміна частоти сканера доступна лише адміністратору.")
                    return
                parts = text.split()
                if len(parts) > 1 and parts[1].isdigit():
                    sec = int(parts[1])
                    if sec < 1:
                        await self.send_message(chat_id, "⚠️ Мінімальний інтервал сканування — <b>1 секунда</b>.")
                        return
                    if sec > 3600:
                        await self.send_message(chat_id, "⚠️ Максимальний інтервал — <b>3600 секунд</b> (1 година).")
                        return
                    if hasattr(self.scanner, "set_scan_interval"):
                        self.scanner.set_scan_interval(sec)
                    else:
                        self.scanner.scan_interval = sec
                    self._update_env_key("EQUIPMENT_SCAN_INTERVAL", str(sec))
                    reply = (
                        f"✅ <b>Частоту сканування змінено на {sec} сек!</b>\n\n"
                        f"Сканер тепер перевірятиме пропозиції кожні {sec} секунд."
                    )
                    keyboard = {
                        "inline_keyboard": [
                            [{"text": "🤖 До панелі керування", "callback_data": "cmd_status"}],
                            [{"text": "⏱ Змінити ще раз", "callback_data": "cmd_interval_menu"}]
                        ]
                    }
                    await self.send_message(chat_id, reply, keyboard)
                else:
                    await self.send_message(chat_id, self._build_interval_menu_text(), self._build_interval_keyboard())

            elif first_word in ("/quality", "/якість", "/качество", "/rarity", "/tier") or clean_cmd in ("quality", "якість", "качество", "якості", "рідкість", "rarity", "tier"):
                if not is_admin:
                    await self.send_message(chat_id, "⛔ Налаштування якості ринку доступне лише адміністратору.")
                    return
                parts = text.split()
                if len(parts) == 1:
                    await self.send_message(chat_id, self._build_quality_menu_text(), self._build_quality_keyboard())
                else:
                    arg1 = parts[1].lower()
                    if arg1 in ("all", "всі", "все"):
                        if hasattr(self.scanner, "set_qualities"):
                            self.scanner.set_qualities(ALL_QUALITIES)
                            self._update_env_key("EQUIPMENT_QUALITIES", ",".join(self.scanner.active_qualities))
                            self._update_env_key("EQUIPMENT_TO_MONITOR", ",".join(self.scanner.equipment_list))
                        await self.send_message(chat_id, "⚡ <b>Увімкнено всі рівні якості (Т1-Т6)!</b>", self._build_quality_keyboard())
                    elif arg1 in ("top", "топ"):
                        if hasattr(self.scanner, "set_qualities"):
                            self.scanner.set_qualities(["mythic", "legendary", "epic"])
                            self._update_env_key("EQUIPMENT_QUALITIES", ",".join(self.scanner.active_qualities))
                            self._update_env_key("EQUIPMENT_TO_MONITOR", ",".join(self.scanner.equipment_list))
                        await self.send_message(chat_id, "🏆 <b>Встановлено пресет Топ (Т4-Т6)!</b>", self._build_quality_keyboard())
                    else:
                        q_key = normalize_quality_key(arg1)
                        if q_key and hasattr(self.scanner, "toggle_quality"):
                            is_enabled = self.scanner.toggle_quality(q_key)
                            self._update_env_key("EQUIPMENT_QUALITIES", ",".join(self.scanner.active_qualities))
                            self._update_env_key("EQUIPMENT_TO_MONITOR", ",".join(self.scanner.equipment_list))
                            q_info = QUALITY_TIERS.get(q_key, {})
                            label = q_info.get("label", q_key)
                            await self.send_message(chat_id, f"{q_info.get('emoji', '')} <b>{label}:</b> {'увімкнено 🟢' if is_enabled else 'вимкнено ⚪'}", self._build_quality_keyboard())
                        else:
                            await self.send_message(chat_id, self._build_quality_menu_text(), self._build_quality_keyboard())

            elif first_word in ("/roll", "/поріг") or clean_cmd in ("roll", "поріг", "рол"):
                if not is_admin:
                    await self.send_message(chat_id, "⛔ Налаштування порогу ролу доступне лише адміністратору.")
                    return
                parts = text.split()
                if len(parts) > 1:
                    try:
                        val = float(parts[1].replace("%", ""))
                        if hasattr(self.scanner, "set_god_roll_threshold"):
                            self.scanner.set_god_roll_threshold(val)
                        self._update_env_key("EQUIPMENT_GOD_ROLL_THRESHOLD", str(val))
                        await self.send_message(chat_id, f"✅ <b>Поріг якості ролу встановлено: {val}%</b>", self._build_quality_keyboard())
                    except ValueError:
                        await self.send_message(chat_id, "⚠️ Будь ласка, вкажіть число, наприклад: <code>/roll 80</code>")
                else:
                    await self.send_message(chat_id, self._build_roll_menu_text(), self._build_roll_keyboard())

            elif first_word in ("/mode", "/режим") or clean_cmd in ("mode", "режим"):
                if not is_admin:
                    await self.send_message(chat_id, "⛔ Перемикання режиму ринку доступне лише адміністратору.")
                    return
                parts = text.split()
                if len(parts) > 1:
                    sub = parts[1].lower()
                    if sub in ("live", "лайв", "онлайн", "ордери", "orders"):
                        if hasattr(self.scanner, "set_pricing_mode"):
                            self.scanner.set_pricing_mode("live")
                        self._update_env_key("PRICING_MODE", "live")
                        await self.send_message(chat_id, "⚡ <b>Режим оцінки: Реальний час (Live)!</b>\nПорівняння з відкритими ордерами ринку.", self._build_keyboard(chat_id, is_admin))
                    elif sub in ("history", "історія", "база", "db", "3d"):
                        if hasattr(self.scanner, "set_pricing_mode"):
                            self.scanner.set_pricing_mode("history")
                        self._update_env_key("PRICING_MODE", "history")
                        await self.send_message(chat_id, "📜 <b>Режим оцінки: 3-денна історія угод!</b>\nАналіз за завершеними угодами з локальної бази SQLite.", self._build_keyboard(chat_id, is_admin))
                    else:
                        await self.send_message(chat_id, "⚠️ Використання: <code>/mode live</code> або <code>/mode history</code>", self._build_mode_keyboard())
                else:
                    await self.send_message(chat_id, self._build_mode_menu_text(), self._build_mode_keyboard())

            elif first_word in ("/clear", "/clean", "/очистити") or clean_cmd in ("clear", "clean", "очистити", "клир", "очистка"):
                if not is_admin:
                    await self.send_message(chat_id, "⛔ Очищення чату доступне лише адміністратору.")
                    return
                curr_msg_id = msg.get("message_id")
                deleted = await self.clear_chat_messages(chat_id, from_msg_id=curr_msg_id, count=100)
                await self.send_message(
                    chat_id,
                    f"🧹 <b>Чат очищено!</b> (видалено ~{deleted} повідомлень)\n\n"
                    + self._build_control_panel_text(chat_id),
                    self._build_keyboard(chat_id, is_admin)
                )

            elif first_word in ("/version", "/ver") or clean_cmd in ("version", "ver", "версія"):
                ver_text = (
                    f"ℹ️ <b>Версія системи:</b> <code>{config.APP_VERSION}</code>\n\n"
                    f"📋 <b>Історія останніх оновлень:</b>\n"
                    f"• <b>b.0001.14</b> — Перемикання способу оцінки вартості (⚡ Live ордери / 📜 3-денна історія) у налаштуваннях та команда /clear для очищення повідомлень у чаті\n"
                    f"• <b>b.0001.13</b> — Оцінка цін за відкритими ринковими ордерами: порівняння зі схожими та точними характеристиками, миттєвий старт без залежності від БД, 13x прискорення запитів\n"
                    f"• <b>b.0001.12</b> — Керування якістю (рідкістю) предметів: перемикання категорій Т1-Т6 в 1 клік, пресети Топ/Всі, фільтр порогу якості ролу (/quality, /roll)\n"
                    f"• <b>b.0001.11</b> — Частота сканування 1, 2, 3, 5 сек (за замовчуванням 1 сек) та гарантоване очищення старих процесів ресурсів\n"
                    f"• <b>b.0001.10</b> — Повне видалення відправки в групу, сповіщення лише в приватні повідомлення\n"
                    f"• <b>b.0001.9</b> — Повний фокус на речах (видалено сировину), турбо-інтервал 2 сек, новий компактний формат сповіщень\n"
                    f"• <b>b.0001.8</b> — Перемикач моніторингу маркету ресурсів (/market on|off)\n"
                    f"• <b>b.0001.7</b> — Версіонування та команда /version, інтерактивна панель\n"
                    f"• <b>b.0001.6</b> — Керування надсиланням у групу (/group on|off)\n"
                    f"• <b>b.0001.5</b> — Зміна інтервалу сканування (/interval)\n"
                    f"• <b>b.0001.4</b> — Дистанційне керування (/stop, /run, wake-up)\n"
                    f"• <b>b.0001.3</b> — Компактний UI сповіщень (іконки 🛩🛡, маркери рідкості 🔴🟡🟣)\n"
                    f"• <b>b.0001.2</b> — Динамічні лінки на кожен предмет ринку\n"
                    f"• <b>b.0001.1</b> — Початковий реліз сканера спорядження\n\n"
                    f"<i>Детальний опис кожної версії зафіксовано у VERSIONS.md</i>"
                )
                keyboard = {
                    "inline_keyboard": [
                        [{"text": "🤖 До панелі керування", "callback_data": "cmd_status"}]
                    ]
                }
                await self.send_message(chat_id, ver_text, keyboard)

    async def start_polling(self):
        """Continuously poll Telegram for updates."""
        if not self.token:
            logger.info("Telegram bot token not configured, skipping command listener.")
            return

        try:
            await self.register_commands()
        except Exception as e:
            logger.warning(f"Error registering Telegram commands: {e}")

        self.is_running = True
        logger.info("WarEra Telegram command listener started.")

        client = await self.get_client()
        url = f"https://api.telegram.org/bot{self.token}/getUpdates"

        while self.is_running:
            try:
                resp = await client.get(
                    url,
                    params={"offset": self.offset, "timeout": 20},
                    timeout=25.0
                )
                if resp.status_code == 200:
                    data = resp.json()
                    updates = data.get("result", [])
                    for update in updates:
                        self.offset = update["update_id"] + 1
                        try:
                            await self.handle_update(update)
                        except Exception as e:
                            logger.error(f"Error handling Telegram update: {e}", exc_info=True)
                elif resp.status_code == 409:
                    logger.warning("Telegram conflict (409): another bot instance is polling.")
                    await asyncio.sleep(4)
                else:
                    await asyncio.sleep(2)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug(f"Telegram polling exception: {e}")
                await asyncio.sleep(2)

        await self.close()

    def stop_polling(self):
        self.is_running = False
