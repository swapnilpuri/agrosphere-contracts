"""Candidate contract boundary tests; no service or external network required."""
import copy
import json
import unittest
from decimal import Decimal

from jsonschema import Draft202012Validator, FormatChecker, ValidationError
from build_collection_contracts import add_operations, event_schema
from collection_contract_validation import ROOT, NAMES, check_compatibility, load, validate_event


class CollectionContractsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api = load(ROOT / "openapi/operations-service.yaml")
        cls.requests = load(ROOT / "examples/operations/v2/requests.json")
        cls.events = {n: load(ROOT / "examples/operations/v2" / (n+".json")) for n in NAMES}

    def request_validator(self, name):
        return Draft202012Validator({"$ref": "#/components/schemas/"+name, "components": self.api["components"]}, format_checker=FormatChecker())

    def test_legacy_bytes_and_all_27_operations(self):
        check_compatibility()

    def test_generated_artifacts_have_not_drifted(self):
        candidate = copy.deepcopy(self.api)
        add_operations(candidate)
        self.assertEqual(json.loads(json.dumps(candidate), parse_float=Decimal), self.api)
        for name in NAMES:
            # Decimal values compare numerically to source schema literals here;
            # exact decimal validation always loads the serialized schema separately.
            generated = event_schema(name)
            self.assertEqual(json.loads(json.dumps(generated), parse_float=Decimal), load(ROOT / "events/operations/v2" / (name+".schema.json")))

    def test_all_positive_fixtures(self):
        for event in self.events.values():
            validate_event(event)
        for path in (ROOT / "examples/operations/v2/edge").glob("*.json"):
            validate_event(load(path))
        for name, body in self.requests.items():
            self.request_validator(name).validate(body)

    def test_each_event_required_field_and_unknown_properties(self):
        for name, event in self.events.items():
            for field in event:
                bad = copy.deepcopy(event)
                del bad[field]
                with self.subTest(event=name, missing=field), self.assertRaises((ValidationError, ValueError)):
                    validate_event(bad)
            for target in [[], ["payload"], ["payload", "collection"], ["payload", "collection", "weightEvidence"]]:
                bad = copy.deepcopy(event)
                obj = bad
                for key in target:
                    obj = obj[key]
                obj["unexpected"] = True
                with self.subTest(event=name, target=target), self.assertRaises(ValidationError):
                    validate_event(bad)

    def test_exact_decimal_request_boundaries(self):
        v = self.request_validator("CollectionCreate")
        for value in [Decimal("0.001"), Decimal("999999.999"), Decimal("1.0000")]:
            body = copy.deepcopy(self.requests["CollectionCreate"])
            body["wetLatexKg"] = value
            v.validate(body)
        for value in [0, -1, Decimal("1000000"), Decimal("1.0001"), "1.000", None, True]:
            body = copy.deepcopy(self.requests["CollectionCreate"])
            body["wetLatexKg"] = value
            with self.subTest(value=value), self.assertRaises(ValidationError):
                v.validate(body)
        v = self.request_validator("CollectionInitialDrcWrite")
        for value in [Decimal("0.00"), Decimal("100.00"), Decimal("32.4000")]:
            body = copy.deepcopy(self.requests["CollectionInitialDrcWrite"])
            body["measurement"]["drcPercent"] = value
            v.validate(body)
        for value in [Decimal("-0.01"), Decimal("100.01"), Decimal("32.401"), "32.40", None]:
            body = copy.deepcopy(self.requests["CollectionInitialDrcWrite"])
            body["measurement"]["drcPercent"] = value
            with self.subTest(value=value), self.assertRaises(ValidationError):
                v.validate(body)

    def test_timestamp_microseconds_offset_and_trailing_zeros(self):
        v = self.request_validator("CollectionCreate")
        for value in ["2026-10-27T10:00:00Z", "2026-10-27T10:00:00.123456000+05:30", "2026-10-27T10:00:00.100000000Z"]:
            body = copy.deepcopy(self.requests["CollectionCreate"])
            body["collectedAt"] = value
            v.validate(body)
        for value in ["2026-10-27T10:00:00", "2026-10-27T10:00:00.0000001Z", "2026-10-27T10:00:00.1000001Z", "2026-02-30T10:00:00Z"]:
            body = copy.deepcopy(self.requests["CollectionCreate"])
            body["collectedAt"] = value
            with self.subTest(value=value), self.assertRaises(ValidationError):
                v.validate(body)

    def test_closed_requests_provenance_and_lab_evidence(self):
        for key in ["estateId", "blockId", "workerId", "dryRubberKg", "drcPercent", "createdBy"]:
            body = copy.deepcopy(self.requests["CollectionCreate"])
            body[key] = "forged"
            with self.subTest(key=key), self.assertRaises(ValidationError):
                self.request_validator("CollectionCreate").validate(body)
        for value in ["ESTIMATED", "PREDICTED"]:
            body = copy.deepcopy(self.requests["CollectionCreate"])
            body["dataProvenance"] = value
            with self.assertRaises(ValidationError):
                self.request_validator("CollectionCreate").validate(body)
        body = copy.deepcopy(self.requests["CollectionInitialDrcWrite"])
        body["measurement"]["method"] = "LAB_REPORTED"
        with self.assertRaises(ValidationError):
            self.request_validator("CollectionInitialDrcWrite").validate(body)
        body["measurement"]["sampleReference"] = "SIMULATED-SAMPLE"
        self.request_validator("CollectionInitialDrcWrite").validate(body)

    def test_correction_shape_and_null_rules(self):
        v = self.request_validator("CollectionCorrection")
        for body in [{"version":1,"reason":"reason"}, {"version":1,"reason":"reason","wetLatexKg":None},
                     {"version":1,"reason":"reason","replacementMeasurement":None}, {"version":1,"reason":"reason","estateId":"forged"}]:
            with self.subTest(body=body), self.assertRaises(ValidationError):
                v.validate(body)
        v.validate({"version":1,"reason":"reason","backdateReason":None})

    def test_receipt_headers_dates_and_auth_are_explicit(self):
        operations = [(path, method, operation) for path, item in self.api["paths"].items() if path.startswith('/api/v1/tapping/collections') for method,operation in item.items()]
        self.assertEqual(9, len(operations))
        for path, method, op in operations:
            self.assertEqual([{"bearerAuth": []}], op["security"])
            if method == 'post':
                key = next(p for p in op['parameters'] if p['name']=='Idempotency-Key')
                self.assertTrue(key['required'])
                self.assertEqual('uuid', key['schema']['format'])
        base = '/api/v1/tapping/collections'
        self.assertEqual('both-or-neither', self.api['paths'][base]['get']['x-query-constraints']['dateBounds'])
        self.assertEqual('both-required', self.api['paths'][base+'/summary']['get']['x-query-constraints']['dateBounds'])
        self.assertIn('Location', self.api['paths'][base]['post']['responses']['201']['headers'])
        self.assertNotIn('status', [p['name'] for p in self.api['paths'][base+'/summary']['get']['parameters']])

    def test_null_is_distinct_from_measured_zero_and_void_retains_shape(self):
        pending = copy.deepcopy(self.events['LatexCollectionRecorded'])
        pending['payload']['collection']['dryRubberKg'] = Decimal('0.000')
        with self.assertRaises(ValidationError):
            validate_event(pending)
        zero = load(ROOT/'examples/operations/v2/edge/zero-drc.json')
        validate_event(zero)
        zero['payload']['collection']['currentMeasurement'] = None
        with self.assertRaises(ValidationError):
            validate_event(zero)

    def test_semantic_mutations_rejected(self):
        mutations = [
            ('aggregateVersion', 99), ('estateId', '00000000-0000-0000-0000-000000000999'),
            ('aggregateId', '00000000-0000-0000-0000-000000000999')]
        for key,value in mutations:
            event = copy.deepcopy(self.events['DrcMeasurementRecorded'])
            event[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_event(event)
        for key,value in [('dryRubberKg',Decimal('40.661')),('dryRubberExactKg',Decimal('40.6621'))]:
            event = copy.deepcopy(self.events['DrcMeasurementRecorded'])
            event['payload']['collection'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_event(event)
        event = copy.deepcopy(self.events['LatexCollectionAdjusted'])
        event['payload']['previousVersion'] = 0
        with self.assertRaises(ValueError):
            validate_event(event)

    def test_persisted_negative_fixtures(self):
        files = list((ROOT/'examples/operations/v2/negative').glob('*.json'))
        self.assertGreaterEqual(len(files), 6)
        for file in files:
            with self.subTest(file=file.name), self.assertRaises((ValueError, ValidationError)):
                validate_event(load(file))


if __name__ == '__main__':
    unittest.main()
