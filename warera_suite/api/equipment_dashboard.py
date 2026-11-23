"""
Interactive Web Dashboard for WarEra Equipment Market Scanner & Intelligence Suite.
Provides real-time visualization of market bargains, clan member intelligence,
purple battle drops, active contracts, and live scanner controls.
Powered by high-performance asynchronous aiohttp routing.
Compatible with Home Assistant Ingress and standalone desktop/Raspberry Pi mode.
"""

import asyncio
import json
import logging
import os
import sys
import time
from threading import Thread
from typing import Dict, Any, Optional, List
from urllib.parse import parse_qs, urlparse

from aiohttp import web

# Ensure UTF-8 output
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import config
from equipment_data import EQUIPMENT_METADATA, ALL_QUALITIES, QUALITY_TIERS
from template_loader import get_template

logger = logging.getLogger("WarEraWebDashboard")

# Reference to the running EquipmentScannerApp instance
_app_instance: Optional[Any] = None
_web_runner: Optional[web.AppRunner] = None


def set_app_instance(app: Any, loop: Optional[asyncio.AbstractEventLoop] = None):
    global _app_instance
    _app_instance = app


# Load HTML template from api/templates/market.html
DASHBOARD_HTML = get_template("market.html")


def is_client_ingress(request: web.Request) -> bool:
    return bool(
        request.headers.get("X-Ingress-Path")
        or "hassio_ingress" in request.path
        or "ingress_session" in (request.headers.get("Cookie") or "")
    )


def is_client_clan_domain(request: web.Request) -> bool:
    host_header = (request.headers.get("Host") or "").lower()
    xf_host = (request.headers.get("X-Forwarded-Host") or "").lower()
    orig_host = (request.headers.get("X-Original-Host") or "").lower()
    xf_server = (request.headers.get("X-Forwarded-Server") or "").lower()
    referer = (request.headers.get("Referer") or "").lower()
    return any(
        "mace" in h or "clan" in h or "keenetic.link" in h
        for h in (host_header, xf_host, orig_host, xf_server, referer)
    )


@web.middleware
async def cors_and_headers_middleware(request: web.Request, handler):
    if request.method == "OPTIONS":
        resp = web.Response(status=204)
    else:
        try:
            resp = await handler(request)
        except web.HTTPException as ex:
            resp = ex
        except Exception as e:
            logger.error(f"Unhandled error in {request.path}: {e}")
            resp = web.json_response({"status": "error", "message": str(e)}, status=500)

    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, X-User-API-Key"
    return resp


async def handle_clan(request: web.Request) -> web.Response:
    from clan_analyzer import WarEraClanAnalyzer
    mu_id = request.query.get("mu") or request.query.get("nick")
    user_key = request.headers.get("X-User-API-Key") or request.query.get("apiKey")
    analyzer = WarEraClanAnalyzer(api_key=user_key) if user_key else WarEraClanAnalyzer()
    try:
        data = await analyzer.analyze_clan(mu_id)
        return web.json_response(data)
    except Exception as e:
        logger.error(f"Error in handle_clan: {e}")
        return web.json_response({"status": "error", "message": str(e)}, status=500)


async def handle_calculator(request: web.Request) -> web.Response:
    from combat_calculator import CombatDamageCalculator
    from clan_analyzer import WarEraClanAnalyzer

    try:
        target_dmg = float(request.query.get("target", "5000000"))
    except (ValueError, TypeError):
        target_dmg = 5_000_000.0

    user_nick = request.query.get("nick")
    use_pill = request.query.get("pill", "1").lower() in ("1", "true", "yes")
    use_fish = request.query.get("fish", "1").lower() in ("1", "true", "yes")
    gear_tier = request.query.get("gear", "epic").lower()

    try:
        clan_analyzer = WarEraClanAnalyzer()
        clan_data = await clan_analyzer.analyze_clan()
        members = clan_data.get("members", [])
        target_member = None
        if user_nick:
            for m in members:
                if m.get("username", "").lower() == user_nick.lower():
                    target_member = m
                    break
        if not target_member and members:
            target_member = members[0]

        if not target_member:
            return web.json_response({"status": "error", "message": "Боєць не знайдений"}, status=404)

        calc = CombatDamageCalculator(market_app=_app_instance)
        plan = calc.calculate_plan(
            target_member,
            target_damage=target_dmg,
            use_pill=use_pill,
            use_fish=use_fish,
            gear_tier=gear_tier,
        )
        return web.json_response({"status": "ok", "plan": plan})
    except Exception as e:
        logger.error(f"Error in handle_calculator: {e}")
        return web.json_response({"status": "error", "message": str(e)}, status=500)


async def handle_battles(request: web.Request) -> web.Response:
    from battle_analyzer import get_shared_battle_analyzer
    sniper_only = request.query.get("sniper", "false").lower() in ("1", "true", "yes")
    analyzer = get_shared_battle_analyzer()
    try:
        data = await analyzer.get_all_battles_intel()
        if sniper_only:
            data = [b for b in data if b.get("timing", {}).get("isSniperWindow")]
        return web.json_response(data)
    except Exception as e:
        logger.warning(f"Error in handle_battles (using cache fallback): {e}")
        cached = getattr(analyzer, "_cached_intel", None) or []
        if sniper_only:
            cached = [b for b in cached if b.get("timing", {}).get("isSniperWindow")]
        return web.json_response(cached)


async def handle_contracts(request: web.Request) -> web.Response:
    from battle_analyzer import get_shared_battle_analyzer
    analyzer = get_shared_battle_analyzer()
    try:
        data = await analyzer.get_active_contracts()
        return web.json_response(data)
    except Exception as e:
        logger.error(f"Error in handle_contracts: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def handle_auctions(request: web.Request) -> web.Response:
    from battle_analyzer import get_shared_battle_analyzer
    analyzer = get_shared_battle_analyzer()
    try:
        data = await analyzer.get_active_contract_auctions()
        return web.json_response(data)
    except Exception as e:
        logger.error(f"Error in handle_auctions: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def handle_status(request: web.Request) -> web.Response:
    if is_client_clan_domain(request):
        raise web.HTTPFound(location="./")

    if _app_instance:
        status = _app_instance.get_status()
    else:
        status = {
            "version": config.APP_VERSION,
            "running": False,
            "paused": True,
            "scan_interval": config.EQUIPMENT_SCAN_INTERVAL,
            "pricing_mode": config.PRICING_MODE,
            "cycles": 0,
            "total_alerts": 0,
            "active_deals_count": 0,
            "history_deals_count": 0,
            "best_discount": 0.0,
            "best_deal_item": "--",
            "last_scan_time": "--:--:--",
            "active_qualities": config.EQUIPMENT_QUALITIES,
            "monitored_items_count": len(config.EQUIPMENT_TO_MONITOR),
            "min_discount": config.EQUIPMENT_MIN_DISCOUNT,
            "god_roll_threshold": config.EQUIPMENT_GOD_ROLL_THRESHOLD,
        }
    return web.json_response(status)


async def handle_deals(request: web.Request) -> web.Response:
    if is_client_clan_domain(request):
        raise web.HTTPFound(location="./")

    deals = _app_instance.get_deals() if _app_instance else []
    return web.json_response({"status": "ok", "deals": deals, "count": len(deals)})


async def handle_market(request: web.Request) -> web.Response:
    if is_client_clan_domain(request):
        raise web.HTTPFound(location="./")

    item_code = request.query.get("item", "boots4")
    offers = []
    if _app_instance:
        offers = _app_instance.get_market_offers(item_code)
    return web.json_response({"status": "ok", "item": item_code, "offers": offers})


async def handle_scan(request: web.Request) -> web.Response:
    if is_client_clan_domain(request) or not is_client_ingress(request):
        return web.json_response({"status": "error", "message": "Access denied"}, status=403)

    if not _app_instance:
        return web.json_response({"status": "error", "message": "Сканер не підключено"}, status=503)

    if hasattr(_app_instance, "trigger_manual_scan"):
        asyncio.create_task(_app_instance.trigger_manual_scan())
    elif hasattr(_app_instance, "wake_event"):
        _app_instance.wake_event.set()

    return web.json_response({"status": "ok", "message": "Сканування запущено"})


async def handle_control(request: web.Request) -> web.Response:
    if is_client_clan_domain(request) or not is_client_ingress(request):
        return web.json_response({"status": "error", "message": "Access denied"}, status=403)

    if not _app_instance:
        return web.json_response({"status": "error", "message": "Сканер не підключено"}, status=503)

    try:
        body = await request.json()
    except Exception:
        body = {}

    action = body.get("action", "")

    if action == "pause":
        _app_instance.pause()
    elif action == "resume":
        _app_instance.resume()
    elif action == "set_interval":
        sec = int(body.get("interval", 1))
        _app_instance.set_scan_interval(sec)
    elif action == "set_mode":
        mode = str(body.get("mode", "live"))
        _app_instance.set_pricing_mode(mode)
    elif action == "toggle_quality":
        q = str(body.get("quality", "mythic"))
        _app_instance.toggle_quality(q)
    elif action == "set_thresholds":
        if "min_discount" in body:
            _app_instance.set_min_discount_pct(float(body["min_discount"]))
        if "god_roll" in body:
            _app_instance.set_god_roll_threshold(float(body["god_roll"]))
    elif action == "clear_deals":
        _app_instance.clear_deals()

    return web.json_response({
        "status": "ok",
        "action": action,
        "current_status": _app_instance.get_status()
    })


async def handle_html_views(request: web.Request) -> web.Response:
    path = request.path.rstrip("/")
    is_clan_domain = is_client_clan_domain(request)
    is_ingress = is_client_ingress(request)

    # 1. Clan Standalone View
    is_root_path = path in ("", "/")
    should_serve_clan = (
        path.endswith("/clan")
        or path.endswith("/clan.html")
        or (is_root_path and (is_clan_domain or not is_ingress))
    )
    if should_serve_clan:
        import clan_dashboard
        return web.Response(text=clan_dashboard.CLAN_DASHBOARD_HTML, content_type="text/html", charset="utf-8")

    # 2. Battle & Purple Sniper Standalone View
    if path.endswith("/battles") or path.endswith("/battles.html") or path.endswith("/sniper"):
        import battle_dashboard
        return web.Response(text=battle_dashboard.DASHBOARD_HTML, content_type="text/html", charset="utf-8")

    # 3. Privacy Shield: Clan domain redirected away from private scanner view
    if is_clan_domain:
        raise web.HTTPFound(location="./")

    # 4. Default: Market Scanner Owner Dashboard
    return web.Response(text=DASHBOARD_HTML, content_type="text/html", charset="utf-8")


async def handle_common_js(request: web.Request) -> web.Response:
    from template_loader import _resolve_template_path
    path = _resolve_template_path("common_utils.js")
    if path.exists():
        return web.Response(text=path.read_text(encoding="utf-8"), content_type="application/javascript", charset="utf-8")
    return web.Response(text="// common_utils not found", content_type="application/javascript", status=404)


def create_app(app_instance: Optional[Any] = None) -> web.Application:
    """Creates and configures the aiohttp Application with all routes and middlewares."""
    if app_instance is not None:
        set_app_instance(app_instance)

    app = web.Application(middlewares=[cors_and_headers_middleware])

    # Static JS utilities
    app.router.add_get(r"/{prefix:.*}common_utils.js", handle_common_js)

    # API endpoints (supporting both direct and Ingress prefixed paths)
    app.router.add_get(r"/{prefix:.*}api/clan", handle_clan)
    app.router.add_get(r"/{prefix:.*}api/calculator", handle_calculator)
    app.router.add_get(r"/{prefix:.*}api/battles", handle_battles)
    app.router.add_get(r"/{prefix:.*}api/contracts", handle_contracts)
    app.router.add_get(r"/{prefix:.*}api/bounties", handle_contracts)
    app.router.add_get(r"/{prefix:.*}api/auctions", handle_auctions)
    app.router.add_get(r"/{prefix:.*}api/status", handle_status)
    app.router.add_get(r"/{prefix:.*}api/deals", handle_deals)
    app.router.add_get(r"/{prefix:.*}api/market", handle_market)

    app.router.add_post(r"/{prefix:.*}api/scan", handle_scan)
    app.router.add_post(r"/{prefix:.*}api/control", handle_control)

    # HTML Views and Fallbacks
    app.router.add_get(r"/{tail:.*}", handle_html_views)

    return app


async def start_web_server(
    host: str = "0.0.0.0",
    port: int = 8080,
    app_instance: Optional[Any] = None,
) -> web.AppRunner:
    """
    Starts the aiohttp web server on the active asyncio event loop.
    Returns the AppRunner instance for lifecycle management.
    """
    app = create_app(app_instance)
    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    print(f"\n[🚀 Web Dashboard] Активний (aiohttp async) за адресою: http://{host}:{port} (Ingress port {port})")
    return runner


def start_dashboard(
    host: str = "0.0.0.0",
    port: int = 8080,
    app_instance: Optional[Any] = None,
    loop: Optional[asyncio.AbstractEventLoop] = None,
):
    """
    Backwards-compatible launcher for Web Dashboard.
    If an event loop is running, schedules the async server on it.
    Otherwise, runs in a dedicated daemon thread with its own asyncio loop.
    """
    if app_instance is not None:
        set_app_instance(app_instance)

    active_loop = loop
    if not active_loop:
        try:
            active_loop = asyncio.get_running_loop()
        except RuntimeError:
            active_loop = None

    if active_loop and active_loop.is_running():
        return active_loop.create_task(start_web_server(host, port, app_instance))

    def _serve_thread():
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            runner = new_loop.run_until_complete(start_web_server(host, port, app_instance))
            new_loop.run_forever()
        except Exception as e:
            logger.error(f"Web Dashboard thread terminated: {e}")

    thread = Thread(target=_serve_thread, daemon=True)
    thread.start()
    return thread


def run_standalone(host: str = "0.0.0.0", port: int = 8080, app_instance: Optional[Any] = None):
    """Blocking standalone launcher for CLI / direct execution."""
    app = create_app(app_instance)
    print(f"🚀 WarEra Equipment Dashboard (aiohttp) запущено на http://{host}:{port}")
    print(f"👉 Відкрийте у браузері: http://localhost:{port}")
    web.run_app(app, host=host, port=port, print=None, access_log=None)


if __name__ == "__main__":
    run_standalone(config.WEB_DASHBOARD_HOST, config.WEB_DASHBOARD_PORT)
