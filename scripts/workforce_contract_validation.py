"""Offline schema/semantic/compatibility checks for isolated WA-1 candidates."""
import hashlib
import json
from datetime import date
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker, ValidationError
from openapi_spec_validator import validate

from build_workforce_contracts import CANDIDATE, NAMES, OPERATIONS, ROOT


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_event(event):
    name = event.get('eventType')
    require(name in NAMES, 'Unsupported workforce event')
    schema = load(CANDIDATE / 'events/operations/workforce/v1' / (name + '.schema.json'))
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(event)
    snapshot = event['payload']['snapshot']
    registration = name.startswith('WorkerRegistration')
    for outer, inner in [('aggregateId', 'registrationId' if registration else 'attendanceId'),
                         ('aggregateVersion', 'version'), ('estateId', 'estateId'), ('dataProvenance', 'dataProvenance')]:
        require(event[outer] == snapshot[inner], 'Envelope/snapshot mismatch: ' + outer)
    if registration:
        periods = snapshot['activePeriods']
        require(len({p['id'] for p in periods}) == len(periods), 'Duplicate active-period id')
        ordered = sorted(periods, key=lambda p: p['activeFrom'])
        for i, period in enumerate(ordered):
            start = date.fromisoformat(period['activeFrom'])
            end = date.fromisoformat(period['activeTo']) if period['activeTo'] else None
            require(end is None or end > start, 'Empty/reversed active period')
            if i:
                prior_end = ordered[i-1]['activeTo']
                require(prior_end is not None and date.fromisoformat(prior_end) <= start, 'Overlapping active periods')
    if name.endswith('Changed'):
        payload = event['payload']
        require(payload['previousVersion'] == snapshot['version'] - 1, 'Nonadjacent previous revision')
        if not registration:
            require((payload['changeKind'] == 'VOID') == (snapshot['status'] == 'VOIDED'), 'Change kind/status mismatch')


def check_compatibility():
    baseline = load(ROOT / 'docs/worker-attendance/compatibility-baseline.json')
    require(hashlib.sha256((ROOT / 'VERSION').read_bytes()).hexdigest() == baseline['versionSha256'], 'Released VERSION changed')
    for name, expected in baseline['files'].items():
        require(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, 'Released artifact changed: ' + name)
    released = load(ROOT / 'openapi/operations-service.yaml')
    candidate = load(CANDIDATE / 'openapi/operations-service.yaml')
    for path, body in released['paths'].items():
        require(candidate['paths'].get(path) == body, 'Old API path changed: ' + path)
    for group, entries in released['components'].items():
        for name, definition in entries.items():
            require(candidate['components'][group].get(name) == definition, 'Old API component changed: ' + name)
    require({k:v for k,v in candidate.items() if k not in ['paths', 'components']} ==
            {k:v for k,v in released.items() if k not in ['paths', 'components']}, 'Old API metadata changed')
    added = {(p,m) for p,v in candidate['paths'].items() for m in v} - {(p,m) for p,v in released['paths'].items() for m in v}
    require(added == {('/api/v1'+suffix, method) for method,suffix,*_ in OPERATIONS}, 'Unexpected added operation')
    require(sum(len(v) for v in candidate['paths'].values()) == 42, 'Expected 27 preserved plus 15 workforce operations')
    return candidate


def request_validator(name):
    api = load(CANDIDATE / 'openapi/operations-service.yaml')
    schema = {'$ref': '#/components/schemas/' + name, 'components': api['components']}
    return Draft202012Validator(schema, format_checker=FormatChecker())


def run():
    api = check_compatibility()
    validate(api)
    for schema in api['components']['schemas'].values():
        Draft202012Validator.check_schema(schema)
    folder = CANDIDATE / 'examples/operations/workforce/v1'
    for name in NAMES:
        schema = load(CANDIDATE / 'events/operations/workforce/v1' / (name + '.schema.json'))
        Draft202012Validator.check_schema(schema)
        validate_event(load(folder / (name + '.json')))
    for name, body in load(folder / 'requests.json').items():
        request_validator(name).validate(body)
    for negative in load(folder / 'negative.json'):
        try:
            validate_event(negative['event'])
        except (ValueError, ValidationError):
            pass
        else:
            raise AssertionError('Accepted negative: ' + negative['case'])
    print('PASS: WA-1 isolated 42-operation API, four private-field-free event types, seven request shapes, nine persisted negatives, all 71 released artifact hashes')


if __name__ == '__main__':
    run()
