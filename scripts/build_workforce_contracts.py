"""Build isolated WA-1 executable candidates; never promote/release/pin artifacts."""
import argparse
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / 'docs/worker-attendance/candidate'
TIMESTAMP = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.[0-9]{1,6}0*)?Z$'
UUID = {'type': 'string', 'format': 'uuid'}
DATE = {'type': 'string', 'format': 'date'}
VERSION = {'type': 'integer', 'format': 'int64', 'minimum': 0, 'maximum': 9223372036854775807}
INSTANT = {'type': 'string', 'format': 'date-time', 'pattern': TIMESTAMP}
PROVENANCE = {'type': 'string', 'enum': ['REAL', 'SIMULATED']}
STATUS = {'type': 'string', 'enum': ['PRESENT', 'ABSENT', 'EXCUSED']}
NAMES = ['WorkerRegistrationCreated', 'WorkerRegistrationChanged',
         'WorkerAttendanceRecorded', 'WorkerAttendanceChanged']


def obj(properties, required=None, **extra):
    return dict(type='object', additionalProperties=False, properties=properties,
                required=list(properties) if required is None else required, **extra)


def nullable(schema):
    return {'anyOf': [schema, {'type': 'null'}]}


def text(limit=200):
    return dict(type='string', minLength=1, maxLength=limit, pattern=r'\S')


def reason():
    return dict(type='string', minLength=1, maxLength=1000,
                pattern=r'^[^\u0000-\u001F\u007F-\u009F]*\S[^\u0000-\u001F\u007F-\u009F]*$',
                description='Trim before validation/hash; nonblank, no control characters. Do not enter health or other sensitive personal details.')


def ref(name):
    return {'$ref': '#/components/schemas/' + name}


def definitions():
    code = dict(type='string', pattern=r'^[A-Z0-9][A-Z0-9_-]{0,63}$')
    period = obj({'id': UUID, 'activeFrom': DATE, 'activeTo': nullable(DATE),
                  'introducedVersion': VERSION, 'closedVersion': nullable(VERSION)})
    worker = obj({'id': UUID, 'estateId': UUID, 'workerCode': code, 'displayName': text(),
                  'divisionId': nullable(UUID), 'dataProvenance': PROVENANCE,
                  'activePeriods': dict(type='array', minItems=1, items=ref('WorkforceActivePeriod')),
                  'version': VERSION, 'createdAt': INSTANT, 'updatedAt': INSTANT})
    attendance = obj({'id': UUID, 'estateId': UUID, 'workerRegistrationId': UUID,
                      'attendanceDate': DATE, 'estateTimezone': text(100), 'workerCodeSnapshot': code,
                      'divisionIdSnapshot': nullable(UUID), 'workerVersionSnapshot': VERSION,
                      'activePeriodId': UUID, 'dataProvenance': PROVENANCE,
                      'status': dict(STATUS, enum=STATUS['enum'] + ['VOIDED']),
                      'version': VERSION, 'createdAt': INSTANT, 'updatedAt': INSTANT})
    schemas = {
        'WorkforceActivePeriod': period, 'WorkerView': worker, 'AttendanceView': attendance,
        'WorkerRegister': obj({'estateId': UUID,
            'workerCode': dict(type='string', pattern=r'^ *[A-Za-z0-9][A-Za-z0-9_-]{0,63} *$',
                               description='Trim and uppercase ASCII before uniqueness and command hashing.'),
            'displayName': text(), 'activeFrom': DATE, 'dataProvenance': PROVENANCE,
            'divisionId': nullable(UUID)},
            ['estateId', 'workerCode', 'displayName', 'activeFrom', 'dataProvenance']),
        'WorkerUpdate': obj({'version': VERSION, 'reason': reason(),
            'displayName': text(), 'divisionId': nullable(UUID)}, ['version', 'reason'],
            anyOf=[{'required': ['displayName']}, {'required': ['divisionId']}]),
        'WorkerClosePeriod': obj({'version': VERSION, 'activePeriodId': UUID, 'activeTo': DATE, 'reason': reason()}),
        'WorkerOpenPeriod': obj({'version': VERSION, 'activeFrom': DATE, 'reason': reason()}),
        'AttendanceRecord': obj({'workerRegistrationId': UUID, 'attendanceDate': DATE,
            'status': STATUS, 'backdateReason': reason()}, ['workerRegistrationId', 'attendanceDate', 'status']),
        'AttendanceChange': obj({'version': VERSION, 'status': STATUS, 'reason': reason()}),
        'AttendanceVoid': obj({'version': VERSION, 'reason': reason()}),
        'WorkerRosterItem': obj({'id': UUID, 'code': code, 'displayName': text(),
            'divisionId': nullable(UUID), 'provenance': PROVENANCE, 'version': VERSION})}
    for prefix, view, commands in [
        ('Worker', 'WorkerView', ['REGISTER', 'PROFILE', 'PERIOD_CLOSED', 'PERIOD_OPENED']),
        ('Attendance', 'AttendanceView', ['RECORD', 'CORRECT', 'VOID', 'RERECORD'])]:
        schemas[prefix + 'HistoryEntry'] = obj({'id': UUID, 'version': VERSION,
            'commandKind': dict(type='string', enum=commands), 'reason': nullable(reason()),
            'recordedAt': INSTANT, 'recordedBy': text(), 'correlationId': UUID, 'snapshot': ref(view)})
        for suffix, item in [('Page', view), ('HistoryPage', prefix + 'HistoryEntry')]:
            schemas[prefix + suffix] = page(ref(item))
    roster = page(obj({'worker': ref('WorkerRosterItem'), 'attendance': nullable(ref('AttendanceView'))}))
    roster['properties'].update({'estateId': UUID, 'date': DATE, 'estateTimezone': text(100),
        'dataProvenance': PROVENANCE, **{k: VERSION for k in [
            'eligibleCount', 'markedCount', 'unmarkedCount', 'voidedCount', 'outsideRosterRecordedCount']}})
    roster['required'] = list(roster['properties'])
    schemas['AttendanceRosterPage'] = roster
    return schemas


def page(item):
    return obj({'content': {'type': 'array', 'items': item}, 'page': dict(type='integer', minimum=0),
                'size': dict(type='integer', minimum=1, maximum=100), 'totalElements': VERSION})


def parameter(name, schema, required=False, where='query'):
    return dict(name=name, **{'in': where}, required=required, schema=schema)


OPERATIONS = [
    ('post', '/workers', 'registerWorker', 'WorkerRegister', 'WorkerView', 'MANAGER'),
    ('get', '/workers', 'listWorkers', None, 'WorkerPage', 'READ'),
    ('get', '/workers/{id}', 'getWorker', None, 'WorkerView', 'READ'),
    ('patch', '/workers/{id}', 'updateWorker', 'WorkerUpdate', 'WorkerView', 'MANAGER'),
    ('post', '/workers/{id}/close-period', 'closeWorkerPeriod', 'WorkerClosePeriod', 'WorkerView', 'MANAGER'),
    ('post', '/workers/{id}/open-period', 'openWorkerPeriod', 'WorkerOpenPeriod', 'WorkerView', 'MANAGER'),
    ('get', '/workers/{id}/history', 'getWorkerHistory', None, 'WorkerHistoryPage', 'HISTORY'),
    ('get', '/attendance/roster', 'getAttendanceRoster', None, 'AttendanceRosterPage', 'READ'),
    ('post', '/attendance/days', 'recordAttendanceDay', 'AttendanceRecord', 'AttendanceView', 'RECORD'),
    ('get', '/attendance/days', 'listAttendanceDays', None, 'AttendancePage', 'READ'),
    ('get', '/attendance/days/{id}', 'getAttendanceDay', None, 'AttendanceView', 'READ'),
    ('post', '/attendance/days/{id}/corrections', 'correctAttendanceDay', 'AttendanceChange', 'AttendanceView', 'MANAGER'),
    ('post', '/attendance/days/{id}/void', 'voidAttendanceDay', 'AttendanceVoid', 'AttendanceView', 'MANAGER'),
    ('post', '/attendance/days/{id}/re-record', 'rerecordAttendanceDay', 'AttendanceChange', 'AttendanceView', 'MANAGER'),
    ('get', '/attendance/days/{id}/history', 'getAttendanceHistory', None, 'AttendanceHistoryPage', 'HISTORY')]


def api_candidate():
    api = json.loads((ROOT / 'openapi/operations-service.yaml').read_text())
    api['components']['schemas'].update(definitions())
    pages = [parameter('page', dict(type='integer', minimum=0, default=0)),
             parameter('size', dict(type='integer', minimum=1, maximum=100, default=20))]
    for method, suffix, name, request, response, permission in OPERATIONS:
        params = [parameter('id', UUID, True, 'path')] if '{id}' in suffix else []
        if response.endswith('Page'):
            params += copy.deepcopy(pages)
        if name in ['listWorkers', 'getAttendanceRoster', 'listAttendanceDays']:
            params.append(parameter('estateId', UUID, True))
            params.append(parameter('provenance', PROVENANCE, name == 'getAttendanceRoster'))
        if name == 'listWorkers':
            params += [parameter('activeOn', DATE), parameter('code', dict(type='string', pattern=r'^[A-Z0-9][A-Z0-9_-]{0,63}$')),
                       parameter('name', text(100)), parameter('divisionId', UUID)]
        if name == 'getAttendanceRoster':
            params += [parameter('date', DATE, True), parameter('divisionId', UUID)]
        if name == 'listAttendanceDays':
            params += [parameter(k, DATE, True) for k in ['from', 'to']]
            params += [parameter('workerRegistrationId', UUID), parameter('status', dict(STATUS, enum=STATUS['enum'] + ['VOIDED']))]
        if request:
            params.append(parameter('Idempotency-Key', UUID, True, 'header'))
        code = '201' if name in ['registerWorker', 'recordAttendanceDay'] else '200'
        headers = {'X-Correlation-ID': {'schema': UUID}}
        if code == '201':
            headers['Location'] = {'schema': {'type': 'string'}, 'description': '/api/v1' + suffix + '/{id}; retained on replay'}
        responses = {code: {'description': 'Original authorized command receipt' if request else 'Authorized minimal resource/query',
            'headers': headers, 'content': {'application/json': {'schema': ref(response)}}}}
        for status, meaning in [('400', 'Invalid syntax, fields, dates or state'), ('401', 'Invalid authentication'),
            ('403', 'Role/estate/backdate denied'), ('404', 'Authorized local resource not found'),
            ('409', 'Version/uniqueness/period/key conflict or bounded lock timeout'),
            ('422', 'Invalid/inactive/mismatched canonical master reference'),
            ('503', 'Bounded dependency unavailable or malformed')]:
            responses[status] = {'description': meaning, 'content': {'application/problem+json': {'schema': ref('ProblemDetail')}}}
        policies = {
            'READ': 'PLATFORM_ADMIN globally; scoped ESTATE_ADMIN/ESTATE_MANAGER/FIELD_SUPERVISOR/AUDITOR.',
            'MANAGER': 'PLATFORM_ADMIN globally; scoped ESTATE_ADMIN/ESTATE_MANAGER; reason required on noncreate.',
            'HISTORY': 'PLATFORM_ADMIN globally; scoped ESTATE_ADMIN/ESTATE_MANAGER/AUDITOR; includes protected reasons/actors.',
            'RECORD': 'PLATFORM_ADMIN globally; scoped ESTATE_ADMIN/ESTATE_MANAGER; scoped FIELD_SUPERVISOR today only. Past dates require manager and backdateReason.'}
        op = dict(operationId=name, tags=['workforce'], security=[{'bearerAuth': []}], parameters=params, responses=responses,
            description=policies[permission] + ' Signed sub and trusted estate_ids required except explicit platform global access. '
                'PLANTATION_ADMIN alone, VIEWER, FIELD_WORKER and AGRONOMIST denied. Positive operation permissions; '
                'scope before queries/counts/history/replay. Unknown fields/filters rejected. Ordinary views omit actors/reasons. '
                'Writes use durable actor/key normalized receipts; reauthorize before replay. Noncreate version is required; exact replay emits nothing. '
                'REAL workforce collection remains disabled until the separate D09 privacy/retention enablement gate is accepted and verified.',
            **{'x-workforce-permission': permission, 'x-query-constraints': {'unknownFilters': 'reject', 'maximumOffset': 2147483647}})
        if name == 'listAttendanceDays':
            op['x-query-constraints'].update(dateBounds='both-required', maximumDateDifferenceDays=366)
        if request:
            op['requestBody'] = {'required': True, 'content': {'application/json': {'schema': ref(request)}}}
        api['paths'].setdefault('/api/v1' + suffix, {})[method] = op
    return api


def event_schema(name):
    registration = name.startswith('WorkerRegistration')
    created = name.endswith(('Created', 'Recorded'))
    state = {'registrationId' if registration else 'attendanceId': UUID, 'estateId': UUID,
             'dataProvenance': PROVENANCE, 'version': VERSION}
    if registration:
        state.update(divisionId=nullable(UUID), activePeriods=dict(type='array', minItems=1,
            items=obj({'id': UUID, 'activeFrom': DATE, 'activeTo': nullable(DATE)})))
    else:
        state.update(workerRegistrationId=UUID, attendanceDate=DATE, estateTimezone=text(100),
            divisionIdSnapshot=nullable(UUID), activePeriodId=UUID, workerVersionSnapshot=VERSION,
            status=STATUS if created else dict(STATUS, enum=STATUS['enum'] + ['VOIDED']))
    if created:
        state['version'] = dict(VERSION, const=0)
    else:
        state['version'] = dict(VERSION, minimum=1)
    payload = {'snapshot': obj(state)}
    if not created:
        payload.update(previousVersion=VERSION, changeKind={'type': 'string', 'enum':
            ['PROFILE', 'PERIOD_CLOSED', 'PERIOD_OPENED'] if registration else ['CORRECT', 'VOID', 'RERECORD']})
    return obj({'eventId': UUID, 'eventType': dict(type='string', const=name),
        'eventVersion': dict(type='integer', const=1), 'timestamp': INSTANT,
        'source': dict(type='string', const='agrosphere-operations-service'), 'correlationId': UUID,
        'estateId': UUID, 'dataProvenance': PROVENANCE, 'aggregateId': UUID,
        'aggregateVersion': dict(VERSION, const=0) if created else dict(VERSION, minimum=1), 'payload': obj(payload)},
        **{'$schema': 'https://json-schema.org/draft/2020-12/schema',
           '$id': 'https://schemas.agrosphere.invalid/operations/workforce/v1/' + name + '.schema.json', 'title': name})


def examples():
    uid = lambda n: '00000000-0000-0000-0000-' + str(n).zfill(12)
    events = {}
    for i, name in enumerate(NAMES):
        registration = name.startswith('WorkerRegistration')
        created = name.endswith(('Created', 'Recorded'))
        snapshot = {'registrationId' if registration else 'attendanceId': uid(2 if registration else 4),
                    'estateId': uid(1), 'dataProvenance': 'SIMULATED', 'version': 0 if created else 1}
        if registration:
            snapshot.update(divisionId=None, activePeriods=[dict(id=uid(3), activeFrom='2026-10-29', activeTo=None)])
        else:
            snapshot.update(workerRegistrationId=uid(2), attendanceDate='2026-10-29', estateTimezone='Africa/Libreville',
                divisionIdSnapshot=None, activePeriodId=uid(3), workerVersionSnapshot=0, status='PRESENT' if created else 'VOIDED')
        payload = {'snapshot': snapshot}
        if not created:
            payload.update(previousVersion=0, changeKind='PROFILE' if registration else 'VOID')
        events[name] = dict(eventId=uid(100+i), eventType=name, eventVersion=1, timestamp='2026-10-29T12:00:00Z',
            source='agrosphere-operations-service', correlationId=uid(200), estateId=uid(1),
            dataProvenance='SIMULATED', aggregateId=snapshot['registrationId' if registration else 'attendanceId'],
            aggregateVersion=snapshot['version'], payload=payload)
    requests = {
        'WorkerRegister': dict(estateId=uid(1), workerCode=' simulated-01 ', displayName='SIMULATED — Example Worker',
            activeFrom='2026-10-29', dataProvenance='SIMULATED'),
        'WorkerUpdate': dict(version=0, reason='SIMULATED profile correction', displayName='SIMULATED — Revised Example'),
        'WorkerClosePeriod': dict(version=1, activePeriodId=uid(3), activeTo='2026-10-30', reason='SIMULATED registration closure'),
        'WorkerOpenPeriod': dict(version=2, activeFrom='2026-10-30', reason='SIMULATED reactivation'),
        'AttendanceRecord': dict(workerRegistrationId=uid(2), attendanceDate='2026-10-29', status='PRESENT'),
        'AttendanceChange': dict(version=0, status='EXCUSED', reason='SIMULATED roll-call correction'),
        'AttendanceVoid': dict(version=1, reason='SIMULATED mistaken entry')}
    return events, requests


def artifacts():
    output = {CANDIDATE / 'openapi/operations-service.yaml': api_candidate()}
    events, requests = examples()
    for name in NAMES:
        output[CANDIDATE / 'events/operations/workforce/v1' / (name + '.schema.json')] = event_schema(name)
        output[CANDIDATE / 'examples/operations/workforce/v1' / (name + '.json')] = events[name]
    output[CANDIDATE / 'examples/operations/workforce/v1/requests.json'] = requests
    negatives = []
    for field, value in [('aggregateId', '00000000-0000-0000-0000-000000009999'),
                         ('aggregateVersion', 7), ('dataProvenance', 'REAL')]:
        bad = copy.deepcopy(events['WorkerAttendanceRecorded'])
        bad[field] = value
        negatives.append({'case': 'mismatched-' + field, 'event': bad})
    for field in ['displayName', 'workerCode', 'reason', 'recordedBy']:
        bad = copy.deepcopy(events['WorkerRegistrationCreated'])
        bad['payload']['snapshot'][field] = 'SIMULATED forbidden disclosure'
        negatives.append({'case': 'private-field-' + field, 'event': bad})
    bad = copy.deepcopy(events['WorkerAttendanceChanged'])
    bad['payload']['previousVersion'] = 5
    negatives.append({'case': 'nonadjacent-revision', 'event': bad})
    bad = copy.deepcopy(events['WorkerAttendanceChanged'])
    bad['payload']['changeKind'] = 'CORRECT'
    negatives.append({'case': 'correction-cannot-be-voided', 'event': bad})
    output[CANDIDATE / 'examples/operations/workforce/v1/negative.json'] = negatives
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    for path, value in artifacts().items():
        encoded = json.dumps(value, indent=2, ensure_ascii=False).replace('1e-07', '0.0000001') + '\n'
        if args.check:
            assert path.read_text(encoding='utf-8') == encoded, f'Workforce candidate drift: {path}'
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(encoded, encoding='utf-8', newline='\n')
    print('PASS: 11 isolated workforce candidate artifacts; no release/pin/promotion')


if __name__ == '__main__':
    main()
