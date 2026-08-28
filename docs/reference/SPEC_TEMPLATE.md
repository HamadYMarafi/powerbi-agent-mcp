# ORG-<Report name> — build spec (<YYYY-MM-DD>)

> Fill every `<…>`. Delete every line that starts with `>` when you are done — they are
> instructions to the writer, not to the builders. The spec is the builders' contract: an agent
> that cannot hit a number here reports it; it does not improvise. Figures below are illustrative.

**Folder:** `ORG-<Report name>.Report/` (a clone of `<original>.Report/`; the original is never
touched).
**Deployed item id:** `00000000-0000-0000-0000-000000000000` · **Workspace:** `<workspace name>` ·
**Bound to model:** `<model name>` (`00000000-0000-0000-0000-000000000000` — `semantic_model.id`
in `config.yaml`, or listed under `deploy.allowed_model_ids` only when the report binds to a
different model).
**Data to:** `<latest traded day, e.g. Mon 24 Aug 2026>` (trading week `<N>`), per
`CALCULATE(MAX('Date'[Date]), 'Date'[HasSales] = TRUE)`.
**Audience:** `<who judges the default view — e.g. Directors and the CEO. They will not touch a slicer.>`
**The one question:** `<e.g. Did we take budget on the latest traded day, and is the year on track?>`
**Greenlit by the owner:** `<date>`, findings `<F01–F24 or "all">`.

## Absolute rules (every builder)

1. **THEME LOCKED.** Do not edit `StaticResources/`. Do not add or change any colour (`fontColor`,
   `fill`, `dataPoint`, `color`, `backColor`…) or any `fontFamily` / `fontSize` beyond what an
   existing visual in this report already uses. Copying an existing visual brings its styling —
   fine. Never invent a colour.
2. **Touch only your page folder** `definition/pages/<your page id>/`. Never `report.json`,
   `pages.json`, `reportExtensions.json`, the theme, or another page.
3. **Header is done — do not move it.** Every page already has the settings strip: header shape
   `(0,0 1280×86)`, accent line, title textbox `(x20 y6 w430 h76 — edit only its text if this
   spec says so)`, Week slicer, Day slicer, "Latest day" button, day card bound to `RM Day Label`,
   basis card bound to `RM Basis Note`. Do not add slicers anywhere else.
4. **Date scope is per visual, never per page.** Run the helper; never hand-write a date filter:
   `python3 scripts/date_filters.py <visual.json> latest-day` for every latest-day visual on a
   model measure; `window-weeks` for trend charts with `'Date'[Date]` on the axis; `this-week` for
   a week-to-date-by-day matrix; `none` for cards bound to `RM WTD …` / `RM YTD …` (they pin
   themselves). **`window-days` is banned** — TESTED: a `'Date'[Date]` window makes the calc
   group's `LY` read the whole last-year week on every day.
5. **Model-pure first.** Model measures + the `'Time Intelligence'` calc group (items `Current`,
   `LW`, `LY`, `vs LW %`, `vs LY %`, `YTD`, `YTD vs LY %`) via a visual-level categorical filter on
   `'Time Intelligence'[Time Intelligence]` — copy the shape from `<page id>/visuals/<visual id>`.
   Use `RM ` report measures only where this spec names them, referenced with
   `"SourceRef": {"Schema": "extension", "Entity": "<measures table>"}` — copy the header card's
   projection.
6. **Copy shapes, don't invent JSON.** Sources, in order: this report's own visuals;
   `docs/reference/snippets/`; the `skills-for-fabric` `references/` (`card.md`, `table.md`, `cartesian.md`,
   `filters.md`, `slicers.md`, `textbox.md` — path in `docs/reference/PLAYBOOK.md` 2.3, the rules used here
   in `docs/reference/snippets/README.md`);
   `powerbi-report-author formatting describe-object <visualType> <object>` for any property you
   are not sure of.
7. **New visuals:** folder `visuals/<20 lowercase hex chars>/visual.json`, `name` = folder name,
   `$schema` copied from a sibling, unique `position.z` and `tabOrder`. Everything inside the
   1280×720 canvas with a 16-px gutter (x 16–1264). No visual may overlap another.
8. **Rename fields in place** — projection `displayName` (tables, matrices) or
   `objects.label[].properties.text` with `selector.metadata = "<queryRef>"` (cards). Plain
   English: `Gross sales (inc tax)`, `Net sales (ex tax)`, `Cash margin`, `Margin % of net sales`,
   `Online orders (placed, inc tax)`, `vs LY %`, `vs LW %`, `vs Budget %`. Never show the reader
   the words "Time Intelligence", "Current" or "Y2": legend title off, axis titles off, retitle.
9. **Number formats:** cards = thousands with one decimal (`labelDisplayUnits` `1000D`,
   `labelPrecision` `1L`); percentages one decimal; tables whole units; negatives with a leading
   minus, no brackets. Data labels ON on every bar, column and line chart. Sort tables and matrices
   by value descending (`query.sortDefinition`, copy from `<visual id>`).
10. **Validate 0 after every batch:**
    `powerbi-report-author validate "ORG-<Report name>.Report" --format json` →
    `data.errorCount: 0` (the CLI is `npm i -g @microsoft/powerbi-report-authoring-cli`; or run
    `npx -y @microsoft/powerbi-report-authoring-cli validate …`). Fix your own errors. Do not
    deploy — the main thread deploys and captures.
11. **Return, as your final text:** the list of visuals on your page (name → type → title →
    position) and anything you could not do, with the reason. Nothing else.

## Model facts you need

> Everything a builder would otherwise have to discover — or guess. Every value here was pulled
> read-only and dated. Keep it current: builders copy it, they do not re-query.

**Contract mapping** (`docs/MODEL_CONTRACT.md` → this model):

| Contract | This model | Note |
|---|---|---|
| `'Date'[Date]` | `<table>[<column>]` | calendar column; axis only |
| `'Date'[TradingYear]` / `[TradingWeek]` | `<…>` / `<…>` | |
| `'Date'[DayName]` | `<…>` | sorted by `<day-number column>` — `<works / broken, see data traps>` |
| `'Date'[WeekLabel]` | `<…>` | values `This week`, `Last week`, `Wk 12 2026`; sorted by `<key>` |
| `'Date'[HasSales]` | `<…>` | TRUE up to the last loaded sale day |
| `'Time Intelligence'` items | `<list>` | `<count>` items; only the seven above are used |
| `[Sales]` / `[Budget Sales]` / `[Orders Value]` | `<…>` | |
| `'Store'[StoreName]` / `Fact[StoreKey]` | `<…>` | |

**Channels** on the report-level filter (already set — must equal the visuals' list):
`<CHANNEL A, CHANNEL B, CHANNEL C, CHANNEL D, CHANNEL E>`.

**Measure bases:** `[Sales]` is `<inc/ex tax>` and `<before/after returns>`;
`[Net Sales ex Tax]` is after returns, ex tax; `[Margin %]` = `[Margin]` ÷ `[Net Sales ex Tax]`;
`[Returns Value]` is `<negative/positive>`-signed; `[Orders Value]` = online orders placed
(`<inc tax>`) — `[Sales]` for the online channel is dated by `<dispatch/order>`. Budget measures:
`<list>`. Volume and mix: `<list>`.

**Tested values (latest traded day, all channels, read-only DAX on `<date>`):** sales 1,234,567;
LW 1,300,000; LY 1,400,000 (`<comparator date — public holiday? yes/no>`); WTD 1,234,567 / LY
1,400,000 (−11.8%) / budget 1,350,000 (−8.6%); YTD 123,456,789 / LY 108,000,000 (+14.3%) / budget
100,000,000 (+23.5%); online orders placed 234,567; store like-for-like (cohort-bridged) 456,789 vs
447,000 (+2.2%).

**Report measures** (self-pinned, need NO date filter; DAX in `docs/reference/measures/`): `RM Day Label`,
`RM Basis Note`, `RM WTD Sales`, `RM WTD Sales LY`, `RM WTD Budget`, `RM WTD vs LY %`,
`RM WTD vs Budget %`, `RM YTD Sales`, `RM YTD Sales LY`, `RM YTD Budget`, `RM YTD vs LY %`,
`RM YTD vs Budget %`, `RM LY Sales by Day`, `RM Bottom 10 vs Budget` — the fourteen
`reportExtensions.json` ships. Optional, **not shipped**: `RM LFL TY`, `RM LFL LY`,
`RM LFL vs LY %` (only `docs/reference/measures/rm_lfl_ly.dax` exists — build the other two from it, and
only if `MODEL_CONTRACT.md` section 4's cohort pieces exist). `<add / remove to match
reportExtensions.json>`

**Clean columns to use:** region = `<clean region column>` (values `<…>`; + blank for unmapped —
filter it out), **not** `<legacy region column>`. Cohort = `<cohort table>[<status column>]`
(values `<…>`; blank = online / no store — exclude).

**Data traps** (already established; reuse, do not re-derive): `<holiday comparator on LY —
which dates>`; `<online sales dispatch-dated>`; `<margin base>`; `<daily budget phasing>`;
`<cohort table keyed store-year>`; `<broken sort column>`; `<mis-coded region members>`;
`<closed site carrying budget>`.

## Page 1 — `<page id>` "Today" (builder: page1)

> One section per page. For each visual: what to keep, what to delete, what to build, with the
> canvas row it lives in. Coordinates are the contract that stops two builders overlapping.

**Keep:** header (as is). **DELETE:** `<visual id>` (`<why — e.g. repeats the table>`).
**Keep and modify:** `<visual id>`.

**Build, top to bottom** (y in canvas px; heights include the visual title):

1. **Hero row, y 100–194 (h 94)** — three groups of single-value cards (copy the style of the
   header day card `<visual id>`; value 22 pt, deltas 16 pt):
   - "Latest day": `[Sales]` (label `Sales · latest day`, `latest-day` filters) — x16 w200;
     `[Sales]` + calc-group filter `vs LY %` (label `vs LY %`) — x222 w96;
     `[Sales vs Budget %]` (label `vs Budget %`, `latest-day`) — x324 w96.
   - "Week to date": `RM WTD Sales` — x438 w200; `RM WTD vs LY %` — x644 w96;
     `RM WTD vs Budget %` — x746 w96. No date filters.
   - "Year to date": `RM YTD Sales` — x860 w200; `RM YTD vs LY %` — x1066 w96;
     `RM YTD vs Budget %` — x1168 w96. **No date filters and no calc-group filter** (TESTED: the
     calc-group `YTD` item under a day pin sums one weekday). Expected: 123.5M / +14.3% / +23.5%.
   (Three groups of 200 + 96 + 96 with 6-px gaps inside and 18-px gaps between fill x 16–1264
   exactly.)
2. **Row 2, y 204–444 (h 240)**:
   - Left x16 w616: matrix `<visual id>` — rows `<channel column>`, columns calc group (`Current`,
     `LW`, `LY`, `vs LW %`, `vs LY %`), values `[Sales]`; `latest-day` filters; title
     `Sales by channel — latest day (stores = till sales · online = dispatched)`; sort by `Current`
     desc.
   - Right x648 w616: NEW matrix `Online orders (placed, inc tax) — latest day`: copy the left
     matrix, values `[Orders Value]`, channel filter `<online channels>`, same columns,
     `latest-day` filters.
3. **Row 3, y 454–708 (h 254)**:
   - Left x16 w760: NEW matrix `Stores like-for-like — latest day and week to date`: rows
     `<cohort column>` (filter: not blank; channels `<store channels>`), values `RM LFL TY`
     (`Sales`), `RM LFL LY` (`LY, same stores`), `RM LFL vs LY %` (the optional, not-shipped
     measures above — add them to `reportExtensions.json` first, or drop this matrix); sort by
     `Sales` desc; totals on. No date filters.
   - Right x792 w472: NEW bar chart `vs Budget % by channel — latest day`: copy `<visual id>`,
     Y `[Sales vs Budget %]`, category `<channel column>`, `latest-day` filters, data labels on.
4. **Phone layout:** `mobile.json` beside every data visual you keep on this page (shape from
   `docs/reference/snippets/`): a 320-px column — day card, title, basis note, hero cards stacked (320×70
   each, in the order above), then the matrices and the bar. Header shapes get no `mobile.json`.

## Page 2 — `<page id>` "Trend" (builder: page2)

**Keep:** header. **DELETE:** `<visual id>` (`<why>`).

1. **y 100–400 (h 300), x16 w1248:** combo chart — category `'Date'[Date]`, columns `[Sales]`
   and `RM LY Sales by Day` (**not** the calc item `LY` — TESTED: on a `'Date'[Date]` axis it
   returns the whole week), line `[Budget Sales]` on the **same** axis (`valueAxis.secShow`
   false, `alignZeros` true — check with `powerbi-report-author formatting describe-object
   lineClusteredColumnComboChart valueAxis`). Filters: `window-weeks`. Title `Sales by day — last
   3 trading weeks: this year vs last year vs budget`. Data labels on the this-year series only.
   Legend on, legend title off. Expected: `<N>` traded dates on the axis; last-year and budget
   per day of the same order as this year's bars.
2. **y 410–708 (h 298), x16 w1248:** matrix — columns `'Date'[Date]`, rows `<channel column>`,
   values `[Sales]`; `this-week` filters (no horizontal scrollbar); title `This week by day —
   sales by channel (Total = week to date)`; totals on.

## Page 3 — `<page id>` "Stores" (builder: page3)

**Keep:** header. **Existing:** `<visual ids>`.

1. **y 100–190 (h 90):** six single-value cards — for each store channel: `[Sales]` (label
   `<Channel> sales · latest day`), `[Sales]` + `vs LY %`, `[Sales vs Budget %]`; `latest-day`
   filters; channel filter per card.
2. **y 200–440 (h 240):** region charts at x16 w410 and x442 w410 — category `<clean region
   column>` + not-blank filter, series calc group (`Current`, `LY`) / Y `[Sales vs Budget %]`,
   store channels only, `latest-day` filters, data labels; titles `Regions — latest day vs LY` /
   `Regions — vs Budget % (latest day)`. Expected regions: `<list>`, no blank.
3. **y 450–708 (h 258):** NEW bar chart `Stores to call — bottom 10 vs budget (latest day)` at x16
   w410: category `'Store'[StoreName]`, Y `[Sales vs Budget]`, sorted by `RM Bottom 10 vs Budget`
   ascending, advanced filter `[Sales] > 0`, store channels, `latest-day` filters. **No store
   `TopN` filter** (TESTED: its subquery ignores the day pins). NEW column chart at x442 w410:
   `<Outlet channel> — last 3 trading weeks vs LY`: category `'Date'[Date]`, `[Sales]` and
   `RM LY Sales by Day`, `window-weeks`. Expected: ten bars, all negative.
4. League matrix `<visual id>` at x868 y200 w396 h508 — `Current`, `LY`, `vs LY %`; `latest-day`
   filters; title `Store league — latest day vs LY`.

## Page 4 — `<page id>` "Margin & Budget" (builder: page4)

**Keep:** header. **Existing:** `<visual ids>`.

1. **y 100–204 (h 104):** multi-value cards — Stores at x16 w620: `[Sales]` (`Gross sales (inc
   tax)`), `[Net Sales ex Tax]` (`Net sales (ex tax)`), `[Margin]` (`Cash margin`), `[Margin %]`
   (`Margin % of net sales`); store channels; `latest-day`. Online at x644 w620: `[Orders Value]`
   (`Orders`), `[Orders]` (`Orders #`), `[AOV]`, `[Orders vs Budget %]`; online channels;
   `latest-day`.
2. **y 214–430 (h 216):** channel charts at x16 w410 and x442 w410 (`latest-day`, data labels),
   and a "Volume & mix" column at x868 w396 of three cards (`[Units]`, `[Full-price mix %]`,
   `[Return rate]`), h 64 each with a 4-px gap.
3. **y 440–708 (h 268), x16 w1248:** `tableEx` `P&L by channel — latest day (daily budget =
   annual budget phased by day)`: rows `<channel column>`; columns with `displayName` overrides:
   `Gross sales`, `Returns`, `Net sales`, `Net sales ex tax`, `COS`, `Cash margin`, `Margin %`,
   `Budget`, `vs Budget %` (use the measure's own 1-dp % format); totals ON; `latest-day`; whole
   units; sort by `Gross sales` desc. Copy the `tableEx` shape from `docs/reference/snippets/`.

## Done criteria (main thread checks after deploy)

> One line of numbers per page. These are what the screenshots must show — the digits, not
> "about right". Keep them equal to the final screenshots.

- **Page 1:** hero 1,234.6K / −11.8% WTD vs LY / +14.3% YTD vs LY; channel matrix Total
  1,234,567 with a row per channel (`<count>` rows); orders matrix `<online channel>` 234,567;
  like-for-like 456,789 vs 447,000.
- **Page 2:** `<N>` dates on the axis, budget as a line on the same scale, no "Time Intelligence"
  legend title, no scrollbar on the matrix.
- **Page 3:** regions `<list>` only; bottom-10 bar has ten bars, all negative; the trend chart has
  `<N>` columns × 2 series.
- **Page 4:** stores card 789,012 gross · `<net>` · `<margin>` · `<margin %>`; the P&L foots.
- **Every page:** `data.errorCount: 0`; `scripts/check_report.py` clean; no overlaps; slicers only
  in the header, with no saved selection; header untouched; no new colours; theme byte-identical.

## Round-N fix list (from the main thread, after each screen pass)

> Corrections go here **and** in place above ("CORRECTION after round 1 (TESTED…)"). Builders read
> the section for their page; the list is the audit trail.

- **Round 1:**
  - Page 1: YTD cards → `RM YTD Sales` / `RM YTD vs LY %` / `RM YTD vs Budget %`, no filters
    (`<what the screen showed>`).
  - Page 2: every chart → `window-weeks`; the matrix → `this-week`. Retitle accordingly.
  - Page 3: bottom-10 → rank inside `RM Bottom 10 vs Budget`; drop the store `TopN`.
  - Page 4: the `Units` card label clipped — h 64 with a 4-px gap; `vs Budget %` showed `34.3`
    with no % sign — use the measure's own format.
- **Accepted as-is:** the matrix column headers `Current` / `LW` / `LY` are calc-item values from
  the model and cannot be renamed — leave them. Delta cards at 13 pt are fine.
- **Do not touch:** header cards (widened by the main thread). Negative numbers use a leading
  minus everywhere; do not add brackets.

## Review brief (the reviewers' shared input)

> Written before an exec review, from the same facts. Every lens gets this and nothing else, so
> disagreement is about meaning, not data. See Part 1, 1.4 and Part 5, 5.5.

- **What it is:** `<report, workspace, model, data to <day>>`; who built it; who has seen it; who
  judges it now; what it replaces.
- **PBIR digest:** for each visual, what it *really* queries — read from the JSON, not the title
  (report-level filters first: `<members>`; visual-level filters: `<members>` — flag any
  mismatch).
- **What is on screen today:** every number as text, per page, from the accessibility dumps.
- **Facts established from the model** (read-only DAX, dated), with every hypothesis marked
  "hypothesis".
- **Hard constraints:** model read-only; no refresh; PBIR-only changes; theme `<locked / open>`;
  "the audience will not touch slicers".
- **Already fixed** (do not re-report): `<list>`.
- **Attachments:** ground truth file; one PNG + one `.txt` per page.
