"""
Break ISF Web Tool — local server that serves UI + proxies Kusto lookups.

Usage:
    python tools/break_isf_server.py          # starts on http://localhost:8091
    python tools/break_isf_server.py --port 9000

Opens the browser automatically. Enter a disk name → Kusto lookup → Geneva link + Python snippet.
"""

import http.server
import json
import os
import subprocess
import sys
import threading
import webbrowser
from urllib.parse import urlparse, parse_qs

PORT = 8091
HTML_FILE = os.path.join(os.path.dirname(__file__), "break-isf.html")


def kusto_query(cluster: str, db: str, kql: str) -> list[dict]:
    body = json.dumps({"db": db, "csl": kql})
    cmd = (
        f'az rest --method post '
        f'--url "https://{cluster}/v1/rest/query" '
        f'--body @- '
        f'--resource "https://{cluster}"'
    )
    result = subprocess.run(cmd, capture_output=True, text=True, shell=True, input=body)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    data = json.loads(result.stdout)
    tables = data.get("Tables", data.get("tables", []))
    if not tables:
        return []
    table = tables[0]
    columns = [c["ColumnName"] for c in table["Columns"]]
    return [dict(zip(columns, row)) for row in table["Rows"]]


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/lookup":
            self._handle_lookup(parse_qs(parsed.query))
        elif parsed.path == "/" or parsed.path == "/break-isf":
            self._serve_html()
        else:
            self.send_error(404)

    def _serve_html(self):
        with open(HTML_FILE, "rb") as f:
            content = f.read()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", len(content))
        self.end_headers()
        self.wfile.write(content)

    def _handle_lookup(self, params):
        disk = params.get("disk", [""])[0].strip()
        if not disk:
            self._json_response(400, {"error": "Missing 'disk' parameter"})
            return

        kql = (
            f"DiskManagerApiQoSEvent "
            f"| where PreciseTimeStamp > ago(7d) "
            f"| where resourceName == '{disk}' "
            f"| project subscriptionId, region, resourceGroupName "
            f"| take 1"
        )
        try:
            rows = kusto_query("disks.kusto.windows.net", "disks", kql)
        except Exception as e:
            self._json_response(500, {"error": str(e)})
            return

        if not rows:
            self._json_response(404, {"error": f"Disk '{disk}' not found in Kusto (last 7 days)"})
            return

        self._json_response(200, rows[0])

    def _json_response(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        if "/api/" in str(args[0]):
            super().log_message(format, *args)


def main():
    port = PORT
    if len(sys.argv) > 2 and sys.argv[1] == "--port":
        port = int(sys.argv[2])

    server = http.server.HTTPServer(("127.0.0.1", port), Handler)
    url = f"http://localhost:{port}/"
    print(f"Break ISF server running at {url}")
    print("Press Ctrl+C to stop.\n")
    threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()


if __name__ == "__main__":
    main()
