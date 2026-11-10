"""Offline II-1 candidate checks, independent of producer implementations."""
from telemetry_release_compatibility import prior_telemetry, telemetry_inventory
import hashlib
import json
from datetime import datetime

from jsonschema import Draft202012Validator, FormatChecker, ValidationError
from openapi_spec_validator import validate

from build_crop_health_contracts import BASE, CANDIDATE, NAMES, OPERATIONS, ROOT


def load(path): return json.loads(path.read_text(encoding='utf-8'))


def require(value, message):
    if not value: raise ValueError(message)


def instant(value): return datetime.fromisoformat(value.replace('Z', '+00:00'))


def validate_event(event):
    name = event.get('eventType'); require(name in NAMES, 'Unsupported event')
    schema = load(CANDIDATE/'events/operations/crop-health/v1'/(name+'.schema.json'))
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(event)
    p = event['payload']; s = p['snapshot']
    for outer, inner in [('aggregateId','id'), ('aggregateVersion','version'), ('estateId','estateId'),
                          ('blockId','blockId'), ('dataProvenance','dataProvenance')]:
        require(event[outer] == s[inner], 'Envelope/snapshot mismatch: ' + outer)
    # IANA identifier validity and local-date/DST semantics are tested by Java ZoneId.
    # Windows Python has no bundled IANA database; do not approximate zones by offsets.
    require(instant(s['observedAt']) <= instant(event['timestamp']), 'Observation after recording')
    inspection = name.startswith('Field'); initial = name.endswith(('Recorded','Reported'))
    if not initial: require(p['previousVersion'] == s['version']-1, 'Nonadjacent version')
    if inspection:
        require(s['outcome'] != 'FOLLOW_UP' or s['linkedIncidentId'] is not None, 'Missing follow-up incident')
        if initial:
            require(s['state']=='RECORDED', 'Initial inspection must be recorded')
            require((s['outcome']=='CLEAR') == (s['linkedIncidentId'] is None), 'Initial inspection link mismatch')
        else: require((p['changeKind']=='VOID') == (s['state']=='VOIDED'), 'Inspection action/state mismatch')
    else:
        resolved = s['resolvedAt']
        require(s['status'] in ['RESOLVED','VOIDED'] or resolved is None, 'Unexpected resolution')
        require(s['status']!='RESOLVED' or resolved is not None, 'Resolution time missing')
        if resolved is not None:
            require(instant(s['observedAt']) <= instant(resolved) <= instant(event['timestamp']), 'Resolution chronology')
        if initial: require(s['status']=='OPEN', 'Initial incident must be open')
        else:
            kind = p['changeKind']
            if kind in ['TRIAGE','RESOLVE','REOPEN','VOID']:
                require(s['status']=={'TRIAGE':'IN_REVIEW','RESOLVE':'RESOLVED','REOPEN':'OPEN','VOID':'VOIDED'}[kind], 'Action/state mismatch')
            if kind=='AMEND': require(s['status'] in ['OPEN','IN_REVIEW'], 'Amend terminal incident')
            if kind=='CORRECT': require(s['status']!='VOIDED', 'Correct voided incident')


def request_validator(name):
    api = load(CANDIDATE/'openapi/operations-service.yaml')
    return Draft202012Validator({'$ref':'#/components/schemas/CH'+name, 'components':api['components']}, format_checker=FormatChecker())


def check_compatibility():
    b = load(BASE/'compatibility-baseline.json')
    promoted = (BASE/'RELEASE_0_7_0.json').exists()
    if promoted:
        require((ROOT/'VERSION').read_text().strip()==('0.13.0' if (ROOT/'docs/m4/RELEASE_0_13_0.json').exists() else '0.12.0' if (ROOT/'docs/analytics-environment-poc/RELEASE_0_12_0.json').exists() else '0.11.0' if (ROOT/'docs/analytics-poc/RELEASE_0_11_0.json').exists() else '0.10.0' if (ROOT/'docs/telemetry-poc/RELEASE_0_10_0.json').exists() else '0.9.0' if (ROOT/'docs/alerts-privacy/RELEASE_0_9_0.json').exists() else '0.8.0' if (ROOT/'docs/alerts-notifications/RELEASE_0_8_0.json').exists() else '0.7.0'),'Release version mismatch')
        for file, expected in load(BASE/'RELEASE_0_7_0.json')['files'].items():
            path=ROOT/'docs/alerts-notifications/previous-0.7.0'/file if file=='openapi/operations-service.yaml' and (ROOT/'docs/alerts-notifications/RELEASE_0_8_0.json').exists() else ROOT/file
            require(hashlib.sha256(prior_telemetry(path).read_bytes()).hexdigest()==expected, 'Accepted 0.7.0 artifact changed: '+file)
    for file, expected in b['files'].items():
        path = BASE/'previous-0.6.0'/file if promoted and file in ['VERSION','openapi/operations-service.yaml'] else ROOT/file
        require(hashlib.sha256(prior_telemetry(path).read_bytes()).hexdigest()==expected, 'Released bytes changed: '+file)
    released = load(BASE/'previous-0.6.0/openapi/operations-service.yaml' if promoted else ROOT/'openapi/operations-service.yaml'); candidate = load(CANDIDATE/'openapi/operations-service.yaml')
    for path, value in released['paths'].items(): require(candidate['paths'].get(path)==value, 'Old path changed')
    for group, entries in released['components'].items():
        for name, value in entries.items(): require(candidate['components'][group].get(name)==value, 'Old component changed')
    metadata = lambda a:{k:v for k,v in a.items() if k not in ['paths','components']}
    require(metadata(released)==metadata(candidate), 'Metadata changed')
    operations = lambda a:{(p,m) for p,body in a['paths'].items() for m in body}
    require(operations(candidate)-operations(released)=={('/api/v1'+p,m) for m,p,*_ in OPERATIONS}, 'Unexpected operation set')
    require(len(operations(released))==42 and len(operations(candidate))==58, 'Expected 42 + 16 operations')
    return candidate


def run():
    api = check_compatibility(); validate(api)
    manifest = load(BASE/'CANDIDATE_MANIFEST.json')
    require(len(manifest['files'])==11, 'Expected eleven reviewed artifacts')
    for file, expected in manifest['files'].items():
        require(hashlib.sha256((ROOT/file).read_bytes()).hexdigest()==expected, 'Manifest drift: '+file)
    for schema in api['components']['schemas'].values(): Draft202012Validator.check_schema(schema)
    folder = CANDIDATE/'examples/operations/crop-health/v1'
    for name in NAMES:
        Draft202012Validator.check_schema(load(CANDIDATE/'events/operations/crop-health/v1'/(name+'.schema.json')))
        validate_event(load(folder/(name+'.json')))
    for name, body in load(folder/'requests.json').items(): request_validator(name).validate(body)
    for negative in load(folder/'negative.json'):
        try: validate_event(negative['event'])
        except (ValueError,ValidationError): pass
        else: raise AssertionError('Accepted negative: '+negative['case'])
    print('PASS: II-1 58-operation candidate, four minimal families, seven request shapes, fourteen negatives, released bytes unchanged')


if __name__=='__main__': run()
