"""Look up citation counts from OpenAlex for the papers the site publishes.

Only for venues whose papers are actually published. Papers still under review
are unpublished, so their true count is zero and any non-zero number we showed
would come from matching the wrong paper - which has already happened in
testing ("Context Language Models" -> "Document Context Language Models", 66
citations). Hence the strict title check below: no match, no number.
"""
import argparse, json, os, re, sys, time, urllib.parse, urllib.request

import venues

API = 'https://api.openalex.org/works'
PAUSE = 1.6  # be polite; 1.1s drew 429s from OpenAlex on a 320-paper run


def norm(t):
    return re.sub(r'[^a-z0-9]+', ' ', (t or '').lower()).strip()


def lookup(title):
    """('ok', count) | ('nomatch', None) | ('error', None).

    A transient failure must NEVER be cached as 'no citations' - the two are
    indistinguishable once written, and an earlier run silently buried 18
    rate-limited lookups that way. Checks several results, not just the first,
    because OpenAlex often ranks a review or a survey above the paper itself.
    """
    url = f'{API}?filter=title.search:{urllib.parse.quote(title)}&per_page=5'
    req = urllib.request.Request(url, headers={'User-Agent': 'conference-report/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            hits = json.load(r).get('results') or []
    except urllib.error.HTTPError as e:
        if e.code == 429:
            time.sleep(20)
        return ('error', None)
    except Exception:
        return ('error', None)
    for h in hits:
        if norm(h.get('title')) == norm(title):
            return ('ok', h.get('cited_by_count'))
    return ('nomatch', None)


def bulk(source_id, years, titles):
    """Page a venue's whole OpenAlex source once instead of searching per title.

    Uses page numbers, NOT a cursor: anonymous cursor pagination returns 401 on
    the second page, which silently limited an earlier run to ~160 papers per
    year. Page numbers work without credentials up to 10k results per filter,
    and both NeurIPS years are well under that.
    """
    found = {}
    for year in years:
        page_no, scanned, misses = 1, 0, 0
        while True:
            url = (f'{API}?filter=primary_location.source.id:{source_id},'
                   f'publication_year:{year}&per-page=200&page={page_no}')
            req = urllib.request.Request(url, headers={'User-Agent': 'conference-report/1.0'})
            try:
                with urllib.request.urlopen(req, timeout=40) as r:
                    page = json.load(r)
            except urllib.error.HTTPError as e:
                if e.code == 429 and misses < 6:
                    misses += 1
                    time.sleep(15 * misses)
                    continue
                print(f'  {year}: stopped at page {page_no}: HTTP {e.code}', file=sys.stderr)
                break
            except Exception as e:
                print(f'  {year}: stopped at page {page_no}: {type(e).__name__}', file=sys.stderr)
                break
            results = page.get('results') or []
            if not results:
                break
            for w in results:
                key = norm(w.get('title'))
                if key in titles:
                    found[titles[key]] = w.get('cited_by_count')
            scanned += len(results)
            print(f'  {year} page {page_no}: scanned {scanned}, matched {len(found)}', flush=True)
            if scanned >= page['meta']['count'] or page_no >= 50:
                break
            page_no += 1
            time.sleep(1.5)
    return found


def main():
    ap = venues.add_venue_arg(argparse.ArgumentParser())
    ap.add_argument('--all', action='store_true',
                    help='every paper, not only the ones the site displays')
    a = ap.parse_args()
    cfg = venues.config(a.venue)
    if not cfg.get('citations'):
        raise SystemExit(f'{a.venue}: citations disabled in venues.json '
                         '(papers are unpublished, so any number would be a mismatch)')

    if a.all:
        wanted = {}
        for year in cfg['years']:
            with open(venues.raw_path(a.venue, year)) as f:
                for line in f:
                    p = json.loads(line)
                    wanted[p['id']] = p['title']
    else:
        report = json.load(open(venues.report_path(a.venue)))
        wanted = {p['id']: p['title'] for p in report['top_papers']}
        for t in report.get('topic_top', {}).values():
            for p in t['papers']:
                wanted[p['id']] = p['title']

    path = os.path.join(venues.ROOT, 'data', f'citations.{a.venue}.json')
    cache = json.load(open(path)) if os.path.exists(path) else {}

    source = cfg.get('openalex_source')
    if a.all and source:
        by_title = {norm(t): pid for pid, t in wanted.items() if pid not in cache}
        if by_title:
            print(f'bulk-scanning OpenAlex source {source}')
            got = bulk(source, cfg['years'], by_title)
            cache.update(got)
            json.dump(cache, open(path, 'w'))
            print(f'  bulk matched {len(got)}')

    todo = [k for k in wanted if k not in cache]
    print(f'{len(wanted)} published papers, {len(todo)} left for per-title search')

    errors = 0
    for i, pid in enumerate(todo, 1):
        status, count = lookup(wanted[pid])
        for _ in range(2):
            if status != 'error':
                break
            time.sleep(5)
            status, count = lookup(wanted[pid])
        if status == 'error':
            errors += 1          # leave it out of the cache so a re-run retries it
        else:
            cache[pid] = count
        if i % 25 == 0 or i == len(todo):
            json.dump(cache, open(path, 'w'))
            print(f'  {i}/{len(todo)}', flush=True)
        time.sleep(PAUSE)

    json.dump(cache, open(path, 'w'))
    found = sum(1 for v in cache.values() if v is not None)
    print(f'matched {found}/{len(cache)}; {errors} still failing (re-run to retry those); '
          'unmatched papers show no citation count')


if __name__ == '__main__':
    main()
