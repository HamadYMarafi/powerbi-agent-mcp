"""powerbi-agent-mcp - an MCP server that connects an AI agent to YOUR Power BI / Fabric tenant.

It wraps the toolkit in scripts/ (same config.yaml, same guardrails) and exposes it as MCP tools
over stdio. The guardrails live in code, not in prose:
  - deploy_report refuses items whose name lacks your prefix and models not allowed in config.yaml
  - run_dax accepts EVALUATE / DEFINE only
  - there is no tool that triggers a refresh - refresh_history is read-only on purpose

Run from the repo root:
    python -m powerbi_agent_mcp            # stdio MCP server (config via POWERBI_MCP_CONFIG)
    python -m powerbi_agent_mcp --check    # no AI involved: load config, mint tokens, list the workspace
or point your MCP host straight at this file:  python /path/to/repo/powerbi_agent_mcp/server.py
"""
from __future__ import annotations

import base64
import contextlib
import inspect
import io
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import auth  # noqa: E402
import check_report  # noqa: E402
import common  # noqa: E402
import date_filters  # noqa: E402
import deploy_report as deploy_mod  # noqa: E402  (aliased: a tool below carries the same name)
import discover  # noqa: E402
import refresh  # noqa: E402
import validate as dax  # noqa: E402

from mcp.server.mcpserver import MCPServer  # noqa: E402

GUID = re.compile(r"^[0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}$")
RULES_FILE = REPO / "rules" / "CLAUDE.md"

INSTRUCTIONS = """Power BI / Fabric tools for building and verifying report pages against the user's own tenant.
Read guardrails() before the first change. The rules that are enforced in code: items you deploy must carry
the configured prefix; DAX is read-only (EVALUATE/DEFINE); nothing here triggers a model refresh.
The rules you must keep yourself: never edit an item you did not create (clone it), keep the theme once
stakeholders have seen it, validate_report after every batch, and a page is not done until you have looked
at capture_pages output with data in every state."""

server = MCPServer("powerbi-agent-mcp", instructions=INSTRUCTIONS, version="0.1.0")


# --- plumbing -----------------------------------------------------------------------------------

def _guarded(fn):
    """The scripts refuse with sys.exit(<message>) and print progress to stdout. Over stdio, stdout IS
    the MCP transport, so everything printed is captured and returned inside the result, and a refusal
    comes back as {"error": ...} instead of a dead server."""
    def wrapper(*args, **kwargs):
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):  # ponytail: process-wide swap; tools run one at a time
                result = fn(*args, **kwargs)
        except SystemExit as exc:
            result = {"error": str(exc.code) if exc.code not in (None, 0) else "stopped"}
        except Exception as exc:  # noqa: BLE001 - the agent needs the message, whatever it is
            result = {"error": f"{type(exc).__name__}: {exc}"}
        log = buf.getvalue().strip()
        if isinstance(result, dict):
            if log:
                result.setdefault("log", log)
            return json.dumps(result, indent=1, default=str)
        return result if isinstance(result, str) else json.dumps(result, default=str)

    sig = inspect.signature(fn)
    wrapper.__signature__ = sig.replace(return_annotation=str)  # the host builds the tool schema from this
    wrapper.__annotations__ = {**getattr(fn, "__annotations__", {}), "return": "str"}
    wrapper.__name__, wrapper.__doc__ = fn.__name__, fn.__doc__
    return wrapper


def tool(fn):
    return server.tool(structured_output=False)(_guarded(fn))


@contextlib.contextmanager
def _argv(argv: list[str]):
    saved, sys.argv = sys.argv, argv
    try:
        yield
    finally:
        sys.argv = saved


def _cfg() -> dict:
    return common.load_config()


def _workspace_id(cfg: dict, headers: dict, workspace: str) -> str:
    if not workspace:
        return common.require_ids(cfg)[0]
    if GUID.match(workspace):
        return workspace
    for ws in common.get_paginated(f"{cfg['api']['fabric_base']}/workspaces", headers, "List workspaces"):
        if ws.get("displayName", "").lower() == workspace.lower():
            return ws["id"]
    raise ValueError(f"workspace '{workspace}' not found - use the exact display name or the id")


def _item_id(cfg: dict, headers: dict, ws_id: str, name: str, item_type: str) -> str:
    if GUID.match(name):
        return name
    url = f"{cfg['api']['fabric_base']}/workspaces/{ws_id}/items?type={item_type}"
    for item in common.get_paginated(url, headers, f"List {item_type} items"):
        if item.get("displayName", "").lower() == name.lower():
            return item["id"]
    raise ValueError(f"{item_type} '{name}' not found in workspace {ws_id} - use the exact display name or the id")


def _model_cfg(cfg: dict, workspace: str, model: str) -> dict:
    """A copy of the config whose workspace/model ids point at the requested pair (default: config.yaml)."""
    if not workspace and not model:
        common.require_ids(cfg)
        return cfg
    headers = auth.fabric_headers(cfg)
    ws_id = _workspace_id(cfg, headers, workspace)
    model_name = model or cfg.get("semantic_model", {}).get("name") or ""
    model_id = _item_id(cfg, headers, ws_id, model_name, "SemanticModel")
    out = json.loads(json.dumps(cfg))
    out.setdefault("workspace", {})["id"] = ws_id
    out.setdefault("semantic_model", {})["id"] = model_id
    return out


def _write_parts(parts: list, out: Path) -> int:
    for part in parts:
        rel = part["path"].replace("\\", "/")
        if rel.startswith("/") or ".." in rel.split("/"):
            raise ValueError(f"refusing suspicious part path: {rel}")
        if part.get("payloadType") != "InlineBase64":
            raise ValueError(f"unexpected payloadType {part.get('payloadType')} for {rel}")
        target = out / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(base64.b64decode(part["payload"]))
    return len(parts)


# --- tools --------------------------------------------------------------------------------------

@tool
def connection_status() -> dict:
    """What the server is pointed at: config file, workspace, model, prefixes, and whether the Azure CLI
    can mint tokens for the Power BI and Fabric APIs (expiry shown). Call this first in a session."""
    cfg = _cfg()
    api = cfg.get("api", {})
    tokens = {}
    for key, default in (("powerbi_resource", "https://analysis.windows.net/powerbi/api"),
                         ("fabric_resource", "https://api.fabric.microsoft.com")):
        try:
            tokens[key] = {"ok": True, "expires": auth.token_expiry(api.get(key) or default)}
        except Exception as exc:  # noqa: BLE001
            tokens[key] = {"ok": False, "error": str(exc)[:300]}
    deploy = cfg.get("deploy", {})
    return {
        "config_file": str(common.config_path()),
        "workspace": cfg.get("workspace"),
        "semantic_model": cfg.get("semantic_model"),
        "item_prefix": deploy.get("item_prefix"),
        "report_measure_prefix": deploy.get("report_measure_prefix"),
        "allowed_model_ids": deploy.get("allowed_model_ids", []),
        "refresh_trigger_tool": "none - by design",
        "tokens": tokens,
    }


@tool
def list_workspaces() -> dict:
    """Workspaces the signed-in identity can see (Fabric): id and display name."""
    cfg = _cfg()
    rows = common.get_paginated(f"{cfg['api']['fabric_base']}/workspaces", auth.fabric_headers(cfg), "List workspaces")
    return {"count": len(rows), "workspaces": [{"id": w.get("id"), "name": w.get("displayName"), "type": w.get("type")} for w in rows]}


@tool
def list_items(workspace: str = "", item_type: str = "") -> dict:
    """Items in a workspace (Report, SemanticModel, Lakehouse, ...). workspace = display name or id;
    empty = the configured workspace. item_type filters (e.g. "Report")."""
    cfg = _cfg()
    headers = auth.fabric_headers(cfg)
    ws_id = _workspace_id(cfg, headers, workspace)
    url = f"{cfg['api']['fabric_base']}/workspaces/{ws_id}/items" + (f"?type={item_type}" if item_type else "")
    rows = common.get_paginated(url, headers, "List items")
    return {"workspace_id": ws_id, "count": len(rows),
            "items": [{"id": i.get("id"), "name": i.get("displayName"), "type": i.get("type")} for i in rows]}


@tool
def get_model_schema(workspace: str = "", model: str = "", max_names: int = 300) -> dict:
    """Export the semantic model's definition (TMDL) into paths.schema_dir and summarise it: tables with
    their columns and measures. Read-only. Defaults to the configured model. Read this before writing DAX."""
    cfg = _model_cfg(_cfg(), workspace, model)
    ws_id, model_id = common.require_ids(cfg)
    parts = discover.export_definition(cfg, auth.fabric_headers(cfg), ws_id, model_id)
    schema_dir = discover.write_schema(cfg, parts)
    summary = discover.summarise_schema(schema_dir)
    tables = {}
    for name, info in sorted(summary.items()):
        tables[name] = {"columns": info["columns"][:max_names], "measures": info["measures"][:max_names]}
    return {"workspace_id": ws_id, "model_id": model_id, "schema_dir": str(schema_dir),
            "tables": len(summary), "columns": sum(len(t["columns"]) for t in summary.values()),
            "measures": sum(len(t["measures"]) for t in summary.values()), "detail": tables}


@tool
def run_dax(query: str, workspace: str = "", model: str = "", max_rows: int = 200) -> dict:
    """Run a READ-ONLY DAX query (must start with EVALUATE or DEFINE) against the model via executeQueries.
    Batch what you need into one query; every call runs under the user's identity and costs capacity."""
    dax.assert_read_only(query)          # refuse before any config or HTTP
    cfg = _model_cfg(_cfg(), workspace, model)
    rows = dax.run_dax(cfg, query)
    return {"rows_returned": len(rows), "rows_shown": min(len(rows), max_rows), "rows": rows[:max_rows]}


@tool
def get_report_definition(report: str, out_dir: str, workspace: str = "", format: str = "") -> dict:
    """Download a report's definition (PBIR: report.json, pages/, visuals/) into a local folder.
    report = display name or id. Reading is safe on any report; edit only your own clone."""
    cfg = _cfg()
    headers = auth.fabric_headers(cfg)
    ws_id = _workspace_id(cfg, headers, workspace)
    report_id = _item_id(cfg, headers, ws_id, report, "Report")
    url = f"{cfg['api']['fabric_base']}/workspaces/{ws_id}/items/{report_id}/getDefinition" + (f"?format={format}" if format else "")
    resp = common.request("POST", url, headers, "Get report definition")
    result = common.poll_lro(resp, headers, "Get report definition", result_required=True)
    parts = (result or {}).get("definition", {}).get("parts", [])
    if not parts:
        raise ValueError("getDefinition returned no parts")
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    return {"report_id": report_id, "folder": str(out), "parts_written": _write_parts(parts, out)}


@tool
def validate_report(folder: str, baseline: str = "", allow_saved_selection: bool = False, run_cli: bool = True) -> dict:
    """Validate a local PBIR report folder: Microsoft's PBIR validator CLI (npx, Node 20+; run_cli=false
    skips it) plus the offline structural checks (overlaps, canvas bounds, unique names, date pins present,
    banned filter kinds, and theme byte-identical to `baseline` when given). Must report ok=true before you deploy."""
    path = Path(folder)
    if not (path / "definition").is_dir():
        raise ValueError(f"{folder} has no definition/ folder - not a PBIR report item")
    c = check_report.Checker()
    if run_cli:
        check_report.run_validator(path, c)
    if baseline:
        check_report.check_theme(path, Path(baseline), c)
    else:
        c.note("no baseline given: theme, colour and font checks skipped")
    check_report.check_folder(path, _cfg(), c, allow_saved_selection)
    return {"ok": not c.fails, "failures": c.fails}


@tool
def set_date_filters(visual_json: str, mode: str, weeks: int = 3) -> dict:
    """Write the self-maintaining date filters on one visual.json: mode = latest-day (the latest traded day,
    LY/LW resolve correctly), window-weeks (last N trading weeks, traded days only), this-week, or none
    (strip them). Never hand-write these filters."""
    if mode not in date_filters.KINDS:
        raise ValueError(f"mode must be one of {list(date_filters.KINDS)}")
    cfg = _cfg()
    names = date_filters.apply(Path(visual_json), mode, common.date_columns(cfg), common.filter_marker(cfg), weeks)
    return {"visual": visual_json, "filters": names}


@tool
def deploy_report(folder: str, bind: bool = False) -> dict:
    """Create or update the report item from a local '<Name>.Report' folder, by display name.
    Guardrails (enforced): the name must start with deploy.item_prefix; the bound model must be the
    configured one or listed in deploy.allowed_model_ids; an existing item without the prefix is never
    touched. bind=true first writes definition.pbir's connection from config.yaml (do it once)."""
    with _argv(["deploy_report.py", folder] + (["--bind"] if bind else [])):
        deploy_mod.main()
    return {"ok": True, "folder": folder}


@tool
def capture_pages(target: str, out_dir: str, headless: bool = True, settle_seconds: int = 60) -> dict:
    """Open the deployed report in a browser (Playwright), visit every page, and save a PNG plus an
    accessibility-text dump per page, with digit and error-marker counts. target = report item id or URL.
    First run: headless=false so you can sign in once; the profile is kept for later headless runs."""
    cmd = [sys.executable, str(REPO / "scripts" / "capture_pages.py"), target, "--out", out_dir,
           "--settle", str(settle_seconds)] + (["--headless"] if headless else [])
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=3600, cwd=REPO)  # own process: Playwright must not run inside the server's event loop
    files = sorted(p.name for p in Path(out_dir).glob("*")) if Path(out_dir).is_dir() else []
    return {"ok": proc.returncode == 0, "out_dir": out_dir, "files": files,
            "stdout": proc.stdout[-4000:], "stderr": proc.stderr[-2000:]}


@tool
def refresh_history(workspace: str = "", model: str = "", top: int = 5) -> dict:
    """Read-only: the model's last refreshes (type, start, end, status, error). There is deliberately no
    tool that triggers a refresh - on a shared model that lands under the user's name."""
    cfg = _model_cfg(_cfg(), workspace, model)
    rows = refresh.history(cfg, top)
    keep = ("refreshType", "startTime", "endTime", "status", "extendedStatus")
    out = []
    for r in rows:
        row = {k: r.get(k) for k in keep if k in r}
        if r.get("serviceExceptionJson"):
            row["error"] = str(r["serviceExceptionJson"])[:500]
        out.append(row)
    return {"count": len(out), "refreshes": out, "trigger": "not available - by design"}


@tool
def guardrails() -> str:
    """The universal rules for working on Power BI / Fabric (rules/CLAUDE.md). Read before the first change."""
    return RULES_FILE.read_text(encoding="utf-8") if RULES_FILE.exists() else "rules/CLAUDE.md is missing from this checkout"


@server.resource("guardrails://rules", name="guardrails", description="The universal rules (rules/CLAUDE.md)", mime_type="text/markdown")
def rules_resource() -> str:
    return RULES_FILE.read_text(encoding="utf-8") if RULES_FILE.exists() else ""


# --- entry points --------------------------------------------------------------------------------

def check() -> int:
    """Human smoke test, no AI involved. Exit 0 when config loads, tokens mint and the workspace is visible."""
    status = json.loads(connection_status())
    print(json.dumps(status, indent=1, default=str))
    ok = all(t.get("ok") for t in status.get("tokens", {}).values())
    if not ok:
        print("\nFAIL: the Azure CLI could not mint a token - run: az login")
        return 1
    ws = json.loads(list_workspaces())
    if "error" in ws:
        print(f"\nFAIL: {ws['error']}")
        return 1
    wanted = (status.get("workspace") or {}).get("name", "")
    names = [w["name"] for w in ws.get("workspaces", [])]
    hit = wanted in names
    print(f"\n{ws['count']} workspaces visible; configured workspace '{wanted}' {'found' if hit else 'NOT found'}")
    print("OK" if hit else "FAIL: fix workspace.name in config.yaml (exact display name)")
    return 0 if hit else 1


def main() -> None:
    if "--check" in sys.argv:
        raise SystemExit(check())
    server.run()


if __name__ == "__main__":
    main()
