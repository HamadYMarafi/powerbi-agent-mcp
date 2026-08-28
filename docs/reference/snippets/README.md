# PBIR snippets

Verbatim JSON shapes from a report that deployed and rendered (TESTED on a real retail model),
renamed to the contract in `docs/MODEL_CONTRACT.md`. Copy them; do not retype them. Each file
shows the key it belongs under, so you can see where it goes in `visual.json`.

| File | What it is | Goes in | Notes |
|---|---|---|---|
| `latest_day_filters.json` | the two day pins: `TopN 1` on `'Date'[DayName]` and on `'Date'[WeekLabel]`, ordered by `Max('Date'[Date])` desc over `HasSales = true` | `visual.json` → `filterConfig.filters` | written by `scripts/date_filters.py <visual.json> latest-day`; `OrderBy` must be an `Aggregation`, the `Where` sits inside the subquery, `SourceRef` uses `Source` inside `Where`. Never on a `'Date'[Date]` column (trap T1) |
| `window_weeks_filters.json` | `orgWindowWeeks` (`TopN 3` on `WeekLabel`) + `orgTradedDays` (`HasSales = true`) — the trend-chart window | `filterConfig.filters` | `date_filters.py … window-weeks`; `this-week` is the same pair with `Top 1` |
| `not_blank_filter.json` | `orgNotBlank`: Advanced `Not(Comparison(column, Literal "null"))` | `filterConfig.filters` | hides the blank row of a slicer or a category axis; shown on `'Date'[WeekLabel]`, change `Entity`/`Property` |
| `conditional_font_colour.json` | the delta-card `value` object: green above 0, red below, default colour at ≥ 100 % | `visual.objects.value` | `ComparisonKind` 1 = `>`, 3 = `<`. Shown for a **model** measure; for an `RM ` measure add `"Schema": "extension"` to both `Left.Measure.Expression.SourceRef` blocks. Replace the two hex values with your approved theme's good/bad pair |
| `sort_definition.json` | sort a visual by `[Sales]` descending, `isDefaultSort: false` | `visual.query.sortDefinition` | a bar chart sorted by a `Tooltips` measure uses this exact shape with that measure |
| `projection_display_name.json` | a projection with a `displayName` header override | any `queryState.<role>.projections[]` | renames a column header in `tableEx`/`pivotTable` and a series name in charts without touching the model |
| `clear_all_slicers_button.json` | the whole "Latest day" `actionButton`: `visualContainerObjects.visualLink.type = 'ClearAllSlicers'` | a `visuals/<id>/visual.json` of its own | rename `name` to the folder id (20 lowercase hex), keep `position.z`/`tabOrder` unique on the page |
| `mobile_layout.json` | a `mobile.json` (phone layout: position only) | `visuals/<id>/mobile.json` beside `visual.json` | validated offline, **UNTESTED** on a phone |
| `report_extensions_shape.json` | `definition/reportExtensions.json` with one illustrative measure | the file itself | `"name": "extension"`, one entity = the measure table in your model, measures with `name`, `dataType` (`Text`, never `String`), `formatString`, `expression`. Visuals reach them with `"Schema": "extension"` in the projection |

The `org` at the front of the filter names is `deploy.filter_marker` in `config.yaml` (default
`org`, independent of the item prefix). `scripts/date_filters.py` owns and replaces exactly five
names — `orgLatestDayName`, `orgLatestWeek`, `orgWindowWeeks`, `orgTradedDays`, `orgWindowDays`;
`orgNotBlank`, `orgRecentWeeks` and `orgRecentDays` share the marker by convention only and are
copied from here by hand. The validator reports the repeated names as
`PBIR_FILTER_NAME_DUPLICATE_GLOBAL` warnings; that is by design.

## The PBIR rules these shapes obey — copied from Microsoft `skills-for-fabric`

The playbook cites `filters.md`, `slicers.md`, `textbox.md`, `card.md`, `conditional-formatting.md`
and friends. They are **not** in this repo: they are
`skills/powerbi-report-authoring/references/<file>` in
<https://github.com/microsoft/skills-for-fabric> (also under
`plugins/powerbi-authoring/skills/powerbi-report-authoring/references/`), re-read at commit
`714ea2f` (2026-08-27). The rules this repo actually leans on, so a clone needs nothing else:

| Rule | Source | Where it bites here |
|---|---|---|
| A `TopN` filter can only be a **visual-level** filter — never page- or report-level. | `filters.md` | the day pins go on every visual, never in `page.json` (T6) |
| A `TopN` subquery's `OrderBy.Expression` must be an **`Aggregation`** (wrapping a Column), not a `Measure`. `Direction` `1` = Bottom, `2` = Top. | `filters.md` | `latest_day_filters.json`: `Aggregation {Function 4 (Max), 'Date'[Date]}`, `Direction 2` (T7) |
| Inside a filter's `Where`, `SourceRef` uses **`"Source"`** (the alias from `From`), not `"Entity"`; the top-level `field` uses `"Entity"`. The validator flags the mistake as `PBIR_FILTER_ENTITY_IN_WHERE`. | `filters.md` | every filter file here: `"Source": "d1"` / `"Source": "subquery"` inside `Where`, `"Entity": "Date"` in `field` |
| A dropdown slicer needs **`h = 60 + top padding + bottom padding`**, snapped up to the next 8 px (60 = header ≈ 28 + selector ≈ 32); declare the `padding` visual-container object whenever you set any other one, or the theme padding cascade is dropped. | `slicers.md` | the two header slicers: h 76 with 0/0 padding validates, 64 fails (T15) |
| A textbox needs a **native `paragraphs` array** directly under `objects.general[].properties.paragraphs` — not wrapped in `{ "paragraphs": [...] }`, not stringified. The wrapped form validates and renders invisible. | `textbox.md` | the title textbox (`visuals/97e504e652a65d840fd6`) |
| A `cardVisual` binds its measure in the **`Data`** role (not `Fields`); the callout area only renders with two or more measures, so a single value cannot be sized on its own. | `card.md` | the hero row is single-value cards (Part 3, 7.1–7.2) |
| Conditional-format selectors differ by visual type: a matrix/table rule needs **both** `data: [{dataViewWildcard}]` and `metadata`; a chart's `dataPoint` rule carries `dataViewWildcard` and **no** `metadata`. | `conditional-formatting.md` | `conditional_font_colour.json` (cards); Part 3, 7.3 and 7.8 |

All of these were re-read in those files at that commit, except the card callout limit, which is
as the reference build found it (TESTED on screen) — re-read the files if a validator message
disagrees. Live output beats this table.
