"""Fetch ICLR submissions + reviews from OpenReview into data/raw/<year>.jsonl.

Keeps only the fields the report needs. Reviews are flattened to ratings so the
raw cache stays a few hundred MB rather than a few GB.
"""
import json, os, sys, time

from orclient import ROOT, client

YEARS = (2024, 2025, 2026, 2027)


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


def main():
    c = client()
    for year in YEARS:
        path = os.path.join(ROOT, 'data', 'raw', f'{year}.jsonl')
        if os.path.exists(path):
            print(f'{year}: already fetched ({sum(1 for _ in open(path))} papers), skipping')
            continue
        t0 = time.time()
        notes = c.get_all_notes(
            invitation=f'ICLR.cc/{year}/Conference/-/Submission',
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
