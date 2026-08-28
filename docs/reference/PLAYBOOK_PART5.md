# Part 5 — Checklists and templates

Everything below is what the reference build actually needed, in the order it needed it. Tick every
box. A box you cannot tick is a blocker to name, not a step to skip.

Labels: **TESTED** = proven on screen or by read-only DAX on a real retail model; **UNTESTED** =
plausible, not proven, test named. Trap numbers (`T1`…) point into `docs/reference/PLAYBOOK_PART4.md`.
Names follow `docs/MODEL_CONTRACT.md`; the company is `YourCo`, items are `ORG-`, report measures
are `RM `, ids are `00000000-0000-0000-0000-000000000000`, figures are illustrative.

The one-page version for daily use is `docs/reference/CHECKLISTS.md`.

## 5.1 Pre-build checklist

| # | Check | How (exact) | Status |
|---|---|---|---|
| 1 | **Audience named.** Who judges the default view, and what they will never touch. | One line at the top of the spec: "Directors and the CEO. They will not touch a slicer." | — |
| 2 | **One question the page must answer.** | One sentence under it: "Did we take budget on the latest traded day, and is the year on track?" | — |
| 3 | **Model discovery done, read-only.** Tables, measures, calc-group items, Date columns. | `python3 scripts/discover.py`, then read `schema/`. Map every row of `docs/MODEL_CONTRACT.md` to a real column and write the mapping into the spec. | TESTED (the export; the contract check is yours) |
| 4 | **Freshness known.** Last refresh and last loaded day are two different dates. | `python3 scripts/refresh.py --history`; `python3 scripts/validate.py "EVALUATE ROW(\"d\", CALCULATE(MAX('Date'[Date]), 'Date'[HasSales] = TRUE))"`. Stale = a note to the model owners, never a refresh you trigger. | TESTED |
| 5 | **Ground truth pulled once.** Latest traded day, LW, LY, WTD, YTD, budget, like-for-like, the channel and region splits — one batched query, saved to a file outside the repo. | `python3 scripts/validate.py --file ground_truth.dax --json > ../ground_truth.json` | TESTED |
| 6 | **Report-level filters read before the tie-out.** A report filter that lists fewer members than the visuals silently drops a channel (T43). | `grep -A30 '"filterConfig"' "<folder>/definition/report.json"` | TESTED |
| 7 | **Data traps written down before any visual is drawn.** Holiday comparator, dispatch-dated online sales, margin base, budget phasing, cohort keying, a saved literal pin, a dropped channel (T35–T45). | A "Data traps" block in the spec's model facts. | — |
| 8 | **Spec written and greenlit.** Rules, per-page coordinates, Done criteria. | `docs/reference/SPEC_TEMPLATE.md`, filled in. The owner says yes before any agent starts. | — |
| 9 | **Clone, never the original.** | `cp -r <original>.Report "ORG-Daily Trading.Report"` (or `cp -r report-template …`); edit `.platform` → `displayName` with the prefix, a new `logicalId`; keep `definition.pbir` `byConnection`, bound to your model (`python3 scripts/deploy_report.py "<folder>" --bind` writes it from `config.yaml`; the template ships placeholders). `deploy_report.py` refuses anything else. | TESTED (`tests/test_guardrails.py`) |
| 10 | **Backup before the first edit.** | `cp -r "ORG-Daily Trading.Report" .backup-header/` (repo root, gitignored). | — |
| 11 | **Theme lock stated.** No theme file, colour, font or size change — "not even for consistency". | Rule 1 of the spec. | — |
| 12 | **Model allowed for deploy.** `semantic_model.id` in `config.yaml` is accepted on its own; list a model under `deploy.allowed_model_ids` **only** when the report binds to a different one. | `grep -A3 allowed_model_ids config.yaml` — empty unless the report binds elsewhere. | TESTED |

## 5.2 Per-page build checklist

Copy this list into every page builder's instructions (it is rules 2–11 of the spec). One builder
per page folder; the main thread owns everything shared.

1. **Header untouched.** The settings strip — shape, accent line, title textbox, Week and Day
   slicers, "Latest day" button, day card (`RM Day Label`), basis card (`RM Basis Note`). Edit only
   the text the spec names.
2. **Only my folder.** `definition/pages/<my page id>/`. Never `report.json`, `pages.json`,
   `reportExtensions.json`, the theme, another page.
3. **Date scope per visual, never per page.** Run the helper; never hand-write a date filter:
   ```
   python3 scripts/date_filters.py <visual.json> latest-day      # day visuals on model measures
   python3 scripts/date_filters.py <visual.json> window-weeks    # trend charts (Date on the axis)
   python3 scripts/date_filters.py <visual.json> this-week       # week-to-date-by-day matrix
   python3 scripts/date_filters.py <visual.json> none            # RM YTD / WTD cards
   ```
   `window-days` is **banned** (T3). `RM ` measures pin themselves — give them **no** date filter
   (T2).
4. **Model-pure first.** Model measure + a calc-group filter on `'Time Intelligence'`. `RM `
   measures only where the spec names them, referenced with
   `"SourceRef": {"Schema": "extension", "Entity": "<measures table>"}`.
5. **Copy shapes, don't invent JSON.** Sources, in order: this report's own visuals;
   `docs/reference/snippets/`; the `skills-for-fabric` `references/*.md` (path in Part 2, 2.3; the rules used
   here are in `docs/reference/snippets/README.md`); `powerbi-report-author formatting describe-object <type>
   <object>`.
6. **New visual = new folder** `visuals/<20 lowercase hex>/visual.json`, `name` = folder name,
   unique `position.z` and `tabOrder`, inside x 16–1264 and y ≤ 720 on a 1280×720 canvas, no
   overlap with anything.
7. **Plain-English labels.** Tables and matrices: projection `displayName`. Cards:
   `objects.label[].properties.text` with `selector.metadata = "<queryRef>"`. Legend and axis titles
   off, so the words "Time Intelligence" and "Y2" never show. The calc-item values `Current` /
   `LW` / `LY` remain as matrix headers and legends — accepted, they cannot be renamed.
8. **Formats.** Cards: thousands with one decimal (`labelDisplayUnits` `1000D`, `labelPrecision`
   `1L`); percentages one decimal; tables whole units; negatives with a leading minus, no brackets.
9. **Sort by value, not alphabet** (`query.sortDefinition`). **Data labels on** every bar, column
   and line chart.
10. **No new colours.** Only hex values the original already uses. Red/green only through the
    report's existing conditional rule.
11. **Validate 0 after every batch:**
    `powerbi-report-author validate "<folder>" --format json` → `data.errorCount: 0` (the CLI is
    `npm i -g @microsoft/powerbi-report-authoring-cli`, or `npx -y @microsoft/powerbi-report-authoring-cli validate …`).
    Do not deploy from a page builder.
12. **Return** the visual list (name → type → title → position) and everything not done, with the
    reason. Nothing else.

## 5.3 Pre-deploy checklist

Run all of it offline first. Verification is capacity-lean by rule (T31): one render pass per
deploy, one batched DAX check, no parallel DAX agents.

"Same script" below is the offline check, `python3 scripts/check_report.py "<folder>" --baseline report-template` (`--baseline "<original>.Report"` when you cloned an existing report; without `--baseline` it skips rows 2–3, the theme checks). Rows 2–11
are its specification: on the reference build every one of them was a PASS line of a single
offline script that ran in seconds with no tenant. If your copy lacks one, add it there before you
deploy — none of them can be seen from the API.

| # | Check | Command / evidence | Status |
|---|---|---|---|
| 1 | PBIR validator: 0 errors | `powerbi-report-author validate "<folder>" --format json` → `data.errorCount: 0`. Read the warnings; the reference build accepted two kinds (duplicate filter names reused on purpose by `date_filters.py`; schema URL unreachable offline). Any other warning is new. | TESTED |
| 2 | Theme byte-identical to the approved one | same script with `--baseline`: every file under `StaticResources/**` byte-identical, no file added or removed (the template ships Microsoft's base theme at `StaticResources/SharedResources/BaseThemes/CY26SU07.json`; a custom theme would sit under `StaticResources/RegisteredResources/` and the same check covers it). By hand: `diff -r "<folder>/StaticResources" "<baseline>/StaticResources"` | TESTED |
| 3 | No hex colour or `fontFamily` outside the original | same script (the set of `#RRGGBB` values and `fontFamily` values under `definition/` is a subset of the original's) | TESTED |
| 4 | `isPersistentUserStateDisabled: true` in `report.json` (T16) | same script | TESTED live |
| 5 | No slicer carries a saved selection; slicers only where designed (T11, T19) | same script (`objects.general[].properties.filter` absent on every slicer) | TESTED |
| 6 | No visual-level filter on a report measure (T22) | same script | TESTED |
| 7 | Every referenced `RM ` name exists in `reportExtensions.json`; none references another `[RM …]`; `dataType` never `"String"` (T20, T21, T23) | same script; or `grep -rhoE '"Property": ?"RM [^"]+"' "<folder>/definition/pages" \| sort -u` against the `name` list | TESTED for cross-references; the phantom-name cause of T23 is UNTESTED — the check is free |
| 8 | Each report measure tested **alone** on the model (T24) | `DEFINE MEASURE 'Measures'[RM X] = … EVALUATE ROW("v", [RM X])` via `python3 scripts/validate.py --file q.dax`, one measure per query | TESTED |
| 9 | No `window-days` filter left; `RM YTD` cards carry no filters; every day visual on a model measure carries both day pins (T2, T3) | same script | TESTED |
| 10 | No overlaps, everything inside 1280×720, `name` = folder and unique | same script — the validator checks bounds, **not** overlaps | TESTED |
| 11 | Page 1 has `mobile.json` beside every data visual | same script | TESTED offline only; the phone layout is UNTESTED on a phone |
| 12 | Repo guardrails still hold | `python3 tests/test_guardrails.py` | TESTED |
| 13 | Nothing secret in the tree | `python3 tools/secret_scan.py .` → 0 hits | TESTED |
| 14 | Snapshot before deploy | `cp -r "<folder>" .backup-roundN/` | — |
| 15 | Deploy | `python3 scripts/deploy_report.py "<folder>"` → `Updated existing report '<name>'` | — |

## 5.4 Post-deploy visual review

Offline checks passed on every build that was wrong on screen. Only the eye caught the
year-to-date tile at a fifth of the truth, the last-year columns at weekly totals, an unrecorded
field error, and a "bottom 10" full of positive stores (Part 1, 1.3 has the full table). So:

1. **Open each page fresh.** `python3 scripts/capture_pages.py <item id> captures/roundN 60 --headless`
   (no `--headless` on the very first run, to sign in) — it navigates to the URL first (an open
   tab keeps the old definition, T27), polls for the page rail (~30–45 s after a definition
   update, T34), then writes one PNG and one accessibility `.txt` per page. If *"Unable to load model due to reaching capacity limits"* appears, stop and wait at
   least 30 minutes (T31).
2. **Read every number against the tie-out table** (5.7.2). The digits, not "looks right".
3. **Look for:** spinners; error tiles (*"Something's wrong with one or more fields / filters"*,
   T22, T23); ellipses or clipped labels (a 9-pt basis note lost its descenders in a 28-px card);
   scrollbars; values that look weekly on a daily axis (T3); alphabetical order where value order
   was asked; empty bands; a ranking with the wrong sign in it (T8); the words "Time Intelligence"
   or "Y2" anywhere.
4. **Grep the text.** `grep -iE "wrong|see details|\(Blank\)" captures/roundN/*.txt`; compare the
   per-page digit counts the script prints with the previous round — a blank page is a number.
5. **Test every slicer state and the reset** (T9, T11, T18): All/All = latest traded day; Day = a
   weekday → that date, LY re-labelled to the same weekday last year; Week = Last week → the last
   traded day of that week, "day 7/7"; the "Latest day" button → All/All; a **fresh open** → All/All
   (T16).
6. **Every page follows the pick** (T17): the day label changes on all pages.
7. **Header age reads sensibly:** `Mon 24 Aug 2026 · Wk 35 · day 1/7 · 3 days ago`.
8. **Count things:** traded dates on the trend × series; regions; ten bars in a bottom 10, all
   negative; the P&L foots.
9. One pass, fix locally, redeploy, one more pass. Any deploy re-opens the loop.

## 5.5 Exec-review lenses

Five read-only seats, same brief, same screenshots, same ground truth; merge; hand every blocker to
a skeptic told to refute it (the method is in Part 1, 1.4). The reference review: 24 findings, 12
skeptic checks, 0 refuted, 2 downgraded, 1 corrected. Questions each seat asks in the first ten
seconds:

| Seat | Questions |
|---|---|
| **CEO** | Which day am I looking at, and is it the latest? What is the headline — day, week, year? Do I trust the biggest red number? Could I read this on a phone? |
| **Trading Director** | Which calls do I make this morning? Is last year comparable (holiday)? Is online measured on orders or dispatches? Is the day budget phased, so "vs budget" is partly calendar? Where are the worst ten stores? |
| **Finance Director** | What is each % a percentage of? Is net sales on the page at all? Do WTD and YTD tie to the finance pack (same channels)? Which tax basis, per column? |
| **Auditor** | Does every number tie to the model to the unit? Does a report-level filter silently drop a member? Is the day pinned to a literal or self-maintaining? Is like-for-like cohort-bridged? |
| **Designer** | Is there a headline and a date? Are labels or axes truncated? Value order or alphabetical? Empty bands? Theme untouched? |

Every finding is one record:

```
id · title · page · severity (blocker | major | minor) · lenses · what_exec_sees · why_it_matters ·
proposed_change · effort (S | M | L) · evidence (file, screenshot or query) · theme (observed only)
· verify {refuted, reason}
```

No `evidence`, no finding. Theme observations are recorded, never proposed. **The owner's own eye
is a lens** — schedule it; on the reference build it caught two things four seats missed.

## 5.6 Handover checklist

1. **Memory note written** with a dated status line, ids, paths, every mechanic labelled TESTED
   (where) or UNTESTED (test), and the decisions owed (5.7.3).
2. **Spec updated in place** with the corrections learned ("CORRECTION after round 1 (TESTED)…")
   and Done criteria equal to the final screenshots.
3. **Backups named** in the note (`.backup-header/` pre-build, `.backup-round2/`, …).
4. **Model-owner asks** written as one-liners the owner can send (5.7.4). The agent never sends.
5. **Nothing committed unless asked.** `git status` listed in the note.
6. **Original untouched:** same page count, theme byte-identical.
7. **Next-session one-liner:** what to run first (`capture_pages.py` once, read every PNG).

## 5.7 Templates

### 5.7.1 Spec skeleton

The full fill-in skeleton is `docs/reference/SPEC_TEMPLATE.md`. Its shape:

```
# ORG-<name> — build spec (<date>)
Folder · item id · workspace · model id · data to <day> (wk N) · greenlit: <findings>
## Absolute rules (every builder)   1 theme locked · 2 only your page folder · 3 header done · 4 date scope per visual
                                    5 model-pure first · 6 copy shapes · 7 new-visual rules · 8 labels · 9 formats
                                    10 validate 0 · 11 what to return
## Model facts you need             contract mapping · channels · measure bases (tax, returns sign, orders vs dispatch)
                                    · tested values · report-measure list · clean columns · data traps
## Page N — <id> "<name>" (builder) Keep / DELETE / Build: rows with y-ranges, x + w per visual, measure, label,
                                    filters, title, expected value
## Done criteria (main thread)      one line of numbers per page + "0 errors, no overlaps, slicers only in the
                                    header with no saved selection, header untouched, no new colours"
## Round-N fix list                 corrections after each screen pass; "accepted as-is" items
```

Microsoft's fuller form (a `Design Brief:` YAML block in the `powerbi-report-planning` skill) was
not used on the reference build — UNTESTED here.

### 5.7.2 Tie-out table (fill before deploy, read after)

| # | Number | Where on screen | Ground truth (DAX) | Screen | Match |
|---|---|---|---|---|---|
| 1 | Latest traded day, sales, all channels | page 1 hero / channel matrix Total | 1,234,567 | 1,234.6K / 1,234,567 | ✓ |
| 2 | Day vs LW / vs LY | channel matrix Total | 1,300,000 / 1,400,000 | −5.0% / −11.8% | ✓ |
| 3 | WTD sales / LY / budget | page 1 hero group 2 | 1,234,567 / 1,400,000 / 1,350,000 | −11.8% / −8.6% | ✓ |
| 4 | YTD sales / LY / budget | page 1 hero group 3 | 123,456,789 / 108,000,000 / 100,000,000 | 123.5M / +14.3% / +23.5% | ✓ (was a fifth of this in round 1, T2) |
| 5 | Online orders placed / LW | orders matrix | 234,567 / 184,000 | 234,567 / +27% | ✓ |
| 6 | Store like-for-like / LY (cohort-bridged) | LFL matrix | 456,789 / 447,000 | +2.2% | ✓ (naive = +16.6%, T42) |
| 7 | Stores total / LY | store league Total | 789,012 / 864,000 | −8.7% | ✓ |
| 8 | Header | day card | max `HasSales` date, week, day-of-week | `Mon 24 Aug 2026 · Wk 35 · day 1/7 · 3 days ago` | ✓ |

Keep the filled table outside the repo — it holds real figures.

### 5.7.3 Memory-note skeleton

```
---
name: <kebab-name>
description: "<one line: what, where, status, date>"
---
**<Report>** = <what it is> (workspace id, item id, model id, page ids). Source of truth on disk: <folder>.
Deploy route: python3 scripts/deploy_report.py "<folder>".
**<date> — status.** BUILT | DEPLOYED | AWAITING GREENLIGHT. Backups: <.backup-*>. Nothing committed.
TESTED mechanics: (1) <claim> — <how proven, where seen>. (2) … (label every one TESTED or UNTESTED)
Data traps (reuse, don't re-derive): <holiday LY · dispatch-dated online · margin base · saved literal pin · dropped channel · budget phasing · cohort keying>
Constraints: theme locked · model read-only · no refreshes · the owner sends, the agent drafts
Decisions the owner still owes: <list>
Next session: <one command>, then <one check>.
Related: <notes>
```

### 5.7.4 Model-owner request one-liners (for the owner to send)

One sentence each, evidence attached, no adjectives. The shapes that came up:

1. `'Date'[DayNumber]` is 0 for every weekday except one, so weekday sort is scrambled — please fix
   (T38).
2. N stores carry a second spelling of a region in `<legacy region column>` and have no budget —
   please recode (T39).
3. Site `<old code>` carries a daily budget but no sales; `<new code>` trades with no budget —
   please move the budget to the new code (inferred — confirm; T40).
4. Is online `[Sales]` recognised on dispatch, not order? The weekday/weekend pattern says so —
   please confirm (T36).
5. How is the daily budget phased? The Monday online budget equals its public-holiday LY (T41).
6. `<column>` errors when queried — please fix or drop.
7. Longer term: a `'Date'[IsHoliday]` flag and a like-for-like measure keyed to this year's
   cohort, so the report DAX can go (T35, T42).

### 5.7.5 "What I will improve — greenlight?" message

The shape the owner said yes to, twice:

```
<Answer first: 2–4 sentences — is it fit to show, and why not yet.>

Checked (table): what | value | one-line note        ← every number pulled read-only, dated

A · Fix before any Director or the CEO sees it        ← untrue or unqualified on screen
  1. <title> — effort S/M/L — what — refs F##         Decision: <X or Y? I would go X.>
  2. …
B · Make it something a Director can act on
  3. …
C · Polish, once A and B are in                       ← theme lock stated here; observations only

Limits: <what was inferred, what was not run, "no change has been made">
One question: greenlight all, or pick by number?
```

Two options at most per decision, with a recommendation. The format works because every item
already has its effort and its recommendation, so the reply can be "all of them" or a list of
numbers.

### 5.7.6 Page-builder brief (what each agent gets)

```
You build page <id> "<name>" of "<folder>". Read docs/reference/SPEC_TEMPLATE.md rules 1–11 (they bind you)
and your page section. Touch only definition/pages/<id>/. Copy shapes from: <visual ids>,
docs/reference/snippets/. Expected numbers: <Done criteria line>. Date filters only via
python3 scripts/date_filters.py. Validate to 0 errors after every batch. Do not deploy.
Return: visual list (name → type → title → position) and anything not done, with the reason.
```
