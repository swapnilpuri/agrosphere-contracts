import copy
import unittest
from jsonschema import ValidationError
from build_alert_contracts import CANDIDATE, OPERATIONS
from alert_contract_validation import check_compatibility, load, validate_value, run


class AlertContractTests(unittest.TestCase):
    def responses(self): return load(CANDIDATE/'examples/responses.json')
    def test_complete_candidate_and_compatibility(self): run()
    def test_positive_permissions_auth_headers_and_query_bounds(self):
        api=check_compatibility()
        for method,suffix,_,request,_,permission in OPERATIONS:
            op=api['paths']['/api/v1/alerts'+suffix][method]
            self.assertEqual([{'bearerAuth':[]}],op['security']);self.assertEqual(permission,op['x-alert-permission'])
            self.assertEqual('reject',op['x-query-constraints']['unknownFilters'])
            self.assertEqual(10000,op['x-query-constraints']['maximumOffset'])
            params={p['name']:p for p in op['parameters']}
            self.assertEqual(bool(request),'Idempotency-Key' in params)
            if request:self.assertTrue(params['Idempotency-Key']['required'])
            if suffix in ['','/counts']:self.assertTrue(params['estateId']['required'])
            for response in op['responses'].values():self.assertEqual('no-store',response['headers']['Cache-Control']['schema']['const'])
    def test_closed_command_shapes_and_missing_fields(self):
        for n,v in load(CANDIDATE/'examples/requests.json').items():
            for key in v:
                bad=dict(v);del bad[key]
                with self.assertRaises(ValidationError):validate_value(n,bad)
            for key in ['issuer','subject','recipientId','estateId','provenance','reason']:
                with self.assertRaises(ValidationError):validate_value(n,dict(v,**{key:'forbidden'}))
    def test_signed_int64_bounds_and_fractional_versions(self):
        for n,v in load(CANDIDATE/'examples/requests.json').items():
            for key in v:
                for bad in [0,-1,9223372036854775808,1.5,'1',None,True]:
                    with self.subTest(n=n,key=key,bad=bad),self.assertRaises(ValidationError):validate_value(n,dict(v,**{key:bad}))
                validate_value(n,dict(v,**{key:9223372036854775807}))
    def test_private_fields_never_appear_in_ordinary_view(self):
        v=self.responses()['unread']['value']
        for key in ['summary','details','findings','subject','acknowledgedBy','recipients','delivered']:
            with self.assertRaises(ValidationError):validate_value('AlertView',dict(v,**{key:'forbidden'}))
    def test_read_receipt_is_personal_not_shared_ack(self):
        v=self.responses()['read']['value'];validate_value('AlertView',v)
        self.assertFalse(v['acknowledged']);self.assertFalse(v['unreadForMe'])
        with self.assertRaises(ValueError):validate_value('AlertView',dict(v,readAttentionVersion=2))
    def test_inactive_reason_and_human_severity_predicate(self):
        v=self.responses()['unread']['value']
        for status in ['OPEN','IN_REVIEW','RESOLVED','VOIDED']:
            for severity in ['LOW','MEDIUM','HIGH','CRITICAL']:
                eligible=status in ['OPEN','IN_REVIEW'] and severity in ['HIGH','CRITICAL']
                reason=None if eligible else status if status in ['RESOLVED','VOIDED'] else 'BELOW_THRESHOLD'
                validate_value('AlertView',dict(v,incidentStatus=status,severity=severity,state='ACTIVE' if eligible else 'INACTIVE',inactiveReason=reason))
    def test_provenance_and_time_precision(self):
        v=self.responses()['unread']['value']
        for value in ['REAL','ESTIMATED','PREDICTED',None]:
            with self.assertRaises(ValidationError):validate_value('AlertView',dict(v,dataProvenance=value))
        for value in ['2026-10-31T12:00:00','2026-10-31T12:00:00+01:00','2026-10-31T12:00:00.1234567Z','2026-02-30T12:00:00Z']:
            with self.assertRaises(ValidationError):validate_value('AlertView',dict(v,updatedAt=value))
    def test_protected_history_actor_only_for_ack(self):
        v=self.responses()['ack-history']['value'];validate_value('HistoryEntry',v)
        with self.assertRaises(ValueError):validate_value('HistoryEntry',dict(v,kind='SOURCE_UPDATED'))
        with self.assertRaises(ValueError):validate_value('HistoryEntry',dict(v,acknowledgedBy=None))
    def test_page_offset_cardinality_and_nested_validation(self):
        v=copy.deepcopy(self.responses()['page']['value'])
        with self.assertRaises(ValueError):validate_value('AlertPage',dict(v,page=501))
        v['content'][0]['summary']='forbidden'
        with self.assertRaises(ValidationError):validate_value('AlertPage',v)
    def test_counts_do_not_invent_recipients_or_exceed_total(self):
        v=self.responses()['counts']['value']
        with self.assertRaises(ValueError):validate_value('Counts',dict(v,activeUnacknowledged=2))
        with self.assertRaises(ValidationError):validate_value('Counts',dict(v,recipientCount=0))
    def test_no_delivered_or_recipient_event_contract(self):
        api=check_compatibility()
        self.assertEqual(6,len(OPERATIONS))
        self.assertFalse(any('event' in p.lower() for p in load(CANDIDATE.parent/'CANDIDATE_MANIFEST.json')['files']))
        self.assertNotIn('email',str(api['components']['schemas']['ANAlertView']))


if __name__=='__main__':unittest.main()
