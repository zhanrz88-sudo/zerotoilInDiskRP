#!/usr/bin/env python3
"""
run_zerotoil_job.py

Build the zerotoil package, publish it to the ADO PyPI feed, then submit
a notebook job via XPortal API with ZEROTOIL_PACKAGE_VERSION so the
TryExecute worker can ``pip install zerotoil==<version>``.

Usage
-----
    python scripts/run_zerotoil_job.py [OPTIONS]
    python scripts/run_zerotoil_job.py --usage       # show common examples

Prerequisites
-------------
- ``pip install build twine keyring artifacts-keyring``
- ``az login``
- xportal package installed (via init.cmd)
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import signal
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from typing import Optional, Tuple

# ---------------------------------------------------------------------------
# Reuse build & upload from the sibling module
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from build_and_upload_package import build_wheel, publish_to_feed, generate_version  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_NOTEBOOK_PATH = "Xstore/Developer/zifanni/zt-test.ipynb"
TEMP_RUN_SCRIPT = "_temp_run"

environment = os.getenv("CLOUD_SERVICE_NAME", default="Prod")
if environment == "USSec":
    XPORTAL_XJPL = "https://xportal.trafficmanager.microsoft.scloud/xjupyterlitereport"
elif environment == "USNat":
    XPORTAL_XJPL = "https://xportal.trafficmanager.eaglex.ic.gov/xjupyterlitereport"
else:
    XPORTAL_XJPL = "https://xportal-aad.trafficmanager.net/xjupyterlitereport"


# ---------------------------------------------------------------------------
# Job sender
# ---------------------------------------------------------------------------
class ZeroToilJobSender:
    """Build, publish, and submit a zerotoil notebook job via XPortal API."""

    def __init__(
        self,
        environment: str,
        notebook_path: str,
        package_version: str,
        extra_params: dict | None = None,
        open_report: bool = False,
        log_type: Optional[str] = None,
        local_notebook: Optional[str] = None,
    ):
        self.environment = environment
        self.notebook_path = notebook_path
        self.package_version = package_version
        self.extra_params = extra_params or {}
        self.open_report = open_report
        self.log_type = log_type
        self.local_notebook = local_notebook

    # -- public entry point --------------------------------------------------
    def run(self) -> None:
        self._clear_previous_jobs()

        params = {
            "ZEROTOIL_PACKAGE_VERSION": self.package_version,
            "FORCE_REFRESH_NOTEBOOK_CACHE": True,
            **self.extra_params,
        }

        if self.local_notebook:
            job_id, script = self._submit_temp_run(params)
        else:
            job_id, script = self._submit_template_run(params)

        print(f"  ✔ Job submitted.  Job ID: {job_id}")

        # Always print the report URL; open in browser if -o is set
        report_url = self._get_report_url(job_id, script)
        print(f"  📄 Report: {report_url}")
        if self.open_report:
            print("  ⏳ Waiting 20s for notebook execution before opening report …")
            time.sleep(20)
            webbrowser.open(report_url)

        if self.log_type:
            self._find_and_print_item_name(job_id)

    # -- submission modes -----------------------------------------------------
    def _get_xportal_env(self) -> str | None:
        """Map CLI environment names to XPortal API environment names."""
        return {"test": "Test", "stage": "Stage", "prod": None}.get(self.environment)

    def _submit_template_run(self, params: dict) -> Tuple[str, str]:
        """Submit a job for an existing template via XPortal API."""
        import asyncio

        job_id = asyncio.run(
            self._submit_template_run_async(
                self.notebook_path, params, self._get_xportal_env(),
            )
        )
        return job_id, self.notebook_path

    @staticmethod
    async def _submit_template_run_async(
        notebook_path: str, params: dict, environment: str | None,
    ) -> str:
        """Submit a template job via xportal.submit_template_job."""
        from xportal import submit_template_job

        job_id = await submit_template_job(
            notebook_path,
            parameters=params,
            environment=environment,
        )
        return job_id

    def _submit_temp_run(self, params: dict) -> Tuple[str, str]:
        """Submit a temporary run via XPortal API (same flow as the UI button).

        Uses xportal.submit_template_job for SubmitAKSJob and
        xportal.save_obj for uploading notebook content.
        Auth is handled automatically by the xportal SDK (browser popup on first call).

        1. submit_template_job("_temp_run", ...) → get job_id
        2. save_obj(notebook_content, storage_id="{job_id}_temp_run") → upload notebook
        """
        import asyncio

        local_path = Path(self.local_notebook)
        if not local_path.exists():
            raise FileNotFoundError(f"Notebook not found: {local_path}")
        if local_path.suffix != ".ipynb":
            raise ValueError(f"Expected .ipynb file, got: {local_path}")

        job_id = asyncio.run(self._submit_temp_run_async(local_path, params, self._get_xportal_env()))
        return job_id, TEMP_RUN_SCRIPT

    @staticmethod
    async def _submit_temp_run_async(local_path: Path, params: dict, environment: str | None) -> str:
        from xportal.utils.rest_helper import RestHelper
        from xportal.utils import get_endpoint
        from urllib.parse import urljoin

        endpoint = get_endpoint()

        # Step 1: SubmitAKSJob — call REST directly because
        # submit_template_job validates the path format and rejects "_temp_run".
        body = {
            "Script": TEMP_RUN_SCRIPT,
            "InputParametersJson": json.dumps(params, default=str),
            "SubmittedBy": "ZeroToilLocalRun",
            "SubmitTime": datetime.datetime.now(tz=datetime.timezone.utc).isoformat(),
            "Environment": environment,
        }
        response = await RestHelper.fetch_post(
            urljoin(endpoint, "/api/v1/XJupyterlite/SubmitAKSJob"),
            json.dumps(body, default=str),
        )
        job_id = response["IncidentDiagnosticItemId"]
        print(f"  ✔ SubmitAKSJob → job_id: {job_id}")

        # Step 2: Upload notebook content as raw JSON (not pickled).
        # tryExecute.py reads the blob as plain text via content_as_text(),
        # so we must upload the raw notebook JSON, not a pickled object.
        # Note: blob name is "{job_id}_temp_run" (worker strips the leading
        # underscore from Script="_temp_run" when building the blob name).
        blob_id = f"{job_id}_temp_run"
        notebook_content = local_path.read_bytes()
        await RestHelper.fetch_post(
            urljoin(endpoint, f"/api/v1/XJupyterlite/SavePickleObj?storageId={blob_id}"),
            notebook_content,
            content_type="application/octet-stream",
        )
        print(f"  ✔ SavePickleObj → uploaded {local_path.name}")

        return job_id

    # -- helpers --------------------------------------------------------------
    def _clear_previous_jobs(self) -> None:
        if not self.log_type:
            return
        try:
            if self.log_type == "worker":
                cmd = "kubectl delete pods -n notebook --all"
                print("Clearing all previous worker pods …")
            else:
                cmd = "kubectl delete jobs -n notebook --all"
                print("Clearing all previous jobs …")
            subprocess.run(cmd, shell=True, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Warning: could not clear previous jobs/pods: {e}")

    def _get_report_url(self, job_id: str, script: str) -> str:
        """Build the report URL for a completed job."""
        if self.local_notebook:
            return f"{XPORTAL_XJPL}?path={job_id}_temp_run.html"
        # Ensure the script path starts with /
        normalized = script if script.startswith("/") else f"/{script}"
        return f"{XPORTAL_XJPL}?path={job_id}_{normalized}.html"

    # -- kubectl log streaming ------------------------------------------------
    def _find_and_print_item_name(self, job_id: str) -> None:
        max_attempts = 10
        for attempt in range(max_attempts):
            try:
                cmd, search_pattern = self._get_kubectl_command(job_id)
                result = subprocess.run(
                    cmd, shell=True, check=True, capture_output=True, text=True,
                )
                items = result.stdout.strip().split("\n")[1:]  # skip header
                if items:
                    for item in reversed(items):
                        if search_pattern in item:
                            item_name, status = self._parse_kubectl_output(item)
                            if status in ("Running", "Completed", "Succeeded", "Error"):
                                print(f"  {self.log_type.capitalize()} {item_name} → {status}. Streaming logs …")
                                self._stream_item_logs(item_name)
                                return
                            print(f"  {self.log_type.capitalize()} {item_name} status: {status}")
                            break
            except subprocess.CalledProcessError:
                pass
            time.sleep(5)
        print(f"Could not find a running {self.log_type} after {max_attempts} attempts.")

    def _get_kubectl_command(self, job_id: str) -> Tuple[str, str]:
        if self.log_type == "worker":
            return (
                "kubectl get pods --sort-by=.metadata.creationTimestamp",
                "python-worker-deployment-",
            )
        return (
            "kubectl get pods --sort-by=.metadata.creationTimestamp -n notebook",
            f"jupyter-job-{job_id}",
        )

    @staticmethod
    def _parse_kubectl_output(item: str) -> Tuple[str, str]:
        parts = item.split()
        return parts[0], parts[2]

    def _stream_item_logs(self, item_name: str) -> None:
        namespace = "-n notebook" if self.log_type == "job" else ""
        cmd = f"kubectl logs -f {item_name} {namespace}"
        print(f"  Running: {cmd}")
        print("  Press Ctrl+C to stop.\n")

        signal.signal(signal.SIGINT, lambda *_: (print("\nLog streaming stopped."), sys.exit(0)))
        try:
            subprocess.run(cmd, shell=True, check=True)
        except (subprocess.CalledProcessError, KeyboardInterrupt):
            print("\nLog streaming ended.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
USAGE_EXAMPLES = """\
Common usage examples:

  === Dev workflow (build your own package) ===

  # 1. Build + publish + run a local notebook
  python scripts/run_zerotoil_job.py \\
      --local-notebook path/to/my_notebook.ipynb -o

  # 2. Reuse a previously published dev version
  python scripts/run_zerotoil_job.py \\
      --local-notebook path/to/my_notebook.ipynb \\
      --version 0.0.1.dev260415033907 -o

  # 3. Run an existing template on XJupyterLite
  python scripts/run_zerotoil_job.py \\
      --notebook Xstore/Developer/zifanni/zt-test.ipynb -o

  # 4. Build + publish only (no job submission)
  python scripts/run_zerotoil_job.py --dry-run

  === Stage: test an official version before Prod ===

  # 5. Run with a specific official version in Stage
  python scripts/run_zerotoil_job.py \\
      --notebook Xstore/ZeroToil/MyTsg.ipynb \\
      --version 0.0.0.3 --use-official --environment stage -o

  # 6. Run with the latest official version in Stage
  python scripts/run_zerotoil_job.py \\
      --notebook Xstore/ZeroToil/MyTsg.ipynb \\
      --version latest --use-official --environment stage -o
"""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build, publish, and run a ZeroToil notebook job via XPortal API.",
    )
    parser.add_argument(
        "--notebook",
        default=DEFAULT_NOTEBOOK_PATH,
        help=f"Template path on XJupyterLite (default: {DEFAULT_NOTEBOOK_PATH}).",
    )
    parser.add_argument(
        "--environment",
        default="test",
        choices=["test", "stage", "prod"],
        help="Target environment (default: test).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build & publish the package but do NOT submit a job.",
    )
    parser.add_argument(
        "-o", "--open",
        action="store_true",
        help="Open the report in the browser after submission (waits 20s).",
    )
    parser.add_argument(
        "--log",
        choices=["worker", "job"],
        help="Stream kubectl logs for worker or job pod.",
    )
    parser.add_argument(
        "--params",
        default="{}",
        help='Extra parameters as JSON string, e.g. \'{"TENANT":"foo"}\'.',
    )
    parser.add_argument(
        "--version",
        default=None,
        help='Use an already-published version instead of building a new one. Use "latest" for newest.',
    )
    parser.add_argument(
        "--use-official",
        action="store_true",
        help="Use zerotoil-official package instead of zerotoil (for pre-prod validation in Stage).",
    )
    parser.add_argument(
        "--local-notebook",
        default=None,
        help="Path to a local .ipynb file to upload and run as a temporary notebook.",
    )
    parser.add_argument(
        "--usage",
        action="store_true",
        help="Show common usage examples and exit.",
    )
    args = parser.parse_args()

    if args.usage:
        print(USAGE_EXAMPLES)
        return

    print("=" * 60)
    print("ZeroToil – Build · Publish · Run")
    print("=" * 60)

    if args.version:
        version = args.version
        if args.use_official:
            print(f"\n  Using official version: zerotoil-official=={version}")
        else:
            print(f"\n  Using existing version: zerotoil=={version}")
    elif args.use_official:
        version = "latest"
        print(f"\n  Using latest official version: zerotoil-official")
    else:
        version = generate_version()
        print(f"\n[1/3] Building wheel (version {version}) …")
        wheel_path = build_wheel(version)
        print(f"  ✔ {wheel_path.name}")

        print("\n[2/3] Publishing to Storage-XI-feed …")
        publish_to_feed(wheel_path, dry_run=args.dry_run)
        if args.dry_run:
            print(f"  ✔ (dry-run) version = {version}")
        else:
            print(f"  ✔ Published: zerotoil=={version}")

    if args.dry_run:
        print("\n  ⚠  Dry-run mode – skipping job submission.")
        print("=" * 60)
        return

    if args.local_notebook:
        print(f"\n[3/3] Temporary run: {args.local_notebook} ({args.environment}) …")
    else:
        print(f"\n[3/3] Submitting job → {args.notebook} ({args.environment}) …")

    extra_params = json.loads(args.params)

    # Pass ZEROTOIL_USE_OFFICIAL if --use-official is set
    if args.use_official:
        extra_params["ZEROTOIL_USE_OFFICIAL"] = True

    sender = ZeroToilJobSender(
        environment=args.environment,
        notebook_path=args.notebook,
        package_version=version,
        extra_params=extra_params,
        open_report=args.open,
        log_type=args.log,
        local_notebook=args.local_notebook,
    )
    sender.run()

    mode = "temporary run (local notebook)" if args.local_notebook else "template"
    pkg = "zerotoil-official" if args.use_official else "zerotoil"
    print("\n" + "=" * 60)
    print(f"package             = {pkg}=={version}")
    print(f"notebook            = {args.local_notebook or args.notebook}")
    print(f"mode                = {mode}")
    print(f"environment         = {args.environment}")
    print("=" * 60)


if __name__ == "__main__":
    main()
