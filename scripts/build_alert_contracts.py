"""Build isolated AN-1 review artifacts; never promote, release or pin them."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'docs/alerts-notifications'
CANDIDATE = BASE / 'candidate'
APPROVED = '22d8c98ede00c4e912f98922f944417aca54bc585a48efe7beb74f59d1364251'
UUID = {'type': 'string', 'format': 'uuid'}
NAT = {'type': 'integer', 'format': 'int64', 'minimum': 0, 'maximum': 9223372036854775807}
VERSION = dict(NAT, minimum=1)
UTC = {'type': 'string', 'format': 'date-time', 'pattern': r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$'}
RULE = 'CROP_HEALTH_HIGH_V1'


def obj(properties):
    return {'type': 'object', 'additionalProperties': False, 'properties': properties, 'required': list(properties)}


def enum(values): return {'type': 'string', 'enum': values}
def nullable(schema): return {'anyOf': [schema, {'type': 'null'}]}
def ref(name): return {'$ref': '#/components/schemas/AN' + name}
def param(name, schema, required=False, where='query'):
    return {'name': name, 'in': where, 'required': required, 'schema': schema}


def page(item):
    return obj({'content': {'type': 'array', 'maxItems': 100, 'items': item},
        'page': {'type': 'integer', 'minimum': 0, 'maximum': 10000},
        'size': {'type': 'integer', 'minimum': 1, 'maximum': 100},
        'totalElements': NAT, 'generatedAt': UTC})


def definitions():
    opaque = {'type': 'string', 'minLength': 1, 'maxLength': 200,
              'pattern': r'\S', 'description': 'Opaque signed subject; never trim, case-fold or remap.'}
    view = obj({'id': UUID, 'incidentId': UUID, 'estateId': UUID, 'blockId': UUID,
        'ruleVersion': {'type': 'string', 'const': RULE}, 'sourceVersion': NAT,
        'alertVersion': VERSION, 'attentionVersion': VERSION,
        'state': enum(['ACTIVE', 'INACTIVE']),
        'inactiveReason': nullable(enum(['RESOLVED', 'VOIDED', 'BELOW_THRESHOLD'])),
        'category': enum(['PEST_SIGNS', 'DISEASE_SIGNS', 'TREE_DAMAGE', 'OTHER_CROP_HEALTH']),
        'severity': enum(['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']),
        'incidentStatus': enum(['OPEN', 'IN_REVIEW', 'RESOLVED', 'VOIDED']),
        'dataProvenance': {'type': 'string', 'const': 'SIMULATED'},
        'estateTimezone': {'type': 'string', 'minLength': 1, 'maxLength': 100},
        'observedAt': UTC, 'raisedAt': UTC, 'attentionAt': UTC, 'updatedAt': UTC,
        'readAttentionVersion': NAT, 'readAt': nullable(UTC), 'unreadForMe': {'type': 'boolean'},
        'acknowledged': {'type': 'boolean'}, 'acknowledgedAt': nullable(UTC)})
    history = obj({'alertId': UUID, 'alertVersion': VERSION, 'sourceVersion': NAT,
        'attentionVersion': VERSION, 'ruleVersion': {'type': 'string', 'const': RULE},
        'kind': enum(['RAISED', 'SOURCE_UPDATED', 'DEACTIVATED', 'REACTIVATED', 'ESCALATED', 'ACKNOWLEDGED']),
        'beforeState': nullable(enum(['ACTIVE', 'INACTIVE'])), 'afterState': enum(['ACTIVE', 'INACTIVE']),
        'recordedAt': UTC, 'correlationId': UUID,
        'acknowledgedBy': nullable(obj({'issuer': {'type': 'string', 'format': 'uri', 'maxLength': 2048}, 'subject': opaque}))})
    return {'ANRead': obj({'attentionVersion': VERSION}),
        'ANAcknowledge': obj({'expectedAlertVersion': VERSION, 'attentionVersion': VERSION}),
        'ANAlertView': view, 'ANAlertPage': page(ref('AlertView')),
        'ANCounts': obj({'activeTotal': NAT, 'activeUnreadForMe': NAT, 'activeUnacknowledged': NAT, 'generatedAt': UTC}),
        'ANHistoryEntry': history, 'ANHistoryPage': page(ref('HistoryEntry'))}


OPERATIONS = [
    ('get', '', 'listCropHealthAlerts', None, 'AlertPage', 'READ'),
    ('get', '/counts', 'countCropHealthAlerts', None, 'Counts', 'READ'),
    ('get', '/{alertId}', 'getCropHealthAlert', None, 'AlertView', 'READ'),
    ('post', '/{alertId}/read', 'readCropHealthAlert', 'Read', 'AlertView', 'READ'),
    ('post', '/{alertId}/acknowledgements', 'acknowledgeCropHealthAlert', 'Acknowledge', 'AlertView', 'MANAGER'),
    ('get', '/{alertId}/history', 'getCropHealthAlertHistory', None, 'HistoryPage', 'HISTORY')]

POLICY = ('Independently validated issuer/audience/sub/roles/trusted estate_ids. PLATFORM_ADMIN with explicit estate selection; '
    'estate-scoped ESTATE_ADMIN/ESTATE_MANAGER read/manage/history; FIELD_SUPERVISOR read and own-read only; AUDITOR read/own-read/history. '
    'Other roles alone grant nothing. Scope before queries/counts/history/replay; explicit denied estate 403, missing/foreign object 404 after feature-role check. '
    'Ordinary responses omit source report text, ack actor and other users read markers. SIMULATED only; generated-only development until AN-D07 policy implemented. '
    'No implicit read on GET; no external/targeted delivery or absent-user guarantee. No historical backfill. '
    'Rule CROP_HEALTH_HIGH_V1: SIMULATED + OPEN/IN_REVIEW + HIGH/CRITICAL; qualification/requalification or HIGH-to-CRITICAL starts new attention. '
    'Same-severity edits/triage and CRITICAL-to-HIGH retain attention. Local source transaction owns source revision/outbox/receipt and rule state; broker delivery is independent. ')
COMMAND = ('UUID Idempotency-Key scoped to trusted issuer/opaque signed subject and alert feature. Normalize method/path/closed integer body with canonical UUID; '
    'preserve opaque identity, canonical JSON integers. Identical retry replays original 200 response after current permission/scope validation; different path/body conflicts 409. '
    'Lock alert before alert-specific rows; no source lock acquired afterward. Failed command saves no success receipt. Retry unknown outcome with identical frozen key/body. ')


def api_candidate():
    source = BASE/'previous-0.7.0/openapi/operations-service.yaml'
    if not source.exists(): source = ROOT/'openapi/operations-service.yaml'
    api = json.loads(source.read_text(encoding='utf-8'))
    assert not any(p.startswith('/api/v1/alerts') for p in api['paths']), 'Released baseline changed; explicit release transition required'
    api['components']['schemas'].update(definitions())
    for method, suffix, name, request, response, permission in OPERATIONS:
        params = [param('alertId', UUID, True, 'path')] if '{alertId}' in suffix else []
        if suffix in ['', '/counts']: params.append(param('estateId', UUID, True))
        if response.endswith('Page'):
            params += [param('page', {'type': 'integer', 'minimum': 0, 'maximum': 10000, 'default': 0}),
                       param('size', {'type': 'integer', 'minimum': 1, 'maximum': 100, 'default': 20})]
        if suffix == '':
            params += [param('state', dict(enum(['ACTIVE', 'INACTIVE']), default='ACTIVE')),
                param('unreadOnly', {'type': 'boolean', 'default': False}),
                param('unacknowledgedOnly', {'type': 'boolean', 'default': False}),
                param('severity', enum(['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'])), param('blockId', UUID)]
        if request: params.append(param('Idempotency-Key', UUID, True, 'header'))
        headers = {'Cache-Control': {'schema': {'type': 'string', 'const': 'no-store'}}, 'X-Correlation-ID': {'schema': UUID}}
        responses = {'200': {'description': 'Original authorized success' if request else 'Authorized query; no read side effect',
            'headers': headers, 'content': {'application/json': {'schema': ref(response)}}}}
        for code, desc in [('400', 'Malformed/unknown fields/filter/UUID/version/page or page*size > 10000'),
            ('401', 'Invalid/missing JWT'), ('403', 'Feature/estate/provenance denied'), ('404', 'Missing or inaccessible alert'),
            ('409', 'Stale alert/attention, inactive ack, already acknowledged or conflicting key; bounded lock timeout retryable'),
            ('429', 'Rate limited; respect Retry-After'), ('503', 'Dependency unavailable')]:
            responses[code] = {'description': desc, 'headers': copy.deepcopy(headers),
                'content': {'application/problem+json': {'schema': {'$ref': '#/components/schemas/ProblemDetail'}}}}
        responses['429']['headers']['Retry-After'] = {'schema': {'type': 'string'}, 'description': 'Delay before retry'}
        desc = POLICY + (COMMAND if request else '')
        if request == 'Read': desc += ('attentionVersion must equal current; update only caller monotonic marker. '
            'Already read with a fresh key succeeds without duplicate effect. Does not change shared alertVersion or acknowledge. Inactive alerts may be read.')
        if request == 'Acknowledge': desc += ('ACTIVE manager only; both displayed versions must match; first acknowledgement for attention only. '
            'Atomically increment alertVersion, shared acknowledgement/evidence, own-read and receipt. Source lifecycle unchanged. '
            'A different manager/key after first acknowledgement conflicts, even at latest alertVersion.')
        op = {'operationId': name, 'tags': ['crop-health-alerts'], 'security': [{'bearerAuth': []}],
            'description': desc, 'parameters': params, 'responses': responses, 'x-alert-permission': permission,
            'x-query-constraints': {'unknownFilters': 'reject', 'maximumOffset': 10000,
                'sort': 'alertVersion DESC' if suffix.endswith('/history') else 'attentionAt DESC,id DESC',
                'counts': 'one scoped consistent snapshot'}}
        if request: op['requestBody'] = {'required': True, 'content': {'application/json': {'schema': ref(request)}}}
        api['paths']['/api/v1/alerts' + suffix] = {method: op}
    return api


def examples():
    at = '2026-10-31T12:00:00Z'; uid = lambda i: f'00000000-0000-0000-0000-{i:012d}'
    alert = dict(id=uid(1), incidentId=uid(2), estateId=uid(3), blockId=uid(4), ruleVersion=RULE,
        sourceVersion=0, alertVersion=1, attentionVersion=1, state='ACTIVE', inactiveReason=None,
        category='TREE_DAMAGE', severity='HIGH', incidentStatus='OPEN', dataProvenance='SIMULATED',
        estateTimezone='Etc/UTC', observedAt='2026-10-31T11:00:00Z', raisedAt=at, attentionAt=at,
        updatedAt=at, readAttentionVersion=0, readAt=None, unreadForMe=True, acknowledged=False, acknowledgedAt=None)
    read = dict(alert, readAttentionVersion=1, readAt=at, unreadForMe=False)
    ack = dict(read, alertVersion=2, acknowledged=True, acknowledgedAt=at)
    inactive = dict(ack, alertVersion=3, sourceVersion=1, state='INACTIVE', inactiveReason='RESOLVED', incidentStatus='RESOLVED')
    entry = dict(alertId=uid(1), alertVersion=1, sourceVersion=0, attentionVersion=1, ruleVersion=RULE,
        kind='RAISED', beforeState=None, afterState='ACTIVE', recordedAt=at, correlationId=uid(5), acknowledgedBy=None)
    ack_entry = dict(entry, alertVersion=2, kind='ACKNOWLEDGED', beforeState='ACTIVE',
        acknowledgedBy={'issuer': 'https://identity.example.invalid/realms/generated', 'subject': 'generated-manager'})
    page_args = dict(page=0, size=20, totalElements=1, generatedAt=at)
    responses = {'unread': {'schema': 'AlertView', 'value': alert}, 'read': {'schema': 'AlertView', 'value': read},
        'acknowledged': {'schema': 'AlertView', 'value': ack}, 'inactive': {'schema': 'AlertView', 'value': inactive},
        'page': {'schema': 'AlertPage', 'value': dict(content=[alert], **page_args)},
        'counts': {'schema': 'Counts', 'value': dict(activeTotal=1, activeUnreadForMe=1, activeUnacknowledged=1, generatedAt=at)},
        'raised-history': {'schema': 'HistoryEntry', 'value': entry}, 'ack-history': {'schema': 'HistoryEntry', 'value': ack_entry},
        'history-page': {'schema': 'HistoryPage', 'value': dict(content=[ack_entry, entry], **dict(page_args, totalElements=2))}}
    requests = {'Read': {'attentionVersion': 1}, 'Acknowledge': {'expectedAlertVersion': 1, 'attentionVersion': 1}}
    negatives = []
    for case, shape, body in [('read-zero', 'Read', {'attentionVersion': 0}), ('read-null','Read',{'attentionVersion': None}),
        ('ack-missing-version','Acknowledge',{'attentionVersion': 1}),
        ('ack-fraction','Acknowledge',{'expectedAlertVersion': 1.5, 'attentionVersion': 1})]:
        negatives.append({'case': case, 'schema': shape, 'value': body})
    for field in ['subject','recipientId','dataProvenance','reason']:
        negatives.append({'case':'forbidden-'+field, 'schema':'Read', 'value':dict(requests['Read'], **{field:'forbidden'})})
    for case, changes in [('real',{'dataProvenance':'REAL'}),('private-text',{'summary':'forbidden'}),
        ('actor-leak',{'acknowledgedBy':'forbidden'}),('false-unread',{'unreadForMe':False}),
        ('future-read',{'readAttentionVersion':2}),('ack-without-time',{'acknowledged':True}),
        ('active-low',{'severity':'LOW'}),('active-resolved',{'incidentStatus':'RESOLVED'}),
        ('active-reason',{'inactiveReason':'RESOLVED'}),('future-observation',{'observedAt':'2026-11-01T00:00:00Z'}),
        ('excess-time-precision',{'updatedAt':'2026-10-31T12:00:00.1234567Z'})]:
        negatives.append({'case':case,'schema':'AlertView','value':dict(alert,**changes)})
    negatives.append({'case':'impossible-counts','schema':'Counts','value':dict(responses['counts']['value'],activeTotal=0)})
    return requests, responses, negatives


def artifacts():
    requests, responses, negatives = examples()
    return {CANDIDATE/'openapi/operations-service.yaml': api_candidate(),
        CANDIDATE/'examples/requests.json': requests, CANDIDATE/'examples/responses.json': responses,
        CANDIDATE/'examples/negative.json': negatives}


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--check', action='store_true'); args = parser.parse_args()
    output = {p: (json.dumps(v, indent=2, ensure_ascii=False)+'\n').encode('utf-8') for p,v in artifacts().items()}
    manifest = {'status':'UNRELEASED_REVIEW_CANDIDATE','baseRelease':'0.7.0','approvedDesignSha256':APPROVED,
        'files':{p.relative_to(ROOT).as_posix():hashlib.sha256(data).hexdigest() for p,data in output.items()}}
    output[BASE/'CANDIDATE_MANIFEST.json'] = (json.dumps(manifest,indent=2)+'\n').encode()
    for path, data in output.items():
        if args.check: assert path.read_bytes()==data, 'Candidate drift: '+str(path)
        else: path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(data)
    print('PASS: four isolated AN-1 artifacts + manifest; released VERSION/API/events/pins unchanged')


if __name__ == '__main__': main()
