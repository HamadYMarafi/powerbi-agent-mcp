"""Deploy a local PBIR report item folder to the workspace (create or update by display name).

Guardrails, all enforced BEFORE any HTTP call:
  - the display name in .platform must start with deploy.item_prefix (default 'ORG-');
  - definition.pbir must bind byConnection to an existing model; byPath is refused
    (it would create a second semantic model in the workspace);
  - the bound semanticmodelid must equal config semantic_model.id or one of
    deploy.allowed_model_ids;
  - hidden files at any depth are never uploaded, except the root .platform;
  - an existing workspace item is only updated if ITS name carries the prefix, so an item
    you did not create can never be touched.

Usage:
    python3 scripts/deploy_report.py "ORG-Daily Trading.Report"
    python3 scripts/deploy_report.py "ORG-Daily Trading.Report" --bind   # first write the binding

--bind rewrites definition.pbir's byConnection.connectionString from config.yaml (workspace.name,
semantic_model.name, semantic_model.id), so the bound id can never disagree with the config. The
template ships with placeholders there; run --bind once (or edit the file by hand) before the
first deploy.
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # no __pycache__ in the tree: .pyc files embed the absolute source path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from auth import fabric_headers  # noqa: E402
from common import (REPO_ROOT, get_paginated, item_prefix, load_config,  # noqa: E402
                    poll_lro, request, require_ids)

MODEL_ID_RE = re.compile(r"semanticmodelid=([0-9a-fA-F-]{36})")


def connection_string(cfg: dict) -> str:
    """The byConnection string for config.yaml's workspace and model (needs the real ids)."""
    ws = str((cfg.get("workspace") or {}).get("name") or "")
    model = str((cfg.get("semantic_model") or {}).get("name") or "")
    if not ws or ws.startswith("<") or not model or model.startswith("<"):
        sys.exit("--bind needs workspace.name and semantic_model.name in config.yaml (still placeholders).")
    _, model_id = require_ids(cfg)
    host = re.sub(r"^https?://", "", cfg["api"]["powerbi_base"]).rstrip("/")   # api.powerbi.com/v1.0/myorg
    return (f'Data Source="powerbi://{host}/{ws}";initial catalog="{model}";'
            f"integrated security=ClaimsToken;semanticmodelid={model_id}")


def bind_pbir(folder: Path, cfg: dict) -> str:
    """Write definition.pbir's byConnection.connectionString from config.yaml; drops any byPath."""
    pbir_file = folder / "definition.pbir"
    pbir = json.loads(pbir_file.read_text())
    ref = pbir.setdefault("datasetReference", {})
    ref.pop("byPath", None)
    conn = connection_string(cfg)
    ref.setdefault("byConnection", {})["connectionString"] = conn
    pbir_file.write_text(json.dumps(pbir, indent=2, ensure_ascii=False) + "\n")
    return conn


def read_item_folder(folder: Path, cfg: dict) -> tuple[str, list]:
    """Validate the item folder against the guardrails and return (display_name, parts)."""
    prefix = item_prefix(cfg)
    if not folder.is_dir():
        sys.exit(f"Not a directory: {folder}")
    platform_file = folder / ".platform"
    pbir_file = folder / "definition.pbir"
    for required in (platform_file, pbir_file, folder / "definition"):
        if not required.exists():
            sys.exit(f"Missing required {required.name} in {folder} - "
                     "not a valid PBIR report item folder.")

    platform = json.loads(platform_file.read_text())
    display_name = platform.get("metadata", {}).get("displayName", "")
    if platform.get("metadata", {}).get("type") != "Report":
        sys.exit(f".platform metadata.type is not 'Report' in {folder}")
    if not display_name.startswith(prefix):
        sys.exit(f"GUARDRAIL: refusing to deploy '{display_name}' - every item we create "
                 f"must be prefixed '{prefix}' (deploy.item_prefix in config.yaml).")

    pbir = json.loads(pbir_file.read_text())
    dataset_ref = pbir.get("datasetReference", {})
    if "byPath" in dataset_ref or "byConnection" not in dataset_ref:
        sys.exit("GUARDRAIL: definition.pbir must bind byConnection to the existing semantic "
                 "model. byPath bindings are refused (they would create a new model in the "
                 "workspace).")
    conn = dataset_ref["byConnection"].get("connectionString", "")
    bound = MODEL_ID_RE.search(conn)
    if not bound:
        sys.exit("definition.pbir byConnection.connectionString has no "
                 "'semanticmodelid=<guid>' - required for REST deployment.")
    cfg_model_id = (cfg.get("semantic_model") or {}).get("id") or ""
    allowed = {cfg_model_id.lower()} | {
        str(m).lower() for m in ((cfg.get("deploy") or {}).get("allowed_model_ids") or [])}
    if bound.group(1).lower() not in allowed:
        sys.exit(f"GUARDRAIL: definition.pbir binds semanticmodelid={bound.group(1)} but "
                 f"config.yaml says the target model is {cfg_model_id or '(unset)'}. Fix "
                 "definition.pbir, re-run discover.py, or list the id under "
                 "deploy.allowed_model_ids if the binding is deliberate.")

    parts = []
    for path in sorted(p for p in folder.rglob("*") if p.is_file()):
        rel = path.relative_to(folder).as_posix()
        # Hidden files and folders at any depth stay local (.pbi/, .DS_Store, .backup-*),
        # except the root .platform, which is a real definition part.
        if rel != ".platform" and any(seg.startswith(".") for seg in path.relative_to(folder).parts):
            continue
        parts.append({
            "path": rel,
            "payload": base64.b64encode(path.read_bytes()).decode(),
            "payloadType": "InlineBase64",
        })
    return display_name, parts


def find_existing(cfg: dict, headers: dict, ws_id: str, display_name: str):
    reports = get_paginated(
        f"{cfg['api']['fabric_base']}/workspaces/{ws_id}/items?type=Report",
        headers, "List reports")
    for r in reports:
        if r.get("displayName", "").lower() == display_name.lower():
            return r
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or update a PBIR report item by name.")
    parser.add_argument("folder", help="Path to the '<Name>.Report' item folder")
    parser.add_argument("--bind", action="store_true",
                        help="first write definition.pbir's connection string from config.yaml")
    args = parser.parse_args()

    folder = Path(args.folder)
    if not folder.is_absolute() and not folder.exists():
        folder = REPO_ROOT / folder

    cfg = load_config()
    if args.bind:
        bind_pbir(folder, cfg)
        print("definition.pbir bound to config.yaml's workspace, model and semantic_model.id")
    display_name, parts = read_item_folder(folder, cfg)   # guardrails first, no HTTP yet
    ws_id, _ = require_ids(cfg)
    headers = fabric_headers(cfg)
    base = cfg["api"]["fabric_base"]

    existing = find_existing(cfg, headers, ws_id, display_name)
    if existing:
        if not existing.get("displayName", "").startswith(item_prefix(cfg)):
            sys.exit(f"GUARDRAIL: workspace item '{existing.get('displayName')}' was not "
                     "created by us - refusing to update it.")
        url = (f"{base}/workspaces/{ws_id}/items/{existing['id']}"
               f"/updateDefinition?updateMetadata=True")
        resp = request("POST", url, headers, "Update report definition",
                       json={"definition": {"parts": parts}})
        poll_lro(resp, headers, f"Update report '{display_name}'")
        print(f"Updated existing report '{display_name}' (id={existing['id']})")
    else:
        body = {"displayName": display_name, "type": "Report",
                "definition": {"parts": parts}}
        resp = request("POST", f"{base}/workspaces/{ws_id}/items", headers,
                       "Create report", json=body)
        result = poll_lro(resp, headers, f"Create report '{display_name}'")
        print(f"Created report '{display_name}' (id={(result or {}).get('id', 'unknown')})")


if __name__ == "__main__":
    main()
