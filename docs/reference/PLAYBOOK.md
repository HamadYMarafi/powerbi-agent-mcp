# Executive Daily-Trading Dashboard Playbook (public edition)

Power BI on Fabric, the proper way. This is the company-neutral edition of a playbook written
straight after a real executive daily-trading report was reviewed, rebuilt and shipped on a live
retail tenant. Every mechanism here was paid for on that build; the company, the model, the people
and the numbers have been removed and replaced with placeholders.

**This file holds Parts 0, 1 and 2.** The rest of the playbook follows in:

| File | What is in it |
|---|---|
| `docs/reference/PLAYBOOK_PART3.md` | Part 3 — the build recipe, step by step (discover, tie-out, spec, folder, header, date mechanics, visual idioms, theme, loop, verification levels, handover) |
| `docs/reference/PLAYBOOK_PART4.md` | Part 4 — the traps catalogue, plus appendices of PBIR snippets, DAX and commands |
| `docs/reference/PLAYBOOK_PART5.md` | Part 5 — checklists and templates (pre-build, per page, pre-deploy, post-deploy review, exec-review seats, handover, spec skeleton) |

---

# Part 0 — How to use this playbook

## 0.1 Who this is for

Two readers, and the text is written for both at once:

- **A BI developer at another company** who has a semantic model, a Fabric workspace and an
  executive who wants one page that answers "how did we trade yesterday?".
- **An AI coding agent** working inside this repo. Everything an agent needs is a file path or an
  exact command; nothing depends on remembering a conversation.

Read Part 1 before you touch anything — each guardrail was paid for. Keep Part 2 open while you
work. Follow Part 3 step by step. Open Part 4 the moment a screen looks wrong. Tick Part 5 before
every deploy and every handover.

## 0.2 Evidence labels — TESTED and UNTESTED

Every mechanism claim in this playbook carries a label:

- **TESTED** — proven on screen or by read-only DAX during the original build on a real retail
  model, with the artefact that proves it named (a screenshot, a query result, a script self-test).
- **UNTESTED** — plausible, not proven here. The test that would prove it is named next to it.

Never upgrade a label without running the test. Never quietly drop one either: a reader who cannot
tell proof from opinion will trust the wrong sentence at the wrong moment.

**Live output beats this document.** If a tool, a file or a rendered page says otherwise, the page
wins. Fix the note and carry on.

## 0.3 Placeholders — replace these first

This repo ships neutral placeholders. Search and replace them in your fork before you build.

| Placeholder | Means | Where it appears |
|---|---|---|
| `YourCo` | your company | docs, spec templates |
| `ORG-` | the prefix on every workspace item this repo creates | `config.yaml` (`deploy.item_prefix`), `scripts/deploy_report.py`, item display names |
| `RM ` | the prefix on report-level measures (as opposed to model measures) | `report-template/definition/reportExtensions.json`, `docs/reference/measures/` |
| `00000000-0000-0000-0000-000000000000` | any workspace / model / report GUID | `config.yaml`, example commands |
| `1,234,567` and similar round figures | illustrative numbers only — never real trading data | examples throughout |

Two of these are configuration, not cosmetics. `ORG-` is what stops the deploy script touching an
item somebody else made, and `RM ` is what tells a reader whether a measure lives in the shared
model or in your report. Pick both once, then never mix them.

## 0.4 The model contract

This playbook assumes your semantic model gives the report a small number of things. That is the
**model contract**. It is a contract because the report cannot fix a model it is not allowed to
change, and because two of the worst traps in Part 1 are caused by a Date table that does not
provide these columns.

Example names are used throughout; yours will differ, so map them once in your spec and keep the
mapping in one place.

**Date table** (`'Date'`):

| Column | Type | What it must mean |
|---|---|---|
| `Date` | date | one row per calendar day, marked as the model's date table |
| `TradingYear` | whole number | the fiscal/trading year the day belongs to |
| `TradingWeek` | whole number | the fiscal/trading week number inside `TradingYear` |
| `DayName` | text | `Monday` … `Sunday`; sorted by a day-number column |
| `WeekLabel` | text | a human label per trading week, e.g. `This week`, `Last week`, `Wk 12 2026`; sorted by a year-and-week key |
| `HasSales` | boolean | `TRUE` on days that have loaded sales, `FALSE` otherwise |

`HasSales` is the important one. An executive page must show the **latest traded day**, which is the
last day with loaded sales — never today, and never yesterday if yesterday has not landed yet.
Without a `HasSales` flag, every "latest day" expression in this playbook has to be rebuilt around a
`MAX` over the fact table, which is slower and silently wrong while a load is half-finished.

**Calculation group** `'Time Intelligence'`, with these items:

`Current`, `LW`, `LY`, `vs LW %`, `vs LY %`, `YTD`, `YTD vs LY %`

**Measures** the examples assume exist in the model: `[Sales]` (the headline sales measure),
`[Budget Sales]`, and — if you sell online — an orders-placed measure such as `[Orders Value]`.
Table names in the examples: `'Store'[StoreName]`, `Fact[StoreKey]`.

**Two known gaps to raise with whoever owns the model**, because the report can only work around
them: a public-holiday flag on the Date table (Part 1, trap 1), and clean, documented bases for
every headline measure — tax in or out, returns signed or not, orders or dispatches (Part 1, traps
2 and 3).

## 0.5 Terms used throughout

- **latest traded day** — the last day with loaded sales (`'Date'[HasSales] = TRUE`). Never today.
- **day pins** — the two visual-level `TopN(1)` filters, on `'Date'[DayName]` and `'Date'[WeekLabel]`,
  written by `scripts/date_filters.py latest-day`. They are what makes a visual show the latest
  traded day without a hard-coded date.
- **trading week** — the model's fiscal week (`'Date'[TradingWeek]`, labelled by `'Date'[WeekLabel]`).
- **calc group** — the model's `'Time Intelligence'` calculation group.
- **report measures** — DAX defined in the report, in `definition/reportExtensions.json`, prefixed
  `RM `. They ship with the report, need no model change, and are the escape hatch when the model is
  read-only. See `docs/reference/measures/`.
- **the settings strip** — the header row shared by every page: a Week slicer, a Day slicer and a
  "Latest day" reset button, synced across pages.
- **the default state** — what the page shows on open, with nothing clicked. For an executive
  report this is the product; everything else is an override.

---

# Part 1 — Principles, guardrails and the see-it doctrine

## 1.1 What the page is for: meaning over arithmetic

An executive daily-trading dashboard answers one question at 08:00: *how did we trade on the latest
traded day, this week and this year — and can I trust it?* The reader is a director or the CEO. They
look at the default page for ten seconds and never touch a slicer. So **the default state is the
product.** Everything else is an override.

The review that started the original build proved the central idea of this playbook. The
data-integrity lens wrote, of a report whose every figure tied to the model to the penny: *"I still
would not put it in front of a CEO."* Every number was arithmetically right. The page was still
wrong, because **a number without its basis tells a false story.**

Six real traps, all TESTED by read-only DAX against a live retail model (figures below are
illustrative):

| Trap | What the page said | What was true |
|---|---|---|
| **Public-holiday comparator** | the latest day down 42% versus last year | Last year's matching weekday was a public holiday. Against a normal equivalent weekday the same day was down about 4%. The following week the same fault flips the other way and prints a fake gain, because this year's holiday falls in that week. |
| **Orders versus dispatches** | the online channel down 56% week on week — the biggest red bar on the page | The measure on the tile counted *dispatched* sales; orders *placed* were up 27%. In the model, a sale exists when it ships, so a weekend of orders shows up as a weekday of sales. Two honest measures, two opposite stories, and nothing on the page said which one you were reading. |
| **Margin percentage base** | gross sales, margin value and "70.6%" side by side in one row | The percentage was margin over *net sales excluding tax*. Net sales were never on the page. Anyone dividing the two tiles that were on the page got 44.7%. |
| **Hard-pinned weekday** | a header reading "week 35", slicers set to a specific weekday | The day slicer held a saved literal value and the week slicer was `TODAY()`-based. Correct on the morning it was built, stale from the next day, blank on Monday mornings. |
| **A channel silently dropped** | a day total of 1,234,567 | A report-level filter allowed four channels; every visual asked for five. The fifth (about 5% of the day) was dropped without a mark on the page. The true total was 1,301,000. |
| **Budget phasing** | one division 34% ahead of budget | The daily budget appeared to be phased on last year's daily profile, so last year's holiday distortion was baked into the budget line too. Marked as a hypothesis for the finance team to confirm — and labelled as one on the page. |

The principle that follows is the one rule this whole playbook exists to serve:

> **Every number carries its basis on the canvas** — which day, which comparator, tax in or out,
> orders or dispatches, cohort or all stores.

Do it with report measures that compute the basis at query time, so it can never go stale. Two live
in the header of the reference build (full DAX in `docs/reference/measures/`):

```
RM Day Label =
VAR _Cut  = CALCULATE(MAX('Date'[Date]), 'Date'[HasSales] = TRUE)
VAR _Y    = CALCULATE(MAX('Date'[TradingYear]), ALL('Date'), 'Date'[Date] = _Cut)
VAR _W    = CALCULATE(MAX('Date'[TradingWeek]), ALL('Date'), 'Date'[Date] = _Cut)
VAR _Days = CALCULATETABLE(
                VALUES('Date'[DayName]), ALL('Date'),
                'Date'[TradingYear] = _Y, 'Date'[TradingWeek] = _W,
                'Date'[HasSales]    = TRUE, 'Date'[Date] <= _Cut)
VAR _Age  = INT(TODAY() - _Cut)
RETURN FORMAT(_Cut, "ddd d mmm yyyy") & " · Wk " & _W &
       " · day " & COUNTROWS(_Days) & "/7" &
       IF(_Age >= 1, " · " & _Age & IF(_Age = 1, " day ago", " days ago"), " · today")
```

On screen that reads `Mon 24 Aug 2026 · Wk 35 · day 1/7 · 3 days ago` (TESTED on the real build).
The age is the honest part: it shows how far the data load lags, and no report can go past an
Import-mode model that somebody else refreshes.

```
RM Basis Note =                                     -- ending only; see docs/reference/measures/
RETURN "LY = " & FORMAT(_LY, "ddd d mmm yy") &
       IF(_LY  IN _Holidays, " (public holiday — distorted)", "") &
       IF(_Cut IN _Holidays, " · latest day is a public holiday", "") &
       "  ·  LW = " & FORMAT(_Cut - 7, "ddd d mmm")
```

`_Holidays` is a hard-coded list of dates, because the model had no holiday flag. That is a
workaround, and it is written down as one: the template ships three placeholder dates (marked in
the DAX) — replace them with your public holidays before the first deploy, then edit the list every
year until the model provides the flag (Part 0, 0.4).

## 1.2 The guardrails and why each exists

These are not preferences. Each one was paid for on a live shared tenant.

| # | Rule | Why | Where it is enforced |
|---|---|---|---|
| 1 | **Never print, log or persist an access token** | A token in a terminal, a log file or an exception message is a leak with a public repo attached to it. | Tokens are minted in memory and passed only in request headers. `tools/secret_scan.py` fails the build on token-shaped strings, e-mail addresses and non-placeholder GUIDs; it runs in CI (`.github/workflows/validate.yml`). |
| 2 | **Never trigger, retry or schedule a refresh on a model you do not own** | Every refresh is attributed to the identity that started it, and it lands in the tenant's refresh history under *your* name, as if you had run a job on someone else's model. On the original build this burned shared capacity and got the practice banned by management. Attribution, not destructiveness, is the problem. | **`scripts/refresh.py` reads history and status; triggering is gated twice** — `deploy.allow_refresh: true` in `config.yaml` *and* `--i-have-permission` on the command line — and the flag ships `false`. Stale data is not your emergency: say so, and hand the owner a one-line request for the data team. |
| 3 | **Prefix every item you create with `ORG-`** | It marks your items in a workspace you share with other teams, and it makes "did we make this?" a string comparison instead of a memory test. | `scripts/deploy_report.py` refuses any display name without the prefix, before any HTTP call. |
| 4 | **Never touch an item you did not create** | The original report was left byte-untouched; all work happened on an `ORG-` clone bound to the same model. | `scripts/deploy_report.py` refuses to update an existing workspace item whose name lacks the prefix; refuses `byPath` bindings (they would create a new model); and refuses any model GUID that is not `semantic_model.id` or listed in `deploy.allowed_model_ids`. |
| 5 | **The shared semantic model is read-only, forever** | Every report in the tenant binds to it. One "small fix" is everyone's outage. | Only `GET`, `getDefinition` and `executeQueries` are ever called against it — all reads. All report DAX lives in `reportExtensions.json`, never in the model. Model defects become a written request to the model owner and a workaround in the report. |
| 6 | **Theme locked once the owner approves it** | Stakeholders have already seen the look. A colour change mid-review costs trust you cannot re-earn with a nicer palette. | Spec rule: no theme-file edits, no new colour, font or size after the lock. Verify the theme file is byte-identical after every round. Design observations after the lock are *recorded*, not implemented. |
| 7 | **The owner sends to colleagues — not the agent** | Outward communication stays under one person's control. | Never click Share, Subscribe or Send; never grant access. Prepare the message and hand it back. |
| 8 | **Nothing is committed unless the owner asks** | The working copy and the committed copy are different vintages on purpose during a build. | Snapshots go to gitignored backup folders per round, not to commits. |
| 9 | **Capacity-lean verification** | Two hours of parallel DAX agents, six deploys and about twenty-five page renders produced *"Unable to load model due to reaching capacity limits"* on a shared capacity — which also broke the original report that other people were reading. | One render pass per deploy. Batch DAX into a single query. Prefer offline checks over live queries. Never fan DAX out across parallel agents. On the throttle message: stop, wait at least 30 minutes, then one light probe. See 2.8. |

Run `python3 tests/test_guardrails.py` after touching any script. It re-checks the deploy guardrails
offline, with no tenant and no network, in seconds.

## 1.3 The see-it doctrine

### Why JSON-only or DAX-only verification is not enough

Three checks passed at *every* round of the original build: the PBIR validator returned
`errorCount: 0`; each measure tied to the model when queried on its own; and an offline structural
diff of the deployed definition against the local folder matched part for part.

None of them can see a page.

A visual is a query assembled at render time out of the visual's projections, its own filters, the
page filters, the report filters, the slicer state and the calculation group. Only the rendered page
shows the product of all of them. As the render helper in the reference repo puts it: *a report that
deploys cleanly and renders blank looks identical from the API.*

### What only the eye caught

Every row below passed the validator. Every row was caught by looking at a screenshot.

| What the eye caught | What the checks said | Cause (TESTED unless marked) | What it would have cost |
|---|---|---|---|
| A **year-to-date tile reading a fifth of the real number, down 81.8%** | validator clean; a model measure plus the `YTD` calc item is a legal binding | The `YTD` calc item kept the visual's day-name pin, so the tile summed **only Mondays** of the year. Fix: bind the tile to a report measure that clears the date filters (`RM YTD Sales`), not to the calc group. | Telling a CEO the year is down 82% when it is up 14% |
| **Last-year columns flat across a trend chart**, every day showing the same value | the measure is correct; the filter is a valid `TopN` | A `TopN` window on `'Date'[Date]` makes the calc group's `LY` item return the *whole* last-year week on every day. Fix: window by trading week, not by date (`date_filters.py window-weeks`), and bind the last-year series to a report measure that shifts by year, week and day name. The related claim that the same window also makes the budget measure read as a weekly total is **UNTESTED** here — verify before repeating it. | Every day on the trend reading about −85% versus last year |
| A **blank page on open** — every visual empty while "Visuals are loading…" | `strictSingleSelect: true` is valid JSON | Strict single-select with no saved selection auto-picks the first item in the list, which is `(Blank)`, and that blanks the whole page. Fix: `singleSelect` true, `strictSingleSelect` false, `selectAllCheckboxEnabled` false, plus a "not blank" advanced filter on the slicer field. | The report opens empty for every user |
| **Clipped header text**: "day…" and a caveat cut off mid-word; 9-pt note losing its descenders | card and text sizes validate | Card widths and heights too small for their text. Fix: widen the header cards, make the note card taller. | The one caveat that changes the reading is the least legible thing on screen |
| A **horizontal scrollbar hiding the last columns** of a channel-by-day matrix | nothing at all | Fourteen date columns in a fixed-width matrix. Fix: show the traded days of the current trading week only (`date_filters.py this-week`). | The Total column — the week-to-date number — is off screen |
| An **empty "stores to call" chart** whenever the week slicer was moved off the default | valid `TopN` subquery | A `TopN` subquery does not inherit the other filters on the visual, so a store `TopN` and the day pins or slicers cannot coexist. | The "who do I call this morning" visual is blank exactly when somebody asks about last week |
| A **week dropdown listing every week since the model's first year**, oldest first | column binding valid | The label column sorts by a year-and-week key, so the dropdown starts in the model's earliest year. Fix: a visual `TopN` of 13 weeks ordered by `MAX('Date'[Date])` descending over `HasSales` rows, plus a descending sort definition. | The reader scrolls thirteen years to find this week |
| **Positive bars inside a "bottom 10"**, and only nine of them | `TopN` ascending is valid | The subquery ranked in its own context — effectively **over all history** — not on the latest traded day. Fix: move the rank into a report measure (`RANKX` over `ALLSELECTED('Store'[StoreName])`, blank outside the bottom ten). | The morning call list names the wrong stores |
| *"Something's wrong with one or more **filters**"* | filter JSON validates | A visual-level filter on a *report* measure errors at render. Never filter on a report measure; put the logic inside the measure. | An error tile on a normal, default page |
| *"Something's wrong with one or more **fields**"* on one chart, spinners elsewhere | validator clean; the visual JSON was byte-identical to a snapshot that rendered fine before and after | **UNTESTED — cause not recorded.** The capacity throttle began minutes later, which is the leading suspicion. On recurrence, read the visual's "See details" text *before* touching any JSON. | Hours spent "fixing" JSON that may never have been broken |
| **Mixed negative signs**: `(45.0%)` next to `−45.0%` | format strings validate | Two conventions in one report. Fix: leading minus everywhere, no brackets. | Two numbers that look different and are the same |
| **45 data labels colliding**; this-year and last-year series indistinguishable | labels "on" is correct JSON | Fix: labels on the current-year series only, thousands axis, and rebuild the clustered chart as a combo. | An unreadable trend page |
| **Missing red/green on the new delta cards**; a chart built in the wrong form | — | Caught by **the owner's own eye** in a polish round, after four agent review passes. | A hero row without the signal the previous version had |

### The rule

> **A page is not done until you have seen it rendered, with data, in every state a user can put it
> in: the default, each pick on the settings strip, the reset, and every page.**

On the reference build those states were: default (latest traded day); a specific day picked; last
week picked; this week picked; the "Latest day" reset button; and cross-page sync (pick on page 1,
check page 3 followed). All TESTED live.

Two settings make the default state real, both TESTED:

- `report.json` → `"isPersistentUserStateDisabled": true`, or the service re-applies the previous
  viewer's slicer picks the next time the page is opened.
- the reset button is an `actionButton` with `visualLink.type = "ClearAllSlicers"`.

The phone layout (`mobile.json`) was authored to the pattern library but never opened on a phone —
**UNTESTED**; verify in the mobile app before you claim it works.

### How to look — the checklist

1. **Header**: the day label reads a real date, a trading week and an age. The basis note names the
   last-year and last-week comparators.
2. **Tie the done-criteria numbers** from your spec, on screen, one by one.
3. **Count things**: dates on the axis, series in the legend, rows in a "top 10", regions in a
   region chart. A bottom-10 with nine bars is a bug you can only see by counting.
4. **No spinners, no error tiles, no "Visuals are loading…"** after the settle time (the first load
   after a definition update takes roughly 30–45 seconds).
5. **No scrollbars, no ellipses in cards, no clipped labels or descenders.**
6. **Signs and colours**: negatives red, positives green, one negative convention everywhere.
7. **Sort order** matches the table next to the chart.
8. **Blanks explained**: a blank last-year figure on a store that opened this year is right. A blank
   hero card is not.
9. **Every slicer pick and the reset**, then **every page** again.
10. **Grep the accessibility text.** `scripts/capture_pages.py` writes a `.txt` next to every `.png`.
    Search it for `wrong`, `See details`, `(Blank)`, and count digits. The script prints a digit
    count and an error-marker count per page, so a blank page is a number, not an impression.

Microsoft's `skills-for-fabric` ships the generic version of this list in
`references/screenshot-review.md` (full path in 2.3), under the same headline: *do not rely only
on structural validation.*

### The loop

```
snapshot   cp -r report-template .backup-roundN/
edit       local folder only; date filters via
           python3 scripts/date_filters.py <visual.json> latest-day|window-weeks|this-week
validate   powerbi-report-author validate report-template --format json      # errorCount must be 0
deploy     python3 scripts/deploy_report.py "ORG-Daily Trading.Report"
capture    python3 scripts/capture_pages.py 00000000-0000-0000-0000-000000000000 shots/roundN 60
look       open every PNG; run the checklist above; grep every .txt
fix        back to edit
```

DAX spot-checks go through `python3 scripts/validate.py --file query.dax` — batched into one query,
and only when the picture raises a question.

### When to stop

Stop when all four hold:

1. every done-criteria number ties **on screen**;
2. every user state above has been seen **after the last deploy** — any deploy re-opens the loop;
3. the theme file is byte-identical to the approved one;
4. the validator reports `errorCount: 0` and `python3 tests/test_guardrails.py` is green.

Stop early on a capacity message: wait at least 30 minutes, then one light probe. And never
re-verify by fanning out DAX what a single screenshot can show.

## 1.4 Running an executive review: lenses and a skeptic pass

This is the process that found the six traps in 1.1, in one evening, with zero changes made to the
report. Use it before a rebuild, and again on the screenshots afterwards.

1. **One brief for everyone.** Write a single brief: what the report is, who reads it, a digest of
   what each visual really queries (read it out of the PBIR JSON, not out of the visual titles),
   what is on screen today as *text*, the facts already established from the model with every
   hypothesis marked as one, the hard constraints, and what has already been fixed. Attach ground
   truth pulled read-only by DAX, and a screenshot plus accessibility dump of every page.

2. **Five lenses in parallel, same brief.** CEO (*"do I trust this in ten seconds?"*), Trading
   Director (*"what call do I make this morning?"*), Finance Director (*"does it foot, and on what
   basis?"*), data-integrity auditor (*"does every figure tie to the model, and what is it really
   measuring?"*), dashboard designer (*"hierarchy, labels, legibility"*). Each returns a
   one-paragraph verdict plus findings in a fixed record:

   ```
   id · title · page · severity · lenses · what_exec_sees · why_it_matters ·
   proposed_change · effort · evidence · theme
   ```

   `what_exec_sees` is the discipline in that record: it forces the reviewer to quote the screen
   rather than the JSON.

3. **Merge, keeping the lens list.** The reference review produced 24 findings. Five of the six
   blockers were seen by four or five lenses; the specialist catches came from one or two — the
   margin-base blocker from the Finance and auditor lenses only, the missing data labels from the
   auditor, the grid and font items from the designer. That spread is the whole argument for five
   lenses instead of one "expert".

4. **A skeptic pass.** Hand the findings, one at a time, to a *separate* agent whose job is to
   refute each one using the screen, the JSON and read-only DAX. Store the result on the finding as
   `verify: {refuted, reason}`. On the reference build 12 were checked and 0 refuted — but it was
   not a rubber stamp: one was upheld "with one correction", one was downgraded from blocker to
   major (*"the number is correct; the label is missing"*), and one had its count corrected. Keep
   the corrections; they are the value.

5. **A plan the owner can decide from.** Plain-language answer, a table of checked facts, then
   groups: **A** fix before any director sees it, **B** make it actionable, **C** polish. Every step
   carries an effort estimate, and every open question is a `decision` line with **two options and a
   recommendation** — not an essay. List separately what was inferred rather than proven.

6. **Theme observations are recorded, not proposed.** The lock in guardrail 6 applies to reviews
   too. Write the finding, mark it "not implemented — theme locked", move on.

7. **Review again after the build, on screenshots only.** Four seats this time (CEO, Trading,
   Finance, designer), each item carrying `what_you_see` and an exact `proposed_change` naming the
   visual and its position. The reference pass produced 30 items: 6 must, 19 should, 5 nice.

**Rules distilled:**

- Give every lens the same ground truth, so disagreement is about meaning, not data.
- Never accept a finding without an `evidence` field naming a file, a screenshot or a DAX result.
- Let the skeptic downgrade and correct, and keep those corrections in the record.
- Put every decision to the owner as two options with a recommendation.
- **The owner's own eye is a lens.** Schedule it. On the reference build the owner caught two things
  four agent seats had missed.

The Microsoft `powerbi-report-planning` skill states the same gate in one line: *do not build before
the user approves the locked report spec.*

---

# Part 2 — Toolchain: what to use, when, and how

Everything in the reference build ran from one Linux box, one repo, one logged-in browser profile
and one read-only model. This part lists every tool, when to reach for it and the exact command.

## 2.1 The map

| Job | Tool | Entry point |
|---|---|---|
| Find the workspace and model ids, export the model as TMDL, write the ids into config | `scripts/discover.py` | `python3 scripts/discover.py` |
| Push a report folder to the workspace | `scripts/deploy_report.py` | `python3 scripts/deploy_report.py "ORG-Daily Trading.Report"` |
| Put self-maintaining date filters on a visual | `scripts/date_filters.py` | `python3 scripts/date_filters.py <visual.json> latest-day` |
| See every page after a deploy | `scripts/capture_pages.py` | `python3 scripts/capture_pages.py <report-item-id> shots/roundN 60` |
| Run read-only DAX against the model | `scripts/validate.py` | `python3 scripts/validate.py --file query.dax` |
| Check the guardrails after any script edit | `tests/test_guardrails.py` | `python3 tests/test_guardrails.py` |
| Check nothing secret is about to be committed | `tools/secret_scan.py` | `python3 tools/secret_scan.py .` |
| Know the PBIR rules (the JSON shapes) | Microsoft `skills-for-fabric` on GitHub (not in this repo; the rules used here are copied into `docs/reference/snippets/README.md`) | see 2.3 |
| Look up a property name; validate the folder | the PBIR authoring CLI (`npm i -g @microsoft/powerbi-report-authoring-cli`, or `npx -y @microsoft/powerbi-report-authoring-cli …`) | `powerbi-report-author validate report-template --format json` |
| Click, read and screenshot the live report | `scripts/capture_pages.py` — Playwright for Python on a persistent, signed-in Chromium profile | `python3 scripts/capture_pages.py <report-item-id> shots/roundN 60`; see 2.2 and 2.5 |

## 2.2 The repo and its scripts

Layout:

```
config.yaml                     ids, prefixes, date-column names, capture settings — the single source of parameters
report-template/                a PBIR report item folder: .platform, definition.pbir, definition/
docs/                           this playbook, measures, PBIR snippets
scripts/                        discover · deploy_report · validate · date_filters · check_report · capture_pages · refresh
tests/test_guardrails.py        offline guardrail tests — no tenant, no network
tools/secret_scan.py            GUID / token / e-mail scan, also wired into CI
.github/workflows/validate.yml  guardrail tests + PBIR validation + secret scan on every push
```

Never hard-code an id in a script. `config.yaml` holds the workspace name and id, the model name and
id, the `deploy:` rules (`item_prefix`, `report_measure_prefix`, `filter_marker`,
`allowed_model_ids`, `allow_refresh`), the `date_filters:` column names and the `capture:` settings
— `config.example.yaml` lists every key. There are no freshness thresholds: freshness is read with
`refresh.py --history` and one DAX row, and judged by a person. `discover.py` writes the two ids
back into it, in place, keeping your comments.

### discover.py

**When:** first run against a new tenant, and any time the model changes shape.

It finds the workspace by name, finds the semantic model inside it by name, verifies that the same
ids work on the Power BI REST API (workspace id equals group id, model id equals dataset id), pulls
the model definition as TMDL, decodes every part into `schema/`, writes the ids into `config.yaml`,
and prints a table-by-table summary of columns and measures.

Two details worth keeping in your fork: it clears `schema/` before each run, so a renamed or deleted
table cannot leave a stale `.tmdl` behind to poison your DAX authoring; and it refuses any
definition part whose path escapes the folder.

This is also your model-contract check. Read the printed summary against Part 0, 0.4 before you
write a single visual.

### deploy_report.py

**When:** after every batch of local edits that passed validation.

Idempotent by display name: it creates the item if the name is new, updates it otherwise. It
base64-packs every file under the folder, skips hidden files at any depth (but keeps the root
`.platform`, which is a real definition part), posts `updateDefinition?updateMetadata=True`, and
polls the long-running operation.

It refuses four things **before any HTTP call**:

```
GUARDRAIL: refusing to deploy '<name>' — every item we create must be prefixed 'ORG-'.
GUARDRAIL: definition.pbir must bind byConnection to the existing semantic model.
           byPath bindings are refused (they would create a new model in the workspace).
GUARDRAIL: definition.pbir binds semanticmodelid=<guid> but config.yaml says the target
           model is <guid>.
GUARDRAIL: workspace item '<name>' was not created by us — refusing to update it.
```

The third refusal is also what a fresh copy of the template hits: its `definition.pbir` ships with
the zero `semanticmodelid`. `python3 scripts/deploy_report.py "<folder>" --bind` rewrites the
connection string from `config.yaml` (workspace name, model name, model id) before the guardrails
run — do it once, or edit the string by hand. The refusal has an escape hatch for the case where
your report binds to a production model that is not the one in `config.yaml`:

```yaml
deploy:
  item_prefix: ORG-
  allowed_model_ids:
    - 00000000-0000-0000-0000-000000000000    # the production model this report binds to
```

Any GUID not listed still exits. **TESTED:** the offline test suite covers the prefix refusal, the
`byPath` refusal, the wrong-model refusal and `--bind`, exercises the allowed-id path with a fake
folder, and checks that `report-template/` is deployable and passes `check_report.py` (your
`*.Report/` working folders are gitignored and not tested — run `check_report.py` on them
yourself). **UNTESTED:** the "was not created by us" refusal has no test, because it needs a live
workspace listing — mock the listing call if you want to close that gap.

### date_filters.py

**When:** on every visual that must show the latest traded day or a trend window. **Never hand-write
these filters.** The script replaces only the five filter names it writes (`<marker>LatestDayName`,
`LatestWeek`, `WindowWeeks`, `TradedDays`, `WindowDays`; the marker is `deploy.filter_marker`,
default `org`, independent of the item prefix) and leaves every other filter alone, so it is safe
to re-run — `none` on a slicer keeps its `orgNotBlank` and `orgRecentWeeks`.

```
python3 scripts/date_filters.py <visual.json> latest-day|window-weeks|this-week|window-days|none [--weeks N]
```

| Kind | What it adds | Use for | Status |
|---|---|---|---|
| `latest-day` (the day pins) | `TopN 1` on `'Date'[DayName]` **and** `TopN 1` on `'Date'[WeekLabel]`, each ordered by `Max('Date'[Date])` descending over rows where `HasSales = true` | every latest-traded-day card, matrix or bar built on a model measure | **TESTED** — last-year and last-week values tie exactly to a read-only DAX check |
| `window-weeks` | `TopN 3` on `'Date'[WeekLabel]` + a categorical `HasSales = true` filter | trend charts with `'Date'[Date]` on the axis | **TESTED** |
| `this-week` | the same shape with `TopN 1` | a week-to-date-by-day matrix | **TESTED** |
| `window-days` | `TopN 14` on `'Date'[Date]` | **banned** — see below | **TESTED wrong** |
| `none` | strips the script's filters | year-to-date cards bound to `RM YTD …` report measures, which must see no date filter | **TESTED** |

**Why the pins sit on `DayName` and `WeekLabel` and not on `'Date'[Date]`.** A calculation group
keeps *non-calendar* Date columns applied when it shifts to last week or last year, but it *replaces*
a `'Date'[Date]` filter with the whole shifted week. So a date-based window makes the `LY` calc item
return the entire last-year week on every single day — the flat last-year columns in the see-it
table above. Proven with one read-only query of the shape:

```
Date          [TY]        [LY via measure]   [LY via calc item]   [Budget]
2026-08-10    1,234,567   1,200,000          8,400,000            1,300,000
2026-08-11    1,111,111   1,150,000          8,400,000            1,250,000
2026-08-17    1,000,000   1,100,000          7,700,000            1,200,000
```

(numbers illustrative). The last-year column via the calc item is the same weekly total on every day
of the week; the report measure version is per day. That is the whole bug, in one table.

Self-check: `python3 scripts/date_filters.py --selftest`.

**Two limits, both TESTED:** a `TopN` subquery does not inherit the other filters on the visual, so a
store `TopN` cannot coexist with the day pins or the slicers; and a visual-level filter on a *report*
measure renders as *"Something's wrong with one or more filters"*. Both are fixed the same way — put
the ranking logic inside a report measure (`RANKX` over `ALLSELECTED(...)`, blank outside the range)
and leave the visual's filters alone.

### capture_pages.py

**When:** once per deploy, to see every page.

```
pip install playwright && python3 -m playwright install chromium          # once
python3 scripts/capture_pages.py <report-item-id> shots/roundN 60          # first run: a window opens, sign in once
python3 scripts/capture_pages.py <report-item-id> shots/roundN 60 --headless
python3 scripts/capture_pages.py --url <report url> --out shots/roundN --settle 60 --profile .browser-profile --rail-wait 45
```

Playwright for Python, not a browser server: the script launches its own Chromium with a
**persistent profile directory** (`capture.browser_profile_dir`, default `./.browser-profile`,
gitignored). The first run opens a window so you can sign in; the profile keeps the session, so
every later run can take `--headless`. (The first run needs a display — `xvfb-run` on a headless
server.) An item id becomes `<capture.app_base>/groups/<workspace.id>/reports/<id>` — set
`capture.app_base` for a sovereign or GCC portal. The third positional argument is the settle time
in seconds after each page click (default 60, `capture.settle_seconds`; 60 was needed on a busy
tenant). It writes `<out>/<n>-<page>.png` and `<n>-<page>.txt` — the accessibility text, so numbers
can be grepped instead of squinted at — prints a digit count plus a count of Power BI error markers
per page, and exits 1 if any page shows an error banner or could not be opened.

Three design decisions are baked into it, each learned the hard way:

1. It **navigates to the report URL first** (`page.goto`). Clicking page names in an already-open
   tab keeps serving the *old* definition — the first round of screenshots after a deploy showed the
   previous build until the reload was added. TESTED (T27).
2. The first page load after a definition update needs about 30–45 seconds; the script polls the
   left rail every 5 s for up to `--rail-wait` seconds (default 45) until the page tabs appear, and
   waits up to 10 minutes while a sign-in page is showing (T34).
3. **Page switches are clicks on the page name in the left rail** (`role=tab`). These keep working
   when a full navigation fails (T30).

Tab-finding, session lifetimes and ping timeouts (T28, T29, T32, T33) only matter if you drive a
shared browser through an MCP server instead — see 2.5.

### validate.py — read-only DAX

**When:** to tie a number on screen to the model.

It posts `executeQueries` — a read — against the model in `config.yaml`.

```
python3 scripts/validate.py "EVALUATE ROW(\"v\", [Sales])"
python3 scripts/validate.py --file query.dax --json
python3 scripts/validate.py --file query.dax --limit 0        # row count only
```

Two things to keep if you rewrite it. First, `executeQueries` errors can appear at **three levels
inside an HTTP 200** — on the payload, on the result, and on the table — including when a row or
size limit truncates the data. Check all three or you will read partial data as fact. Second, a 401
or 403 usually means either missing Build permission on the dataset or the tenant setting *Dataset
Execute Queries REST API* being switched off; say both in the error message, or the next person
spends an hour on the wrong one.

**Test a report measure the way a single card runs it:**

```
DEFINE MEASURE 'Measures'[X] = <the measure body>
EVALUATE ROW("v", [X])
```

with **only that one measure defined**. Defining them all together hides the "cannot be determined"
error that appears when one report measure references another — a real trap, because the card that
references it will fail in the service while your batch query passed.

### tests/test_guardrails.py

**When:** after touching any script. Offline, no tenant, seconds.

It builds fake report folders in a temp directory and asserts the deploy refusals fire: a
non-prefixed display name, a `byPath` binding, a model GUID that is not allowed. It checks that
`config.example.yaml` carries every key the scripts read, that `report-template/` is deployable and
passes `check_report.py`, that `--bind` writes the binding from config, that `discover.py`'s config
rewrite keeps every comment, that `secret_scan.py` skips gitignored paths, and it shells out to
each script's own `--selftest`. The date-filter tests compare the snippets and the template against
the names in `config.yaml`, so a renamed fork passes when its config and its files agree. Add a
case here before you add a guardrail anywhere else — this file is the cheapest place in the repo
to be right.

`tools/secret_scan.py` is the other half of the same idea: it fails on any GUID that is not the
all-zero placeholder, any e-mail address, or any token-shaped string — in what git would commit;
gitignored paths (`config.yaml`, `schema/`, `captures/`, your `*.Report/` folders) are skipped, so
a configured checkout still passes. Both run in CI on every push (`.github/workflows/validate.yml`),
alongside PBIR validation of `report-template/`.

## 2.3 The Microsoft skills-for-fabric skills

Microsoft publishes a set of agent skills for Power BI and Fabric work at
**`microsoft/skills-for-fabric`** on GitHub. Five of them matter here. **None of their files are in
this repo.** Every bare file name in this playbook and its parts — `filters.md`, `slicers.md`,
`card.md`, `table.md`, `cartesian.md`, `textbox.md`, `conditional-formatting.md`,
`powerbi-report-author-cli.md`, `screenshot-review.md`, `SKILL.md` — means
`skills-for-fabric` **`skills/powerbi-report-authoring/references/<file>`**:
<https://github.com/microsoft/skills-for-fabric/tree/main/skills/powerbi-report-authoring/references>
(the same files sit under `plugins/powerbi-authoring/skills/powerbi-report-authoring/references/`).
The rules quoted here were re-read at commit `714ea2f` (2026-08-27); the handful this repo actually
leans on are copied into `docs/reference/snippets/README.md`, so a clone is self-sufficient for them. To use
the skills with an agent, clone that repo and install them where your agent tooling looks for
skills; if the loader cannot see them, read the `SKILL.md` and `references/*.md` files straight off
disk or on GitHub — they are plain Markdown and they are the reference this playbook defers to for
JSON shapes.

| Skill | Use it for | Do not use it for |
|---|---|---|
| `powerbi-report-authoring` | PBIR mechanics: pages, visuals, filters, slicers, formatting, validation. The reference build followed it. | design choices, planning, Fabric item CRUD |
| `powerbi-report-design` | look and critique *before* writing files: chart choice, layout grid, accessibility, producing a design brief | writing any JSON — it says so itself |
| `powerbi-report-planning` | greenfield work: define, inspect the model, lock a report spec, get approval, then build | small edits to an existing report |
| `powerbi-report-management` | Fabric item CRUD over the REST API | content authoring |
| `semantic-model-authoring` | TMDL, measures, DAX rules, model deployment — only ever against a model **you own** | reports, RLS |

Read these first (all in that `references/` folder):

| File | What it settles |
|---|---|
| `filters.md` | the `TopN` shape; a `TopN` filter can only be a **visual-level** filter; `OrderBy.Expression` must be an `Aggregation`, not a `Measure`; direction 1 is bottom and 2 is top; inside `Where` use `Source`, not `Entity` |
| `slicers.md` | dropdown height arithmetic (`h = 60 + top padding + bottom padding`); declare a `padding` visual-container object whenever you set any other one; sync groups |
| `card.md` | the data role is `Data`, not `Fields`; one callout per card visual if you need to size it |
| `table.md` | `tableEx` versus `pivotTable`, `displayName` header overrides, the totals object |
| `cartesian.md` | combo-chart roles, `sortDefinition`, labels, legend, value axis |
| `textbox.md` | the native `paragraphs` array — the wrapped form validates and then renders invisible |
| `conditional-formatting.md` | selector rules per visual type: a matrix needs both `dataViewWildcard` and `metadata`, charts need `dataPoint` with no metadata |
| `powerbi-report-author-cli.md` | the CLI command table (2.4) |
| `screenshot-review.md` | the generic version of the see-it checklist |

**One gap to plan around.** The authoring skill's render loop assumes Power BI Desktop and its CLI.
On a headless Linux box that is not available (TESTED: no such binary), so section 2.5 replaces that
loop with the browser. Everything else in the skill applies unchanged.

The skill's own advice on large builds matches what worked here: split the work by page or visual
family, give each subagent the relevant brief excerpt, the exact fields and measures and the layout
contract, and have it return scoped PBIR JSON for the owning agent to integrate and validate.

## 2.4 The PBIR authoring CLI

The CLI is the source of truth for PBIR authoring details. Examples and memory are not. In practice
that means one rule: **never guess a property name.**

It is `@microsoft/powerbi-report-authoring-cli` on npm. `npm i -g @microsoft/powerbi-report-authoring-cli`
puts the `powerbi-report-author` command on your PATH — the form the playbook, the spec and the
checklists use. With nothing installed, `npx -y @microsoft/powerbi-report-authoring-cli <same
arguments>` runs it (the README and CI use that form).

```
powerbi-report-author validate report-template --format json
powerbi-report-author catalog describe <visualType>
powerbi-report-author formatting list-objects <visualType>
powerbi-report-author formatting describe-object <visualType> <object>
powerbi-report-author formatting describe-property <visualType> <object> <property>
powerbi-report-author formatting search <visualType> <regex>
```

The CI job runs the same validation through `npx`, so a fork needs nothing installed globally to get
the check (`.github/workflows/validate.yml`).

`validate` returns an envelope: read `data.errorCount` and `data.diagnostics`. The rule from the
build spec is `errorCount: 0` after every batch and before every deploy. Warnings are read, not
automatically fixed — the finished reference report validated at `errorCount 0` with 72 warnings,
all of them understood and explained in Part 3. `validate` also checks layout bounds (negative x or
y, out-of-bounds width or height) but **not overlaps**; overlap checking is an offline script of your
own plus the screenshots.

Three lookups that earned their keep on the reference build:

1. **Budget as a line on the same axis as the columns.** `formatting describe-object
   lineClusteredColumnComboChart valueAxis` reveals `secShow` ("Show secondary") next to
   `alignZeros`. Set `secShow` to false and both series share one scale — otherwise the budget line
   silently gets its own axis and every visual comparison on that chart is a lie.
2. **A wrong guess fails loudly.** `describe-property slicer general orientation` returns
   `FORMATTING_PROP_UNKNOWN` together with the available property names, so one command replaces a
   guessing loop.
3. **The blank-page slicer bug, explained in one line.** `describe-property slicer selection
   strictSingleSelect` says: *if no item is selected, the first available will be automatically
   chosen.* The first item in a date-column dropdown is `(Blank)`. That is the whole mechanism
   behind the blank page in 1.3 (TESTED). Ship slicers with `singleSelect` true,
   `strictSingleSelect` false, `selectAllCheckboxEnabled` false, and a "not blank" advanced filter
   on the field.

## 2.5 The browser: seeing what the audience sees

Nothing in the API tells you a visual rendered blank. Every round of the reference build was judged
on screenshots.

Drive a **real, logged-in browser profile**. The shipped way is `scripts/capture_pages.py` (2.2):
Playwright for Python launching its own Chromium on a persistent user-data directory
(`.browser-profile/`), signed in once by hand, `--headless` afterwards. What holds for any driver:

- **Reload the report URL after every deploy.** A page click alone keeps the old definition.
- **Take both artefacts**: the screenshot (PNG) *and* the accessibility snapshot (text). The
  snapshot turns "is 1,234,567 on the page?" into a grep instead of a squint.
- **Slicer states are driven by script**: click the dropdown, pick the value, screenshot, reset.
  Derive the element references from the accessibility snapshot each run rather than saving
  hard-coded selectors — the reference build did not keep its slicer scripts, which makes that exact
  recipe **UNTESTED** as written (the shipped script captures the default state only).
- **Never click Share, Subscribe or Send.** Guardrail 7: the owner sends, not the agent.

**Only if you drive the browser through an MCP server** (a Playwright MCP endpoint on a shared,
logged-in browser — how the reference build did it; none of this applies to the shipped script):

- **Check which browser automation you are actually talking to.** If your environment offers more
  than one endpoint, a wrong one returns a *logged-out* page that looks perfectly valid and is
  completely wrong. A login wall or missing data means "check the endpoint" before it means "debug
  the page" (T32).
- **A session sees every tab in the browser. Never close or navigate a tab you did not create.**
  Pick the tab whose URL contains the report item id, never by title or index (T29).
- **One session per page**; re-create it for the next one. Sessions expire in 60–90 seconds (T28),
  and a short ping timeout kills slow page loads (T33).

## 2.6 DAX tie-outs: read-only, batched, one agent

`executeQueries` is a read and stays allowed on a shared model. It still runs under your identity and
still burns shared capacity, so:

1. **Batch.** One `SUMMARIZECOLUMNS` returning this year, last year, the calc-item version and
   budget per day beats fifteen `ROW()` calls — and, as the table in 2.2 shows, comparing the
   columns side by side is what exposes the bug.
2. **Never fan out across agents.** Four parallel verifier agents each running DAX was one direct
   cause of a capacity throttle that also broke a report other people were reading.
3. **Prefer offline checks.** Pull the deployed definition back with `getDefinition` and diff it
   against the local folder; assert your PBIR JSON against the spec with a small script. Neither
   costs the model anything.
4. **Reuse established values.** Keep the tested numbers in the spec's "model facts" block so the
   next session does not re-derive them from the tenant.

## 2.7 Workflow and agents

The shape that worked: **one builder per page, non-overlapping folders** → validate → deploy →
screenshot every page → verify against the spec → targeted fixes → redeploy → final check. Two fix
rounds, maximum.

- Each page agent touches only `definition/pages/<its page id>/`. Nothing else. Not `report.json`,
  not `pages.json`, not `reportExtensions.json`, not the theme, not another page.
- **The main thread owns the shared files**: the header, the report measures, the theme, the deploy
  and the capture. Page agents do not deploy.
- **Briefs are spec-driven.** Each agent gets its page's section of the build spec, the visual ids
  to copy shapes from, the expected numbers, and a required return format: the list of visuals it
  wrote, plus everything it could not do.
- **Two agents at a time.** More than that is UNTESTED here; the risk is browser and tenant
  contention, not agent confusion.
- **Verify delegated work before it ships**: validator at zero errors, then your own eyes on the
  screenshots against the spec's done criteria. A subagent reporting success is not evidence.

## 2.8 Capacity etiquette

The reference build hit *"Unable to load model due to reaching capacity limits — your organization's
compute capacity has exceeded its limits"* after roughly two hours of parallel DAX, six deploys and
about twenty-five page renders, all under one identity. It also stopped the *original* report
rendering for everyone else. That is the real cost: not your build failing, but somebody else's
morning report going dark.

Standing rules:

- One render pass per deploy — one capture run, one PNG per page.
- Batch DAX into a single query; never fan it out across agents.
- Prefer offline checks (definition diff, JSON versus spec) over live queries.
- On the throttle message: **stop every query and every render.** Wait at least 30 minutes, then run
  one light probe — a single page load that prints a digit count and whether the capacity text is on
  the page — before resuming.
- Deploy in batches. Six deploys in an evening is a smell; each one costs a render pass to verify.
