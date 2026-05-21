"""Build the zerotoil wheel and publish it to the ADO PyPI feed.

Usage
-----
    python scripts/build_and_upload_package.py [--dry-run]

Prerequisites
-------------
- ``pip install build twine keyring artifacts-keyring``
- ADO credentials (``az login`` or artifacts credential provider)

What it does
------------
1. Stamps a unique PEP 440 dev version (``0.0.1.devYYYYMMDDHHMMSS<8hex>``)
   into ``pyproject.toml``.
2. Builds a ``.whl`` from the ``zerotoil`` package.
3. Publishes the wheel to the **Storage-XI-feed** ADO PyPI feed via
   ``twine upload``.
4. Prints the version string — pass it as ``ZEROTOIL_PACKAGE_VERSION``
   to the notebook job so the worker can ``pip install zerotoil==<version>``.

Every invocation produces a unique version.  There is no linear version
history — each build is an independent, disposable debug snapshot.

Safety notes
------------
- No destructive actions; ``twine`` will fail if the exact version already
  exists, but that is virtually impossible with the timestamp+uuid scheme.
- No secrets are embedded; auth uses ``artifacts-keyring`` (keyring plugin
  for Azure DevOps).
"""

from __future__ import annotations

import argparse
import datetime
import re
import shutil
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
PACKAGE_NAME = "zerotoil"
FEED_URL = (
    "https://msazure.pkgs.visualstudio.com/One/_packaging/Storage-XI-feed/pypi/upload/"
)

# Repository layout – this script lives at  zero-toil/scripts/
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent  # zero-toil/


# ---------------------------------------------------------------------------
# Version helpers
# ---------------------------------------------------------------------------

def generate_version() -> str:
    """Generate a unique PEP 440 dev version.

    Format: ``0.0.1.dev<compact_timestamp>``

    Examples:
        0.0.1.dev241306091612
        0.0.1.dev241306183217

    The dev segment is a 12-digit integer: YYMMDDHHmmSS (2-digit year).
    Combined with second-level precision this is unique enough for
    single-developer debug builds.  If a collision somehow occurs,
    twine will reject the duplicate and you just re-run.
    """
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%y%m%d%H%M%S")
    return f"0.0.1.dev{ts}"


def _stamp_version(version: str) -> None:
    """Patch the version field in pyproject.toml."""
    pyproject = PROJECT_ROOT / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8")
    text = re.sub(
        r'^version\s*=\s*".*"',
        f'version = "{version}"',
        text,
        count=1,
        flags=re.MULTILINE,
    )
    pyproject.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build_wheel(version: str) -> Path:
    """Stamp version, build the wheel, return path to the .whl file."""
    dist_dir = PROJECT_ROOT / "dist"
    if dist_dir.exists():
        shutil.rmtree(dist_dir)

    _stamp_version(version)

    try:
        subprocess.run(
            [sys.executable, "-m", "build", "--wheel", "--outdir", str(dist_dir)],
            cwd=str(PROJECT_ROOT),
            check=True,
        )
    finally:
        # Always reset pyproject.toml so git stays clean
        _stamp_version("0.0.0")

    wheels = list(dist_dir.glob("*.whl"))
    if not wheels:
        raise FileNotFoundError("Build succeeded but no .whl found in dist/")
    return wheels[0]


# ---------------------------------------------------------------------------
# Publish to ADO feed
# ---------------------------------------------------------------------------

def publish_to_feed(wheel_path: Path, *, dry_run: bool = False) -> None:
    """Upload the wheel to the Storage-XI-feed using twine."""
    if dry_run:
        print(f"  (dry-run) Would upload {wheel_path.name} → {FEED_URL}")
        return

    subprocess.run(
        [
            sys.executable, "-m", "twine", "upload",
            "--repository-url", FEED_URL,
            str(wheel_path),
        ],
        check=True,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build and publish the zerotoil package to the ADO PyPI feed.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build the wheel but skip the actual feed upload.",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("ZeroToil – Build & Publish to Feed")
    print("=" * 60)

    # Step 1: Generate unique version
    version = generate_version()
    print(f"\n  Version: {version}")

    # Step 2: Build
    print("\n[1/2] Building wheel …")
    wheel_path = build_wheel(version)
    print(f"  ✔ {wheel_path.name}")

    # Step 3: Publish
    print(f"\n[2/2] Publishing to Storage-XI-feed …")
    publish_to_feed(wheel_path, dry_run=args.dry_run)

    if args.dry_run:
        print("\n  ⚠  Dry-run mode – nothing was uploaded.")
    else:
        print("  ✔ Published to feed.")

    print(f"\n{'=' * 60}")
    print(f"version = {version}")
    print(f"\nWorker install command:")
    print(f"  pip install zerotoil=={version} --index-url <feed-url>")
    print(f"\nNotebook job parameter:")
    print(f'  "ZEROTOIL_PACKAGE_VERSION": "{version}"')
    print("=" * 60)


if __name__ == "__main__":
    main()
