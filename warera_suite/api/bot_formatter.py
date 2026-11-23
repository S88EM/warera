"""
Telegram HTML Message Templates & Formatters for WarEra Sniper Bot.
Produces rich formatted alerts, overview panels, and combat/bounty reports.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
import config
from battle_analyzer import get_shared_battle_analyzer

logger = logging.getLogger("WarEraBotFormatter")


def build_panel_text(subscribers_db: Any, chat_id: Optional[str] = None) -> str:
    user_prefs = subscribers_db.get_user_prefs(chat_id) if chat_id else {}
    sniper_on = user_prefs.get("sniper_alerts", True)
    contract_on = user_prefs.get("contract_alerts", False)
    auction_on = user_prefs.get("auction_alerts", False)
    subs_count = subscribers_db.count()

    user_th = subscribers_db.get_user_threshold(chat_id) if chat_id else getattr(config, "SNIPER_MAX_DAMAGE", 75000)
    formatted_max = f"{user_th:,}".replace(",", " ")

    min_rate = subscribers_db.get_user_min_bounty_rate(chat_id) if chat_id else 0.0
    rate_display = f"≥ {min_rate} 🪙 / 1k" if min_rate > 0 else "Всі (від 0.01)"

    min_budget = subscribers_db.get_user_min_contract_budget(chat_id) if chat_id else 0.0
    budget_display = f"≥ {min_budget:g} 🪙" if min_budget > 0 else "Всі (від 0)"

    focused = subscribers_db.get_user_focused_battle(chat_id) if chat_id else None
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


def build_sniper_menu_text(subscribers_db: Any, chat_id: Optional[str] = None) -> str:
    user_prefs = subscribers_db.get_user_prefs(chat_id) if chat_id else {}
    sniper_on = user_prefs.get("sniper_alerts", True)
    user_th = subscribers_db.get_user_threshold(chat_id) if chat_id else getattr(config, "SNIPER_MAX_DAMAGE", 75000)
    formatted_max = f"{user_th:,}".replace(",", " ")

    return (
        f"🎯 <b>Меню: Снайпер фіолетового дропу (T4 Epic+)</b>\n\n"
        f"⚙️ <b>Ваш особистий поріг:</b> ≤ <code>{formatted_max} dmg</code>\n"
        f"🔔 <b>Автосповіщення:</b> <b>{'🟢 УВІМКНЕНО' if sniper_on else '🔴 ВИМКНЕНО'}</b>\n\n"
        f"⏳ <i>Бот відслідковує битви на фінішній прямі (15–20 хв до кінця раунду), "
        f"де розраховано гарантований фіолетовий лут і потрібний дамаг не перевищує ваш поріг.</i>\n\n"
        f"<i>Скористайтеся кнопками нижче:</i>"
    )


def build_bounties_menu_text(subscribers_db: Any, chat_id: Optional[str] = None) -> str:
    user_prefs = subscribers_db.get_user_prefs(chat_id) if chat_id else {}
    contract_on = user_prefs.get("contract_alerts", False)
    min_rate = subscribers_db.get_user_min_bounty_rate(chat_id) if chat_id else 0.0
    rate_display = f"≥ {min_rate} 🪙 / 1k" if min_rate > 0 else "Всі (без обмежень)"
    focused = subscribers_db.get_user_focused_battle(chat_id) if chat_id else None

    if focused:
        f_side = focused.get("side", "all")
        side_badge = "⚔️ Тільки Атака" if f_side == "attacker" else ("🛡 Тільки Оборона" if f_side == "defender" else "⚖️ Обидві сторони")
        enemy_note = " (баунті супротивника відфільтровано)" if f_side in ("attacker", "defender") else ""
        return (
            f"💰 <b>Меню: Баунті за урон (Bounties)</b>\n\n"
            f"🎯 <b>Фокус на битві:</b> <b>⚔️ {focused['battle_name']}</b>\n"
            f"🛡 <b>Сторона:</b> <b>{side_badge}</b>{enemy_note}\n"
            f"🔔 <b>Режим відстеження:</b> Тільки ця битва (будь-яка ставка)\n"
            f"🔕 <b>Фільтр спаму:</b> Інші битви приховані\n"
            f"💵 <b>Ваш поріг ставки (загальний):</b> <code>{rate_display}</code>\n\n"
            f"🎯 <i>Ви стежите за битвою <b>{focused['battle_name']}</b> ({side_badge}). "
            f"Бот сповістить про <b>БУДЬ-ЯКЕ баунті</b> для цієї сторони та не спамитиме іншими.\n\n"
            f"Фокус скинеться автоматично, коли битва закінчиться, або ви можете змінити сторону чи зняти його нижче.</i>"
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


def build_auctions_menu_text(subscribers_db: Any, chat_id: Optional[str] = None) -> str:
    user_prefs = subscribers_db.get_user_prefs(chat_id) if chat_id else {}
    auction_on = user_prefs.get("auction_alerts", False)
    min_budget = subscribers_db.get_user_min_contract_budget(chat_id) if chat_id else 0.0
    budget_str = f"≥ {min_budget:g} 🪙" if min_budget > 0 else "Всі (без обмежень)"

    return (
        f"📜 <b>Меню: Найманські аукціони контрактів</b>\n\n"
        f"💰 <b>Ваш поріг бюджету:</b> <code>{budget_str}</code>\n"
        f"🔔 <b>Автосповіщення:</b> <b>{'🟢 УВІМКНЕНО' if auction_on else '🔴 ВИМКНЕНО'}</b>\n\n"
        f"⏱ <i>Коли країна виставляє новий контракт на битву, починається аукціон (тривалістю кілька хвилин). "
        f"Військові підрозділи роблять ставки, щоб забрати цей контракт собі.</i>\n\n"
        f"<i>Скористайтеся кнопками нижче:</i>"
    )


def format_battles_text(battles: List[Dict[str, Any]], sniper_only: bool, max_dmg: int) -> str:
    formatted_max = f"{max_dmg:,}".replace(",", " ")

    if sniper_only:
        target_battles = [
            b for b in battles
            if b.get("type") != "tournament"
            and b.get("timing", {}).get("isSniperWindow")
            and b.get("roundCutoff", {}).get("has_purple")
            and (b.get("roundCutoff", {}).get("min_damage_for_purple") or 0) <= max_dmg
        ]
        if not target_battles:
            exceeded = [
                b for b in battles
                if b.get("type") != "tournament"
                and b.get("timing", {}).get("isSniperWindow")
                and b.get("roundCutoff", {}).get("has_purple")
                and (b.get("roundCutoff", {}).get("min_damage_for_purple") or 0) > max_dmg
            ]
            active_only = [
                b for b in battles
                if b.get("type") != "tournament"
                and b.get("timing", {}).get("minutesLeft", 0) > 0
                and b.get("roundCutoff", {}).get("has_purple")
            ]
            sorted_by_time = sorted(active_only or [b for b in battles if b.get("type") != "tournament"], key=lambda x: x.get("timing", {}).get("minutesLeft", 999))
            next_battle = sorted_by_time[0] if sorted_by_time else None
            next_eta = next_battle['timing']['formattedEta'].lstrip("~") if next_battle else "—"
            next_name = next_battle['region']['name'] if next_battle else "—"

            exceeded_text = ""
            if exceeded:
                exceeded_list = [f"• {b['region']['name']}: <code>{b['roundCutoff']['min_damage_for_purple']:,} dmg</code> ({b['roundCutoff']['last_purple_item']['name']})".replace(",", " ") for b in exceeded[:3]]
                exceeded_text = f"\n🚫 <b>Відсіяно через перевищення порогу ({formatted_max} dmg):</b>\n" + "\n".join(exceeded_list) + "\n"

            return (
                f"🎯 <b>Снайперське вікно (поріг ≤ {formatted_max} dmg):</b>\n\n"
                f"⚠️ <i>Наразі немає відкритих битв у 15–20 хв вікні з уроном до {formatted_max} dmg.</i>\n"
                f"{exceeded_text}\n"
                f"⏳ Найбільш зрілий раунд: <b>{next_name}</b> (~{next_eta} до кінця).\n"
                f"💡 <i>Всі битви, що вимагають більше {formatted_max} урону, автоматично відсіюються.</i>\n\n"
                f"Щоб переглянути всі активні битви, надішліть /battles"
            )
    else:
        target_battles = [
            b for b in battles
            if b.get("type") != "tournament"
            and (
                (b.get("roundCutoff", {}).get("has_purple") and (b.get("roundCutoff", {}).get("min_damage_for_purple") or 0) <= max_dmg)
                or (b.get("battleCutoff", {}).get("has_purple") and (b.get("battleCutoff", {}).get("min_damage_for_purple") or 0) <= max_dmg)
            )
        ]

    msg = f"🎯 <b>WarEra · Снайпер фіолетового дропу (≤ {formatted_max} dmg):</b>\n\n" if sniper_only else f"⚔️ <b>WarEra · Активні битви (поріг ≤ {formatted_max} dmg):</b>\n\n"
    if not target_battles:
        all_purple = [b for b in battles if b.get("type") != "tournament" and (b.get("roundCutoff", {}).get("has_purple") or b.get("battleCutoff", {}).get("has_purple"))]
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


def format_contracts_text(contracts: List[Dict[str, Any]], user_min: float, focused: Optional[Dict[str, Any]]) -> str:
    msg = "💰 <b>WarEra · Активні Баунті за урон (Bounties):</b>\n\n"
    if focused:
        msg += f"🎯 <i>Ваш поточний фокус: <b>{focused['battle_name']}</b> (сповіщення про всі баунті в ній)</i>\n\n"
    elif user_min > 0:
        msg += f"<i>(Ваш фільтр сповіщень: від ≥ {user_min} 🪙 / 1k dmg)</i>\n\n"

    for idx, c in enumerate(contracts[:8], 1):
        reg = c['region']
        btype = "Війна" if c['type'] == 'war' else ("Повстання" if c['type'] == 'resistance' else ("Турнір" if c['type'] == 'tournament' else str(c['type']).capitalize()))
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

    return msg


def format_auctions_text(auctions: List[Dict[str, Any]], user_min_budget: float = 0.0) -> str:
    if not auctions:
        return (
            "📜 <b>WarEra · Активні Найманські Аукціони Контрактів:</b>\n\n"
            "<i>Наразі немає відкритих аукціонів контрактів від країн.</i>\n\n"
            "💡 <i>Коли країна виставляє контракт на битву, аукціон триває лише кілька хвилин! "
            "Підрозділи змагаються ставками за право забрати контракт. Бот надішле сповіщення миттєво, щойно з'явиться новий лот.</i>"
        )

    msg = "📜 <b>WarEra · Активні Найманські Аукціони Контрактів:</b>\n\n"
    if user_min_budget > 0:
        msg += f"<i>(Ваш фільтр бюджету: ≥ {user_min_budget:g} 🪙)</i>\n\n"

    for idx, a in enumerate(auctions[:8], 1):
        reg = a['region']
        btype = "Війна" if a['type'] == 'war' else ("Повстання" if a['type'] == 'resistance' else ("Турнір" if a['type'] == 'tournament' else str(a['type']).capitalize()))
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


async def format_focus_select_screen(subscribers_db: Any, chat_id: Optional[str] = None, page: int = 0) -> Tuple[str, dict]:
    from bot_keyboards import build_focus_select_keyboard
    try:
        analyzer = get_shared_battle_analyzer()
        active_list = await analyzer.get_active_battles_for_focus()
    except Exception as e:
        logger.error(f"Error getting active battles for focus: {e}")
        active_list = []

    focused = subscribers_db.get_user_focused_battle(chat_id) if chat_id else None
    cur_focus_text = ""
    if focused:
        f_side = focused.get("side", "all")
        side_badge = "⚔️ Атака" if f_side == "attacker" else ("🛡 Оборона" if f_side == "defender" else "⚖️ Обидві сторони")
        cur_focus_text = f"🎯 <b>Поточний фокус:</b> <b>⚔️ {focused['battle_name']}</b> (<i>{side_badge}</i>)\n\n"

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
        f"• Ви обираєте <b>свою сторону</b> (Атака або Оборона).\n"
        f"• Отримуватимете пуші про <b>БУДЬ-ЯКЕ баунті</b> для вашої сторони.\n"
        f"• Баунті <b>противника</b> та інші битви <b>не спамитимуть</b>.\n"
        f"• Щойно битва завершиться, фокус <b>автоматично зніметься</b>.\n"
        f"• Ви можете змінити сторону або зняти фокус будь-коли кнопкою."
    )

    kb = build_focus_select_keyboard(page_battles, page, total_pages, focused.get("battle_id") if focused else None)
    return text, kb


async def format_focus_side_screen(subscribers_db: Any, battle_id: str, chat_id: Optional[str] = None) -> Tuple[str, dict]:
    from bot_keyboards import build_focus_side_keyboard
    try:
        analyzer = get_shared_battle_analyzer()
        active_list = await analyzer.get_active_battles_for_focus()
        b_match = next((b for b in active_list if b.get('battleId') == battle_id), None)
        if not b_match:
            raw_b = await analyzer.fetch_active_battles()
            raw = next((b for b in raw_b if b.get('_id') == battle_id), None)
            if raw:
                def_c = raw.get('defender', {}).get('country')
                att_c = raw.get('attacker', {}).get('country')
                reg_id = raw.get('defender', {}).get('region')
                reg_name = analyzer._regions_cache.get(reg_id, {}).get('name', 'Битва')
                att_name = analyzer._countries_cache.get(att_c, {}).get('name', 'Атака')
                att_flag = analyzer._countries_cache.get(att_c, {}).get('flag', '🏳️')
                def_name = analyzer._countries_cache.get(def_c, {}).get('name', 'Оборона')
                def_flag = analyzer._countries_cache.get(def_c, {}).get('flag', '🏳️')
                r_num = raw.get('currentRound', {}).get('number', 1)
                b_match = {
                    'battleId': battle_id,
                    'regionName': reg_name,
                    'roundNumber': r_num,
                    'attackerCountry': att_name,
                    'attackerFlag': att_flag,
                    'defenderCountry': def_name,
                    'defenderFlag': def_flag,
                    'attackerRate': 0.0,
                    'defenderRate': 0.0,
                    'hasBounty': False
                }
    except Exception as e:
        logger.error(f"Error in format_focus_side_screen: {e}")
        b_match = None

    if not b_match:
        text = "❌ <b>Битву не знайдено або вона вже завершилась.</b>"
        kb = {
            "inline_keyboard": [
                [{"text": "🔙 До вибору битви", "callback_data": "menu_bounty_focus_select"}],
                [{"text": "💰 Меню Баунті", "callback_data": "menu_bounties"}]
            ]
        }
        return text, kb

    reg_name = b_match.get('regionName', 'Битва')
    r_num = b_match.get('roundNumber', 1)
    att_c = b_match.get('attackerCountry', 'Атака')
    att_f = b_match.get('attackerFlag', '🏳️')
    def_c = b_match.get('defenderCountry', 'Оборона')
    def_f = b_match.get('defenderFlag', '🏳️')

    att_rate = b_match.get('attackerRate', 0.0)
    def_rate = b_match.get('defenderRate', 0.0)
    att_rate_str = f" • 💵 <code>{att_rate}🪙/1k</code>" if att_rate > 0 else " • <i>(без баунті)</i>"
    def_rate_str = f" • 💵 <code>{def_rate}🪙/1k</code>" if def_rate > 0 else " • <i>(без баунті)</i>"

    focused = subscribers_db.get_user_focused_battle(chat_id) if chat_id else None
    cur_side = focused.get("side", "all") if (focused and focused.get("battle_id") == battle_id) else None

    text = (
        f"🎯 <b>Вибір сторони: ⚔️ {reg_name}</b> (Раунд #{r_num})\n\n"
        f"<i>За яку сторону ви б'єтеся в цій битві?</i>\n"
        f"Бот надсилатиме сповіщення <b>тільки про баунті вашої сторони</b>, а пуші від супротивника будуть заблоковані:\n\n"
        f"⚔️ <b>Атака:</b> {att_f} <b>{att_c}</b>{att_rate_str}\n"
        f"🛡 <b>Оборона:</b> {def_f} <b>{def_c}</b>{def_rate_str}\n\n"
        f"Оберіть сторону для моніторингу:"
    )

    kb = build_focus_side_keyboard(battle_id, att_c, def_c, att_f, def_f)
    return text, kb


async def format_focus_confirmed_screen(battle_id: str, side: str = "all") -> Tuple[str, dict]:
    from bot_keyboards import build_focus_confirmed_keyboard
    analyzer = get_shared_battle_analyzer()
    active_list = await analyzer.get_active_battles_for_focus()
    b_match = next((b for b in active_list if b.get('battleId') == battle_id), None)
    reg_name = b_match.get('regionName', 'Битва') if b_match else "Битва"
    att_c = b_match.get('attackerCountry', 'Атака') if b_match else 'Атака'
    att_f = b_match.get('attackerFlag', '🏳️') if b_match else '🏳️'
    def_c = b_match.get('defenderCountry', 'Оборона') if b_match else 'Оборона'
    def_f = b_match.get('defenderFlag', '🏳️') if b_match else '🏳️'

    side_labels = {
        "attacker": f"⚔️ Тільки Атака ({att_f} {att_c})",
        "defender": f"🛡 Тільки Оборона ({def_f} {def_c})",
        "all": "⚖️ Обидві сторони"
    }
    side_label = side_labels.get(side, "⚖️ Обидві сторони")

    bounty_info = ""
    if b_match:
        att_r = b_match.get('attackerRate', 0.0)
        def_r = b_match.get('defenderRate', 0.0)
        if side == "attacker" and att_r > 0:
            bounty_info = f"💵 <b>Поточна ставка атаки:</b> <code>{att_r} монет / 1k dmg</code>\n"
        elif side == "defender" and def_r > 0:
            bounty_info = f"💵 <b>Поточна ставка оборони:</b> <code>{def_r} монет / 1k dmg</code>\n"
        elif side == "all" and b_match.get('hasBounty'):
            bounty_info = f"💵 <b>Максимальна ставка:</b> <code>{b_match.get('maxBountyRate')} монет / 1k dmg</code>\n"

    enemy_filter_text = (
        "🔕 <b>Фільтр противника:</b> Баунті ворожої сторони та інших битв <b>повністю приховані</b>!\n\n"
        if side in ("attacker", "defender")
        else "🔕 <b>Фільтр спаму:</b> Інші битви не надсилатимуться.\n\n"
    )

    confirm_text = (
        f"✅ <b>Фокус на битву активовано!</b>\n\n"
        f"⚔️ <b>Битва:</b> <b>{reg_name}</b>\n"
        f"🎯 <b>Відстеження сторони:</b> <b>{side_label}</b>\n"
        f"{bounty_info}"
        f"🔔 <b>Режим відстеження:</b> Сповіщення про <b>БУДЬ-ЯКЕ баунті</b> вашої сторони (поріг ставки ігнорується)\n"
        f"{enemy_filter_text}"
        f"<i>Фокус автоматично зніметься при закінченні битви. Нижче ви можете будь-коли перемкнути сторону або скинути фокус:</i>"
    )
    confirm_kb = build_focus_confirmed_keyboard(battle_id)
    return confirm_text, confirm_kb
