"""Exact ANL release and historical Analytics placeholder, with no sibling reads."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'docs/analytics-poc'
MANIFEST = '43d9e5f7b328002c735cdf85da3f6ed5e0c9ff41a2f74aaccdcc0b8e8a396998'


def original_analytics_input(path):
    if (ROOT / 'docs/analytics-environment-poc/RELEASE_0_12_0.json').exists() and path in ['VERSION', 'openapi/analytics-service.yaml']:
        return ROOT / 'docs/analytics-environment-poc/previous-0.11.0' / path
    return ROOT / path


def validate_release():
    release = BASE / 'RELEASE_0_11_0.json'
    if not release.exists(): return
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    assert sha(BASE / 'CANDIDATE_MANIFEST.json') == MANIFEST
    m = json.loads((BASE / 'CANDIDATE_MANIFEST.json').read_text())
    r = json.loads(release.read_text())
    assert r['release'] == '0.11.0' and r['sourceManifestSha256'] == MANIFEST
    assert sha(BASE / 'CANDIDATE_REVIEW.md') == r['reviewSha256']
    assert original_analytics_input('VERSION').read_text().strip() == '0.11.0'
    files = {}
    for path, digest in m['artifacts'].items():
        path = path.removeprefix('candidate/')
        if path.startswith('examples/'): path = 'examples/analytics/v1/' + path.split('/')[-1]
        files[path] = digest
    archive = {'docs/analytics-poc/previous-0.10.0/VERSION': 'dc24feb5bd35084d8ae32a4eafbec12352707d4662401fcbcc9bbd696cde77a9',
               'docs/analytics-poc/previous-0.10.0/openapi/analytics-service.yaml': '2efa666c3e48c2fce9338645adb2ad6ef42be1154de49712f14d4360c3bc2514'}
    assert r['files'] == files and r['archive'] == archive and r['inputSchemasSha256'] == m['inputSchemasSha256']
    for path, digest in {**files, **archive, **r['inputSchemasSha256']}.items(): assert sha(original_analytics_input(path)) == digest, path


def prior_analytics(path):
    if (BASE / 'RELEASE_0_11_0.json').exists() and path == ROOT / 'openapi/analytics-service.yaml':
        validate_release()
        return BASE / 'previous-0.10.0/openapi/analytics-service.yaml'
    return path


def analytics_inventory():
    if not (BASE / 'RELEASE_0_11_0.json').exists(): return set()
    validate_release()
    return set(json.loads((BASE / 'RELEASE_0_11_0.json').read_text())['files'])
