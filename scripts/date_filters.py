#!/usr/bin/env python3
"""Self-maintaining date filters for a PBIR visual (visual-level TopN pins). Never hand-write these.

Why these shapes: a time-intelligence calculation group keeps NON-calendar Date columns applied
when it shifts to last week / last year, but it REPLACES a 'Date'[Date] filter with the whole
shifted week. So "latest traded day" is expressed without any date literal as
    TopN 1 on 'Date'[DayName]    ordered by Max('Date'[Date]) desc, rows where HasSales = true
    TopN 1 on 'Date'[WeekLabel]  ordered by Max('Date'[Date]) desc, rows where HasSales = true
and a trend window as TopN N on 'Date'[WeekLabel] plus a Categorical HasSales = true filter.
Column names come from config.yaml (date_filters:); the defaults are the model contract's. The
filter-name marker comes from deploy.filter_marker (default 'org').

Usage:
    python3 scripts/date_filters.py <visual.json> latest-day|window-weeks|this-week|window-days|none [--weeks N]
    python3 scripts/date_filters.py --selftest

  latest-day    the two day pins (every latest-traded-day visual on a model measure)
  window-weeks  last N trading weeks (default 3), traded days only (trend charts, Date on the axis)
  this-week     the week of the latest traded day, traded days only (week-to-date-by-day matrix)
  window-days   TopN 14 on 'Date'[Date] - kept for history, BANNED: it breaks LY (see the playbook)
  none          strip the script's filters (report-measure YTD/WTD cards pin themselves)

The script owns exactly five filter names - <marker>LatestDayName, LatestWeek, WindowWeeks,
TradedDays, WindowDays - and replaces only those on re-run. Every other filter on the visual is
left alone, including the hand-written slicer filters that share the marker by convention
(orgNotBlank, orgRecentWeeks, orgRecentDays; see docs/reference/snippets/).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # no __pycache__ in the tree: .pyc files embed the absolute source path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import DATE_DEFAULTS, REPO_ROOT, date_columns, filter_marker, load_config  # noqa: E402

KINDS = ("latest-day", "window-weeks", "this-week", "window-days", "none")
OWNED = ("LatestDayName", "LatestWeek", "WindowWeeks", "TradedDays", "WindowDays")   # the names build() writes


def _col(prop: str, source: str = "d1") -> dict:
    return {"Column": {"Expression": {"SourceRef": {"Source": source}}, "Property": prop}}


def topn(name: str, display: str, prop: str, top: int, cols: dict) -> dict:
    """TopN on <date_table>[prop], ordered by Max(<date_column>) descending over rows where
    <has_sales_column> = true. The subquery is self-contained (its own Where) and OrderBy is an
    Aggregation, not a Measure - both are PBIR rules, both TESTED on a real build."""
    table = cols["date_table"]
    return {
        "name": name, "displayName": display,
        "field": {"Column": {"Expression": {"SourceRef": {"Entity": table}}, "Property": prop}},
        "type": "TopN",
        "filter": {"Version": 2,
                   "From": [{"Name": "subquery", "Expression": {"Subquery": {"Query": {
                       "Version": 2,
                       "From": [{"Name": "d1", "Entity": table, "Type": 0}],
                       "Select": [{**_col(prop), "Name": "field"}],
                       "Where": [{"Condition": {"Comparison": {"ComparisonKind": 0,
                                  "Left": _col(cols["has_sales_column"]),
                                  "Right": {"Literal": {"Value": "true"}}}}}],
                       "OrderBy": [{"Direction": 2, "Expression": {"Aggregation": {
                                    "Expression": _col(cols["date_column"]), "Function": 4}}}],
                       "Top": top}}}, "Type": 2},
                            {"Name": "d1", "Entity": table, "Type": 0}],
                   "Where": [{"Condition": {"In": {"Expressions": [_col(prop)],
                                                   "Table": {"SourceRef": {"Source": "subquery"}}}}}]},
        "howCreated": "User"}


def traded_days(name: str, cols: dict) -> dict:
    """Categorical <date_table>[<has_sales_column>] = true. Non-calendar, so LY/LW keep working."""
    table, hs = cols["date_table"], cols["has_sales_column"]
    return {"name": name, "displayName": "Traded days only",
            "field": {"Column": {"Expression": {"SourceRef": {"Entity": table}}, "Property": hs}},
            "type": "Categorical",
            "filter": {"Version": 2, "From": [{"Name": "d1", "Entity": table, "Type": 0}],
                       "Where": [{"Condition": {"In": {"Expressions": [_col(hs)],
                                                       "Values": [[{"Literal": {"Value": "true"}}]]}}}]},
            "howCreated": "User"}


def build(kind: str, cols: dict, marker: str, weeks: int = 3) -> list:
    """The filters for one kind, using the given column names and marker."""
    if kind == "latest-day":
        return [topn(f"{marker}LatestDayName", "Latest traded day", cols["day_name_column"], 1, cols),
                topn(f"{marker}LatestWeek", "Week of latest traded day", cols["week_label_column"], 1, cols)]
    if kind in ("window-weeks", "this-week"):
        n = 1 if kind == "this-week" else weeks
        label = "This trading week" if n == 1 else f"Last {n} trading weeks"
        return [topn(f"{marker}WindowWeeks", label, cols["week_label_column"], n, cols),
                traded_days(f"{marker}TradedDays", cols)]
    if kind == "window-days":
        print("WARNING: window-days is BANNED by the playbook - a 'Date'[Date] window makes the "
              "LY calc item return the whole week on every day. Use window-weeks.", file=sys.stderr)
        return [topn(f"{marker}WindowDays", "Last 14 traded days", cols["date_column"], 14, cols)]
    if kind == "none":
        return []
    sys.exit(f"Unknown kind '{kind}'. Choose one of: {', '.join(KINDS)}")


def apply(path: Path, kind: str, cols: dict, marker: str, weeks: int = 3) -> list:
    """Replace the script's own filters on the visual with the requested kind. Returns the names."""
    visual = json.loads(path.read_text())
    fc = visual.setdefault("filterConfig", {})
    owned = {marker + n for n in OWNED}
    kept = [f for f in fc.get("filters", []) if f.get("name") not in owned]
    fc["filters"] = kept + build(kind, cols, marker, weeks)
    if not fc["filters"] and len(fc) == 1:
        del visual["filterConfig"]
    path.write_text(json.dumps(visual, indent=2, ensure_ascii=False) + "\n")
    return [f["name"] for f in (visual.get("filterConfig") or {}).get("filters", [])]


def _query(f: dict) -> dict:
    return f["filter"]["From"][0]["Expression"]["Subquery"]["Query"]


def selftest() -> None:
    """Offline: shapes, Top values, column names from config, the has-sales condition, re-run
    replacement, and byte-equality with the verbatim snippets in docs/reference/snippets/."""
    cols, marker = dict(DATE_DEFAULTS), "org"
    day = build("latest-day", cols, marker)
    assert [f["name"] for f in day] == ["orgLatestDayName", "orgLatestWeek"]
    assert [_query(f)["Top"] for f in day] == [1, 1]
    assert [f["field"]["Column"]["Property"] for f in day] == ["DayName", "WeekLabel"]
    for f in day:
        assert f["type"] == "TopN" and f["howCreated"] == "User"
        q = _query(f)
        assert q["Where"][0]["Condition"]["Comparison"]["Left"]["Column"]["Property"] == "HasSales"
        assert q["Where"][0]["Condition"]["Comparison"]["Right"] == {"Literal": {"Value": "true"}}
        order = q["OrderBy"][0]
        assert order["Direction"] == 2 and order["Expression"]["Aggregation"]["Function"] == 4
        assert order["Expression"]["Aggregation"]["Expression"]["Column"]["Property"] == "Date"
        assert f["filter"]["From"][0]["Type"] == 2 and f["filter"]["From"][1]["Entity"] == "Date"
    assert json.dumps(day).count('"HasSales"') == 2

    weeks = build("window-weeks", cols, marker)
    assert [f["name"] for f in weeks] == ["orgWindowWeeks", "orgTradedDays"]
    assert _query(weeks[0])["Top"] == 3 and weeks[0]["field"]["Column"]["Property"] == "WeekLabel"
    assert weeks[1]["type"] == "Categorical"
    cond = weeks[1]["filter"]["Where"][0]["Condition"]["In"]
    assert cond["Expressions"][0]["Column"]["Property"] == "HasSales"
    assert cond["Values"] == [[{"Literal": {"Value": "true"}}]]
    assert _query(build("this-week", cols, marker)[0])["Top"] == 1
    assert _query(build("window-weeks", cols, marker, weeks=5)[0])["Top"] == 5
    assert build("none", cols, marker) == []

    # Column names and the marker come from config, not from the script.
    custom = {**cols, "date_table": "Calendar", "day_name_column": "Weekday",
              "week_label_column": "FiscalWeekName", "has_sales_column": "IsTraded", "date_column": "Day"}
    f = build("latest-day", custom, "yc")[0]
    assert f["name"] == "ycLatestDayName" and f["field"]["Column"]["Property"] == "Weekday"
    assert f["field"]["Column"]["Expression"]["SourceRef"]["Entity"] == "Calendar"
    assert '"HasSales"' not in json.dumps(f) and json.dumps(f).count('"IsTraded"') == 1
    assert _query(f)["OrderBy"][0]["Expression"]["Aggregation"]["Expression"]["Column"]["Property"] == "Day"

    # The verbatim snippets beside the playbook are exactly what the script writes with the
    # configured names (config.yaml if present, else the contract defaults) - so a renamed fork
    # passes only when config.yaml and the renamed snippets agree.
    cfg = load_config()
    ccols, cmark = date_columns(cfg), filter_marker(cfg)
    snippets = REPO_ROOT / "docs" / "snippets"
    for kind, name in (("latest-day", "latest_day_filters.json"), ("window-weeks", "window_weeks_filters.json")):
        if (snippets / name).exists():
            want = json.loads((snippets / name).read_text())["filterConfig"]["filters"]
            assert build(kind, ccols, cmark) == want, f"{name} differs from build('{kind}') with config.yaml names"

    # Re-running replaces only the five names the script writes; a slicer filter that shares the
    # marker (orgNotBlank) and a calc-item filter both survive, including on 'none'.
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "visual.json"
        p.write_text(json.dumps({"name": "v", "filterConfig": {"filters": [
            {"name": "keepMe", "type": "Categorical"}, {"name": "orgNotBlank", "type": "Advanced"},
            {"name": "orgWindowDays", "type": "TopN"}]}}))
        assert apply(p, "latest-day", cols, marker) == ["keepMe", "orgNotBlank", "orgLatestDayName", "orgLatestWeek"]
        assert apply(p, "window-weeks", cols, marker) == ["keepMe", "orgNotBlank", "orgWindowWeeks", "orgTradedDays"]
        assert apply(p, "none", cols, marker) == ["keepMe", "orgNotBlank"]
        assert p.read_text().endswith("}\n")
    print("date_filters selftest: PASS")


def main() -> None:
    parser = argparse.ArgumentParser(description="Write self-maintaining date filters on a PBIR visual.")
    parser.add_argument("visual", nargs="?", help="path to the visual.json")
    parser.add_argument("kind", nargs="?", choices=KINDS)
    parser.add_argument("--weeks", type=int, default=3, help="window-weeks: number of trading weeks (default 3)")
    parser.add_argument("--selftest", action="store_true", help="offline shape checks, then exit")
    args = parser.parse_args()
    if args.selftest:
        selftest()
        return
    if not args.visual or not args.kind:
        parser.error("usage: date_filters.py <visual.json> <kind>   (or --selftest)")
    cfg = load_config()
    names = apply(Path(args.visual), args.kind, date_columns(cfg), filter_marker(cfg), args.weeks)
    print(f"{args.visual}: filters now {names}")


if __name__ == "__main__":
    main()
