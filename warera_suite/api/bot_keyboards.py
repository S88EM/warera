"""
Telegram Inline Keyboard Builders for WarEra Sniper Bot.
Provides modular keyboards for menus, thresholds, bounties, auctions, and focus selection.
"""

from typing import Dict, Any, List, Optional
import config


def build_main_keyboard(subscribers_db: Any, chat_id: Optional[str] = None) -> dict:
    user_prefs = subscribers_db.get_user_prefs(chat_id) if chat_id else {}
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


def build_sniper_menu_keyboard(subscribers_db: Any, chat_id: Optional[str] = None) -> dict:
    user_th = subscribers_db.get_user_threshold(chat_id) if chat_id else getattr(config, "SNIPER_MAX_DAMAGE", 75000)
    formatted_th = f"{user_th // 1000}k" if user_th < 1000000 else f"{user_th // 1000000}M"

    return {
        "inline_keyboard": [
            [
                {"text": "🎯 Снайпер (15–20 хв)", "callback_data": "sniper_cmd_snipe"},
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


def build_bounties_menu_keyboard(subscribers_db: Any, chat_id: Optional[str] = None) -> dict:
    min_rate = subscribers_db.get_user_min_bounty_rate(chat_id) if chat_id else 0.0
    rate_btn = f"≥ {min_rate} 🪙" if min_rate > 0 else "Всі"
    focused = subscribers_db.get_user_focused_battle(chat_id) if chat_id else None

    rows = [
        [
            {"text": "💰 Список активних баунті", "callback_data": "sniper_cmd_contracts"},
        ]
    ]

    if focused:
        b_name = focused.get('battle_name', 'битви')
        rows.append([
            {"text": "🔄 Змінити сторону", "callback_data": f"focus_select_side_{focused['battle_id']}"},
            {"text": f"❌ Скинути фокус ({b_name[:14]})", "callback_data": "bounty_unfocus"},
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


def build_auctions_menu_keyboard(subscribers_db: Any, chat_id: Optional[str] = None) -> dict:
    min_budget = subscribers_db.get_user_min_contract_budget(chat_id) if chat_id else 0.0
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


def build_contracts_keyboard(subscribers_db: Any, contracts: List[Dict[str, Any]], chat_id: Optional[str] = None) -> dict:
    focused = subscribers_db.get_user_focused_battle(chat_id) if chat_id else None
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
        focus_btns.append({"text": f"{icon} Фокус: {reg[:13]}", "callback_data": f"focus_select_side_{bid}"})
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


def build_threshold_keyboard() -> dict:
    return {
        "inline_keyboard": [
            [
                {"text": "≤ 25k dmg", "callback_data": "set_th_25000"},
                {"text": "≤ 50k dmg", "callback_data": "set_th_50000"},
                {"text": "≤ 75k dmg", "callback_data": "set_th_75000"},
            ],
            [
                {"text": "≤ 100k dmg", "callback_data": "set_th_100000"},
                {"text": "≤ 150k dmg", "callback_data": "set_th_150000"},
                {"text": "≤ 250k dmg", "callback_data": "set_th_250000"},
            ],
            [
                {"text": "≤ 500k dmg", "callback_data": "set_th_500000"},
                {"text": "≤ 1M dmg", "callback_data": "set_th_1000000"},
                {"text": "≤ 2M dmg", "callback_data": "set_th_2000000"},
            ],
            [
                {"text": "🔙 Назад до меню снайпера", "callback_data": "menu_sniper"}
            ]
        ]
    }


def build_rate_keyboard() -> dict:
    return {
        "inline_keyboard": [
            [
                {"text": "Всі (0 🪙)", "callback_data": "set_rate_0"},
                {"text": "≥ 0.05 🪙", "callback_data": "set_rate_0.05"},
                {"text": "≥ 0.1 🪙", "callback_data": "set_rate_0.1"},
            ],
            [
                {"text": "≥ 0.15 🪙", "callback_data": "set_rate_0.15"},
                {"text": "≥ 0.2 🪙", "callback_data": "set_rate_0.2"},
                {"text": "≥ 0.3 🪙", "callback_data": "set_rate_0.3"},
            ],
            [
                {"text": "≥ 0.5 🪙", "callback_data": "set_rate_0.5"},
                {"text": "≥ 1.0 🪙", "callback_data": "set_rate_1.0"},
                {"text": "≥ 2.0 🪙", "callback_data": "set_rate_2.0"},
            ],
            [
                {"text": "🔙 Назад до меню баунті", "callback_data": "menu_bounties"}
            ]
        ]
    }


def build_budget_keyboard() -> dict:
    return {
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


def build_focus_select_keyboard(page_items: List[Dict[str, Any]], page: int, total_pages: int, focused_bid: Optional[str]) -> dict:
    rows = []
    for b in page_items:
        bid = b['battleId']
        reg = b.get('regionName') or b.get('region') or 'Битва'
        btype = "⚔️" if b.get('type') == 'war' else "✊"
        is_cur = (bid == focused_bid)
        status_icon = "✅ " if is_cur else ""
        btn_text = f"{status_icon}{btype} {reg[:18]}"
        rows.append([{"text": btn_text, "callback_data": f"focus_select_side_{bid}"}])

    nav_row = []
    if page > 0:
        nav_row.append({"text": "⬅️ Попередня", "callback_data": f"focus_page_{page-1}"})
    if page < total_pages - 1:
        nav_row.append({"text": "Наступна ➡️", "callback_data": f"focus_page_{page+1}"})
    if nav_row:
        rows.append(nav_row)

    if focused_bid:
        rows.append([{"text": "❌ Скинути поточний фокус", "callback_data": "bounty_unfocus"}])

    rows.append([{"text": "🔙 Меню Баунті", "callback_data": "menu_bounties"}])
    return {"inline_keyboard": rows}


def build_focus_side_keyboard(battle_id: str, att_country: str, def_country: str, att_flag: str, def_flag: str) -> dict:
    return {
        "inline_keyboard": [
            [
                {"text": f"🔴 Атака ({att_flag} {att_country[:12]})", "callback_data": f"focus_set_{battle_id}_attacker"},
                {"text": f"🛡 Оборона ({def_flag} {def_country[:12]})", "callback_data": f"focus_set_{battle_id}_defender"},
            ],
            [
                {"text": "⚖️ Обидві сторони (будь-яке баунті)", "callback_data": f"focus_set_{battle_id}_all"},
            ],
            [
                {"text": "🔙 Обрати іншу битву", "callback_data": "menu_bounty_focus_select"},
                {"text": "🏠 Меню Баунті", "callback_data": "menu_bounties"},
            ]
        ]
    }


def build_focus_confirmed_keyboard(battle_id: str) -> dict:
    return {
        "inline_keyboard": [
            [
                {"text": "🔄 Змінити сторону", "callback_data": f"focus_select_side_{battle_id}"},
                {"text": "❌ Скинути фокус", "callback_data": "bounty_unfocus"},
            ],
            [
                {"text": "💰 Переглянути активні баунті", "callback_data": "sniper_cmd_contracts"},
                {"text": "🏠 Головне меню", "callback_data": "menu_main"},
            ]
        ]
    }
