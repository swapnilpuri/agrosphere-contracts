import copy
import unittest

from jsonschema import ValidationError
from build_crop_health_contracts import CANDIDATE, NAMES, OPERATIONS
from crop_health_contract_validation import check_compatibility, load, request_validator, validate_event, run


class CropHealthContractTests(unittest.TestCase):
    def event(self, name=NAMES[2]):
        return load(CANDIDATE/'examples/operations/crop-health/v1'/(name+'.json'))

    def requests(self): return load(CANDIDATE/'examples/operations/crop-health/v1/requests.json')

    def test_compatibility_and_all_persisted_examples(self): run()

    def test_security_keys_paths_and_scoped_lists(self):
        api=check_compatibility()
        for method,path,_,request,_,permission in OPERATIONS:
            op=api['paths']['/api/v1'+path][method]
            self.assertEqual([{'bearerAuth':[]}],op['security'])
            self.assertEqual(permission,op['x-crop-health-permission'])
            self.assertEqual('reject',op['x-query-constraints']['unknownFilters'])
            params={p['name']:p for p in op['parameters']}
            self.assertEqual(bool(request),'Idempotency-Key' in params)
            if request: self.assertTrue(params['Idempotency-Key']['required'])
            if '{id}' in path: self.assertTrue(params['id']['required'])
            if method=='get' and path in ['/incidents','/inspections']:
                self.assertTrue(params['estateId']['required']);self.assertTrue(params['provenance']['required'])

    def test_required_fields_unknown_fields_and_immutable_identity(self):
        for name,body in self.requests().items():
            v=request_validator(name);v.validate(body)
            schema=v.schema['components']['schemas']['CH'+name]
            for key in schema['required']:
                bad=dict(body);del bad[key]
                with self.subTest(name=name,key=key),self.assertRaises(ValidationError):v.validate(bad)
            for key in ['recordedBy','createdAt','status','workerRegistrationId','attachmentUrl']:
                with self.subTest(name=name,key=key),self.assertRaises(ValidationError):v.validate(dict(body,**{key:'forbidden'}))
            if name not in ['InspectionRecord','IncidentReport']:
                with self.assertRaises(ValidationError):v.validate(dict(body,estateId='00000000-0000-0000-0000-000000000001'))

    def test_clear_and_follow_up_conditionals(self):
        body=self.requests()['InspectionRecord'];v=request_validator('InspectionRecord')
        bad=dict(body);del bad['incident']
        with self.assertRaises(ValidationError):v.validate(bad)
        bad['outcome']='CLEAR';v.validate(bad)
        with self.assertRaises(ValidationError):v.validate(dict(body,outcome='CLEAR'))

    def test_no_real_estimated_or_predicted_create(self):
        for name in ['InspectionRecord','IncidentReport']:
            for provenance in ['REAL','ESTIMATED','PREDICTED',None]:
                with self.subTest(name=name,provenance=provenance),self.assertRaises(ValidationError):
                    request_validator(name).validate(dict(self.requests()[name],dataProvenance=provenance))

    def test_offset_input_and_microsecond_precision(self):
        body=self.requests()['IncidentReport'];v=request_validator('IncidentReport')
        for value in ['2026-10-31T10:00:00Z','2026-10-31T11:00:00.123456+01:00']:
            v.validate(dict(body,observedAt=value))
        for value in ['2026-10-31T10:00:00','2026-10-31T10:00:00.1234567Z','2026-02-30T10:00:00Z']:
            with self.assertRaises(ValidationError):v.validate(dict(body,observedAt=value))

    def test_controls_blanks_and_unicode_lengths(self):
        body=self.requests()['IncidentReport'];v=request_validator('IncidentReport')
        for summary in ['', '  ', 'x\ny', 'x\x85y', 'x'*201]:
            with self.assertRaises(ValidationError):v.validate(dict(body,summary=summary))
        v.validate(dict(body,summary='SIMULATED — é 🌱'))

    def test_no_shared_text_or_actor_and_closed_envelopes(self):
        for name in NAMES:
            event=self.event(name);validate_event(event)
            for key in ['summary','details','findings','reason','recordedBy','resolutionNote','workerId']:
                bad=copy.deepcopy(event);bad['payload']['snapshot'][key]='forbidden'
                with self.subTest(name=name,key=key),self.assertRaises(ValidationError):validate_event(bad)
            for key in event:
                bad=copy.deepcopy(event);del bad[key]
                with self.subTest(name=name,key=key),self.assertRaises((ValueError,ValidationError)):validate_event(bad)

    def test_envelope_snapshot_identity_and_version(self):
        for key in ['aggregateId','estateId','blockId','dataProvenance','aggregateVersion']:
            bad=self.event();bad[key]=8 if key=='aggregateVersion' else ('REAL' if key=='dataProvenance' else '00000000-0000-0000-0000-000000000099')
            with self.assertRaises((ValueError,ValidationError)):validate_event(bad)
        bad=self.event(NAMES[3]);bad['payload']['previousVersion']=2
        with self.assertRaises(ValueError):validate_event(bad)

    def test_lifecycle_snapshot_and_resolution_chronology(self):
        bad=self.event();bad['payload']['snapshot']['status']='RESOLVED'
        with self.assertRaises(ValueError):validate_event(bad)
        event=self.event(NAMES[3]);p=event['payload'];p['changeKind']='RESOLVE';s=p['snapshot'];s['status']='RESOLVED'
        for time in ['2026-10-31T09:00:00Z','2026-10-31T13:00:00Z']:
            s['resolvedAt']=time
            with self.assertRaises(ValueError):validate_event(event)
        s['resolvedAt']='2026-10-31T11:00:00Z';validate_event(event)
        p['changeKind']='REOPEN';s['status']='OPEN'
        with self.assertRaises(ValueError):validate_event(event)
        s['resolvedAt']=None;validate_event(event)

    def test_followup_links_and_terminal_inspection(self):
        bad=self.event(NAMES[0]);bad['payload']['snapshot']['linkedIncidentId']=None
        with self.assertRaises(ValueError):validate_event(bad)
        bad=self.event(NAMES[1]);bad['payload']['changeKind']='CORRECT'
        with self.assertRaises(ValueError):validate_event(bad)

    def test_current_views_omit_actors_and_reasons_history_protects_them(self):
        api=check_compatibility();shapes=api['components']['schemas']
        for name in ['CHInspectionView','CHIncidentView']:
            self.assertFalse(set(shapes[name]['properties'])&{'createdBy','updatedBy','reason','recordedBy'})
        for name in ['CHInspectionHistoryEntry','CHIncidentHistoryEntry']:
            self.assertIn('recordedBy',shapes[name]['properties']);self.assertIn('reason',shapes[name]['properties'])


if __name__=='__main__':unittest.main()
