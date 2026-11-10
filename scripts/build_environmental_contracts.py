"""Deterministic isolated ANL-02 candidate; no release, pins or producer changes."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
from build_analytics_contracts import UUID, COUNT, obj, nullable

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'docs/analytics-environment-poc'
INPUT = 'events/telemetry/v1/TelemetryObservationRecorded.schema.json'
INPUT_SHA = '43f652fbbe98c6be3e545307a0fc6c50b2ebce0834c986dfe87d5c3bc5a4a2d2'
PATH = '/api/v1/analytics/estates/{estateId}/blocks/{blockId}/environment/observations'
KINDS = ['AIR_TEMPERATURE', 'SOIL_MOISTURE', 'INTERVAL_RAINFALL']
UTC = {'type': 'string', 'format': 'date-time', 'pattern': r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.[0-9]{1,3})?Z$'}


def baseline_input(path):
    """After accepted promotion, reproduce the candidate from its exact archived inputs."""
    if (BASE / 'RELEASE_0_12_0.json').exists() and path in ['openapi/analytics-service.yaml', 'VERSION']:
        return BASE / 'previous-0.11.0' / path
    return ROOT / path


def schemas():
    event = json.loads((ROOT / INPUT).read_text())
    variants = []
    for payload in event['properties']['payload']['oneOf']:
        properties = {k: copy.deepcopy(v) for k, v in payload['properties'].items()
                      if k not in ['estateId', 'blockId', 'schemaVersion', 'dataProvenance']}
        properties.update(sourceEventId=UUID, sourceEventAt=UTC)
        variants.append(obj(properties))
    history = obj({'estateId': UUID, 'blockId': UUID, 'from': UTC, 'to': UTC, 'generatedAt': UTC,
        'dataProvenance': {'type': 'string', 'const': 'SIMULATED'},
        'availability': {'type': 'string', 'enum': ['NONE', 'OBSERVED']},
        'projectionState': {'type': 'string', 'enum': ['OBSERVED_ONLY', 'INCOMPLETE']},
        'totalMatchingCount': {'type': 'string', 'pattern': r'^(?:0|[1-9][0-9]*)$'},
        'truncated': {'type': 'boolean'}, 'returnedKindCounts': obj({k: {'type': 'integer', 'minimum': 0, 'maximum': 1000} for k in KINDS}),
        'conflictCount': COUNT, 'lastProcessedAt': nullable(UTC), 'latestSourceEventAt': nullable(UTC),
        'observations': {'type': 'array', 'maxItems': 1000, 'items': {'oneOf': variants}}})
    problem = obj({'type': {'type': 'string', 'format': 'uri'}, 'title': {'type': 'string'},
                   'status': {'type': 'integer', 'enum': [400, 401, 403, 404, 429, 503]}, 'detail': {'type': 'string'}})
    return {'EnvironmentalHistory': history, 'EnvironmentalProblem': problem}


def artifacts():
    # Released production API is an immutable candidate input; the candidate adds exactly one GET.
    api = json.loads(baseline_input('openapi/analytics-service.yaml').read_text())
    api['info']['title'] = 'ANL-02 isolated Analytics candidate'
    api['info']['description'] += ' UNRELEASED environmental history extension; explicit UTC windows, observed evidence only.'
    api['components']['schemas'].update(schemas())
    responses = {'200': {'description': 'First 1000 exact per-device observations in [from,to); counts include all matches. No inferred coverage or rainfall sum.',
        'content': {'application/json': {'schema': {'$ref': '#/components/schemas/EnvironmentalHistory'}}}}}
    for code, label in [(400, 'Invalid, repeated or unknown query; non-UTC/submillisecond/empty/over-24h window'),
                        (401, 'Missing/invalid signed token'), (403, 'Role/estate/delegated access denied'),
                        (404, 'Unknown/inactive block'), (429, 'Rate limited'), (503, 'Reference/projection unavailable')]:
        responses[str(code)] = {'description': label, 'content': {'application/problem+json': {'schema': {'$ref': '#/components/schemas/EnvironmentalProblem'}}}}
    api['paths'][PATH] = {'get': {'operationId': 'getEnvironmentalObservationHistory',
        'description': 'Required explicit UTC millisecond [from,to), positive and at most 24 hours; filter observedAt. Ascending observedAt then canonical observationId. No default window, pagination, device aggregation or causal claim. Reject repeated/unknown query parameters. PLATFORM_ADMIN/PLANTATION_ADMIN globally; assigned ESTATE_ADMIN/ESTATE_MANAGER/AUDITOR only. Verify signed issuer/audience/lifetime and trusted estate scope before delegated active Estate/block checks, then read. No worker/supervisor/viewer widening. Dependency failure is 503, never NONE. Scope-wide conflicts remain visible outside query. NONE means no matching facts, never measured zero or known coverage. OBSERVED_ONLY never certifies stream completeness. Source times are inspected metadata, not watermarks. Untrusted admission diagnostics cannot be attributed to a block.',
        'parameters': [{'name': k, 'in': where, 'required': True, 'schema': schema} for k, where, schema in
                       [('estateId', 'path', UUID), ('blockId', 'path', UUID), ('from', 'query', UTC), ('to', 'query', UTC)]],
        'responses': responses}}
    uid = lambda n: f'00000000-0000-4000-8000-{n:012d}'
    empty = {'estateId': uid(1), 'blockId': uid(2), 'from': '2026-01-01T00:00:00Z', 'to': '2026-01-02T00:00:00Z',
        'generatedAt': '2026-01-02T00:00:02Z', 'dataProvenance': 'SIMULATED', 'availability': 'NONE',
        'projectionState': 'OBSERVED_ONLY', 'totalMatchingCount': '0', 'truncated': False,
        'returnedKindCounts': dict.fromkeys(KINDS, 0), 'conflictCount': 0, 'lastProcessedAt': None,
        'latestSourceEventAt': None, 'observations': []}
    def observed(rows):
        value = copy.deepcopy(empty)
        value.update(availability='OBSERVED', totalMatchingCount=str(len(rows)), observations=rows,
                     lastProcessedAt='2026-01-02T00:00:01Z', latestSourceEventAt='2026-01-01T12:00:01Z')
        value['returnedKindCounts'] = {k: sum(r['kind'] == k for r in rows) for k in KINDS}
        return value
    rows = []
    for n, (kind, unit, number) in enumerate(zip(KINDS, ['CELSIUS', 'PERCENT', 'MILLIMETRE'], ['-2.125000', '0', '0.000']), 10):
        row = {'observationId': uid(n), 'deviceId': uid(n+10), 'kind': kind, 'unit': unit, 'value': number,
               'observedAt': '2026-01-01T12:00:00Z', 'receivedAt': '2026-01-01T12:00:01Z',
               'sourceEventId': uid(n+20), 'sourceEventAt': '2026-01-01T12:00:01Z'}
        if kind == 'INTERVAL_RAINFALL': row.update(intervalStart='2025-12-31T23:00:00Z', intervalEnd='2026-01-01T12:00:00Z')
        rows.append(row)
    mixed = observed(rows)
    conflict = copy.deepcopy(empty)
    conflict.update(projectionState='INCOMPLETE', conflictCount=1, lastProcessedAt='2026-01-02T00:00:01Z', latestSourceEventAt='2026-01-01T12:00:01Z')
    cap = observed([dict(rows[0], observationId=uid(1000+n), sourceEventId=uid(3000+n)) for n in range(1000)])
    cap.update(totalMatchingCount='1001', truncated=True)
    examples = {'none': empty, 'mixed': mixed, 'truncated': cap, 'conflict-outside-window': conflict}
    for i, k in enumerate(KINDS): examples[k.lower()] = observed([rows[i]])
    for status, title in [(400, 'Bad Request'), (401, 'Unauthorized'), (403, 'Forbidden'), (404, 'Not Found'), (429, 'Too Many Requests'), (503, 'Unavailable')]:
        examples[f'problem-{status}'] = {'type': 'about:blank', 'title': title, 'status': status, 'detail': responses[str(status)]['description']}
    return {'openapi/analytics-service.yaml': api, **{f'examples/{k}.json': v for k, v in examples.items()}}


def build(check=False):
    encode = lambda v: (json.dumps(v, indent=2, ensure_ascii=True) + '\n').encode()
    outputs = {'candidate/' + k: encode(v) for k, v in artifacts().items()}
    inputs = {k: hashlib.sha256(baseline_input(k).read_bytes()).hexdigest() for k in [INPUT, 'openapi/analytics-service.yaml', 'VERSION']}
    assert inputs[INPUT] == INPUT_SHA
    assert baseline_input('VERSION').read_text().strip() == '0.11.0'
    manifest = {'status': 'UNRELEASED_CANDIDATE', 'scope': 'ANL-02', 'releaseVersion': None,
                'inputsSha256': inputs, 'artifacts': {k: hashlib.sha256(v).hexdigest() for k, v in sorted(outputs.items())}}
    outputs['CANDIDATE_MANIFEST.json'] = encode(manifest)
    for k, raw in outputs.items():
        path = BASE / k
        if check: assert path.read_bytes() == raw, k
        else: path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--check', action='store_true')
    build(parser.parse_args().check)
    print('PASS: deterministic isolated ANL-02 candidate; release/pins unchanged')
