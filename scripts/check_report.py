#!/usr/bin/env python3
"""Offline checks on a PBIR report folder: no tenant, seconds. PASS/FAIL per check, exit 1 on any FAIL.

Usage:
    python3 scripts/check_report.py "ORG-Daily Trading.Report"
    python3 scripts/check_report.py "ORG-Daily Trading.Report" --baseline "<approved original>.Report"
    python3 scripts/check_report.py report-template --no-validator [--allow-saved-selection]

The validator sees schema errors and bounds but not overlaps; nothing else sees the theme, the
pins or the slicers. These checks do:
  validator   npx @microsoft/powerbi-report-authoring-cli validate -> data.errorCount == 0
              (skipped with a note when npx is missing or the run fails)
  theme       with --baseline: StaticResources byte-identical, no #RRGGBB or fontFamily outside it
  state       report.json settings.isPersistentUserStateDisabled == true
  pages       pages.json pageOrder non-empty, unique, matches the page folders; activePageName in it
  names       visual name == its folder name, unique across the report
  bounds      every visual inside its page canvas
  overlaps    no data visual overlaps another (shapes, textboxes, slicers, buttons, images excluded)
  filters     no visual-level filter on a report (extension) measure; no window-days filter left
  measures    every extension measure a visual references exists in reportExtensions.json and
              carries the report-measure prefix; none references another; dataType never "String"
  pins        model-measure day visuals carry both latest-day pins (or a week window)
  ytd         cards on report-measure YTD measures carry no filters
  slicers     no saved selection (objects.general[].properties.filter) unless --allow-saved-selection
  mobile      page 1: mobile.json beside every data visual
"""

from __future__ import annotations

import argparse
import filecmp
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # no __pycache__ in the tree: .pyc files embed the absolute source path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import date_columns, filter_marker, load_config, measure_prefix  # noqa: E402

DECOR = {"shape", "textbox", "slicer", "actionButton", "image", "visualGroup"}   # not data visuals
PINNED = {"cardVisual", "card", "pivotTable", "tableEx", "barChart", "clusteredBarChart",
          "columnChart", "clusteredColumnChart"}
HEX = re.compile(r"#[0-9A-Fa-f]{6}")
FONT = re.compile(r"fontFamily[^,}]{0,60}")


class Checker:
    def __init__(self) -> None:
        self.fails: list[str] = []

    def ok(self, cond: bool, msg: str) -> None:
        print(("PASS " if cond else "FAIL ") + msg)
        if not cond:
            self.fails.append(msg)

    @staticmethod
    def note(msg: str) -> None:
        print("NOTE " + msg)


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def ext_measures(obj, out: set) -> set:
    """Collect every measure referenced with Schema 'extension' anywhere in a visual's JSON."""
    if isinstance(obj, dict):
        m = obj.get("Measure")
        if isinstance(m, dict) and ((m.get("Expression") or {}).get("SourceRef") or {}).get("Schema") == "extension":
            out.add(m.get("Property"))
        for v in obj.values():
            ext_measures(v, out)
    elif isinstance(obj, list):
        for v in obj:
            ext_measures(v, out)
    return out


def run_validator(folder: Path, c: Checker) -> None:
    npx = shutil.which("npx")
    if not npx:
        c.note("validator skipped: npx not found (install Node 20+; the CLI runs through npx)")
        return
    cmd = [npx, "-y", "@microsoft/powerbi-report-authoring-cli", "validate", str(folder), "--format", "json"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired:
        c.note("validator skipped: npx timed out after 600s")
        return
    try:
        data = json.loads(proc.stdout).get("data") or {}
    except json.JSONDecodeError:
        c.note(f"validator skipped: no JSON envelope (rc={proc.returncode}): "
               f"{(proc.stderr or proc.stdout)[:300].strip()}")
        return
    errors = data.get("errorCount")
    c.ok(errors == 0, f"validator errorCount 0 (errorCount={errors}, warningCount={data.get('warningCount')})")
    diagnostics = data.get("diagnostics") or {}
    if isinstance(diagnostics, dict):
        for code, d in diagnostics.items():
            if d.get("severity") == "error":
                for item in d.get("items", [])[:10]:
                    print(f"       {code}: {item.get('message')}")


def check_theme(folder: Path, base: Path, c: Checker) -> None:
    def static(d: Path) -> dict:
        root = d / "StaticResources"
        return {p.relative_to(d).as_posix(): p for p in root.rglob("*") if p.is_file()} if root.exists() else {}

    ours, theirs = static(folder), static(base)
    c.ok(set(ours) == set(theirs), "theme file set unchanged "
         f"(added: {sorted(set(ours) - set(theirs))}, removed: {sorted(set(theirs) - set(ours))})")
    for rel in sorted(set(ours) & set(theirs)):
        c.ok(filecmp.cmp(ours[rel], theirs[rel], shallow=False), f"theme byte-identical: {rel}")

    def scan(d: Path, rx: re.Pattern, upper: bool) -> set:
        found = set()
        for p in (d / "definition").rglob("*.json"):
            for m in rx.findall(p.read_text(errors="replace")):
                found.add(m.upper() if upper else m)
        return found

    new_hex = scan(folder, HEX, True) - scan(base, HEX, True)
    c.ok(not new_hex, f"no hex colour outside the baseline palette (new: {sorted(new_hex)})")
    new_font = scan(folder, FONT, False) - scan(base, FONT, False)
    c.ok(not new_font, f"no fontFamily outside the baseline set (new: {sorted(new_font)})")


def check_folder(folder: Path, cfg: dict, c: Checker, allow_saved: bool) -> None:
    rm, mark, cols = measure_prefix(cfg), filter_marker(cfg), date_columns(cfg)
    week_ref = f'"{cols["date_table"]}.{cols["week_label_column"]}"'
    date_ref = f'"{cols["date_table"]}.{cols["date_column"]}"'
    definition = folder / "definition"

    report = load(definition / "report.json")
    c.ok((report.get("settings") or {}).get("isPersistentUserStateDisabled") is True,
         "report.json settings.isPersistentUserStateDisabled = true")

    pages_json = load(definition / "pages" / "pages.json")
    order = pages_json.get("pageOrder") or []
    on_disk = sorted(p.name for p in (definition / "pages").iterdir() if p.is_dir())
    c.ok(bool(order) and len(order) == len(set(order)), f"pages.json pageOrder non-empty and unique ({len(order)} pages)")
    c.ok(set(order) == set(on_disk), "pageOrder matches the page folders "
         f"(listed but missing: {sorted(set(order) - set(on_disk))}; unlisted: {sorted(set(on_disk) - set(order))})")
    active = pages_json.get("activePageName")
    c.ok(not active or active in order, f"activePageName '{active}' is in pageOrder")

    names: set = set()
    refs: set = set()
    oob, overlaps, ext_filter, win_days, ytd_bad, slicer_saved, missing_pin, no_mobile = ([] for _ in range(8))
    for i, pg in enumerate(order):
        page_dir = definition / "pages" / pg
        meta = load(page_dir / "page.json") if (page_dir / "page.json").exists() else {}
        c.ok(meta.get("name") == pg, f"{pg}: page.json name equals the folder")
        width, height = meta.get("width", 1280), meta.get("height", 720)
        bodies = []
        for vj in sorted(page_dir.glob("visuals/*/visual.json")):
            v = load(vj)
            n, vis, pos = v.get("name"), v.get("visual") or {}, v.get("position") or {}
            vt = vis.get("visualType", "?")
            label = f"{pg}/{vj.parent.name}"
            c.ok(n == vj.parent.name and n not in names, f"{label}: name '{n}' equals the folder and is unique")
            names.add(n)
            grouped = "parentGroupName" in v          # positions are relative to the group
            if pos and not grouped:
                x, y, w, h = (pos.get(k, 0) for k in ("x", "y", "width", "height"))
                if not (0 <= x and x + w <= width and 0 <= y and y + h <= height):
                    oob.append(label)
                if vt not in DECOR and not v.get("isHidden"):
                    bodies.append((label, x, y, w, h))
            filters = (v.get("filterConfig") or {}).get("filters") or []
            fnames = {f.get("name") for f in filters}
            for f in filters:
                fm = (f.get("field") or {}).get("Measure") or {}
                if ((fm.get("Expression") or {}).get("SourceRef") or {}).get("Schema") == "extension":
                    ext_filter.append(f"{label}:{f.get('name')}")
                if f.get("name") == f"{mark}WindowDays":
                    win_days.append(label)
            used = ext_measures(v, set())
            refs |= used
            if any(str(u).startswith(f"{rm}YTD") for u in used) and filters:
                ytd_bad.append(label)
            q = json.dumps(vis.get("query") or {})
            if vt in PINNED and not used and week_ref not in q and date_ref not in q:
                pinned = {f"{mark}LatestDayName", f"{mark}LatestWeek"} <= fnames or f"{mark}WindowWeeks" in fnames
                if not pinned:
                    missing_pin.append(label)
            if vt == "slicer":
                general = (vis.get("objects") or {}).get("general") or []
                if any("filter" in (g.get("properties") or {}) for g in general):
                    slicer_saved.append(label)
            if i == 0 and vt not in ("shape", "slicer", "actionButton") and not (vj.parent / "mobile.json").exists():
                no_mobile.append(label)
        for a in range(len(bodies)):
            la, ax, ay, aw, ah = bodies[a]
            for lb, bx, by, bw, bh in bodies[a + 1:]:
                if ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah:
                    overlaps.append((la, lb))

    c.ok(not oob, f"every visual inside its page canvas ({oob})")
    c.ok(not overlaps, f"no data visual overlaps another ({overlaps})")
    c.ok(not ext_filter, f"no visual-level filter on a report (extension) measure ({ext_filter})")
    c.ok(not win_days, f"no {mark}WindowDays filter left ({win_days})")
    c.ok(not ytd_bad, f"{rm}YTD cards carry no filters ({ytd_bad})")
    c.ok(not missing_pin, f"model-measure day visuals carry both latest-day pins ({missing_pin})")
    c.ok(allow_saved or not slicer_saved, f"slicers have no saved selection ({slicer_saved})")
    c.ok(not no_mobile, f"page 1: mobile.json beside every data visual (missing: {no_mobile})")

    defined: dict = {}
    ext_path = definition / "reportExtensions.json"
    if ext_path.exists():
        for entity in load(ext_path).get("entities") or []:
            for m in entity.get("measures") or []:
                defined[m.get("name")] = m
    missing = sorted(r for r in refs if r not in defined)
    c.ok(not missing, f"every referenced report measure exists in reportExtensions.json (missing: {missing})")
    unprefixed = sorted(n for n in defined if not str(n).startswith(rm))
    c.ok(not unprefixed, f"every report measure is prefixed '{rm}' ({unprefixed})")
    xref = sorted(n for n, m in defined.items() if re.search(r"\[" + re.escape(rm), m.get("expression", "")))
    c.ok(not xref, f"no report measure references another report measure ({xref})")
    strings = sorted(n for n, m in defined.items() if m.get("dataType") == "String")
    c.ok(not strings, f"extension dataType never 'String' ({strings})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline PBIR checks on a report folder.")
    parser.add_argument("folder", help="the '<Name>.Report' folder")
    parser.add_argument("--baseline", help="the approved original folder: enables the theme checks")
    parser.add_argument("--allow-saved-selection", action="store_true",
                        help="do not fail on a slicer with a saved selection")
    parser.add_argument("--no-validator", action="store_true", help="skip the npx PBIR validator")
    args = parser.parse_args()

    folder = Path(args.folder)
    if not (folder / "definition").is_dir():
        sys.exit(f"{folder} has no definition/ folder - not a PBIR report item.")
    c = Checker()
    if not args.no_validator:
        run_validator(folder, c)
    if args.baseline:
        check_theme(folder, Path(args.baseline), c)
    else:
        c.note("no --baseline given: theme, colour and font checks skipped")
    check_folder(folder, load_config(), c, args.allow_saved_selection)
    print(f"\n{len(c.fails)} failures")
    sys.exit(1 if c.fails else 0)


if __name__ == "__main__":
    main()
