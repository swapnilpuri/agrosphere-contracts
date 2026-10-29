import copy
import unittest

from jsonschema import ValidationError

from build_workforce_contracts import CANDIDATE, NAMES, OPERATIONS
from workforce_contract_validation import check_compatibility, load, request_validator, validate_event


class WorkforceContractTests(unittest.TestCase):
    def event(self, name='WorkerAttendanceRecorded'):
        return load(CANDIDATE / 'examples/operations/workforce/v1' / (name + '.json'))

    def test_released_bytes_and_all_old_operation_semantics_preserved(self):
        check_compatibility()

    def test_all_operations_authenticate_and_writes_require_keys(self):
        api = check_compatibility()
        for method, suffix, _, request, *_ in OPERATIONS:
            op = api['paths']['/api/v1' + suffix][method]
            self.assertEqual([{'bearerAuth': []}], op['security'])
            self.assertEqual('reject', op['x-query-constraints']['unknownFilters'])
            keys = [p for p in op['parameters'] if p['name'] == 'Idempotency-Key']
            self.assertEqual(bool(request), bool(keys))
            if keys:
                self.assertTrue(keys[0]['required'])
                self.assertEqual('header', keys[0]['in'])
            if '{id}' in suffix:
                self.assertTrue(any(p['name']=='id' and p['required'] and p['in']=='path' for p in op['parameters']))

    def test_initial_attendance_cannot_supply_authority_or_voided_state(self):
        valid = dict(workerRegistrationId='00000000-0000-0000-0000-000000000001', attendanceDate='2026-10-29', status='PRESENT')
        validator = request_validator('AttendanceRecord')
        validator.validate(valid)
        for key,value in [('estateId',valid['workerRegistrationId']),('recordedBy','other-sub'),
                          ('dataProvenance','REAL'),('status','VOIDED'),('workerId','legacy-sub'),('recordedAt','2026-10-29T12:00:00Z')]:
            with self.subTest(key=key), self.assertRaises(ValidationError):
                validator.validate(dict(valid, **{key:value}))

    def test_required_request_properties_cannot_be_omitted(self):
        for name,body in load(CANDIDATE / 'examples/operations/workforce/v1/requests.json').items():
            validator = request_validator(name)
            validator.validate(body)
            for key in validator.schema['components']['schemas'][name]['required']:
                bad = dict(body); del bad[key]
                with self.subTest(schema=name,key=key), self.assertRaises(ValidationError):
                    validator.validate(bad)

    def test_reasons_reject_blanks_controls_and_oversized_text(self):
        validator = request_validator('AttendanceVoid')
        for reason in ['', '  ', 'x\ny', '\ttext', 'x\x85y', 'x'*1001, None]:
            with self.subTest(reason=repr(reason)), self.assertRaises(ValidationError):
                validator.validate(dict(version=0,reason=reason))
        validator.validate(dict(version=0,reason='SIMULATED — correction'))

    def test_update_omission_clear_and_immutable_identity(self):
        validator = request_validator('WorkerUpdate')
        validator.validate(dict(version=0,reason='SIMULATED clear',divisionId=None))
        for extra in [{}, {'displayName':None}, {'workerCode':'NEW'}, {'estateId':'00000000-0000-0000-0000-000000000001'}]:
            with self.subTest(extra=extra), self.assertRaises(ValidationError):
                validator.validate(dict(version=0,reason='SIMULATED change',**extra))

    def test_event_required_properties_and_private_fields_rejected(self):
        for name in NAMES:
            event = self.event(name); validate_event(event)
            for key in list(event):
                bad = copy.deepcopy(event); del bad[key]
                with self.subTest(name=name,key=key), self.assertRaises((ValueError,ValidationError)):
                    validate_event(bad)
            for key in ['displayName','workerCode','workerCodeSnapshot','reason','backdateReason','recordedBy','subject']:
                bad = copy.deepcopy(event); bad['payload']['snapshot'][key]='SIMULATED private'
                with self.subTest(name=name,private=key), self.assertRaises(ValidationError):
                    validate_event(bad)

    def test_event_identity_revision_and_provenance_cannot_diverge(self):
        for key,value in [('aggregateId','00000000-0000-0000-0000-000000000099'),('aggregateVersion',1),
                          ('estateId','00000000-0000-0000-0000-000000000099'),('dataProvenance','REAL')]:
            bad=self.event(); bad[key]=value
            with self.subTest(key=key), self.assertRaises((ValueError,ValidationError)):
                validate_event(bad)

    def test_event_version_source_namespace_and_precision(self):
        for key,value in [('eventVersion',2),('source','estate-service'),('eventType','TappingCompleted'),
                          ('timestamp','2026-10-29T12:00:00.1234567Z'),('blockId','00000000-0000-0000-0000-000000000001')]:
            bad=self.event(); bad[key]=value
            with self.subTest(key=key), self.assertRaises((ValueError,ValidationError)):
                validate_event(bad)
        bad=self.event(); bad['timestamp']='2026-10-29T12:00:00.123456000Z'; validate_event(bad)

    def test_period_order_and_overlap_semantics(self):
        event=self.event('WorkerRegistrationChanged')
        period=event['payload']['snapshot']['activePeriods'][0]
        for end in ['2026-10-29','2026-10-28']:
            period['activeTo']=end
            with self.subTest(end=end), self.assertRaises(ValueError): validate_event(event)
        period['activeTo']=None
        event['payload']['snapshot']['activePeriods'].append(dict(id='00000000-0000-0000-0000-000000000090',activeFrom='2026-10-30',activeTo=None))
        with self.assertRaises(ValueError): validate_event(event)
        period['activeTo']='2026-10-30'; validate_event(event)

    def test_void_and_rerecord_snapshot_tombstones(self):
        event=self.event('WorkerAttendanceChanged'); validate_event(event)
        event['payload']['changeKind']='RERECORD'
        with self.assertRaises(ValueError): validate_event(event)
        event['payload']['snapshot']['status']='EXCUSED'; validate_event(event)
        event['payload']['previousVersion']=7
        with self.assertRaises(ValueError): validate_event(event)

    def test_current_views_exclude_private_history_fields(self):
        api=check_compatibility()
        for name in ['WorkerView','AttendanceView','WorkerRosterItem']:
            properties=api['components']['schemas'][name]['properties']
            self.assertFalse(set(properties) & {'createdBy','updatedBy','recordedBy','reason','backdateReason'})
        for name in ['WorkerHistoryEntry','AttendanceHistoryEntry']:
            self.assertIn('recordedBy',api['components']['schemas'][name]['properties'])


if __name__ == '__main__':
    unittest.main()
