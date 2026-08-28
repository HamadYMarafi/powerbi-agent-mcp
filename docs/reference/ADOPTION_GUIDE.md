# Adoption guide — from clone to an exec-reviewed page in a day

Ten steps. They assume one person, one working day, a semantic model you can read, and
permission to create items in a workspace. You do **not** need write access to the model.

| | Step | Time |
|---|---|---|
| 1 | Read the three ideas and the guardrails | 30 min |
| 2 | Map your model to the contract | 90 min |
| 3 | Set the config | 15 min |
| 4 | Rename the prefixes | 10 min |
| 5 | Pull ground truth once (the tie-out table) | 45 min |
| 6 | First deploy of the template | 20 min |
| 7 | First capture — see it | 30 min |
| 8 | Fix round one against the tie-out table | 90 min |
| 9 | First exec review | 60 min |
| 10 | Handover: write down what is TESTED | 30 min |

If you have two hours, not a day: steps 2, 3, 6, 7. A template deployed and looked at, with
the numbers untied, still tells you more than a week of planning.

---

## Step 1 — Read the three ideas and the guardrails (30 min)

`README.md`, then Part 1 of `docs/reference/PLAYBOOK.md`. The guardrails matter most if you work in a
shared workspace: they are what keeps your build from landing in someone else's audit log.

Decide now, and write it down:

- Who judges the default view, and what they will never touch. (If the answer is "the CEO,
  and they will never touch a slicer", the default state is the whole product.)
- The single question the page answers in ten seconds.

**Done when** those two lines exist in a document your team can see.

## Step 2 — Map your model to the contract (90 min)

This is the only step that is really about your company, and the only one that can fail
silently later. Open `docs/MODEL_CONTRACT.md` beside your model.

```bash
python3 scripts/discover.py    # exports the model definition into schema/ so you can read it
```

For every row of the contract, write one of three answers:

1. **Have it** — name your column. Example: the contract's `Date[WeekLabel]` is your
   `Calendar[Fiscal Week Name]`. The five Date columns go in the `date_filters:` block of
   `config.yaml` (`date_table`, `date_column`, `day_name_column`, `week_label_column`,
   `has_sales_column` — the block `config.example.yaml` ships). Every other name — tables,
   measures, calc items — is renamed inside the template and the DAX by the find/replace recipe
   in `docs/MODEL_CONTRACT.md` section 8.2; no config key carries those.
2. **Can derive it in the report** — a report measure can compute it at query time. The
   contract marks which rows allow this.
3. **Missing** — it has to exist in a model. Never add it to a shared model you do not own.
   Copy the model into an item you own, prefixed `ORG-`, add it there, and point the
   template at your copy while you negotiate the real change with the model owners.

Two rows are worth extra care, because everything else leans on them:

- **`Date[HasSales]`** (TRUE on days with loaded sales). Every "latest traded day"
  calculation anchors here. Without it you will pin to `TODAY()` and the page will be blank
  every morning until the data lands. If your model has no such flag, derive it: the last
  date with a real sales row, excluding cancellations and gift-card-style rows.
- **The time-intelligence calculation group** (`Current`, `LW`, `LY`, `vs LW %`, `vs LY %`,
  `YTD`, `YTD vs LY %`). If your model has separate last-year measures instead, that works
  too — but read the playbook's calculation-group traps before you wire a chart, because
  the failure mode ("last year" returning a whole week on every day) validates clean and
  looks plausible.

**Done when** every contract row has an answer, and you have run one read-only query that
returns your latest traded day:

```
EVALUATE ROW("latest", CALCULATE(MAX('Date'[Date]), 'Date'[HasSales] = TRUE))
```

## Step 3 — Set the config (15 min)

```bash
cp config.example.yaml config.yaml     # config.yaml is gitignored, and stays that way
$EDITOR config.yaml
python3 scripts/discover.py            # fills in the ids it can find
```

Set the workspace and model names, the `date_filters:` block from step 2, and leave every
safety default alone: refresh triggering off, the prefix check on, `filter_marker` as shipped.
`discover.py` rewrites only the two `id:` lines, so the comments you kept from the example stay.

**Done when** `python3 tests/test_guardrails.py` passes and one read-only query through
`python3 scripts/validate.py` returns your latest traded day. If the data is older than you
expected, that is a note to the model owners, never a refresh you trigger.

## Step 4 — Rename the prefixes (10 min)

Two prefixes, both configurable, both worth choosing deliberately because they end up in
front of colleagues:

- **Item prefix**, default `ORG-`. Every workspace item this repo creates starts with it.
  Pick something that reads as "built by the analytics automation", not a person's initials.
- **Report-measure prefix**, default `RM `. Marks a measure that lives in the report rather
  than the model, so nobody hunts for it in the model later.

```bash
grep -rn "ORG-\|RM " config.example.yaml docs/ report-template/ | head
```

- **Item prefix:** change `deploy.item_prefix` in `config.yaml` and the `displayName` in your
  report folder's `.platform`. Nothing inside the template moves: the marker at the front of
  the filter names (`orgLatestDayName` …) is its own key, `deploy.filter_marker`, default
  `org`, and it stays whatever the item prefix is. Leave it. If you must change it, also run
  `python3 scripts/date_filters.py <visual.json> latest-day` on each of the three hero cards
  (`visuals/444cf488b3be4d1336b4`, `39e033c6701e0262d09d`, `12b3e5028145ccf8e7d1`) and rename
  `orgNotBlank`, `orgRecentWeeks` and `orgRecentDays` by hand on the two slicers
  (`grep -rn '"org' report-template/definition` finds them — the `ORG-` grep above cannot).
- **Report-measure prefix:** change `deploy.report_measure_prefix`, then every `name` in
  `reportExtensions.json` and the `Property` / `queryRef` / `nativeQueryRef` of the two header
  cards. The validator does not see this; `check_report.py` does.

**Done when** all three are clean after the rename:

```bash
npx -y @microsoft/powerbi-report-authoring-cli validate report-template --format json   # errorCount 0
python3 scripts/check_report.py report-template --no-validator                          # 0 failures: pins found, RM names match
python3 tests/test_guardrails.py                                                        # green
```

The tests read `date_filters:` and `deploy.filter_marker` from `config.yaml` and compare the
snippets and the template against those names, so after a column rename (step 2, recipe 8.2)
they pass only when `config.yaml` names the renamed columns. A mismatch fails
`test_date_filter_shapes`, `test_date_filters_rerun_replaces_only_its_own` and
`date_filters.py --selftest` — on purpose.

## Step 5 — Pull ground truth once (45 min)

Write the numbers **before** you look at the page, or you will read the page and call it
right. One batched query, saved to a file. One query, not fifteen: your queries run under
your identity and burn shared capacity.

Pull, for the latest traded day and its comparators: total sales, sales last week, sales
last year, week to date, year to date, budget, and the two or three channel or region splits
your page will show.

Write them into a tie-out table — the template is in `docs/reference/PLAYBOOK_PART5.md`:

| Number | Where it will appear | Expected | Seen on screen |
|---|---|---|---|
| Day total | page 1 hero card | 1,234,567 | |
| vs last year % | page 1 hero card | −45.0% | |
| Year to date | page 1 tile | 123,456,789 | |

**Done when** the table is filled to the last column being empty, and saved outside the
repo (it holds real figures).

## Step 6 — First deploy of the template (20 min)

```bash
cp -r report-template "ORG-Daily Trading.Report"
$EDITOR "ORG-Daily Trading.Report/.platform"       # display name + a new logicalId
$EDITOR "ORG-Daily Trading.Report/definition/pages/ba68e70f8cb3263db789/visuals/97e504e652a65d840fd6/visual.json"
#   the title textbox prints the basis on the canvas: replace <channels> and <inc or ex tax> with yours
npx -y @microsoft/powerbi-report-authoring-cli validate "ORG-Daily Trading.Report" --format json
python3 scripts/check_report.py "ORG-Daily Trading.Report" --baseline report-template
python3 scripts/deploy_report.py "ORG-Daily Trading.Report" --bind
```

`--bind` writes `definition.pbir`'s `byConnection.connectionString` from `config.yaml`
(workspace name, model name, model id) — the template ships placeholders there, and without
the rewrite the deploy script stops at its own guardrail (*binds semanticmodelid=0000… but
config.yaml says …*). You can also edit the string by hand once; after that a plain
`deploy_report.py` is enough. The binding stays **by connection** to the model you configured.
A by-path binding would create a second model, and the deploy script refuses it.
`--baseline "<original>.Report"` replaces `report-template` only when you cloned an existing
report instead of starting from the template.

**Done when** the item exists in the workspace under your prefix, and no item you did not
create was touched.

## Step 7 — First capture: see it (30 min)

```bash
pip install playwright && python3 -m playwright install chromium   # once
python3 scripts/capture_pages.py <item id> captures/round1         # first run: a window opens — sign in once
python3 scripts/capture_pages.py <item id> captures/round1 --headless   # every later run
```

One PNG and one accessibility text file per page. The signed-in session lives in
`.browser-profile/` (gitignored). The first run needs a display for the sign-in — on a headless
server wrap it in `xvfb-run`. The first load after a definition update takes about 30–45
seconds; the capture polls for the page rail (`--rail-wait`, default 45 s), then settles
(`capture.settle_seconds`, default 60) before every screenshot.

Then look, in this order (the full list is the post-deploy review in `docs/reference/CHECKLISTS.md`):

1. The header reads a real date, a trading week, and how old the data is.
2. Every tie-out number from step 5, digit by digit — not "looks about right".
3. Count things: days on the trend, bars in a top-10, regions in a split.
4. No spinners, no error tiles, no `(Blank)`, no "Visuals are loading" after the settle time.
5. No scrollbars, no clipped labels, no ellipses in a card.
6. `grep -iE "wrong|see details|\(Blank\)" captures/round1/*.txt`

**Done when** you have written down what is wrong. Expect several things to be. That is the
point of the step.

## Step 8 — Fix round one (90 min)

Fix locally, validate, deploy, capture again. Never fix by trying a different filter in the
service and copying it back — the file is the source of truth.

The five most likely first-round problems, all in the traps catalogue (`docs/reference/PLAYBOOK_PART4.md`)
with exact fixes:

1. **A tile reads a wildly wrong year-to-date** — a date pin is leaking into a cumulative
   measure. Cumulative measures take no date filter.
2. **Last year's series is flat across a daily chart** — a date-column window is expanding
   the comparison to a whole week. Use `python3 scripts/date_filters.py <visual.json> window-weeks`.
3. **The page opens blank** — a slicer with strict single-select and no saved selection.
4. **A "bottom 10" contains positive numbers** — a top-N subquery ranking in its own
   context. Move the ranking into a measure.
5. **A number is right but means something else** — the basis is missing from the canvas.
   Add it to the label, in words the reader already uses.

**Done when** every tie-out number matches on screen, after the **last** deploy. A deploy
re-opens the loop; a page verified before it is not verified.

## Step 9 — First exec review (60 min)

Do not show a director a page nobody has argued with.

- Write the brief from `docs/reference/SPEC_TEMPLATE.md` and give five reviewers (or five agent lenses) the **same** brief, the same screenshots and
  the same ground truth: CEO, trading director, finance director, data auditor, designer.
  Same inputs is what makes their disagreement about meaning rather than data.
- Every finding needs a `what the exec sees` sentence quoting the screen, and an `evidence`
  field naming a file, a screenshot or a query result. No evidence, no finding.
- Hand the blockers to a skeptic told to refute each one. Keep the downgrades and the
  corrections; they are the most valuable output.
- Put every decision to the owner as **two options and a recommendation** — tax basis,
  self-maintaining filters versus a scheduled re-pin, include or label a channel, four
  pages or five.

**Done when** the owner has picked, and the page has been seen in every state a user can put
it in: default, each slicer pick, the reset, every page, and a fresh open.

## Step 10 — Handover (30 min)

Write the note that stops the next person re-learning today:

- What exists: the item, the folder, the page ids, the backups you took before each round.
- Every mechanism claim labelled **TESTED** (with the screenshot, query or file that proves
  it) or **UNTESTED** (with the test that would settle it). Facts without a "where" rot into
  folklore inside a month.
- The decisions still owed, and who owes them.
- The requests for the model owners: each one a single sentence, with the evidence attached,
  ready to send.
- The one-liner for next time: what to run first (capture once, read four screenshots).

**Done when** somebody who was not here could redeploy and re-verify from your note alone.

---

## What will break first, in order

1. **A column your model does not have** the way the contract expects. Step 2 is where you
   pay for it or where it ambushes you in step 7.
2. **The latest-traded-day anchor.** If your loads lag, the page must say how old the data
   is, on the canvas, in words.
3. **Comparison periods.** Public holidays, a 53-week year, a shifted fiscal calendar — all
   of them make a correct number tell a false story.
4. **Capacity.** Keep verification lean: one render pass per deploy, one batched query, and
   never fan queries across parallel agents.

## Contributing back

If you find a trap that is not in the catalogue (`docs/reference/PLAYBOOK_PART4.md`), `CONTRIBUTING.md`
has the record format.
Traps travel between companies far better than dashboards do.
