"""Measure labeller quality without hand-labelling anything.

RECALL: papers whose *title* contains an unmistakable phrase for a concept must
get that concept. A title is the author's own claim about the paper's subject,
so these are near-certain ground truth.

PRECISION PROXY: a predicted concept whose aliases appear nowhere in the paper's
title, keywords or abstract is suspicious. Some are legitimate (synonyms we
didn't list) but the *rate* is comparable between prompt versions.
"""
import json, os, random, re, statistics, sys

import anthropic

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import label as L

# concept -> phrase that, in a TITLE, makes the concept certain
GOLD = {
    'saes': r'sparse autoencoder',
    'diffusion-lm': r'diffusion language model|masked diffusion language',
    'world-models': r'\bworld model',
    'jepa': r'\bjepa\b',
    'agent-memory': r'\bagent(ic)? memory\b|memory for .{0,20}agents',
    'flow-matching': r'flow matching',
    'moe': r'mixture[- ]of[- ]experts',
    'speculative-decoding': r'speculative decoding',
    'federated': r'federated learning',
    'gnn': r'graph neural network',
    'vla': r'vision[- ]language[- ]action',
    'unlearning': r'machine unlearning|\bunlearning\b',
    'kv-cache': r'\bkv[- ]cache',
    'optimal-transport': r'optimal transport',
    'snn': r'spiking neural network',
}
ALIASES = {t['id']: [t['label'].lower()] + [a.lower() for a in t['aliases']] for t in L.TOPICS}


def build_set(per=4, venue='iclr', year=None):
    year = year or L.venues.config(venue)['years'][-1]
    pool = list(L.papers(venue, [year]))
    random.seed(1)
    cases = []
    for cid, pat in GOLD.items():
        hits = [p for p in pool if re.search(pat, (p['title'] or '').lower())]
        for p in random.sample(hits, min(per, len(hits))):
            cases.append((p, cid))
    return cases


def run(cases, system, model=L.MODEL, thinking=None):
    client = anthropic.Anthropic(api_key=L.env('ANTHROPIC_API_KEY'))
    recall_hit = 0
    nlabels, unsupported = [], []
    for p, cid in cases:
        kw = {'model': model, 'max_tokens': 1500 if thinking else 200,
              'system': [{'type': 'text', 'text': system,
                          'cache_control': {'type': 'ephemeral'}}],
              'messages': [{'role': 'user', 'content': L.user_msg(p)}]}
        kw['thinking'] = thinking or {'type': 'disabled'}
        r = client.messages.create(**kw)
        text = ''.join(b.text for b in r.content if b.type == 'text')
        ids = L.parse(text) or []
        if cid in ids:
            recall_hit += 1
        nlabels.append(len(ids))
        blob = ((p['title'] or '') + ' ' + ' '.join(p['keywords'] or []) + ' '
                + (p['abstract'] or '')).lower()
        for i in ids:
            if not any(a in blob for a in ALIASES[i]):
                unsupported.append(i)
    n = len(cases)
    print(f'  recall on certain cases: {recall_hit}/{n} = {100*recall_hit/n:.0f}%')
    print(f'  mean labels/paper: {statistics.mean(nlabels):.2f}  (max {max(nlabels)})')
    print(f'  unsupported labels: {len(unsupported)}/{sum(nlabels)} = '
          f'{100*len(unsupported)/max(1,sum(nlabels)):.0f}%')
    return recall_hit / n, statistics.mean(nlabels), len(unsupported) / max(1, sum(nlabels))


if __name__ == '__main__':
    cases = build_set()
    print(f'{len(cases)} certain-ground-truth cases\n')
    print('--- v1 (current prompt)')
    run(cases, L.SYSTEM)
