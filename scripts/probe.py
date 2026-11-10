"""Probe: can we log in, how many papers per year, are reviews public?"""
import os, sys, json
import openreview

def env(k):
    for line in open(os.path.join(os.path.dirname(__file__), '..', '.env')):
        line = line.strip()
        if line.startswith(k + '='):
            return line.split('=', 1)[1]
    sys.exit(f'missing {k} in .env')

c = openreview.api.OpenReviewClient(
    baseurl='https://api2.openreview.net',
    username=env('OPENREVIEW_USERNAME'),
    password=env('OPENREVIEW_PASSWORD'),
)
print('logged in, token:', bool(c.token))

for year in (2024, 2025, 2026, 2027):
    inv = f'ICLR.cc/{year}/Conference/-/Submission'
    try:
        notes = c.get_notes(invitation=inv, limit=3, details='directReplies')
    except Exception as e:
        print(year, 'ERROR', type(e).__name__, str(e)[:200]); continue
    cnt = c.get_notes(invitation=inv, limit=1)
    total = getattr(cnt, 'count', None)
    print(f'--- {year}: sample={len(notes)}')
    if notes:
        n = notes[0]
        print('  content keys:', sorted(n.content.keys()))
        print('  venueid:', n.content.get('venueid', {}).get('value'))
        reps = n.details.get('directReplies', []) if n.details else []
        print('  directReplies:', len(reps))
        kinds = {}
        for r in reps:
            for i in r.get('invitations', []):
                kinds[i.split('/')[-1]] = kinds.get(i.split('/')[-1], 0) + 1
        print('  reply kinds:', kinds)
        for r in reps:
            if any('Review' in i for i in r.get('invitations', [])):
                print('  REVIEW fields:', sorted(r['content'].keys()))
                break
