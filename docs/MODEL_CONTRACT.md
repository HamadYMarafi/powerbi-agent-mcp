# The model contract

What the semantic model must give the report. The report is read-only against the model: it
never adds a column, never triggers a refresh. Everything it cannot get from the model it computes
in `definition/reportExtensions.json` (the `RM ` measures) — but a few things must exist in the
model, and this file lists them.

Example names are used throughout the repo. Yours will differ. Map them once (section 8) and keep
the mapping in one place.

Labels: **TESTED** = proven on a real retail model during the original build; **UNTESTED** =
plausible, not proven, with the test that would settle it. Live output beats this file.

---

## 1. The Date table — required

Table `'Date'`, marked as the model's date table, one row per calendar day.

| Column | Type | Meaning | Sort by | Used for |
|---|---|---|---|---|
| `Date` | date | the calendar day | itself | the Day slicer list; trend-chart axes; **never** a filter on a pinned visual (trap T1/T3) |
| `TradingYear` | whole number | the fiscal/trading year the day belongs to | itself | `_Y` in every `RM ` measure; year to date |
| `TradingWeek` | whole number | the fiscal/trading week number inside `TradingYear` | itself | `_W` in every `RM ` measure; week to date |
| `DayName` | text | `Monday` … `Sunday` | `DayNumber` (next row) | **the day pin** (`orgLatestDayName`); the `LY`/`LW` shift keeps it |
| `DayNumber` | whole number | `1` = first trading day of the week … `7`; the sort column of `DayName` | itself | **optional by name**: nothing in the template binds to it, but the section 6 check (query 3) and the typical `LY` calc item key on it. If yours is called `DayOfWeek`, put it in the 8.2 recipe and in query 3 |
| `WeekLabel` | text | one label per trading week: `This week`, `Last week`, `2 weeks ago`, then `Wk 12 2026` … | a year-and-week key, oldest first (`TradingYear * 100 + TradingWeek` works) | **the week pin** (`orgLatestWeek`); the Week slicer; the trend windows |
| `HasSales` | true/false | `TRUE` on every day that has loaded sales, `FALSE` after the last loaded day | — | the anchor of everything: both pins, the slicer lists, every `RM ` measure |

**What "latest traded day" means.** The last day where `HasSales = TRUE`. Never today; never
yesterday if yesterday has not landed. Every pin and every `RM ` measure starts from
`CALCULATE(MAX('Date'[Date]), 'Date'[HasSales] = TRUE)` with **no `ALL`**, so it follows the Week
and Day slicers exactly as the pins do (TESTED).

**Two columns are calendar, four are not.** The calculation group (section 2) rewrites filters on
`Date`, `TradingYear` and `TradingWeek` when it shifts to `LY` or `LW`. Filters on `DayName`,
`WeekLabel` and `HasSales` survive the shift. That is the whole reason the pins sit on `DayName` +
`WeekLabel` and never on `Date` (TESTED — a `Date` filter under `LY` returns the whole last-year
week on every day).

**Watch the sort keys** (TESTED on the reference model, where they were broken): if the day-number
column is `0` for six days of the week, `DayName` sorts scrambled and the calc group's own day key
cannot tell days apart. Run the check in section 6 before you trust either.

**If a column is missing**, add it to a **copy** of the model that you own (prefixed `ORG-`),
never to a shared model. Illustrative calculated columns — **UNTESTED** as written, adapt to your
calendar (a 53-week year breaks the naive week arithmetic below):

```dax
HasSales = 'Date'[Date] <= CALCULATE(MAX(Fact[Date]), REMOVEFILTERS())

WeekKey = 'Date'[TradingYear] * 100 + 'Date'[TradingWeek]          -- sortByColumn for WeekLabel

WeekLabel =
VAR _y = LOOKUPVALUE('Date'[TradingYear], 'Date'[Date], TODAY())
VAR _w = LOOKUPVALUE('Date'[TradingWeek], 'Date'[Date], TODAY())
VAR _back = (_y - 'Date'[TradingYear]) * 52 + (_w - 'Date'[TradingWeek])
RETURN SWITCH(TRUE(), _back = 0, "This week", _back = 1, "Last week", _back = 2, "2 weeks ago",
              "Wk " & 'Date'[TradingWeek] & " " & 'Date'[TradingYear])
```

`WeekLabel` is computed from `TODAY()`, so "This week" can be a week with no sales yet (Monday
morning). That is fine: the pins and the slicer lists all filter on `HasSales`, so an empty week is
never selected by default.

## 2. The calculation group — required

Table `'Time Intelligence'`, column `'Time Intelligence'`, items:

| Item | Meaning | The report uses it for |
|---|---|---|
| `Current` | the measure as is | matrix columns |
| `LW` | same weekday, one week earlier (`'Date'[Date] - 7` over days with sales) | matrix columns |
| `LY` | last trading year, same trading week, same weekday number, over days with sales | matrix columns; the **vs LY %** hero card |
| `vs LW %` | `(Current - LW) / LW` | matrix columns |
| `vs LY %` | `(Current - LY) / LY` | the **vs LY %** hero card (a visual-level filter on this item, keeping `[Sales]`) |
| `YTD` | year to date | **not used under the day pins** — it sums only the pinned weekday (TESTED, trap T2). Year to date comes from `RM YTD …` |
| `YTD vs LY %` | year to date against last year | not used; same reason |

The one sentence the whole date mechanism rests on — read your `LY` item and confirm it:
*re-point the days in context that have sales to last trading year, same trading week, same
weekday; filters on the calendar columns are replaced, every other filter stays.* A calc group
that also replaces `DayName` or `WeekLabel` filters breaks the pins. Test in section 6.

A typical shape, for comparison (yours will differ — read it, do not assume it):

```dax
calculationItem LY = CALCULATE ( SELECTEDMEASURE (),
    TREATAS ( SELECTCOLUMNS ( FILTER ( 'Date', 'Date'[HasSales] = TRUE ),
                  "y", 'Date'[TradingYear] - 1, "w", 'Date'[TradingWeek], "dn", 'Date'[DayNumber] ),
              'Date'[TradingYear], 'Date'[TradingWeek], 'Date'[DayNumber] ) )
```

## 3. Model measures — required

| Measure | Meaning | Where the template uses it |
|---|---|---|
| `[Sales]` | the headline daily sales figure, on the basis the page states (tax in or out, returns signed — write it down) | the **Sales · latest day** card; under the calc group on the **vs LY %** card; inside every `RM ` sales measure |
| `[Budget Sales]` | budget on the same basis and grain as `[Sales]` | `RM WTD Budget`, `RM YTD Budget`, the `… vs Budget %` measures |
| `[Sales vs Budget]` | `[Sales] - [Budget Sales]` | `RM Bottom 10 vs Budget` |
| `[Sales vs Budget %]` | `DIVIDE([Sales] - [Budget Sales], [Budget Sales])` | the **vs Budget %** hero card |

The model needs **no** last-year, last-week or year-to-date measure: `LY` and `LW` come from the
calculation group, week and year to date from the `RM ` measures.

**The measure table.** The examples put these measures on a table called `'Measures'`. Two places
depend on that name: every projection in a visual (`"Entity": "Measures"`, `"queryRef":
"Measures.Sales"`) and the single entity in `reportExtensions.json`, which is where the `RM `
measures are attached. The entity must be a table that exists in your model; a measure's entity is
its home table.

**Budget grain.** If the daily budget is a weekly figure phased on last year's daily profile, say
so on the page (TESTED — it was, on the reference model, and nobody had labelled it).

## 4. Optional pieces

| Piece | Needed by | If you do not have it |
|---|---|---|
| `'Store'[Channel]` | the report-level filter placeholder `reportChannelScope` (channel not blank); the channel matrix and bar chart in the playbook | delete the filter from `definition/report.json` (`filterConfig.filters`) |
| `'Store'[StoreName]` + `[Sales vs Budget]` | `RM Bottom 10 vs Budget` (rank inside the measure) | delete that measure from `reportExtensions.json` |
| `'Store'[StoreKey]`, `Fact[StoreKey]`, a cohort table `'Store LFL'` keyed by store **and year** | like-for-like: `docs/reference/measures/rm_lfl_ly.dax` (not in the template) | skip like-for-like |
| a public-holiday flag on `'Date'` | the basis note | `RM Basis Note` carries a literal holiday list that ships as a **placeholder** (three illustrative dates, marked in the DAX) — replace it with your public holidays before the first deploy, then keep it current each year (**UNTESTED** beyond the dates you list) |

## 5. What the report never does

- Never a filter on `'Date'[Date]` on a pinned visual, and never a saved slicer value: the
  template ships with **no** `objects.general.filter` on either slicer (an absent filter lands on
  "All", TESTED) and `settings.isPersistentUserStateDisabled: true` in `report.json` (TESTED live —
  without it the service replays the last viewer's picks).
- Never a `TopN` on a store column beside the day pins (a `TopN` subquery ignores the visual's
  other filters, TESTED), and never a visual-level filter on an `RM ` measure (renders
  *"Something's wrong with one or more filters"*, TESTED). Rank inside the measure.
- Never an `RM ` measure that references another `RM ` measure (fails at render on a card, works in
  a matrix — looks random, TESTED). Inline the base as a nested `VAR … RETURN` block.

## 6. Contract check — read-only DAX

Run these before you draw a visual (`scripts/validate.py --file <query>.dax`, or any DAX client,
against the model the report will bind to). Batch them; they are reads.

```dax
-- 1. The latest traded day, its keys, its age (must be a real date; age in days)
EVALUATE
VAR d = CALCULATE(MAX('Date'[Date]), 'Date'[HasSales] = TRUE())
RETURN ROW("latest", d, "age_days", INT(TODAY() - d),
           "year", CALCULATE(MAX('Date'[TradingYear]), 'Date'[Date] = d),
           "week", CALCULATE(MAX('Date'[TradingWeek]), 'Date'[Date] = d),
           "day", CALCULATE(MAX('Date'[DayName]), 'Date'[Date] = d),
           "label", CALCULATE(MAX('Date'[WeekLabel]), 'Date'[Date] = d))

-- 2. The calc items exist with these exact names
EVALUATE 'Time Intelligence'

-- 3. The day sort key: one distinct number per weekday, 1..7 (a column of zeros = trap T38).
--    Replace 'Date'[DayNumber] with your DayName sort column if it is called something else.
EVALUATE SUMMARIZECOLUMNS('Date'[DayName], 'Date'[DayNumber], "days", COUNTROWS('Date'))

-- 4. WeekLabel sorts newest first when its sort column is descending; the first three rows read
--    This week / Last week / 2 weeks ago
EVALUATE TOPN(5, CALCULATETABLE(VALUES('Date'[WeekLabel]), 'Date'[HasSales] = TRUE),
              CALCULATE(MAX('Date'[Date])), DESC)

-- 5. The pins survive the LY shift: per channel, Current / LY / vs LY % for the latest day.
--    LY must be ONE day (same weekday last year), not a week total.
EVALUATE
VAR d  = CALCULATE(MAX('Date'[Date]), 'Date'[HasSales] = TRUE())
VAR dn = CALCULATE(MAX('Date'[DayName]),  'Date'[Date] = d)
VAR wk = CALCULATE(MAX('Date'[WeekLabel]), 'Date'[Date] = d)
RETURN SUMMARIZECOLUMNS('Store'[Channel], 'Time Intelligence'[Time Intelligence],
    TREATAS({dn}, 'Date'[DayName]), TREATAS({wk}, 'Date'[WeekLabel]),
    TREATAS({"Current", "LY", "vs LY %"}, 'Time Intelligence'[Time Intelligence]),
    "Sales", [Sales])

-- 6. Each report measure alone, exactly as a single card queries it (rule: never define them all
--    together — that hides a cross-reference). Paste the body from docs/reference/measures/.
DEFINE MEASURE 'Measures'[RM Day Label] = <expression>
EVALUATE ROW("v", [RM Day Label])
```

Expected: query 1 returns a date a day or two old; query 5's `LY` row for each channel equals
last year's same-weekday day total when you look it up by date (query it as a date — that is how
a public-holiday comparator shows itself).

## 7. What is in `report-template/`

A Fabric report item folder: `.platform`, `definition.pbir`, `definition/**`, plus Microsoft's
built-in base theme under `StaticResources/SharedResources/BaseThemes/` (no custom theme, no
company colours — every colour in `definition/` is `#000000` or `#FFFFFF`). Copy it, rename it,
give it a fresh `logicalId`, bind it, deploy.

| File | What to change |
|---|---|
| `.platform` | `displayName` (`ORG-Daily Trading Template` → yours); a **new** `logicalId` (all zeros ships; two items with one id collide) |
| `definition.pbir` | `byConnection` only — `python3 scripts/deploy_report.py "<folder>" --bind` writes the connection string from `config.yaml` (workspace name, model name, model id); or replace `<Workspace Name>`, `<Model Name>` and the zero `semanticmodelid` by hand. Until then the deploy script stops at its own guardrail. **Never `byPath`** (it would create a new semantic model) |
| `definition/report.json` | the `reportChannelScope` filter (section 4); keep `isPersistentUserStateDisabled: true` |
| `definition/reportExtensions.json` | the `RM ` measures (section 3 names); regenerate from `docs/reference/measures/` rather than hand-edit; the holiday placeholder in `RM Basis Note` (section 4) |
| `definition/pages/<id>/visuals/97e504e652a65d840fd6/visual.json` | the title textbox: its second paragraph is the basis line printed on the canvas and ships as `<channels> · <inc or ex tax> unless stated` — write yours (the reference build read `Stores & Online · inc tax unless stated`). A wrong basis here is the exact trap Part 1 warns about |
| every other `visuals/*/visual.json` | nothing, if the contract holds |

One page, **Today**, 1280 × 720, eleven visuals:

| Visual | `visualType` | x y w h | Bound to | Visual-level filters |
|---|---|---|---|---|
| header band | `shape` | 0 0 1280 86 | — | — |
| accent line | `shape` | 0 86 1280 3 | — | — |
| title | `textbox` | 20 6 430 76 | three text runs (title, basis line — a placeholder to fill, hint) | — |
| Week slicer | `slicer` | 462 6 120 76 | `'Date'[WeekLabel]`, dropdown, single-select not strict, no saved pick, sort descending, `syncGroup` `WeekSync` | `orgNotBlank`, `orgRecentWeeks` (`TopN 13`) |
| Day slicer | `slicer` | 588 6 170 76 | `'Date'[Date]`, same settings, `syncGroup` `DaySync` | `orgNotBlank`, `orgRecentDays` (`TopN 91`) |
| Latest day | `actionButton` | 766 26 90 36 | `visualLink.type = 'ClearAllSlicers'` | — |
| day card | `cardVisual` | 860 8 404 42 | `RM Day Label` (`Schema: "extension"`) | none — it pins itself |
| basis note | `cardVisual` | 860 50 404 34 | `RM Basis Note` | none |
| Sales · latest day | `cardVisual` | 16 100 196 94 | `[Sales]` | `orgLatestDayName`, `orgLatestWeek` |
| vs LY % | `cardVisual` | 218 100 100 94 | `[Sales]` under calc item `vs LY %` | `calcItemVsLY` + the two pins |
| vs Budget % | `cardVisual` | 324 100 100 94 | `[Sales vs Budget %]` | the two pins |

`scripts/date_filters.py` owns exactly five filter names — `orgLatestDayName`, `orgLatestWeek`,
`orgWindowWeeks`, `orgTradedDays`, `orgWindowDays` — and replaces only those on re-run. The slicers'
`orgNotBlank`, `orgRecentWeeks` and `orgRecentDays` share the marker by convention but are
hand-written (from `docs/reference/snippets/`) and the script never touches them; nor the calc-item filter.
The marker is `deploy.filter_marker` in `config.yaml` (default `org`) and is independent of the
item prefix.
Title, day card, basis note and the three hero cards carry a `mobile.json` (a 320-px column;
validated offline, **UNTESTED** on a phone).

**Validation.** `powerbi-report-author validate report-template --format json` (or
`npx -y @microsoft/powerbi-report-authoring-cli validate …`) → `data.errorCount: 0` with 5
warnings, all `PBIR_FILTER_NAME_DUPLICATE_GLOBAL`: the `org*` names repeat on every visual **by
design** so the script can find them. Any other warning is new — read it. The visuals declare the
`visualContainer/2.9.0` schema, the newest one published at the time of writing, so the validator
really checks them; Desktop writes newer versions (`2.11.0`) whose schema URL is not published, and
for those the validator silently skips the visual schema (`PBIR_SCHEMA_UNREACHABLE`).

Nothing else goes in the item folder — Fabric accepts only the parts above. Keep notes, specs and
screenshots outside it.

## 8. Adapting the names

### 8.1 Record the mapping once

Only the five Date columns are read from config. Set them in the `date_filters:` block of
`config.yaml` (gitignored) — the block `config.example.yaml` ships, with the contract names as
the defaults:

```yaml
date_filters:
  date_table: Date                 # your Date table
  date_column: Date                # the calendar-day column
  day_name_column: DayName         # Monday … Sunday — the day pin
  week_label_column: WeekLabel     # one label per trading week — the week pin
  has_sales_column: HasSales       # TRUE on days with loaded sales — the anchor
```

`scripts/date_filters.py`, `scripts/check_report.py`, `date_filters.py --selftest` and
`tests/test_guardrails.py` all read this block, so the filters the script writes, the offline
checks and the tests follow your names. Two more keys under `deploy:` are read: the
report-measure prefix `report_measure_prefix` (`RM `) and the filter-name marker `filter_marker`
(`org` — leave it).

Every other contract name — `TradingYear`, `TradingWeek`, `DayNumber`, the calc-group table,
column and items, the measure table, the measures, the `Store` pieces — has **no config key**.
They live inside the template JSON, the snippets and the DAX, and are renamed there by the recipe
in 8.2. Keep the full mapping in your spec (`docs/reference/SPEC_TEMPLATE.md`, "Contract mapping").

### 8.2 Apply it — the find/replace list

The template JSON, the snippets and the DAX are text. Every contract name appears in one of these
exact forms, so a plain replace on the exact form is safe (replacing the bare word `Date` is not):

| Contract name | Appears as (JSON) | Appears as (DAX) | Files |
|---|---|---|---|
| a column, e.g. `HasSales` | `"Property": "HasSales"` · `"queryRef": "Date.HasSales"` · `"nativeQueryRef": "HasSales"` | `[HasSales]` | `report-template/definition/**/*.json`, `docs/reference/snippets/*.json`, `docs/reference/measures/*.dax` |
| a measure, e.g. `Sales` | `"Property": "Sales"` · `"queryRef": "Measures.Sales"` · `"nativeQueryRef": "Sales"` | `[Sales]` | same |
| a table, e.g. `Date` | `"Entity": "Date"` · `"queryRef": "Date.…"` | the whole quoted token `'Date'`: `'Date'[…]`, `ALL('Date')`, `REMOVEFILTERS('Date')` | same |
| the calc group | `"Entity": "Time Intelligence"` (the table) · `"Property": "Time Intelligence"` (the column) | `'Time Intelligence'[Time Intelligence]` in tie-out queries | the **vs LY %** card, docs |
| a calc item, e.g. `vs LY %` | `"Value": "'vs LY %'"` (a filter literal) | `"vs LY %"` in tie-out queries | the **vs LY %** card, docs |
| the `Store` pieces | `"Entity": "Store"` · `"Property": "Channel"` (the `reportChannelScope` filter) | `'Store'[StoreName]`, `'Store'[StoreKey]` | `report.json`, `rm_bottom10_vs_budget.dax`, `rm_lfl_ly.dax` |
| the day sort key `DayNumber` | — | `'Date'[DayNumber]` | section 6, query 3 (docs only) |
| the `RM ` prefix | `"name": "RM …"` · `"Property": "RM …"` · `"queryRef": "Measures.RM …"` | `[RM …]` in test queries only | `reportExtensions.json`, the two header cards, `docs/reference/measures/` |
| the `ORG-` prefix | `"displayName": "ORG-…"` | — | `.platform`, `config.yaml` |

A recipe that does exactly that. **TESTED offline** (2026-08-28, a scratch copy of this repo with
the example dictionaries below): afterwards `grep -rn "'Date'\|\"Date\.\|Time Intelligence\|'vs LY %'\|\"Entity\": \"Store\"\|HasSales\|DayName\|WeekLabel" report-template/definition docs/reference/snippets docs/reference/measures`
printed nothing; `npx -y @microsoft/powerbi-report-authoring-cli validate report-template` gave
`errorCount 0` (5 warnings, the usual duplicate filter names); and with `date_filters:` in
`config.yaml` set to the same new names, `tests/test_guardrails.py` passed 14/14,
`date_filters.py --selftest` PASS, `check_report.py report-template` 0 failures. **UNTESTED**
against a live model — run section 6.

```python
import pathlib
COLS   = {"HasSales": "IsTradingDay", "DayName": "Weekday", "WeekLabel": "FiscalWeek", "DayNumber": "DayOfWeek",
          "Time Intelligence": "Period", "StoreName": "Store Name", "Channel": "Sales Channel"}   # columns: contract -> yours
MEAS   = {"Sales": "Gross Sales", "Budget Sales": "Budget", "Sales vs Budget %": "Sales vs Budget Pct"}
TABLES = {"Date": "Calendar", "Measures": "Model Measures", "Time Intelligence": "Period", "Store": "Site"}
ITEMS  = {"vs LY %": "vs PY %"}                                                        # calc items (filter literals)
files = [*pathlib.Path("report-template/definition").rglob("*.json"),
         *pathlib.Path("docs/reference/snippets").glob("*.json"), *pathlib.Path("docs/reference/measures").glob("*.dax")]
for p in files:
    t = p.read_text(encoding="utf-8")
    for old, new in {**COLS, **MEAS}.items():
        t = t.replace(f'"Property": "{old}"', f'"Property": "{new}"')
        t = t.replace(f'"nativeQueryRef": "{old}"', f'"nativeQueryRef": "{new}"')
        t = t.replace(f'.{old}"', f'.{new}"')          # queryRef "Table.Name"
        t = t.replace(f"[{old}]", f"[{new}]")           # DAX
    for old, new in TABLES.items():
        t = t.replace(f'"Entity": "{old}"', f'"Entity": "{new}"')
        t = t.replace(f'"queryRef": "{old}.', f'"queryRef": "{new}.')
        t = t.replace(f"'{old}'", f"'{new}'")           # DAX: 'Date'[...], ALL('Date'), REMOVEFILTERS('Date')
    for old, new in ITEMS.items():
        t = t.replace(f"'{old}'", f"'{new}'")           # the filter literal "Value": "'vs LY %'"
    p.write_text(t, encoding="utf-8")
```

Order matters when one name contains another (`Sales` inside `Budget Sales`): the DAX replace
`[Sales]` cannot touch `[Budget Sales]` because of the brackets, the table replace `'Store'`
cannot touch `'Store LFL'` because of the closing quote, and the JSON forms are quoted whole —
that is why the recipe replaces exact forms and never bare words. The prose in `docs/*.md` keeps
the contract names on purpose; only the files the recipe lists are renamed.

Then set the `date_filters:` block of `config.yaml` to the same new names (8.1). The tests and
the offline checks compare the snippets and the template against the **configured** names, so
`test_date_filter_shapes`, `test_date_filters_rerun_replaces_only_its_own` and
`date_filters.py --selftest` fail until `config.yaml` and the renamed files agree — that is the
point. Then validate to 0 errors, run `tests/test_guardrails.py`, and run section 6 against the
model.

### 8.3 The prefixes

`RM ` marks a measure that lives in the report; `ORG-` marks an item this repo created. Change them
in `config.yaml`, in `reportExtensions.json` (`name`), in the two header cards (`Property`,
`queryRef`, `nativeQueryRef`) and in `.platform`. Pick both once and never mix them. The `org` at
the front of the filter names is a third thing — `deploy.filter_marker` — and it does **not**
follow `ORG-`: leave it, and a prefix change never touches the template (`docs/reference/ADOPTION_GUIDE.md`
step 4 says what to re-run if you do change it).

## 9. Raise with the model owner

Two gaps the report can only work around: a public-holiday flag on `'Date'` (the basis note keeps a
literal list instead), and a written basis for every headline measure — tax in or out, returns
signed or not, orders placed or dispatched (two honest measures told opposite stories on the
reference build, and nothing on the page said which one it was).
