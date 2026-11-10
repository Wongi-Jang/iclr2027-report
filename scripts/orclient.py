"""Authenticated OpenReview client with on-disk token cache.

Login is rate-limited to 3 requests per window, so never log in per run.
"""
import json, os, time

import openreview

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN_PATH = os.path.join(ROOT, 'data', '.or_token.json')
BASE = 'https://api2.openreview.net'


def env(key):
    with open(os.path.join(ROOT, '.env')) as f:
        for line in f:
            line = line.strip()
            if line.startswith(key + '='):
                return line.split('=', 1)[1]
    raise SystemExit(f'missing {key} in .env')


def client():
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH) as f:
            cached = json.load(f)
        if cached['expires_at'] > time.time() + 300:
            return openreview.api.OpenReviewClient(baseurl=BASE, token=cached['token'])

    ttl = 60 * 60 * 24  # seconds
    c = openreview.api.OpenReviewClient(
        baseurl=BASE, username=env('OPENREVIEW_USERNAME'),
        password=env('OPENREVIEW_PASSWORD'), tokenExpiresIn=ttl,
    )
    os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
    with open(TOKEN_PATH, 'w') as f:
        json.dump({'token': c.token, 'expires_at': time.time() + ttl}, f)
    os.chmod(TOKEN_PATH, 0o600)
    return c
