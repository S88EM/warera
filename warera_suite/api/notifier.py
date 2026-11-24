import sys
import logging
from typing import Optional, List
import httpx
from rich.console import Console
from rich.panel import Panel

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import config
from equipment_data import get_item_icon, get_rarity_info

console = Console()
logger = logging.getLogger("WarEraNotifier")

class Notifier:
    def __init__(
        self,
        telegram_token: Optional[str] = config.TELEGRAM_BOT_TOKEN,
        telegram_chat_ids: Optional[List[str]] = None,
        discord_webhook: Optional[str] = config.DISCORD_WEBHOOK_URL,
    ):
        self.telegram_token = telegram_token
        self.telegram_chat_ids = telegram_chat_ids if telegram_chat_ids is not None else config.TELEGRAM_CHAT_IDS
        self.discord_webhook = discord_webhook
        self._http_client: Optional[httpx.AsyncClient] = None

    def get_target_chat_ids(self) -> List[str]:
        try:
            from subscribers_db import SubscribersDB
            s_ids = SubscribersDB().get_market_chat_ids()
            if s_ids:
                return s_ids
        except Exception as e:
            logger.warning(f"Failed to load subscriber chat IDs: {e}")
        return self.telegram_chat_ids or []

    async def get_client(self) -> httpx.AsyncClient:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=10.0)
        return self._http_client

    async def close(self):
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()

    async def _send_telegram_message(self, chat_id: str, text: str):
        client = await self.get_client()
        msg_endpoint = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        try:
            resp = await client.post(msg_endpoint, json=payload)
            if resp.status_code != 200:
                logger.error(f"Failed to send Telegram alert to {chat_id}: {resp.text}")
                console.print(f"[bold red]❌ Помилка Telegram ({chat_id}, {resp.status_code}): {resp.text}[/bold red]")
        except Exception as e:
            logger.error(f"Error sending Telegram alert to {chat_id}: {e}")
            console.print(f"[bold red]❌ Виняток Telegram ({chat_id}): {e}[/bold red]")

    async def notify_equipment(self, opp):
        # 1. Console notification
        self._notify_equipment_console(opp)

        # 2. Telegram notification
        if config.ENABLE_TELEGRAM_ALERTS and self.telegram_token and self.telegram_chat_ids:
            await self._notify_equipment_telegram(opp)

    def _notify_equipment_console(self, opp):
        stats_str = ", ".join(f"{k}: {v}" for k, v in opp.skills.items())
        ref_label = "3-денна медіана" if opp.opp_type == "STAT_3D_DISCOUNT" else "Медіана ринку"
        text = (
            f"[bold cyan]{opp.item_name}[/bold cyan] ({opp.rarity})\n"
            f"Характеристики: {stats_str}\n"
            f"Ціна: [red]{opp.price:.2f}[/red] | {ref_label}: [green]{opp.reference_price:.2f}[/green] "
            f"(Знижка: [magenta]{opp.discount_pct}%[/magenta] | Профіт: [bold green]+{opp.potential_profit:.2f}[/bold green])\n"
            f"[italic]{opp.notes}[/italic]"
        )
        console.print(Panel(text, title=f"Знайдено спорядження: {opp.item_name}", border_style="cyan"))

    async def _notify_equipment_telegram(self, opp):
        icon = get_item_icon(opp.item_code)
        rarity_data = get_rarity_info(opp.rarity)
        rarity_emoji = rarity_data["emoji"]
        rarity_name = rarity_data["name"]

        stats_str = ", ".join(f"{k}: {v}" for k, v in opp.skills.items())
        discount_str = f" (знижка {opp.discount_pct}%)" if opp.discount_pct > 0 else ""

        ref_title = "3-денна медіана статів" if opp.opp_type == "STAT_3D_DISCOUNT" else "Медіана ринку статів"

        lines = [
            f"{rarity_emoji} {icon} <b>{opp.item_name}</b> ({rarity_name})",
            f"📊 <b>Характеристики:</b> {stats_str}",
            f"💰 <b>Ціна:</b> <code>{opp.price:.2f}</code>{discount_str}",
        ]
        if opp.potential_profit > 0:
            lines.append(f"💵 <b>Очікуваний профіт:</b> <b>+{opp.potential_profit:.2f}</b>")
        lines.append(f"🎯 <b>{ref_title}:</b> <code>{opp.reference_price:.2f}</code>")
        lines.append(f"ℹ️ {opp.notes}")
        lines.append(f'🛒 <a href="https://app.warera.io/market/equipments?item={opp.item_code}">Відкрити {opp.item_name} на ринку</a>')

        msg = "\n".join(lines)
        for chat_id in self.get_target_chat_ids():
            await self._send_telegram_message(chat_id, msg)
