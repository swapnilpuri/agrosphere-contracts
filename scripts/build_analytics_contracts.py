"""Deterministic isolated ANL-01 candidate, never promotes or pins a release."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'docs/analytics-poc'
UUID = {'type': 'string', 'format': 'uuid', 'pattern': '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'}
UTC = {'type': 'string', 'format': 'date-time', 'pattern': r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.[0-9]{1,6})?Z$'}
DATE = {'type': 'string', 'format': 'date', 'pattern': r'^\d{4}-\d{2}-\d{2}$'}
COUNT = {'type': 'integer', 'minimum': 0, 'maximum': 9223372036854775807}
MASS = {'type': 'string', 'pattern': r'^(?:0|[1-9][0-9]*)\.[0-9]{3}$'}
PATH = '/api/v1/analytics/estates/{estateId}/blocks/{blockId}/production/daily'
POLICY = 'SUM_ROUNDED_COLLECTION_KG_V1'


def obj(properties):
    return {'type': 'object', 'additionalProperties': False, 'properties': properties, 'required': list(properties)}


def nullable(schema):
    return {'anyOf': [schema, {'type': 'null'}]}


def schemas():
    metrics = obj({**{k: COUNT for k in ['activeCollectionCount', 'pendingDrcCount', 'calculatedCollectionCount', 'voidedCollectionCount']},
                   **{k: MASS for k in ['totalWetLatexKg', 'pendingWetLatexKg', 'calculatedWetLatexKg']},
                   'knownDryRubberKg': nullable(MASS), 'isComplete': {'type': 'boolean'}})
    day = obj({'date': DATE, 'availability': {'type': 'string', 'enum': ['NONE', 'OBSERVED']}, 'metrics': nullable(metrics)})
    source = obj({'collectionId': UUID, 'aggregateVersion': COUNT, 'sourceEventId': UUID, 'sourceEventAt': UTC, 'collectionDate': DATE})
    history = obj({'estateId': UUID, 'blockId': UUID, 'from': DATE, 'to': DATE, 'generatedAt': UTC,
                   'dataProvenance': {'type': 'string', 'const': 'SIMULATED'},
                   'aggregationPolicy': {'type': 'string', 'const': POLICY},
                   'projectionState': {'type': 'string', 'enum': ['OBSERVED_ONLY', 'INCOMPLETE']},
                   'lastProcessedAt': nullable(UTC), 'latestSourceEventAt': nullable(UTC),
                   'missingSourceVersionCount': {'type': 'string', 'pattern': r'^(?:0|[1-9][0-9]*)$'},
                   'conflictCount': COUNT, 'unsupportedCount': COUNT,
                   'sourceVersionSample': {'type': 'array', 'maxItems': 100, 'items': source},
                   'sourceVersionSampleTruncated': {'type': 'boolean'},
                   'days': {'type': 'array', 'minItems': 1, 'maxItems': 367, 'items': day}})
    problem = obj({'type': {'type': 'string', 'format': 'uri'}, 'title': {'type': 'string'}, 'status': {'type': 'integer', 'enum': [400, 401, 403, 404, 429, 503]}, 'detail': {'type': 'string'}})
    return {'DailyProductionHistory': history, 'Problem': problem}


def artifacts():
    definitions = schemas()
    parameters = [{'name': name, 'in': location, 'required': True, 'schema': schema}
                  for name, location, schema in [('estateId', 'path', UUID), ('blockId', 'path', UUID), ('from', 'query', DATE), ('to', 'query', DATE)]]
    responses = {'200': {'description': 'Exactly one row per requested date; NONE metrics are null. Observed records do not prove stream completeness.',
                         'content': {'application/json': {'schema': {'$ref': '#/components/schemas/DailyProductionHistory'}}}}}
    for code, label in [(400, 'Invalid/unknown query or range'), (401, 'Invalid/missing signed token'), (403, 'Role/estate/delegated read denied'), (404, 'Unknown/inactive canonical block'), (429, 'Rate limited'), (503, 'Reference/projection unavailable')]:
        responses[str(code)] = {'description': label, 'content': {'application/problem+json': {'schema': {'$ref': '#/components/schemas/Problem'}}}}
    api = {'openapi': '3.1.0', 'info': {'title': 'ANL-01 isolated Analytics candidate', 'version': '0.1.0',
           'description': 'UNRELEASED candidate. SIMULATED-only observed production history; no stream-completeness, forecast or yield claim.'},
           'paths': {PATH: {'get': {'operationId': 'getDailyProductionHistory', 'parameters': parameters, 'responses': responses,
             'description': 'Explicit estate/block; inclusive 1..367 dates, unknown parameters rejected. PLATFORM_ADMIN/PLANTATION_ADMIN globally; assigned ESTATE_ADMIN/ESTATE_MANAGER/AUDITOR only. Validate signed issuer/audience/lifetime and estate scope before references or projection queries. No worker/viewer/supervisor access. Delegated active-block check; dependency failure is 503, never empty success.'}}},
           'security': [{'bearerAuth': []}], 'components': {'securitySchemes': {'bearerAuth': {'type': 'http', 'scheme': 'bearer', 'bearerFormat': 'JWT'}}, 'schemas': definitions}}
    ids = ['00000000-0000-4000-8000-' + str(n).zfill(12) for n in range(1, 6)]
    empty = {'estateId': ids[0], 'blockId': ids[1], 'from': '2026-01-01', 'to': '2026-01-01', 'generatedAt': '2026-01-01T12:00:03Z',
        'dataProvenance': 'SIMULATED', 'aggregationPolicy': POLICY, 'projectionState': 'OBSERVED_ONLY', 'lastProcessedAt': None,
        'latestSourceEventAt': None, 'missingSourceVersionCount': '0', 'conflictCount': 0, 'unsupportedCount': 0,
        'sourceVersionSample': [], 'sourceVersionSampleTruncated': False,
        'days': [{'date': '2026-01-01', 'availability': 'NONE', 'metrics': None}]}
    pending = copy.deepcopy(empty)
    pending.update(lastProcessedAt='2026-01-01T12:00:02Z', latestSourceEventAt='2026-01-01T12:00:01Z',
        sourceVersionSample=[{'collectionId': ids[2], 'aggregateVersion': 0, 'sourceEventId': ids[3], 'sourceEventAt': '2026-01-01T12:00:01Z', 'collectionDate': '2026-01-01'}])
    pending['days'][0].update(availability='OBSERVED', metrics={'activeCollectionCount': 1, 'pendingDrcCount': 1,
        'calculatedCollectionCount': 0, 'voidedCollectionCount': 0, 'totalWetLatexKg': '10.000', 'pendingWetLatexKg': '10.000',
        'calculatedWetLatexKg': '0.000', 'knownDryRubberKg': None, 'isComplete': False})
    calculated = copy.deepcopy(pending); calculated['sourceVersionSample'][0]['aggregateVersion'] = 1
    calculated['days'][0]['metrics'].update(pendingDrcCount=0, calculatedCollectionCount=1, pendingWetLatexKg='0.000',
        calculatedWetLatexKg='10.000', knownDryRubberKg='3.333', isComplete=True)
    zero = copy.deepcopy(calculated); zero['days'][0]['metrics']['knownDryRubberKg'] = '0.000'
    voided = copy.deepcopy(calculated); voided['sourceVersionSample'][0]['aggregateVersion'] = 2
    voided['days'][0]['metrics'].update(activeCollectionCount=0, calculatedCollectionCount=0, voidedCollectionCount=1,
        totalWetLatexKg='0.000', calculatedWetLatexKg='0.000', knownDryRubberKg=None)
    corrected = copy.deepcopy(calculated); corrected['to'] = '2026-01-02'; corrected['sourceVersionSample'][0].update(aggregateVersion=2, collectionDate='2026-01-02')
    corrected['days'] = [copy.deepcopy(empty['days'][0]), dict(copy.deepcopy(calculated['days'][0]), date='2026-01-02')]
    incomplete = copy.deepcopy(calculated); incomplete.update(projectionState='INCOMPLETE', missingSourceVersionCount='1', conflictCount=1)
    denied = {'type': 'about:blank', 'title': 'Forbidden', 'status': 403, 'detail': 'Production history access denied'}
    unavailable = dict(denied, title='Unavailable', status=503, detail='Production history dependency unavailable')
    return {'openapi/analytics-service.yaml': api, **{'examples/' + name + '.json': data for name, data in
        [('none', empty), ('pending', pending), ('calculated', calculated), ('zero-drc', zero), ('voided', voided),
         ('corrected', corrected), ('incomplete', incomplete), ('denied', denied), ('unavailable', unavailable)]}}


def build(check=False):
    encoded = lambda x: (json.dumps(x, indent=2, ensure_ascii=True) + '\n').encode('utf-8')
    outputs = {'candidate/' + k: encoded(v) for k, v in artifacts().items()}
    inputs = {f'events/operations/v2/{name}.schema.json': hashlib.sha256((ROOT / f'events/operations/v2/{name}.schema.json').read_bytes()).hexdigest()
              for name in ['LatexCollectionRecorded', 'DrcMeasurementRecorded', 'LatexCollectionAdjusted', 'LatexCollectionVoided']}
    manifest = {'status': 'UNRELEASED_CANDIDATE', 'scope': 'ANL-01', 'releaseVersion': None,
                'inputSchemasSha256': inputs, 'artifacts': {k: hashlib.sha256(v).hexdigest() for k, v in sorted(outputs.items())}}
    outputs['CANDIDATE_MANIFEST.json'] = encoded(manifest)
    for key, raw in outputs.items():
        p = BASE / key
        if check: assert p.read_bytes() == raw, key
        else: p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(raw)
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--check', action='store_true')
    build(parser.parse_args().check)
    print('PASS: deterministic isolated ANL-01 candidate; no release/pins')
