"""Turn raw papers + labels into src/data/report.json (aggregates only).

Withdrawn and desk-rejected papers are excluded from every statistic, per the
report's stated method. Nothing with an abstract ships to the browser.
"""
import json, os, statistics, datetime, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YEARS = (2024, 2025, 2026, 2027)
EXCLUDE = ('Withdrawn_Submission', 'Desk_Rejected_Submission')
# Display names come from the taxonomy the labels were MADE under, not the current
# topics.json - otherwise editing a concept silently renames data it never saw.
# After a re-label, copy topics.json over the snapshot.
_SNAP = os.path.join(ROOT, 'data', 'topics.at-labelling.json')
_LIVE = os.path.join(ROOT, 'topics.json')
TOPICS = json.load(open(_SNAP if os.path.exists(_SNAP) else _LIVE))['topics']
LABEL = {t['id']: t['label'] for t in TOPICS}
# ICLR changed its rating scale every year; never compare across years.
SCALES = {2024: '1-10', 2025: '1-10', 2026: '0-10', 2027: '1-4'}


def load():
    labels = {}
    lp = os.path.join(ROOT, 'data', 'labels.jsonl')
    with open(lp) as f:
        for line in f:
            d = json.loads(line)
            labels[d['id']] = d['topics']
    papers = []
    for y in YEARS:
        with open(os.path.join(ROOT, 'data', 'raw', f'{y}.jsonl')) as f:
            for line in f:
                p = json.loads(line)
                p['stage'] = (p['venueid'] or '').split('/')[-1]
                p['topics'] = labels.get(p['id'], [])
                papers.append(p)
    return papers, labels


def main():
    papers, labels = load()
    stale = {t for ids in labels.values() for t in ids} - {t['id'] for t in TOPICS}
    if stale:
        raise SystemExit(f'labels reference concepts not in the snapshot: {sorted(stale)} - '
                         'the snapshot and data/labels.jsonl have drifted apart')
    live = [p for p in papers if p['stage'] not in EXCLUDE]

    counts = {y: sum(1 for p in papers if p['year'] == y) for y in YEARS}
    live_counts = {y: sum(1 for p in live if p['year'] == y) for y in YEARS}
    labelled = {y: sum(1 for p in live if p['year'] == y and p['id'] in labels) for y in YEARS}

    # topic counts per year, over labelled live papers only
    per = {y: collections.Counter() for y in YEARS}
    for p in live:
        for t in set(p['topics']):
            per[p['year']][t] += 1
    topics = []
    for t in TOPICS:
        row = {'id': t['id'], 'label': t['label'], 'counts': {}, 'share': {}}
        for y in YEARS:
            c = per[y][t['id']]
            row['counts'][y] = c
            row['share'][y] = round(100 * c / labelled[y], 3) if labelled[y] else 0
        topics.append(row)
    topics.sort(key=lambda r: -r['counts'][2027])

    movers = sorted(
        ({'id': r['id'], 'label': r['label'],
          'from': r['share'][2026], 'to': r['share'][2027],
          'delta': round(r['share'][2027] - r['share'][2026], 3),
          'n2027': r['counts'][2027]}
         for r in topics if r['counts'][2027] + r['counts'][2026] >= 50),
        key=lambda r: -r['delta'])

    # 2027 leaderboards (1-4 scale, >=3 reviews)
    scored = []
    for p in live:
        if p['year'] != 2027:
            continue
        rs = [r['rating'] for r in p['reviews'] if r['rating'] is not None]
        if len(rs) < 3:
            continue
        scored.append({
            'id': p['id'], 'title': p['title'],
            'mean': round(statistics.mean(rs), 2),
            'sd': round(statistics.pstdev(rs), 2),
            'n': len(rs), 'ratings': rs,
            'topics': [LABEL[t] for t in p['topics']],
        })
    top = sorted(scored, key=lambda r: (-r['mean'], -r['n']))[:30]
    contested = sorted(scored, key=lambda r: (-r['sd'], -r['n']))[:20]

    dist = collections.Counter()
    for p in live:
        if p['year'] == 2027:
            for r in p['reviews']:
                if r['rating'] is not None:
                    dist[int(r['rating'])] += 1

    out = {
        'meta': {
            'as_of': datetime.date.today().isoformat(),
            'years': list(YEARS),
            'submissions': counts,
            'analysed': live_counts,
            'labelled': labelled,
            'excluded_note': 'Withdrawn and desk-rejected papers are excluded from all statistics.',
            'rating_scales': SCALES,
            'n_concepts': len(TOPICS),
        },
        'topics': topics,
        'risers': movers[:12],
        'fallers': movers[-12:][::-1],
        'top_papers': top,
        'contested_papers': contested,
        'rating_distribution': dict(sorted(dist.items())),
    }
    dest = os.path.join(ROOT, 'src', 'data')
    os.makedirs(dest, exist_ok=True)
    path = os.path.join(dest, 'report.json')
    with open(path, 'w') as f:
        json.dump(out, f, separators=(',', ':'))
    print(f'wrote {path} ({os.path.getsize(path)/1024:.0f} KB)')
    print('submissions:', counts)
    print('labelled:', labelled)
    print('top 8 concepts 2027:', [(r['label'], r['counts'][2027]) for r in topics[:8]])
    print('top risers:', [(r['label'], r['delta']) for r in movers[:5]])


if __name__ == '__main__':
    main()
