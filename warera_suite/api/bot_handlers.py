"""
Telegram Update and Command Handlers for WarEra Sniper Bot.
Handles inline callback queries and slash commands:
/focus, /snipe, /battles, /bounties, /rate, /cb, /threshold, /auth, etc.
"""

import logging
import re
from typing import Any, Optional, Dict, List
import config
from battle_analyzer import get_shared_battle_analyzer

from bot_keyboards import (
    build_main_keyboard,
    build_sniper_menu_keyboard,
    build_bounties_menu_keyboard,
    build_auctions_menu_keyboard,
    build_contracts_keyboard,
    build_threshold_keyboard,
    build_rate_keyboard,
    build_budget_keyboard,
    build_focus_select_keyboard,
    build_focus_side_keyboard,
    build_focus_confirmed_keyboard,
)
from bot_formatter import (
    build_panel_text,
    build_sniper_menu_text,
    build_bounties_menu_text,
    build_auctions_menu_text,
    format_battles_text,
    format_contracts_text,
    format_auctions_text,
    format_focus_select_screen,
    format_focus_side_screen,
    format_focus_confirmed_screen,
)

logger = logging.getLogger("WarEraBotHandlers")


async def handle_callback_query(bot: Any, cb: dict):
    cb_id = cb["id"]
    from_user = cb.get("from", {})
    message = cb.get("message", {})
    chat = message.get("chat", {})
    chat_id = str(chat.get("id"))
    msg_id = message.get("message_id")
    data = cb.get("data", "")

    bot.subscribers_db.register_user(
        chat_id=chat_id,
        username=from_user.get("username"),
        first_name=from_user.get("first_name")
    )

    # Security gate: require password authorization
    if not bot.subscribers_db.is_authorized(chat_id):
        await bot.answer_callback(cb_id, "🔒 Доступ обмежено паролем клану!", show_alert=True)
        await bot.send_auth_prompt(chat_id)
        return

    if data in ("menu_main", "sniper_cmd_status"):
        await bot.answer_callback(cb_id, "Головне меню")
        if msg_id:
            await bot.edit_message(chat_id, msg_id, build_panel_text(bot.subscribers_db, chat_id), build_main_keyboard(bot.subscribers_db, chat_id))
        return

    elif data == "menu_sniper":
        await bot.answer_callback(cb_id, "🎯 Розділ: Снайпер фіолу")
        if msg_id:
            await bot.edit_message(chat_id, msg_id, build_sniper_menu_text(bot.subscribers_db, chat_id), build_sniper_menu_keyboard(bot.subscribers_db, chat_id))
        return

    elif data == "menu_bounties":
        await bot.answer_callback(cb_id, "💰 Розділ: Баунті")
        if msg_id:
            await bot.edit_message(chat_id, msg_id, build_bounties_menu_text(bot.subscribers_db, chat_id), build_bounties_menu_keyboard(bot.subscribers_db, chat_id))
        return

    elif data == "menu_auctions":
        await bot.answer_callback(cb_id, "📜 Розділ: Контракти")
        if msg_id:
            await bot.edit_message(chat_id, msg_id, build_auctions_menu_text(bot.subscribers_db, chat_id), build_auctions_menu_keyboard(bot.subscribers_db, chat_id))
        return

    elif data == "cmd_list_auctions":
        await bot.answer_callback(cb_id, "📜 Шукаю активні аукціони контрактів...")
        txt = await bot._get_auctions_text(chat_id=chat_id)
        await bot.send_message(chat_id, txt)
        return

    elif data == "sniper_toggle_alerts":
        curr = bot.subscribers_db.get_user_prefs(chat_id).get("sniper_alerts", True)
        new_val = bot.subscribers_db.set_sniper_alerts(chat_id, not curr)
        status_txt = "🟢 УВІМКНЕНО" if new_val else "🔴 ВИМКНЕНО"
        await bot.answer_callback(cb_id, f"🎯 Снайпер: {status_txt}")
        if msg_id:
            await bot.edit_message(chat_id, msg_id, build_panel_text(bot.subscribers_db, chat_id), build_main_keyboard(bot.subscribers_db, chat_id))
        return

    elif data == "sniper_toggle_contracts":
        curr = bot.subscribers_db.get_user_prefs(chat_id).get("contract_alerts", False)
        new_val = bot.subscribers_db.set_contract_alerts(chat_id, not curr)
        status_txt = "🟢 УВІМКНЕНО" if new_val else "🔴 ВИМКНЕНО"
        await bot.answer_callback(cb_id, f"💰 Баунті: {status_txt}")
        if msg_id:
            await bot.edit_message(chat_id, msg_id, build_panel_text(bot.subscribers_db, chat_id), build_main_keyboard(bot.subscribers_db, chat_id))
        return

    elif data == "sniper_toggle_auctions":
        curr = bot.subscribers_db.get_user_prefs(chat_id).get("auction_alerts", False)
        new_val = bot.subscribers_db.set_auction_alerts(chat_id, not curr)
        status_txt = "🟢 УВІМКНЕНО" if new_val else "🔴 ВИМКНЕНО"
        await bot.answer_callback(cb_id, f"📜 Контракти: {status_txt}")
        if msg_id:
            await bot.edit_message(chat_id, msg_id, build_panel_text(bot.subscribers_db, chat_id), build_main_keyboard(bot.subscribers_db, chat_id))
        return

    elif data == "menu_auction_budget":
        curr_budget = bot.subscribers_db.get_user_min_contract_budget(chat_id)
        budget_str = f"≥ {curr_budget:g} 🪙" if curr_budget > 0 else "Всі (без обмежень)"
        ab_text = (
            f"💰 <b>Налаштування мінімального бюджету Контракту</b>\n\n"
            f"Ваш поточний мінімальний поріг: <b>{budget_str}</b>\n\n"
            f"Бот надсилатиме сповіщення лише про ті аукціони, бюджет яких не менший за цей поріг.\n\n"
            f"Оберіть бажаний поріг або введіть команду вручну:\n"
            f"• <code>/contract_budget 50</code>\n"
            f"• <code>/cb 100</code>"
        )
        if msg_id:
            await bot.edit_message(chat_id, msg_id, ab_text, build_budget_keyboard())
        return

    elif data.startswith("set_cb_"):
        new_budget = float(data.replace("set_cb_", ""))
        bot.subscribers_db.set_user_min_contract_budget(chat_id, new_budget)
        budget_disp = f"≥ {new_budget:g} 🪙" if new_budget > 0 else "Всі контракти"
        await bot.answer_callback(cb_id, f"Поріг бюджету: {budget_disp}")
        if msg_id:
            await bot.edit_message(chat_id, msg_id, build_auctions_menu_text(bot.subscribers_db, chat_id), build_auctions_menu_keyboard(bot.subscribers_db, chat_id))
        return

    elif data == "sniper_menu_bounty_rate":
        curr_rate = bot.subscribers_db.get_user_min_bounty_rate(chat_id)
        rate_str = f"≥ {curr_rate} 🪙 / 1k" if curr_rate > 0 else "Всі (без обмежень)"
        br_text = (
            f"💵 <b>Налаштування мінімальної ставки Баунті</b>\n\n"
            f"Ваш поточний мінімальний поріг: <b>{rate_str}</b>\n\n"
            f"Бот надсилатиме сповіщення лише про ті битви, де виплата за 1 000 урону не менша за цей поріг.\n\n"
            f"Оберіть бажаний поріг або введіть команду вручну:\n"
            f"• <code>/bounty_rate 0.07</code>\n"
            f"• <code>/rate 0.05</code>"
        )
        if msg_id:
            await bot.edit_message(chat_id, msg_id, br_text, build_rate_keyboard())
        return

    elif data.startswith("set_br_") or data.startswith("set_rate_"):
        raw_val = data.replace("set_br_", "").replace("set_rate_", "")
        new_rate = float(raw_val)
        bot.subscribers_db.set_user_min_bounty_rate(chat_id, new_rate)
        rate_disp = f"≥ {new_rate} 🪙 / 1k" if new_rate > 0 else "Всі баунті"
        await bot.answer_callback(cb_id, f"Поріг баунті: {rate_disp}")
        if msg_id:
            await bot.edit_message(chat_id, msg_id, build_bounties_menu_text(bot.subscribers_db, chat_id), build_bounties_menu_keyboard(bot.subscribers_db, chat_id))
        return

    elif data == "sniper_cmd_snipe":
        await bot.answer_callback(cb_id, "🎯 Шукаю битви у 15-20 хв вікні...")
        txt = await bot._get_battles_text(sniper_only=True, chat_id=chat_id)
        await bot.send_message(chat_id, txt)
        return

    elif data == "sniper_cmd_battles":
        await bot.answer_callback(cb_id, "⚔️ Отримую активні битви...")
        txt = await bot._get_battles_text(sniper_only=False, chat_id=chat_id)
        await bot.send_message(chat_id, txt)
        return

    elif data == "sniper_cmd_contracts":
        await bot.answer_callback(cb_id, "💰 Шукаю активні баунті...")
        txt, kb = await bot._get_contracts_data(chat_id=chat_id)
        await bot.send_message(chat_id, txt, reply_markup=kb)
        return

    elif data == "menu_bounty_focus_select":
        await bot.answer_callback(cb_id, "🎯 Завантажую активні битви...")
        text, kb = await format_focus_select_screen(bot.subscribers_db, chat_id=chat_id, page=0)
        if msg_id:
            await bot.edit_message(chat_id, msg_id, text, kb)
        else:
            await bot.send_message(chat_id, text, kb)
        return

    elif data.startswith("menu_bounty_focus_p_") or data.startswith("focus_page_"):
        p_raw = data.replace("menu_bounty_focus_p_", "").replace("focus_page_", "").strip()
        p_idx = int(p_raw)
        await bot.answer_callback(cb_id)
        text, kb = await format_focus_select_screen(bot.subscribers_db, chat_id=chat_id, page=p_idx)
        if msg_id:
            await bot.edit_message(chat_id, msg_id, text, kb)
        else:
            await bot.send_message(chat_id, text, kb)
        return

    elif data == "noop":
        await bot.answer_callback(cb_id)
        return

    elif data.startswith("focus_battle_") or data.startswith("focus_select_side_"):
        b_id = data.replace("focus_select_side_", "").replace("focus_battle_", "").strip()
        await bot.answer_callback(cb_id, "🎯 Оберіть сторону...")
        text, kb = await format_focus_side_screen(bot.subscribers_db, b_id, chat_id=chat_id)
        if msg_id:
            await bot.edit_message(chat_id, msg_id, text, kb)
        else:
            await bot.send_message(chat_id, text, kb)
        return

    elif data.startswith("set_focus_") or data.startswith("focus_set_"):
        clean_data = data.replace("focus_set_", "set_focus_")
        parts = clean_data.split("_")
        if len(parts) >= 4:
            b_id = parts[2]
            side = parts[3]
            analyzer = get_shared_battle_analyzer()
            active_list = await analyzer.get_active_battles_for_focus()
            b_match = next((b for b in active_list if b.get('battleId') == b_id), None)
            reg_name = b_match.get('regionName', 'Битва') if b_match else "Битва"

            bot.subscribers_db.set_user_focused_battle(chat_id, b_id, reg_name, side=side)
            side_labels = {"attacker": "⚔️ Атака", "defender": "🛡 Оборона", "all": "⚖️ Обидві"}
            await bot.answer_callback(cb_id, f"🎯 Фокус: {reg_name} ({side_labels.get(side, 'Обидві')})")

            confirm_text, confirm_kb = await format_focus_confirmed_screen(b_id, side=side)
            if msg_id:
                await bot.edit_message(chat_id, msg_id, confirm_text, confirm_kb)
            else:
                await bot.send_message(chat_id, confirm_text, confirm_kb)
            return

    elif data == "bounty_unfocus":
        focused = bot.subscribers_db.get_user_focused_battle(chat_id)
        prev_name = focused.get("battle_name") if focused else "битви"
        bot.subscribers_db.clear_user_focused_battle(chat_id)
        await bot.answer_callback(cb_id, "🎯 Фокус битви знято")
        if msg_id:
            await bot.edit_message(
                chat_id,
                msg_id,
                build_bounties_menu_text(bot.subscribers_db, chat_id),
                build_bounties_menu_keyboard(bot.subscribers_db, chat_id)
            )
        else:
            await bot.send_message(
                chat_id,
                f"🎯 <b>Фокус знято!</b> Відстеження битви {prev_name} припинено. Відновлено стандартні налаштування сповіщень.",
                build_bounties_menu_keyboard(bot.subscribers_db, chat_id)
            )
        return

    elif data == "sniper_menu_threshold":
        curr_th = bot.subscribers_db.get_user_threshold(chat_id)
        th_text = (
            f"⚙️ <b>Налаштування вашого особистого порогу урону</b>\n\n"
            f"Ваш поточний поріг: <b>{curr_th:,} dmg</b>\n\n"
            f"Бот відсіює битви особисто для вас і надсилає пуші лише тоді, коли для фіолетового дропу потрібно не більше цього значення.\n\n"
            f"Оберіть бажаний поріг або введіть <code>/threshold 75k</code>:"
        ).replace(",", " ")
        if msg_id:
            await bot.edit_message(chat_id, msg_id, th_text, build_threshold_keyboard())
        return

    elif data.startswith("set_th_"):
        new_th = int(data.replace("set_th_", ""))
        bot.subscribers_db.set_user_threshold(chat_id, new_th)
        th_display = "Без обмежень" if new_th > 10000000 else f"{new_th:,} dmg".replace(",", " ")
        await bot.answer_callback(cb_id, f"Ваш особистий поріг: {th_display}")
        if msg_id:
            await bot.edit_message(chat_id, msg_id, build_sniper_menu_text(bot.subscribers_db, chat_id), build_sniper_menu_keyboard(bot.subscribers_db, chat_id))
        return


async def handle_text_message(bot: Any, msg: dict):
    text = (msg.get("text") or "").strip()
    from_user = msg.get("from", {})
    chat = msg.get("chat", {})
    chat_id = str(chat.get("id"))

    bot.subscribers_db.register_user(
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
    if not bot.subscribers_db.is_authorized(chat_id):
        auth_success = False
        if first_word in ("/start", "/auth", "/login", "/пароль", "/вхід") and len(words) > 1:
            auth_success = bot.subscribers_db.authorize_user(chat_id, words[1].strip())
        elif text and not text.startswith("/"):
            auth_success = bot.subscribers_db.authorize_user(chat_id, text.strip())

        if auth_success:
            await bot.send_message(
                chat_id,
                "🎉 <b>Доступ надано!</b> Ласкаво просимо до Снайпера Клану WarEra ⚔️\n\n"
                "Пароль успішно підтверджено. Тепер ви маєте повний доступ до снайпінгу битв."
            )
            await bot.send_message(chat_id, build_panel_text(bot.subscribers_db, chat_id), build_main_keyboard(bot.subscribers_db, chat_id))
            return
        else:
            await bot.send_auth_prompt(chat_id)
            return

    if first_word in ("/start", "/menu", "/help") or clean_cmd in ("start", "menu", "help", "меню", "допомога"):
        await bot.send_message(chat_id, build_panel_text(bot.subscribers_db, chat_id), build_main_keyboard(bot.subscribers_db, chat_id))

    elif first_word in ("/status", "/стан") or clean_cmd in ("status", "стан", "статус"):
        await bot.send_message(chat_id, build_panel_text(bot.subscribers_db, chat_id), build_main_keyboard(bot.subscribers_db, chat_id))

    elif first_word in ("/battles", "/битви", "/purple", "/фіол") or clean_cmd in ("battles", "битви", "purple", "фіол"):
        await bot.send_message(chat_id, "🔍 <i>Аналізую битви та шукаю фіолетовий дроп...</i>")
        txt = await bot._get_battles_text(sniper_only=False, chat_id=chat_id)
        await bot.send_message(chat_id, txt)

    elif first_word in ("/bounties", "/баунті") or clean_cmd in ("bounties", "баунті"):
        await bot.send_message(chat_id, "💰 <i>Шукаю відкриті баунті з оплатою за урон...</i>")
        txt, kb = await bot._get_contracts_data(chat_id=chat_id)
        await bot.send_message(chat_id, txt, reply_markup=kb)

    elif first_word in ("/contracts", "/контракти", "/auctions", "/аукціони") or clean_cmd in ("contracts", "контракти", "auctions", "аукціони"):
        await bot.send_message(chat_id, "📜 <i>Шукаю активні найманські аукціони контрактів...</i>")
        txt = await bot._get_auctions_text(chat_id=chat_id)
        await bot.send_message(chat_id, txt)

    elif first_word in ("/snipe", "/снайп", "/hot", "/гарячі") or clean_cmd in ("snipe", "снайп", "hot"):
        await bot.send_message(chat_id, "🎯 <i>Шукаю битви на фінішній прямі (15–20 хв до кінця)...</i>")
        txt = await bot._get_battles_text(sniper_only=True, chat_id=chat_id)
        await bot.send_message(chat_id, txt)

    elif first_word in ("/threshold", "/поріг", "/dmg", "/урон") or clean_cmd in ("threshold", "поріг", "dmg", "урон"):
        if len(words) > 1:
            raw_val = words[1].lower().replace("k", "000").replace("к", "000").replace("m", "000000").replace("м", "000000")
            try:
                val = int(raw_val)
                bot.subscribers_db.set_user_threshold(chat_id, val)
                await bot.send_message(chat_id, f"✅ <b>Ваш особистий поріг оновлено:</b> <code>{val:,} dmg</code>\nТепер ви отримуватимете пуші та результати /snipe тільки для битв до цього урону.".replace(",", " "))
            except ValueError:
                await bot.send_message(chat_id, "⚠️ Будь ласка, вкажіть число, наприклад: <code>/threshold 75000</code> або <code>/threshold 75k</code>")
        else:
            curr_th = bot.subscribers_db.get_user_threshold(chat_id)
            await bot.send_message(chat_id, f"🎯 <b>Ваш особистий поріг снайпінгу:</b> <code>{curr_th:,} dmg</code>\nЩоб змінити, введіть: <code>/threshold 75000</code> або натисніть кнопку в меню.".replace(",", " "))

    elif first_word in ("/sniper_on",) or clean_cmd in ("sniper_on", "вкл"):
        bot.subscribers_db.set_sniper_alerts(chat_id, True)
        await bot.send_message(
            chat_id,
            "🎯 <b>Снайпінг битв:</b> Сповіщення за 15–20 хв до кінця раунду <b>УВІМКНЕНО 🟢</b>\n\n"
            "Ви отримуватимете особисте повідомлення, щойно з'явиться бій на фінішній прямі з фіолетовим дропом."
        )

    elif first_word in ("/sniper_off",) or clean_cmd in ("sniper_off", "викл"):
        bot.subscribers_db.set_sniper_alerts(chat_id, False)
        await bot.send_message(
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
                bot.subscribers_db.set_user_min_bounty_rate(chat_id, val)
                disp = f"≥ {val} 🪙 / 1k" if val > 0 else "Всі (без обмежень)"
                await bot.send_message(
                    chat_id,
                    f"✅ <b>Ваш поріг баунті оновлено:</b> <code>{disp}</code>\n\n"
                    f"Тепер ви отримуватимете пуш-сповіщення тільки про баунті з виплатою від {val} монет за 1k урону."
                )
            except ValueError:
                await bot.send_message(chat_id, "⚠️ Будь ласка, вкажіть число, наприклад: <code>/bounty_rate 0.07</code> або <code>/rate 0.05</code>")
        else:
            curr_rate = bot.subscribers_db.get_user_min_bounty_rate(chat_id)
            disp = f"≥ {curr_rate} 🪙 / 1k" if curr_rate > 0 else "Всі (без обмежень)"
            await bot.send_message(
                chat_id,
                f"💵 <b>Ваш поточний мінімальний поріг баунті:</b> <code>{disp}</code>\n\n"
                f"Щоб змінити, введіть: <code>/bounty_rate 0.07</code> або оберіть значення в меню /start."
            )

    elif first_word in ("/bounties_on", "/баунті_вкл") or clean_cmd in ("bounties_on", "баунті_вкл"):
        bot.subscribers_db.set_contract_alerts(chat_id, True)
        curr_rate = bot.subscribers_db.get_user_min_bounty_rate(chat_id)
        rate_disp = f"≥ {curr_rate} 🪙 / 1k" if curr_rate > 0 else "від 0.01 🪙"
        await bot.send_message(
            chat_id,
            f"💰 <b>Баунті на урон:</b> Сповіщення <b>УВІМКНЕНО 🟢</b>\n\n"
            f"🎯 <b>Ваш фільтр ставки:</b> <code>{rate_disp}</code>\n"
            f"Ви отримуватимете особисте сповіщення, щойно з'явиться баунті з виплатою від {rate_disp}."
        )

    elif first_word in ("/bounties_off", "/баунті_викл") or clean_cmd in ("bounties_off", "баунті_викл"):
        bot.subscribers_db.set_contract_alerts(chat_id, False)
        await bot.send_message(
            chat_id,
            "💰 <b>Баунті на урон:</b> Сповіщення <b>ВИМКНЕНО 🔴</b>\n\n"
            "Автоматичні пуші вимкнено. Ви можете перевірити активні виплати в будь-який час через /bounties."
        )

    elif first_word in ("/focus", "/bounty_focus", "/фокус") or clean_cmd in ("focus", "bounty_focus", "фокус"):
        if len(words) > 1:
            raw_arg = " ".join(words[1:]).strip()
            side_override = None
            tokens = raw_arg.split()
            clean_tokens = []
            for t in tokens:
                tl = t.lower()
                if tl in ("def", "defense", "defend", "деф", "оборона", "захист"):
                    side_override = "defender"
                elif tl in ("att", "attack", "atk", "атк", "атака", "напад"):
                    side_override = "attacker"
                elif tl in ("all", "both", "всі", "все", "обидві"):
                    side_override = "all"
                else:
                    clean_tokens.append(t)

            search_query = " ".join(clean_tokens).strip() or raw_arg
            url_match = re.search(r"battle/([a-f0-9]{24})", search_query)
            target_bid = url_match.group(1) if url_match else None
            if not target_bid and re.match(r"^[a-f0-9]{24}$", search_query):
                target_bid = search_query

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
                q = search_query.lower()
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
                if side_override:
                    bot.subscribers_db.set_user_focused_battle(chat_id, bid, bname, side=side_override)
                    confirm_text, confirm_kb = await format_focus_confirmed_screen(bid, side=side_override)
                    await bot.send_message(chat_id, confirm_text, confirm_kb)
                else:
                    side_text, side_kb = await format_focus_side_screen(bot.subscribers_db, bid, chat_id=chat_id)
                    await bot.send_message(chat_id, side_text, side_kb)
            else:
                await bot.send_message(
                    chat_id,
                    f"⚠️ Не вдалося знайти активну битву за запитом: <code>{raw_arg}</code>\n"
                    f"Оберіть битву зі списку нижче:",
                )
                text, kb = await format_focus_select_screen(bot.subscribers_db, chat_id=chat_id)
                await bot.send_message(chat_id, text, kb)
        else:
            text, kb = await format_focus_select_screen(bot.subscribers_db, chat_id=chat_id)
            await bot.send_message(chat_id, text, kb)

    elif first_word in ("/unfocus", "/bounty_unfocus", "/розфокус") or clean_cmd in ("unfocus", "bounty_unfocus", "розфокус"):
        focused = bot.subscribers_db.get_user_focused_battle(chat_id)
        prev_name = focused.get("battle_name") if focused else "битви"
        bot.subscribers_db.clear_user_focused_battle(chat_id)
        await bot.send_message(
            chat_id,
            f"🎯 <b>Фокус відстеження битви знято.</b>\n\n"
            f"Більше не відстежуємо <b>{prev_name}</b>.\n"
            f"Відновлено стандартні налаштування сповіщень про баунті.",
            build_bounties_menu_keyboard(bot.subscribers_db, chat_id)
        )

    elif first_word in ("/contract_budget", "/cb", "/бюджет") or clean_cmd in ("contract_budget", "cb", "бюджет"):
        if len(words) > 1:
            raw_val = words[1].replace(",", ".")
            try:
                val = float(raw_val)
                if val < 0:
                    val = 0.0
                bot.subscribers_db.set_user_min_contract_budget(chat_id, val)
                disp = f"≥ {val:g} 🪙" if val > 0 else "Всі (без обмежень)"
                await bot.send_message(
                    chat_id,
                    f"✅ <b>Ваш поріг бюджету контракту оновлено:</b> <code>{disp}</code>\n\n"
                    f"Тепер ви отримуватимете пуш-сповіщення тільки про аукціони з бюджетом від {val:g} монет."
                )
            except ValueError:
                await bot.send_message(chat_id, "⚠️ Будь ласка, вкажіть число, наприклад: <code>/contract_budget 50</code> або <code>/cb 100</code>")
        else:
            curr_budget = bot.subscribers_db.get_user_min_contract_budget(chat_id)
            disp = f"≥ {curr_budget:g} 🪙" if curr_budget > 0 else "Всі (без обмежень)"
            await bot.send_message(
                chat_id,
                f"💰 <b>Ваш поточний мінімальний поріг бюджету контракту:</b> <code>{disp}</code>\n\n"
                f"Щоб змінити, введіть: <code>/contract_budget 50</code> або оберіть значення в меню /start."
            )

    elif first_word in ("/auctions_on", "/contracts_on", "/контракти_вкл") or clean_cmd in ("auctions_on", "contracts_on", "контракти_вкл"):
        bot.subscribers_db.set_auction_alerts(chat_id, True)
        curr_budget = bot.subscribers_db.get_user_min_contract_budget(chat_id)
        budget_disp = f"≥ {curr_budget:g} 🪙" if curr_budget > 0 else "від 0 🪙"
        await bot.send_message(
            chat_id,
            f"📜 <b>Найманські аукціони контрактів:</b> Сповіщення <b>УВІМКНЕНО 🟢</b>\n\n"
            f"💰 <b>Ваш фільтр бюджету:</b> <code>{budget_disp}</code>\n"
            f"Ви отримуватимете особисте сповіщення, щойно країна виставить контракт на аукціон!"
        )

    elif first_word in ("/auctions_off", "/contracts_off", "/контракти_викл") or clean_cmd in ("auctions_off", "contracts_off", "контракти_викл"):
        bot.subscribers_db.set_auction_alerts(chat_id, False)
        await bot.send_message(
            chat_id,
            "📜 <b>Найманські аукціони контрактів:</b> Сповіщення <b>ВИМКНЕНО 🔴</b>\n\n"
            "Автоматичні пуші вимкнено. Ви можете перевірити активні аукціони в будь-який час через /contracts."
        )

    elif first_word in ("/revoke", "/відкликати") and len(words) > 1:
        if not bot._is_admin(from_user.get("id"), chat_id):
            await bot.send_message(chat_id, "⛔ Команда доступна лише адміністратору.")
            return
        target_cid = words[1].strip()
        bot.subscribers_db.revoke_user(target_cid)
        await bot.send_message(chat_id, f"🔒 Доступ для користувача <code>{target_cid}</code> відкликано.")

    elif first_word in ("/subscribers", "/users") or clean_cmd in ("subscribers", "users", "бійці"):
        if not bot._is_admin(from_user.get("id"), chat_id):
            await bot.send_message(chat_id, "⛔ Список підписників доступний лише адміністратору.")
            return
        all_subs = bot.subscribers_db.get_all_subscribers()
        sub_text = f"👥 <b>Підписники снайпер-бота ({len(all_subs)} бійців):</b>\n\n"
        for cid, u in all_subs.items():
            name = u.get("first_name", "Fighter")
            uname = f"@{u['username']}" if u.get("username") and u['username'] != "Unknown" else "без юзернейму"
            s_ico = "🎯" if u.get("sniper_alerts", True) else "⚪"
            c_ico = "💰" if u.get("contract_alerts", False) else "⚪"
            a_ico = "📜" if u.get("auction_alerts", False) else "⚪"
            sub_text += f"• <code>{cid}</code>: <b>{name}</b> ({uname}) [{s_ico} {c_ico} {a_ico}]\n"
        await bot.send_message(chat_id, sub_text)
