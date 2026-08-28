"""Shared helpers: config load/save, HTTP with 429 retry, Fabric long-running operations, paging.

Import from the other scripts; this file is not a command.
"""

from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path

import requests
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLE_PATH = REPO_ROOT / "config.example.yaml"


def config_path() -> Path:
    """Where config.yaml is looked for, first hit wins: $POWERBI_MCP_CONFIG, ./config.yaml (current
    directory), <repo>/config.yaml, ~/.config/powerbi-agent-mcp/config.yaml. Falls back to the
    example file (placeholders only) so read-only commands still run."""
    env = os.environ.get("POWERBI_MCP_CONFIG")
    candidates = ([Path(env)] if env else []) + [Path.cwd() / "config.yaml", REPO_ROOT / "config.yaml",
                                                  Path.home() / ".config" / "powerbi-agent-mcp" / "config.yaml"]
    for c in candidates:
        if c.is_file():
            return c
    return EXAMPLE_PATH


CONFIG_PATH = REPO_ROOT / "config.yaml"   # where save_ids() writes; reads go through config_path()
PLACEHOLDER_ID = "00000000-0000-0000-0000-000000000000"
FABRIC_BASE = "https://api.fabric.microsoft.com/v1"

# Contract column names (docs/MODEL_CONTRACT.md); config.yaml date_filters overrides them.
DATE_DEFAULTS = {
    "date_table": "Date",
    "date_column": "Date",
    "day_name_column": "DayName",
    "week_label_column": "WeekLabel",
    "has_sales_column": "HasSales",
}

# Fabric LRO terminal states (open enum: anything else counts as still running).
LRO_TERMINAL = {"Succeeded", "Failed"}


def load_config() -> dict:
    """config.yaml if present, else config.example.yaml with a warning (placeholders only)."""
    path = config_path()
    if path == EXAMPLE_PATH:
        if not path.exists():
            sys.exit(f"Neither config.yaml nor config.example.yaml found in {REPO_ROOT}")
        print("WARNING: config.yaml not found - using config.example.yaml, which holds placeholders "
              "only. Run: cp config.example.yaml config.yaml (or set POWERBI_MCP_CONFIG)", file=sys.stderr)
    with open(path) as fh:
        return yaml.safe_load(fh) or {}


def rewrite_ids(text: str, workspace_id: str, model_id: str) -> str:
    """Replace only the 'id:' line inside the workspace: and semantic_model: blocks of a config
    text. Every other line - including the comments kept from config.example.yaml - survives."""
    for section, value in (("workspace", workspace_id), ("semantic_model", model_id)):
        text, n = re.subn(rf"(?m)(^{section}:[ \t]*\n(?:[ \t]+[^\n]*\n)*?[ \t]+id:[ \t]*)\S+",
                          rf"\g<1>{value}", text, count=1)
        if n != 1:
            sys.exit(f"config.yaml has no '{section}:' block with an 'id:' line to rewrite")
    return text


def save_ids(workspace_id: str, model_id: str) -> None:
    """Write the two ids into config.yaml (gitignored) in place; never the committed example."""
    src = CONFIG_PATH if CONFIG_PATH.exists() else EXAMPLE_PATH
    CONFIG_PATH.write_text(rewrite_ids(src.read_text(), workspace_id, model_id))


def item_prefix(cfg: dict) -> str:
    return (cfg.get("deploy") or {}).get("item_prefix") or "ORG-"


def measure_prefix(cfg: dict) -> str:
    return (cfg.get("deploy") or {}).get("report_measure_prefix") or "RM "


def filter_marker(cfg: dict) -> str:
    """Prefix of every filter name date_filters.py writes ('org' -> 'orgLatestDayName'): its own
    key, deploy.filter_marker, letters and digits only. Deliberately NOT derived from item_prefix,
    so renaming your items never touches the filter names inside the template."""
    raw = (cfg.get("deploy") or {}).get("filter_marker") or "org"
    return re.sub(r"[^a-z0-9]", "", str(raw).lower()) or "org"


def date_columns(cfg: dict) -> dict:
    """Date-table column names: config.yaml date_filters over the contract defaults."""
    given = {k: v for k, v in (cfg.get("date_filters") or {}).items() if v}
    return {**DATE_DEFAULTS, **given}


def require_ids(cfg: dict) -> tuple[str, str]:
    """Return (workspace_id, model_id) or exit pointing at discover.py."""
    ws_id = (cfg.get("workspace") or {}).get("id")
    model_id = (cfg.get("semantic_model") or {}).get("id")
    if not ws_id or not model_id or PLACEHOLDER_ID in (ws_id, model_id):
        sys.exit("workspace.id / semantic_model.id are missing or still the placeholder in "
                 "config.yaml - run: python3 scripts/discover.py")
    return ws_id, model_id


def request(method: str, url: str, headers: dict, context: str,
            max_attempts: int = 5, **kwargs) -> requests.Response:
    """HTTP request honouring 429 Retry-After. Returns the response un-raised."""
    for attempt in range(1, max_attempts + 1):
        resp = requests.request(method, url, headers=headers, **kwargs)
        if resp.status_code != 429:
            return resp
        wait = float(resp.headers.get("Retry-After", 10) or 10)
        if attempt == max_attempts:
            break
        print(f"  {context}: throttled (429), retrying in {wait:.0f}s "
              f"[{attempt}/{max_attempts}]", file=sys.stderr)
        time.sleep(wait)
    return resp


def check_response(resp: requests.Response, context: str) -> requests.Response:
    """Exit with a readable message on HTTP errors. Never prints request headers."""
    if resp.status_code >= 400:
        sys.exit(
            f"{context} failed: HTTP {resp.status_code} {resp.reason}\n"
            f"URL: {resp.request.method} {resp.url}\n"
            f"Body: {resp.text[:2000]}"
        )
    return resp


def poll_lro(initial: requests.Response, headers: dict, context: str,
             timeout_s: float = 600.0, result_required: bool = False):
    """Follow a Fabric long-running operation to completion.

    200/201 -> return the body at once. 202 -> poll GET /operations/{id} until Succeeded
    (then fetch /result) or Failed.

    result_required=True (getDefinition): a failure to fetch /result is fatal.
    result_required=False (updateDefinition, which has no result payload): a 4xx from /result
    means "no result" and the operation state is returned instead.
    """
    if initial.status_code != 202:
        check_response(initial, context)
        return initial.json() if initial.text else None

    op_url = initial.headers.get("Location")
    if not op_url:
        op_id = initial.headers.get("x-ms-operation-id")
        if not op_id:
            sys.exit(f"{context}: 202 received but no Location/x-ms-operation-id header")
        op_url = f"{FABRIC_BASE}/operations/{op_id}"

    retry_after = float(initial.headers.get("Retry-After", 5) or 5)
    deadline = time.monotonic() + timeout_s
    while True:
        if time.monotonic() > deadline:
            sys.exit(f"{context}: operation did not finish within {timeout_s:.0f}s")
        time.sleep(min(retry_after, 30.0))
        op = request("GET", op_url, headers, f"{context} (poll)")
        check_response(op, f"{context} (polling operation)")
        body = op.json()
        status = body.get("status")
        if status == "Succeeded":
            result = request("GET", op_url.rstrip("/") + "/result", headers,
                             f"{context} (result)")
            if result.status_code == 200 and result.text:
                return result.json()
            if result_required:
                check_response(result, f"{context} (fetch operation result)")
                sys.exit(f"{context}: operation Succeeded but /result returned "
                         f"HTTP {result.status_code} with no body.")
            if 400 <= result.status_code < 500 and result.status_code != 429:
                return body  # operation has no result payload
            check_response(result, f"{context} (fetch operation result)")
            return body
        if status == "Failed":
            err = body.get("error") or {}
            sys.exit(f"{context}: operation Failed: "
                     f"{err.get('errorCode', '?')} - {err.get('message', body)}")
        retry_after = float(op.headers.get("Retry-After", retry_after) or retry_after)


def get_paginated(url: str, headers: dict, context: str) -> list:
    """GET a Fabric collection endpoint, following continuationUri pages."""
    items: list = []
    next_url = url
    while next_url:
        resp = request("GET", next_url, headers, context)
        check_response(resp, context)
        body = resp.json()
        items.extend(body.get("value", []))
        next_url = body.get("continuationUri")  # absent on the last page
    return items
