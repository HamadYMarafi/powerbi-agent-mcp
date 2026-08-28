# The model side: Microsoft's Power BI Modeling MCP

This repo's server (`powerbi-agent-mcp`) is the **report** side, plus read-only access
to the model: it exports schema, runs read-only DAX, and deploys report files. It has no
tool that edits a semantic model.

For **editing** a semantic model — measures, tables, relationships, calculation groups,
security roles, and more, 21 tool families in total — Microsoft ships its own MCP server:
`powerbi-modeling-mcp`. This page is what a real session against it looked like, with every
tenant-specific detail replaced by a placeholder.

## Two ways to run it

**Hosted**, over HTTP, no local process:

```json
{ "type": "http", "url": "https://api.fabric.microsoft.com/v1/mcp/powerbi/authoring" }
```

**Local, over stdio:**

```
npx -y @microsoft/powerbi-modeling-mcp@latest --start
```

Microsoft's own Claude Code plugin for this registers exactly that command — `--start` is
not optional (see below).

## Connecting

One call, once per session:

```json
{
  "name": "connection_operations",
  "arguments": {
    "request": {
      "operation": "ConnectFabric",
      "workspaceName": "<Workspace Name>",
      "semanticModelName": "<Model Name>"
    }
  }
}
```

TESTED: this connects, and every later tool call in the session reuses the connection
automatically.

Rules that caused real failures in testing:

- **Every argument is wrapped in a `request` object**, as shown above. Skip the wrapper and
  the call fails with `System.ArgumentException: The arguments dictionary is missing a
  value for the required parameter 'request'`. TESTED.
- **`--start` is required** when the process's stdin is a pipe, which it is under an MCP
  host. Without it, the program tries to print a welcome banner and wait for a keypress, and
  throws immediately: `System.InvalidOperationException: Cannot read keys when ... console
  input has been redirected`. TESTED.
- **Do not pass `connectionName`** to `ConnectFabric` — it is generated automatically, and a
  supplied one is rejected.
- **Workspace and model names are matched exactly, case-sensitive.** An all-lowercase
  variant of a correct name failed in testing with `Failed to resolve workspace ID for
  cloud connection.`
- **`workspaceName` and `semanticModelName` are easy to swap** — they are two different
  strings, and the error you get back does not say which one is wrong.
- **A live-connected report has no local model to attach to.** `ListLocalInstances`, and a
  `Connect` aimed at `localhost`, both fail with "No databases found on the server" against
  a report whose model lives in Fabric rather than on disk. Don't chase the local path for a
  report like that — go straight to `ConnectFabric`.
- **XMLA can lag behind the control plane after a deployment-pipeline run.** A model that a
  workspace listing already shows can still answer `Database '<Model Name>' not found` from
  `ConnectFabric` for a few minutes, because the XMLA endpoint has not caught up yet. Wait
  and retry — this is not a permissions problem.
- **The workspace needs at least the Contributor role** before `ConnectFabric` will resolve.

## Tool families

TESTED, on `npx -y @microsoft/powerbi-modeling-mcp@latest --start`: 21 tool families —
measure, column, table, relationship, calculation_group, dax_query, partition, perspective,
security_role, model, database, culture, calendar, trace, transaction, function,
named_expression, query_group, object_translation, user_hierarchy, connection.

## Auth on a headless Linux server

Current versions authenticate interactive-browser only — there is no service-principal or
pre-minted-token mode left in the latest release. (An older beta accepted an access token
via an environment variable, but the XMLA endpoint rejected an Azure-CLI-issued token for
that audience anyway, so it was a dead end even where it was accepted — UNTESTED against
any other token source.)

That leaves the interactive browser flow, which needs two things a headless server does not
have by default:

1. **A process that outlives a single shell call.** If the MCP process starts and dies
   within one command invocation, it dies before a human can possibly click anything — this
   reads as "auth is impossible headless" but is really a process-lifetime problem. Run it
   as a long-lived process (or a small local wrapper that keeps it alive) instead of
   invoking it fresh for every call.
2. **A way to see the sign-in URL.** The server hands the URL to whatever the system opens
   links with. Put a stub `xdg-open` earlier on `PATH` than any real one, and have it write
   the URL it was given to a file instead of trying to launch a desktop browser. Fire
   `ConnectFabric`, read the URL back out of that file, and open it in a real, already
   signed-in browser running on the **same machine** — the sign-in redirect targets
   `127.0.0.1`, so only a browser on that same machine can complete the round trip back to
   the server's listener. A human still clicks their account once; nothing here removes
   that step, it only makes the click possible on a box with no desktop.

TESTED: this combination connects, on a headless Linux box. UNTESTED: running it
unattended, on a schedule, or without a human present for the one click — `InteractiveBrowser`
mode in the current release still requires that click every session.

## The local, unattended alternative

The modeling MCP needs a human for that one click, every session. For anything that has to
run unattended — a script, a scheduled job — read the model and run DAX through
`powerbi-agent-mcp`'s own read-only tools (`get_model_schema`, `run_dax`) instead. They
need no interactive sign-in beyond the Azure CLI's own `az login`.

## The rule

With this MCP, the agent **can write to a model** — that is the entire point of it, and the
entire risk of it. Only ever point `ConnectFabric` at a model you own, or a copy of one.
Never the shared model that other reports depend on. Same guardrail as `rules/CLAUDE.md`,
rule 4 — this MCP is simply powerful enough to actually break it.
