import copy
import unittest
from datetime import date, timedelta
from build_analytics_contracts import artifacts, build, PATH
from analytics_contract_validation import history, query, run


class AnalyticsContractsTests(unittest.TestCase):
    def sample(self, name='calculated'):
        return copy.deepcopy(artifacts()['examples/' + name + '.json'])

    def invalid(self, change, name='calculated'):
        value = self.sample(name)
        change(value)
        with self.assertRaises(Exception):
            history(value)

    def test_candidate_and_examples_are_deterministic_and_valid(self):
        build(check=True)
        run()

    def test_one_read_only_route_and_existing_role_boundary(self):
        api = artifacts()['openapi/analytics-service.yaml']
        self.assertEqual([PATH], list(api['paths']))
        self.assertEqual(['get'], list(api['paths'][PATH]))
        self.assertEqual([{'bearerAuth': []}], api['security'])

    def test_no_data_pending_and_known_zero_drc_are_distinct(self):
        self.assertIsNone(self.sample('none')['days'][0]['metrics'])
        self.assertIsNone(self.sample('pending')['days'][0]['metrics']['knownDryRubberKg'])
        self.assertEqual('0.000', self.sample('zero-drc')['days'][0]['metrics']['knownDryRubberKg'])
        self.invalid(lambda x: x['days'][0]['metrics'].update(knownDryRubberKg='0.000'), 'pending')

    def test_rejects_noncanonical_decimal_numeric_and_inconsistent_partitions(self):
        for value in [3.333, '3e0', '03.333', '-0.001', 'NaN', '3.3330']:
            self.invalid(lambda x: x['days'][0]['metrics'].update(knownDryRubberKg=value))
        self.invalid(lambda x: x['days'][0]['metrics'].update(totalWetLatexKg='11.000'))
        self.invalid(lambda x: x['days'][0]['metrics'].update(activeCollectionCount=2))
        self.invalid(lambda x: x['days'][0]['metrics'].update(knownDryRubberKg='11.000'))

    def test_rejects_missing_duplicate_and_unordered_dates(self):
        self.invalid(lambda x: x['days'].clear())
        self.invalid(lambda x: x['days'].append(copy.deepcopy(x['days'][0])))
        self.invalid(lambda x: x['days'][0].update(date='2026-02-30'))

    def test_range_is_inclusive_bounded_and_unknown_filters_fail(self):
        q = {k: self.sample()[k] for k in ['estateId', 'blockId', 'from', 'to']}
        q['to'] = (date(2026, 1, 1) + timedelta(days=366)).isoformat()
        query(q)
        for change in [{'to': '2027-01-03'}, {'to': '2025-12-31'}, {'workerId': 'not-supported'}]:
            with self.assertRaises(Exception): query(dict(q, **change))

    def test_rejects_unknown_fields_real_provenance_and_false_completeness(self):
        self.invalid(lambda x: x.update(workerId='not-a-summary-field'))
        self.invalid(lambda x: x.update(dataProvenance='REAL'))
        self.invalid(lambda x: x.update(projectionState='COMPLETE'))
        self.invalid(lambda x: x.update(projectionState='OBSERVED_ONLY'), 'incomplete')
        self.invalid(lambda x: x['days'][0]['metrics'].update(isComplete=True), 'pending')

    def test_source_evidence_bounds_scope_and_order_are_enforced(self):
        q = {k: self.sample()[k] for k in ['estateId', 'blockId', 'from', 'to']}
        history(self.sample(), q)
        q['estateId'] = '00000000-0000-4000-8000-000000000999'
        with self.assertRaises(ValueError): history(self.sample(), q)
        self.invalid(lambda x: x['sourceVersionSample'].clear())
        self.invalid(lambda x: x.update(sourceVersionSampleTruncated=True))
        self.invalid(lambda x: x['sourceVersionSample'][0].update(collectionDate='2026-01-02'))
        self.invalid(lambda x: x.update(lastProcessedAt='2026-01-01T12:00:04Z'))


if __name__ == '__main__':
    unittest.main()
