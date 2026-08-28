"""Mint Azure AD access tokens at runtime through the Azure CLI.

HARD RULE: tokens are never printed, logged or written to disk. They live in memory and go
only into request headers. Error text never includes process stdout (it may hold a token).

As a module:
    from auth import powerbi_headers, fabric_headers

As a script (prints expiry times only, never a token):
    python3 scripts/auth.py --check
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess

POWERBI_RESOURCE = "https://analysis.windows.net/powerbi/api"
FABRIC_RESOURCE = "https://api.fabric.microsoft.com"


class AuthError(RuntimeError):
    """Raised when a token cannot be minted. The message never contains a token."""


def _token_payload(resource: str) -> dict:
    az = shutil.which("az")
    if not az:
        raise AuthError("Azure CLI ('az') not found on PATH. Install it, then run: az login")
    proc = subprocess.run(
        [az, "account", "get-access-token", "--resource", resource, "-o", "json"],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        # stderr is safe to show; stdout could contain the token and is never included.
        raise AuthError(
            f"az account get-access-token failed for {resource} (exit {proc.returncode}). "
            f"If the session expired run: az login\n--- az stderr ---\n{proc.stderr.strip()}"
        )
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise AuthError(f"Could not parse the az token output for {resource}: {exc}") from exc


def get_token(resource: str) -> str:
    """Return a bearer token for the resource. Never log the result."""
    return _token_payload(resource)["accessToken"]


def token_expiry(resource: str) -> str:
    """Return the token's expiresOn timestamp - the only safe thing to print."""
    return _token_payload(resource)["expiresOn"]


def _resource(cfg: dict | None, key: str, default: str) -> str:
    return ((cfg or {}).get("api") or {}).get(key) or default


def powerbi_headers(cfg: dict | None = None) -> dict:
    """Headers for the Power BI REST API (executeQueries, refresh history)."""
    token = get_token(_resource(cfg, "powerbi_resource", POWERBI_RESOURCE))
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def fabric_headers(cfg: dict | None = None) -> dict:
    """Headers for the Fabric REST API (items, definitions, operations)."""
    token = get_token(_resource(cfg, "fabric_resource", FABRIC_RESOURCE))
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prove Azure CLI auth works. Prints token expiry only, never a token.")
    parser.add_argument("--check", action="store_true",
                        help="Mint the Power BI and Fabric tokens and print their expiresOn.")
    args = parser.parse_args()
    if not args.check:
        parser.print_help()
        return
    print(f"Power BI token expires: {token_expiry(POWERBI_RESOURCE)}")
    print(f"Fabric   token expires: {token_expiry(FABRIC_RESOURCE)}")


if __name__ == "__main__":
    main()
