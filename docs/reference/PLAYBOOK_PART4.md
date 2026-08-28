# Part 4 — Traps catalogue

Every trap here was met on one real build: an executive daily-trading report on a shared retail
Fabric tenant, rebuilt against a read-only semantic model. Nearly all of them passed the PBIR
validator; most passed a DAX tie-out too. They were caught on screen, or by one read-only query
written after the screen looked wrong. The few the validator or the deploy did catch (T15, T21)
are here because the message does not say what to change.

Open this part the moment a page looks wrong. Find the symptom in the index, read the cause, apply
the fix, then put the report back in the state named under **See it again** and look.

## 4.1 How to read this part

Each trap has the fields `CONTRIBUTING.md` asks for, plus a status line:

| Field | What it holds |
|---|---|
| **What the page showed** | The wrong thing, in the words on screen. |
| **What was true** | The right number or behaviour. |
| **Cause** | The mechanism, in one or two sentences. |
| **Fix** | The exact change: file, property, command. |
| **See it again** | The state to put the report in to reproduce it. |
| **Status** | **TESTED** — proven on screen or by read-only DAX on a real retail model, with the kind of artefact that proved it named. **UNTESTED** — plausible, not proven; the test that would settle it is named. |

Never upgrade a label without running the test. Live output beats this document.

Names used below are the **model contract** names from `docs/MODEL_CONTRACT.md`:
`'Date'[Date]`, `'Date'[TradingYear]`, `'Date'[TradingWeek]`, `'Date'[DayName]` (sorted by
`'Date'[DayNumber]`), `'Date'[WeekLabel]` (`This week`, `Last week`, `Wk 12 2026`),
`'Date'[HasSales]`; the calculation group `'Time Intelligence'` with items `Current`, `LW`, `LY`,
`vs LW %`, `vs LY %`, `YTD`, `YTD vs LY %`; model measures `[Sales]`, `[Budget Sales]`,
`[Orders Value]`; `'Store'[StoreName]`, `Fact[StoreKey]`. Report measures carry the `RM ` prefix and
their DAX lives in `docs/reference/measures/`. PBIR shapes named here are in `docs/reference/snippets/`. All figures
are illustrative.

Two terms used a lot:

- **Calc group** — the model's `'Time Intelligence'` calculation group: a table of time-shift
  rules that re-computes any measure. Its `LY` item re-points every day in context that has sales to
  *last trading year, same trading week, same day number*. It **replaces** filters on the calendar
  columns it shifts and **keeps** filters on every other column. Half of Part 4 follows from that
  sentence.
- **TopN filter** — a PBIR filter that keeps the top N values of one column, ranked by a
  *subquery* (a small query inside the filter). The subquery has its own filter context.

### Index

| # | Symptom in one line | Group | Status |
|---|---|---|---|
| T1 | Last-year value on a day visual is week-sized | Calc group and dates | TESTED |
| T2 | Year-to-date tile is a fraction of the truth | Calc group and dates | TESTED |
| T3 | Last-year columns flat across a daily trend chart | Calc group and dates | TESTED |
| T4 | Last week ties at day grain; last year only through the two pins | Calc group and dates | TESTED |
| T5 | A Date column in context blanks LY / LW | Calc group and dates | TESTED for the columns named |
| T6 | A page-level TopN filter | TopN filters | UNTESTED |
| T7 | TopN `OrderBy` on a Measure breaks the visual | TopN filters | Aggregation form TESTED |
| T8 | A "bottom 10" full of positive numbers, or empty under a slicer pick | TopN filters | TESTED |
| T9 | Slicer picks on the pinned column do reach the pin | TopN filters | TESTED |
| T10 | TopN returns fewer rows than asked | TopN filters | TESTED |
| T11 | The report opens blank | Slicers | TESTED |
| T12 | `(Blank)` in a dropdown | Slicers | TESTED |
| T13 | Week dropdown starts thirteen years ago | Slicers | TESTED |
| T14 | Weekday list in a scrambled order | Slicers | TESTED |
| T15 | Validator rejects a dropdown slicer's height | Slicers | TESTED (floor between 65 and 76 UNTESTED) |
| T16 | A colleague's slicer picks greet the next viewer | Slicers | TESTED |
| T17 | A synced slicer does nothing on the other pages | Slicers | TESTED |
| T18 | No way back to the default state | Slicers | TESTED |
| T19 | The page is stuck on one weekday, or blank on Monday morning | Slicers | TESTED |
| T20 | "The value for '…' cannot be determined" on one card, not on the matrix | Report measures | TESTED |
| T21 | Deploy payload fails schema validation on a measure | Report measures | TESTED |
| T22 | "Something's wrong with one or more filters" | Report measures | TESTED |
| T23 | "Something's wrong with one or more fields" | Report measures | UNTESTED cause |
| T24 | A measure passes in a batch query and fails on a card | Report measures | TESTED |
| T25 | Report measures ignore the slicers | Report measures | TESTED |
| T26 | A per-day measure shows one day's value in a card | Report measures | TESTED on one model |
| T27 | Screenshots show the previous build | Rendering and capture | TESTED |
| T28 | "Session not found" mid-capture | Rendering and capture | TESTED |
| T29 | The screenshot is of the wrong tab | Rendering and capture | TESTED |
| T30 | Every new navigation fails, in-page clicks work | Rendering and capture | TESTED |
| T31 | "Unable to load model due to reaching capacity limits" | Rendering and capture | TESTED |
| T32 | A login wall, or a page with no data, that looks valid | Rendering and capture | TESTED |
| T33 | Slow page loads kill the automation session | Rendering and capture | TESTED |
| T34 | The first capture after a deploy is empty | Rendering and capture | TESTED |
| T35 | A big negative "vs last year" on a normal day | Data quality | TESTED |
| T36 | Online sales collapse while online orders grow | Data quality | TESTED |
| T37 | Margin % does not match the two tiles beside it | Data quality | TESTED |
| T38 | Weekdays sort wrong everywhere | Data quality | TESTED |
| T39 | Two regions with almost the same name | Data quality | TESTED |
| T40 | A store with budget and no sales tops the call list | Data quality | TESTED |
| T41 | "vs budget" swings by weekday | Data quality | TESTED behaviour, cause UNTESTED |
| T42 | Like-for-like growth too good to be true | Data quality | TESTED |
| T43 | The total is short by one channel | Data quality | TESTED |
| T44 | "Latest day" is not today | Data quality | TESTED |
| T45 | Numbers look stale | Data quality | TESTED |
| T46 | A ratio measure ten times too big | Model quirks | TESTED |
| T47 | A value column that is mostly zero | Model quirks | TESTED |
| T48 | A bridge that does not foot by a few units | Model quirks | TESTED |
| T49 | Period-end measures blank on an open period | Model quirks | TESTED |
| T50 | A measure switcher needs a model table | Read-only model limits | TESTED |
| T51 | Measure DAX comes back blank from the query API | Read-only model limits | TESTED |

## 4.2 Calc group and dates

### T1 — A `'Date'[Date]` filter makes LY the whole last-year week

**What the page showed** — On a visual pinned to the latest traded day, `LY` read a number about
seven times the day's sales (illustrative: `[Sales]` 1,234,567, `LY` 8,400,000).
**What was true** — Last year's same weekday was of the same order as this year's day.
**Cause** — When the calc group shifts to `LY` it drops the `'Date'[Date]` filter and keeps only
the trading-week context, so `LY` = the full last-year week. Filters on *non-calendar* columns
(`DayName`, `WeekLabel`) survive the shift.
**Fix** — Never pin a day on `'Date'[Date]`. Run
`python3 scripts/date_filters.py <visual.json> latest-day`. It writes the two **day pins**: a
`TopN 1` on `'Date'[DayName]` and a `TopN 1` on `'Date'[WeekLabel]`, each ordered by
`Max('Date'[Date])` descending over rows where `HasSales = true`. With the pins, `LY` and `LW` tie
to the unit against a read-only query.
**See it again** — Put a `TopN 1` on `'Date'[Date]` on any card that also carries the calc item
`LY`. The card reads the week.
**Status** — TESTED (one batched query listing `[Sales]`, `LY` via the calc item and `LY` via a
report measure per date shows the calc-item column flat at the weekly total; the fixed matrix
ties on screen).

### T2 — The `YTD` calc item keeps the day pin and sums one weekday

**What the page showed** — Year-to-date tile at about a fifth of the real number, `−81.8%` vs
last year, when the year was `+14.2%`.
**What was true** — The full year to the latest traded day.
**Cause** — The `YTD` item widened the week but the `DayName` pin stayed, so the tile summed every
Monday of the year (the latest traded day was a Monday).
**Fix** — Bind cumulative tiles to report measures that clear the date filters themselves —
`RM YTD Sales`, `RM YTD vs LY %`, `RM YTD vs Budget %` — with **no** date filter on the visual
(`python3 scripts/date_filters.py <visual.json> none` strips the pins). The measures anchor on
`CALCULATE(MAX('Date'[Date]), 'Date'[HasSales] = TRUE)` and `REMOVEFILTERS('Date')`.
**See it again** — Bind a card to `[Sales]` plus the calc item `YTD`, add the day pins, look.
**Status** — TESTED (two screenshots: the wrong tile, then the fixed tile tying to the tie-out
table).

### T3 — A date-column trend window (`window-days`) turns LY into weekly totals

**What the page showed** — On a daily trend chart, the last-year columns printed the same weekly
total on every day of each week; only one weekday per week showed a day-grain value. The budget
line read daily values.
**What was true** — Last-year daily values of the same order as this year's bars.
**Cause** — A `TopN 14` on `'Date'[Date]` is a `'Date'[Date]` filter, so T1 applies at week grain.
(Why one weekday per week escaped is the T38 hypothesis: the model's day-number column was only
populated for that weekday.) A separate claim that the same window also makes `[Budget Sales]`
read as a weekly total has no screenshot behind it — **UNTESTED**; verify before repeating it.
**Fix** — `python3 scripts/date_filters.py <visual.json> window-weeks` = `TopN 3` on
`'Date'[WeekLabel]` plus a categorical `HasSales = true` filter, and the last-year series bound to
`RM LY Sales by Day` (a report measure that shifts by year, week and day name — no calc group
call). `this-week` is the same pair with `TopN 1`. `window-days` stays in the script for history
only; it is **banned** on any visual that uses the calc group.
**See it again** — Run `window-days` on a chart with `'Date'[Date]` on the axis and the calc item
`LY` as a series.
**Status** — TESTED for LY (screenshot before and after; the batched per-date query).

### T4 — LW works at day grain; LY at day grain works only through the two pins

**What the page showed / What was true** — The channel matrix's `LW` column equalled the same
weekday's actual one week earlier; its `LY` column equalled the same weekday of the same trading
week last year. Both to the unit.
**Cause** — `LW` shifts by seven days and needs nothing else. `LY` shifts by year, week and day
number, and only the non-calendar pins survive that shift.
**Fix** — None needed; this is the proof that the pin method works at day grain. An older note
from a different model of the same company said "vs LY only at completed-week grain" — that note is
superseded on the production model by the pins. Re-test on yours.
**See it again** — Day pins on a matrix with `Current`, `LW`, `LY` as columns; compare with
`python3 scripts/validate.py --file query.dax` for the same day.
**Status** — TESTED.

### T5 — Other Date columns in context can blank the calc group

**What the page showed** — `LY` and `LW` blank on visuals that filtered on a relative-week column
or put a non-calendar date column on the axis.
**Cause** — The calc group's shift re-points calendar columns; a non-calendar date column that
counts backwards (0 = this week, 1 = last week) is not re-pointed, so the shifted context matches
nothing. `FILTER(ALL('Date'))` inside a calc-group query broke it the same way. A chart whose
series uses the calc group must put a **calendar** column on its axis — a "week start date" axis
silently kills the `LY` series.
**Fix** — Pin only on `DayName` and `WeekLabel` (proven to survive); axis only `'Date'[Date]` or
`TradingWeek`; filter only calendar columns or the two pin columns.
**See it again** — Add a categorical filter on a relative-week column to any calc-group visual.
**Status** — TESTED for three columns (a relative-week column blanks; `DayName` and `WeekLabel`
survive). Any other column: prove it with one DAX row before you pin on it.

## 4.3 TopN filters

### T6 — TopN is visual-level only

**Cause** — The PBIR filter rules (`skills-for-fabric` `references/filters.md`, Part 2, 2.3;
copied into `docs/reference/snippets/README.md`) allow `TopN` only on a visual, not on a page or the report.
**Fix** — Put the pins on every visual that needs them; never on `page.json`.
**See it again** — Paste a day pin into a page's `filterConfig`, validate, render.
**Status** — Documented; UNTESTED on this build.

### T7 — `OrderBy.Expression` must be an `Aggregation`, not a `Measure`

**Cause** — The pins order by `Aggregation { Column 'Date'[Date], Function 4 }` (4 = Max). A
`Measure` in that slot errors in Desktop with `Cannot read properties of undefined (reading
'accept')` (`references/filters.md`).
**Fix** — Let `scripts/date_filters.py` write the shape. Direction `2` = top, `1` = bottom.
**Status** — Aggregation form TESTED (every page renders); the failure mode UNTESTED here.

### T8 — A TopN subquery does not inherit the visual's other filters

**What the page showed** — "Stores to call — bottom 10 vs budget" showed positive bars, and only
nine of them; with the week slicer on "Last week" it was empty.
**What was true** — Ten stores, all below budget, on the latest traded day.
**Cause** — The subquery ranks `'Store'[StoreName]` in its own context. The day pins and the
slicer picks on `'Date'` do not reach it, so it ranked over all history and then displayed the
result for the pinned day.
**Fix** — Delete the store `TopN`. Put the rank inside a report measure and sort the visual by it:

```
RM Bottom 10 vs Budget =
RANKX(FILTER(ALLSELECTED('Store'[StoreName]), [Sales] > 0), [Sales vs Budget], , ASC, DENSE)
```

blank outside the range. Keep an advanced filter `[Sales] > 0` on the visual so closed sites drop
out (T40).
**See it again** — A store `TopN 10` ascending on `[Sales vs Budget]` plus the day pins; move the
week slicer.
**Status** — TESTED (screenshot of the wrong list; screenshot after the fix; slicer-state pass).

### T9 — Slicer picks on the pinned column DO flow into the pin

**What the page showed** — Day slicer = Wednesday → the header read that Wednesday, "day 3/7", and
LY was re-labelled to the matching Wednesday last year. Week slicer = Last week → the last traded
day of that week, "day 7/7".
**Cause** — The `TopN 1` on `'Date'` picks the latest traded day *within* the slicer context,
because the slicer filters the same table the subquery ranks.
**Fix** — None; this is the behaviour the settings strip depends on. It is also why the report
measures use a cut-off without `ALL` (T25).
**Status** — TESTED (slicer-state screenshots).

### T10 — A TopN subquery must be self-contained

**What the page showed** — A top-10 with fewer rows than ten, or none.
**Cause** — Conditions placed outside the subquery (a week flag, a threshold) rank in the wrong
context, then intersect with the visual's other filters.
**Fix** — Put every condition inside `Subquery.Query.Where`. The day pins carry `HasSales = true`
inside for this reason.
**Status** — TESTED (an earlier report on the same tenant).

## 4.4 Slicers

### T11 — `strictSingleSelect: true` with no saved selection blanks the page

**What the page showed** — Both dropdowns read `(Blank)`; the day card read "· Week · day of 7";
every card `--`; "Visuals are loading…" that never finished.
**Cause** — Strict single-select auto-picks the first item when nothing is selected. The first
item of a Date-column dropdown is `(Blank)`. The PBIR CLI says so in one line:
`powerbi-report-author formatting describe-property slicer selection strictSingleSelect`.
**Fix** — `objects.selection`: `singleSelect` true, `strictSingleSelect` false,
`selectAllCheckboxEnabled` false; no saved selection. "All" then means the latest traded day.
**See it again** — Set `strictSingleSelect` true on a slicer with no `objects.general` filter,
deploy, open.
**Status** — TESTED (accessibility text of the blank state; screenshot of the fixed state).

### T12 — Blank members appear in the list

**Fix** — An advanced "not blank" filter on the slicer field:
`Not(Comparison ComparisonKind 0, <column>, Literal "null")`. Use the same shape on any category
column with unmapped rows (a region column, a cohort column).
**Status** — TESTED (`(Blank)` absent in the accessibility text after the fix).

### T13 — The week label lists every week since the model's first year, oldest first

**What the page showed** — A week dropdown starting thirteen years ago.
**Cause** — `'Date'[WeekLabel]` sorts by a year-and-week key, ascending.
**Fix** — A visual `TopN 13` on `WeekLabel` ordered by `Max('Date'[Date])` descending over
`HasSales` rows, plus `query.sortDefinition` Descending with `isDefaultSort: false`. Result:
`This week, Last week, 2 weeks ago, Wk 32 2026…`.
**Status** — TESTED (screenshot with "This week" picked).

### T14 — `DayName` sorts by a broken `DayNumber`, so weekday lists come out scrambled

**Cause** — The model's day-number column was wrong (T38), and `DayName` sorts by it.
**Fix** — Put the Day slicer on `'Date'[Date]` itself, descending, `TopN 91` traded days. Dates
need no sort column, and a date pick keeps `LY` on the same weekday.
**Status** — TESTED (a picked date re-labelled `LY` to the same weekday last year).

### T15 — Dropdown slicer height floor

**What the validator said** — `PBIR_SLICER_HEIGHT_BELOW_FLOOR` at height 64.
**Cause** — With a header, the validator wants roughly header 28 + selector 32 + padding. The
`skills-for-fabric` `references/slicers.md` gives `h = 60 + top padding + bottom padding`, snapped up to 8 px.
**Fix** — Height 76 with 0/0 top/bottom padding passes.
**Status** — TESTED (76 passes at `errorCount 0`; 64 fails). The exact floor between 65 and 76 is
UNTESTED.

### T16 — The service re-applies the last user's slicer picks on open

**Cause** — Persistent user state is on by default. "The default state is the product" stops
being true the first time somebody picks a week.
**Fix** — `report.json` → `"settings": { "isPersistentUserStateDisabled": true }`.
**See it again** — Pick a week, close the tab, reopen.
**Status** — TESTED live.

### T17 — Synced slicers need a copy on every page

**Cause** — `syncGroup { groupName, fieldChanges: true, filterChanges: true }` links slicers; it
does not place them.
**Fix** — Every page carries its own settings strip (Week + Day slicer, reset button, day card,
basis note) at the same positions. Group names `WeekSync` / `DaySync`.
**Status** — TESTED (a pick on page 1 followed to page 3).

### T18 — Reset needs a button

**Fix** — An `actionButton` whose `visualContainerObjects.visualLink` has `show` true and `type`
`'ClearAllSlicers'`. Label it "Latest day", not "Reset".
**Status** — TESTED (screenshot after the click: All/All).

### T19 — A saved literal selection goes stale

**What the page showed** — The original report was stuck on one weekday from Tuesday onward, and
blank on Monday mornings before the load landed.
**Cause** — The Day slicer saved `'Monday'` in `objects.general[].properties.filter`, and the week
slicer saved a `TODAY()`-based label ("This week").
**Fix** — No saved selection anywhere; the day pins choose the day. Make the offline check
(`scripts/check_report.py`) fail on any slicer with a saved selection.
**Status** — TESTED (screen; the original visual's JSON).

## 4.5 Report measures (`reportExtensions.json`)

### T20 — Report measures must not reference each other

**What the page showed** — *"The value for '<name>' cannot be determined. Either the column doesn't
exist, or there is no current row for this column."* on a single-measure card — while a matrix
showing both measures rendered fine.
**Cause** — The service injects report measures as `DEFINE MEASURE` per visual query. A reference
to another report measure resolves as a column unless that measure happens to be projected in the
same visual. That is why it looks random.
**Fix** — Inline the base DAX as nested `VAR x = VAR y = … RETURN y` blocks. Two sub-traps: a
`VAR` block must end in `RETURN`, so a derived measure that was a bare expression (`[A] - [B]`)
needs one adding; and see T21.
**See it again** — Bind a card to a report measure whose DAX contains `[Another RM measure]`.
**Status** — TESTED (measured live on a deployed report).

### T21 — `dataType` must be `"Text"`, not `"String"`

**Cause** — `"String"` is not a valid value; the deploy payload fails schema validation.
**Status** — TESTED.

### T22 — A visual-level filter on a report measure is rejected at render

**What the page showed** — *"Something's wrong with one or more filters. See details / Fix this"*.
**Cause** — Extension measures cannot be filter fields.
**Fix** — Move the logic inside the measure (rank, threshold), leave the visual's filters alone
(T8). Make the offline check fail on any filter whose field is `Schema: "extension"`.
**Status** — TESTED (screenshot).

### T23 — "Something's wrong with one or more fields"

**What the page showed** — The error on one combo chart, spinners on every other visual.
**Cause** — Not recorded. The visual's JSON was byte-identical to a snapshot that rendered clean
before and after; a capacity throttle began minutes later (T31). The "See details" text was not
captured.
**Fix** — On recurrence: read "See details" in the accessibility text **first**; confirm every
projected `RM ` name exists in `reportExtensions.json`; then wait out any throttle. Do not edit JSON
on suspicion.
**Status** — UNTESTED cause. The name check is free — put it in the offline check.

### T24 — Test each measure ALONE

**Cause** — Defining all report measures in one `DEFINE` block hides T20, because the referenced
measure is then in scope.
**Fix** —

```
DEFINE MEASURE 'Measures'[RM X] = <expression>
EVALUATE ROW("v", [RM X])
```

one measure per query, via `python3 scripts/validate.py --file q.dax`. This reproduces the card's
query exactly.
**Status** — TESTED.

### T25 — The cut-off date must not use `ALL`

**Cause** — `_Cut = CALCULATE(MAX('Date'[Date]), 'Date'[HasSales] = TRUE)` respects the slicers,
so WTD / YTD / like-for-like / the header labels follow a week or day pick exactly as the pins do
(T9). With `ALL('Date')` they would stay on the latest load whatever the reader picked.
**Fix** — No `ALL` in `_Cut`; cap the weekday list at `<= _Cut`.
**Status** — TESTED (slicer-state pass).

### T26 — A per-axis-point measure collapses inside an aggregate visual

**Cause** — `RM LY Sales by Day` starts with `VAR _d = MAX('Date'[Date])`. On a `'Date'[Date]`
axis that is one day; in a card or a donut it is the latest day.
**Fix** — Use it only where `'Date'[Date]` is on the axis.
**Status** — TESTED on one model of the same company; UNTESTED on the production model (test: drop
it in a card).

## 4.6 Rendering and capture

### T27 — Captures must reload the report after a deploy

**What the page showed** — Screenshots of the previous build.
**Cause** — Clicking page names in an already-open tab keeps serving the old definition.
**Fix** — `scripts/capture_pages.py` opens its own Chromium context and navigates to the report
URL first (`page.goto`), then polls up to `--rail-wait` 45 s for the page rail before the first
click.
**Status** — TESTED (every round).

### T28 — Browser automation sessions expire after 60–90 s (MCP-driven browser only)

**What the tool said** — `Session not found` part-way through a capture driven through a
Playwright MCP server.
**Cause** — A short-lived session against the browser server expires; a long capture outlives it.
**Fix** — Not an issue for the shipped `scripts/capture_pages.py`, which holds one Playwright
context for the whole run. Only if you drive the browser through an MCP server: one session per
step (select tab → click page → settle → snapshot → screenshot), re-created per page.
**Status** — TESTED (on the MCP setup of the reference build).

### T29 — The screenshot is of the wrong tab (MCP-driven or shared browser only)

**Cause** — Tab indexes shift, tab titles lie, and an automation layer may re-anchor on another
window.
**Fix** — The shipped script sidesteps it: its own persistent Chromium profile, one page,
`goto(URL)`, so there is no other tab to pick. Only if you drive a shared browser through an MCP
server: select the tab whose **URL contains the report item id**, never by title or index; open
one only if none exists; never close a tab you did not create.
**Status** — TESTED (on the MCP setup of the reference build).

### T30 — Every new navigation fails while in-page clicks still work

**What the tool said** — `net::ERR_TUNNEL_CONNECTION_FAILED` on `goto`.
**Cause** — A transient network or proxy outage between the browser and the service.
**Fix** — Wait. Do not debug the report.
**Status** — TESTED (observed once, cleared by itself).

### T31 — Capacity throttle

**What the page showed** — *"Unable to load model due to reaching capacity limits"* — on the new
report and on the original one other people were reading.
**Cause** — About two hours of four parallel DAX agents, six deploys and ~25 renders under one
identity on a shared capacity.
**Fix** — One render pass per deploy; DAX batched into one query; offline PBIR checks first; on
the message **stop and wait at least 30 minutes**, then one light probe. Never a refresh.
**Status** — TESTED (observed).

### T32 — Two browser endpoints with identical tool names (MCP-driven browser only)

*Only if you drive the browser through an MCP server.* The shipped `capture_pages.py` launches its
own signed-in profile, so it cannot hit this; it prints "Sign in in the browser window" and waits
instead.
**What the page showed** — A login wall, or a report with no data, that looked perfectly valid.
**Cause** — The automation was talking to a browser profile that was not signed in.
**Fix** — A login wall means "check which endpoint you are on" before it means "debug the page".
Deny the wrong endpoint in the agent's tool permissions.
**Status** — TESTED (on the MCP setup of the reference build).

### T33 — A short ping timeout kills any slow session (MCP-driven browser only)

*Only if you drive the browser through an MCP server.* Playwright for Python in the shipped script
has no ping timeout: `goto` waits up to 120 s and the rail poll up to `--rail-wait`.
**Cause** — The browser server's default ping timeout (5 s) closed sessions during 10–60 s page
loads.
**Fix** — Raise it in the server's environment (for Playwright MCP:
`PLAYWRIGHT_MCP_PING_TIMEOUT_MS=600000`). Do not bump versions chasing it.
**Status** — TESTED (navigations of 9 s and 58 s survived, on the MCP setup).

### T34 — First load after `updateDefinition` takes ~30 s

**Fix** — `capture_pages.py` polls up to `--rail-wait` seconds (default 45) for the page rail after
`goto`, then waits `settle` seconds per page (default 60, `capture.settle_seconds`; 60 was needed
on a busy tenant). Screenshots taken earlier show spinners, not bugs.
**Status** — TESTED.

## 4.7 Data quality patterns

None of these is a report bug. Each is a true number that tells a false story until its basis is
on the canvas or the model is fixed. Each ends in a request to whoever owns the model.

### T35 — Public-holiday LY

**What the page showed** — Latest day `−42%` vs last year; the outlet channel `−43%`.
**What was true** — Last year's comparator (same weekday, same trading week) was a public holiday.
Against the previous normal Monday the business was about flat. The following week the distortion
flips to a fake plus, because this year's holiday falls one trading week later.
**Fix** — `RM Basis Note` in the header prints the comparator date and flags it: `LY = Mon 25 Aug
25 (public holiday — distorted)`. The holiday list is a literal table inside the measure; keep it
current by hand. Model ask: a `'Date'[IsHoliday]` flag.
**Status** — TESTED (read-only query; the header on screen).

### T36 — Online sales are dated by dispatch

**What the page showed** — The online channel `−56%` week on week — the biggest red bar on the
page — while orders placed were `+27%`.
**What was true** — `[Sales]` for the online channel is recognised on shipment, so the latest day is
only partly loaded and the dip is timing, not lost trade. Orders placed (`[Orders Value]`) is the
same-day online signal.
**Fix** — An "Online orders (placed, inc tax)" matrix on `[Orders Value]` beside the sales matrix;
every title says "stores = till sales · online = dispatched".
**Status** — TESTED for the measure definitions (from the model's own descriptions). The
weekday/weekend shipping shape is an inference — confirm with the data team.

### T37 — Margin % base mismatch

**What the page showed** — Gross sales inc tax, cash margin, and `70.6%` side by side. Anyone
dividing the two tiles gets `44.7%`.
**What was true** — `[Margin %]` = margin ÷ **net sales ex tax**, a number that was not on the
page.
**Fix** — A margin row showing net sales ex tax, cash margin, and "Margin % of net sales", with the
base in the label.
**Status** — TESTED.

### T38 — A broken sort column

**What the page showed** — Weekday lists in a scrambled order (T14).
**What was true** — `'Date'[DayNumber]` was 0 for every weekday except one.
**Fix** — Work around in the report (T14). Model ask: fix the day-number column. Hypothesis worth
handing over: the calc group's `LY` keys on that column, which may be why only one weekday per
week escaped T3 — re-run the per-date query after the column is fixed.
**Status** — TESTED (one `EVALUATE VALUES(...)` on the column).

### T39 — Mis-coded regions

**What the page showed** — Two region bars with almost the same name; one tiny.
**What was true** — A legacy region column held two spellings of one region (a dozen stores under
the second spelling, with no budget), dozens of sites with a blank region, and a region with no
sales at all. A cleaner region column existed on the same table.
**Fix** — Use the clean column plus a not-blank filter (T12); check that the region chart foots to
the store league total. Model ask: recode the legacy column.
**Status** — TESTED (region chart foots to the league table).

### T40 — Budget keyed to a closed site

**What the page showed** — A site with last-year sales and a daily budget, but no sales this year,
topping "stores to call" with the biggest shortfall.
**What was true** — The site had closed or relocated; its successor code traded with no budget.
**Fix** — Rank only stores with `[Sales] > 0` (T8). Model ask: move the budget to the new code.
**Status** — TESTED (the site gone from the list after the fix).

### T41 — Budget phasing

**What the page showed** — Stores `+34%` vs budget on a Monday; a Monday budget lower than any
normal Monday's actual; the online Monday budget almost equal to its public-holiday LY.
**What was true** — The daily budget is the weekly budget blown down to days on a daily profile, so
day-level "vs budget" is partly calendar.
**Fix** — Titles say "daily budget = annual budget phased by day"; the basis note flags it.
**Status** — TESTED that the numbers behave so. "Phased on last year's daily profile" is a
hypothesis for the finance team.

### T42 — A like-for-like cohort table keyed by store-and-year

**What the page showed** — Store like-for-like `+16.6%`.
**What was true** — `+2.1%`. The cohort table joins on a store-**year** key, so a plain cohort
matrix compares this year's cohort with last year's cohort, not the same stores.
**Fix** — `RM LFL LY` bridges this year's stores onto last year:

```
VAR _S = CALCULATETABLE(VALUES(Fact[StoreKey]), REMOVEFILTERS('Date'), 'Date'[TradingYear] = _Y)
RETURN CALCULATE([Sales], REMOVEFILTERS('Store LFL'), TREATAS(_S, 'Store'[StoreKey]), …)
```

Budget does not slice by cohort — never show cohort × vs budget. Model ask: a like-for-like measure
keyed to this year's cohort.
**Status** — TESTED (prototype as `DEFINE MEASURE`, then the matrix on screen).

### T43 — A channel silently dropped

**What the page showed** — A day total short by about 5%.
**What was true** — The report-level channel filter listed four channels; every visual asked for
five. The report filter wins, so the fifth was dropped everywhere with no error.
**Fix** — The report-level filter lists all five; the total shows a row per channel. Check this
**before** the tie-out, or the tie-out will agree with the wrong number.
**Status** — TESTED.

### T44 — "Latest day" is the last day with loaded sales, never today

**Cause** — An import-mode model refreshed by someone else. No report can go past its last load.
**Fix** — `RM Day Label` prints the lag: `Mon 24 Aug 2026 · Wk 35 · day 1/7 · 3 days ago`. The
reader sees the age; the builder never chases "today".
**Status** — TESTED.

### T45 — Numbers look stale

**What the page showed** — A flat week, or last week's numbers on a Monday.
**Cause** — The model's last refresh, or the data pipeline's last load date, lags. The two lag
differently: the model can be refreshed on time against a source that is two weeks behind.
**Fix** — `python3 scripts/refresh.py --history` for the refresh date; `EVALUATE ROW("d",
CALCULATE(MAX('Date'[Date]), 'Date'[HasSales] = TRUE))` for the load date. Put the age on the
canvas (T44). The fix is **never** a refresh you trigger.
**Status** — TESTED.

## 4.8 Model quirks seen on the same model, worth checking on yours

### T46 — A ratio measure whose denominator spans all history

**What the page showed** — A "weeks cover" measure about eight times too big.
**Cause** — Its denominator averaged over every calendar day in the Date table, not the last full
week.
**Fix** — Use the measure defined over the last full week; read the DAX before you trust a ratio.
**Status** — TESTED.

### T47 — A value column that is mostly zero

**What the page showed** — Stock value near zero on every page.
**Cause** — 94% of stock units carried a zero cost; retail-value columns were 100% zero.
**Fix** — Report units only until the model is fixed. One `COLUMNSTATISTICS()` or a
`COUNTROWS(FILTER(...))` per value column before you bind it.
**Status** — TESTED.

### T48 — A bridge that does not foot by a few units

**Cause** — `DIVIDE` over fixed-decimal (currency) measures stays currency-typed at four decimals
and leaks pennies across a multi-step bridge.
**Fix** — Append `+ 0.0` to force double before dividing.
**Status** — TESTED (a real reconciliation hole closed by it).

### T49 — Period-end measures blank on an open period

**Cause** — Measures built on `LASTDATE('Date'[Date])` (closing stock, weeks cover) are blank
unless the period's last date has rows; stock posts weekly.
**Fix** — Show them for a completed trading week; say so in the title.
**Status** — TESTED.

## 4.9 Read-only model limits

### T50 — A measure switcher needs a model table

**Cause** — A field parameter is a calculated table in the semantic model; `reportExtensions.json`
can only add measures.
**Fix** — Use the calc group as the switcher: a slicer on `'Time Intelligence'` re-expresses every
measure on the page. To use field parameters, add the table to a model **you own** (`ORG-` copy)
and bind via `queryState.<role>.fieldParameters`.
**Status** — TESTED (the block; the calc-group switcher).

### T51 — Measure DAX comes back blank from the query API

**Cause** — `executeQueries` blanks `[Expression]` and `[FormatString]` on
`INFO.VIEW.MEASURES()` and rejects `INFO.CALCDEPENDENCY()`.
**Fix** — Measure DAX comes only from the TMDL export (`python3 scripts/discover.py` → `schema/`).
The INFO views are still good for `[State]`, relationship cardinality and inventory.
**Status** — TESTED.

## 4.10 Appendix A — snippets and DAX

Verbatim PBIR shapes are in `docs/reference/snippets/`, one file per shape; report-measure DAX is in
`docs/reference/measures/`, one file per measure, contract columns only. Which trap each answers:

| Shape or measure | Answers |
|---|---|
| the two day-pin `TopN 1` filters | T1, T3, T6–T10 |
| the `HasSales = true` categorical filter | T3 |
| the "not blank" advanced filter | T12 |
| slicer `objects.selection` + `syncGroup` | T11, T17 |
| the `ClearAllSlicers` action button | T18 |
| `report.json` `settings.isPersistentUserStateDisabled` | T16 |
| `reportExtensions.json` shell (`"Schema": "extension"` references) | T20–T24 |
| `RM Day Label`, `RM Basis Note` | T35, T44, T45 |
| `RM WTD …`, `RM YTD …` | T2, T25 |
| `RM LY Sales by Day` | T3, T26 |
| `RM Bottom 10 vs Budget` | T8, T22, T40 |
| `RM LFL LY` | T42 |

## 4.11 Appendix B — commands cheat-sheet

```
# discover, read-only
python3 scripts/discover.py                                    # ids + TMDL -> schema/
python3 scripts/validate.py --file query.dax                   # one batched query
python3 scripts/refresh.py --history                           # read only; never --trigger

# author
python3 scripts/date_filters.py <visual.json> latest-day       # day visuals on model measures
python3 scripts/date_filters.py <visual.json> window-weeks     # trend charts (Date on the axis)
python3 scripts/date_filters.py <visual.json> this-week        # week-to-date-by-day matrix
python3 scripts/date_filters.py <visual.json> none             # RM YTD cards: no date filter
powerbi-report-author formatting describe-object <visualType> <object>   # never guess a property

# check, offline
powerbi-report-author validate "ORG-Daily Trading.Report" --format json  # data.errorCount must be 0
python3 scripts/check_report.py "ORG-Daily Trading.Report" --baseline report-template   # overlaps, bounds, pins, banned filters; theme vs the template (or "<original>.Report" when you cloned one)
python3 tests/test_guardrails.py
python3 tools/secret_scan.py .

# ship and look
cp -r "ORG-Daily Trading.Report" .backup-roundN/
python3 scripts/deploy_report.py "ORG-Daily Trading.Report"                # first time: add --bind (definition.pbir from config.yaml)
python3 scripts/capture_pages.py 00000000-0000-0000-0000-000000000000 captures/roundN 60 --headless   # first run without --headless: sign in
grep -iE "wrong|see details|\(Blank\)" captures/roundN/*.txt
```
