"""Deterministic isolated TLM-01 candidate; never promotes released artifacts."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'docs/telemetry-poc'
UUID = {'type': 'string', 'format': 'uuid',
        'pattern': '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'}
UTC = {'type': 'string', 'format': 'date-time',
       'pattern': r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?Z$'}
KINDS = {'AIR_TEMPERATURE': 'CELSIUS', 'SOIL_MOISTURE': 'PERCENT', 'INTERVAL_RAINFALL': 'MILLIMETRE'}


def obj(properties):
    return {'type': 'object', 'additionalProperties': False,
            'properties': properties, 'required': list(properties)}


def observation():
    # Decimal string avoids binary floating point and fixes canonical wire precision.
    common = {'schemaVersion': {'type': 'integer', 'const': 1},
              'observationId': UUID, 'deviceId': UUID, 'estateId': UUID, 'blockId': UUID,
              'dataProvenance': {'type': 'string', 'const': 'SIMULATED'}, 'observedAt': UTC}
    variants = []
    for kind, unit in KINDS.items():
        props = dict(common, kind={'type': 'string', 'const': kind},
                     unit={'type': 'string', 'const': unit},
                     value={'type': 'string', 'maxLength': 20,
                            'pattern': r'^-?(?:0|[1-9][0-9]{0,11})(?:\.[0-9]{1,6})?$'})
        if kind == 'INTERVAL_RAINFALL':
            props.update(intervalStart=UTC, intervalEnd=UTC)
        variants.append(obj(props))
    return {'oneOf': variants}


def recorded():
    result = observation()
    for variant in result['oneOf']:
        variant['properties']['receivedAt'] = UTC
        variant['required'].append('receivedAt')
    return result


def artifacts():
    message = dict(observation(), **{'$schema': 'https://json-schema.org/draft/2020-12/schema',
        '$id': 'https://contracts.agrosphere.invalid/telemetry/v1/Observation.schema.json'})
    event = dict(obj({'eventId': UUID, 'eventType': {'type': 'string', 'const': 'TelemetryObservationRecorded'},
        'eventVersion': {'type': 'integer', 'const': 1}, 'timestamp': UTC,
        'source': {'type': 'string', 'const': 'agrosphere-telemetry-service'}, 'correlationId': UUID,
        'estateId': UUID, 'blockId': UUID, 'dataProvenance': {'type': 'string', 'const': 'SIMULATED'},
        'aggregateId': UUID, 'aggregateVersion': {'type': 'integer', 'const': 1}, 'payload': recorded()}),
        **{'$schema': 'https://json-schema.org/draft/2020-12/schema',
           '$id': 'https://contracts.agrosphere.invalid/telemetry/v1/TelemetryObservationRecorded.schema.json'})
    latest = obj({'estateId': UUID, 'blockId': UUID, 'generatedAt': UTC,
        'dataProvenance': {'type': 'string', 'const': 'SIMULATED'},
        'coverage': {'type': 'string', 'enum': ['NONE', 'PARTIAL', 'COMPLETE']},
        'readings': {'type': 'array', 'minItems': 0, 'maxItems': 3, 'items': recorded()}})
    problem = obj({'type': {'type': 'string', 'format': 'uri'}, 'title': {'type': 'string', 'maxLength': 120},
                   'status': {'type': 'integer', 'minimum': 400, 'maximum': 599},
                   'detail': {'type': 'string', 'maxLength': 512}})
    api = {'openapi': '3.1.0', 'info': {'title': 'Telemetry TLM-01 isolated candidate', 'version': '0.1.0',
        'description': 'UNRELEASED. One latest-readings operation; no MQTT HTTP publication endpoint.'},
        'servers': [{'url': 'https://api.agrosphere.invalid'}],
        'security': [{'bearerAuth': []}], 'paths': {'/api/v1/telemetry/estates/{estateId}/blocks/{blockId}/latest': {
            'parameters': [{'name': name, 'in': 'path', 'required': True, 'schema': UUID} for name in ['estateId', 'blockId']],
            'get': {'operationId': 'getLatestTelemetryReadings',
                'description': 'Issuer/audience and trusted estate_ids validated independently at Gateway/service. '
                    'Reuse Estate read roles: PLATFORM_ADMIN/PLANTATION_ADMIN with explicit target estate; '
                    'ESTATE_ADMIN/ESTATE_MANAGER/VIEWER/FIELD_SUPERVISOR/FIELD_WORKER/AUDITOR require trusted estate_ids. '
                    'Deny before query. Unknown/inactive authoritative block: 404; dependency unavailable: 503. '
                    'An authorized active block without readings returns 200, NONE and empty readings. '
                    'At most one reading per kind, sorted by kind; latest uses observedAt then lowercase UUID lexical order. '
                    'Coverage denotes kind presence, not freshness, calibration or accuracy.',
                'responses': {'200': {'description': 'Latest per measurement kind', 'content': {
                    'application/json': {'schema': {'$ref': '#/components/schemas/LatestReadings'}}}},
                    **{str(s): {'description': d, 'content': {'application/problem+json': {
                        'schema': {'$ref': '#/components/schemas/Problem'}}}} for s,d in [
                        (400,'Invalid request'),(401,'Unauthenticated'),(403,'Forbidden'),(404,'Not found'),
                        (429,'Rate limited'),(503,'Dependency unavailable')]}}}}},
        'components': {'securitySchemes': {'bearerAuth': {'type': 'http', 'scheme': 'bearer', 'bearerFormat': 'JWT'}},
                       'schemas': {'LatestReadings': latest, 'Problem': problem}}}
    ids = [f'00000000-0000-4000-8000-{i:012d}' for i in range(1, 8)]
    examples = []
    for i, (kind, unit) in enumerate(KINDS.items()):
        sample = {'schemaVersion': 1, 'observationId': ids[i], 'deviceId': ids[3], 'estateId': ids[4],
                  'blockId': ids[5], 'kind': kind, 'unit': unit, 'value': ['27.5','45','2.125'][i],
                  'observedAt': '2026-01-01T12:00:00Z', 'dataProvenance': 'SIMULATED'}
        if kind == 'INTERVAL_RAINFALL':
            sample.update(intervalStart='2026-01-01T11:00:00Z', intervalEnd='2026-01-01T12:00:00Z')
        examples.append(sample)
    readings = [dict(x, receivedAt='2026-01-01T12:00:01Z') for x in examples]
    envelope = {'eventId': ids[6], 'eventType': 'TelemetryObservationRecorded', 'eventVersion': 1,
        'timestamp': readings[0]['receivedAt'], 'source': 'agrosphere-telemetry-service', 'correlationId': ids[6],
        'estateId': ids[4], 'blockId': ids[5], 'dataProvenance': 'SIMULATED',
        'aggregateId': examples[0]['observationId'], 'aggregateVersion': 1, 'payload': readings[0]}
    return {'openapi/telemetry-service.yaml': api,
        'mqtt/Observation.schema.json': message,
        'events/telemetry/v1/TelemetryObservationRecorded.schema.json': event,
        **{f'examples/{x["kind"]}.json': x for x in examples},
        'examples/TelemetryObservationRecorded.json': envelope,
        'examples/LatestReadings.json': {'estateId': ids[4], 'blockId': ids[5],
            'generatedAt': '2026-01-01T12:00:02Z', 'dataProvenance': 'SIMULATED',
            'coverage': 'COMPLETE', 'readings': sorted(readings, key=lambda x: x['kind'])}}


def encoded(value):
    return (json.dumps(value, indent=2, ensure_ascii=True) + '\n').encode('utf-8')


def build(check=False):
    outputs = {'candidate/' + key: encoded(value) for key, value in artifacts().items()}
    manifest = {'status': 'UNRELEASED_CANDIDATE', 'scope': 'TLM-01', 'releaseVersion': None,
                'artifacts': {key: hashlib.sha256(value).hexdigest() for key,value in sorted(outputs.items())}}
    outputs['CANDIDATE_MANIFEST.json'] = encoded(manifest)
    for name, content in outputs.items():
        path = BASE / name
        if check:
            assert path.read_bytes() == content, f'Candidate drift: {name}'
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    build(args.check)
    print('PASS: isolated TLM-01 candidate deterministic bytes' if args.check else 'Built isolated TLM-01 candidate; no release/pins')
