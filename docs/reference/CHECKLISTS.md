# Checklists — the one page for daily use

Tick in order. A box you cannot tick is a blocker to name, not a step to skip. The long form with
evidence and trap numbers is `docs/reference/PLAYBOOK_PART5.md`; the traps are `docs/reference/PLAYBOOK_PART4.md`.

`powerbi-report-author` below is the PBIR CLI: `npm i -g @microsoft/powerbi-report-authoring-cli`
puts it on your PATH; with nothing installed, write `npx -y @microsoft/powerbi-report-authoring-cli`
in its place (same arguments).

## Before you build

- [ ] Audience and the one question written at the top of the spec (`docs/reference/SPEC_TEMPLATE.md`).
- [ ] `python3 scripts/discover.py` run; every row of `docs/MODEL_CONTRACT.md` mapped in the spec.
- [ ] Freshness known: `python3 scripts/refresh.py --history` and
      `EVALUATE ROW("d", CALCULATE(MAX('Date'[Date]), 'Date'[HasSales] = TRUE))`. Stale = a note, never a refresh.
- [ ] Report-level filters read against the visuals' filters (a dropped channel hides in the gap).
- [ ] Ground truth pulled **once**, one batched query, saved outside the repo; tie-out table filled.
- [ ] Data traps written into the spec: holiday LY, dispatch-dated online, margin base, budget phasing, cohort keying, saved literal pin, dropped channel.
- [ ] Spec greenlit by the owner. Theme lock stated in rule 1.
- [ ] Cloned, never the original: `.platform` → `ORG-` name + new `logicalId`; `definition.pbir` `byConnection` bound to your model (`python3 scripts/deploy_report.py "<folder>" --bind` writes it from `config.yaml`).
- [ ] Title textbox basis line says **your** channels and tax basis (the template ships `<channels> · <inc or ex tax>`).
- [ ] `cp -r "ORG-Daily Trading.Report" .backup-header/`
- [ ] Model id under `deploy.allowed_model_ids` in `config.yaml` **only** when the report binds to a model other than `semantic_model.id` (that one is accepted on its own).

## Per page (give this to the builder)

- [ ] Header untouched. Only `definition/pages/<my page id>/`. No slicers outside the header.
- [ ] Date filters only via `python3 scripts/date_filters.py <visual.json> latest-day | window-weeks | this-week | none`. `window-days` banned. `RM ` cards get `none`.
- [ ] Model measure + calc-group filter first; `RM ` measures only where the spec names them.
- [ ] Copy shapes (this report, `docs/reference/snippets/`, the `skills-for-fabric` `references/` — path and the rules used here in `docs/reference/snippets/README.md` — `powerbi-report-author formatting describe-object`). Never guess a property.
- [ ] New visual: own folder, `name` = folder, unique `z` and `tabOrder`, inside x 16–1264 / y ≤ 720, no overlap.
- [ ] Labels in plain English; legend and axis titles off; "Time Intelligence" and "Y2" never on screen.
- [ ] Cards `1000D` / `1L`; % one decimal; tables whole units; leading minus, no brackets; data labels on; sort by value.
- [ ] No new colours.
- [ ] `powerbi-report-author validate "<folder>" --format json` → `data.errorCount: 0`. Do not deploy.
- [ ] Return the visual list and what was not done, with the reason.

## Before deploy (offline first)

```
powerbi-report-author validate "ORG-Daily Trading.Report" --format json     # errorCount 0; read the warnings
python3 scripts/check_report.py "ORG-Daily Trading.Report" --baseline report-template
                                            # --baseline "<original>.Report" only when you cloned an existing report
                                            # theme, colours, fonts (only with --baseline), state setting,
                                            # saved selections, extension filters, RM names, pins,
                                            # window-days, overlaps, bounds, unique names, mobile.json
                                            # (Part 5, 5.3 lists them; add any it lacks)
python3 scripts/validate.py --file q.dax          # each RM measure ALONE: DEFINE MEASURE … EVALUATE ROW(...)
python3 tests/test_guardrails.py
python3 tools/secret_scan.py .                    # 0 hits (what git would commit; gitignored paths skipped)
cp -r "ORG-Daily Trading.Report" .backup-roundN/
python3 scripts/deploy_report.py "ORG-Daily Trading.Report"
```

## After deploy — look

```
python3 scripts/capture_pages.py 00000000-0000-0000-0000-000000000000 captures/roundN 60 --headless   # no --headless on the first run: sign in
grep -iE "wrong|see details|\(Blank\)" captures/roundN/*.txt
```

- [ ] Header: a real date, the trading week, the age; basis note names LY and LW.
- [ ] Every tie-out number on screen, digit by digit.
- [ ] Count: dates on the trend × series; regions; ten bars in a bottom 10, all negative; the P&L foots.
- [ ] No spinners, error tiles, `(Blank)`, "Visuals are loading…" after the settle time.
- [ ] No scrollbars, ellipses, clipped labels or descenders. Value order, not alphabetical.
- [ ] One negative convention; red/green as the original.
- [ ] Slicer states: All/All → latest traded day; a day pick → LY re-labelled same weekday; Week = Last week → "day 7/7"; "Latest day" button → All/All; fresh open → All/All.
- [ ] Every page follows the pick.
- [ ] Capacity message → stop, wait ≥ 30 min, one light probe. Any deploy re-opens this list.

## Stop when

1. every Done-criteria number ties **on screen** after the **last** deploy;
2. every slicer state and every page seen since that deploy;
3. theme byte-identical to the approved one;
4. validator 0 errors, `tests/test_guardrails.py` green, secret scan 0 hits.

## Before handover

- [ ] Memory note: status line, ids, paths, every mechanic TESTED (where) / UNTESTED (test), decisions owed, next-session one-liner.
- [ ] Spec corrected in place; Done criteria equal the final screenshots.
- [ ] Backups named. Original untouched. Nothing committed unless asked.
- [ ] Model-owner asks as one-liners with evidence — the owner sends, not the agent.

## When a screen looks wrong

| You see | Go to |
|---|---|
| LY week-sized on a day visual; LY flat on a trend | T1, T3 |
| YTD a fraction of the truth | T2 |
| Blank page on open; `(Blank)` in a dropdown | T11, T12 |
| Positive bars in a "bottom 10"; empty under a slicer pick | T8 |
| "Something's wrong with one or more filters / fields" | T22, T23 |
| "The value for '…' cannot be determined" | T20 |
| Screenshots of the old build; wrong tab; `Session not found` | T27–T29 |
| "Unable to load model due to reaching capacity limits" | T31 |
| A number that is right and still tells a false story | T35–T45 |
