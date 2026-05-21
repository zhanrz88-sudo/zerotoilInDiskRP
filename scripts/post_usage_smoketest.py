import asyncio
import sys

import xportal
from xportal.utils import fetch_post, get_endpoint


RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
CYAN = "\033[36m"
YELLOW = "\033[33m"


def line(label: str, value: str, ok: bool = False) -> None:
    icon = f"{GREEN}[OK]{RESET}" if ok else f"{CYAN} -> {RESET}"
    print(f"  {RESET}{icon} {BOLD}{label:<24}{RESET} {value}")


def banner(title: str, subtitle: str) -> None:
    art = r"""
   _  __ ____             __        __
  | |/ // __ \____  _____/ /_____ _/ /
  |   // /_/ / __ \/ ___/ __/ __ `/ / 
 /   |/ ____/ /_/ / /  / /_/ /_/ / /  
/_/|_/_/    \____/_/   \__/\__,_/_/
"""
    print(f"{CYAN}{art}{RESET}{BOLD}  {title}")
    print(f"  {RESET}{DIM}{subtitle}")
    print("  " + "-" * 64)


async def main() -> None:
    api_route = "/api/v1/XPortalUsers/PostUsage?mainMenu=zerotoil&subMenu=smoketest"
    endpoint = get_endpoint()

    banner("ZeroToil Smoke Test", "Validating local Python environment and XPortal connectivity")
    print(f"  {RESET}{YELLOW}{BOLD}Python Environment Ready")
    line("Python executable", sys.executable)
    line("xportal package", str(xportal.__file__))
    line("XPortal endpoint", endpoint)
    if ".venv" not in sys.executable:
        raise RuntimeError("This script is not running from the zero-toil .venv Python.")
    line("Virtual environment", "zero-toil .venv detected", ok=True)

    response = await fetch_post(api_route, {}, response_type="raw_response")
    status = getattr(response, "status", None)
    reason = getattr(response, "reason", "")

    print("  " + "-" * 64)
    print(f"  {RESET}{YELLOW}{BOLD}XPortal Connected")
    line("Route", api_route)
    line("HTTP status", f"{status} {reason}".rstrip(), ok=status is not None and 200 <= status < 300)
    if status is None or not 200 <= status < 300:
        raise RuntimeError(f"Unexpected PostUsage response status: {status} {reason}".rstrip())
    line("Authentication", "current user accepted by XPortal", ok=True)
    line("PostUsage response", "successful response received", ok=True)
    print("  " + "=" * 64)
    print(f"  {RESET}{GREEN}{BOLD}SUCCESS:{RESET} Python Environment Ready | XPortal Connected")
    print(f"  {RESET}")
    print()


if __name__ == "__main__":
    asyncio.run(main())
