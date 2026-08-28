---
name: powerbi-dashboard-verify
description: Verify a Power BI / Microsoft Fabric report after a deploy, before calling the work done. Use immediately after any deploy_report call, when the user says "check it", "is it right", or "verify the dashboard", or before reporting a build finished. Runs the see-it doctrine — structural validation, a definition diff, then screenshots of every page and slicer state read against a tie-out table — under capacity-lean verification etiquette.
---

# Power BI dashboard verify

A report that deploys cleanly and renders blank looks identical from the API.
This skill is the post-deploy check that catches what structural validation
cannot see — `docs/reference/PLAYBOOK.md` 1.3. Run it after every deploy, not
just the first one: any deploy re-opens the loop.

## The four verification levels

Each level catches what the one before it cannot
(`docs/reference/PLAYBOOK_PART3.md` Step 10):

| Level | Tool | Catches | Cannot see |
|---|---|---|---|
| 1 Offline JSON | `validate_report` | schema errors, overlaps, out-of-canvas, missing date pins, theme drift, banned filter kinds, saved slicer picks | field errors the service only resolves at render time |
| 2 DAX tie-out | `run_dax` | wrong numbers, a broken last-year basis, measure bugs | layout, formats, labels |
| 3 Screenshots | `capture_pages` | clipping, label truncation, wrong sort, error tiles, wrong series, a weekly value on a daily axis | slicer behaviour |
| 4 Slicer-state capture | `capture_pages`, one state per pass | blank pages, filters that ignore context, broken sync, a reset that does not reset, persisted state | — |

Run them in order — levels 1 and 2 are free (no render, no capacity cost).
Never jump to level 3 or 4 to save time: a page can fail level 1 or 2 in a way
that makes the screenshot round pointless.

## Procedure

1. `validate_report(folder, baseline)` — do not continue past a nonzero error
   count. Read the warnings too; a warning outside the two known kinds
   (duplicate filter names by design, an unreachable offline schema URL)
   means look closer before dismissing it.
2. Structural diff: `get_report_definition(report, out_dir, workspace)` on
   the just-deployed item, then compare its JSON against the local folder
   that was deployed. They should match part for part — a difference here is
   a deploy problem, not a design problem, and it is cheaper to catch here
   than in a wrong screenshot.
3. `run_dax(query, ...)` — one batched query — only if no tie-out table
   already exists from the build; otherwise reuse it rather than
   re-deriving it.
4. `capture_pages(target, out_dir, headless=True, settle_seconds=60)` for
   every page, in every state a user can put it in:

   | State | How | Expect |
   |---|---|---|
   | Default | open the report | every visual on the latest traded day, nothing pre-picked |
   | One day | pick a specific day | that date; the comparator relabels to the matching day last year |
   | One week | pick a specific week | the last traded day of that week |
   | Both | a week pick, then a day pick | the week pick narrows the day list; the day pick still lands on the matching weekday last year |
   | Reset | the "latest day" / clear-slicers control | back to default |
   | Other pages | pick on one page, open another | the pick followed, if pages are meant to sync |
   | Reopen | close and reopen the report | back to default — a report should not remember one viewer's picks for the next |

   A deploy without a matching capture round, in every state above, has not
   been verified.
5. Read the digits in every `.txt` against the tie-out table. Digit by
   digit, not "looks about right".
6. Grep each `.txt` for `wrong`, `See details`, and `(Blank)` — the
   accessibility-text markers for an error tile, a render failure, or a
   blanked slicer. Zero hits required.
7. Check the header basis labels on every page: a real date, the trading
   week, the load age, and the comparator dates — not a placeholder, not a
   generic label that fails to say which day or basis is on screen.
8. Capacity etiquette, every round: **one** render pass per deploy, **one**
   batched DAX query, offline checks first (steps 1–3 before 4–7), never fan
   captures or DAX queries across parallel agents. If the tenant reports a
   capacity limit, stop every query and render, wait at least 30 minutes,
   then run one light probe before resuming — never retry immediately.

## Traps to remember

Source: `docs/reference/PLAYBOOK.md` 1.3, 2.5, 2.6, 2.8; post-deploy section
of `docs/reference/CHECKLISTS.md`; full catalogue
`docs/reference/PLAYBOOK_PART4.md`. What passed every offline check on the
reference build and was only caught by looking: a year-to-date tile reading a
fifth of the true number, because a calculation item kept a day-level filter
pin (T2); last year's values flat at a weekly total across a daily trend
chart (T1, T3); a page that opened completely blank because a
strict-single-select slicer with no saved selection auto-picked `(Blank)`
(T11); a "bottom 10" list full of positive numbers because a top-N filter's
subquery ignored the page's other filters (T8); a caveat label clipped
mid-word in an undersized card. Every one of these rendered wrong on screen
while the validator reported 0 errors.

## Definition of done

Report pass/fail per Done criterion, each with the evidence file name (which
`.png` / `.txt`, which DAX result) — not a bare "looks fine". Stop only when
all four hold:

1. every Done-criteria number ties **on screen**, from the last deploy;
2. every state in the table above has been seen since that deploy;
3. the theme is byte-identical to the approved baseline;
4. `validate_report` reports 0 errors.

No capacity limit hit, or the required 30-minute wait was honoured before the
next probe.
