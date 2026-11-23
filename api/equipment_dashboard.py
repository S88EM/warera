"""
Interactive Web Dashboard for WarEra Equipment Market Scanner.
Provides real-time visualization of market bargains, anomalies, stat rolls,
filters by rarity/slot, direct links to game market, and live scanner controls.
Compatible with Home Assistant Ingress and standalone desktop/Raspberry Pi mode.
"""

import asyncio
import json
import os
import sys
import time
from http import HTTPStatus
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from threading import Thread
from typing import Dict, Any, Optional, List
from urllib.parse import parse_qs, urlparse

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

# Reference to the running EquipmentScannerApp instance
_app_instance: Optional[Any] = None
_loop_instance: Optional[asyncio.AbstractEventLoop] = None


def set_app_instance(app: Any, loop: Optional[asyncio.AbstractEventLoop] = None):
    global _app_instance, _loop_instance
    _app_instance = app
    _loop_instance = loop or getattr(app, "event_loop", None)


# Load HTML template from api/templates/market.html
DASHBOARD_HTML = get_template("market.html")


class EquipmentDashboardHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Silence default request logging to avoid terminal clutter
        pass

    def _send_json(self, data: Any, status: int = HTTPStatus.OK):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-User-API-Key")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-User-API-Key")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        clean_path = parsed.path.rstrip("/")

        # Determine client origin: Home Assistant Ingress vs External Clan / Keenetic
        host_header = (self.headers.get("Host") or "").lower()
        xf_host = (self.headers.get("X-Forwarded-Host") or "").lower()
        orig_host = (self.headers.get("X-Original-Host") or "").lower()
        xf_server = (self.headers.get("X-Forwarded-Server") or "").lower()
        referer = (self.headers.get("Referer") or "").lower()

        is_ingress = bool(
            self.headers.get("X-Ingress-Path")
            or "hassio_ingress" in self.path
            or "ingress_session" in (self.headers.get("Cookie") or "")
        )
        is_clan_domain = any(
            "mace" in h or "clan" in h or "keenetic.link" in h
            for h in (host_header, xf_host, orig_host, xf_server, referer)
        )

        # 1. Clan & Military Unit (MU) Intelligence API endpoint (PUBLIC, Zero-Auth)
        if clean_path.endswith("/api/clan"):
            from clan_analyzer import WarEraClanAnalyzer
            query_params = parse_qs(parsed.query)
            mu_id = query_params.get("mu", [None])[0] or query_params.get("nick", [None])[0]
            user_key = self.headers.get("X-User-API-Key") or query_params.get("apiKey", [None])[0]
            analyzer = WarEraClanAnalyzer(api_key=user_key) if user_key else WarEraClanAnalyzer()
            try:
                if _loop_instance and _loop_instance.is_running():
                    future = asyncio.run_coroutine_threadsafe(analyzer.analyze_clan(mu_id), _loop_instance)
                    data = future.result(timeout=10.0)
                else:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    data = loop.run_until_complete(analyzer.analyze_clan(mu_id))
                    loop.close()
                self._send_json(data)
            except Exception as e:
                self._send_json({"status": "error", "message": str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        # 1b. Combat Damage & Gear Calculator API endpoint (PUBLIC, Zero-Auth)
        if clean_path.endswith("/api/calculator"):
            from combat_calculator import CombatDamageCalculator
            from clan_analyzer import WarEraClanAnalyzer

            query_params = parse_qs(parsed.query)
            target_dmg = float(query_params.get("target", [5_000_000])[0])
            user_nick = query_params.get("nick", [None])[0]
            use_pill = query_params.get("pill", ["1"])[0].lower() in ("1", "true", "yes")
            use_fish = query_params.get("fish", ["1"])[0].lower() in ("1", "true", "yes")
            gear_tier = query_params.get("gear", ["epic"])[0].lower()

            try:
                clan_analyzer = WarEraClanAnalyzer()
                if _loop_instance and _loop_instance.is_running():
                    future = asyncio.run_coroutine_threadsafe(clan_analyzer.analyze_clan(), _loop_instance)
                    clan_data = future.result(timeout=10.0)
                else:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    clan_data = loop.run_until_complete(clan_analyzer.analyze_clan())
                    loop.close()

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
                    self._send_json({"status": "error", "message": "Боєць не знайдений"}, HTTPStatus.NOT_FOUND)
                    return

                calc = CombatDamageCalculator(market_app=_app_instance)
                plan = calc.calculate_plan(
                    target_member,
                    target_damage=target_dmg,
                    use_pill=use_pill,
                    use_fish=use_fish,
                    gear_tier=gear_tier,
                )
                self._send_json({"status": "ok", "plan": plan})
            except Exception as e:
                self._send_json({"status": "error", "message": str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        # 2. Clan Standalone HTML Dashboard (PUBLIC, Zero-Auth)
        is_root_path = clean_path in ("", "/", "/index.html")
        should_serve_clan = (
            clean_path.endswith("/clan")
            or clean_path.endswith("/clan.html")
            or (is_root_path and (is_clan_domain or not is_ingress))
        )

        if should_serve_clan and not clean_path.endswith("/api/clan"):
            import clan_dashboard
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(clan_dashboard.CLAN_DASHBOARD_HTML.encode("utf-8"))
            return

        # 2b. Battle & Purple Sniper API endpoint (PUBLIC, Zero-Auth)
        if clean_path.endswith("/api/battles"):
            from battle_analyzer import get_shared_battle_analyzer
            query_params = parse_qs(parsed.query)
            sniper_only = query_params.get("sniper", ["false"])[0].lower() in ("1", "true", "yes")
            analyzer = get_shared_battle_analyzer()
            try:
                if _loop_instance and _loop_instance.is_running():
                    future = asyncio.run_coroutine_threadsafe(analyzer.get_all_battles_intel(), _loop_instance)
                    data = future.result(timeout=6.0)
                else:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    data = loop.run_until_complete(analyzer.get_all_battles_intel())
                    loop.close()
                if sniper_only:
                    data = [b for b in data if b.get("timing", {}).get("isSniperWindow")]
                self._send_json(data)
            except Exception as e:
                cached = getattr(analyzer, "_cached_intel", None) or []
                if sniper_only:
                    cached = [b for b in cached if b.get("timing", {}).get("isSniperWindow")]
                self._send_json(cached)
            return

        # 2b-2. Active Contracts / Bounties API endpoint (PUBLIC, Zero-Auth)
        if clean_path.endswith("/api/contracts") or clean_path.endswith("/api/bounties"):
            from battle_analyzer import get_shared_battle_analyzer
            analyzer = get_shared_battle_analyzer()
            try:
                if _loop_instance and _loop_instance.is_running():
                    future = asyncio.run_coroutine_threadsafe(analyzer.get_active_contracts(), _loop_instance)
                    data = future.result(timeout=6.0)
                else:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    data = loop.run_until_complete(analyzer.get_active_contracts())
                    loop.close()
                self._send_json(data)
            except Exception as e:
                self._send_json({"error": str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        # 2b-3. Active Mercenary Contract Auctions API endpoint (PUBLIC, Zero-Auth)
        if clean_path.endswith("/api/auctions"):
            try:
                if _loop_instance and _loop_instance.is_running():
                    future = asyncio.run_coroutine_threadsafe(analyzer.get_active_contract_auctions(), _loop_instance)
                    data = future.result(timeout=6.0)
                else:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    data = loop.run_until_complete(analyzer.get_active_contract_auctions())
                    loop.close()
                self._send_json(data)
            except Exception as e:
                self._send_json({"error": str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        # 2c. Battle & Purple Sniper Standalone HTML Dashboard (PUBLIC, Zero-Auth)
        if clean_path.endswith("/battles") or clean_path.endswith("/battles.html") or clean_path.endswith("/sniper"):
            import battle_dashboard
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(battle_dashboard.DASHBOARD_HTML.encode("utf-8"))
            return

        # 3. PRIVACY & SECURITY SHIELD:
        # If client connects via clan domain or outside Ingress, block private market endpoints
        if is_clan_domain:
            self.send_response(HTTPStatus.FOUND)
            self.send_header("Location", "./")
            self.end_headers()
            return

        # Status endpoint (Ingress only)
        if clean_path.endswith("/api/status"):
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
            self._send_json(status)
            return

        # Deals endpoint (Ingress only)
        if clean_path.endswith("/api/deals"):
            deals = _app_instance.get_deals() if _app_instance else []
            self._send_json({"status": "ok", "deals": deals, "count": len(deals)})
            return

        # Market offers inspector endpoint (Ingress only)
        if clean_path.endswith("/api/market"):
            query_params = parse_qs(parsed.query)
            item_code = query_params.get("item", ["boots4"])[0]
            offers = []
            if _app_instance:
                offers = _app_instance.get_market_offers(item_code)
            self._send_json({"status": "ok", "item": item_code, "offers": offers})
            return

        # 2b-3. Active Mercenary Contract Auctions API endpoint (PUBLIC, Zero-Auth)
        if clean_path.endswith("/api/auctions"):
            try:
                if _loop_instance and _loop_instance.is_running():
                    future = asyncio.run_coroutine_threadsafe(analyzer.get_active_contract_auctions(), _loop_instance)
                    data = future.result(timeout=6.0)
                else:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    data = loop.run_until_complete(analyzer.get_active_contract_auctions())
                    loop.close()
                self._send_json(data)
            except Exception as e:
                self._send_json({"error": str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        # Explicit scanner view for owner
        if clean_path.endswith("/scanner") or clean_path.endswith("/market"):
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(DASHBOARD_HTML.encode("utf-8"))
            return

        # Serve SPA HTML for Ingress (Owner UI: Market Scanner)
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(DASHBOARD_HTML.encode("utf-8"))

    def do_POST(self):
        parsed = urlparse(self.path)
        clean_path = parsed.path.rstrip("/")

        host_header = (self.headers.get("Host") or "").lower()
        xf_host = (self.headers.get("X-Forwarded-Host") or "").lower()
        orig_host = (self.headers.get("X-Original-Host") or "").lower()
        xf_server = (self.headers.get("X-Forwarded-Server") or "").lower()
        referer = (self.headers.get("Referer") or "").lower()

        is_ingress = bool(
            self.headers.get("X-Ingress-Path")
            or "hassio_ingress" in self.path
            or "ingress_session" in (self.headers.get("Cookie") or "")
        )
        is_clan_domain = any(
            "mace" in h or "clan" in h or "keenetic.link" in h
            for h in (host_header, xf_host, orig_host, xf_server, referer)
        )

        # Protect all POST endpoints (scan, control) from external clan domain or non-ingress clients
        if is_clan_domain or not is_ingress:
            self._send_json({"status": "error", "message": "Access denied"}, HTTPStatus.FORBIDDEN)
            return

        # Manual Scan endpoint
        if clean_path.endswith("/api/scan"):
            if _app_instance:
                if _loop_instance and _loop_instance.is_running():
                    asyncio.run_coroutine_threadsafe(_app_instance.trigger_manual_scan(), _loop_instance)
                else:
                    _app_instance.wake_event.set()
                self._send_json({"status": "ok", "message": "Сканування запущено"})
            else:
                self._send_json({"status": "error", "message": "Сканер не підключено"}, HTTPStatus.SERVICE_UNAVAILABLE)
            return

        # Control actions endpoint
        if clean_path.endswith("/api/control"):
            content_length = int(self.headers.get("Content-Length", 0))
            body_raw = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
            try:
                body = json.loads(body_raw)
            except Exception:
                body = {}

            action = body.get("action", "")

            if not _app_instance:
                self._send_json({"status": "error", "message": "Сканер не підключено"}, HTTPStatus.SERVICE_UNAVAILABLE)
                return

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

            self._send_json({
                "status": "ok",
                "action": action,
                "current_status": _app_instance.get_status()
            })
            return

        self._send_json({"status": "error", "message": "Невідомий маршрут"}, HTTPStatus.NOT_FOUND)


def start_dashboard(host: str = "0.0.0.0", port: int = 8080, app_instance: Optional[Any] = None, loop: Optional[asyncio.AbstractEventLoop] = None):
    """Starts the Web Dashboard HTTP server in a separate background daemon thread."""
    if app_instance is not None:
        set_app_instance(app_instance, loop)

    def _serve():
        try:
            server = ThreadingHTTPServer((host, port), EquipmentDashboardHandler)
            print(f"\n[🚀 Web Dashboard] Активний за адресою: http://{host}:{port} (Ingress port {port})")
            server.serve_forever()
        except Exception as e:
            print(f"[Web Dashboard] Помилка або сервер зупинено: {e}")

    thread = Thread(target=_serve, daemon=True)
    thread.start()
    return thread


if __name__ == "__main__":
    print(f"Starting standalone WarEra Equipment Dashboard on port {config.WEB_DASHBOARD_PORT}...")
    server = ThreadingHTTPServer((config.WEB_DASHBOARD_HOST, config.WEB_DASHBOARD_PORT), EquipmentDashboardHandler)
    try:
        print(f"Open: http://localhost:{config.WEB_DASHBOARD_PORT}")
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
