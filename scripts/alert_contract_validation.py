"""Offline AN-1 executable candidate, semantic and exact compatibility checks."""
from telemetry_release_compatibility import prior_telemetry, telemetry_inventory
import hashlib
import json
from datetime import datetime
from jsonschema import Draft202012Validator, FormatChecker, ValidationError
from openapi_spec_validator import validate
from build_alert_contracts import BASE, CANDIDATE, ROOT, OPERATIONS, artifacts, APPROVED


def load(path): return json.loads(path.read_text(encoding='utf-8'))
def require(value, message):
    if not value: raise ValueError(message)
def instant(value): return datetime.fromisoformat(value.replace('Z', '+00:00'))


def validator(name):
    api=load(CANDIDATE/'openapi/operations-service.yaml')
    return Draft202012Validator({'$ref':'#/components/schemas/AN'+name,'components':api['components']},format_checker=FormatChecker())


def validate_value(name, value):
    validator(name).validate(value)
    if name=='AlertView':
        active=value['incidentStatus'] in ['OPEN','IN_REVIEW'] and value['severity'] in ['HIGH','CRITICAL']
        require((value['state']=='ACTIVE')==active,'Eligibility mismatch')
        reason=None if active else (value['incidentStatus'] if value['incidentStatus'] in ['RESOLVED','VOIDED'] else 'BELOW_THRESHOLD')
        require(value['inactiveReason']==reason,'Inactive reason mismatch')
        require(value['attentionVersion']<=value['alertVersion'],'Attention exceeds alert version')
        read=value['readAttentionVersion']
        require(read<=value['attentionVersion'],'Future read marker')
        require((read==0)==(value['readAt'] is None),'Read time mismatch')
        require(value['unreadForMe']==(read<value['attentionVersion']),'Unread mismatch')
        require(value['acknowledged']==(value['acknowledgedAt'] is not None),'Ack time mismatch')
        raised,attention,updated=map(lambda k:instant(value[k]),['raisedAt','attentionAt','updatedAt'])
        require(raised<=attention<=updated,'Reversed alert chronology')
        require(instant(value['observedAt'])<=updated,'Future observation')
        if value['acknowledgedAt'] is not None: require(attention<=instant(value['acknowledgedAt'])<=updated,'Ack chronology')
        if value['readAt'] is not None:
            require(instant(value['readAt'])>=raised,'Read before alert creation')
            if read==value['attentionVersion']: require(instant(value['readAt'])>=attention,'Read before current attention')
    elif name=='Counts':
        require(value['activeUnreadForMe']<=value['activeTotal'] and value['activeUnacknowledged']<=value['activeTotal'],'Counts exceed scoped total')
    elif name=='HistoryEntry':
        require((value['kind']=='ACKNOWLEDGED')==(value['acknowledgedBy'] is not None),'History actor leak/missing')
        require((value['kind']=='RAISED')==(value['beforeState'] is None),'Raised history mismatch')
        require(value['attentionVersion']<=value['alertVersion'],'History attention exceeds version')
        if value['kind'] in ['RAISED','REACTIVATED','ESCALATED','ACKNOWLEDGED']: require(value['afterState']=='ACTIVE','Attention transition must be active')
        if value['kind']=='DEACTIVATED': require(value['beforeState']=='ACTIVE' and value['afterState']=='INACTIVE','Deactivation mismatch')
    elif name.endswith('Page'):
        require(value['page']*value['size']<=10000,'Excessive offset')
        require(len(value['content'])<=value['size'] and len(value['content'])<=value['totalElements'],'Invalid page cardinality')
        for item in value['content']: validate_value('AlertView' if name=='AlertPage' else 'HistoryEntry',item)


def check_compatibility():
    baseline=load(BASE/'compatibility-baseline.json')
    promoted=(BASE/'RELEASE_0_8_0.json').exists()
    require((ROOT/'VERSION').read_text().strip()==('0.13.0' if (ROOT/'docs/m4/RELEASE_0_13_0.json').exists() else '0.12.0' if (ROOT/'docs/analytics-environment-poc/RELEASE_0_12_0.json').exists() else '0.11.0' if (ROOT/'docs/analytics-poc/RELEASE_0_11_0.json').exists() else '0.10.0' if (ROOT/'docs/telemetry-poc/RELEASE_0_10_0.json').exists() else '0.9.0' if (ROOT/'docs/alerts-privacy/RELEASE_0_9_0.json').exists() else '0.8.0' if promoted else '0.7.0'),'Release version mismatch')
    for f,h in baseline['files'].items():
        path=BASE/'previous-0.7.0'/f if promoted and f in ['VERSION','openapi/operations-service.yaml'] else ROOT/f
        require(hashlib.sha256(prior_telemetry(path).read_bytes()).hexdigest()==h,'Released bytes changed: '+f)
    release=load(BASE/'RELEASE_0_8_0.json') if promoted else {'files':{}}
    for f,h in release['files'].items():
        path=ROOT/'docs/alerts-privacy/previous-0.8.0'/f if f=='openapi/operations-service.yaml' and (ROOT/'docs/alerts-privacy/RELEASE_0_9_0.json').exists() else ROOT/f
        require(hashlib.sha256(prior_telemetry(path).read_bytes()).hexdigest()==h,'Accepted release changed: '+f)
    inventory={p.relative_to(ROOT).as_posix() for d in ['events','examples','openapi'] for p in (ROOT/d).rglob('*') if p.is_file()}
    privacy=load(ROOT/'docs/alerts-privacy/RELEASE_0_9_0.json') if (ROOT/'docs/alerts-privacy/RELEASE_0_9_0.json').exists() else {'files':{}}
    require(inventory==(set(baseline['files'])-{'VERSION'})|set(release['files'])|set(privacy['files'])|telemetry_inventory(),'Released inventory changed')
    old=load(BASE/'previous-0.7.0/openapi/operations-service.yaml' if promoted else ROOT/'openapi/operations-service.yaml');new=load(CANDIDATE/'openapi/operations-service.yaml')
    for p,v in old['paths'].items(): require(new['paths'].get(p)==v,'Existing path changed: '+p)
    for group,entries in old['components'].items():
        for n,v in entries.items(): require(new['components'][group].get(n)==v,'Existing component changed: '+n)
    require({k:v for k,v in old.items() if k not in ['paths','components']}=={k:v for k,v in new.items() if k not in ['paths','components']},'Metadata changed')
    operations=lambda a:{(p,m) for p,body in a['paths'].items() for m in body}
    require(len(operations(old))==58 and len(operations(new))==64,'Expected 58+6 operations')
    require(operations(new)-operations(old)=={('/api/v1/alerts'+suffix,method) for method,suffix,*_ in OPERATIONS},'Unexpected additions')
    return new


def run():
    api=check_compatibility();validate(api)
    for schema in api['components']['schemas'].values(): Draft202012Validator.check_schema(schema)
    manifest=load(BASE/'CANDIDATE_MANIFEST.json')
    require(manifest['approvedDesignSha256']==APPROVED and len(manifest['files'])==4,'Candidate manifest mismatch')
    require(set(manifest['files'])=={p.relative_to(ROOT).as_posix() for p in artifacts()},'Unexpected manifest inventory')
    for f,h in manifest['files'].items(): require(hashlib.sha256((ROOT/f).read_bytes()).hexdigest()==h,'Manifest drift: '+f)
    folder=CANDIDATE/'examples'
    for n,v in load(folder/'requests.json').items(): validate_value(n,v)
    for v in load(folder/'responses.json').values(): validate_value(v['schema'],v['value'])
    for v in load(folder/'negative.json'):
        try: validate_value(v['schema'],v['value'])
        except (ValueError,ValidationError): pass
        else: raise AssertionError('Accepted negative: '+v['case'])
    print('PASS: AN-1 64-operation candidate, two write shapes, nine positive responses, twenty negatives; released 0.7.0 bytes unchanged')


if __name__=='__main__':run()
