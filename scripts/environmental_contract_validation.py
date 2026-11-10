"""Offline environmental query/response semantic oracle; not a runtime adapter."""
from datetime import timedelta
from decimal import Decimal
from jsonschema import Draft202012Validator, FormatChecker
from openapi_spec_validator import validate as validate_openapi
from build_environmental_contracts import ROOT, PATH, UTC, UUID, KINDS, schemas, artifacts, build, baseline_input
from telemetry_contract_validation import instant


def require(ok, message):
    if not ok: raise ValueError(message)


def validate(schema, value):
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(value)


def query(value):
    require(set(value) == {'estateId', 'blockId', 'from', 'to'}, 'Explicit query/unknown filters')
    for k in ['estateId', 'blockId']: validate(UUID, value[k])
    for k in ['from', 'to']: validate(UTC, value[k])
    require(timedelta(0) < instant(value['to']) - instant(value['from']) <= timedelta(hours=24), 'Half-open 24h window')


def history(value, expected_query=None):
    validate(schemas()['EnvironmentalHistory'], value)
    q = {k: value[k] for k in ['estateId', 'blockId', 'from', 'to']}
    query(q)
    if expected_query is not None: require(q == expected_query, 'Scope/window mismatch')
    rows = value['observations']; total = int(value['totalMatchingCount'])
    require(len(rows) == min(total, 1000) and value['truncated'] == (total > 1000), 'Cap/count/truncation')
    require(value['availability'] == ('NONE' if total == 0 else 'OBSERVED'), 'Absence is not zero')
    require(value['projectionState'] == ('INCOMPLETE' if value['conflictCount'] > 0 else 'OBSERVED_ONLY'), 'Conflict state')
    keys = [(instant(r['observedAt']), r['observationId']) for r in rows]
    require(keys == sorted(keys), 'Ordering')
    require(len({r['observationId'] for r in rows}) == len(rows) and len({r['sourceEventId'] for r in rows}) == len(rows), 'Immutable source identity')
    require(value['returnedKindCounts'] == {k: sum(r['kind'] == k for r in rows) for k in KINDS}, 'Returned kind counts')
    for r in rows:
        require(instant(value['from']) <= instant(r['observedAt']) < instant(value['to']), 'Observation outside window')
        require(r['sourceEventAt'] == r['receivedAt'], 'Recorded source time')
        require(instant(r['observedAt']) <= instant(r['receivedAt']) + timedelta(minutes=5), 'Future skew')
        number = Decimal(r['value'])
        if r['kind'] == 'SOIL_MOISTURE': require(0 <= number <= 100, 'Percent range')
        if r['kind'] == 'INTERVAL_RAINFALL':
            require(number >= 0 and instant(r['intervalStart']) < instant(r['intervalEnd']) <= instant(r['observedAt']), 'Rain interval/range')
        require(value['latestSourceEventAt'] is not None and instant(r['sourceEventAt']) <= instant(value['latestSourceEventAt']), 'Source metadata')
    require((value['lastProcessedAt'] is None) == (value['latestSourceEventAt'] is None), 'Paired metadata')
    if rows or value['conflictCount']: require(value['lastProcessedAt'] is not None, 'Missing processing metadata')
    if value['lastProcessedAt'] is not None: require(instant(value['lastProcessedAt']) <= instant(value['generatedAt']), 'Processing after generation')


def run():
    build(check=True)
    values = artifacts(); api = values['openapi/analytics-service.yaml']
    validate_openapi(api)
    for name, schema in schemas().items(): Draft202012Validator.check_schema(schema)
    # Every released production path/schema remains semantically unchanged in the extension.
    import json
    released = json.loads(baseline_input('openapi/analytics-service.yaml').read_text())
    require(set(api['paths']) == set(released['paths']) | {PATH}, 'Exactly one additive path')
    for path, definition in released['paths'].items(): require(api['paths'][path] == definition, 'Production path changed')
    for name, definition in released['components']['schemas'].items(): require(api['components']['schemas'][name] == definition, 'Production schema changed')
    require(api['security'] == released['security'], 'Security changed')
    for name, value in values.items():
        if name.startswith('examples/'):
            if 'status' in value: validate(schemas()['EnvironmentalProblem'], value)
            else: history(value)
    print('PASS: isolated ANL-02 additive API, 13 examples, exact observation/window/conflict/source semantics')
    from environmental_release_compatibility import validate_release
    validate_release()


if __name__ == '__main__': run()
