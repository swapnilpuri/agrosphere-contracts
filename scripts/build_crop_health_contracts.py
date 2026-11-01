"""Build II-1 candidates in isolation; no release, promotion or pin mutation."""
import argparse
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'docs/incident-inspection'
CANDIDATE = BASE / 'candidate'
UUID = {'type': 'string', 'format': 'uuid'}
VERSION = {'type': 'integer', 'format': 'int64', 'minimum': 0, 'maximum': 9223372036854775807}
# Requests accept an explicit offset; event/response serialization uses canonical UTC.
TIME = {'type': 'string', 'format': 'date-time', 'pattern': r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$'}
UTC = dict(TIME, pattern=r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$')
PROVENANCE = {'type': 'string', 'const': 'SIMULATED'}
CATEGORIES = ['PEST_SIGNS', 'DISEASE_SIGNS', 'TREE_DAMAGE', 'OTHER_CROP_HEALTH']
SEVERITIES = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
STATUSES = ['OPEN', 'IN_REVIEW', 'RESOLVED', 'VOIDED']
NAMES = ['FieldInspectionRecorded', 'FieldInspectionChanged', 'CropHealthIncidentReported', 'CropHealthIncidentChanged']


def enum(values):
    return {'type': 'string', 'enum': values}


def obj(properties, required=None, **extra):
    return dict(type='object', additionalProperties=False, properties=properties,
                required=list(properties) if required is None else required, **extra)


def nullable(schema):
    return {'anyOf': [schema, {'type': 'null'}]}


def text(limit):
    return {'type': 'string', 'minLength': 1, 'maxLength': limit,
            'pattern': r'^[^\u0000-\u001F\u007F-\u009F]*\S[^\u0000-\u001F\u007F-\u009F]*$',
            'description': 'Unicode; trim surrounding whitespace before validation and command hashing. No controls or personal information.'}


def ref(name):
    return {'$ref': '#/components/schemas/CH' + name}


def page(item):
    return obj({'content': {'type': 'array', 'items': item}, 'page': {'type': 'integer', 'minimum': 0},
                'size': {'type': 'integer', 'minimum': 1, 'maximum': 100}, 'totalElements': VERSION})


def definitions():
    observation = {'observedAt': TIME, 'findings': text(2000), 'outcome': enum(['CLEAR', 'FOLLOW_UP'])}
    report = {'observedAt': TIME, 'category': enum(CATEGORIES), 'severity': enum(SEVERITIES),
              'summary': text(200), 'details': text(2000)}
    identity = {'estateId': UUID, 'blockId': UUID, 'dataProvenance': PROVENANCE}
    linked = obj({k: v for k, v in report.items() if k != 'observedAt'})
    audit = {'id': UUID, **identity, 'observedAt': UTC, 'estateTimezone': text(100),
             'version': VERSION, 'createdAt': UTC, 'updatedAt': UTC}
    inspection = obj({**audit, 'findings': text(2000), 'outcome': enum(['CLEAR', 'FOLLOW_UP']),
        'state': enum(['RECORDED', 'VOIDED']), 'linkedIncidentId': nullable(UUID),
        'linkedIncidentStatus': nullable(enum(STATUSES)), 'linkedIncidentVersion': nullable(VERSION)})
    incident = obj({**audit, 'inspectionId': nullable(UUID), 'category': enum(CATEGORIES),
        'severity': enum(SEVERITIES), 'summary': text(200), 'details': text(2000), 'status': enum(STATUSES),
        'resolvedAt': nullable(UTC), 'resolutionNote': nullable(text(1000))})
    change = {'expectedVersion': VERSION, 'reason': text(1000), 'inspectionVersion': VERSION}
    shapes = {
        'InspectionView': inspection, 'IncidentView': incident,
        'InspectionSnapshot': obj({k:v for k,v in inspection['properties'].items()
                                  if k not in ['linkedIncidentStatus', 'linkedIncidentVersion']}),
        'InspectionCreateResult': obj({'inspection': ref('InspectionView'), 'incident': nullable(ref('IncidentView'))}),
        'InspectionRecord': obj({**identity, **observation, 'incident': linked, 'backdateReason': text(1000)},
            [*identity, *observation], oneOf=[
                {'properties': {'outcome': {'const': 'CLEAR'}}, 'not': {'required': ['incident']}},
                {'properties': {'outcome': {'const': 'FOLLOW_UP'}}, 'required': ['incident']}]),
        'IncidentReport': obj({**identity, **report, 'backdateReason': text(1000)}, [*identity, *report]),
        'InspectionCorrect': obj({'inspectionVersion': VERSION, 'incidentVersion': VERSION, 'reason': text(1000),
            **observation, 'incident': linked}, ['inspectionVersion', 'reason', *observation]),
        'InspectionVoid': obj({'inspectionVersion': VERSION, 'incidentVersion': VERSION, 'reason': text(1000)},
            ['inspectionVersion', 'reason']),
        'IncidentEdit': obj({**change, **report}, ['expectedVersion', 'reason', *report]),
        'IncidentAction': obj(change, ['expectedVersion', 'reason']),
        'IncidentResolve': obj({**change, 'resolvedAt': TIME, 'resolutionNote': text(1000)},
            ['expectedVersion', 'reason', 'resolvedAt', 'resolutionNote'])}
    for prefix, view in [('Inspection', 'InspectionView'), ('Incident', 'IncidentView')]:
        shapes[prefix + 'Page'] = page(ref(view))
        shapes[prefix + 'HistoryEntry'] = obj({'id': UUID, 'version': VERSION, 'previousVersion': nullable(VERSION),
            'commandKind': enum(['RECORD', 'CORRECT', 'VOID'] if prefix == 'Inspection' else
                                ['REPORT', 'AMEND', 'TRIAGE', 'RESOLVE', 'REOPEN', 'VOID', 'CORRECT']),
            'reason': nullable(text(1000)), 'recordedAt': UTC, 'recordedBy': text(200),
            'correlationId': UUID, 'snapshot': ref('InspectionSnapshot' if prefix == 'Inspection' else view)})
        shapes[prefix + 'HistoryPage'] = page(ref(prefix + 'HistoryEntry'))
    return {'CH' + k: v for k, v in shapes.items()}


OPERATIONS = [
    ('post', '/inspections', 'recordFieldInspection', 'InspectionRecord', 'InspectionCreateResult', 'CREATE'),
    ('get', '/inspections', 'listFieldInspections', None, 'InspectionPage', 'READ'),
    ('get', '/inspections/{id}', 'getFieldInspection', None, 'InspectionView', 'READ'),
    ('get', '/inspections/{id}/history', 'getFieldInspectionHistory', None, 'InspectionHistoryPage', 'HISTORY'),
    ('post', '/inspections/{id}/corrections', 'correctFieldInspection', 'InspectionCorrect', 'InspectionCreateResult', 'MANAGER'),
    ('post', '/inspections/{id}/void', 'voidFieldInspection', 'InspectionVoid', 'InspectionView', 'MANAGER'),
    ('post', '/incidents', 'reportCropHealthIncident', 'IncidentReport', 'IncidentView', 'CREATE'),
    ('get', '/incidents', 'listCropHealthIncidents', None, 'IncidentPage', 'READ'),
    ('get', '/incidents/{id}', 'getCropHealthIncident', None, 'IncidentView', 'READ'),
    ('get', '/incidents/{id}/history', 'getCropHealthIncidentHistory', None, 'IncidentHistoryPage', 'HISTORY'),
    ('post', '/incidents/{id}/amendments', 'amendCropHealthIncident', 'IncidentEdit', 'IncidentView', 'MANAGER'),
    ('post', '/incidents/{id}/triage', 'triageCropHealthIncident', 'IncidentAction', 'IncidentView', 'MANAGER'),
    ('post', '/incidents/{id}/resolve', 'resolveCropHealthIncident', 'IncidentResolve', 'IncidentView', 'MANAGER'),
    ('post', '/incidents/{id}/reopen', 'reopenCropHealthIncident', 'IncidentAction', 'IncidentView', 'MANAGER'),
    ('post', '/incidents/{id}/void', 'voidCropHealthIncident', 'IncidentAction', 'IncidentView', 'MANAGER'),
    ('post', '/incidents/{id}/corrections', 'correctCropHealthIncident', 'IncidentEdit', 'IncidentView', 'MANAGER')]


def param(name, schema, required=False, where='query'):
    return {'name': name, 'in': where, 'required': required, 'schema': schema}


POLICY = ('Validated signed sub and trusted estate_ids. PLATFORM_ADMIN globally with explicit estate on lists; '
          'scoped ESTATE_ADMIN/ESTATE_MANAGER manage; FIELD_SUPERVISOR reads current and creates estate-today only; '
          'AUDITOR reads current/history. PLANTATION_ADMIN/FIELD_WORKER/VIEWER alone grant nothing. '
          'Ordinary views omit actors/revision reasons; history manager/auditor only. Scope before query/count/link/replay. '
          'Foreign/missing object IDs uniformly 404 after feature role validation; explicit denied estate 403. '
          'All writes SIMULATED-only; REAL enablement requires separately implemented reviewed privacy policy. ')
COMMAND = ('UUID Idempotency-Key: feature-scoped actor/key reservation; normalize method/path/body, trim text and '
           'canonicalize times to UTC microseconds before hashing. Identical retries return original success/status/Location; '
           'different command 409. Reauthorize current operation/scope/projection before replay; permission downgrade denies replay. '
           'Unknown outcome: retry same frozen command/key. Fresh-key no-op 409. Existing roots require versions; '
           'all linked incident commands require inspectionVersion; inspection commands require incidentVersion iff linked. '
           'Reserve then lock inspection before incident; validate both versions and write root(s)/revision(s)/receipt/outbox atomically. ')


def api_candidate():
    base_api = ROOT / 'docs/incident-inspection/previous-0.6.0/openapi/operations-service.yaml'
    if not base_api.exists(): base_api = ROOT / 'openapi/operations-service.yaml'
    api = json.loads(base_api.read_text(encoding='utf-8'))
    api['components']['schemas'].update(definitions())
    for method, suffix, name, request, response, permission in OPERATIONS:
        params = [param('id', UUID, True, 'path')] if '{id}' in suffix else []
        if response.endswith('Page'):
            params += [param('page', {'type': 'integer', 'minimum': 0, 'default': 0}),
                       param('size', {'type': 'integer', 'minimum': 1, 'maximum': 100, 'default': 25})]
        if suffix in ['/inspections', '/incidents'] and method == 'get':
            params += [param('estateId', UUID, True), param('provenance', PROVENANCE, True), param('blockId', UUID),
                       param('observedFrom', TIME), param('observedTo', TIME)]
            if suffix == '/inspections':
                params += [param('outcome', enum(['CLEAR', 'FOLLOW_UP'])), param('state', enum(['RECORDED', 'VOIDED']))]
            else:
                params += [param('category', enum(CATEGORIES)), param('severity', enum(SEVERITIES)),
                           dict(param('status', {'type': 'array', 'minItems': 1, 'uniqueItems': True, 'items': enum(STATUSES),
                                                 'default': ['OPEN', 'IN_REVIEW']}), style='form', explode=True)]
        if request:
            params += [param('Idempotency-Key', UUID, True, 'header')]
        code = '201' if request in ['InspectionRecord', 'IncidentReport'] else '200'
        headers = {'X-Correlation-ID': {'schema': UUID}}
        if code == '201':
            headers['Location'] = {'schema': {'type': 'string'}, 'description': '/api/v1' + suffix + '/{id}; preserved on replay'}
        responses = {code: {'description': 'Authorized original command result' if request else 'Authorized query',
            'headers': headers, 'content': {'application/json': {'schema': ref(response)}}}}
        for status, description in [('400', 'Malformed/unknown fields, precision, range or page'), ('401', 'Invalid JWT'),
            ('403', 'Role/estate/backdate/provenance denied'), ('404', 'Missing or inaccessible object'),
            ('409', 'Version/link/state/key/no-op conflict; bounded lock timeout is retryable'),
            ('422', 'Missing/inactive/mismatched master reference'), ('503', 'Bounded master dependency failure')]:
            responses[status] = {'description': description, 'content': {'application/problem+json':
                {'schema': {'$ref': '#/components/schemas/ProblemDetail'}}}}
        description = POLICY + (COMMAND if request else '')
        if name == 'recordFieldInspection':
            description += 'CLEAR: no incident. FOLLOW_UP: required category/severity/summary/details, linked atomically at the inspection observedAt. Missing backdateReason on manager past-date creation is 400.'
        if name == 'correctFieldInspection':
            description += ('Only RECORDED. Full observation replacement, mandatory reason. Linked incident is never edited. '
                'CLEAR->FOLLOW_UP creates first incident iff no retained link; incident input required only then. '
                'FOLLOW_UP->CLEAR requires linked VOIDED incident and retains link; never create second link. '
                'Other corrections must omit incident input. Block/identity/provenance immutable; new linked evidence revalidates active master.')
        if name == 'voidFieldInspection':
            description += 'Only RECORDED; linked incident must already be VOIDED; no automatic cascade.'
        if name == 'amendCropHealthIncident':
            description += 'Only OPEN/IN_REVIEW; full mutable report replacement, no status/identity/link edits.'
        if name == 'correctCropHealthIncident':
            description += 'OPEN/IN_REVIEW/RESOLVED only; full report replacement; preserve lifecycle, link and all retained resolution chronology.'
        if name == 'triageCropHealthIncident': description += 'OPEN->IN_REVIEW only.'
        if name == 'resolveCropHealthIncident': description += 'OPEN/IN_REVIEW->RESOLVED; observedAt<=resolvedAt<=now, resolution note required.'
        if name == 'reopenCropHealthIncident': description += 'RESOLVED->OPEN; clear current resolution fields, retain historical evidence.'
        if name == 'voidCropHealthIncident': description += 'Any nonvoided->VOIDED terminal; retain resolution metadata if previously resolved; inspection not automatically voided.'
        op = {'operationId': name, 'tags': ['crop-health'], 'security': [{'bearerAuth': []}],
              'parameters': params, 'responses': responses, 'description': description,
              'x-crop-health-permission': permission,
              'x-query-constraints': {'unknownFilters': 'reject', 'dateBounds': 'both-or-neither; half-open [from,to)',
                  'maximumOffset': 2147483647, 'sort': 'observedAt DESC,id DESC', 'counts': 'same scoped request snapshot'}}
        if request:
            op['requestBody'] = {'required': True, 'content': {'application/json': {'schema': ref(request)}}}
        api['paths'].setdefault('/api/v1' + suffix, {})[method] = op
    return api


def snapshot(inspection):
    fields = {'id': UUID, 'estateId': UUID, 'blockId': UUID, 'observedAt': UTC, 'estateTimezone': text(100),
              'dataProvenance': PROVENANCE, 'version': VERSION}
    if inspection:
        fields.update(outcome=enum(['CLEAR', 'FOLLOW_UP']), state=enum(['RECORDED', 'VOIDED']), linkedIncidentId=nullable(UUID))
    else:
        fields.update(inspectionId=nullable(UUID), category=enum(CATEGORIES), severity=enum(SEVERITIES),
                      status=enum(STATUSES), resolvedAt=nullable(UTC))
    return fields


def event_schema(name):
    inspection = name.startswith('Field')
    initial = name.endswith(('Recorded', 'Reported'))
    fields = snapshot(inspection)
    fields['version'] = dict(VERSION, **({'const': 0} if initial else {'minimum': 1}))
    payload = {'snapshot': obj(fields)}
    if not initial:
        payload.update(previousVersion=VERSION, changeKind=enum(['CORRECT', 'VOID'] if inspection else
                      ['AMEND', 'TRIAGE', 'RESOLVE', 'REOPEN', 'VOID', 'CORRECT']))
    return obj({'eventId': UUID, 'eventType': {'type': 'string', 'const': name},
        'eventVersion': {'type': 'integer', 'const': 1}, 'timestamp': UTC,
        'source': {'type': 'string', 'const': 'agrosphere-operations-service'}, 'correlationId': UUID,
        'estateId': UUID, 'blockId': UUID, 'dataProvenance': PROVENANCE, 'aggregateId': UUID,
        'aggregateVersion': dict(VERSION, **({'const': 0} if initial else {'minimum': 1})), 'payload': obj(payload)},
        **{'$schema': 'https://json-schema.org/draft/2020-12/schema',
           '$id': 'https://schemas.agrosphere.invalid/operations/crop-health/v1/' + name + '.schema.json', 'title': name})


def uid(n): return '00000000-0000-0000-0000-' + str(n).zfill(12)


def examples():
    events = {}
    for i, name in enumerate(NAMES):
        inspection = name.startswith('Field'); initial = name.endswith(('Recorded', 'Reported'))
        state = dict(id=uid(3 if inspection else 4), estateId=uid(1), blockId=uid(2),
            observedAt='2026-10-31T10:00:00Z', estateTimezone='Africa/Libreville', dataProvenance='SIMULATED', version=0 if initial else 1)
        if inspection: state.update(outcome='FOLLOW_UP', state='RECORDED' if initial else 'VOIDED', linkedIncidentId=uid(4))
        else: state.update(inspectionId=uid(3), category='TREE_DAMAGE', severity='LOW', status='OPEN' if initial else 'VOIDED', resolvedAt=None)
        payload = {'snapshot': state}
        if not initial: payload.update(previousVersion=0, changeKind='VOID')
        events[name] = dict(eventId=uid(100+i), eventType=name, eventVersion=1, timestamp='2026-10-31T12:00:00Z',
            source='agrosphere-operations-service', correlationId=uid(200), estateId=uid(1), blockId=uid(2),
            dataProvenance='SIMULATED', aggregateId=state['id'], aggregateVersion=state['version'], payload=payload)
    report = dict(observedAt='2026-10-31T11:00:00+01:00', category='TREE_DAMAGE', severity='LOW',
                  summary='SIMULATED crop observation', details='SIMULATED field evidence for contract testing')
    observation = dict(observedAt=report['observedAt'], findings='SIMULATED inspection finding', outcome='FOLLOW_UP')
    identity = dict(estateId=uid(1), blockId=uid(2), dataProvenance='SIMULATED')
    requests = {'InspectionRecord': dict(**identity, **observation, incident={k:v for k,v in report.items() if k!='observedAt'}),
        'IncidentReport': dict(**identity, **report),
        'InspectionCorrect': dict(inspectionVersion=0, incidentVersion=1, reason='SIMULATED correction', **observation),
        'InspectionVoid': dict(inspectionVersion=1, incidentVersion=1, reason='SIMULATED mistaken inspection'),
        'IncidentEdit': dict(expectedVersion=0, inspectionVersion=0, reason='SIMULATED correction', **report),
        'IncidentAction': dict(expectedVersion=0, inspectionVersion=0, reason='SIMULATED manager action'),
        'IncidentResolve': dict(expectedVersion=0, inspectionVersion=0, reason='SIMULATED closure',
            resolvedAt='2026-10-31T12:00:00Z', resolutionNote='SIMULATED resolution evidence')}
    negatives = []
    for field, value in [('aggregateId', uid(999)), ('aggregateVersion', 8), ('estateId', uid(999)),
                         ('blockId', uid(999)), ('dataProvenance', 'REAL'), ('source', 'operations-service')]:
        bad = copy.deepcopy(events[NAMES[2]]); bad[field] = value
        negatives.append({'case': 'invalid-' + field, 'event': bad})
    for field in ['summary', 'details', 'findings', 'reason', 'recordedBy', 'resolutionNote']:
        bad = copy.deepcopy(events[NAMES[2]]); bad['payload']['snapshot'][field] = 'SIMULATED forbidden text'
        negatives.append({'case': 'private-' + field, 'event': bad})
    bad = copy.deepcopy(events[NAMES[3]]); bad['payload']['previousVersion'] = 9
    negatives.append({'case': 'nonadjacent-version', 'event': bad})
    bad = copy.deepcopy(events[NAMES[3]]); bad['payload']['changeKind'] = 'TRIAGE'
    negatives.append({'case': 'triage-voided', 'event': bad})
    return events, requests, negatives


def artifacts():
    events, requests, negatives = examples()
    folder = CANDIDATE / 'examples/operations/crop-health/v1'
    output = {CANDIDATE / 'openapi/operations-service.yaml': api_candidate(), folder/'requests.json': requests, folder/'negative.json': negatives}
    for name in NAMES:
        output[CANDIDATE/'events/operations/crop-health/v1'/(name+'.schema.json')] = event_schema(name)
        output[folder/(name+'.json')] = events[name]
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--check', action='store_true'); args = parser.parse_args()
    for path, value in artifacts().items():
        encoded = json.dumps(value, indent=2, ensure_ascii=False) + '\n'
        if args.check: assert path.read_text(encoding='utf-8') == encoded, 'Candidate drift: ' + str(path)
        else:
            path.parent.mkdir(parents=True, exist_ok=True); path.write_text(encoded, encoding='utf-8', newline='\n')
    print('PASS: eleven isolated II-1 artifacts; no release or pins changed')


if __name__ == '__main__': main()
