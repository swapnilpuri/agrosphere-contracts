import copy
import unittest
from build_environmental_contracts import PATH, artifacts, build
from environmental_contract_validation import history, query, run


class EnvironmentalContractsTests(unittest.TestCase):
    def sample(self, name='mixed'): return copy.deepcopy(artifacts()['examples/' + name + '.json'])
    def invalid(self, change, name='mixed'):
        value = self.sample(name); change(value)
        with self.assertRaises(Exception): history(value)

    def test_deterministic_candidate_and_all_closed_examples(self):
        build(check=True); run()
        self.assertEqual(['get'], list(artifacts()['openapi/analytics-service.yaml']['paths'][PATH]))

    def test_explicit_utc_half_open_window_and_no_unknown_filters(self):
        q = {k: self.sample()[k] for k in ['estateId', 'blockId', 'from', 'to']}
        query(q)
        for change in [{'to': q['from']}, {'to': '2026-01-02T00:00:00.001Z'}, {'from': '2026-01-01T00:00:00+00:00'},
                       {'from': '2026-01-01T00:00:00.0001Z'}, {'deviceId': 'unsupported'}, {'from': '2026-02-30T00:00:00Z'}]:
            with self.assertRaises(Exception): query(dict(q, **change))
        self.invalid(lambda x: x['observations'][0].update(observedAt=x['to']))

    def test_absence_zero_and_conflict_outside_window(self):
        history(self.sample('none')); history(self.sample('conflict-outside-window'))
        self.assertEqual('0', self.sample('soil_moisture')['observations'][0]['value'])
        self.invalid(lambda x: x.update(availability='NONE'))
        self.invalid(lambda x: x.update(projectionState='OBSERVED_ONLY'), 'conflict-outside-window')

    def test_cap_counts_and_returned_kind_counts(self):
        history(self.sample('truncated'))
        self.invalid(lambda x: x.update(truncated=False), 'truncated')
        self.invalid(lambda x: x.update(totalMatchingCount='4'))
        self.invalid(lambda x: x['returnedKindCounts'].update(AIR_TEMPERATURE=2))
        self.invalid(lambda x: x.update(totalMatchingCount=3))

    def test_exact_decimal_kind_unit_interval_and_source_semantics(self):
        for v in [0, '1e0', '01', '1.1234567', 'NaN']:
            self.invalid(lambda x: x['observations'][0].update(value=v))
        self.invalid(lambda x: x['observations'][1].update(value='100.000001'))
        self.invalid(lambda x: x['observations'][2].update(value='-1'))
        self.invalid(lambda x: x['observations'][2].update(intervalEnd='2026-01-02T00:00:00Z'))
        self.invalid(lambda x: x['observations'][0].update(unit='PERCENT'))
        self.invalid(lambda x: x['observations'][0].update(sourceEventAt='2026-01-01T12:00:02Z'))
        self.assertLess(self.sample()['observations'][2]['intervalStart'], self.sample()['from'])

    def test_identity_order_scope_and_metadata(self):
        self.invalid(lambda x: x['observations'].reverse())
        self.invalid(lambda x: x['observations'][1].update(observationId=x['observations'][0]['observationId']))
        self.invalid(lambda x: x['observations'][1].update(sourceEventId=x['observations'][0]['sourceEventId']))
        self.invalid(lambda x: x.update(lastProcessedAt=None))
        self.invalid(lambda x: x.update(latestSourceEventAt='2026-01-01T00:00:00Z'))
        self.invalid(lambda x: x.update(lastProcessedAt='2026-01-03T00:00:00Z'))
        q = {k: self.sample()[k] for k in ['estateId', 'blockId', 'from', 'to']}
        q['blockId'] = '00000000-0000-4000-8000-000000000999'
        with self.assertRaises(ValueError): history(self.sample(), q)

    def test_closed_schema_and_no_real_complete_or_personal_fields(self):
        for change in [dict(dataProvenance='REAL'), dict(projectionState='COMPLETE'), dict(actorId='private')]:
            self.invalid(lambda x: x.update(change))
        self.invalid(lambda x: x['observations'][0].update(estateId=x['estateId']))


if __name__ == '__main__': unittest.main()
