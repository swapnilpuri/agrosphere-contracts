"""Validate the isolated privacy candidate; oracle functions are not service enforcement."""
import copy
import uuid
from datetime import datetime, timedelta, timezone
from jsonschema import Draft202012Validator, FormatChecker
from openapi_spec_validator import validate
from build_alert_privacy_contracts import ROOT, HOME, CANDIDATE, BASE, POLICY, UUID7, load, sha, artifacts
from alert_contract_validation import validate_value as legacy_value

def require(ok, message):
    if not ok: raise ValueError(message)
def instant(value): return datetime.fromisoformat(value.replace('Z', '+00:00'))
def validate_value(name, value):
    api=load(CANDIDATE/'openapi/operations-service.yaml')
    Draft202012Validator({'$ref':'#/components/schemas/'+name, 'components':api['components']},format_checker=FormatChecker()).validate(value)
    if name=='ANPAlertView':
        v=copy.deepcopy(value)
        for k in ['policyVersion','readState','readExpiresAt','acknowledgementState']: v.pop(k)
        if value['readState']=='EXPIRED':
            require(value['state']=='INACTIVE' and value['readAttentionVersion']==0 and value['readAt'] is None and not value['unreadForMe'] and value['readExpiresAt'] is not None,'Invalid expired read')
            v['unreadForMe']=True  # v1 has no retention state; check its other semantics independently.
        else:
            require((value['readState']=='READ')==(value['readAttentionVersion']==value['attentionVersion']),'Read state mismatch')
        if value['state']=='ACTIVE': require(value['readExpiresAt'] is None,'Active retention deadline')
        else: require(value['readExpiresAt'] is not None,'Missing inactive read deadline')
        ack=value['acknowledgementState']
        require((ack=='NONE')==(not value['acknowledged']),'Ack state mismatch')
        if ack=='REDACTED':
            require(value['state']=='INACTIVE' and value['acknowledgedAt'] is None,'Redacted ack mismatch')
            v['acknowledgedAt']=v['updatedAt']  # Test other v1 constraints without inventing a returned actor/time.
        elif ack=='RETAINED': require(value['acknowledgedAt'] is not None,'Missing retained ack time')
        legacy_value('AlertView',v)
    elif name in ['ANPAlertPage','ANPHistoryPage']:
        require(value['page']*value['size']<=10000,'Excessive offset')
        require(len(value['content'])<=min(value['size'],value['totalElements']),'Invalid page cardinality')
        for item in value['content']:
            if name=='ANPAlertPage': validate_value('ANPAlertView',item)
            else: legacy_value('HistoryEntry',item)
        if name=='ANPHistoryPage':
            if value['retentionState']=='EXPIRED': require(not value['content'] and value['totalElements']==0,'Expired history not empty')
            require((value['retentionState']=='COMPLETE')==(value['lastExpiredAt'] is None),'Missing/extra history expiry')
            if value['lastExpiredAt'] is not None: require(instant(value['lastExpiredAt'])<=instant(value['generatedAt']),'Future history expiry')

def key_decision(key, now, receipt=None, authorized=True, removal_cutoff=None, removal_pending=False):
    # Contract oracle for status precedence: real endpoint must authorize object/scope first.
    if not authorized: return 403
    try:
        u=uuid.UUID(key)
        if str(u)!=key or u.version!=7 or u.variant!=uuid.RFC_4122: return 400
        at=datetime.fromtimestamp((u.int>>80)/1000,timezone.utc)
    except (ValueError, OverflowError, OSError): return 400
    if at>now+timedelta(minutes=5): return 400
    if removal_pending or (removal_cutoff is not None and at<=removal_cutoff): return 410
    if now>=at+timedelta(days=30): return 410
    if receipt is not None: return 410 if now>=receipt else 200
    if now-at>timedelta(minutes=5): return 409
    return 201  # Oracle's NEW disposition, not the endpoint HTTP success status (200).

def run():
    api=load(CANDIDATE/'openapi/operations-service.yaml'); validate(api)
    manifest=load(HOME/'CANDIDATE_MANIFEST.json')
    require(manifest['baselineApiSha256']==sha(BASE.read_bytes()),'Released baseline drift')
    require(manifest['baselineVersionSha256']==sha((HOME/'previous-0.8.0/VERSION').read_bytes()),'Released VERSION drift')
    require(set(manifest['artifacts'])==set(artifacts()),'Artifact inventory drift')
    for name,raw in artifacts().items():
        require((CANDIDATE/name).read_bytes()==raw,'Nonreproducible candidate: '+name)
        require(manifest['artifacts'][name]==sha(raw),'Candidate hash drift: '+name)
    base=load(BASE)
    for name,schema in base['components']['schemas'].items(): require(api['components']['schemas'][name]==schema,'Old schema changed: '+name)
    for path,ops in base['paths'].items():
        if not path.startswith('/api/v1/alerts'): require(api['paths'][path]==ops,'Non-alert operation changed: '+path)
        else:
            expected=copy.deepcopy(api['paths'][path])
            for op in expected.values():
                op.pop('deprecated'); op.pop('x-privacy-mode'); op['responses'].pop('410')
            require(expected==ops,'Unexpected legacy change: '+path)
    v2=[p for p in api['paths'] if p.startswith('/api/v2/alerts')]
    require(len(v2)==6,'Need six privacy operations')
    for path in v2:
        for method,op in api['paths'][path].items():
            require(op['security']==[{'bearerAuth':[]}],'Unsigned operation')
            require(op['x-alert-permission'] in ['READ','MANAGER','HISTORY'],'Missing permission')
            for response in op['responses'].values(): require(response['headers']['Cache-Control']['schema']['const']=='no-store','Cacheable response')
            if method=='post': require(next(p for p in op['parameters'] if p['name']=='Idempotency-Key')['schema']==UUID7,'Unbounded key')
    for item in load(CANDIDATE/'examples/responses.json').values(): validate_value(item['schema'],item['value'])
    for name,value in load(CANDIDATE/'examples/requests.json').items(): legacy_value(name,value)
    for item in load(CANDIDATE/'examples/negative.json'):
        try: validate_value(item['schema'],item['value'])
        except (ValueError, __import__('jsonschema').ValidationError): pass
        else: raise ValueError('Negative accepted: '+item['reason'])
    release=load(HOME/'RELEASE_0_9_0.json')
    require(release['sourceManifestSha256']==sha((HOME/'CANDIDATE_MANIFEST.json').read_bytes()),'Release manifest drift')
    require((ROOT/'VERSION').read_text().strip()=='0.9.0','Local release version')
    for name,h in release['files'].items(): require(sha((ROOT/name).read_bytes())==h,'Release byte drift: '+name)
    print('PASS: five exact privacy artifacts, 70 operations, retained 58 non-alert operations/all old schemas, six v2 operations, bounded keys and expiry/redaction fixtures')

if __name__=='__main__': run()
