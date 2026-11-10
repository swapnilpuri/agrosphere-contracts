import copy
import unittest
from jsonschema import ValidationError
from build_telemetry_contracts import artifacts, build, KINDS
from telemetry_contract_validation import message, event, latest, run


class TelemetryContractTests(unittest.TestCase):
    def setUp(self):
        self.items = artifacts()
        self.temperature = copy.deepcopy(self.items['examples/AIR_TEMPERATURE.json'])
        self.rain = copy.deepcopy(self.items['examples/INTERVAL_RAINFALL.json'])
        self.soil = copy.deepcopy(self.items['examples/SOIL_MOISTURE.json'])
        self.event = copy.deepcopy(self.items['examples/TelemetryObservationRecorded.json'])
        self.latest = copy.deepcopy(self.items['examples/LatestReadings.json'])

    def denied(self, validator, value):
        with self.assertRaises((ValueError, ValidationError)):
            validator(value)

    def test_all_examples_and_exact_manifest(self):
        run()
        self.assertEqual(8, len(build(check=True)['artifacts']))

    def test_every_required_message_field_and_unknown_fields(self):
        for kind in KINDS:
            original = self.items[f'examples/{kind}.json']
            for key in original:
                value = copy.deepcopy(original); del value[key]
                self.denied(message, value)
            value = dict(original, actorSubject='forbidden')
            self.denied(message, value)

    def test_units_provenance_and_versions(self):
        for key, wrong in [('kind','UNKNOWN'),('unit','FAHRENHEIT'),('schemaVersion',2),('dataProvenance','REAL')]:
            self.denied(message, dict(self.temperature, **{key: wrong}))

    def test_decimal_wire_is_bounded_string_not_float_or_special(self):
        for invalid in [27.5, 'NaN', 'Infinity', '1e2', '+1', '01', '.1', '1.', '0.0000001', '1000000000000']:
            self.denied(message, dict(self.temperature, value=invalid))
        for valid in ['-999999999999.999999','999999999999.999999','-0','27.500000']:
            message(dict(self.temperature, value=valid))

    def test_moisture_boundaries(self):
        for valid in ['0','100','0.000001','99.999999']:
            message(dict(self.soil, value=valid))
        for invalid in ['-0.000001','100.000001']:
            self.denied(message, dict(self.soil, value=invalid))

    def test_rainfall_nonnegative_interval_and_observation_order(self):
        message(dict(self.rain, value='0'))
        self.denied(message, dict(self.rain, value='-1'))
        for change in [{'intervalStart': self.rain['intervalEnd']},
                       {'intervalStart':'2026-01-01T13:00:00Z'},
                       {'intervalEnd':'2026-01-01T12:00:00.001Z'}]:
            self.denied(message, dict(self.rain, **change))
        self.denied(message, dict(self.temperature, intervalStart=self.rain['intervalStart']))

    def test_uuid_and_utc_millisecond_formats(self):
        for value in ['not-uuid', '00000000-0000-4000-8000-00000000000A']:
            self.denied(message, dict(self.temperature, deviceId=value))
        for value in ['0000-01-01T00:00:00Z','2026-02-30T12:00:00Z','2026-01-01T12:00:00+00:00','2026-01-01T12:00:00.0001Z','2026-01-01T12:00:60Z']:
            self.denied(message, dict(self.temperature, observedAt=value))
        message(dict(self.temperature, observedAt='2026-01-01T12:00:00.001Z'))

    def test_recorded_future_skew_boundary(self):
        for bound in ['0001-01-01T00:00:00Z','9999-12-31T23:59:59.999Z']:
            message(dict(self.temperature, observedAt=bound, receivedAt=bound), recorded=True)
        value = dict(self.temperature, receivedAt='2026-01-01T11:55:00Z')
        message(value, recorded=True)
        value['receivedAt'] = '2026-01-01T11:54:59.999Z'
        self.denied(lambda x: message(x, recorded=True), value)

    def test_envelope_requires_all_fields_and_fixed_source(self):
        for key in self.event:
            value = copy.deepcopy(self.event); del value[key]
            self.denied(event, value)
        for key,wrong in [('source','other'),('eventVersion',2),('eventType','Other'),('aggregateVersion',2)]:
            self.denied(event, dict(self.event, **{key: wrong}))

    def test_cross_field_event_identity_and_time_cannot_lie(self):
        for key in ['estateId','blockId','aggregateId','timestamp']:
            value = copy.deepcopy(self.event)
            value[key] = '2026-01-01T12:00:02Z' if key == 'timestamp' else '00000000-0000-4000-8000-000000000099'
            self.denied(event, value)

    def test_empty_and_partial_are_not_missing_measurement_zeroes(self):
        latest(dict(self.latest, readings=[], coverage='NONE'))
        latest(dict(self.latest, readings=self.latest['readings'][:1], coverage='PARTIAL'))
        self.denied(latest, dict(self.latest, readings=[], coverage='COMPLETE'))

    def test_duplicate_kinds_wrong_scope_and_future_receipt_rejected(self):
        value = copy.deepcopy(self.latest); value['readings'][1] = value['readings'][0]
        self.denied(latest, value)
        value = copy.deepcopy(self.latest); value['readings'].reverse()
        self.denied(latest, value)
        value = copy.deepcopy(self.latest); value['readings'][0]['blockId'] = '00000000-0000-4000-8000-000000000099'
        self.denied(latest, value)
        self.denied(latest, dict(self.latest, generatedAt='2026-01-01T11:59:59Z'))


if __name__ == '__main__':
    unittest.main()
