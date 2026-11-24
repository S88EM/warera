import asyncio
from aiohttp.test_utils import make_mocked_request

import config
from telegram_base import BaseTelegramBot
from telegram_bot import TelegramBotController
from sniper_bot import SniperBotController
import equipment_dashboard


def test_bots_inherit_base_telegram_bot():
    assert issubclass(TelegramBotController, BaseTelegramBot)
    assert issubclass(SniperBotController, BaseTelegramBot)

    sniper = SniperBotController(token="123:test")
    assert sniper.base_url == "https://api.telegram.org/bot123:test"
    assert hasattr(sniper, "send_message")
    assert hasattr(sniper, "edit_message")
    assert hasattr(sniper, "answer_callback")


def test_dashboard_post_auth_guard(monkeypatch):
    monkeypatch.setattr(config, "DASHBOARD_API_TOKEN", "secret-token")

    async def ok_handler(request):
        from aiohttp import web
        return web.json_response({"status": "ok"})

    # 1. Missing token outside Ingress -> 401
    req_unauth = make_mocked_request("POST", "/api/scan")
    resp_unauth = asyncio.run(equipment_dashboard.cors_and_headers_middleware(req_unauth, ok_handler))
    assert resp_unauth.status == 401

    # 2. Valid X-Dashboard-Token -> 200
    req_auth = make_mocked_request("POST", "/api/scan", headers={"X-Dashboard-Token": "secret-token"})
    resp_auth = asyncio.run(equipment_dashboard.cors_and_headers_middleware(req_auth, ok_handler))
    assert resp_auth.status == 200

    # 3. Home Assistant Ingress request -> 200 without external token
    req_ingress = make_mocked_request("POST", "/api/scan", headers={"X-Ingress-Path": "/api/hassio_ingress/xyz"})
    resp_ingress = asyncio.run(equipment_dashboard.cors_and_headers_middleware(req_ingress, ok_handler))
    assert resp_ingress.status == 200
