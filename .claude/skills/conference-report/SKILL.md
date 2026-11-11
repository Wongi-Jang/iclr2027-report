---
name: conference-report
description: Build a submission-and-review statistics report for an ML conference (ICLR, NeurIPS, ICML, or another OpenReview venue) - fetch from OpenReview, label papers against a concept taxonomy with the Batch API, aggregate, and publish a static site. Use when asked to analyse conference submissions, topic trends, review scores, or to add a new venue to this pipeline.
---

# Conference report pipeline

The mechanics are four commands. This skill is about the judgment calls that
make the numbers defensible - each one below was learned by getting it wrong.

## Run order

```bash
.venv/bin/python scripts/fetch.py --venue <v> --probe   # ALWAYS first
.venv/bin/python scripts/fetch.py --venue <v>
.venv/bin/python scripts/label.py --venue <v> --test 15 # validate before spending
.venv/bin/python scripts/label.py --venue <v> --submit
.venv/bin/python scripts/label.py --venue <v> --collect
.venv/bin/python scripts/aggregate.py --venue <v>
npm run build
```

Venues live in `venues.json`. Credentials live in `.env`
(`OPENREVIEW_USERNAME`, `OPENREVIEW_PASSWORD`, `ANTHROPIC_API_KEY`) - never ask
the user to paste these into chat; have them write the file.

## Rules that are not optional

**1. Probe before anything else, and read the `corpus` field.**
`--probe` reports the mix of accepted / rejected / withdrawn papers. This
decides what every chart means:

- `all-submissions` (ICLR): counts measure what the field *submits*.
- `accepted-only` (NeurIPS, ICML - ~95% accepted): counts measure what got
  *in*. Acceptance rates and withdrawal rates are not computable. Say so on
  the page; do not let a reader mistake one for the other.

A new venue needs a `venues.json` entry whose `corpus_note` states this in
plain words. The site prints it verbatim.

**2. Never compare ratings across years without checking the scale.**
ICLR used 1-10 in 2024-25, 0-10 in 2026 and 1-4 in 2027. `--probe` prints the
rating values it sees. If scales differ, do not normalise them into one chart -
drop the comparison and explain why.

**3. Build the taxonomy from the data, not from memory.**
Count keyword frequencies in the latest year, take the top ~200, and write
concepts with an `id`, a display `label`, a one-line `hint` (what the labeller
reads) and `aliases` (what the sanity check reads). Aliases never reach the
prompt - enriching them changes measurement, not labels, and needs no re-label.

**4. Measure label quality before spending, with `scripts/eval_labeller.py`.**
It needs no hand-labelling: papers whose *titles* name a concept unambiguously
must receive that concept. Run it on every prompt or model change. Reference
numbers on ICLR with 73 concepts:

| Configuration | Recall | Unsupported labels |
|---|---|---|
| Haiku 5.5, loose prompt | 78% | 46% |
| Haiku 5.5, tight prompt | 90% | 34% |
| **Haiku 5.5 + adaptive thinking** | **100%** | **12%** |
| Sonnet 5.5 | 100% | 19% |
| Haiku 5.5 + thinking, `effort: low` | 88% | 19% |

Adaptive thinking is what buys the accuracy; low effort breaks it. Do not
"optimise" it away.

**5. A high unsupported-label rate means one of two different things.**
Either the concept is a catch-all, or its alias list is too thin to recognise
legitimate phrasing. Sample the actual papers before deciding - narrowing a
hint that was working correctly breaks good labels. (`sci-ml` read as 79%
unsupported purely because no alias covered "MRI reconstruction".)

**6. Pin display names to the taxonomy that produced the labels.**
`aggregate.py` reads names from `data/topics.at-labelling.<venue>.json`, a
snapshot taken at labelling time, and refuses to run if the two drift apart.
After a re-label, copy `topics.json` over the snapshot. Without this, renaming
a concept silently relabels data it was never applied to.

**7. Quote costs including cache reads.**
`--test` prints uncached tokens only and understates the bill. The real cost
has four parts: input, output, cache writes, cache reads. On ICLR's 81,680
papers it came to **$9.06**, of which output (thinking tokens) was 44%. Measure
with `usage.cache_read_input_tokens` included before telling anyone a number.

## Things that look like savings and are not

- **Free OpenRouter models**: capped at 1,000 requests/day, so 81,680 papers
  takes 82 days - and unlocking that cap costs $10, more than the job.
- **Cheaper paid models**: losing the Batch API's 50% discount and prompt
  caching means a $0.05/M model costs *more* than Haiku does here.
- **Running it through an agent instead of the API**: ~33M tokens of reading,
  serial, and it leaves no re-runnable script.
- **Dropping the hints to shrink the prompt**: the longest hints are the ones
  doing the disambiguation work.

## Publishing

`src/active-report.js` selects which venue the built site shows - one line.
The site is per-venue; there is no venue switcher, and nobody has asked for one.
