# Security

This repo is an MCP server, the scripts it wraps, documentation and a report template. It is designed to hold **no
credentials at all**, and the CI job fails the build if one appears.

## No secrets in the repo

- Real ids live in `config.yaml`, which is **gitignored**. The committed file is
  `config.example.yaml`, and every id in it is the placeholder
  `00000000-0000-0000-0000-000000000000`.
- `tools/secret_scan.py` fails on a token-like string, an e-mail address, or any GUID that
  is not that placeholder. It runs in CI on every push and pull request. Run it yourself
  before you commit:

  ```
  python3 tools/secret_scan.py .
  ```

- Screenshots, accessibility dumps and validator envelopes carry real trading figures and
  real item ids. `.gitignore` keeps `*.png`, `captures/`, `shots/`, `scratch/`,
  `validate.json` and `.backup-*/` out of the repo. Do not force-add them.

## Tokens

- Every token is minted at runtime by the Azure CLI (`az account get-access-token`), kept
  in memory, and passed only in the `Authorization` header of the request that needs it.
- **Never print, log or persist a token** — not to the terminal, not to a file, not inside
  an exception message. Code that formats an error must not include the request headers.
- To prove auth works, print the expiry and nothing else:

  ```
  az account get-access-token --query expiresOn -o tsv
  ```

- The scripts use your own signed-in identity. Every deploy, query and refresh you start is
  attributed to you in the tenant's audit and monitoring views. That is a reason to keep
  verification lean, and the reason the refresh trigger is double-gated.

## Guardrails are safety, not a security boundary

The scripts refuse to touch items they did not create, refuse a `byPath` model binding, and
refuse to trigger a refresh unless two separate gates are set. Those stop accidents. They
do not stop a determined caller, and they are not a substitute for permissions: give the
account you sign in with only the workspace access it needs.

## If a secret is committed

1. Revoke first, rewrite history second. Sign the identity out (`az logout`), and ask your
   tenant admin to revoke the sign-in session or rotate the credential.
2. Then remove it from history and force-push, and re-run `tools/secret_scan.py`.
3. Treat any workspace, model or report id that leaked as information about your tenant —
   rotate nothing, but expect it to be public from then on.

## Reporting a problem

Report privately. Use the repository's **Security** tab -> *Report a vulnerability*, which
opens a private advisory that only the maintainer can see.

Do not open a public issue for anything that contains a token, a tenant id, a workspace or
item id, or company data. Public issues are the right place for a bug in a script that
reproduces with placeholder ids.
