"""Turn raw papers + labels into src/data/report.json (aggregates only).

Withdrawn and desk-rejected papers are excluded from every statistic, per the
report's stated method. Nothing with an abstract ships to the browser.
"""
import argparse, json, os, statistics, datetime, collections

import venues

ROOT = venues.ROOT
def taxonomy(venue):
    """Display names come from the taxonomy the labels were MADE under, not the
    current topics.json - otherwise editing a concept silently renames data it
    never saw. After a re-label, copy topics.json over the snapshot."""
    snap = venues.snapshot_path(venue)
    live = os.path.join(ROOT, 'topics.json')
    return json.load(open(snap if os.path.exists(snap) else live))['topics']


def load(venue, years):
    labels = {}
    with open(venues.labels_path(venue)) as f:
        for line in f:
            d = json.loads(line)
            labels[d['id']] = d['topics']
    papers = []
    for y in years:
        with open(venues.raw_path(venue, y)) as f:
            for line in f:
                p = json.loads(line)
                p['stage'] = (p['venueid'] or '').split('/')[-1]
                p['topics'] = labels.get(p['id'], [])
                papers.append(p)
    return papers, labels


def main():
    a = venues.add_venue_arg(argparse.ArgumentParser()).parse_args()
    venue = a.venue
    cfg = venues.config(venue)
    YEARS = tuple(cfg['years'])
    EXCLUDE = tuple(cfg['exclude_stages'])
    TOPICS = taxonomy(venue)
    LABEL = {t['id']: t['label'] for t in TOPICS}
    LATEST = YEARS[-1]
    papers, labels = load(venue, YEARS)
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
    topics.sort(key=lambda r: -r['counts'][LATEST])

    movers = sorted(
        ({'id': r['id'], 'label': r['label'],
          'from': r['share'][YEARS[-2]] if len(YEARS) > 1 else 0,
          'to': r['share'][LATEST],
          'delta': round(r['share'][LATEST] - r['share'][YEARS[-2]], 3) if len(YEARS) > 1 else 0,
          'n2027': r['counts'][LATEST]}
         for r in topics if len(YEARS) > 1
         and r['counts'][LATEST] + r['counts'][YEARS[-2]] >= 50),
        key=lambda r: -r['delta'])

    # 2027 leaderboards (1-4 scale, >=3 reviews)
    scored = []
    for p in live:
        if p['year'] != LATEST:
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
        if p['year'] == LATEST:
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
            'rating_scales': cfg['rating_scales'],
            'venue': cfg.get('name', venue.upper()),
            'latest': LATEST,
            'corpus': cfg['corpus'],
            'corpus_note': cfg['corpus_note'],
            'n_concepts': len(TOPICS),
        },
        'topics': topics,
        'risers': movers[:12],
        'fallers': movers[-12:][::-1],
        'top_papers': top,
        'contested_papers': contested,
        'rating_distribution': dict(sorted(dist.items())),
    }
    path = venues.report_path(venue)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(out, f, separators=(',', ':'))
    print(f'wrote {path} ({os.path.getsize(path)/1024:.0f} KB)')
    print('submissions:', counts)
    print('labelled:', labelled)
    print(f'top 8 concepts {LATEST}:', [(r['label'], r['counts'][LATEST]) for r in topics[:8]])
    print('top risers:', [(r['label'], r['delta']) for r in movers[:5]])


if __name__ == '__main__':
    main()
