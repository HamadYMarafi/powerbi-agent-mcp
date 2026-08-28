"""Run a read-only DAX query against the configured semantic model (executeQueries).

Only EVALUATE / DEFINE queries are accepted; anything else is refused before any HTTP call.
executeQueries runs under your identity and burns shared capacity: batch your checks into one
query, and test each report measure ALONE the way a single card runs it:

    DEFINE MEASURE 'Measures'[RM X] = <body>
    EVALUATE ROW("v", [RM X])

Usage:
    python3 scripts/validate.py "EVALUATE ROW(\\"v\\", [Sales])"
    python3 scripts/validate.py --file query.dax
    python3 scripts/validate.py --file query.dax --json
    python3 scripts/validate.py --file query.dax --limit 0     # row count only
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # no __pycache__ in the tree: .pyc files embed the absolute source path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from auth import powerbi_headers  # noqa: E402
from common import check_response, load_config, request, require_ids  # noqa: E402

READ_ONLY = re.compile(r"^\s*(EVALUATE|DEFINE)\b", re.IGNORECASE)
COMMENTS = re.compile(r"/\*.*?\*/|//[^\n]*|--[^\n]*", re.DOTALL)


def assert_read_only(dax: str) -> None:
    """Exit unless the query (comments stripped) starts with EVALUATE or DEFINE."""
    if not READ_ONLY.match(COMMENTS.sub("", dax)):
        sys.exit("REFUSED: validate.py runs read-only DAX only - the query must start with "
                 "EVALUATE or DEFINE (comments before it are fine).")


def run_dax(cfg: dict, dax: str) -> list:
    assert_read_only(dax)
    _, model_id = require_ids(cfg)
    url = f"{cfg['api']['powerbi_base']}/datasets/{model_id}/executeQueries"
    body = {"queries": [{"query": dax}], "serializerSettings": {"includeNulls": True}}
    resp = request("POST", url, powerbi_headers(cfg), "executeQueries", json=body)
    if resp.status_code in (401, 403):
        sys.exit(
            f"executeQueries denied (HTTP {resp.status_code}). Two usual causes: you lack Build "
            "permission on the semantic model, or the tenant setting 'Dataset Execute Queries "
            "REST API' (admin portal > Integration settings) is off.\n"
            f"Body: {resp.text[:1000]}"
        )
    check_response(resp, "executeQueries")
    payload = resp.json()
    # Errors appear at three levels, including inside an HTTP 200 when a row or size limit
    # truncates the data (the response then holds PARTIAL rows). Check all three.
    result = (payload.get("results") or [{}])[0]
    table = (result.get("tables") or [{}])[0]
    for level, err in (("query", payload.get("error")), ("result", result.get("error")),
                       ("table", table.get("error"))):
        if err:
            sys.exit(f"DAX {level} error: {json.dumps(err, indent=2)}")
    return table.get("rows", [])


def print_rows(rows: list, limit: int) -> None:
    if not rows:
        print("(no rows)")
        return
    limit = max(limit, 0)
    if limit == 0:
        print(f"({len(rows)} rows)")
        return
    cols = list(rows[0].keys())
    widths = {c: max([len(c)] + [len(str(r.get(c, ""))) for r in rows[:limit]]) for c in cols}
    header = "  ".join(c.ljust(widths[c]) for c in cols)
    print(header)
    print("-" * len(header))
    for row in rows[:limit]:
        print("  ".join(str(row.get(c, "")).ljust(widths[c]) for c in cols))
    if len(rows) > limit:
        print(f"... {len(rows) - limit} more rows (use --limit to see more)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run read-only DAX against the target model.")
    parser.add_argument("dax", nargs="?", help="DAX query text (EVALUATE ... / DEFINE ...)")
    parser.add_argument("--file", help="Read the DAX query from a file")
    parser.add_argument("--limit", type=int, default=50, help="Max rows to print (0 = count only)")
    parser.add_argument("--json", action="store_true", help="Print the rows as JSON")
    args = parser.parse_args()

    if args.file:
        dax = Path(args.file).read_text()
    elif args.dax:
        dax = args.dax
    else:
        parser.error("provide a DAX query or --file")

    rows = run_dax(load_config(), dax)
    if args.json:
        print(json.dumps(rows, indent=2))
    else:
        print_rows(rows, args.limit)


if __name__ == "__main__":
    main()
