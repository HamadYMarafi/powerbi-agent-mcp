# Connect your AI to your Power BI in 10 minutes

`powerbi-agent-mcp` gives an AI agent read and report access to your own Power BI or
Fabric tenant: schema, read-only DAX, report deploys, screenshots. No service principal and
no stored secret — it uses your own Azure CLI login.

## What you need

- Python 3.11+
- Azure CLI, signed in to the tenant that holds your workspace (`az login`)
- Node 20+ (for the PBIR validator, run through `npx`)
- Optional: Playwright, only if you want `capture_pages` —
  `pip install playwright && python -m playwright install chromium`

## Install

```bash
git clone https://github.com/HamadYMarafi/powerbi-agent-mcp.git
cd powerbi-agent-mcp

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

az login

cp config.example.yaml config.yaml
$EDITOR config.yaml            # set workspace.name, semantic_model.name, and your prefixes
python scripts/discover.py     # finds the two ids by name, writes them into config.yaml, exports the model to schema/

python -m powerbi_agent_mcp --check
```

`--check` loads the config, mints tokens from the Azure CLI for both the Power BI and the
Fabric resource, lists the configured workspace, and prints OK or exactly what failed. Get
this to OK before registering the server with anything.

## Register the server

**Claude Code** — run this once from the repo root; it stores absolute paths, so the server
starts from any folder you later open Claude in:

```bash
claude mcp add powerbi-agent --env POWERBI_MCP_CONFIG="$PWD/config.yaml" \
  -- "$PWD/.venv/bin/python" "$PWD/powerbi_agent_mcp/server.py"
```

**Claude Desktop, Cursor, or any other MCP host** — generic JSON, in that host's MCP config
file:

```json
{
  "mcpServers": {
    "powerbi-agent": {
      "command": "/absolute/path/to/repo/.venv/bin/python",
      "args": ["/absolute/path/to/repo/powerbi_agent_mcp/server.py"],
      "env": { "POWERBI_MCP_CONFIG": "/absolute/path/to/repo/config.yaml" }
    }
  }
}
```

**One-command route, Claude Code only:**

```
/plugin marketplace add HamadYMarafi/powerbi-agent-mcp
/plugin install powerbi-agent@powerbi-agent-mcp
```

This installs the skills and registers the server, but it does not install the Python
dependencies or write `config.yaml` — do the Install section above either way.

## Install the rules

- Copy `rules/CLAUDE.md` into your project as `CLAUDE.md` (or `AGENTS.md`, or append it to
  one you already have).
- Optionally copy `rules/settings.example.json` to `.claude/settings.json` (merge the
  `permissions` block if you already have a settings file).

## Install the skills

```bash
bash skills/install.sh
```

Microsoft's own Power BI report-authoring skills, separately:

```
/plugin marketplace add microsoft/skills-for-fabric
/plugin install powerbi-authoring@fabric-collection
```

## First conversation

With the server registered, try these three prompts in order:

1. `Show connection_status`
2. `list_workspaces`
3. `run_dax EVALUATE ROW("ok", 1)`

All three coming back clean means config, auth, and the read path all work.

## What the guardrails stop

| You ask for | What happens |
|---|---|
| "Refresh the model" | Refused — there is no refresh-trigger tool, by design. Read history with `refresh_history` instead. |
| "Update `<some other item>`" | Refused — `deploy_report` only creates or updates items whose display name starts with your configured prefix. |
| "Add a measure to the model" | Not possible through this server — it is read-only on the model. Use report measures instead, or Microsoft's modeling MCP against a model you own (`docs/modeling-mcp.md`). |
| "Run this DAX and change some data" | Refused — `run_dax` only accepts `EVALUATE`/`DEFINE`. |
| "Change the theme colours" | Not blocked by the tool itself, but by the rules once stakeholders have signed off — `validate_report` flags a theme that no longer matches the baseline. |

## Troubleshooting

| Symptom | Fix |
|---|---|
| `--check` fails with an expired or missing token | `az login` again. |
| `run_dax` returns 401/403 | Turn on the tenant setting **"Dataset Execute Queries REST API"**, and confirm your identity has Read and Build permission on the dataset. |
| `validate_report` fails to find the validator | Install Node 20+; the validator runs through `npx -y @microsoft/powerbi-report-authoring-cli`. |
| `capture_pages` hangs or errors on a server | It needs a real display, or `xvfb-run` on a headless machine. |
| "workspace not found" | Names must match the display name (spaces and punctuation included; case does not matter) — run `list_workspaces` and copy the name it returns, or pass the id. |
