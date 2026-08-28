# Contributing

This repo is an MCP server plus the method around it. The most valuable thing you can add is **a trap you
hit and how you proved it** — the JSON that validated and still rendered wrong, the filter
that silently changed the basis of a number, the slicer setting that opened the page blank.

One trap or one snippet per pull request. Small and provable beats broad and plausible.

## The one rule: every claim carries a label

Every mechanism claim in this repo is labelled, and the label says how it was proven:

- **TESTED** — you ran it and saw the result. Name where: a screenshot you took, the DAX
  query you ran, the validator output, the error text on the page. "It worked for me" with
  no artefact named is not TESTED.
- **UNTESTED** — plausible, read in docs, or inferred, but not proven here. Name the test
  that would prove it, so the next reader can settle it in one command.

Never upgrade a label without running the test. If you test an UNTESTED claim and it holds,
change the label and add the evidence in the same pull request. If it fails, say so and
delete the claim.

**Live output beats this repo.** If a page, a tool or an API contradicts a document here,
the page wins. Fix the document in the same pull request rather than working around it.

## Proposing a trap

Add it to `docs/reference/PLAYBOOK_PART4.md`, the traps catalogue, in this shape. Keep every field.

```
### T<n> — <one-line title>

What the page showed   The wrong thing, in the words on screen ("LY columns flat at the weekly total").
What was true          The right number or behaviour, with the query or file that proves it.
Cause                  The mechanism, in one or two sentences. TESTED (where) or UNTESTED (test that would settle it).
Fix                    The exact change: file, property, command. Copy-pasteable.
See it again           The state to put the report in to reproduce, in one line.
```

Two things make a trap worth merging: it survives the validator (i.e. the JSON is legal and
still wrong), and the fix is exact. A trap with no `Cause` is a bug report; keep it in an
issue until the cause is known.

## Proposing a snippet

Snippets go in `docs/reference/snippets/` as one `.json` file per shape, and must be:

- **Verbatim** from a report that rendered correctly — not typed from memory.
- **Minimal.** Only the properties that make the shape work. Delete positions, ids and
  formatting that carry no meaning.
- **Neutral.** Placeholders only: company `YourCo`, created items prefixed `ORG-`, report
  measures prefixed `RM `, ids `00000000-0000-0000-0000-000000000000`. No real store,
  brand, channel, colleague or figure. Use obviously illustrative numbers such as 1,234,567.
- **Attributed to a check.** State the visual type, the schema version it validated
  against, and what the snippet proves ("puts a budget line on the same axis as the
  columns: `valueAxis.secShow = false`").

DAX for a report measure goes in `docs/reference/measures/`, one `.dax` file per measure, using only
the columns in `docs/MODEL_CONTRACT.md`. If your measure needs a column the contract does not
name, propose the contract change in the same pull request and say what the column must
contain.

## Before you open a pull request

```
python3 tools/secret_scan.py .                                    # must print 0 hits (what git would commit; gitignored paths skipped)
python3 tests/test_guardrails.py                                  # offline, seconds
python3 scripts/date_filters.py --selftest
python3 scripts/check_report.py report-template                   # offline structural checks
npx -y @microsoft/powerbi-report-authoring-cli validate report-template --format json   # errorCount must be 0
```

Never commit a screenshot, a capture dump, a validator envelope, a `config.yaml` or your
`*.Report/` working folder. They carry real ids and real trading figures, and `.gitignore` already
excludes them.

Changes that remove a guardrail (the create-prefix check, the "never touch items we did not
create" check, the two gates on refresh) will not be merged. Make the guardrail
configurable if it is in your way, and keep the default strict.

## Style

Two readers: a BI developer at another company, and an AI agent following the repo as
instructions. Both need the same things.

- Plain, direct English. Short sentences. Answer first, detail after.
- Exact paths and exact commands, copy-pasteable, no placeholders inside a command except
  the ones the reader must obviously fill.
- Say what a thing does, not how careful you were.
- Keep the labels. A document with unlabelled claims is the failure mode this repo exists
  to fix.
