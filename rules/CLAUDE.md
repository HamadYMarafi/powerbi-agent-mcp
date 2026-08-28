# Power BI / Fabric agent rules

Universal rules for an AI coding agent working on Power BI or Microsoft Fabric reports
through `powerbi-agent-mcp`. Drop this file into a project as `CLAUDE.md` (or
`AGENTS.md`, or append it to one you already have) and the agent picks it up automatically.

These rules exist because a shared Fabric tenant is a shared resource: other people's
reports bind to the same model, other people read the refresh history, and render capacity
is finite. None of this is about writing prettier DAX. It is about not being the session
that breaks someone else's morning report.

## A. Hard guardrails

1. **Never touch an item you did not create. Work on a clone.**
   Why: other reports in the workspace may bind to the same model — editing an item you
   did not make can break someone else's report without warning.

2. **Prefix everything you create** (default `ORG-` for items, `RM ` for report measures —
   both configurable in `config.yaml`).
   Why: it turns "did we make this?" into a string match instead of a memory test, and lets
   `deploy_report` refuse anything unprefixed before it makes a single HTTP call.

3. **Never trigger, retry, or schedule a refresh on a shared model. Read history only**
   (`refresh_history`).
   Why: a refresh is attributed to whoever started it — it lands in the tenant's history
   under the human's name, not the agent's. There is deliberately no refresh-trigger tool.

4. **Treat the shared semantic model as read-only.** New DAX goes in the report, as report
   measures — never in the model. A model defect becomes a written request to the model
   owner, not a live edit.
   Why: every report in the tenant depends on that one model — a "small fix" is everyone's
   outage.

5. **Lock the theme once stakeholders have seen the report.** No new colour, font, or size
   after sign-off.
   Why: stakeholders reviewed a specific look. A "consistency" tweak mid-review spends trust
   you cannot buy back with a nicer palette.

6. **Verify capacity-lean:** one render pass per deploy, one batched DAX query, offline
   checks before anything live, and never run DAX or captures from more than one agent at
   once.
   Why: shared Fabric capacity throttles under load — and takes down other people's reports
   with it, not just yours.

7. **Validate after every batch of edits, and treat the validator CLI as the source of
   truth for PBIR shape.** Never guess a property name or JSON structure.
   Why: PBIR schema is exact. A guessed property either fails validation loudly or does
   nothing silently — the second one is worse.

8. **Put the basis of every number on the canvas:** which day, which comparator, tax in or
   out, which channels.
   Why: a figure that ties to the model to the penny can still tell a false story if its
   basis is invisible — a reader has ten seconds, not ten minutes, to catch that.

9. **A page is not done until you have seen it rendered, with data, in every state a user
   can reach it** — default, each filter or slicer pick, the reset, every page.
   Why: a visual's query is assembled at render time from its own filters, the page and
   report filters, slicer state, and any calculation group, together. Nothing but the
   rendered page shows the product of all of them at once.

10. **One page per agent. Only the main thread touches shared files** — `report.json`,
    `pages.json`, `reportExtensions.json`, the theme, the deploy step, and the captures.
    Why: two agents writing the same file at the same time is how a page gets silently
    overwritten.

11. **Prefer deterministic checks over judgement calls.** Run the validator, the offline
    structural checks, and the guardrail tests before any subjective review.
    Why: a script makes the same call every time; an agent reading a screenshot might not
    notice the same problem twice.

12. **Label every claim of success or failure TESTED or UNTESTED.** TESTED means you ran it
    and can point at the evidence; UNTESTED means it is plausible but unverified — say what
    would prove it.
    Why: "should work" and "works" read identically in a chat transcript. On a shared
    tenant they are not the same claim.

13. **Never commit `config.yaml`, ids, tokens, or screenshots.**
    Why: `config.yaml` carries your tenant's real workspace and model names; screenshots
    carry real figures. Both are exactly what a shared or public repo must not leak.

## B. Which tool, in which order

Build order for a normal session — do not skip ahead:

| Step | Tool | Why now |
|---|---|---|
| 1 | `guardrails()` | Read the rules back from the server itself — current, not remembered. |
| 2 | `connection_status()` | Confirm config loaded, both tokens valid, and which workspace/model is configured. |
| 3 | `get_model_schema()` | Real table, column, and measure names before writing any DAX. Never guess a name. |
| 4 | `run_dax()` — the tie-out | One batched, read-only query for the numbers you will need to match on screen later. |
| 5 | `get_report_definition()` on a report to clone, or start from the template | Always a clone. Never the original. |
| 6 | `set_date_filters()` | Self-maintaining date logic on each visual. Never hand-write these filters. |
| 7 | `validate_report()` | PBIR CLI plus offline structural checks. Must be clean before deploy. |
| 8 | `deploy_report()` | Creates or updates by prefixed display name only; refuses anything that breaks a guardrail. |
| 9 | `capture_pages()` | One screenshot and one accessibility-text file per page, in every state. |
| 10 | Look | No tool for this — read every image against your tie-out numbers; grep every text file for `wrong`, `See details`, `(Blank)`. |
| 11 | Fix | Edit locally, back to step 6 or 7, redeploy. Any deploy re-opens the loop. |

## C. Which skill, when

- **`powerbi-dashboard-build`** — building or extending report pages.
- **`powerbi-dashboard-review`** — running an executive/stakeholder review pass over a
  finished build.
- **`powerbi-dashboard-verify`** — after every single deploy, before calling a round done.
- **Microsoft's `skills-for-fabric` collection** — `powerbi-report-authoring`,
  `powerbi-report-design`, `powerbi-report-planning`, `powerbi-report-management`,
  `semantic-model-authoring` — for exact PBIR mechanics and model-authoring specifics. Its
  own rule is the right one: the CLI is the source of truth, not memory.

## D. If in doubt

- Can't tie a number to the model? Stop and say so. Do not adjust a number to fit.
- Not sure a JSON property exists? Look it up with the validator CLI. Do not guess.
- Model is missing something you need? Write a request to the model owner. Do not edit
  the model.
- Tenant says a capacity limit was reached? Stop every query and render. Wait. Run one
  light probe before resuming.
- Not sure a claim is proven? Call it UNTESTED and name the test that would settle it.
- About to touch a file another agent might own? Don't. Hand it to the main thread.
