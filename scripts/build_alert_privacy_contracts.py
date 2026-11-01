"""Isolated AN privacy candidate authoring; never writes released contracts or pins."""
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'docs/alerts-privacy/previous-0.8.0/openapi/operations-service.yaml'
HOME = ROOT / 'docs/alerts-privacy'
CANDIDATE = HOME / 'candidate'
POLICY = 'AN_PRIVACY_PROVISIONAL_1'
UUID7 = {'type': 'string', 'format': 'uuid', 'pattern': '^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'}

def dump(value): return (json.dumps(value, indent=2, ensure_ascii=False) + '\n').encode('utf-8')
def sha(raw): return hashlib.sha256(raw).hexdigest()
def load(path): return json.loads(path.read_text(encoding='utf-8'))
def nullable(value): return {'anyOf': [copy.deepcopy(value), {'type': 'null'}]}
def ref(name): return {'$ref': '#/components/schemas/' + name}

def artifacts():
    api = load(BASE)
    schemas = api['components']['schemas']
    timestamp = schemas['ANAlertView']['properties']['updatedAt']
    view = copy.deepcopy(schemas['ANAlertView'])
    view['properties'].update({
        'policyVersion': {'type': 'string', 'const': POLICY},
        'readState': {'type': 'string', 'enum': ['UNREAD', 'READ', 'EXPIRED']},
        'readExpiresAt': nullable(timestamp),
        'acknowledgementState': {'type': 'string', 'enum': ['NONE', 'RETAINED', 'REDACTED']}})
    view['required'] = list(view['properties'])
    schemas['ANPAlertView'] = view
    page = copy.deepcopy(schemas['ANAlertPage'])
    page['properties']['content']['items'] = ref('ANPAlertView')
    schemas['ANPAlertPage'] = page
    history = copy.deepcopy(schemas['ANHistoryPage'])
    history['properties'].update({
        'retentionState': {'type': 'string', 'enum': ['COMPLETE', 'PARTIAL', 'EXPIRED']},
        'lastExpiredAt': nullable(timestamp)})
    history['required'] = list(history['properties'])
    schemas['ANPHistoryPage'] = history
    problem = {'type': 'object', 'additionalProperties': False,
        'properties': {'type': {'type': 'string', 'format': 'uri'}, 'title': {'type': 'string'},
            'status': {'type': 'integer', 'const': 410}, 'code': {'type': 'string', 'enum': [
                'ALERT_API_RETIRED', 'ALERT_COMMAND_EXPIRED', 'ALERT_READ_RETENTION_EXPIRED']},
            'policyVersion': {'type': 'string', 'const': POLICY}},
        'required': ['type', 'title', 'status', 'code', 'policyVersion']}
    schemas['ANPExpiredProblem'] = problem
    legacy = [(path, copy.deepcopy(ops)) for path, ops in api['paths'].items() if path.startswith('/api/v1/alerts')]
    for path, ops in legacy:
        method = 'post' if 'post' in ops else 'get'
        op = ops[method]
        expiry = {'description': 'Authorized request rejected without an effect or stored success; see closed code.',
            'headers': copy.deepcopy(op['responses']['200']['headers']),
            'content': {'application/problem+json': {'schema': ref('ANPExpiredProblem')}}}
        api['paths'][path][method]['deprecated'] = True
        api['paths'][path][method]['x-privacy-mode'] = '410 ALERT_API_RETIRED when privacy mode enabled; legacy generated-only mode remains isolated'
        api['paths'][path][method]['responses']['410'] = dict(copy.deepcopy(expiry), description='Privacy mode retires v1 alert access; no v1 fallback')
        op['operationId'] += 'PrivacyV2'
        op['description'] = ('AN privacy v2 candidate. Positive role/estate matrix and SIMULATED/generated-only gate retained. '
            'Privacy storage only; never fall back to v1. Logical expiry uses one server UTC decision time. '
            'All current authorization/scope checks precede receipt replay. No client-supplied identities. '
            'UUIDv7 key time is an admission bound, not a trusted completion time. New key must be within '
            'five minutes of server time; known live key/body replays exact success only before its deadline. '
            'Key time plus 30 days is an absolute upper bound; first completion plus 30 days and any personal '
            'copy expiry can shorten it. Expired/absent-old keys return 410, never execute again. '
            'Unknown recent keys outside the five-minute admission window return 409; never treat them as new. '
            'Inactive read retention expiry returns 410; GET expiry does not mark read. '
            'History expiration is explicit and cannot be undone by reopening. No external delivery, offline queue or new event. '
            'Normative candidate behavior is in semantics.json and Architecture privacy extension review.')
        op['responses']['410'] = expiry
        for param in op.get('parameters', []):
            if param['name'] == 'Idempotency-Key': param['schema'] = copy.deepcopy(UUID7)
        schema = op['responses']['200']['content']['application/json']['schema']
        replacements = {'ANAlertView':'ANPAlertView', 'ANAlertPage':'ANPAlertPage', 'ANHistoryPage':'ANPHistoryPage'}
        old = schema.get('$ref', '').split('/')[-1]
        if old in replacements: schema['$ref'] = ref(replacements[old])['$ref']
        api['paths'][path.replace('/api/v1/alerts', '/api/v2/alerts', 1)] = ops
    api['x-alert-privacy-candidate'] = {'releaseProposal':'0.9.0', 'status':'UNRELEASED', 'policyVersion':POLICY,
        'breakingChanges':['privacy-mode v1 retirement','UUIDv7 command admission/expiry','expired read state','history retention/redacted acknowledgement state']}
    old_examples = load(ROOT / 'docs/alerts-notifications/candidate/examples/responses.json')
    base_view = copy.deepcopy(old_examples['unread']['value'])
    base_view.update(policyVersion=POLICY, readState='UNREAD', readExpiresAt=None, acknowledgementState='NONE')
    responses = {'activeUnread': {'schema':'ANPAlertView', 'value':base_view}}
    read = dict(base_view, readState='READ', readAttentionVersion=base_view['attentionVersion'], readAt=base_view['updatedAt'], unreadForMe=False)
    responses['activeRead'] = {'schema':'ANPAlertView', 'value':read}
    expired = dict(base_view, state='INACTIVE', incidentStatus='RESOLVED', inactiveReason='RESOLVED',
        readState='EXPIRED', readExpiresAt='2026-11-30T12:00:00Z', unreadForMe=False)
    responses['expiredRead'] = {'schema':'ANPAlertView', 'value':expired}
    redacted = dict(expired, acknowledged=True, acknowledgementState='REDACTED', acknowledgedAt=None)
    responses['redactedAcknowledgement'] = {'schema':'ANPAlertView', 'value':redacted}
    responses['expiredHistory'] = {'schema':'ANPHistoryPage', 'value':{
        'content':[], 'page':0, 'size':20, 'totalElements':0,
        'generatedAt':'2027-10-31T12:00:00Z', 'retentionState':'EXPIRED', 'lastExpiredAt':'2027-10-31T12:00:00Z'}}
    for code in problem['properties']['code']['enum']:
        responses[code] = {'schema':'ANPExpiredProblem', 'value':{'type':'urn:agrosphere:alerts:privacy-expired',
            'title':'Alert request expired', 'status':410, 'code':code, 'policyVersion':POLICY}}
    requests = load(ROOT / 'docs/alerts-notifications/candidate/examples/requests.json')
    negative = [
        {'schema':'ANPAlertView', 'value':dict(base_view, readState='EXPIRED'), 'reason':'Active cannot have expired read'},
        {'schema':'ANPAlertView', 'value':dict(expired, unreadForMe=True), 'reason':'Expired read not an unread action'},
        {'schema':'ANPAlertView', 'value':dict(redacted, acknowledged=False), 'reason':'Redaction preserves acknowledgement'},
        {'schema':'ANPAlertView', 'value':dict(base_view, acknowledgedBy={'subject':'generated'}), 'reason':'Ordinary actor leak'},
        {'schema':'ANPHistoryPage', 'value':dict(responses['expiredHistory']['value'], totalElements=1), 'reason':'Expired page empty'},
        {'schema':'ANPExpiredProblem', 'value':dict(responses['ALERT_COMMAND_EXPIRED']['value'], status=200), 'reason':'Expiry not success'}]
    semantics = {'policyVersion':POLICY, 'releaseProposal':'0.9.0', 'keyVersion':7,
        'newKeyClockSkewSeconds':300, 'receiptMaximumSeconds':2592000,
        'personalReadInactiveSeconds':2592000, 'ackAuditInactiveSeconds':31536000,
        'applicationLogSeconds':1209600, 'securityLogSeconds':7776000, 'backupMaximumSeconds':3024000,
        'livePhysicalCleanupMaximumDelaySeconds':86400, 'expiryBoundary':'now >= deadline',
        'retryDeadline':'min(key timestamp + 30d, original completion + 30d, applicable personal-copy deadline)',
        'newKeyAdmission':'abs(key timestamp - server time) <= 300s; malformed/future-outside-window=400, absent old within30d=409, expired=410',
        'permissionBeforeReplay':True, 'legacyFallback':False, 'offlineCommands':False,
        'removalKeyCutoff':'verified request time + 300 seconds; deny new personal-copy commands while pending; reject keys at/before cutoff after reinstatement',
        'legacyEnablementPrecondition':'all five V6 alert tables empty; nonempty requires separate reviewed data migration',
        'restoreAccessPrecondition':'deadline enforcement, eligible cleanup and deletion-request reconciliation before access'}
    return {'openapi/operations-service.yaml':dump(api), 'examples/requests.json':dump(requests),
        'examples/responses.json':dump(responses), 'examples/negative.json':dump(negative), 'semantics.json':dump(semantics)}

def build():
    for relative, raw in artifacts().items():
        p=CANDIDATE/relative; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(raw)
    manifest={'status':'UNRELEASED', 'releaseProposal':'0.9.0', 'policyVersion':POLICY,
        'baselineApiSha256':sha(BASE.read_bytes()), 'baselineVersionSha256':sha((HOME/'previous-0.8.0/VERSION').read_bytes()),
        'artifacts':{name:sha(raw) for name,raw in artifacts().items()}}
    (HOME/'CANDIDATE_MANIFEST.json').write_bytes(dump(manifest))
    print('Prepared five isolated privacy artifacts; released files and VERSION unchanged.')

if __name__ == '__main__': build()
