"""
Shared asynchronous Telegram Bot HTTP transport for WarEra bots.
Consolidates httpx.AsyncClient lifecycle, send_message, edit_message,
and answer_callback across TelegramBotController and SniperBotController.
"""

import logging
from typing import Optional, Dict, Any
import httpx

logger = logging.getLogger("WarEraTelegramBase")


class BaseTelegramBot:
    def __init__(self, token: Optional[str] = None):
        self.token = (token or "").strip()
        self.base_url = f"https://api.telegram.org/bot{self.token}" if self.token else ""
        self._http_client: Optional[httpx.AsyncClient] = None

    async def get_client(self) -> httpx.AsyncClient:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=35.0)
        return self._http_client

    async def close(self):
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()

    async def send_message(
        self,
        chat_id: str,
        text: str,
        reply_markup: Optional[dict] = None,
    ) -> Optional[int]:
        if not self.token:
            return None
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
            if resp.status_code == 200:
                return resp.json().get("result", {}).get("message_id")
        except Exception as e:
            logger.error(f"Error sending Telegram message to {chat_id}: {e}")
        return None

    async def edit_message(
        self,
        chat_id: str,
        message_id: int,
        text: str,
        reply_markup: Optional[dict] = None,
    ) -> bool:
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
            logger.error(f"Error editing Telegram message {message_id} in {chat_id}: {e}")
            return False

    async def answer_callback(
        self,
        callback_query_id: str,
        text: Optional[str] = None,
        show_alert: bool = False,
    ):
        if not self.token:
            return
        client = await self.get_client()
        payload: Dict[str, Any] = {"callback_query_id": callback_query_id}
        if text:
            payload["text"] = text
            payload["show_alert"] = show_alert
        try:
            await client.post(f"{self.base_url}/answerCallbackQuery", json=payload)
        except Exception as e:
            logger.debug(f"answerCallbackQuery failed: {e}")
