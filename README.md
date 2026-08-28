# powerbi-agent-mcp

Connect your AI agent to **your own Power BI / Microsoft Fabric tenant** — and give it the rules and
skills it needs to build dashboard pages that an executive can trust.

Three parts, one repo:

| Part | What you get |
|---|---|
| **The MCP server** — `powerbi_agent_mcp/` | Runs on your machine, signs in as **you** (Azure CLI), stores no secret. 12 tools: list workspaces and items, read the model schema, run read-only DAX, download / validate / deploy PBIR report definitions, write self-maintaining date filters, screenshot every page, read refresh history. The guardrails are **in the code**: it refuses to touch items you did not create, refuses DAX that is not read-only, and has no tool that triggers a refresh. |
| **The rules** — `rules/CLAUDE.md` | The universal rules an AI agent must follow on a Power BI tenant. Drop it into your project as `CLAUDE.md` (or `AGENTS.md`). Also served by the `guardrails` tool so the agent can read it mid-session. |
| **The skills** — `skills/` | Three skills the agent uses: **build** a page (spec → build → validate → deploy → look), **review** a page through executive eyes, **verify** after every deploy (the see-it doctrine). Plus the install of Microsoft's own `powerbi-authoring` skills for PBIR and model specifics. |

It comes from a real build on a shared retail tenant — an executive daily-trading report rebuilt and
verified by AI agents — with everything company-specific stripped out. The company here is `YourCo`,
items you create are prefixed `ORG-`, report measures `RM `, and every id is
`00000000-0000-0000-0000-000000000000`.

## Why the guardrails exist

Each one was paid for on a shared tenant:

- **Never touch an item you did not create.** Other people's reports bind to the same model. Work on a clone. → `deploy_report` refuses any item name without your prefix.
- **Never trigger a refresh on a shared model.** It lands in the tenant's history under *your* name. → there is no refresh tool; `refresh_history` is read-only.
- **The shared model is read-only.** New DAX goes into the report (`RM ` measures), never the model. → `run_dax` accepts `EVALUATE` / `DEFINE` only; model edits need a copy you own (see [docs/modeling-mcp.md](docs/modeling-mcp.md)).
- **A page is not done until you have seen it rendered with data**, in every state a user can put it in. Validators cannot see a page. → `capture_pages` + the `powerbi-dashboard-verify` skill.
- **Capacity is shared.** One render pass per deploy, one batched DAX query, offline checks first.

## Install in 10 minutes

You need Python 3.11+, the Azure CLI signed in to your tenant, Node 20+ (for Microsoft's PBIR
validator), and — only for screenshots — Playwright. Full detail: [docs/SETUP.md](docs/SETUP.md).

```bash
git clone https://github.com/HamadYMarafi/powerbi-agent-mcp.git
cd powerbi-agent-mcp
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
az login                                               # your own identity; no service principal

cp config.example.yaml config.yaml                     # gitignored
$EDITOR config.yaml                                    # workspace.name, semantic_model.name, deploy.item_prefix
python scripts/discover.py                             # fills the ids, exports the model definition to schema/
python -m powerbi_agent_mcp --check                # loads config, mints tokens, finds your workspace → OK
```

Register the server with your AI host. Claude Code:

```bash
claude mcp add powerbi-agent --env POWERBI_MCP_CONFIG="$PWD/config.yaml" \
  -- "$PWD/.venv/bin/python" "$PWD/powerbi_agent_mcp/server.py"
```

Any other MCP host (Claude Desktop, Cursor, …) takes the same thing as JSON:

```json
{ "mcpServers": { "powerbi-agent": {
    "command": "/absolute/path/to/repo/.venv/bin/python",
    "args": ["/absolute/path/to/repo/powerbi_agent_mcp/server.py"],
    "env": { "POWERBI_MCP_CONFIG": "/absolute/path/to/repo/config.yaml" } } } }
```

Then the rules and the skills:

```bash
cp rules/CLAUDE.md /path/to/your/project/CLAUDE.md     # or append to an existing one
bash skills/install.sh                                 # copies the three skills into ~/.claude/skills
```

In Claude Code, add Microsoft's skills for PBIR and semantic-model specifics:
`/plugin marketplace add microsoft/skills-for-fabric` then `/plugin install powerbi-authoring@fabric-collection`.

One-command alternative for Claude Code (this repo is also a plugin marketplace — it registers the
server and installs the three skills; you still need the `pip install`, `az login` and `config.yaml`
above): `/plugin marketplace add HamadYMarafi/powerbi-agent-mcp` then
`/plugin install powerbi-agent@powerbi-agent-mcp`.

First conversation: *"Call connection_status, then list_workspaces, then run_dax with
`EVALUATE ROW("ok", 1)`."* Three tools, no change to the tenant.

## The tools

| Tool | What it does | Touches the tenant? |
|---|---|---|
| `connection_status()` | Config file, workspace, model, prefixes, token expiry for both APIs. Call first. | no (token check only) |
| `list_workspaces()` | Workspaces the signed-in identity can see. | read |
| `list_items(workspace, item_type)` | Items in a workspace: `Report`, `SemanticModel`, … | read |
| `get_model_schema(workspace, model)` | Exports the model definition (TMDL) to `schema/` and summarises tables, columns, measures. Read this before writing DAX. | read |
| `run_dax(query, workspace, model, max_rows)` | Read-only DAX via `executeQueries`. `EVALUATE` / `DEFINE` only. Batch what you need into one query. | read |
| `get_report_definition(report, out_dir, workspace)` | Downloads a report's PBIR folder (`report.json`, `pages/`, `visuals/`). Reading any report is safe. | read |
| `validate_report(folder, baseline)` | Microsoft's PBIR validator CLI + offline checks: overlaps, canvas bounds, unique names, date pins present, banned filter kinds, theme byte-identical to `baseline`. | no |
| `set_date_filters(visual_json, mode, weeks)` | Writes the self-maintaining date filters on a visual: `latest-day`, `window-weeks`, `this-week`, `none`. Never hand-write these. | no |
| `deploy_report(folder, bind)` | Creates or updates the report by display name. Refuses names without your prefix and models not allowed in config. | **write — your items only** |
| `capture_pages(target, out_dir, headless, settle_seconds)` | Opens the report, visits every page, saves a PNG and an accessibility-text dump per page. | read (browser) |
| `refresh_history(workspace, model, top)` | The model's last refreshes and their errors. | read |
| `guardrails()` | The rules text. Also the MCP resource `guardrails://rules`. | no |

## What it will never do

- Update or delete an item whose name does not start with your prefix (`deploy.item_prefix`).
- Bind a report to a model that is not `semantic_model.id` or listed in `deploy.allowed_model_ids`.
- Run DAX that is not `EVALUATE` / `DEFINE`.
- Trigger, retry or schedule a refresh — no such tool exists.
- Store a token. Tokens are minted in memory by the Azure CLI per request; `config.yaml` holds names
  and ids only and is gitignored; `tools/secret_scan.py` fails CI on a token, an e-mail address or a
  non-placeholder GUID.

## The rules the agent follows

`rules/CLAUDE.md` in one breath: never touch what you did not create · prefix everything · never refresh
a shared model · model read-only, DAX in the report · theme locked once stakeholders have seen it ·
validate after every batch and the CLI is the source of truth — never guess PBIR JSON · every number
carries its basis on the canvas · a page is not done until seen rendered in every state · one page per
agent, the main thread owns the shared files · deterministic checks before judgement · label every claim
TESTED or UNTESTED · never commit ids, tokens or screenshots. `rules/settings.example.json` is a matching
Claude Code permission allow-list.

## The skills

| Skill | When the agent loads it |
|---|---|
| `powerbi-dashboard-build` | "build / add / rebuild a page", "deploy this report", "clone my report and fix it" — spec first, one builder per page, date pins by tool, validate after every batch, deploy, capture, look. |
| `powerbi-dashboard-review` | "review this", "would a CEO understand it" — five lenses (CEO, trading director, finance director, data auditor, designer) over the same screenshots, then a skeptic pass; changes nothing. |
| `powerbi-dashboard-verify` | after any deploy — validator, live-vs-local diff, every page in every state, digits against the tie-out, error-marker grep, capacity etiquette. |

For PBIR mechanics (visual JSON, formatting objects, filters, the validator, PBIP workflows) and
semantic-model authoring, the skills defer to Microsoft's `powerbi-authoring` bundle:
`powerbi-report-planning`, `powerbi-report-design`, `powerbi-report-authoring`,
`powerbi-report-management`, `semantic-model-authoring`.

## The model side

This server reads models and writes reports. To **edit** a semantic model (measures, tables,
relationships, calculation groups, roles), Microsoft ships its own MCP — the Power BI Modeling MCP —
hosted or local. [docs/modeling-mcp.md](docs/modeling-mcp.md) has the connection recipe, the argument
shape that trips people up, and the headless-server sign-in trick. The rule stands: point it only at a
model you own or a copy.

## Repo map

```
powerbi_agent_mcp/server.py   the MCP server (stdio); --check for a no-AI smoke test
scripts/                          the toolkit the server wraps; every script also runs on its own
rules/CLAUDE.md                   the universal rules — drop into your project
rules/settings.example.json       Claude Code permission allow-list for the tools
skills/                           powerbi-dashboard-build / -review / -verify + install.sh
docs/SETUP.md                     connect your AI to your Power BI, step by step
docs/modeling-mcp.md              Microsoft's Power BI Modeling MCP: recipe and rules
docs/MODEL_CONTRACT.md            what your semantic model must provide (the one thing to adapt)
docs/reference/                   the playbook the rules were distilled from: recipe, 51 traps, checklists, spec template, snippets, DAX
report-template/                  a deployable one-page PBIR report (the "Today" page) on Microsoft's stock theme
config.example.yaml               every id and rule the server reads; copy to config.yaml (gitignored)
tests/                            offline: guardrails, server surface and refusals
.claude-plugin/marketplace.json   makes this repo installable as a Claude Code plugin
.github/workflows/validate.yml    CI: tests, PBIR validation of the template, secret scan
```

## Credits

- **Microsoft `skills-for-fabric`** (github.com/microsoft/skills-for-fabric, MIT) — the Power BI
  authoring skills this repo's skills defer to, and the plugin-marketplace layout this repo copies.
- **`@microsoft/powerbi-report-authoring-cli`** — the PBIR validator and catalogue: look a property up,
  never guess it.
- **`@microsoft/powerbi-modeling-mcp`** — the model-side MCP.
- **Model Context Protocol** Python SDK (`mcp`).
- `report-template/StaticResources/SharedResources/BaseThemes/CY26SU07.json` is Microsoft's own base
  theme copied unmodified out of a report definition; it is Microsoft's, not this repo's, and the MIT
  licence does not cover it. Delete it and the service supplies the same theme.

## License

MIT — see `LICENSE`. Author: Hamad Marafi.
