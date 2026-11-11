"""Fetch ICLR submissions + reviews from OpenReview into data/raw/<year>.jsonl.

Keeps only the fields the report needs. Reviews are flattened to ratings so the
raw cache stays a few hundred MB rather than a few GB.
"""
import argparse, collections, json, os, sys, time

from orclient import client
import venues


def num(v):
    """Ratings arrive as '8: accept' or 8 or '8'. Return the leading int."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    head = str(v).split(':')[0].strip()
    try:
        return float(head)
    except ValueError:
        return None


def reviews_of(note):
    out = []
    for r in (note.details or {}).get('directReplies', []):
        if not any('Official_Review' in i for i in r.get('invitations', [])):
            continue
        c = r.get('content', {})
        out.append({
            'rating': num(c.get('rating', {}).get('value')),
            'confidence': num(c.get('confidence', {}).get('value')),
            'soundness': num(c.get('soundness', {}).get('value')),
            'presentation': num(c.get('presentation', {}).get('value')),
            # 2027 renamed 'contribution' -> 'informativeness'
            'informativeness': num(c.get('informativeness', c.get('contribution', {})).get('value')),
        })
    return out


def slim(note, year):
    c = note.content
    val = lambda k: c.get(k, {}).get('value')
    return {
        'id': note.id,
        'year': year,
        'title': val('title'),
        'abstract': val('abstract'),
        'keywords': val('keywords') or [],
        'primary_area': val('primary_area'),
        'venueid': val('venueid'),
        'authors': val('authors'),  # None for 2027 (still anonymous)
        'reviews': reviews_of(note),
    }


def probe(c, venue):
    """Report what a venue actually exposes before anyone spends money on it."""
    cfg = venues.config(venue)
    for year in cfg['years']:
        notes = c.get_notes(invitation=cfg['group'].format(year=year) + '/-/Submission',
                            limit=1000, details='directReplies')
        if not notes:
            print(f'{year}: nothing visible'); continue
        mix = collections.Counter(
            (n.content.get('venueid', {}).get('value') or '').split('/')[-1] for n in notes)
        rated = sum(1 for n in notes if reviews_of(n))
        scales = sorted({r['rating'] for n in notes for r in reviews_of(n)
                         if r['rating'] is not None})
        print(f'{year}: first {len(notes)} -> {dict(mix)}')
        print(f'      {rated} have reviews; rating values seen: {scales}')


def main():
    ap = venues.add_venue_arg(argparse.ArgumentParser())
    ap.add_argument('--probe', action='store_true',
                    help='report what the venue exposes, fetch nothing')
    a = ap.parse_args()
    c = client()
    if a.probe:
        return probe(c, a.venue)
    cfg = venues.config(a.venue)
    os.makedirs(venues.raw_dir(a.venue), exist_ok=True)
    print(f"{a.venue}: {cfg['corpus']} - {cfg['corpus_note']}")
    for year in cfg['years']:
        path = venues.raw_path(a.venue, year)
        if os.path.exists(path):
            print(f'{year}: already fetched ({sum(1 for _ in open(path))} papers), skipping')
            continue
        t0 = time.time()
        notes = c.get_all_notes(
            invitation=cfg['group'].format(year=year) + '/-/Submission',
            details='directReplies',
        )
        tmp = path + '.part'
        with open(tmp, 'w') as f:
            for n in notes:
                f.write(json.dumps(slim(n, year)) + '\n')
        os.rename(tmp, path)
        print(f'{year}: {len(notes)} papers in {time.time()-t0:.0f}s', flush=True)


if __name__ == '__main__':
    main()
