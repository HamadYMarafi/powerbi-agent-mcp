"""Offline guardrail tests. No pytest, no tenant, no network. Plain asserts.

Covers what is cheap to test and expensive to get wrong:
  - deploy_report.py refuses a display name without the prefix, a byPath binding and a model
    id that is not allowed; packs no hidden file except the root .platform; --bind writes the
    binding from config.yaml
  - discover.py's config rewrite keeps every comment; secret_scan.py skips gitignored paths
  - refresh.py refuses to trigger without BOTH the config flag and --i-have-permission
  - validate.py refuses anything that is not EVALUATE / DEFINE
  - date_filters.py writes the documented shapes with the configured column names
  - capture_pages.py judges error markers
  - config.example.yaml carries every key the scripts read, with the safe defaults
  - report-template is deployable and passes check_report.py

Usage:
    python3 tests/test_guardrails.py            # all
    python3 tests/test_guardrails.py deploy     # only tests whose name contains 'deploy'
"""

from __future__ import annotations

import base64
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# Keep the tree clean for the secret scan: no __pycache__ from the tests or their subprocesses.
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import capture_pages  # noqa: E402
import date_filters  # noqa: E402
import deploy_report  # noqa: E402
import refresh  # noqa: E402
import validate  # noqa: E402
from common import (DATE_DEFAULTS, EXAMPLE_PATH, PLACEHOLDER_ID, date_columns,  # noqa: E402
                    filter_marker, load_config, rewrite_ids)

TESTS: list = []
# No literal GUID but the placeholder may appear in the repo (tools/secret_scan.py), so build the others.
MODEL_ID = PLACEHOLDER_ID.replace("0", "1")
ALLOWED_ID = PLACEHOLDER_ID.replace("0", "2")
WRONG_ID = PLACEHOLDER_ID.replace("0", "3")
CFG = {"deploy": {"item_prefix": "ORG-", "allowed_model_ids": [ALLOWED_ID]},
       "semantic_model": {"id": MODEL_ID}}


def conn(model_id: str) -> str:
    return ('Data Source="powerbi://api.powerbi.com/v1.0/myorg/<Workspace Name>";'
            f'initial catalog="<Model Name>";integrated security=ClaimsToken;semanticmodelid={model_id}')


def test(fn):
    TESTS.append(fn)
    return fn


def exits(fn, *a, **kw) -> str:
    """Call fn expecting sys.exit; return the exit message. Fail if it returns."""
    try:
        fn(*a, **kw)
    except SystemExit as e:
        return str(e.code)
    raise AssertionError(f"{getattr(fn, '__name__', fn)} returned instead of exiting")


def fake_report(root: Path, name: str, *, model_id: str = MODEL_ID, by_path: bool = False,
                item_type: str = "Report") -> Path:
    folder = root / f"{name}.Report"
    (folder / "definition" / "pages" / "p1").mkdir(parents=True, exist_ok=True)
    (folder / ".platform").write_text(json.dumps(
        {"metadata": {"type": item_type, "displayName": name},
         "config": {"version": "2.0", "logicalId": PLACEHOLDER_ID}}))
    ref = {"byPath": {"path": "../x.SemanticModel"}} if by_path else {"byConnection": {"connectionString": conn(model_id)}}
    (folder / "definition.pbir").write_text(json.dumps({"version": "4.0", "datasetReference": ref}))
    (folder / "definition" / "report.json").write_text('{"$schema":"x"}')
    (folder / "definition" / "pages" / "p1" / "page.json").write_text('{"name":"p1"}')
    return folder


def load_example() -> dict:
    return yaml.safe_load(EXAMPLE_PATH.read_text())


# --- deploy_report guardrails -------------------------------------------------
@test
def test_deploy_prefix_guard():
    root = Path(tempfile.mkdtemp(prefix="playbook-tests-"))
    try:
        name, parts = deploy_report.read_item_folder(fake_report(root, "ORG-Sales Report"), CFG)
        assert name == "ORG-Sales Report"
        assert sorted(p["path"] for p in parts) == [".platform", "definition.pbir",
                                                    "definition/pages/p1/page.json", "definition/report.json"]
        assert base64.b64decode(next(p["payload"] for p in parts
                                     if p["path"] == "definition/report.json")) == b'{"$schema":"x"}'
        msg = exits(deploy_report.read_item_folder, fake_report(root, "Sales Report"), CFG)
        assert "GUARDRAIL" in msg and "ORG-" in msg, msg
        assert "GUARDRAIL" in exits(deploy_report.read_item_folder, fake_report(root, "ORGSales Report"), CFG)
        # the prefix is configurable, not hard-coded
        yc = {**CFG, "deploy": {**CFG["deploy"], "item_prefix": "YC-"}}
        deploy_report.read_item_folder(fake_report(root, "YC-Sales Report"), yc)
        assert "YC-" in exits(deploy_report.read_item_folder, fake_report(root, "ORG-Sales Report"), yc)
    finally:
        shutil.rmtree(root, ignore_errors=True)


@test
def test_deploy_skips_hidden_files_except_platform():
    root = Path(tempfile.mkdtemp(prefix="playbook-tests-"))
    try:
        folder = fake_report(root, "ORG-Hidden")
        (folder / ".pbi").mkdir()
        (folder / ".pbi" / "localSettings.json").write_text("{}")
        (folder / "definition" / ".DS_Store").write_bytes(b"\x00")
        _, parts = deploy_report.read_item_folder(folder, CFG)
        paths = [p["path"] for p in parts]
        assert ".platform" in paths
        assert not any(seg.startswith(".") for p in paths if p != ".platform" for seg in p.split("/")), paths
    finally:
        shutil.rmtree(root, ignore_errors=True)


@test
def test_deploy_refuses_bypath_and_wrong_model():
    root = Path(tempfile.mkdtemp(prefix="playbook-tests-"))
    try:
        msg = exits(deploy_report.read_item_folder, fake_report(root, "ORG-ByPath", by_path=True), CFG)
        assert "byPath" in msg and "byConnection" in msg, msg
        msg = exits(deploy_report.read_item_folder, fake_report(root, "ORG-Wrong", model_id=WRONG_ID), CFG)
        assert "GUARDRAIL" in msg and "allowed_model_ids" in msg, msg
        deploy_report.read_item_folder(fake_report(root, "ORG-Allowed", model_id=ALLOWED_ID), CFG)
        folder = fake_report(root, "ORG-NoId2")
        (folder / "definition.pbir").write_text(json.dumps(
            {"version": "4.0", "datasetReference": {"byConnection": {"connectionString": "Data Source=x"}}}))
        assert "semanticmodelid" in exits(deploy_report.read_item_folder, folder, CFG)
        assert "not 'Report'" in exits(deploy_report.read_item_folder,
                                       fake_report(root, "ORG-Model", item_type="SemanticModel"), CFG)
    finally:
        shutil.rmtree(root, ignore_errors=True)


@test
def test_deploy_bind_writes_the_binding_from_config():
    root = Path(tempfile.mkdtemp(prefix="playbook-tests-"))
    try:
        cfg = {**CFG, "workspace": {"name": "Sales WS", "id": ALLOWED_ID},
               "semantic_model": {"name": "Sales Model", "id": MODEL_ID},
               "api": {"powerbi_base": "https://api.powerbi.com/v1.0/myorg"}}
        folder = fake_report(root, "ORG-Bind", by_path=True)          # wrong binding on purpose
        assert "byPath" in exits(deploy_report.read_item_folder, folder, cfg)
        conn = deploy_report.bind_pbir(folder, cfg)
        assert conn == ('Data Source="powerbi://api.powerbi.com/v1.0/myorg/Sales WS";initial catalog="Sales Model";'
                        f"integrated security=ClaimsToken;semanticmodelid={MODEL_ID}"), conn
        pbir = json.loads((folder / "definition.pbir").read_text())
        assert "byPath" not in pbir["datasetReference"]
        deploy_report.read_item_folder(folder, cfg)                    # the guardrail now passes
        assert deploy_report.bind_pbir(folder, cfg) == conn            # idempotent
        assert "placeholders" in exits(deploy_report.bind_pbir, folder,
                                       {**cfg, "workspace": {"name": "<Workspace Name>", "id": ALLOWED_ID}})
        assert "discover.py" in exits(deploy_report.bind_pbir, folder,
                                      {**cfg, "semantic_model": {"name": "Sales Model", "id": PLACEHOLDER_ID}})
    finally:
        shutil.rmtree(root, ignore_errors=True)


# --- discover.py config rewrite ------------------------------------------------
@test
def test_rewrite_ids_keeps_every_comment():
    text = EXAMPLE_PATH.read_text()
    out = rewrite_ids(text, ALLOWED_ID, MODEL_ID)
    cfg = yaml.safe_load(out)
    assert cfg["workspace"]["id"] == ALLOWED_ID and cfg["semantic_model"]["id"] == MODEL_ID
    assert out.count("#") == text.count("#") and len(out.splitlines()) == len(text.splitlines()), "a line or comment was lost"
    assert rewrite_ids(out, PLACEHOLDER_ID, PLACEHOLDER_ID) == text, "round trip must reproduce the example"
    assert "workspace" in exits(rewrite_ids, "semantic_model:\n  id: x\n", ALLOWED_ID, MODEL_ID)


# --- secret scan --------------------------------------------------------------
@test
def test_secret_scan_skips_gitignored_paths():
    root = Path(tempfile.mkdtemp(prefix="playbook-tests-"))
    try:
        (root / ".gitignore").write_text("config.yaml\n*.Report/\n!report-template/\n")
        (root / "config.yaml").write_text(f"semantic_model:\n  id: {MODEL_ID}\n")
        (root / "ORG-X.Report").mkdir()
        (root / "ORG-X.Report" / ".platform").write_text(json.dumps({"logicalId": MODEL_ID}))
        (root / "report-template").mkdir()
        (root / "report-template" / ".platform").write_text(json.dumps({"logicalId": PLACEHOLDER_ID}))

        def scan():
            return subprocess.run([sys.executable, str(REPO_ROOT / "tools/secret_scan.py"), str(root)],
                                  capture_output=True, text=True, timeout=60)
        p = scan()
        assert p.returncode == 0 and "hits: 0" in p.stdout, p.stdout
        (root / "README.md").write_text(f"id {MODEL_ID} mail " + "someone@" + "example.com")
        p = scan()
        assert p.returncode == 1 and "hits: 2" in p.stdout, p.stdout
    finally:
        shutil.rmtree(root, ignore_errors=True)


# --- refresh double gate ------------------------------------------------------
@test
def test_refresh_double_gate():
    assert not refresh.refresh_allowed({}, True)
    assert not refresh.refresh_allowed({"deploy": {"allow_refresh": True}}, False), "config alone must not open the gate"
    assert not refresh.refresh_allowed({"deploy": {"allow_refresh": False}}, True), "the flag alone must not open the gate"
    assert not refresh.refresh_allowed({"deploy": {"allow_refresh": "true"}}, True), "a string is not True"
    assert refresh.refresh_allowed({"deploy": {"allow_refresh": True}}, True)
    assert not refresh.refresh_allowed(load_example(), True), "config.example.yaml must ship allow_refresh false"
    # Only if the live config is closed do we exercise the CLI: it must refuse before minting a token.
    assert not refresh.refresh_allowed(load_config(), True), "config.yaml has allow_refresh true - keep it false"
    for argv in (["--trigger"], ["--trigger", "--i-have-permission"],
                 ["--trigger", "--i-have-permission", "--type", "dataOnly"]):
        p = subprocess.run([sys.executable, "scripts/refresh.py", *argv], cwd=REPO_ROOT,
                           capture_output=True, text=True, timeout=60)
        assert p.returncode != 0 and "REFUSED" in p.stderr, f"refresh.py {argv}: {p.stderr[-400:]}"
    p = subprocess.run([sys.executable, "scripts/refresh.py"], cwd=REPO_ROOT,
                       capture_output=True, text=True, timeout=60)
    assert p.returncode != 0 and "nothing to do" in p.stderr, p.stderr


# --- validate.py read-only guard ---------------------------------------------
@test
def test_validate_refuses_non_read_only_dax():
    validate.assert_read_only('EVALUATE ROW("v", [Sales])')
    validate.assert_read_only("  // comment\n/* block */ DEFINE MEASURE 'M'[X] = 1\nEVALUATE ROW(\"v\", [X])")
    validate.assert_read_only("evaluate VALUES('Date'[Date])")
    for bad in ("", "SELECT 1", "CREATE TABLE x", "DELETE 'Date'", "EVALUATION", "-- only a comment"):
        assert "REFUSED" in exits(validate.assert_read_only, bad), bad


# --- date_filters shapes ------------------------------------------------------
@test
def test_date_filter_shapes():
    cols, marker = dict(DATE_DEFAULTS), "org"
    day = date_filters.build("latest-day", cols, marker)
    assert [f["name"] for f in day] == ["orgLatestDayName", "orgLatestWeek"]
    assert [f["field"]["Column"]["Property"] for f in day] == ["DayName", "WeekLabel"]
    for f in day:
        q = f["filter"]["From"][0]["Expression"]["Subquery"]["Query"]
        assert q["Top"] == 1
        assert q["Where"][0]["Condition"]["Comparison"]["Left"]["Column"]["Property"] == "HasSales"
        assert q["OrderBy"][0]["Expression"]["Aggregation"]["Function"] == 4
        assert q["OrderBy"][0]["Direction"] == 2
    weeks = date_filters.build("window-weeks", cols, marker)
    assert weeks[0]["filter"]["From"][0]["Expression"]["Subquery"]["Query"]["Top"] == 3
    assert weeks[1]["type"] == "Categorical" and weeks[1]["field"]["Column"]["Property"] == "HasSales"
    assert date_filters.build("this-week", cols, marker)[0]["filter"]["From"][0]["Expression"]["Subquery"]["Query"]["Top"] == 1
    # column names and the marker come from config; the marker is its own key, never the item prefix
    cfg = {"deploy": {"item_prefix": "YC-", "filter_marker": "YC"},
           "date_filters": {"date_table": "Calendar", "day_name_column": "Weekday", "has_sales_column": "IsTraded"}}
    assert filter_marker(cfg) == "yc"
    assert filter_marker({"deploy": {"item_prefix": "YC-"}}) == "org", "item_prefix alone must not move the marker"
    f = date_filters.build("latest-day", date_columns(cfg), filter_marker(cfg))[0]
    assert f["name"] == "ycLatestDayName" and f["field"]["Column"]["Property"] == "Weekday"
    assert f["field"]["Column"]["Expression"]["SourceRef"]["Entity"] == "Calendar"
    assert json.dumps(f).count('"IsTraded"') == 1 and '"HasSales"' not in json.dumps(f)
    assert date_columns(cfg)["week_label_column"] == "WeekLabel", "unset names keep the contract default"
    # the verbatim snippets beside the playbook are what the script writes with the CONFIGURED names
    # (config.yaml if present, else the contract defaults), so a renamed fork passes when its
    # config.yaml and its renamed snippets agree - and fails when they do not
    live = load_config()
    ccols, cmark = date_columns(live), filter_marker(live)
    want = json.loads((REPO_ROOT / "docs/reference/snippets/latest_day_filters.json").read_text())["filterConfig"]["filters"]
    assert date_filters.build("latest-day", ccols, cmark) == want, \
        "docs/reference/snippets/latest_day_filters.json differs from build('latest-day') with config.yaml names"
    want = json.loads((REPO_ROOT / "docs/reference/snippets/window_weeks_filters.json").read_text())["filterConfig"]["filters"]
    assert date_filters.build("window-weeks", ccols, cmark) == want, \
        "docs/reference/snippets/window_weeks_filters.json differs from build('window-weeks') with config.yaml names"


@test
def test_date_filters_rerun_replaces_only_its_own():
    root = Path(tempfile.mkdtemp(prefix="playbook-tests-"))
    try:
        live = load_config()
        ccols, cmark = date_columns(live), filter_marker(live)
        src = next(v for v in sorted((REPO_ROOT / "report-template/definition/pages").glob("*/visuals/*/visual.json"))
                   if f'"{cmark}LatestDayName"' in v.read_text())
        p = root / "visual.json"
        # the calc-item filter and the hand-written slicer filter (same marker) both survive, even 'none'
        p.write_text(json.dumps({"name": "v", "filterConfig": {"filters": [
            {"name": "calcItemVsLY", "type": "Categorical"}, {"name": "orgNotBlank", "type": "Advanced"},
            {"name": "orgLatestDayName", "type": "TopN"}]}}))
        assert date_filters.apply(p, "window-weeks", DATE_DEFAULTS, "org") == ["calcItemVsLY", "orgNotBlank", "orgWindowWeeks", "orgTradedDays"]
        assert date_filters.apply(p, "latest-day", DATE_DEFAULTS, "org") == ["calcItemVsLY", "orgNotBlank", "orgLatestDayName", "orgLatestWeek"]
        assert date_filters.apply(p, "none", DATE_DEFAULTS, "org") == ["calcItemVsLY", "orgNotBlank"]
        shutil.copy(src, p)   # a real template visual survives a round trip with the configured names
        before = p.read_text()
        v = json.loads(before)
        date_filters.apply(p, "latest-day", ccols, cmark)
        assert json.loads(p.read_text()) == v, "round trip changed the visual"
    finally:
        shutil.rmtree(root, ignore_errors=True)


# --- capture judge ------------------------------------------------------------
@test
def test_capture_judge():
    assert capture_pages.judge("Sales 1,234,567 vs LY 12.3%") == (10, 0)
    digits, bad = capture_pages.judge("Can't display the visual. See details 1 2 3")
    assert bad == 2 and digits == 3
    assert capture_pages.judge("Today")[1] == 0
    cfg = {"workspace": {"id": PLACEHOLDER_ID}, "capture": {"report_url": "<report url>"}}
    assert "workspace.id" in exits(capture_pages.resolve_url, cfg, PLACEHOLDER_ID)
    assert "No report given" in exits(capture_pages.resolve_url, cfg, None)
    assert capture_pages.resolve_url(cfg, "https://app.powerbi.com/x") == "https://app.powerbi.com/x"
    cfg["workspace"]["id"] = MODEL_ID
    assert PLACEHOLDER_ID in capture_pages.resolve_url(cfg, PLACEHOLDER_ID)


# --- config -------------------------------------------------------------------
@test
def test_config_example_has_every_key_the_scripts_read():
    cfg = load_example()
    required = [
        "workspace.name", "workspace.id", "semantic_model.name", "semantic_model.id",
        "deploy.item_prefix", "deploy.report_measure_prefix", "deploy.allowed_model_ids",
        "deploy.allow_refresh", "deploy.filter_marker",
        "api.powerbi_resource", "api.powerbi_base", "api.fabric_resource", "api.fabric_base",
        "date_filters.date_table", "date_filters.date_column", "date_filters.day_name_column",
        "date_filters.week_label_column", "date_filters.has_sales_column",
        "capture.app_base", "capture.report_url", "capture.browser_profile_dir", "capture.settle_seconds",
        "paths.schema_dir",
    ]
    for dotted in required:
        node = cfg
        for part in dotted.split("."):
            assert isinstance(node, dict) and part in node, f"config.example.yaml missing {dotted}"
            node = node[part]
        assert node is not None, f"config.example.yaml {dotted} is null"
    assert cfg["deploy"]["allow_refresh"] is False
    assert cfg["deploy"]["item_prefix"] == "ORG-" and cfg["deploy"]["report_measure_prefix"] == "RM "
    assert cfg["deploy"]["filter_marker"] == "org" and cfg["deploy"]["allowed_model_ids"] == []
    assert "mode" not in cfg["deploy"], "deploy.mode was a dead knob - no script reads it"
    assert cfg["workspace"]["id"] == PLACEHOLDER_ID and cfg["semantic_model"]["id"] == PLACEHOLDER_ID
    assert date_columns(cfg) == DATE_DEFAULTS and filter_marker(cfg) == "org"


# --- the template -------------------------------------------------------------
@test
def test_report_template_is_deployable_and_clean():
    cfg = load_example()
    name, parts = deploy_report.read_item_folder(REPO_ROOT / "report-template", cfg)
    assert name.startswith("ORG-"), name
    paths = {p["path"] for p in parts}
    assert {".platform", "definition.pbir", "definition/report.json", "definition/pages/pages.json"} <= paths
    p = subprocess.run([sys.executable, "scripts/check_report.py", "report-template", "--no-validator"],
                       cwd=REPO_ROOT, capture_output=True, text=True, timeout=120)
    assert p.returncode == 0, f"check_report.py report-template failed:\n{p.stdout}\n{p.stderr}"
    assert "FAIL" not in p.stdout


# --- each script's own selftest ----------------------------------------------
@test
def test_script_selftests_pass():
    for argv in (["scripts/date_filters.py", "--selftest"], ["scripts/refresh.py", "--selftest"]):
        p = subprocess.run([sys.executable, *argv], cwd=REPO_ROOT, capture_output=True, text=True, timeout=120)
        assert p.returncode == 0, f"{' '.join(argv)} failed (rc={p.returncode}):\n{p.stdout}\n{p.stderr}"


def main() -> None:
    pattern = sys.argv[1] if len(sys.argv) > 1 else ""
    selected = [t for t in TESTS if pattern in t.__name__]
    if not selected:
        sys.exit(f"No test matches '{pattern}'. Known: " + ", ".join(t.__name__ for t in TESTS))
    failures = []
    for t in selected:
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                t()
            print(f"PASS  {t.__name__}")
        except (Exception, SystemExit) as e:  # noqa: BLE001 - SystemExit is how the scripts refuse
            print(f"FAIL  {t.__name__}: {type(e).__name__}: {e}")
            if buf.getvalue():
                print("      --- captured output ---")
                print("      " + buf.getvalue().replace("\n", "\n      ").rstrip())
            failures.append(t.__name__)
    print(f"\n{len(selected) - len(failures)}/{len(selected)} passed")
    if failures:
        sys.exit("FAILED: " + ", ".join(failures))


if __name__ == "__main__":
    main()
