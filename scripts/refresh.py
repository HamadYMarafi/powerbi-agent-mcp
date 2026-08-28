"""Read refresh history and status for the target semantic model. Triggering is double-gated.

WHY TWO GATES. A refresh is attributed to the identity that starts it. On a shared model it
lands in the tenant's refresh history under YOUR name, as if you had run a job on the data
team's model, and it burns their capacity. Attribution, not destructiveness, is the risk. So
--trigger refuses unless BOTH hold:

    1. config.yaml has  deploy.allow_refresh: true
    2. the command line carries  --i-have-permission

and you need the model owner's word before you set either. Stale data is not your emergency:
say so, and hand the owner a one-line request for the data team.

Reading is always fine - refresh history is a plain GET.

Usage:
    python3 scripts/refresh.py --history            # last 5 refreshes
    python3 scripts/refresh.py --history 20
    python3 scripts/refresh.py --status <requestId> # poll one refresh
    python3 scripts/refresh.py --selftest           # offline gate check
    python3 scripts/refresh.py --trigger --i-have-permission   # refused unless allow_refresh: true
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True  # no __pycache__ in the tree: .pyc files embed the absolute source path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from auth import powerbi_headers  # noqa: E402
from common import check_response, load_config, request, require_ids  # noqa: E402

# status 'Unknown' means in progress; extendedStatus carries the richer enum.
TERMINAL_STATUS = {"Completed", "Failed", "Disabled", "Cancelled"}
TERMINAL_EXTENDED = {"Completed", "Failed", "TimedOut", "Disabled", "Cancelled"}
# clearValues (empties the model) and defragment are deliberately not offered.
VALID_TYPES = ["full", "automatic", "dataOnly", "calculate"]

REFUSAL = (
    "REFUSED: refresh triggering is off for this repo's target model.\n"
    "\n"
    "A refresh is attributed to whoever starts it: it lands in the tenant's refresh history\n"
    "under YOUR name, on a model the data team owns, and it burns shared capacity.\n"
    "\n"
    "To trigger one you need BOTH, and the model owner's word before you set either:\n"
    "  1. deploy.allow_refresh: true   in config.yaml\n"
    "  2. --i-have-permission          on the command line\n"
    "\n"
    "Reading is unaffected:  python3 scripts/refresh.py --history"
)


def refresh_allowed(cfg: dict, flag: bool) -> bool:
    """Both gates must be open. The config alone or the flag alone is not enough."""
    return (cfg.get("deploy") or {}).get("allow_refresh") is True and bool(flag)


def refreshes_url(cfg: dict) -> str:
    ws_id, model_id = require_ids(cfg)
    return f"{cfg['api']['powerbi_base']}/groups/{ws_id}/datasets/{model_id}/refreshes"


def history(cfg: dict, top: int) -> list[dict]:
    resp = request("GET", f"{refreshes_url(cfg)}?$top={top}", powerbi_headers(cfg),
                   "Read refresh history")
    check_response(resp, "Read refresh history")
    return (resp.json() if resp.text else {}).get("value", [])


def print_history(rows: list[dict]) -> None:
    if not rows:
        print("No refresh history returned for this model.")
        return
    for r in rows:
        print(f"  {r.get('startTime', '?'):<26} -> {r.get('endTime', '?'):<26} {r.get('status', '?')}"
              + (f" ({r['extendedStatus']})" if r.get("extendedStatus") else "")
              + f"  [{r.get('refreshType', '?')}] id={r.get('requestId', '?')}")


def trigger(cfg: dict, headers: dict, refresh_type: str) -> str:
    resp = request("POST", refreshes_url(cfg), headers, "Trigger refresh",
                   json={"type": refresh_type, "commitMode": "transactional"})
    if resp.status_code == 400 and "another refresh" in resp.text.lower():
        sys.exit("A refresh is already running for this model (one at a time). Wait and retry.")
    check_response(resp, "Trigger refresh")
    # requestId is the last segment of the Location header; x-ms-request-id carries the same id.
    location = resp.headers.get("Location", "")
    request_id = location.rstrip("/").split("/")[-1] if location else ""
    request_id = request_id or resp.headers.get("x-ms-request-id", "")
    if not request_id:
        sys.exit("Refresh accepted but no request id in the Location/x-ms-request-id headers - "
                 "follow it with: python3 scripts/refresh.py --history")
    print(f"Refresh triggered (type={refresh_type}), request id: {request_id}")
    return request_id


def poll(cfg: dict, request_id: str, timeout_s: float = 3600.0) -> None:
    # Tokens are re-minted per iteration: a long refresh outlives one access token.
    url = f"{refreshes_url(cfg)}/{request_id}"
    deadline = time.monotonic() + timeout_s
    while True:
        if time.monotonic() > deadline:
            sys.exit(f"Refresh still running after {timeout_s:.0f}s - giving up on polling "
                     "(the refresh itself continues server-side).")
        resp = request("GET", url, powerbi_headers(cfg), "Poll refresh")
        check_response(resp, "Poll refresh")
        body = resp.json() if resp.text else {}
        status = body.get("status", "Unknown")
        extended = body.get("extendedStatus", "")
        done = resp.status_code == 200 and (status in TERMINAL_STATUS or extended in TERMINAL_EXTENDED)
        if done:
            final = extended if extended in TERMINAL_EXTENDED else status
            if final == "Completed":
                print(f"Refresh completed. Start: {body.get('startTime', '?')}  "
                      f"End: {body.get('endTime', '?')}")
                return
            details = body.get("messages") or body.get("serviceExceptionJson") or body
            sys.exit(f"Refresh {final}. Details: {json.dumps(details, indent=2, default=str)}")
        print(f"  status={status}" + (f" extendedStatus={extended}" if extended else "") + " ... waiting")
        time.sleep(10)


def selftest() -> int:
    """Offline: the two gates are AND-ed and default to closed."""
    assert not refresh_allowed({}, True), "an empty config must not allow a refresh"
    assert not refresh_allowed({"deploy": {}}, True), "a missing key defaults to closed"
    assert not refresh_allowed({"deploy": {"allow_refresh": False}}, True)
    assert not refresh_allowed({"deploy": {"allow_refresh": True}}, False), \
        "the config alone must not be enough - the flag is the second gate"
    assert not refresh_allowed({"deploy": {"allow_refresh": "yes"}}, True), "true means True, not truthy"
    assert refresh_allowed({"deploy": {"allow_refresh": True}}, True)
    assert not (load_config().get("deploy") or {}).get("allow_refresh"), \
        "config has deploy.allow_refresh true - it must ship false"
    print("refresh selftest: PASS (7 checks)")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Read semantic-model refresh history. Triggering is double-gated and off by default.")
    parser.add_argument("--history", nargs="?", type=int, const=5, metavar="N",
                        help="Print the last N refreshes (default 5). Read-only.")
    parser.add_argument("--status", metavar="REQUEST_ID", help="Poll one refresh by request id. Read-only.")
    parser.add_argument("--trigger", action="store_true",
                        help="Start a refresh. Refused unless deploy.allow_refresh is true AND "
                             "--i-have-permission is passed.")
    parser.add_argument("--i-have-permission", dest="permitted", action="store_true",
                        help="Assert that the model owner gave an explicit go-ahead.")
    parser.add_argument("--type", choices=VALID_TYPES, default="full")
    parser.add_argument("--no-wait", action="store_true", help="With --trigger: fire and exit without polling.")
    parser.add_argument("--selftest", action="store_true", help="Run the offline gate check and exit.")
    args = parser.parse_args()

    if args.selftest:
        sys.exit(selftest())

    cfg = load_config()
    if args.status:
        poll(cfg, args.status)
        return
    if args.history is not None:
        print_history(history(cfg, args.history))
        return
    if not args.trigger:
        parser.error("nothing to do - pass --history, --status <id>, or --trigger (double-gated, see --help).")

    # The only write path in this file. Both gates, or nothing - and no token is minted before this.
    if not refresh_allowed(cfg, args.permitted):
        sys.exit(REFUSAL)
    print(f"WARNING: triggering a refresh on '{(cfg.get('semantic_model') or {}).get('name', '?')}'. "
          "It will appear in the tenant refresh history under your account.")
    request_id = trigger(cfg, powerbi_headers(cfg), args.type)
    if not args.no_wait:
        poll(cfg, request_id)


if __name__ == "__main__":
    main()
