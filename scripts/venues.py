"""Venue configuration and per-venue paths, shared by every pipeline step."""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CFG = json.load(open(os.path.join(ROOT, 'venues.json')))['venues']


def config(venue):
    if venue not in _CFG:
        raise SystemExit(f'unknown venue {venue!r}; known: {", ".join(_CFG)}')
    return _CFG[venue]


def raw_dir(venue):
    return os.path.join(ROOT, 'data', 'raw', venue)


def raw_path(venue, year):
    return os.path.join(raw_dir(venue), f'{year}.jsonl')


def labels_path(venue):
    return os.path.join(ROOT, 'data', f'labels.{venue}.jsonl')


def batches_path(venue):
    return os.path.join(ROOT, 'data', f'batches.{venue}.json')


def snapshot_path(venue):
    return os.path.join(ROOT, 'data', f'topics.at-labelling.{venue}.json')


def report_path(venue):
    return os.path.join(ROOT, 'src', 'data', f'report.{venue}.json')


def add_venue_arg(parser):
    parser.add_argument('--venue', default='iclr', choices=sorted(_CFG),
                        help='conference to work on (default: iclr)')
    return parser
