# Part 3 — The build recipe

Steps 0–6 make every visual know *which day it is*. Steps 7–11 build the visuals, lock the theme,
verify and hand over. Every mechanism claim carries a label: **TESTED** = proven on screen or by
read-only DAX on a real retail model during the original build, with the artefact named;
**UNTESTED** = plausible, not proven, with the test that would settle it. Live output beats this
document.

This part continues `docs/reference/PLAYBOOK.md` (Parts 0–2). The traps it points at (`T<n>`) are in
`docs/reference/PLAYBOOK_PART4.md`; the checklists are in `docs/reference/PLAYBOOK_PART5.md`.

**Names used below.** Company `YourCo`; item prefix `ORG-`; report-measure prefix `RM `; every id
`00000000-0000-0000-0000-000000000000`; figures such as `1,234,567` are illustrative. The Date
table follows the model contract in Part 0, 0.4: `'Date'[Date]`, `[TradingYear]`, `[TradingWeek]`,
`[DayName]`, `[WeekLabel]` (values `This week`, `Last week`, `Wk 12 2026`) and `[HasSales]`; the
calculation group is `'Time Intelligence'` with items `Current`, `LW`, `LY`, `vs LW %`, `vs LY %`,
`YTD`, `YTD vs LY %`. Model measures in the examples: `[Sales]`, `[Budget Sales]`,
`[Sales vs Budget]`, `[Sales vs Budget %]`, `[Orders Value]`, `[Net Sales ex Tax]`, `[Margin]`,
`[Margin %]`. Store dimension `'Store'[StoreName]`, `'Store'[Channel]`, `'Store'[Region]`,
`'Store'[StoreKey]`; fact table `Fact[StoreKey]`; a like-for-like cohort table `'Store LFL'`.

Verbatim code lives beside this file so it can be copied, not retyped:

| Kind | Files |
|---|---|
| Report-measure DAX | `docs/reference/measures/preamble.dax`, `rm_wtd_sales.dax`, `rm_ytd_vs_ly_pct.dax`, `rm_lfl_ly.dax`, `rm_ly_sales_by_day.dax`, `rm_bottom10_vs_budget.dax`, `rm_day_label.dax`, `rm_basis_note.dax` |
| PBIR JSON shapes | `docs/reference/snippets/latest_day_filters.json`, `window_weeks_filters.json`, `not_blank_filter.json`, `conditional_font_colour.json`, `sort_definition.json`, `projection_display_name.json`, `clear_all_slicers_button.json`, `mobile_layout.json`, `report_extensions_shape.json` |
| Spec skeleton | `docs/reference/SPEC_TEMPLATE.md` |

`scripts/date_filters.py` writes, and on re-run replaces, exactly five filter names:
`orgLatestDayName`, `orgLatestWeek`, `orgWindowWeeks`, `orgTradedDays` (and the banned
`orgWindowDays`). The slicer filters `orgNotBlank`, `orgRecentWeeks` and `orgRecentDays` share the
`org` marker by convention only — they are copied from `docs/reference/snippets/` by hand and the script never
touches them. The marker is `deploy.filter_marker` in `config.yaml` (default `org`, independent of
the item prefix); the script, the offline checks (Step 10) and the tests all read it from there.

**Terms.** *Latest traded day* = the last day with loaded sales (`'Date'[HasSales] = TRUE`), never
today. *Day pins* = the two visual-level `TopN(1)` filters of 6.2. *Report measures* = the `RM `
measures in `definition/reportExtensions.json`. *Settings strip* = the Week slicer, Day slicer and
"Latest day" button in the header. *The original* = the report you were asked to fix, which is never
edited; *the clone* = the `ORG-` copy you build on. Starting greenfield, `report-template/` is the
clone.

---

## Step 0 — Pin the audience and the single question

**Inputs.** Who judges the page and what they will not do. On the reference build: directors and
the CEO; *the audience will not touch slicers — whatever the page shows by default is what they
judge.*

**Actions.**

1. Write the one-sentence question at the top of the brief: *does what is on screen make sense to
   a director and to a CEO, and what must change?*
2. Run the five-lens review before touching JSON (Part 1, 1.4). Verdicts and findings go in one
   file, each finding with `what_exec_sees`, `why_it_matters`, `proposed_change`, `evidence` and a
   skeptic `verify` block.
3. Write the plan with the owner's decisions left open: group **A** "fix before any director sees
   it", **B** "make it something a director can act on", **C** "polish"; effort S/M/L per step; a
   `decision` line per open question with two options and a recommendation.
4. Record the constraints in the brief: read-only model, no refreshes, theme lock, who sends what
   to whom (Part 1, 1.2).

**Outputs.** `brief.md`, `findings.json`, `plan.json` and the owner's greenlight — on the reference
build, literally *"clone it, do all of them"*. Keep these files outside the repo; they hold real
figures.

**Checks.** Every blocker must be a data fact, proven by read-only DAX before the plan is written:
the literal weekday saved in a slicer, the public-holiday comparator, the dispatch-dated online
measure, the missing week-to-date and year-to-date, the margin percentage whose base was not on the
page, the weekly budget blown down to days (Part 1, 1.1). A finding without a query or a screenshot
behind it is an opinion.

---

## Step 1 — Discover the model

**Inputs.** The decoded TMDL under `schema/` (written by `python3 scripts/discover.py`) and live
`INFO` views through `executeQueries` — a read.

**Actions.**

1. **Inventory from TMDL.** Read `schema/` for every table, column, measure and calculation item.
   `discover.py` prints a table-by-table summary; keep it beside the model contract (Part 0, 0.4)
   and tick each contract row.

2. **Confirm the live state with INFO views** (batched into as few queries as possible):

   ```
   EVALUATE SELECTCOLUMNS(INFO.VIEW.MEASURES(), "N", [Name], "S", [State])
   EVALUATE INFO.VIEW.RELATIONSHIPS()
   EVALUATE SELECTCOLUMNS(INFO.VIEW.TABLES(), "N", [Name])
   EVALUATE 'Time Intelligence'
   EVALUATE SELECTCOLUMNS(FILTER(COLUMNSTATISTICS(), [Table Name] = "Date"), "col", [Column Name])
   ```

   **TESTED limit** (real retail tenant): `executeQueries` blanks `[Expression]` and
   `[FormatString]` on `INFO.VIEW.MEASURES()` and rejects `INFO.CALCDEPENDENCY()`. Measure DAX can
   only come from the TMDL under `schema/`; the DMVs are good for `[State]`, relationships and
   inventory.

3. **Read the calculation items you will lean on.** A typical shape (yours will differ — read it,
   do not assume it):

   ```
   calculationItem LW = CALCULATE ( SELECTEDMEASURE (),
       TREATAS ( SELECTCOLUMNS ( FILTER ( 'Date', 'Date'[HasSales] = TRUE ), "d", 'Date'[Date] - 7 ), 'Date'[Date] ) )

   calculationItem LY = CALCULATE ( SELECTEDMEASURE (),
       TREATAS ( SELECTCOLUMNS ( FILTER ( 'Date', 'Date'[HasSales] = TRUE ),
                     "y", 'Date'[TradingYear] - 1, "w", 'Date'[TradingWeek], "dn", 'Date'[DayNumber] ),
                 'Date'[TradingYear], 'Date'[TradingWeek], 'Date'[DayNumber] ) )
   ```

   Read `LY` as: *re-point the days in context that have sales to last trading year, same trading
   week, same weekday number — filters on those three columns are replaced, every other filter
   stays.* That one sentence drives the whole of Step 6.

4. **Classify every Date column** as calendar or non-calendar, and note its `sortByColumn`. A
   *calendar* column is one the model's calendar definition (or the calc group's `TREATAS`) owns;
   the calc group rewrites filters on those. A *non-calendar* column survives the shift.

   | Column | Kind | What it is | Use it for |
   |---|---|---|---|
   | `Date` | calendar, the key | the date | trend-chart axis **only** |
   | `TradingYear`, `TradingWeek` | calendar | fiscal year / week integers | pins inside DAX, year to date |
   | `DayName` | non-calendar; `sortByColumn` = a day-number column | Monday … Sunday | **the day pin** |
   | `WeekLabel` | non-calendar, calculated from `TODAY()`; `sortByColumn` = a year-and-week key (oldest first) | `This week`, `Last week`, `2 weeks ago`, `Wk 12 2026` | **the week pin** and the Week slicer |
   | `HasSales` | non-calendar flag, TRUE up to the last loaded sale day | the anchor | every pin and every `RM ` measure |
   | a numeric relative-week column (`0` = this week, `1` = last week …) | non-calendar, `TODAY()`-based | weeks back | **never** under the calc group — TESTED: it returns BLANK for `LY`/`LW` |
   | a "last full week" flag tied to the load date | non-calendar | lags the load | not used |
   | any column that errors when queried | — | — | do not use; report it |

   **TESTED for the three columns actually used** (`DayName`, `WeekLabel` as pins; the relative-week
   column as the thing that blanks the calc group). Any other column: prove it with one DAX row
   before you pin on it (T5).

5. **Data-quality checks that changed the design** (all TESTED read-only on the reference model —
   run the equivalents on yours before drawing a visual):

   - **The day-number sort key.** `EVALUATE SUMMARIZECOLUMNS('Date'[DayName], 'Date'[DayNumber],
     FILTER(ALL('Date'), 'Date'[TradingYear] IN {2025, 2026}), "Days", COUNTROWS('Date'))`. On the
     reference model every weekday was `0` except one. Consequences: `DayName` sorted scrambled, and
     the calc group's `dn` key could not separate days — only a `DayName` filter in context could
     (T38). That is why the Day slicer became a date list (6.4).
   - **Region coding.** Count stores and sales per region value. The reference model had the same
     region spelled two ways, one of them with no budget, plus dozens of blank sites. Use the clean
     column and a not-blank filter (7.10); write the recoding request for the data team.
   - **Budget phasing.** Compare one channel's daily budget with its last-year actual for the same
     weekday. When they match to within a rounding error, the daily budget is phased on last year's
     daily profile — label it on the canvas; confirm with finance (T41).
   - **The cohort table key.** If the like-for-like status table is keyed by store *and year*, a
     plain cohort matrix under `LY` compares two different cohorts. On the reference model naive
     retail LFL read +16.6%; cohort-bridged it was +2.1% (6.5, T42).
   - **Report filter versus visual filters.** List the values a report-level channel filter allows
     and the values each visual asks for. One channel silently missing from the report filter took
     5% off the day total with no mark on the page (T43).
   - **Which measure means what.** For each headline measure write the basis: tax in or out,
     returns signed, dated by order or by dispatch. The reference model's online sales measure
     counted dispatches; orders placed was a different measure (T36).

**Outputs.** A "Model facts you need" block in the spec (Step 3): channels, measure bases, the
tested values, the clean columns to use and the ones to avoid.

**Checks.** Read the latest traded day —
`EVALUATE ROW("latest", CALCULATE(MAX('Date'[Date]), 'Date'[HasSales] = TRUE()))` — and its age. If
the data is stale, write a one-line note for the data team. Never trigger a refresh (Part 1, 1.2).

---

## Step 2 — Pull ground truth (the tie-out table)

**Inputs.** The model id, `scripts/validate.py` (read-only `executeQueries`; point it at the model
the report binds to, which may not be the one in `config.yaml`).

**Actions.** Build the numbers *in the context the page will use*, one batched query per question.

1. The latest day and its keys — the block every other query starts with:

   ```
   VAR d  = CALCULATE(MAX('Date'[Date]), 'Date'[HasSales] = TRUE())
   VAR dn = CALCULATE(MAX('Date'[DayName]),  'Date'[Date] = d)
   VAR wk = CALCULATE(MAX('Date'[WeekLabel]), 'Date'[Date] = d)
   ```

2. The channel matrix *as the visual queries it* — the same columns, the same calc items, the day
   pins expressed as `TREATAS`:

   ```
   EVALUATE
   VAR d  = CALCULATE(MAX('Date'[Date]), 'Date'[HasSales] = TRUE())
   VAR dn = CALCULATE(MAX('Date'[DayName]),  'Date'[Date] = d)
   VAR wk = CALCULATE(MAX('Date'[WeekLabel]), 'Date'[Date] = d)
   RETURN SUMMARIZECOLUMNS('Store'[Channel], 'Time Intelligence'[Time Intelligence],
       TREATAS({dn}, 'Date'[DayName]), TREATAS({wk}, 'Date'[WeekLabel]),
       TREATAS({"Current", "LW", "LY", "vs LW %", "vs LY %"}, 'Time Intelligence'[Time Intelligence]),
       "Sales", [Sales])
   ORDER BY 'Store'[Channel], 'Time Intelligence'[Time Intelligence]
   ```

3. The *old* page's context, to prove what it was really showing — e.g. the saved literal
   selections: `TREATAS({2026}, 'Date'[TradingYear]), TREATAS({"This week"}, 'Date'[WeekLabel]),
   TREATAS({"Monday"}, 'Date'[DayName])`.

4. **LY as a date, not a number.** Ask for the four same-weekdays around the comparator:

   ```
   EVALUATE SUMMARIZECOLUMNS('Date'[Date], 'Store'[Channel],
       TREATAS({DATE(2025,8,11), DATE(2025,8,18), DATE(2025,8,25), DATE(2025,9,1)}, 'Date'[Date]),
       "Sales", [Sales])
   ```

   This is the query that turns "down 42% versus last year" into "last year's day was a public
   holiday" (T35). Look at the dates, not just the totals.

5. **Year to date by hand**, to check the calc group's `YTD` item:
   `CALCULATE([Sales], FILTER(ALL('Date'), 'Date'[TradingYear] = 2025 && 'Date'[Date] <= DATE(2025,8,25)), <your channel set>)`.

6. **The week window as the visual pins it** — the same `TopN` the filters will use, in DAX:

   ```
   DEFINE
     VAR __wk = TOPN(1, CALCULATETABLE(VALUES('Date'[WeekLabel]), 'Date'[HasSales] = TRUE),
                     CALCULATE(MAX('Date'[Date]), 'Date'[HasSales] = TRUE), DESC)
   EVALUATE
     SUMMARIZECOLUMNS('Store'[Channel], 'Date'[Date],
       TREATAS(__wk, 'Date'[WeekLabel]), TREATAS({TRUE}, 'Date'[HasSales]),
       "Sales", [Sales])
   ```

7. **The comparison that exposes the calc-group trap** — one `SUMMARIZECOLUMNS` over
   `'Date'[Date]` returning this year, last year via a day-shifting measure, last year via the
   `LY` calc item, and budget, side by side (the table in Part 2, 2.2). Run it once, keep the
   output; it is the proof behind 6.1.

**Outputs.** One JSON file of results (kept outside the repo) and this table, which "done" is
checked against. Figures illustrative:

| Item | Value |
|---|---|
| Latest traded day (`HasSales`) | Mon 24 Aug 2026, trading week 35, day 1 of 7 |
| LW (as the `LW` item computes it) | Mon 17 Aug 2026 |
| LY (same weekday, same trading week) | Mon 25 Aug 2025 — a public holiday; this year's falls the following week, so the sign flips next week |
| Day total, the channel set the old page used | 1,234,567 · LW 1,500,000 · LY 2,000,000 |
| Day total, every channel the visuals ask for | 1,301,000 (the dropped channel: +67,000) |
| By channel (Current / LW / LY / Budget) | one row per channel |
| Online orders placed (`[Orders Value]`) vs dispatched (`[Sales]`) | 234,567 (+27% vs LW) vs 98,765 (−56% vs LW) |
| Full previous week | sales · LY · budget |
| WTD / YTD per the report measures | WTD sales · LY · % · budget · %; YTD sales · LY · % · budget · % |
| Retail LFL | this year vs naive LY (+16.6%) vs cohort-bridged LY (+2.1%) |

Two YTD figures pulled on different channel sets are not comparable — before quoting a YTD, re-run
one query on one channel set.

**Checks.** (1) Every figure on the original screen ties to the model *before* you change anything;
if it does not, you have found a bug in the original, not in your query. (2) One batched query per
question; no parallel DAX agents (Part 2, 2.8).

---

## Step 3 — Write the spec with Done criteria

**Inputs.** Findings, plan, ground truth, and the reference visuals you will copy shapes from.

**Actions.** One file a builder can follow without asking a question. Use `docs/reference/SPEC_TEMPLATE.md`;
its sections, in order:

1. **Identity** — folder, item id, workspace, model id, latest data day, greenlit scope.
2. **Absolute rules** for every builder (the full list is Part 5, 5.2): theme locked; only your page
   folder; header done; date scope per visual via `scripts/date_filters.py`, never hand-written;
   model-pure first; copy shapes, don't invent JSON; new-visual rules; plain-English labels;
   number formats; `powerbi-report-author validate "<folder>" --format json` → `errorCount: 0` after
   every batch; what to return.
3. **Model facts you need** — channels, measure bases, TESTED values, the report-measure list, clean
   columns.
4. **Per page** — every visual: keep / delete / modify / build, `x y w h`, fields, filters, title,
   expected numbers.
5. **Done criteria** — the Step 2 numbers per page, one line each ("Page 1 hero: 1.2M / −45.0% WTD
   vs LY / +14.2% YTD vs LY"), plus "0 validation errors, no overlaps, header untouched, no new
   colours, slicers only in the header with no saved selection".
6. **Round-N fix list** — after each screen review, corrections marked in place:
   *CORRECTION after round 1 (TESTED)*. On the reference build two mechanics changed this way: the
   date-column trend window became the week-based window, and the year-to-date cards moved from the
   calc-group `YTD` item to `RM YTD …` measures (T2, T3).

**Outputs.** The spec and the approval gate. The Microsoft `powerbi-report-planning` skill
(`microsoft/skills-for-fabric`) states it in one line: *do not build before the user approves the
locked report spec.*

**Checks.** A builder can list back "name → type → title → position" for its page from the spec
alone; every Done number comes from Step 2, not from a builder's belief.

---

## Step 4 — Create the report folder

**Inputs.** A report item folder in Fabric Git format: `.platform`, `definition.pbir`,
`definition/**`, optionally `StaticResources/**`. Either the original (cloned) or
`report-template/`.

**Actions.**

1. Copy the folder to `ORG-Daily Trading.Report/`. Nothing else goes in an item folder — Fabric
   accepts only those parts.

2. Set the display name and a **fresh** `logicalId` in `.platform` (a copied original may carry
   all zeros, or the original's id — either would collide):

   ```json
   {
     "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
     "metadata": { "type": "Report", "displayName": "ORG-Daily Trading" },
     "config": { "version": "2.0", "logicalId": "00000000-0000-0000-0000-000000000000" }
   }
   ```

3. Keep `definition.pbir` bound **`byConnection`** to the existing model:

   ```json
   {
     "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
     "version": "4.0",
     "datasetReference": {
       "byConnection": {
         "connectionString": "Data Source=\"powerbi://api.powerbi.com/v1.0/myorg/<Workspace Name>\";initial catalog=\"<Model Name>\";integrated security=ClaimsToken;semanticmodelid=00000000-0000-0000-0000-000000000000"
       }
     }
   }
   ```

   The template ships exactly these placeholders. `python3 scripts/deploy_report.py
   "ORG-Daily Trading.Report" --bind` writes the string from `config.yaml` (workspace name, model
   name, model id) — once; or replace the three placeholders by hand. **Never `byPath`.** A
   `byPath` binding would create a new semantic model in the workspace; `scripts/deploy_report.py`
   refuses it before any HTTP call (TESTED by `tests/test_guardrails.py`).

4. Allow the model id **only if it is not `semantic_model.id`**. The deploy script accepts
   `semantic_model.id` from `config.yaml` on its own, or any id listed under
   `deploy.allowed_model_ids` — the case when the report binds to a production model that is not
   the one you discovered against:

   ```yaml
   deploy:
     item_prefix: ORG-
     allowed_model_ids:
       - 00000000-0000-0000-0000-000000000000
   ```

5. Validate, run the offline tests, deploy **as-is**, snapshot:

   ```
   powerbi-report-author validate "ORG-Daily Trading.Report" --format json   # data.errorCount must be 0
   python3 tests/test_guardrails.py
   python3 scripts/check_report.py "ORG-Daily Trading.Report" --baseline report-template
   python3 scripts/deploy_report.py "ORG-Daily Trading.Report" --bind       # --bind once (action 3)
   cp -r "ORG-Daily Trading.Report" .backup-round0                          # gitignored snapshot
   ```

   `deploy_report.py` is idempotent by display name and prints `Created report '…' (id=…)` — keep
   that id; every capture needs it.

**Outputs.** An `ORG-` item that renders identically to the original (or to the template), and
`.backup-round0/` as the rollback point.

**Checks.** `tests/test_guardrails.py` green (it checks that `report-template/` is deployable and
clean; your `ORG-…Report/` folder is gitignored and not tested — `check_report.py` above covers
it). The first page load after a definition update takes ~30–45 s (TESTED). Capture round
0 and compare with the original before editing anything: a difference here is a deploy problem,
not a design problem.

---

## Step 5 — The header pattern

Every page carries the same header at the same positions. The reference layout, 1280 × 720 canvas:

| Visual | `visualType` | x | y | w | h | Bound to |
|---|---|---|---|---|---|---|
| header band | `shape` | 0 | 0 | 1280 | 86 | — |
| accent line | `shape` | 0 | 86 | 1280 | 3 | — |
| title | `textbox` | 20 | 6 | 430 | 76 | — |
| Week slicer | `slicer` | 462 | 6 | 120 | 76 | `'Date'[WeekLabel]` |
| Day slicer | `slicer` | 588 | 6 | 170 | 76 | `'Date'[Date]` |
| "Latest day" button | `actionButton` | 766 | 26 | 90 | 36 | — |
| day card | `cardVisual` | 860 | 8 | 404 | 42 | `RM Day Label` |
| basis note | `cardVisual` | 860 | 50 | 404 | 34 | `RM Basis Note` |

The slicers and the button are the settings strip (6.4). Two sizes were learned on screen: the
basis note grew from h 28 to h 34 after a visual review found its descenders clipped; and a dropdown
slicer with a header needs h ≥ 76 — **TESTED:** h 76 validates, h 64 fails with
`PBIR_SLICER_HEIGHT_BELOW_FLOOR` (header ≈ 28 + selector 32 + padding). The exact floor between 65
and 76 is **UNTESTED**; `skills-for-fabric` `references/slicers.md` (Part 2, 2.3) gives
`h = 60 + top padding + bottom padding`.

**Title textbox** — three `paragraphs` runs in the native textbox shape (the wrapped form validates
and renders invisible — `references/textbox.md`): a 19 px bold title (`Daily Trading — Today`); a
10 px basis line — the reference build read `Daily sales · latest traded day | Stores & Online ·
inc tax unless stated`; the template ships `<channels> · <inc or ex tax> unless stated`, and you
**must** write your own basis there, because it is printed on the canvas; a 9 px hint
(`Week & Day on All = latest traded day · pick either to move the whole report`).

**Day card** — the projection shape for every report-measure binding. `Schema: "extension"` is
what tells the service the measure lives in `reportExtensions.json`; the entity is a table that
exists in your model (the examples use a measure table called `Measures`):

```json
"projections": [{
  "field": { "Measure": { "Expression": { "SourceRef": { "Schema": "extension", "Entity": "Measures" } }, "Property": "RM Day Label" } },
  "queryRef": "Measures.RM Day Label",
  "nativeQueryRef": "RM Day Label"
}]
```

`objects.label[0].properties.text` reads `'Latest trading day'`; every card object carries
`"selector": { "id": "default" }` (`references/card.md`). The original's header card projected
`Max('Date'[TradingWeek])` — a week number without a date, which is how "which day am I looking at?"
went unanswered.

Title, day card and basis card each get a `mobile.json` (7.12); shapes, slicers and the button do
not.

**Checks.** The header renders on every page (round-0 capture), and the day label reads a real
date, week and age.

---

## Step 6 — Date mechanics

The core of the method: land on the latest traded day with **no saved literal**, and keep `LY`/`LW`
right while you do it.

### 6.1 Why a `'Date'[Date]` filter breaks LY (TESTED)

The `LY` item (Step 1) rewrites the filters on `TradingYear`, `TradingWeek` and the day-number
column. Filter a visual on `'Date'[Date]` — a `TopN` window, a page filter, a slicer — and the
shift replaces that filter with the **whole last-year week**: every day on a daily trend reads the
weekly LY total, and a single-day card reads a week-sized LY. Proven two ways on the reference
build: on screen (LY columns flat at the weekly total on every day of a daily chart, budget line
daily) and by the side-by-side query of Step 2, action 7, where the calc-item column repeats one
number across the week while the day-shifting measure differs per day (T1, T3).

A filter on `DayName` or `WeekLabel` — non-calendar columns — survives the shift, so `LY` becomes
*same weekday, same trading week, last year* and `LW` becomes *same weekday, last week*.

**The rule:** pins go on `DayName` + `WeekLabel`. `'Date'[Date]` is only ever an axis.

Why the calc group's own day-number key cannot do this job on the reference model is the broken
sort key of Step 1 (T38) — an **UNTESTED** hypothesis for the general case; the pin method does not
depend on it.

### 6.2 The latest-day pin — two visual-level `TopN(1)` filters (TESTED)

Run, never hand-write:

```
python3 scripts/date_filters.py <visual.json> latest-day
```

It strips any earlier `org*` filter on the visual and appends two: `orgLatestDayName` (`TopN 1` on
`'Date'[DayName]`) and `orgLatestWeek` (`TopN 1` on `'Date'[WeekLabel]`), each ordered by
`Max('Date'[Date])` descending over rows where `HasSales = true`. Verbatim JSON:
`docs/reference/snippets/latest_day_filters.json`. In words, each filter is:

- `field` = the Date column; `type` = `TopN`; `howCreated` = `User`;
- `From` = a `subquery` over `Date` that selects the column, `Where` `HasSales = true`, `OrderBy`
  `Direction 2` (top) on `Aggregation {Function 4 (Max), 'Date'[Date]}`, `Top 1`; plus the `Date`
  entity itself;
- outer `Where` = the column `In` the subquery.

Rules that make it valid, from `skills-for-fabric` `references/filters.md`: `OrderBy.Expression`
must be an `Aggregation`, not a `Measure` (T7); the `Where` sits **inside** the subquery (T10);
`TopN` is a visual-level filter only (T6); inside `Where`, `SourceRef` uses `Source`, not `Entity`.

There is no date literal anywhere, so the pin moves with each load. **TESTED:** `LY` and `LW` tie
exactly to the Step 2 table; and the pin picks the latest traded day **within the slicer context** —
Day = a Wednesday → that Wednesday, with `LY`/`LW` relabelled; Week = `Last week` → the Sunday of
last week, "day 7/7" (T9).

Two traps, both TESTED: a `TopN` subquery does not inherit the other-column filters on the visual, so
a store `TopN` cannot coexist with the day pins or the slicers — it ranked over all history and put
positive stores in a "bottom 10" (T8); and a visual-level filter on a *report* measure renders
*"Something's wrong with one or more filters"* (T22). Both fixed by ranking inside the measure (7.9).

### 6.3 Week windows: `window-weeks` and `this-week` (TESTED)

```
python3 scripts/date_filters.py <visual.json> window-weeks   # last 3 trading weeks, traded days only
python3 scripts/date_filters.py <visual.json> this-week      # the week of the latest traded day
```

`window-weeks` = `orgWindowWeeks` (`TopN 3` on `WeekLabel`, same ordering as the pin) plus the
Categorical filter `orgTradedDays` (`'Date'[HasSales] = true`, non-calendar, so `LY`/`LW` keep
working). Verbatim JSON: `docs/reference/snippets/window_weeks_filters.json`. `this-week` is the same pair with
`Top 1`; the week-to-date-by-day matrix uses it, and its Total column is week to date.

On a trend chart with `'Date'[Date]` on the axis, the last-year series is the report measure
`RM LY Sales by Day` (`docs/reference/measures/rm_ly_sales_by_day.dax`) — plain DAX shifting year, week and
day name, **no calc group** — because the calc item `LY` under a date axis is the 6.1 failure.

`window-days` (`TopN 14` on `'Date'[Date]`) stays in the script for history and is **banned** by
the spec: **TESTED wrong** for LY (T3). The related claim that the same window also makes
`[Budget Sales]` read as the weekly total is **UNTESTED** — no screenshot shows it; verify before
repeating it.

### 6.4 Slicers that do not fight the pins (TESTED live)

The original saved a pick: the Day slicer's `objects.general[0].properties.filter` held
`In 'Date'[DayName] Values 'Monday'`, and the Week slicer held `'This week'`. Correct the morning it
was built, stale from the next day, blank on Monday mornings (T19). The rebuilt settings:

| Setting | Value | Why |
|---|---|---|
| `objects.data.mode` | `'Dropdown'` | compact header |
| `objects.selection` | `singleSelect` `true`, `strictSingleSelect` `false`, `selectAllCheckboxEnabled` `false` | one week / one day. **TESTED:** strict single-select with no saved selection auto-picks the first item, `(Blank)`, and blanks the whole page (T11). "All" is the resting state, not a checkbox |
| `objects.general` | absent | no saved selection. **TESTED:** an absent `general.filter` lands on "All" |
| filter `orgNotBlank` | `Advanced`, `Not(Comparison ComparisonKind 0, column, Literal "null")` | hides the blank row (T12). `docs/reference/snippets/not_blank_filter.json` |
| Week filter `orgRecentWeeks` + `sortDefinition` | `TopN 13` on `WeekLabel`, `Max(Date)` desc over `HasSales`; sort `Descending`, `isDefaultSort: false` | the label column sorts by its year-and-week key, oldest first, over every week in the model (T13). Now: `This week`, `Last week`, `2 weeks ago`, `Wk 32 2026` … newest first. `docs/reference/snippets/sort_definition.json` |
| Day field | `'Date'[Date]`, `Descending`, `TopN 91` (`orgRecentDays`) | a date list, not a weekday list: `DayName` sorted scrambled on the reference model (T14), and dates need no sort column. A date pick keeps `LY` on the same weekday |
| `syncGroup` | `{"groupName": "WeekSync" / "DaySync", "fieldChanges": true, "filterChanges": true}` — a sibling of `visualType` | one pick moves every page (T17). Sync links slicers; it does not place them — every page carries its own copy |

Proven on screen (Step 10, Level 4): newest-first dates; a date pick keeps `LY` on the same weekday;
a Week pick narrows the Day list; cross-page sync. The resting state is Week All / Day All, every
visual on the latest traded day.

**The reset button** is an `actionButton` whose `visualContainerObjects.visualLink` has `show`
`true` and `type` `'ClearAllSlicers'` (`docs/reference/snippets/clear_all_slicers_button.json`; T18).

**`report.json` → `settings.isPersistentUserStateDisabled: true`.** Without it the service
re-applies the last viewer's picks and the next viewer does not land on All/All (T16). TESTED live.

### 6.5 The report measures — `definition/reportExtensions.json`

File shape: `docs/reference/snippets/report_extensions_shape.json` — `"name": "extension"`, one entity (your
measure table), measures with `name`, `dataType`, `formatString`, `expression`. Visuals reference
them with `"Schema": "extension"` (Step 5). Every name starts with `RM ` so a reader, a grep and a
dead-measure scan can tell them from model measures.

**The shared preamble** (`docs/reference/measures/preamble.dax`) is the prefix of every `RM ` measure:

```
VAR _Cut = CALCULATE(MAX('Date'[Date]), 'Date'[HasSales] = TRUE)                      -- latest traded day IN CONTEXT
VAR _Y   = CALCULATE(MAX('Date'[TradingYear]), ALL('Date'), 'Date'[Date] = _Cut)
VAR _W   = CALCULATE(MAX('Date'[TradingWeek]), ALL('Date'), 'Date'[Date] = _Cut)
VAR _Dn  = CALCULATETABLE(VALUES('Date'[DayName]), ALL('Date'), 'Date'[Date] = _Cut)
VAR _DnW = CALCULATETABLE(VALUES('Date'[DayName]), ALL('Date'),
               'Date'[TradingYear] = _Y, 'Date'[TradingWeek] = _W, 'Date'[HasSales] = TRUE, 'Date'[Date] <= _Cut)
VAR _S   = CALCULATETABLE(VALUES(Fact[StoreKey]), REMOVEFILTERS('Date'), 'Date'[TradingYear] = _Y)   -- LFL and labels only
```

`_Cut` has **no** `ALL`. It is the latest traded day *in the current filter context*, so every
`RM ` measure follows the Week and Day slicers exactly as the day pins do (T25). `_DnW` is the set
of weekday names traded so far this week, capped at `<= _Cut`. `_S` is this year's trading stores.

**What each measure returns** (preamble omitted; full bodies in `docs/reference/measures/`):

| Measure | `dataType` / `formatString` | RETURN | File |
|---|---|---|---|
| `RM Day Label`, `RM Basis Note` | `Text` | the date-week-age label; the LY / LW dates with the public-holiday flag (Part 1, 1.1) | `rm_day_label.dax`, `rm_basis_note.dax` |
| `RM WTD Sales` | `Double`, `#,##0;-#,##0;0` | `CALCULATE([Sales], REMOVEFILTERS('Date'), 'Date'[TradingYear] = _Y, 'Date'[TradingWeek] = _W, TREATAS(_DnW, 'Date'[DayName]))` | `rm_wtd_sales.dax` |
| `RM WTD Sales LY`, `RM WTD Budget` | same | the WTD shape with `_Y - 1`; with `[Budget Sales]` | derive from `rm_wtd_sales.dax` |
| `RM YTD Sales` | same | `CALCULATE([Sales], REMOVEFILTERS('Date'), 'Date'[TradingYear] = _Y, 'Date'[Date] <= _Cut)` | inside `rm_ytd_vs_ly_pct.dax` |
| `RM YTD Sales LY`, `RM YTD Budget` | same | `'Date'[TradingYear] = _Y - 1` with `FILTER(ALL('Date'[TradingWeek], 'Date'[DayName]), 'Date'[TradingWeek] < _W \|\| ('Date'[TradingWeek] = _W && 'Date'[DayName] IN _DnW))` — same weeks, same weekdays; `[Budget Sales]` in the YTD shape | inside `rm_ytd_vs_ly_pct.dax` |
| `RM LFL TY`, `RM LFL LY` (+ `WTD` variants) — **optional, not shipped** in `reportExtensions.json`; only `rm_lfl_ly.dax` is in `docs/reference/measures/` | same | TY: the WTD shape with `TREATAS(_Dn, …)`; LY: `_Y - 1` **plus** `REMOVEFILTERS('Store LFL'), TREATAS(_S, 'Store'[StoreKey])`; WTD: `_DnW` | `rm_lfl_ly.dax` |
| the four `… vs LY %` / `… vs Budget %` (WTD and YTD) | `Double`, `0.0%;-0.0%;0.0%` | `VAR __a = <full TY body> VAR __b = <full LY or Budget body> RETURN DIVIDE(__a - __b, __b)` | `rm_ytd_vs_ly_pct.dax` |
| `RM LY Sales by Day` | `Double`, `#,##0;-#,##0;0` | per-axis-date LY; own preamble on `MAX('Date'[Date])`; no calc group | `rm_ly_sales_by_day.dax` |
| `RM Bottom 10 vs Budget` | `Double`, `#,##0;-#,##0;0` | the rank inside the measure (7.9) | `rm_bottom10_vs_budget.dax` |

**The LFL cohort bridge.** `REMOVEFILTERS('Store LFL')` drops the store-year cohort from the LY
side; `TREATAS(_S, 'Store'[StoreKey])` keeps only the stores that trade *this* year. That is what
turned a naive +16.6% into +2.1% on the reference build (T42). Budget does not slice by cohort —
never build cohort × vs Budget.

**Rules — all TESTED on a real retail model:**

1. **No report measure references another.** DAX containing `[RM Something]` fails at render with
   *"The value for '<name>' cannot be determined. Either the column doesn't exist, or there is no
   current row for this column."* — and only when that other measure is not projected in the same
   visual, so a matrix works while a card breaks and it looks random (T20). Inline the base as a
   nested `VAR x = VAR … RETURN …` block; every `VAR` block ends in `RETURN`.
2. **`dataType` is `"Text"`, never `"String"`** — else the deploy payload fails schema validation
   (T21).
3. **Test each measure alone before deploying** (T24):
   `DEFINE MEASURE 'Measures'[RM X] = <expression> EVALUATE ROW("v", [RM X])` with only that one
   measure defined reproduces a single card's query. Defining them all together hides rule 1's bug.
4. **One source of truth.** Keep the DAX in one place (one file per measure under
   `docs/reference/measures/`, or one JSON of `name → expression`) and *regenerate*
   `reportExtensions.json` from it after every change — each entry becomes
   `{name, dataType, formatString, expression}`; then validate. Hand-editing the expression strings
   inside the JSON is how a working measure and a deployed measure drift apart.
5. **Never filter a visual on a report measure** (T22); rank inside the measure.
6. **Replace the holiday list, then keep it current.** `_Holidays` in `RM Basis Note` is a literal
   table because the model had no holiday flag. The template ships three placeholder dates (marked
   in the DAX) — replace them with your public holidays before the first deploy, extend the list
   each year (**UNTESTED** beyond the last date you list) and ask the model owner for the flag.
7. **Labels are computed at query time.** `TODAY() - _Cut` is the age of the load ("3 days ago").
   The model is Import mode refreshed by someone else; no report can show newer data than `_Cut`.
   Latest traded day = last day with loaded sales, never today (T44).

**Checks for Step 6.** With Week All / Day All every Step 2 value ties on the first page; the header
reads `Mon 24 Aug 2026 · Wk 35 · day 1/7 · 3 days ago` and the basis note
`LY = Mon 25 Aug 25 (public holiday — distorted) · LW = Mon 17 Aug`. A screen check is not optional:
the round-1 YTD tiles (a fifth of the real number, −81.8% — the calc-group `YTD` item summing only
Mondays under the day pin, T2) and the round-2 *"Something's wrong with one or more fields"* (cause
never recorded — the *See details* text was not captured, T23) both passed every offline check.

---

## Step 7 — The visual idioms actually used

One rule: **copy a visual that already works, then change only what the spec names.** A new visual
is a folder `definition/pages/<pageId>/visuals/<20 lowercase hex>/visual.json`; its `name` equals
the folder name; `position.z` and `tabOrder` are unique on the page; everything inside the
1280 × 720 canvas with a 16 px gutter; no visual overlaps another.

### 7.1 Single-value cards — the hero row

A `cardVisual` with one `Data` projection and seven formatting objects (`value`, `label`,
`accentBar`, `outline`, `padding`, `layout`, `spacing`), each with `"selector": {"id": "default"}`
(`references/card.md`). The two that carry meaning:

```json
"value": [{"properties": {"fontSize": {"expr": {"Literal": {"Value": "22D"}}}, "horizontalAlignment": {"expr": {"Literal": {"Value": "'left'"}}}, "labelPrecision": {"expr": {"Literal": {"Value": "1L"}}}, "labelDisplayUnits": {"expr": {"Literal": {"Value": "1000D"}}}}, "selector": {"id": "default"}}],
"label": [{"properties": {"show": {"expr": {"Literal": {"Value": "true"}}}, "text": {"expr": {"Literal": {"Value": "'Sales · latest day'"}}}, "fontSize": {"expr": {"Literal": {"Value": "10D"}}}, "horizontalAlignment": {"expr": {"Literal": {"Value": "'left'"}}}}, "selector": {"id": "default"}}]
```

Colours, fill and accent come with the copy (the theme lock, Step 8). Then: (1) change the
projection `Property`, `queryRef`, `nativeQueryRef` and `label.text`; (2) for a **model** measure
that must read the latest traded day, run `date_filters.py <visual.json> latest-day`; (3) for an
`RM ` measure add **no** date filter — it pins itself — and use the `Schema: "extension"` projection
of Step 5. The first build bound the year-to-date tile to `[Sales]` + the calc-group `YTD` item under
the day pin and summed only Mondays (T2).

A **delta card** is the same card at `fontSize 13D` with a calc-group filter (a visual-level
Categorical filter on `'Time Intelligence'[Time Intelligence]` = `'vs LY %'`, keeping `[Sales]`) and
a conditional font colour. The rule is per card and its `Left` is the card's own measure:
`docs/reference/snippets/conditional_font_colour.json` — `ComparisonKind` 1 = `>`, 3 = `<`; a `< 1D` guard
leaves the default colour on values ≥ 100%. A report-measure card carries
`"SourceRef": {"Schema": "extension", "Entity": "Measures"}` in both `Left` blocks; a model-measure
card has no `Schema` key. Use only the good/bad hex pair the approved theme already uses. **TESTED:**
red negative, green positive on the hero row.

### 7.2 Multi-value cards and their limits

A `cardVisual` with several measures in `Data`; per-measure text and format use a `selector.metadata`
entry keyed by `queryRef`:

```json
"label": [{"properties": {"show": {"expr": {"Literal": {"Value": "true"}}}, "fontSize": {"expr": {"Literal": {"Value": "9D"}}}}, "selector": {"id": "default"}},
          {"properties": {"text": {"expr": {"Literal": {"Value": "'Sales (inc tax)'"}}}}, "selector": {"metadata": "Measures.Sales"}}],
"value": [{"properties": {"fontSize": {"expr": {"Literal": {"Value": "18D"}}}, "labelDisplayUnits": {"expr": {"Literal": {"Value": "1000D"}}}, "labelPrecision": {"expr": {"Literal": {"Value": "1L"}}}}, "selector": {"id": "default"}},
          {"properties": {"labelDisplayUnits": {"expr": {"Literal": {"Value": "0D"}}}, "labelPrecision": {"expr": {"Literal": {"Value": "1L"}}}}, "selector": {"metadata": "Measures.Margin %"}}]
```

**Limits** (`references/card.md`; TESTED): `value`/`label` font, size, colour and alignment apply to every
callout alike, and the callout area only renders with two or more measures — one callout cannot be
sized alone. So the hero row (a 22-pt value beside 13-pt deltas) is single-value cards; a
multi-value card is for a row of equals.

### 7.3 Matrix with calc-group columns

`pivotTable`: `Rows` = `'Store'[Channel]`, `Columns` = `'Time Intelligence'[Time Intelligence]`,
`Values` = `[Sales]`, plus the day pins and a visual-level Categorical filter picking the items:

```json
"Values": [[{"Literal": {"Value": "'Current'"}}], [{"Literal": {"Value": "'LW'"}}], [{"Literal": {"Value": "'LY'"}}], [{"Literal": {"Value": "'vs LW %'"}}], [{"Literal": {"Value": "'vs LY %'"}}]]
```

Sort by `[Sales]` descending (`docs/reference/snippets/sort_definition.json`). Whole units via
`columnFormatting` with `labelPrecision 0L` and `selector.metadata = "Measures.Sales"`. Red/green
on the % columns uses the table selector shape — **both** `data` and `metadata` are required
(`references/conditional-formatting.md`):
`"selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}], "metadata": "Measures.Sales"}`.

Two limits, accepted in the spec: the column headers `Current` / `LW` / `LY` are calc-item **values**
and cannot be renamed in a matrix; and one `columnFormatting` entry per measure hits every calc-group
column, so the % columns show whole percent while cards show one decimal (a per-item `scopeId`
selector fix is **UNTESTED**).

### 7.4 Matrix on report measures (LFL)

`Rows` = `'Store LFL'[LFL Status]` renamed in place with `"displayName": "Store group"`; six
`RM LFL …` measures renamed the same way (`"LY, same stores"`, `"WTD"` …). **No day pins** — the
measures pin themselves. Blank rows (online has no cohort status) are removed with the not-blank
shape on that column. The % measures inline both bases as nested `VAR` blocks (6.5, rule 1).
**TESTED:** cohort-bridged LFL on screen equals the Step 2 value; each measure also ran alone.

### 7.5 `tableEx` P&L

Every projection carries a `displayName` header override (`docs/reference/snippets/projection_display_name.json`;
`[Net Sales ex Tax]` → `Net sales ex tax`). Fixed column widths:

```json
"columnWidth": [{"properties": {"value": {"expr": {"Literal": {"Value": "120D"}}}}, "selector": {"metadata": "Store.Channel"}},
                {"properties": {"value": {"expr": {"Literal": {"Value": "96D"}}}}, "selector": {"metadata": "Measures.Sales"}}]
```

Widths must sum to no more than the visual width or the table grows a horizontal scrollbar:
120 + 11 × 96 = 1176 ≤ 1248 (**TESTED:** all columns visible, no scrollbar). Precision per column
via `columnFormatting` (`0L` for currency, `1L` for %). Totals on: object **`total`**, property
**`totals`** — `"total": [{"properties": {"totals": {"expr": {"Literal": {"Value": "true"}}}}}]`
(not `show`). Sort `[Sales]` descending, `isDefaultSort: false`. Red/green on the % columns only; the
total row stays uncoloured.

### 7.6 Combo chart — budget as a line on the **same** axis

`lineClusteredColumnComboChart`: `Category` = `'Date'[Date]`; `Y` = `[Sales]` (`displayName`
`This year`) and `RM LY Sales by Day` (`Last year`); `Y2` = `[Budget Sales]` (`Budget`), which lands
on a secondary axis by default. One scale:

```json
"valueAxis": [{"properties": {"start": {"expr": {"Literal": {"Value": "0D"}}}, "secStart": {"expr": {"Literal": {"Value": "0D"}}}, "alignZeros": {"expr": {"Literal": {"Value": "true"}}}, "secShow": {"expr": {"Literal": {"Value": "false"}}}, "showAxisTitle": {"expr": {"Literal": {"Value": "false"}}}, "labelDisplayUnits": {"expr": {"Literal": {"Value": "1000D"}}}, "labelPrecision": {"expr": {"Literal": {"Value": "0L"}}}}}]
```

`secShow` came from `powerbi-report-author formatting describe-object lineClusteredColumnComboChart
valueAxis` (Part 2, 2.4). Data labels on one series only — `showAll` switches on per-series control,
then each hidden series gets `showSeries false`:

```json
"labels": [{"properties": {"show": {"expr": {"Literal": {"Value": "true"}}}, "labelDisplayUnits": {"expr": {"Literal": {"Value": "1000D"}}}, "labelPrecision": {"expr": {"Literal": {"Value": "0L"}}}, "showAll": {"expr": {"Literal": {"Value": "true"}}}}},
           {"properties": {"show": {"expr": {"Literal": {"Value": "false"}}}, "showSeries": {"expr": {"Literal": {"Value": "false"}}}}, "selector": {"metadata": "Measures.RM LY Sales by Day"}},
           {"properties": {"show": {"expr": {"Literal": {"Value": "false"}}}, "showSeries": {"expr": {"Literal": {"Value": "false"}}}}, "selector": {"metadata": "Measures.Budget Sales"}}]
```

Legend on, `position 'Top'`, `showTitle false` — so the words "Time Intelligence" never show. Date
window: `window-weeks` (6.3). **TESTED:** one axis, a budget line, labels on this-year columns only.

Two on-screen-only failures on this visual: round 1 used the date-column window with the calc
group and drew the weekly LY total on every day (T3); round 2 rendered *"Something's wrong with one
or more fields"* with a cause that was never recorded — read the *See details* text in the `.txt`
snapshot before touching JSON (T23). The same visual with a channel filter is the single-channel
trend on the stores page.

### 7.7 Scalar (continuous) date axis for short dates

`columnChart` with `Category` = `'Date'[Date]` and `Series` = `'Store'[Channel]`:
`"categoryAxis": [{"properties": {"axisType": {"expr": {"Literal": {"Value": "'Scalar'"}}}, "fontSize": {"expr": {"Literal": {"Value": "9D"}}}, "showAxisTitle": {"expr": {"Literal": {"Value": "false"}}}}}]`.
**TESTED:** the axis reads `10 Aug … 24 Aug` where the `'Categorical'` version printed the long date
cut off mid-word. The combo above it stays categorical (room for two-line dates).

### 7.8 Bar charts sorted by a Tooltips measure

`Y` = `[Sales vs Budget %]`, `Tooltips` = `[Sales]`, sort on the tooltip measure
(`docs/reference/snippets/sort_definition.json` with `"isDefaultSort": false`). Bars run by sales size, not
by the plotted percentage (**TESTED**). Bar colour is a `dataPoint.fill` conditional with
`"selector": {"data": [{"dataViewWildcard": {"matchingOption": 0}}]}` and **no** `metadata` — charts
must not carry it (`references/conditional-formatting.md`).

### 7.9 Bottom-10 by a rank measure, not `TopN`, when slicers exist

Bind `Y` to `RM Bottom 10 vs Budget` (`docs/reference/measures/rm_bottom10_vs_budget.dax`):

```
VAR _r = RANKX(FILTER(ALLSELECTED('Store'[StoreName]), [Sales] > 0), [Sales vs Budget], , ASC, DENSE)
RETURN IF(_r <= 10 && [Sales] > 0, [Sales vs Budget])
```

plus a visual-level Advanced filter `[Sales] > 0` (a **model** measure — allowed), the day pins,
`sortDefinition` ascending, labels `1000D`/`1L`, `categoryAxis.maxMarginFactor 40L` for long store
names. The two reasons are the 6.2 traps (T8, T22). Ranking only stores that traded also removed a
closed site that carried a budget and no sales from the top of the call list (T40).

### 7.10 Region charts on the clean region column

`Category` = `'Store'[Region]`, `Series` = the calc group filtered to `Current`, `LY`; the store
channels; the day pins; the not-blank shape on `Region`. The column with two spellings of one region
was dropped in Step 1 (T39). **TESTED on screen:** four regions, no blank band, footing to the league
total.

### 7.11 Data labels — `1000D` / `1L`

`"labelDisplayUnits": {"expr": {"Literal": {"Value": "1000D"}}}` shows thousands (`1.2K`);
`labelPrecision` `"1L"` = one decimal, `"0L"` = none; `D` = double literal, `L` = integer literal
(`powerbi-report-author expr encode` produces them). Used: cards `1000D`/`1L`; region and trend
charts `1000D`/`0L`; bottom-10 bars `1000D`/`1L`; tables `0L`; percentages `1L`. Every bar, column
and line chart: `"labels": [{"properties": {"show": {"expr": {"Literal": {"Value": "true"}}}}}]`.
Negatives with a leading minus everywhere, no brackets — two conventions on one page read as two
different numbers.

### 7.12 `mobile.json` — the phone layout

One file per visual, beside `visual.json`, position only (`docs/reference/snippets/mobile_layout.json`;
`$schema` `…/visualContainerMobileState/2.0.0/schema.json`, `position` `{x, y, z, height, width,
tabOrder}`). Page 1 is a 320-px column: day card, title, basis note, the hero cards at 78-px steps,
then the matrices and the budget bar; header shapes, slicers and the button get none. **TESTED
offline only** (validator 0 errors, deploy accepted); **UNTESTED on a phone** — verify in the mobile
app before claiming it.

---

## Step 8 — Theme rules: locked means locked

Standing order once the owner approves the look: no theme-file edits, no colour or font change,
*"not even for consistency"*. Allowed: layout, titles, labels, `displayName`, formats, data labels,
sort, filters, visuals **copied** from existing ones. Not allowed: `StaticResources/`, any new hex,
any `fontFamily`, `fontSize` values not already in use, series colours. Restyle proposals from a
review are recorded, not built.

How to check (TESTED on the final reference folder — theme byte-identical, zero new hex values,
`fontFamily` only in the copied header textboxes):

```sh
python3 scripts/check_report.py "ORG-Daily Trading.Report" --baseline report-template   # or --baseline "<approved original>.Report"
```

`--baseline` compares **every** file under `StaticResources/**` byte for byte and the sets of
`#RRGGBB` and `fontFamily` values under `definition/`. The template ships Microsoft's base theme at
`StaticResources/SharedResources/BaseThemes/CY26SU07.json`; a custom theme would sit under
`StaticResources/RegisteredResources/`, and the same check covers it. By hand, the equivalent is:

```sh
diff -r "ORG-Daily Trading.Report/StaticResources" "<baseline>/StaticResources" && echo IDENTICAL
comm -23 <(grep -rhoE "#[0-9A-Fa-f]{6}" "ORG-Daily Trading.Report/definition" | tr a-f A-F | sort -u) \
         <(grep -rhoE "#[0-9A-Fa-f]{6}" "<baseline>/definition" | tr a-f A-F | sort -u)   # must print nothing
grep -rho '"fontFamily": *"[^"]*"' "ORG-Daily Trading.Report/definition" | sort | uniq -c
```

---

## Step 9 — The loop

1. **Edit** the local folder — only the page folder you own; shared files only when the step says
   so.
2. **Validate**: `powerbi-report-author validate "ORG-Daily Trading.Report" --format json` (or
   `npx -y @microsoft/powerbi-report-authoring-cli validate …`). Gate: `data.errorCount: 0`. The
   finished reference report validated at 0 errors with 72 warnings, all understood: 71 ×
   `PBIR_FILTER_NAME_DUPLICATE_GLOBAL` — the `org*` filter names are reused on every visual **by
   design**, so `date_filters.py` can find and replace them — and 1 × `PBIR_SCHEMA_UNREACHABLE`
   (the schema URL is unreachable offline). Any other warning is new: read it.
3. **Snapshot**: `cp -r "ORG-Daily Trading.Report" .backup-round<N>` (gitignored, at the repo root).
4. **Deploy**: `python3 scripts/deploy_report.py "ORG-Daily Trading.Report"` →
   `Updated existing report 'ORG-Daily Trading' (id=…)`.
5. **Capture with a reload**: `python3 scripts/capture_pages.py <report-item-id> shots/round<N> 60 --headless`
   — navigates to the report URL first (page clicks in an open tab keep the **old** definition,
   T27), polls up to `--rail-wait` 45 s for the page rail (T34), then settles `60` s per page in
   its own persistent, signed-in Chromium profile, and writes `<n>-<page>.png` + `.txt` with digit
   and error-marker counts.
6. **Look** at every PNG against the spec's Done criteria and the "How to look" checklist
   (Part 1, 1.3); grep every `.txt` for `wrong`, `See details`, `(Blank)`.
7. **Fix** the local folder; go to 2.

Lean rule (Part 2, 2.8): one render pass per deploy, DAX batched into one query, no parallel agents
on the model. On *"Unable to load model due to reaching capacity limits"*: stop, wait at least
30 minutes, one light probe (T31).

---

## Step 10 — Verification levels and what each catches

Four levels. Each catches what the one before cannot.

| Level | Catches | Cannot see |
|---|---|---|
| **1 Offline JSON** | schema errors, overlaps, out-of-canvas, missing pins, theme drift, banned filters, saved slicer picks, report-measure cross-references | anything only the service resolves: field errors, phantom measure names |
| **2 DAX tie-out** | wrong numbers, the LY basis, measure bugs | layout, formats, labels |
| **3 Screenshots** | clipping, labels, sort, error tiles, wrong series, weekly values on a daily axis | slicer behaviour |
| **4 Slicer-state tests** in the live browser | blank pages, context-ignoring filters, sync, reset, persisted state | — |

**Level 2.** `scripts/validate.py --file query.dax`, pointed at the model the report binds to. Test
each report measure **alone** (6.5, rule 3); tie to the Step 2 table. The most useful single query
was the channel matrix in the visual's own context (Step 2, action 2).

**Level 3** caught, on the reference build: the year-to-date tile at a fifth of the real number; LY
columns drawn at weekly totals; the round-2 field error; the clipped basis note; 45 colliding combo
labels; a closed site at the top of the call list.

**Level 4 — the states to test, on every page** (all TESTED live on the reference build):

| State | How | Expect |
|---|---|---|
| Default | open the report | Week All / Day All = latest traded day: `Mon 24 Aug 2026 · Wk 35 · day 1/7 · 3 days ago` |
| One day | Day = a Wednesday | `Wed 19 Aug 2026 · Wk 34 · day 3/7`; basis note relabels LY to that Wednesday last year |
| One week | Week = `Last week` | the Sunday of last week, `day 7/7`; LY = that Sunday last year |
| Both | a Week pick, then the Day list | the Week pick narrows the Day list; a date pick keeps LY on the same weekday |
| Reset | the "Latest day" button | back to All/All |
| Other pages | pick on page 1, open page 3 | the pick followed (sync groups) |
| Reopen | close the tab, open the report again | All/All — `isPersistentUserStateDisabled` |

These states found the strict-single-select blank page (T11), the `TopN`-over-all-history and
report-measure-filter errors (T8, T22) and the scrambled weekday order (T14). Drive the picks by
script from the accessibility snapshot's element refs each run; the exact click recipe is
**UNTESTED** as written (Part 2, 2.5).

**Level 1 — the offline script.** The validator checks bounds but not overlaps; nothing checks the
theme, the pins or the slicers. `scripts/check_report.py` does, in seconds, with no tenant:

```
python3 scripts/check_report.py "ORG-Daily Trading.Report" --baseline report-template   # or "<original>.Report" when you cloned one
```

`--baseline` is the approved folder — `report-template` when you started from the template, the
original when you cloned an existing report; it enables the theme checks (byte-identical
`StaticResources/**`, no `#RRGGBB` or `fontFamily` outside it) and without it they are skipped with
a note. `--no-validator` skips the npx validator; `--allow-saved-selection` waives the slicer check.
`tests/test_guardrails.py` runs it against `report-template/` on every push.

On the reference build the equivalent ran 34 checks against the deployed definition and diffed the
`getDefinition` pull against the local folder (every part equal; the service re-serialises
textboxes, which is a no-op). Neither costs the model a query.

---

## Step 11 — Handover

**Backups.** One gitignored snapshot per round at the repo root: `.backup-round0/` (pre-build),
`.backup-round<N>/` before each deploy, and one before the polish round. Rollback = copy the
snapshot's `definition/` over the report folder, validate, deploy. Deploying a `.backup-*` folder
directly should also work, since `deploy_report.py` reads the name from `.platform` — **UNTESTED**.
Delete snapshots by hand when done.

**The handover note** (skeleton in Part 5, 5.7.3): item id, folder, page ids, snapshot names; every
mechanism claim tagged **TESTED (where: screenshot, DAX query, or on-screen)** or **UNTESTED**; the
decisions still owed and who owes them; the traps met. Facts without a "where" rot into folklore
inside a month.

**Spec updates.** The spec is the contract builders read: record corrections in place
(*CORRECTION after round 1 (TESTED …)*) and keep the Done criteria equal to the final screenshots.

**Requests for the model owner** — one sentence each, evidence attached, for the **owner** to send
(Part 1, 1.2, guardrail 7). From the reference build, genericised:

1. The weekday sort key on the Date table is wrong for most days, so weekday lists sort scrambled —
   please fix.
2. One region value is spelled two ways and the second spelling carries no budget; dozens of sites
   have a blank region — please recode.
3. A closed site code carries a daily budget with no sales while its replacement trades with no
   budget — please move the budget (inferred; confirm).
4. Is the online sales measure recognised on dispatch, not on order? The weekday/weekend pattern
   says so — please confirm the basis for the executive pack.
5. How is the daily budget phased? One channel's day budget equals its last-year actual for the
   same weekday to the unit.
6. One Date column errors when queried — please fix or drop it.
7. Longer term: a public-holiday flag on the Date table and a model like-for-like measure keyed to
   this year's cohort, so the report DAX for both can go.

**Nothing committed unless the owner asks** (guardrail 8). The report folder is on disk and
deployed; `config.yaml` is gitignored; run `python3 tools/secret_scan.py .` before any commit.

**Links.** The review page and the live report URL stay with the owner; the agent never shares them.
