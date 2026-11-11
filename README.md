# ICLR 2027 in numbers

Submission, topic and review statistics for ICLR 2027, with 2024–2026 for comparison.
Built from the public OpenReview record.

**→ [ICLR 2027](https://wongi-jang.github.io/iclr2027-report/) · [NeurIPS 2025](https://wongi-jang.github.io/iclr2027-report/neurips.html)**

## Headline

| Year | Submissions | Growth |
|---|---|---|
| 2024 | 7,404 | — |
| 2025 | 11,672 | +58% |
| 2026 | 19,814 | +70% |
| 2027 | **42,790** | **+116%** |

## Other conferences

The pipeline takes `--venue` (`iclr`, `neurips`, `icml`; add more in
`venues.json`). **Always probe first** — it reports what a venue actually
exposes:

```bash
.venv/bin/python scripts/fetch.py --venue neurips --probe
```

This matters more than it sounds. ICLR publishes **every** submission;
NeurIPS and ICML publish essentially only **accepted** papers (~95%), so there
the same charts measure what got *in*, not what was *submitted*, and
acceptance and withdrawal rates cannot be computed at all. Rating scales also
move: ICLR ran 1–10, 0–10 then 1–4 across four years; NeurIPS went 1–10 (2024)
to 1–6 (2025). Never compare scores across years without checking.

`.claude/skills/conference-report/SKILL.md` carries the full judgment
checklist, including which apparent cost savings are false economies.

## How it works

```
scripts/fetch.py       OpenReview → data/raw/<venue>/<year>.jsonl  (gitignored, ~195 MB)
scripts/label.py       label every paper against topics.json via the Batch API
scripts/aggregate.py   → src/data/report.<venue>.json              (~25 KB, committed)
src/pages.js           the published pages and their nav order
npm run build          → dist/, deployed to Pages by .github/workflows/pages.yml
```

`data/labels.<venue>.jsonl` is committed on purpose: it is the output of about
$10 of API spend, carries no abstracts, and lets anyone reproduce every
published number by running `aggregate.py` alone. Only the raw papers are
gitignored.

`topics.json` is the taxonomy: 84 research concepts with aliases and
disambiguation hints. It is meant to be edited — re-run `label.py --submit`
and `aggregate.py` after changing it.

**Two taxonomy files, on purpose.** `data/topics.at-labelling.json` is a
snapshot of the taxonomy the current labels were made under (73 concepts);
`aggregate.py` reads display names from it, so editing `topics.json` can never
silently rename data it was never applied to. The published site therefore shows
73 concepts. After a re-label, copy `topics.json` over the snapshot.

The largest concept, "Benchmarks & evaluation (broad)", is a known catch-all —
it absorbs anything that evaluates something, not just benchmark releases. The
revised `topics.json` narrows it and adds 11 concepts (ML systems, agent
evaluation, data poisoning and others); applying it costs about $9.

### Labelling

Each paper's title, keywords and abstract go to Claude Haiku 5.5, which returns
up to three concept ids. `scripts/eval_labeller.py` measures quality without
hand-labelling anything: papers whose *titles* name a concept unambiguously must
receive that concept.

| Configuration | Recall | Labels/paper | Unsupported labels |
|---|---|---|---|
| Haiku, loose prompt | 78% | 3.18 | 46% |
| Haiku, tight prompt | 90% | 2.40 | 34% |
| **Haiku + thinking** | **100%** | **1.70** | **12%** |
| Sonnet 5.5 | 100% | 2.08 | 19% |

81,659 of 81,680 papers labelled; 21 batch failures.

## Caveats

- Concepts overlap. A paper carries up to three, so counts do not sum to the total.
- Withdrawn and desk-rejected papers are excluded from every statistic.
- ICLR changed its rating scale every year — 1–10 (2024–25), 0–10 (2026), **1–4 (2027)**.
  Scores are never compared across years.
- ICLR 2027 submissions are still anonymous, so tables show titles without authors.
- No 2027 decisions have been released; a high score is not an acceptance.

## Running it

```bash
python3 -m venv .venv && .venv/bin/pip install openreview-py anthropic
printf 'OPENREVIEW_USERNAME=...\nOPENREVIEW_PASSWORD=...\nANTHROPIC_API_KEY=...\n' > .env
.venv/bin/python scripts/fetch.py
.venv/bin/python scripts/label.py --submit && .venv/bin/python scripts/label.py --collect
.venv/bin/python scripts/aggregate.py
npm install && npm run dev
```

A full re-label of all four ICLR years costs **$9.06** on the Batch API —
input, output, cache writes and cache reads, of which output (thinking tokens)
is 44%. `--test` prints uncached tokens only and understates this.

## Venues covered

| Venue | Years | Papers | Corpus |
|---|---|---|---|
| ICLR | 2024–2027 | 81,680 | all submissions |
| NeurIPS | 2024–2025 | 9,776 | accepted only |

Not affiliated with ICLR, NeurIPS or OpenReview.
