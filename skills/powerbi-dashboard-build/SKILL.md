---
name: powerbi-dashboard-build
description: Build, add to, rebuild, or extend a Power BI / Microsoft Fabric report page as PBIR files, and deploy it through the powerbi-agent MCP server against the user's own tenant. Use when the user asks to build a dashboard, add or rebuild a report page, deploy a PBIR report, clone a report and fix it, or "make a dashboard for my directors". Drives the MCP tools step by step through spec, tie-out, build, validate, deploy and capture, and will not call a page finished until it has been seen on screen.
---

# Power BI dashboard build

Build an executive-grade report page as PBIR files and deploy it through the
`powerbi-agent` MCP server. Nothing is "done" until every page has been
captured as a screenshot and read against a written Done-criteria table — the
see-it doctrine, `docs/reference/PLAYBOOK.md` 1.3.

## Procedure

0. Call `guardrails()` (or read the `guardrails://rules` resource) and hold to it
   all session: never touch an item you did not create, never trigger a refresh,
   the model is read-only, the theme is locked once approved, one render pass
   per deploy, one batched DAX query — not many.
1. Call `connection_status()`. Do not proceed on a failed or ambiguous
   connection; report it back instead of guessing which tenant you are on.
2. Fill `docs/reference/SPEC_TEMPLATE.md` before writing any JSON: audience, the
   one question the page must answer, a per-page visual list with positions, and
   **Done criteria** — the expected number for every tile, per page. An agent
   that cannot hit a Done-criteria number reports it; it does not improvise.
3. `get_model_schema(workspace, model)` to see every table, column, measure and
   calculation item, then one batched `run_dax(query, ...)` to build the tie-out
   table: latest traded day, week-to-date, last year same weekday, budget, per
   channel. One query, not fifteen — `docs/reference/PLAYBOOK_PART3.md` Step 2.
4. Start from `report-template/` (copy to `"ORG-<name>.Report"`) or call
   `get_report_definition(report, out_dir, workspace)` on an existing report
   into a **clone** folder. Never edit the original item — that is what the
   `ORG-` prefix and the "never touch an item you did not create" guardrail
   exist to stop.
5. Split by page: one builder per `definition/pages/<page id>/` folder. The main
   thread alone owns `report.json`, `pages.json`, `reportExtensions.json`, the
   theme and the deploy — this is what stops two builders writing the same
   file.
6. Set date scope per visual with `set_date_filters(visual_json, mode, weeks)` —
   `latest-day` for latest-day visuals on model measures, `window-weeks` for
   trend charts, `this-week` for week-to-date matrices, `none` for cards already
   bound to self-pinning report measures. **Never hand-write a date filter**: a
   plain `'Date'[Date]` window under a time-intelligence calculation group
   returns the whole last-year week instead of one day (see Part 4, trap T1/T3).
7. Report-only measures go in `reportExtensions.json`, prefixed `RM `, never in
   the model — the model is read-only. Follow `docs/reference/measures/README.md`:
   no `RM ` measure references another; its `dataType` is `"Text"`, never
   `"String"`; test each measure alone before shipping it.
8. Call `validate_report(folder, baseline)` after every batch. **Do not
   continue past a nonzero error count** — fix and re-validate. `baseline` is
   `report-template` (or the original's folder, when you cloned one); it also
   checks theme byte-identity, overlaps, canvas bounds, date pins present and
   banned filter kinds.
9. `deploy_report(folder, bind=True)` the first time (writes the model binding
   from config); plain `deploy_report(folder)` after that. It refuses names
   without the `ORG-` prefix and models not in the allowed list — that refusal
   is correct; do not route around it.
10. `capture_pages(target, out_dir, headless=True, settle_seconds=60)`, then
    LOOK at every PNG and read every `.txt` against the Done criteria — this is
    the hand-off to the `powerbi-dashboard-verify` skill. A clean validator run
    is not a finished page.
11. At most two fix rounds. After that, report which Done-criteria numbers are
    still not met and why, instead of a third silent attempt.

## Traps to remember

Full catalogue: `docs/reference/PLAYBOOK_PART4.md` (T1–T51). Build recipe with
every JSON shape: `docs/reference/PLAYBOOK_PART3.md`. Load Microsoft's
`powerbi-report-authoring` and `powerbi-report-design` skills for PBIR
mechanics and layout critique; their CLI
(`npx -y @microsoft/powerbi-report-authoring-cli` — `validate`, `catalog
describe <visualType>`, `formatting describe-object <visualType> <object>`) is
the source of truth for PBIR details — never guess a property's shape; copy it
from an existing visual or from `docs/reference/snippets/`. The six traps that
cost the most on the reference build:

- A date-column filter window makes a "last year" calculation item return the
  whole comparable **week** on every day, not one day (T1, T3).
- A top-N filter's subquery does not inherit the visual's other filters, so a
  ranking ranks in the wrong context and cannot coexist with slicers (T8).
- A visual-level filter on a **report** measure renders an error tile (T22).
- A report measure that references another report measure fails only on
  screen, and only sometimes, because measures are injected per visual query
  (T20).
- Strict single-select on a slicer with no saved selection auto-picks
  `(Blank)` and blanks the whole page (T11).
- Persisted user state re-applies the last viewer's slicer picks, so set
  `report.json` → `isPersistentUserStateDisabled: true` (T16).

## Definition of done

- `validate_report` reports 0 errors on the final folder.
- Every Done-criteria number in the spec ties on screen, in every PNG/`.txt`
  pair from the last `capture_pages` call — not from memory of an earlier round.
- Theme is byte-identical to the baseline; no new colour or font.
- Any deploy re-opens the loop: a deploy after the last capture means look
  again before calling the page done.
- What is not met is written down, not silently dropped.
