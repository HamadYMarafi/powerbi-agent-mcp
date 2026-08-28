"""Offline checks on the MCP server: the tool surface is what the docs promise, and the guardrails refuse
what they should without touching any tenant. Run: python3 tests/test_server.py (needs `pip install mcp`)."""
from __future__ import annotations

import asyncio
import json
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from powerbi_agent_mcp import server as s  # noqa: E402

EXPECTED = ["connection_status", "list_workspaces", "list_items", "get_model_schema", "run_dax",
            "get_report_definition", "validate_report", "set_date_filters", "deploy_report",
            "capture_pages", "refresh_history", "guardrails"]


def main() -> None:
    tools = asyncio.run(s.server.list_tools())
    names = [t.name for t in tools]
    assert names == EXPECTED, f"tool surface changed: {names}"
    assert not [n for n in names if "trigger" in n or n == "refresh"], "no refresh trigger tool, by design"
    for t in tools:
        assert t.description, f"{t.name} has no description"
        assert "properties" in (t.input_schema or {}), f"{t.name} has no input schema"
    assert [str(r.uri) for r in asyncio.run(s.server.list_resources())] == ["guardrails://rules"]
    print("PASS tool surface: 12 tools, guardrails resource, no refresh trigger")

    out = json.loads(s.run_dax("SELECT 1"))
    assert "error" in out and "EVALUATE" in out["error"], out
    print("PASS run_dax refuses a non-EVALUATE query before any HTTP")

    out = json.loads(s.deploy_report(str(REPO / "report-template")))
    assert "error" in out, out
    print(f"PASS deploy_report refuses the unprefixed template: {out['error'][:80]}")

    tmp = Path(tempfile.mkdtemp())
    try:
        folder = tmp / "ORG-Test.Report"
        shutil.copytree(REPO / "report-template", folder)
        visual = sorted(folder.rglob("visual.json"))[0]
        out = json.loads(s.set_date_filters(str(visual), "none"))
        assert not {"orgLatestDayName", "orgLatestWeek"} & set(out["filters"]), out
        out = json.loads(s.set_date_filters(str(visual), "latest-day"))   # put the template's pins back
        assert {"orgLatestDayName", "orgLatestWeek"} <= set(out["filters"]), out
        out = json.loads(s.set_date_filters(str(visual), "yesterday"))
        assert "error" in out, out
        print("PASS set_date_filters strips, writes, and refuses an unknown mode")

        shutil.copytree(REPO / "report-template", tmp / "template-copy")
        out = json.loads(s.validate_report(str(folder), baseline=str(tmp / "template-copy"), run_cli=False))
        assert out["ok"] is True and out["failures"] == [], out
        out = json.loads(s.validate_report(str(tmp), run_cli=False))
        assert "error" in out, out
        print("PASS validate_report: offline checks pass on the template, refuse a non-report folder")
    finally:
        shutil.rmtree(tmp)

    text = s.guardrails()
    assert "refresh" in text.lower() and "prefix" in text.lower(), "rules/CLAUDE.md must state the refresh and prefix rules"
    print("PASS guardrails() returns the rules text")

    out = json.loads(s.connection_status())
    assert out["refresh_trigger_tool"].startswith("none"), out
    assert "tokens" in out and "item_prefix" in out, out
    print("PASS connection_status reports config and token state")
    print("\nall server checks passed")


if __name__ == "__main__":
    main()
