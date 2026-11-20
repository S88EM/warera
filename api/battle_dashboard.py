"""
WarEra Battle & Purple Sniper Web Dashboard.
Visualizes active battles, round timers, sniper windows, and loot drop thresholds.
"""

import asyncio
import json
import logging
from http import HTTPStatus
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

from template_loader import get_template
from battle_analyzer import WarEraBattleAnalyzer

logger = logging.getLogger("WarEraBattleDashboard")

# Backwards compatibility: exports the HTML string loaded from template
DASHBOARD_HTML = get_template("battles.html")


class BattleDashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/battles":
            try:
                analyzer = WarEraBattleAnalyzer()
                battles = asyncio.run(analyzer.get_all_battles_intel())
                payload = json.dumps(battles).encode("utf-8")
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(payload)
            except Exception as e:
                logger.error(f"Error handling /api/battles: {e}")
                err_payload = json.dumps({"error": str(e)}).encode("utf-8")
                self.send_response(HTTPStatus.INTERNAL_SERVER_ERROR)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(err_payload)
            return

        payload = DASHBOARD_HTML.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        pass


def start_dashboard(host: str = "0.0.0.0", port: int = 8086):
    server = HTTPServer((host, port), BattleDashboardHandler)
    print(f"🚀 WarEra Purple Sniper Dashboard запущено на http://{host}:{port}")
    print(f"👉 Відкрийте у браузері: http://localhost:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nДашборд зупинено.")


if __name__ == "__main__":
    start_dashboard()
