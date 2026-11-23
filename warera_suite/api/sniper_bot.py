"""
Autonomous Sniper Telegram Bot for WarEra Clan Members.
Features:
- Dedicated bot token & optional Clan password protection
- Multi-user notification preferences
- /snipe, /battles, /bounties, /contracts, /cb, /rate, /focus
Modularized into bot_keyboards, bot_formatter, and bot_handlers.
"""

import asyncio
import json
import logging
import os
import sys
import time
from typing import Dict, Any, List, Optional, Tuple
import httpx

# Ensure UTF-8 output
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import config
from battle_analyzer import get_shared_battle_analyzer
from subscribers_db import SubscribersDB

import bot_keyboards
import bot_formatter
import bot_handlers

logger = logging.getLogger("WarEraSniperBot")


class SniperBotController:
    def __init__(self, token: Optional[str] = None, password: Optional[str] = None):
        self.token = (token or getattr(config, "TELEGRAM_SNIPER_BOT_TOKEN", None) or os.getenv("TELEGRAM_SNIPER_BOT_TOKEN", "")).strip()
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.password = (password or getattr(config, "SNIPER_BOT_PASSWORD", "") or os.getenv("SNIPER_BOT_PASSWORD", "")).strip()
        self.subscribers_db = SubscribersDB()
        self._client: Optional[httpx.AsyncClient] = None
        self.running = False
        self._commands_registered = False

    async def get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=35.0)
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    def _is_admin(self, user_id: Optional[int], chat_id: str) -> bool:
        admin_cids = getattr(config, "TELEGRAM_CHAT_IDS", [])
        if chat_id in admin_cids or str(user_id) in admin_cids:
            return True
        return False

    # -------------------------------------------------------------------------
    # Backward-compatible Delegation Methods to Modular Components
    # -------------------------------------------------------------------------
    def _build_panel_text(self, chat_id: Optional[str] = None) -> str:
        return bot_formatter.build_panel_text(self.subscribers_db, chat_id)

    def _build_keyboard(self, chat_id: Optional[str] = None) -> dict:
        return bot_keyboards.build_main_keyboard(self.subscribers_db, chat_id)

    def _build_sniper_menu_text(self, chat_id: Optional[str] = None) -> str:
        return bot_formatter.build_sniper_menu_text(self.subscribers_db, chat_id)

    def _build_sniper_menu_keyboard(self, chat_id: Optional[str] = None) -> dict:
        return bot_keyboards.build_sniper_menu_keyboard(self.subscribers_db, chat_id)

    def _build_bounties_menu_text(self, chat_id: Optional[str] = None) -> str:
        return bot_formatter.build_bounties_menu_text(self.subscribers_db, chat_id)

    def _build_bounties_menu_keyboard(self, chat_id: Optional[str] = None) -> dict:
        return bot_keyboards.build_bounties_menu_keyboard(self.subscribers_db, chat_id)

    def _build_auctions_menu_text(self, chat_id: Optional[str] = None) -> str:
        return bot_formatter.build_auctions_menu_text(self.subscribers_db, chat_id)

    def _build_auctions_menu_keyboard(self, chat_id: Optional[str] = None) -> dict:
        return bot_keyboards.build_auctions_menu_keyboard(self.subscribers_db, chat_id)

    async def _get_battles_text(self, sniper_only: bool = False, chat_id: Optional[str] = None) -> str:
        analyzer = get_shared_battle_analyzer()
        battles = await analyzer.get_all_battles_intel()
        if not battles:
            await asyncio.sleep(0.6)
            battles = await analyzer.get_all_battles_intel(force_refresh=True)

        if not battles:
            return (
                "⏳ <b>Оновлюю дані битв із серверів WarEra...</b>\n\n"
                "Бот зараз синхронізує активні сутички. Будь ласка, спробуйте ще раз через кілька секунд."
            )

        max_dmg = self.subscribers_db.get_user_threshold(chat_id) if chat_id else getattr(config, "SNIPER_MAX_DAMAGE", 75000)
        return bot_formatter.format_battles_text(battles, sniper_only, max_dmg)

    async def _get_contracts_data(self, chat_id: Optional[str] = None) -> Tuple[str, dict]:
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
        text = bot_formatter.format_contracts_text(contracts, user_min, focused)
        kb = bot_keyboards.build_contracts_keyboard(self.subscribers_db, contracts, chat_id=chat_id)
        return text, kb

    async def _get_contracts_text(self, chat_id: Optional[str] = None) -> str:
        txt, _ = await self._get_contracts_data(chat_id=chat_id)
        return txt

    async def _get_auctions_text(self, chat_id: Optional[str] = None) -> str:
        analyzer = get_shared_battle_analyzer()
        auctions = await analyzer.get_active_contract_auctions()
        user_min = self.subscribers_db.get_user_min_contract_budget(chat_id) if chat_id else 0.0
        return bot_formatter.format_auctions_text(auctions, user_min)

    async def _build_focus_select_screen(self, chat_id: Optional[str] = None, page: int = 0) -> Tuple[str, dict]:
        return await bot_formatter.format_focus_select_screen(self.subscribers_db, chat_id=chat_id, page=page)

    async def _build_focus_side_screen(self, battle_id: str, chat_id: Optional[str] = None) -> Tuple[str, dict]:
        return await bot_formatter.format_focus_side_screen(self.subscribers_db, battle_id, chat_id=chat_id)

    async def _build_focus_confirmed_screen(self, battle_id: str, side: str = "all", chat_id: Optional[str] = None) -> Tuple[str, dict]:
        return await bot_formatter.format_focus_confirmed_screen(battle_id, side=side)

    # -------------------------------------------------------------------------
    # Telegram API Interaction
    # -------------------------------------------------------------------------

    async def register_commands(self):
        """Registers command menu in Telegram UI for the sniper bot."""
        if not self.token or self._commands_registered:
            return
        commands = [
            {"command": "start", "description": "Головне меню та налаштування"},
            {"command": "snipe", "description": "Битви на фінішній прямі (15–20 хв)"},
            {"command": "battles", "description": "Всі активні битви з фіолетовим дропом"},
            {"command": "bounties", "description": "Битви з виплатами за урон (баунті)"},
            {"command": "focus", "description": "Слідкувати за однією битвою"},
            {"command": "rate", "description": "Налаштувати мінімальну ставку баунті"},
            {"command": "cb", "description": "Налаштувати поріг бюджету контракту"},
            {"command": "auctions", "description": "Найманські аукціони контрактів"},
            {"command": "threshold", "description": "Змінити особистий поріг урону"},
            {"command": "status", "description": "Поточний статус моніторингу"},
        ]
        try:
            client = await self.get_client()
            r = await client.post(f"{self.base_url}/setMyCommands", json={"commands": commands})
            if r.status_code == 200:
                self._commands_registered = True
        except Exception as e:
            logger.debug(f"Failed to set Telegram commands: {e}")

    async def send_message(self, chat_id: str, text: str, reply_markup: Optional[dict] = None) -> bool:
        if not self.token:
            return False
        client = await self.get_client()
        payload: Dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        try:
            resp = await client.post(f"{self.base_url}/sendMessage", json=payload)
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"Error sending Sniper Bot message to {chat_id}: {e}")
            return False

    async def edit_message(self, chat_id: str, message_id: int, text: str, reply_markup: Optional[dict] = None) -> bool:
        if not self.token:
            return False
        client = await self.get_client()
        payload: Dict[str, Any] = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        try:
            resp = await client.post(f"{self.base_url}/editMessageText", json=payload)
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"Error editing message {message_id} in {chat_id}: {e}")
            return False

    async def answer_callback(self, callback_query_id: str, text: Optional[str] = None, show_alert: bool = False):
        if not self.token:
            return
        client = await self.get_client()
        payload: Dict[str, Any] = {"callback_query_id": callback_query_id}
        if text:
            payload["text"] = text
            payload["show_alert"] = show_alert
        try:
            await client.post(f"{self.base_url}/answerCallbackQuery", json=payload)
        except Exception:
            pass

    async def send_auth_prompt(self, chat_id: str):
        text = (
            "🔒 <b>Військова розвідка клану WarEra</b> ⚔️\n\n"
            "Цей бот призначений виключно для бійців нашого військового підрозділу.\n\n"
            "Будь ласка, введіть <b>пароль доступу</b> до бота у чат (або надішліть команду <code>/auth &lt;пароль&gt;</code>):\n\n"
            "<i>(Пароль можна дізнатися у командира або в закріплених повідомленнях кланового чату).</i>"
        )
        await self.send_message(chat_id, text)

    async def handle_update(self, update: dict):
        if "callback_query" in update:
            await bot_handlers.handle_callback_query(self, update["callback_query"])
        elif "message" in update:
            await bot_handlers.handle_text_message(self, update["message"])

    def stop_polling(self):
        self.running = False

    async def start_polling(self):
        """Continuously poll Telegram for updates on the Sniper Bot."""
        if not self.token:
            return

        self.running = True
        offset = 0
        logger.info("WarEra Clan Sniper Bot started polling...")
        await self.register_commands()

        while self.running:
            try:
                client = await self.get_client()
                resp = await client.get(
                    f"{self.base_url}/getUpdates",
                    params={"offset": offset, "timeout": 20},
                    timeout=25.0
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for upd in data.get("result", []):
                        offset = upd["update_id"] + 1
                        await self.handle_update(upd)
                elif resp.status_code == 409:
                    await asyncio.sleep(5)
                else:
                    await asyncio.sleep(2)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug(f"Sniper Bot polling error: {e}")
                await asyncio.sleep(3)


# Global singleton controller
_sniper_bot_controller: Optional[SniperBotController] = None


def get_sniper_bot_controller() -> SniperBotController:
    global _sniper_bot_controller
    if _sniper_bot_controller is None:
        _sniper_bot_controller = SniperBotController()
    return _sniper_bot_controller
