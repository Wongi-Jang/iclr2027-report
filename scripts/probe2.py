import os, sys, json, openreview
def env(k):
    for l in open(os.path.join(os.path.dirname(__file__),'..','.env')):
        if l.strip().startswith(k+'='): return l.strip().split('=',1)[1]
c = openreview.api.OpenReviewClient(baseurl='https://api2.openreview.net',
    username=env('OPENREVIEW_USERNAME'), password=env('OPENREVIEW_PASSWORD'))
for year in (2024,2025,2026,2027):
    inv=f'ICLR.cc/{year}/Conference/-/Submission'
    r=c.get_notes(invitation=inv, limit=1)
    # count via raw http
    resp=c.session.get('https://api2.openreview.net/notes',params={'invitation':inv,'limit':1},
        headers=c.headers).json()
    print(year,'total submissions =',resp.get('count'))
# 2027 rating scale + sample
n=c.get_notes(invitation='ICLR.cc/2027/Conference/-/Submission',limit=5,details='directReplies')
for note in n[:2]:
    print('\nTITLE:',note.content['title']['value'][:70])
    print(' venueid:',note.content['venueid']['value'])
    print(' primary_area:',note.content.get('primary_area',{}).get('value'))
    print(' keywords:',note.content.get('keywords',{}).get('value'))
    for r in (note.details or {}).get('directReplies',[]):
        if any('Official_Review' in i for i in r.get('invitations',[])):
            print('  rating=',r['content'].get('rating',{}).get('value'),
                  'conf=',r['content'].get('confidence',{}).get('value'),
                  'sound=',r['content'].get('soundness',{}).get('value'),
                  'info=',r['content'].get('informativeness',{}).get('value'))
