"""Offline TLM candidate wire and cross-field oracle, not a running service."""
import json
import hashlib
from datetime import datetime, timedelta
from decimal import Decimal
from jsonschema import Draft202012Validator, FormatChecker
from openapi_spec_validator import validate as validate_openapi
from build_telemetry_contracts import BASE, KINDS, artifacts, build


def schema_validate(schema, value):
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(value)


def instant(text):
    return datetime.fromisoformat(text.replace('Z', '+00:00'))


def message(value, recorded=False):
    definitions = artifacts()
    schema = (definitions['events/telemetry/v1/TelemetryObservationRecorded.schema.json']['properties']['payload']
              if recorded else definitions['mqtt/Observation.schema.json'])
    schema_validate(schema, value)
    number = Decimal(value['value'])
    if abs(number) > Decimal('999999999999.999999'):
        raise ValueError('Measurement bounds')
    if value['kind'] == 'SOIL_MOISTURE' and not Decimal(0) <= number <= Decimal(100):
        raise ValueError('Percent bounds')
    if value['kind'] == 'INTERVAL_RAINFALL':
        if number < 0 or not instant(value['intervalStart']) < instant(value['intervalEnd']) <= instant(value['observedAt']):
            raise ValueError('Rainfall interval/range')
    if recorded and instant(value['observedAt']) - instant(value['receivedAt']) > timedelta(minutes=5):
        raise ValueError('Future skew')


def event(value):
    schema_validate(artifacts()['events/telemetry/v1/TelemetryObservationRecorded.schema.json'], value)
    payload = value['payload']
    message(payload, recorded=True)
    for key in ['estateId', 'blockId', 'dataProvenance']:
        if value[key] != payload[key]:
            raise ValueError('Envelope identity/provenance mismatch')
    if value['aggregateId'] != payload['observationId'] or value['timestamp'] != payload['receivedAt']:
        raise ValueError('Aggregate or recorded timestamp mismatch')


def latest(value):
    schema_validate(artifacts()['openapi/telemetry-service.yaml']['components']['schemas']['LatestReadings'], value)
    kinds = [x['kind'] for x in value['readings']]
    if kinds != sorted(set(kinds)):
        raise ValueError('Duplicate or unsorted kinds')
    expected = 'NONE' if not kinds else 'COMPLETE' if len(kinds) == len(KINDS) else 'PARTIAL'
    if value['coverage'] != expected:
        raise ValueError('Incorrect presence coverage')
    for reading in value['readings']:
        message(reading, recorded=True)
        if reading['estateId'] != value['estateId'] or reading['blockId'] != value['blockId']:
            raise ValueError('Cross-scope response')
        if instant(reading['receivedAt']) > instant(value['generatedAt']):
            raise ValueError('Response precedes receipt')


def run():
    build(check=True)
    items = artifacts()
    for path, value in items.items():
        if path.endswith('.schema.json'):
            Draft202012Validator.check_schema(value)
    validate_openapi(items['openapi/telemetry-service.yaml'])
    for kind in KINDS:
        message(json.loads((BASE / f'candidate/examples/{kind}.json').read_text()))
    event(json.loads((BASE / 'candidate/examples/TelemetryObservationRecorded.json').read_text()))
    latest(json.loads((BASE / 'candidate/examples/LatestReadings.json').read_text()))
    validate_release()
    print('PASS: TLM-01 isolated OpenAPI, MQTT/event schema formats, cross-field example semantics and manifest')


def validate_release():
    release_path = BASE / 'RELEASE_0_10_0.json'
    if not release_path.exists():
        return  # Isolated authoring before release remains supported.
    root = BASE.parents[1]
    release = json.loads(release_path.read_text(encoding='utf-8'))
    manifest_bytes = (BASE / 'CANDIDATE_MANIFEST.json').read_bytes()
    expected_manifest = '174140bc1db129ab879d9e431e9065a6715746c31c70fa0ec2bb7992063f01b0'
    assert hashlib.sha256(manifest_bytes).hexdigest() == expected_manifest
    assert release['release'] == '0.10.0' and release['sourceManifestSha256'] == expected_manifest
    version = root / 'docs/analytics-poc/previous-0.10.0/VERSION' if (root / 'docs/analytics-poc/RELEASE_0_11_0.json').exists() else root / 'VERSION'
    assert version.read_text().strip() == '0.10.0'
    manifest = json.loads(manifest_bytes)
    expected_files = {}
    for path, digest in manifest['artifacts'].items():
        relative = path.removeprefix('candidate/')
        if relative.startswith('examples/'):
            relative = 'examples/telemetry/v1/' + relative.split('/')[-1]
        expected_files[relative] = digest
    assert release['files'] == expected_files
    archive = {
        'docs/telemetry-poc/previous-0.9.0/VERSION': '03627dfd7695e0e68ca0cb329b30582a35c49384d98227536edca14080eea08b',
        'docs/telemetry-poc/previous-0.9.0/openapi/telemetry-service.yaml': '1bfc36028bd17709009e45ab1625da80307fdfb8d89a37b6487f8e7be3a9a829',
    }
    assert release['archive'] == archive
    for path, digest in {**expected_files, **archive}.items():
        assert hashlib.sha256((root / path).read_bytes()).hexdigest() == digest, path
    print('PASS: local Contracts 0.10.0 exact eight-artifact promotion and prior-version archive')


if __name__ == '__main__':
    run()
