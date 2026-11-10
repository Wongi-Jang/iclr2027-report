"""Label papers against topics.json with Haiku 5.5.

  --test N    label N random 2027 papers synchronously, print results + token cost
  --submit    create Batch API jobs for every unlabelled paper
  --collect   poll batches and write data/labels.jsonl
"""
import argparse, json, os, random, re, sys, time

import anthropic

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL = 'claude-haiku-5-5'
YEARS = (2024, 2025, 2026, 2027)
LABELS_PATH = os.path.join(ROOT, 'data', 'labels.jsonl')
BATCH_IDS_PATH = os.path.join(ROOT, 'data', 'batches.json')
CHUNK = 20000  # requests per batch job (API caps at 100k / 256MB)


def env(key):
    with open(os.path.join(ROOT, '.env')) as f:
        for line in f:
            if line.strip().startswith(key + '='):
                return line.strip().split('=', 1)[1]
    raise SystemExit(f'missing {key} in .env')


TOPICS = json.load(open(os.path.join(ROOT, 'topics.json')))['topics']
VALID = {t['id'] for t in TOPICS}
TAXONOMY = '\n'.join(f"{t['id']}: {t['label']} - {t['hint']}" for t in TOPICS)

SYSTEM = f"""You label machine-learning paper abstracts with the research concepts the paper is ABOUT.

Concepts:
{TAXONOMY}

How to decide:
- A concept matches only if it names something the paper ITSELF studies, builds, or measures - its subject or contribution.
- It does NOT match if the paper merely mentions it, cites it, uses it as a baseline, compares against it, or says it does not do it.
- If the title or keywords name a concept, it almost certainly matches.
- Prefer FEWER labels. Most papers have 1-3. Never output more than 3.
- Pick the most specific concept, not the general family too: a paper on sparse autoencoders is "saes", not also "interpretability".

Examples:
Title: When Do Sparse Autoencoders Recover Features?
-> ["saes"]
Title: Revisiting Temporal Link Prediction through Structural Proximity
-> ["gnn"]
Title: A Counterfactual Audit of Noisy-Label Corrections
-> ["causal","data-selection"]

Output ONLY a JSON array of concept ids. Use [] if nothing applies. Never invent ids."""


def user_msg(p):
    kw = ', '.join(p['keywords'] or [])
    return f"Title: {p['title']}\nKeywords: {kw}\nAbstract: {p['abstract']}"


def parse(text):
    """Pull the JSON array out of a response; drop anything not a known id."""
    m = re.search(r'\[.*?\]', text, re.S)
    if not m:
        return None
    try:
        ids = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    return [i for i in ids if i in VALID] if isinstance(ids, list) else None


def papers(years=YEARS):
    for y in years:
        with open(os.path.join(ROOT, 'data', 'raw', f'{y}.jsonl')) as f:
            for line in f:
                yield json.loads(line)


def params(p):
    return {
        'model': MODEL,
        'max_tokens': 2000,
        # adaptive thinking measured at 100% recall / 12% unsupported vs 78%/46%
        # without it (scripts/eval_labeller.py); it also beats Sonnet 5.5 here.
        'thinking': {'type': 'adaptive'},
        'system': [{'type': 'text', 'text': SYSTEM, 'cache_control': {'type': 'ephemeral'}}],
        'messages': [{'role': 'user', 'content': user_msg(p)}],
    }


def cmd_test(n):
    client = anthropic.Anthropic(api_key=env('ANTHROPIC_API_KEY'))
    pool = [p for p in papers([2027])]
    random.seed(0)
    sample = random.sample(pool, n)
    tin = tout = 0
    for p in sample:
        r = client.messages.create(**params(p))
        ids = parse(''.join(b.text for b in r.content if b.type == 'text'))
        tin += r.usage.input_tokens + getattr(r.usage, 'cache_creation_input_tokens', 0) or 0
        tout += r.usage.output_tokens
        print(f"{(p['title'] or '')[:62]:62s} -> {ids}")
    total = 81680
    cost = (tin / n * total / 1e6 * 0.10 + tout / n * total / 1e6 * 0.50) / 2
    print(f'\navg tokens in={tin/n:.0f} out={tout/n:.0f}')
    print(f'projected batch cost for {total} papers: ${cost:.2f}')


def cmd_submit():
    client = anthropic.Anthropic(api_key=env('ANTHROPIC_API_KEY'))
    done = set()
    if os.path.exists(LABELS_PATH):
        done = {json.loads(l)['id'] for l in open(LABELS_PATH)}
    todo = [p for p in papers() if p['id'] not in done]
    print(f'{len(todo)} papers to label')
    ids = []
    for i in range(0, len(todo), CHUNK):
        chunk = todo[i:i + CHUNK]
        b = client.messages.batches.create(requests=[
            {'custom_id': p['id'], 'params': params(p)} for p in chunk])
        ids.append(b.id)
        print(f'  batch {b.id}: {len(chunk)} requests', flush=True)
    json.dump(ids, open(BATCH_IDS_PATH, 'w'))


def cmd_collect():
    client = anthropic.Anthropic(api_key=env('ANTHROPIC_API_KEY'))
    ids = json.load(open(BATCH_IDS_PATH))
    while True:
        states = [client.messages.batches.retrieve(i) for i in ids]
        pend = [s for s in states if s.processing_status != 'ended']
        if not pend:
            break
        counts = states[0].request_counts
        print(f'{len(pend)}/{len(ids)} batches running; first: {counts}', flush=True)
        time.sleep(120)
    ok = bad = 0
    with open(LABELS_PATH, 'a') as out:
        for i in ids:
            for res in client.messages.batches.results(i):
                if res.result.type != 'succeeded':
                    bad += 1
                    continue
                parsed = parse(''.join(
                    b.text for b in res.result.message.content if b.type == 'text'))
                if parsed is None:
                    bad += 1
                    continue
                out.write(json.dumps({'id': res.custom_id, 'topics': parsed}) + '\n')
                ok += 1
    print(f'labelled {ok}, failed {bad}')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--test', type=int)
    ap.add_argument('--submit', action='store_true')
    ap.add_argument('--collect', action='store_true')
    a = ap.parse_args()
    if a.test: cmd_test(a.test)
    elif a.submit: cmd_submit()
    elif a.collect: cmd_collect()
    else: ap.error('pick a mode')
