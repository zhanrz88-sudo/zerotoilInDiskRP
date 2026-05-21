"""Fetch the status and report of an XJPL job via XPortal API.

Usage:
    python scripts/fetch_job_report.py <job_id> [--temp-run]
"""
import asyncio
import sys
from urllib.parse import urljoin


async def fetch_job_report(job_id: str, is_temp_run: bool = False):
    from xportal.utils.rest_helper import RestHelper
    from xportal.utils import get_endpoint

    endpoint = get_endpoint()

    # Step 1: Get job status
    print(f"Fetching job status for {job_id} ...")
    status_url = urljoin(endpoint, f"/api/v1/XJupyterlite/GetAKSJobResult?jobId={job_id}")
    result = await RestHelper.fetch_get(status_url)
    print(f"  Job result: {result}")

    # Step 2: Try multiple approaches to load the report
    if is_temp_run:
        blob_id = f"{job_id}_temp_run"
        report_path = f"{job_id}_temp_run.html"
    else:
        blob_id = f"{job_id}"
        report_path = f"{job_id}.html"

    # Try the xjupyterlitereport endpoint directly (same URL pattern the browser uses)
    attempts = [
        ("Report page (raw)", f"/xjupyterlitereport?path={report_path}", "text/plain"),
        ("GetPrivateWithHNS", f"/api/v1/XJupyterlite/GetPrivateWithHNS?path={report_path}", "text/plain"),
        ("LoadPickleObj (.html)", f"/api/v1/XJupyterlite/LoadPickleObj?id={report_path}", "text/plain"),
        ("LoadPickleObj (no ext)", f"/api/v1/XJupyterlite/LoadPickleObj?id={blob_id}", None),
    ]

    for label, path, resp_type in attempts:
        url = urljoin(endpoint, path)
        print(f"\n  [{label}] {path}")
        try:
            kwargs = {"response_type": resp_type} if resp_type else {}
            data = await RestHelper.fetch_get(url, **kwargs)
            if data:
                content = str(data)
                print(f"    ✔ Got {len(content)} chars")
                # Extract useful text from HTML if it looks like HTML
                if "<" in content[:100]:
                    # Try to extract text between <pre>, <code>, or output cells
                    import re
                    # Look for output text in notebook HTML
                    outputs = re.findall(r'<pre[^>]*>(.*?)</pre>', content, re.DOTALL)
                    if outputs:
                        print("    Output cells found:")
                        for i, out in enumerate(outputs):
                            # Strip HTML tags
                            clean = re.sub(r'<[^>]+>', '', out).strip()
                            if clean:
                                print(f"      [{i}] {clean}")
                    else:
                        print(f"    Raw (first 2000 chars): {content[:2000]}")
                else:
                    print(f"    Content: {content[:2000]}")
            else:
                print("    (empty response)")
        except Exception as e:
            print(f"    ✗ {e}")


if __name__ == "__main__":
    job_id = sys.argv[1] if len(sys.argv) > 1 else "bb96ac1a-63fd-4e34-9ce9-bf8a4ad8aa9c"
    is_temp = "--temp-run" in sys.argv or len(sys.argv) <= 2  # default to temp run for our test
    asyncio.run(fetch_job_report(job_id, is_temp))
