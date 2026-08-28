# Report measures (`RM `)

DAX that ships inside the report (`definition/reportExtensions.json`), not in the model. Contract
names only (`docs/MODEL_CONTRACT.md`). Every file here is the full expression of one measure, or
the block they share — copy it into a `DEFINE MEASURE` to test it, paste it into the JSON to ship it.

## The shared preamble — `preamble.dax`

The first five lines of every `RM ` measure except the two that pin per axis row:

| VAR | Meaning |
|---|---|
| `_Cut` | the latest traded day **in the current filter context** — no `ALL`, so the measure follows the Week and Day slicers exactly as the day pins do (TESTED) |
| `_Y`, `_W` | the trading year and week of `_Cut` |
| `_Dn` | the weekday name of `_Cut` (one row) |
| `_DnW` | the weekday names traded so far this week, capped at `_Cut` — the week-to-date shape |

`rm_lfl_ly.dax` adds a sixth, `_S` = the stores that trade this year, used only by like-for-like.

## The measures in the template

| Measure | `dataType` / `formatString` | Body after the preamble | File |
|---|---|---|---|
| `RM Day Label` | `Text` | `ddd d mmm yyyy · Wk N · day n/7 · N days ago` | `rm_day_label.dax` |
| `RM Basis Note` | `Text` | `LY = <date> (public holiday — distorted) · LW = <date>`; the holiday list is a literal table that ships as a **placeholder** (three illustrative dates, marked `PLACEHOLDER` in the DAX) — replace it with your public holidays before the first deploy, then extend it each year (**UNTESTED** beyond the dates you list) | `rm_basis_note.dax` |
| `RM WTD Sales` | `Double`, `#,##0;-#,##0;0` | `CALCULATE([Sales], REMOVEFILTERS('Date'), 'Date'[TradingYear] = _Y, 'Date'[TradingWeek] = _W, TREATAS(_DnW, 'Date'[DayName]))` | `rm_wtd_sales.dax` |
| `RM WTD Sales LY` | same | the WTD body with `_Y - 1` | derived from `rm_wtd_sales.dax` |
| `RM WTD Budget` | same | the WTD body with `[Budget Sales]` | derived |
| `RM YTD Sales` | same | `CALCULATE([Sales], REMOVEFILTERS('Date'), 'Date'[TradingYear] = _Y, 'Date'[Date] <= _Cut)` | inside `rm_ytd_vs_ly_pct.dax` (`__a`) |
| `RM YTD Sales LY` | same | `_Y - 1`, same weeks and same weekdays: `FILTER(ALL('Date'[TradingWeek], 'Date'[DayName]), 'Date'[TradingWeek] < _W \|\| ('Date'[TradingWeek] = _W && 'Date'[DayName] IN _DnW))` | inside `rm_ytd_vs_ly_pct.dax` (`__b`) |
| `RM YTD Budget` | same | the YTD body with `[Budget Sales]` | derived |
| `RM WTD vs LY %`, `RM WTD vs Budget %`, `RM YTD vs LY %`, `RM YTD vs Budget %` | `Double`, `0.0%;-0.0%;0.0%` | `VAR __a = <full TY body> VAR __b = <full LY or Budget body> RETURN DIVIDE(__a - __b, __b)` — both bases inlined as nested `VAR … RETURN` blocks | `rm_ytd_vs_ly_pct.dax` is the pattern |
| `RM LY Sales by Day` | `Double`, `#,##0;-#,##0;0` | per axis date: last year, same week, same weekday — **no calc group**; its own preamble on `MAX('Date'[Date])` | `rm_ly_sales_by_day.dax` |
| `RM Bottom 10 vs Budget` | same | `RANKX` over `ALLSELECTED('Store'[StoreName])` with `[Sales] > 0`, keep rank ≤ 10 — the rank lives inside the measure because a `TopN` filter cannot coexist with the pins or the slicers (TESTED) | `rm_bottom10_vs_budget.dax` |

Not in the template, optional: `rm_lfl_ly.dax` — like-for-like last year on this year's store
cohort (`REMOVEFILTERS('Store LFL')`, `TREATAS(_S, 'Store'[StoreKey])`). Needs the pieces in
`MODEL_CONTRACT.md` section 4. On the reference model it turned a naive +16.6 % into +2.1 %
(TESTED). Budget never slices by cohort.

## Rules (all TESTED on a real retail model)

1. **No `RM ` measure references another.** `[RM X]` inside an expression fails at render on a card
   and works in a matrix. Inline the base as a nested `VAR x = VAR … RETURN …` block.
2. **`dataType` is `"Text"`, never `"String"`** — the deploy payload fails schema validation.
3. **Test each measure alone** before deploying — one `DEFINE MEASURE` per query reproduces a
   single card; defining them all together hides rule 1.
4. **Never filter a visual on an `RM ` measure.** Rank inside the measure.
5. **No date filter on an `RM ` card.** It pins itself through `_Cut`; add the day pins only to
   cards bound to **model** measures.
6. **Labels are computed at query time.** `TODAY() - _Cut` is the age of the load; no report can
   show newer data than `_Cut`.

## One source of truth

The `.dax` files are the source; `reportExtensions.json` is generated from them and must match
byte for byte. Check it (from the repo root):

```python
import json, pathlib
ext = {m["name"]: m["expression"] for e in json.load(open("report-template/definition/reportExtensions.json"))["entities"] for m in e["measures"]}
pre = pathlib.Path("docs/reference/measures/preamble.dax").read_text().rstrip("\n")
for f, name in [("rm_day_label.dax", "RM Day Label"), ("rm_basis_note.dax", "RM Basis Note"),
                ("rm_wtd_sales.dax", "RM WTD Sales"), ("rm_ytd_vs_ly_pct.dax", "RM YTD vs LY %"),
                ("rm_ly_sales_by_day.dax", "RM LY Sales by Day"), ("rm_bottom10_vs_budget.dax", "RM Bottom 10 vs Budget")]:
    assert pathlib.Path("docs/reference/measures", f).read_text().rstrip("\n") == ext[name], f
for name, expr in ext.items():
    assert "[RM " not in expr, name                                   # rule 1
    assert name in ("RM LY Sales by Day", "RM Bottom 10 vs Budget") or pre in expr, name
print("measures OK:", len(ext))
```

To change a measure: edit the `.dax`, paste the expression into the JSON entry (`\n` for line
breaks — `json.dumps` does it for you), run the check, validate the folder, then test the measure
alone against the model.

Test one measure alone (read-only, `scripts/validate.py --file q.dax`):

```dax
DEFINE MEASURE 'Measures'[RM WTD Sales] = <paste rm_wtd_sales.dax>
EVALUATE ROW("v", [RM WTD Sales])
```
