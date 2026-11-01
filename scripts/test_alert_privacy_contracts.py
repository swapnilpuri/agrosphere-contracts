import copy
import unittest
from datetime import datetime, timedelta, timezone
from jsonschema import ValidationError
from build_alert_privacy_contracts import CANDIDATE, load
from alert_privacy_contract_validation import validate_value, key_decision, run

class AlertPrivacyContractsTest(unittest.TestCase):
    now=datetime(2026,10,31,12,tzinfo=timezone.utc)
    def example(self,name): return copy.deepcopy(load(CANDIDATE/'examples/responses.json')[name]['value'])
    def key(self,at):
        stamp=f'{int(at.timestamp()*1000):012x}'
        return stamp[:8]+'-'+stamp[8:]+'-7000-8000-000000000001'
    def test_exact_candidate_and_compatibility(self): run()
    def test_ordinary_view_rejects_all_identity_and_tracking_extras(self):
        for field in ['issuer','subject','acknowledgedBy','summary','recipients','delivered']:
            with self.subTest(field=field),self.assertRaises(ValidationError): validate_value('ANPAlertView',dict(self.example('activeUnread'),**{field:'forbidden'}))
    def test_expiry_does_not_turn_deleted_read_into_unread(self):
        v=self.example('expiredRead')
        validate_value('ANPAlertView',v)
        for changes in [{'unreadForMe':True},{'readAttentionVersion':1},{'state':'ACTIVE'},{'readExpiresAt':None}]:
            with self.subTest(changes=changes),self.assertRaises(ValueError): validate_value('ANPAlertView',dict(v,**changes))
    def test_redaction_preserves_ack_but_not_actor_or_time(self):
        v=self.example('redactedAcknowledgement'); validate_value('ANPAlertView',v)
        for changes in [{'acknowledged':False},{'acknowledgedAt':v['updatedAt']},{'acknowledgementState':'RETAINED'}]:
            with self.subTest(changes=changes),self.assertRaises(ValueError): validate_value('ANPAlertView',dict(v,**changes))
    def test_history_expiry_is_explicit_and_empty(self):
        v=self.example('expiredHistory');validate_value('ANPHistoryPage',v)
        for changes in [{'totalElements':1},{'lastExpiredAt':None},{'lastExpiredAt':'2028-10-31T12:00:00Z'}]:
            with self.subTest(changes=changes),self.assertRaises(ValueError):validate_value('ANPHistoryPage',dict(v,**changes))
    def test_key_admission_and_future_skew_boundaries(self):
        for delta,expected in [(0,201),(-300,201),(-301,409),(300,201),(301,400)]:
            with self.subTest(delta=delta): self.assertEqual(expected,key_decision(self.key(self.now+timedelta(seconds=delta)),self.now))
    def test_deleted_old_receipt_cannot_be_reexecuted_without_tombstone(self):
        k=self.key(self.now-timedelta(days=30))
        self.assertEqual(410,key_decision(k,self.now))
        self.assertEqual(410,key_decision(k,self.now,receipt=self.now+timedelta(days=1)))
    def test_existing_live_receipt_replays_but_expiry_is_inclusive(self):
        k=self.key(self.now-timedelta(days=1))
        self.assertEqual(200,key_decision(k,self.now,receipt=self.now+timedelta(microseconds=1)))
        self.assertEqual(410,key_decision(k,self.now,receipt=self.now))
        self.assertEqual(409,key_decision(k,self.now))
    def test_authorization_precedes_receipt_and_expiry_disclosure(self):
        k=self.key(self.now-timedelta(days=31))
        self.assertEqual(403,key_decision(k,self.now,authorized=False))
    def test_removal_cutoff_covers_previously_admitted_future_skew_keys(self):
        key=self.key(self.now+timedelta(minutes=5))
        self.assertEqual(201,key_decision(key,self.now))
        request_at=self.now+timedelta(seconds=10)
        cutoff=request_at+timedelta(minutes=5)
        # Erasing the old receipt does not make a future-skew key new after reinstatement.
        self.assertEqual(410,key_decision(key,request_at,removal_cutoff=cutoff))
        fresh_at=cutoff+timedelta(seconds=1)
        self.assertEqual(201,key_decision(self.key(fresh_at),fresh_at,removal_cutoff=cutoff))
        self.assertEqual(410,key_decision(self.key(fresh_at),fresh_at,removal_cutoff=cutoff,removal_pending=True))
    def test_v4_or_malformed_or_noncanonical_keys_never_admitted(self):
        for key in ['00000000-0000-4000-8000-000000000001','not-a-key',self.key(self.now).upper()]:
            self.assertEqual(400,key_decision(key,self.now))

if __name__=='__main__': unittest.main()
