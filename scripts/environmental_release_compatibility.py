"""Exact accepted local 0.12.0 release plus immutable candidate and 0.11.0 archive."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = '1759e5d95fb3602b623b995e4650f035b67dbb550760116587f46c031ca7d111'


def original_environmental_input(path):
    if path == 'VERSION' and (ROOT / 'docs/m4/RELEASE_0_13_0.json').exists():
        from m4_release_compatibility import validate_release as validate_m4
        validate_m4()
        return ROOT / 'docs/m4/previous-0.12.0/VERSION'
    return ROOT / path


def validate_release():
    base = ROOT / 'docs/analytics-environment-poc'
    if not (base / 'RELEASE_0_12_0.json').exists(): return
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    assert sha(base / 'CANDIDATE_MANIFEST.json') == MANIFEST
    m = json.loads((base / 'CANDIDATE_MANIFEST.json').read_text())
    r = json.loads((base / 'RELEASE_0_12_0.json').read_text())
    assert r['release'] == '0.12.0' and r['sourceManifestSha256'] == MANIFEST
    assert r['reviewSha256'] == sha(base / 'CANDIDATE_REVIEW.md') == '841278e1fe7576e137cb48ec68b3d9509e087baecd75729d6d3e6379dc6db924'
    assert original_environmental_input('VERSION').read_text().strip() == '0.12.0'
    files = {}
    for path, digest in m['artifacts'].items():
        assert sha(base / path) == digest, path
        path = path.removeprefix('candidate/')
        if path.startswith('examples/'): path = 'examples/analytics/environment/v1/' + path.split('/')[-1]
        files[path] = digest
    archive = {}
    for path, digest in m['inputsSha256'].items():
        actual = 'docs/analytics-environment-poc/previous-0.11.0/' + path if path in ['VERSION', 'openapi/analytics-service.yaml'] else path
        assert sha(ROOT / actual) == digest, actual
        if actual != path: archive[actual] = digest
    assert r['files'] == files and r['archive'] == archive and r['inputsSha256'] == m['inputsSha256']
    for path, digest in files.items(): assert sha(ROOT / path) == digest, path


def environmental_inventory():
    base = ROOT / 'docs/analytics-environment-poc'
    if not (base / 'RELEASE_0_12_0.json').exists(): return set()
    validate_release()
    return set(json.loads((base / 'RELEASE_0_12_0.json').read_text())['files'])
