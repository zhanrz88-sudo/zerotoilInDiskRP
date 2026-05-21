"""
Break ISF Tool — enter a disk name, get Geneva portal link + Python snippet.

Usage:
    python tools/break_isf.py <diskName>
    python tools/break_isf.py <diskName> --skip-validation --clear-billing

Queries disks.kusto.windows.net to auto-discover subscription, region, and
resource group, then prints:
  1. Geneva portal link (click in SAW browser)
  2. Python snippet (paste in SAW JupyterLite)
"""

import argparse
import json
import subprocess
import sys
import urllib.parse


def kusto_query(cluster: str, db: str, kql: str) -> list[dict]:
    """Run a KQL query via az rest and return rows as dicts."""
    body = json.dumps({"db": db, "csl": kql})
    cmd = (
        f'az rest --method post '
        f'--url "https://{cluster}/v1/rest/query" '
        f'--body @- '
        f'--resource "https://{cluster}"'
    )
    result = subprocess.run(
        cmd, capture_output=True, text=True, shell=True, input=body,
    )
    if result.returncode != 0:
        print(f"Kusto query failed: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    data = json.loads(result.stdout)
    tables = data.get("Tables", data.get("tables", []))
    if not tables:
        return []
    table = tables[0]
    columns = [c["ColumnName"] for c in table["Columns"]]
    return [dict(zip(columns, row)) for row in table["Rows"]]


def lookup_disk(disk_name: str) -> dict:
    """Find subscription, region, resourceGroup for a disk via Kusto."""
    kql = (
        f"DiskManagerApiQoSEvent "
        f"| where PreciseTimeStamp > ago(7d) "
        f"| where resourceName == '{disk_name}' "
        f"| project subscriptionId, region, resourceGroupName "
        f"| take 1"
    )
    rows = kusto_query("disks.kusto.windows.net", "disks", kql)
    if not rows:
        print(f"ERROR: Disk '{disk_name}' not found in Kusto (last 7 days).")
        print("Try extending the time range or provide params manually.")
        sys.exit(1)
    return rows[0]


def geneva_link(sub_id: str, region: str, rg: str, disk_name: str,
                skip_validation: bool, clear_billing: bool) -> str:
    params = {
        "page": "actions",
        "acisEndpoint": "Public",
        "tab": "Extensions",
        "extension": "Compute Platform Disks",
        "operationId": "RemoveIncrementalSnapshotFamilyOnDisk",
        "inputMode": "single",
        "params": json.dumps({
            "wellknownsubscriptionid": sub_id,
            "smeregionarmnameparameter": region,
            "smeresourcegroupnameparameter": rg,
            "smedisknameparameter": disk_name,
            "smeskipvalidationparameter": str(skip_validation).lower(),
            "smeclearbillingparameter": str(clear_billing).lower(),
            "smeapiversionparameter": "",
        }),
        "actionEndpoint": "Prod",
    }
    return "https://portal.microsoftgeneva.com/?" + urllib.parse.urlencode(params)


def python_snippet(sub_id: str, region: str, rg: str, disk_name: str,
                   skip_validation: bool, clear_billing: bool) -> str:
    return f"""from xportal import acis
import json

r = await acis.execute(
    'Compute Platform Disks',
    'RemoveIncrementalSnapshotFamilyOnDisk',
    ['{sub_id}', '{region}', '{rg}', '{disk_name}',
     '{str(skip_validation).lower()}', '{str(clear_billing).lower()}', ''],
    endpoint='Prod')

msg = r.get('resultMessage', '') if isinstance(r, dict) else str(r)
try:
    print(json.dumps(json.loads(msg), indent=2))
except Exception:
    print(msg)"""


def main():
    parser = argparse.ArgumentParser(description="Break ISF — lookup disk and generate SAW links")
    parser.add_argument("disk_name", help="Name of the disk")
    parser.add_argument("--skip-validation", action="store_true", default=False)
    parser.add_argument("--clear-billing", action="store_true", default=False)
    args = parser.parse_args()

    print(f"Looking up disk '{args.disk_name}' in Kusto ...")
    info = lookup_disk(args.disk_name)

    sub_id = info["subscriptionId"]
    region = info["region"]
    rg = info["resourceGroupName"]

    print(f"  subscriptionId : {sub_id}")
    print(f"  region         : {region}")
    print(f"  resourceGroup  : {rg}")
    print()

    link = geneva_link(sub_id, region, rg, args.disk_name,
                       args.skip_validation, args.clear_billing)
    snippet = python_snippet(sub_id, region, rg, args.disk_name,
                             args.skip_validation, args.clear_billing)

    print("=" * 60)
    print("GENEVA PORTAL LINK (open in SAW browser):")
    print("=" * 60)
    print(link)
    print()
    print("=" * 60)
    print("PYTHON SNIPPET (paste in SAW JupyterLite):")
    print("=" * 60)
    print(snippet)


if __name__ == "__main__":
    main()
