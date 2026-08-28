#!/usr/bin/env python3
"""Screenshot every page of a deployed report and save its accessibility text (Playwright for Python).

Usage:
    python3 scripts/capture_pages.py <report-item-id> captures/round1 60
    python3 scripts/capture_pages.py --url <report url> --out captures/round1 [--settle 60] [--profile <dir>]

Positional form: <item id or URL> [<out dir>] [<settle seconds>]. An item id becomes
<capture.app_base>/groups/<workspace.id>/reports/<item id> with workspace.id from config.yaml
(app_base defaults to https://app.powerbi.com; set it for a sovereign or GCC portal).
Defaults come from config.yaml: capture.report_url, capture.settle_seconds, capture.browser_profile_dir.

Chromium runs with a persistent profile directory (default ./.browser-profile, gitignored). The
first run opens a window: sign in once and the session is kept. Add --headless once signed in.

Per page it writes <out>/<n>-<page>.png and <out>/<n>-<page>.txt (the accessibility tree as text,
so numbers can be grepped instead of squinted at), and prints the digit count plus the count of
Power BI error markers. Exit code 1 if any page shows an error banner or could not be opened.

Design decisions, each learned the hard way on a real build:
  - navigate to the report URL FIRST: page clicks in an already-open tab keep serving the OLD
    definition after a deploy;
  - wait up to --rail-wait seconds for the page rail (the first load after a definition update
    takes ~30-45 s), then --settle seconds after every page click; earlier shots show spinners;
  - switch pages by clicking the page name in the rail (role=tab), which keeps working when a
    full navigation fails.

Needs:  pip install playwright && python3 -m playwright install chromium
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True  # no __pycache__ in the tree: .pyc files embed the absolute source path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import PLACEHOLDER_ID, load_config  # noqa: E402

# Power BI's failure texts. A visual that failed to bind keeps its frame and loses its number,
# so the check is these strings plus a digit count you read against your tie-out table.
ERROR_MARKERS = (
    "can't display the visual", "cannot display the visual", "couldn't load the data",
    "see details", "something went wrong", "something's wrong", "we couldn't find the field",
    "field is no longer available", "network error",
)
GUID = re.compile(r"^[0-9a-f-]{36}$", re.IGNORECASE)
SIGN_IN_HOSTS = ("login.microsoftonline.com", "login.live.com", "login.microsoft.com")


def judge(text: str) -> tuple[int, int]:
    """(digit count, error-marker count) for one page's accessibility text."""
    low = text.lower()
    return sum(c.isdigit() for c in text), sum(1 for m in ERROR_MARKERS if m in low)


def resolve_url(cfg: dict, target: str | None) -> str:
    if target and "://" in target:
        return target
    if target and GUID.match(target):
        ws = (cfg.get("workspace") or {}).get("id")
        if not ws or ws == PLACEHOLDER_ID:
            sys.exit("An item id needs workspace.id in config.yaml (run scripts/discover.py), "
                     "or pass the full report URL with --url.")
        base = str((cfg.get("capture") or {}).get("app_base") or "https://app.powerbi.com").rstrip("/")
        return f"{base}/groups/{ws}/reports/{target}?experience=power-bi"
    url = str((cfg.get("capture") or {}).get("report_url") or "")
    if "://" not in url:
        sys.exit("No report given. Pass <item id>, --url <report url>, or set capture.report_url in config.yaml.")
    return url


def rail_pages(page) -> list[str]:
    """Page names from the left rail: every role=tab element, de-duplicated, in rail order."""
    names: list[str] = []
    for tab in page.get_by_role("tab").all():
        try:
            raw = tab.get_attribute("aria-label") or tab.inner_text() or ""
        except Exception:  # noqa: BLE001 - a tab that vanished mid-read is not a page
            continue
        name = re.sub(r"\s+Selected$", "", raw.strip()).strip()
        if name and name not in names:
            names.append(name)
    return names


def page_text(page) -> str:
    try:
        return page.locator("body").aria_snapshot()
    except Exception:  # noqa: BLE001 - older Playwright: fall back to visible text
        return page.inner_text("body")


def wait_for_rail(page, rail_wait: float) -> list[str]:
    deadline = time.monotonic() + rail_wait
    told = False
    while True:
        if any(h in page.url for h in SIGN_IN_HOSTS):
            if not told:
                print("Sign in in the browser window (once; the profile keeps the session). "
                      "Waiting up to 10 minutes...", flush=True)
                told, deadline = True, time.monotonic() + 600
        names = rail_pages(page)
        if names:
            return names
        if time.monotonic() > deadline:
            sys.exit("No page rail appeared. Is the URL a report, and is the profile signed in? "
                     "(Run once without --headless to sign in.)")
        time.sleep(5)


def main() -> None:
    parser = argparse.ArgumentParser(description="Screenshot every page of a deployed report.")
    parser.add_argument("target", nargs="?", help="report item id, or the full report URL")
    parser.add_argument("out_pos", nargs="?", metavar="out", help="output folder")
    parser.add_argument("settle_pos", nargs="?", metavar="settle", type=float,
                        help="seconds to wait after each page click")
    parser.add_argument("--url", help="report URL (instead of the item id)")
    parser.add_argument("--out", help="output folder (default captures/latest)")
    parser.add_argument("--settle", type=float, help="seconds after each page click (config: capture.settle_seconds)")
    parser.add_argument("--profile", help="persistent browser profile dir (config: capture.browser_profile_dir)")
    parser.add_argument("--headless", action="store_true", help="no window; only once the profile is signed in")
    parser.add_argument("--rail-wait", type=float, default=45.0, help="seconds to wait for the page rail")
    args = parser.parse_args()

    cfg = load_config()
    cap = cfg.get("capture") or {}
    url = resolve_url(cfg, args.url or args.target)
    out = Path(args.out or args.out_pos or "captures/latest")
    settle = args.settle or args.settle_pos or float(cap.get("settle_seconds") or 60)
    profile = Path(args.profile or cap.get("browser_profile_dir") or "./.browser-profile")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("playwright is not installed. Run: pip install playwright && "
                 "python3 -m playwright install chromium")

    out.mkdir(parents=True, exist_ok=True)
    failures = 0
    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(
            str(profile), headless=args.headless, viewport={"width": 1600, "height": 960})
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        print(f"opening {url}", flush=True)
        page.goto(url, wait_until="domcontentloaded", timeout=120_000)
        pages = wait_for_rail(page, args.rail_wait)
        print("pages:", pages, flush=True)

        for n, name in enumerate(pages, 1):
            safe = re.sub(r"[^A-Za-z0-9]+", "-", name).strip("-") or f"page{n}"
            try:
                page.get_by_role("tab", name=re.compile(rf"^{re.escape(name)}(\s+Selected)?$")) \
                    .first.click(timeout=30_000)
            except Exception as exc:  # noqa: BLE001 - report and carry on to the next page
                print(f"{n} {name}: could not click the page tab: {str(exc)[:160]}", flush=True)
                failures += 1
                continue
            time.sleep(settle)
            text = page_text(page)
            (out / f"{n}-{safe}.txt").write_text(text)
            png = out / f"{n}-{safe}.png"
            page.screenshot(path=str(png))
            digits, bad = judge(text)
            print(f"{n} {name}: digits={digits} error_markers={bad} -> {png}", flush=True)
            failures += 1 if bad else 0
        ctx.close()

    if failures:
        sys.exit(f"{failures} page(s) failed or show a Power BI error banner - look at the screenshots.")
    print("All pages captured with no error markers. Now read the digits against your tie-out table.")


if __name__ == "__main__":
    main()
