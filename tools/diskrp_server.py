"""
DiskRP Tools Server — local server for all DiskRP web tools.

Usage:
    python tools/diskrp_server.py              # starts on http://localhost:8091
    python tools/diskrp_server.py --port 9000

Serves HTML tools and provides API endpoints:
    /                           → index page
    /tools/<name>.html          → tool pages
    /api/lookup?disk=<name>     → Kusto lookup (sub, region, RG)
    /api/getdisk?disk=<name>    → Kusto lookup + GetDisk via ACIS backend
"""

import datetime
import http.server
import json
import os
import re
import subprocess
import sys
import threading
import time
import webbrowser
from urllib.parse import urlparse, parse_qs

PORT = 8091
TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(TOOLS_DIR)


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


def normalize_region(region: str) -> str:
    """Convert lowercase region to ACIS PascalCase (e.g. eastus2euap → EastUS2EUAP)."""
    # Common mappings — ACIS is case-sensitive on region names
    REGION_MAP = {
        "eastus": "EastUS", "eastus2": "EastUS2", "eastus2euap": "EastUS2EUAP",
        "eastus3": "EastUS3", "eastusstg": "EastUSSTG", "eastusslv": "EastUSSLV",
        "westus": "WestUS", "westus2": "WestUS2", "westus3": "WestUS3",
        "centralus": "CentralUS", "centraluseuap": "CentralUSEUAP",
        "northcentralus": "NorthCentralUS", "southcentralus": "SouthCentralUS",
        "southcentralusstg": "SouthCentralUSSTG", "westcentralus": "WestCentralUS",
        "canadacentral": "CanadaCentral", "canadaeast": "CanadaEast",
        "brazilsouth": "BrazilSouth", "brazilsoutheast": "BrazilSoutheast",
        "northeurope": "NorthEurope", "westeurope": "WestEurope",
        "uksouth": "UKSouth", "ukwest": "UKWest",
        "francecentral": "FranceCentral", "francesouth": "FranceSouth",
        "germanywestcentral": "GermanyWestCentral", "germanynorth": "GermanyNorth",
        "switzerlandnorth": "SwitzerlandNorth", "switzerlandwest": "SwitzerlandWest",
        "norwayeast": "NorwayEast", "norwaywest": "NorwayWest",
        "swedencentral": "SwedenCentral", "swedensouth": "SwedenSouth",
        "polandcentral": "PolandCentral", "italynorth": "ItalyNorth",
        "spaincentral": "SpainCentral", "austriaeast": "AustriaEast",
        "belgiumcentral": "BelgiumCentral", "denmarkeast": "DenmarkEast",
        "finlandcentral": "FinlandCentral", "greececentral": "GreeceCentral",
        "eastasia": "EastAsia", "southeastasia": "SouthEastAsia",
        "japaneast": "JapanEast", "japanwest": "JapanWest",
        "koreacentral": "KoreaCentral", "koreasouth": "KoreaSouth",
        "centralindia": "CentralIndia", "southindia": "SouthIndia",
        "westindia": "WestIndia", "jioindiawest": "JioIndiaWest",
        "jioindiacentral": "JioIndiaCentral",
        "australiaeast": "AustraliaEast", "australiasoutheast": "AustraliaSouthEast",
        "australiacentral": "AustraliaCentral", "australiacentral2": "AustraliaCentral2",
        "southafricanorth": "SouthAfricaNorth", "southafricawest": "SouthAfricaWest",
        "uaenorth": "UAENorth", "uaecentral": "UAECentral",
        "qatarcentral": "QatarCentral", "israelcentral": "IsraelCentral",
        "mexicocentral": "MexicoCentral", "newzealandnorth": "NewZealandNorth",
        "chilecentral": "ChileCentral", "taiwannorth": "TaiwanNorth",
        "indonesiacentral": "IndonesiaCentral", "malaysiasouth": "MalaysiaSouth",
    }
    return REGION_MAP.get(region.lower(), region)


def disk_lookup(disk_name: str) -> dict | None:
    kql = (
        f"DiskManagerApiQoSEvent "
        f"| where PreciseTimeStamp > ago(7d) "
        f"| where resourceName == '{disk_name}' "
        f"| project subscriptionId, region, resourceGroupName "
        f"| take 1"
    )
    rows = kusto_query("disks.kusto.windows.net", "disks", kql)
    if not rows:
        return None
    row = rows[0]
    row["region"] = normalize_region(row["region"])
    return row


def find_venv_python() -> str:
    candidates = [
        os.path.join(ROOT_DIR, ".venv", "Scripts", "python.exe"),
        os.path.join("C:\\git\\XScript-Templates\\zero-toil", ".venv", "Scripts", "python.exe"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    raise RuntimeError("No .venv found. Run scripts/prepare_env.ps1 first.")


def run_backend_acis(extension: str, operation: str, params: list[str], endpoint: str = "Prod") -> dict:
    """Submit an ACIS operation to XJupyterLite backend, wait for result, return output."""
    venv_python = find_venv_python()
    params_str = ", ".join(f"'{p}'" for p in params)

    submit_script = f'''
import asyncio, json, datetime, time
from urllib.parse import urljoin

src = [
    "from xportal import acis\\n",
    "import json\\n",
    "try:\\n",
    "    r = await acis.execute('{extension}', '{operation}', [{params_str}], endpoint='{endpoint}')\\n",
    "    msg = r.get('resultMessage', '') if isinstance(r, dict) else str(r)\\n",
    "    try:\\n",
    "        d = json.loads(msg)\\n",
    "        print(json.dumps(d, indent=2))\\n",
    "    except Exception:\\n",
    "        print(msg)\\n",
    "except Exception as e:\\n",
    "    print(f'ERROR: {{type(e).__name__}}: {{e}}')\\n",
]

NB = json.dumps({{
    "cells": [{{"cell_type": "code", "execution_count": None, "metadata": {{}}, "outputs": [], "source": src}}],
    "metadata": {{"kernelspec": {{"display_name": "Python 3", "language": "python", "name": "python3"}}, "language_info": {{"name": "python", "version": "3.10.0"}}}},
    "nbformat": 4, "nbformat_minor": 4
}}).encode()

async def main():
    from xportal.utils import RestHelper
    endpoint = "https://xportal-aad.trafficmanager.net"
    body = {{
        "Script": "_temp_run",
        "InputParametersJson": json.dumps({{"FORCE_REFRESH_NOTEBOOK_CACHE": True}}),
        "SubmittedBy": "DiskRPToolsServer",
        "SubmitTime": datetime.datetime.now(tz=datetime.timezone.utc).isoformat(),
        "Environment": "Prod",
    }}
    resp = await RestHelper.fetch_post(urljoin(endpoint, "/api/v1/XJupyterlite/SubmitAKSJob"), json.dumps(body))
    job_id = resp["IncidentDiagnosticItemId"]
    report_url = f"https://xportal-aad.trafficmanager.net/xjupyterlitereport?path={{job_id}}_temp_run.html"

    blob_id = f"{{job_id}}_temp_run"
    await RestHelper.fetch_post(
        urljoin(endpoint, f"/api/v1/XJupyterlite/SavePickleObj?storageId={{blob_id}}"),
        NB, content_type="application/octet-stream",
    )

    st = "Unknown"
    for i in range(30):
        time.sleep(5)
        r = await RestHelper.fetch_get(urljoin(endpoint, f"/api/v1/XJupyterlite/GetAKSJobResult?jobId={{job_id}}"))
        st = r.get("Status", "") if isinstance(r, dict) else ""
        if st in ("Pass", "Fail", "Cancelled", "Success"):
            break

    # Fetch report
    report_html = ""
    try:
        report_html = await RestHelper.fetch_get(urljoin(endpoint, f"/xjupyterlitereport?path={{job_id}}_temp_run.html"))
        if not isinstance(report_html, str):
            report_html = str(report_html)
    except:
        pass

    print(json.dumps({{"job_id": job_id, "status": st, "report_url": report_url, "report_html": report_html}}))

asyncio.run(main())
'''
    result = subprocess.run(
        [venv_python, "-c", submit_script],
        capture_output=True, text=True, timeout=300,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip()[:500])
    return json.loads(result.stdout.strip())


def extract_output(html: str) -> str:
    """Extract cell output from Jupyter notebook report HTML."""
    outputs = []
    # Match <pre> content inside jp-OutputArea-output divs
    pattern = r'jp-OutputArea-output[^>]*>\s*<pre[^>]*>(.*?)</pre>'
    for m in re.findall(pattern, html, re.DOTALL):
        text = re.sub(r'<[^>]+>', '', m)
        text = text.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
        text = text.replace('&#34;', '"').replace('&#39;', "'").replace('&quot;', '"')
        if text.strip():
            outputs.append(text.strip())
    return '\n'.join(outputs)


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip('/')

        if path == "/api/lookup":
            self._handle_lookup(parse_qs(parsed.query))
        elif path == "/api/getdisk":
            self._handle_getdisk(parse_qs(parsed.query))
        elif path == "" or path == "/":
            self._serve_file(os.path.join(ROOT_DIR, "index.html"))
        elif path.startswith("/tools/") and path.endswith(".html"):
            filepath = os.path.join(ROOT_DIR, path.lstrip("/").replace("/", os.sep))
            self._serve_file(filepath)
        else:
            self.send_error(404)

    def _serve_file(self, filepath):
        if not os.path.exists(filepath):
            self.send_error(404)
            return
        with open(filepath, "rb") as f:
            content = f.read()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", len(content))
        self.end_headers()
        self.wfile.write(content)

    def _handle_lookup(self, params):
        disk = params.get("disk", [""])[0].strip()
        if not disk:
            return self._json_response(400, {"error": "Missing 'disk' parameter"})
        try:
            info = disk_lookup(disk)
        except Exception as e:
            return self._json_response(500, {"error": str(e)})
        if not info:
            return self._json_response(404, {"error": f"Disk '{disk}' not found in Kusto (last 7 days)"})
        self._json_response(200, info)

    def _handle_getdisk(self, params):
        disk = params.get("disk", [""])[0].strip()
        if not disk:
            return self._json_response(400, {"error": "Missing 'disk' parameter"})

        # Kusto lookup
        try:
            info = disk_lookup(disk)
        except Exception as e:
            return self._json_response(500, {"error": f"Kusto lookup failed: {e}"})
        if not info:
            return self._json_response(404, {"error": f"Disk '{disk}' not found in Kusto (last 7 days)"})

        sub_id = info["subscriptionId"]
        region = info["region"]
        rg = info["resourceGroupName"]

        # Backend ACIS call
        try:
            result = run_backend_acis(
                "Compute Platform Disks", "GetDisk",
                [sub_id, region, rg, disk], "Prod",
            )
        except Exception as e:
            return self._json_response(500, {"error": f"Backend job failed: {e}", "lookup": info})

        output = extract_output(result.get("report_html", "")) if result.get("report_html") else ""

        self._json_response(200, {
            "lookup": info,
            "job_id": result.get("job_id", ""),
            "status": result.get("status", ""),
            "output": output,
            "report_url": result.get("report_url", ""),
        })

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
    print(f"DiskRP Tools server running at {url}")
    print("Endpoints:")
    print(f"  GET /                           → index")
    print(f"  GET /tools/approve-feature.html → approve feature")
    print(f"  GET /tools/break-isf.html       → break ISF")
    print(f"  GET /tools/get-disk.html        → get disk")
    print(f"  GET /api/lookup?disk=<name>     → Kusto lookup")
    print(f"  GET /api/getdisk?disk=<name>    → Kusto + GetDisk ACIS")
    print("\nPress Ctrl+C to stop.\n")
    threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()


if __name__ == "__main__":
    main()
