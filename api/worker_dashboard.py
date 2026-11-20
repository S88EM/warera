"""
WarEra Workforce & Factory Intelligence Web Dashboard.
Visualizes companies, employees, PP margins, wages, and workforce relocation.
"""

import asyncio
import json
import logging
from http import HTTPStatus
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from template_loader import get_template
from worker_analyzer import WarEraWorkerAnalyzer

logger = logging.getLogger("WarEraWorkerDashboard")

# Backwards compatibility: exports the HTML string loaded from template
DASHBOARD_HTML = get_template("workers.html")


class WorkerDashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        # Extract API key if user provided personal token via header or query
        user_key = self.headers.get("X-User-API-Key") or query.get("apiKey", [None])[0]
        analyzer = WarEraWorkerAnalyzer(api_key=user_key) if user_key else WarEraWorkerAnalyzer()

        if path in ("/", "/index.html", "/workers", "/workforce"):
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(DASHBOARD_HTML.encode("utf-8"))
            return

        elif path == "/api/analyze":
            nick = query.get("nick", [None])[0]
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                data = loop.run_until_complete(analyzer.analyze_user(nick))
                loop.close()

                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
            except Exception as e:
                self.send_response(HTTPStatus.INTERNAL_SERVER_ERROR)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}, ensure_ascii=False).encode("utf-8"))
            return

        elif path == "/api/prices":
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                prices = loop.run_until_complete(analyzer.get_market_prices())
                loop.close()

                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(prices, ensure_ascii=False).encode("utf-8"))
            except Exception as e:
                self.send_response(HTTPStatus.INTERNAL_SERVER_ERROR)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}, ensure_ascii=False).encode("utf-8"))
            return

        self.send_response(HTTPStatus.NOT_FOUND)
        self.end_headers()

    def do_OPTIONS(self):
        self.send_response(HTTPStatus.OK)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-User-API-Key")
        self.end_headers()

    def log_message(self, format, *args):
        pass


def start_dashboard(host: str = "0.0.0.0", port: int = 8085):
    server = HTTPServer((host, port), WorkerDashboardHandler)
    print(f"🚀 WarEra Workforce & Factory Dashboard запущено на http://{host}:{port}")
    print(f"👉 Відкрийте у браузері: http://localhost:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nДашборд зупинено.")


if __name__ == "__main__":
    start_dashboard()
