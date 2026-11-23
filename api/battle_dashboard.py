"""
WarEra Battle & Purple Sniper Web Dashboard.
Visualizes active battles, round timers, sniper windows, and loot drop thresholds.
Powered by asynchronous aiohttp routing.
"""

import asyncio
import json
import logging
from typing import Optional
from aiohttp import web
from template_loader import get_template

logger = logging.getLogger("WarEraBattleDashboard")

# Backwards compatibility: exports the HTML string loaded from template
DASHBOARD_HTML = get_template("battles.html")


async def handle_battles(request: web.Request) -> web.Response:
    from battle_analyzer import get_shared_battle_analyzer
    analyzer = get_shared_battle_analyzer()
    try:
        battles = await analyzer.get_all_battles_intel()
        return web.json_response(battles)
    except Exception as e:
        logger.error(f"Error handling /api/battles: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def handle_html(request: web.Request) -> web.Response:
    return web.Response(text=DASHBOARD_HTML, content_type="text/html", charset="utf-8")


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_get(r"/{prefix:.*}api/battles", handle_battles)
    app.router.add_get(r"/{tail:.*}", handle_html)
    return app


async def start_web_server(host: str = "0.0.0.0", port: int = 8086) -> web.AppRunner:
    app = create_app()
    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    print(f"🚀 WarEra Purple Sniper Dashboard (aiohttp) запущено на http://{host}:{port}")
    print(f"👉 Відкрийте у браузері: http://localhost:{port}")
    return runner


def start_dashboard(host: str = "0.0.0.0", port: int = 8086):
    """Starts the battles dashboard server."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        return loop.create_task(start_web_server(host, port))

    run_standalone(host, port)


def run_standalone(host: str = "0.0.0.0", port: int = 8086):
    app = create_app()
    print(f"🚀 WarEra Purple Sniper Dashboard (aiohttp) запущено на http://{host}:{port}")
    print(f"👉 Відкрийте у браузері: http://localhost:{port}")
    web.run_app(app, host=host, port=port, print=None, access_log=None)


if __name__ == "__main__":
    run_standalone()
