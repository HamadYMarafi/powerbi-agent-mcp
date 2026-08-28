---
name: powerbi-dashboard-review
description: Review, critique, or "exec-proof" a Power BI / Microsoft Fabric report before a director or CEO sees it. Use before showing a page to executives, when the user asks to sanity-check or review a dashboard, or asks whether a report "makes sense to a CEO". Runs five read-only lenses (CEO, trading director, finance director, data auditor, designer) over the same screenshots and ground truth, then a skeptic pass that tries to refute every finding. The reviewer changes nothing.
---

# Power BI dashboard review

Find what is wrong with a report before a director does. Arithmetically
correct numbers that still tell a false story are the whole reason this skill
exists — `docs/reference/PLAYBOOK.md` 1.1. The reviewer is **read-only**: it
produces a findings table and a change plan, and never edits or deploys.

## Procedure

1. **Write one shared brief** before anything else: what the report is, who
   reads it and who has seen it, a digest of what each visual *really*
   queries — read out of the PBIR JSON via `get_report_definition`, not out
   of visual titles — what is on screen today as plain text, the facts
   already established from the model with every hypothesis marked as one,
   the hard constraints (model read-only, no refresh, theme locked or open,
   "the audience will not touch a slicer"), and what has already been fixed.
   Give every lens in step 4 this same brief, so disagreement is about
   meaning, not data.
2. `capture_pages(target, out_dir, ...)` for every page in its **default**
   state first — nothing clicked, because for an executive report the
   default state is the product. Then repeat for each slicer pick and the
   reset button. Do not skip straight to slicer states; the default-state
   screenshots are what most readers actually see.
3. Pull ground truth with one batched `run_dax(query, ...)` — latest traded
   day, week-to-date, year-to-date, last year same weekday, budget, per
   channel. One query, not one per number (`docs/reference/PLAYBOOK.md` 2.6,
   2.8 — capacity etiquette applies to a review too).
4. Run **five lenses** over the same brief, screenshots and ground truth,
   each returning a one-paragraph verdict plus findings in this record: `id ·
   title · page · severity · lenses · what_exec_sees · why_it_matters ·
   proposed_change · effort · evidence · theme`. `what_exec_sees` is the
   discipline: it forces a quote of the screen, not the JSON. The questions
   each seat asks in its first ten seconds:

   | Seat | Questions |
   |---|---|
   | CEO | Which day am I looking at, and is it the latest? What is the headline — day, week, year? Do I trust the biggest red number? |
   | Trading director | Which calls do I make this morning? Is last year comparable (holiday)? Is online measured on orders or on dispatches? Is the day budget phased, so "vs budget" is partly calendar? |
   | Finance director | What is each percentage a percentage *of*? Is net sales on the page at all? Do the period-to-date figures tie to the finance pack? Which tax basis, per column? |
   | Data auditor | Does every number tie to the model to the unit? Does a report-level filter silently drop a member? Is the day pinned to a literal or self-maintaining? |
   | Designer | Is there a headline and a date? Are labels or axes truncated? Value order or alphabetical? Empty bands? Theme untouched? |

   **Never propose a theme, colour or font change unless the owner explicitly
   asked** — the theme is locked once approved (`docs/reference/PLAYBOOK.md`
   1.2). Record a design observation and move on.
5. Merge the five lenses' findings, keeping the lens list per finding — a
   finding seen by four or five lenses is a different kind of blocker than
   one seen by a single specialist.
6. Run a **skeptic pass**: separately try to refute every finding using the
   screen, the JSON (`get_report_definition`) and read-only `run_dax`. Record
   `verify: {refuted, reason}` on each finding. This is not a rubber stamp —
   expect it to downgrade or correct some findings, not only confirm them.
7. Output a findings table — `id, severity, what the page says, what is
   true, evidence, fix, TESTED/UNTESTED` — and a change plan grouped **A**
   fix before any director sees it, **B** make it actionable, **C** polish.
   Every open question is a `decision` line: two options and a
   recommendation, not an essay. The owner approves the plan before anything
   gets built.
8. After a rebuild driven by this plan, run the review again on the new
   screenshots only — a shorter second pass (CEO, trading, finance, designer
   is enough) catches what a fresh render introduced. Also schedule **the
   owner's own eye** as a lens: on the reference build it caught findings
   all five agent seats had missed.

## Traps to remember

Source: `docs/reference/PLAYBOOK.md` 1.1 and 1.4; review section of
`docs/reference/CHECKLISTS.md`. Six traps a validator-clean, arithmetically
correct report still had, none of them visible from JSON or a DAX tie-out
alone: a public-holiday LY comparator read as a fake decline; an
online-sales tile dated by dispatch rather than by order, telling the
opposite story from demand; a margin % whose base (net sales ex tax) was
never on the page; a "this week" slicer holding a saved literal weekday,
stale by the next day and blank on Monday; a report-level filter silently
dropping one of several channels from the total; a daily budget phased on
last year's shape, making "vs budget" partly a calendar artefact. Full
catalogue, data-quality section: `docs/reference/PLAYBOOK_PART4.md`
(T35–T45).

## Definition of done

- Every finding carries an `evidence` field naming a screenshot, a JSON path
  or a DAX result — no evidence, no finding.
- Every finding has been through the skeptic pass, with `verify` recorded.
- The change plan has a decision line (two options + a recommendation) for
  every open question, and the owner has not yet been asked to approve a
  build.
- No file in the report folder has been edited or deployed by this skill.
