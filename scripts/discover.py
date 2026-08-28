"""Find the workspace and semantic-model ids by name, export the model definition (TMDL) into
the schema folder, and write the ids into config.yaml (only the two id: lines change; your
comments stay).

Read-only against the tenant: list workspaces, list items, getDefinition. Run it first, and
again whenever the model changes shape - the decoded TMDL under schema/ is what you read before
writing any DAX or visual binding.

Usage:
    python3 scripts/discover.py
"""

from __future__ import annotations

import base64
import re
import shutil
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # no __pycache__ in the tree: .pyc files embed the absolute source path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from auth import fabric_headers, powerbi_headers  # noqa: E402
from common import (REPO_ROOT, get_paginated, load_config, poll_lro,  # noqa: E402
                    request, save_ids)


def _configured_name(cfg: dict, section: str) -> str:
    name = (cfg.get(section) or {}).get("name") or ""
    if not name or name.startswith("<"):
        sys.exit(f"Set {section}.name in config.yaml first (it is still the placeholder).")
    return name


def find_workspace(cfg: dict, headers: dict) -> dict:
    name = _configured_name(cfg, "workspace")
    workspaces = get_paginated(f"{cfg['api']['fabric_base']}/workspaces", headers, "List workspaces")
    matches = [w for w in workspaces if w.get("displayName", "").lower() == name.lower()]
    if not matches:
        available = ", ".join(sorted(w.get("displayName", "?") for w in workspaces)) or "none"
        sys.exit(f"Workspace '{name}' not found. You have access to: {available}")
    return matches[0]


def find_model(cfg: dict, headers: dict, workspace_id: str) -> dict:
    name = _configured_name(cfg, "semantic_model")
    models = get_paginated(
        f"{cfg['api']['fabric_base']}/workspaces/{workspace_id}/items?type=SemanticModel",
        headers, "List semantic models")
    matches = [m for m in models if m.get("displayName", "").lower() == name.lower()]
    if not matches:
        available = ", ".join(sorted(m.get("displayName", "?") for m in models)) or "none"
        sys.exit(f"Semantic model '{name}' not found in the workspace. Models there: {available}")
    return matches[0]


def export_definition(cfg: dict, headers: dict, workspace_id: str, model_id: str) -> list:
    url = (f"{cfg['api']['fabric_base']}/workspaces/{workspace_id}"
           f"/items/{model_id}/getDefinition?format=TMDL")
    resp = request("POST", url, headers, "Get model definition")
    result = poll_lro(resp, headers, "Get model definition (TMDL)", result_required=True)
    parts = (result or {}).get("definition", {}).get("parts", [])
    if not parts:
        sys.exit("getDefinition succeeded but the response holds no definition.parts. "
                 f"Raw keys: {sorted((result or {}).keys())}")
    return parts


def write_schema(cfg: dict, parts: list) -> Path:
    """Decode every definition part under paths.schema_dir. Cleared first, so a renamed or
    deleted table cannot leave a stale .tmdl behind; refuses any part path that escapes it."""
    schema_dir = REPO_ROOT / (cfg.get("paths") or {}).get("schema_dir", "schema")
    shutil.rmtree(schema_dir, ignore_errors=True)
    schema_dir.mkdir(parents=True)
    for part in parts:
        rel = part["path"].replace("\\", "/")
        if rel.startswith("/") or ".." in rel.split("/"):
            sys.exit(f"Refusing suspicious part path: {rel}")
        if part.get("payloadType") != "InlineBase64":
            sys.exit(f"Unexpected payloadType {part.get('payloadType')} for {rel}")
        target = schema_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(base64.b64decode(part["payload"]))
    return schema_dir


TABLE_RE = re.compile(r"^table\s+(?:'([^']+)'|(\S+))", re.MULTILINE)
MEASURE_RE = re.compile(r"^\s+measure\s+(?:'([^']+)'|([^\s=]+))\s*=", re.MULTILINE)
COLUMN_RE = re.compile(r"^\s+column\s+(?:'([^']+)'|(\S+))", re.MULTILINE)


def summarise_schema(schema_dir: Path) -> dict:
    """Light TMDL scan: table -> {measures, columns}. Enough to check the model contract."""
    summary: dict = {}
    for tmdl in sorted(schema_dir.rglob("*.tmdl")):
        text = tmdl.read_text(errors="replace")
        tables = TABLE_RE.findall(text)
        if not tables:
            continue
        table_name = next(g for g in tables[0] if g)
        measures = [next(g for g in m if g) for m in MEASURE_RE.findall(text)]
        columns = [next(g for g in c if g) for c in COLUMN_RE.findall(text)]
        summary[table_name] = {"measures": measures, "columns": columns}
    return summary


def verify_powerbi_ids(cfg: dict, workspace_id: str, model_id: str) -> None:
    """The Fabric ids double as Power BI ids (workspace = group, semantic model = dataset).
    Confirm that, so executeQueries and refresh history work later."""
    url = f"{cfg['api']['powerbi_base']}/groups/{workspace_id}/datasets/{model_id}"
    resp = request("GET", url, powerbi_headers(cfg), "Verify ids on the Power BI API")
    if resp.status_code != 200:
        print(f"WARNING: the Power BI API did not confirm the ids (HTTP {resp.status_code}) - "
              f"executeQueries / refresh history may fail. Body: {resp.text[:300]}")
        return
    print("Power BI API confirms the ids (dataset reachable as "
          f"groups/{workspace_id}/datasets/{model_id}).")


def main() -> None:
    cfg = load_config()
    headers = fabric_headers(cfg)

    workspace = find_workspace(cfg, headers)
    print(f"Workspace: {workspace['displayName']}  id={workspace['id']}")

    model = find_model(cfg, headers, workspace["id"])
    print(f"Semantic model: {model['displayName']}  id={model['id']}")

    verify_powerbi_ids(cfg, workspace["id"], model["id"])

    parts = export_definition(cfg, headers, workspace["id"], model["id"])
    schema_dir = write_schema(cfg, parts)
    print(f"Decoded {len(parts)} definition parts into {schema_dir.relative_to(REPO_ROOT)}/")

    save_ids(workspace["id"], model["id"])
    print("config.yaml updated with the workspace and model ids (only the two id: lines changed).")

    summary = summarise_schema(schema_dir)
    n_measures = sum(len(t["measures"]) for t in summary.values())
    n_columns = sum(len(t["columns"]) for t in summary.values())
    print(f"\nModel contents: {len(summary)} tables, {n_columns} columns, {n_measures} measures")
    for table, info in sorted(summary.items()):
        print(f"\n  table {table}  ({len(info['columns'])} columns)")
        for m in info["measures"]:
            print(f"    measure {m}")
    print("\nNow check every row of docs/MODEL_CONTRACT.md against this list.")


if __name__ == "__main__":
    main()
