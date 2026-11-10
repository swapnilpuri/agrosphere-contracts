"""Offline ANL-01 response/query oracle; not a server or production projection."""
from datetime import date, datetime, timedelta
from decimal import Decimal
import json
from jsonschema import Draft202012Validator, FormatChecker
from openapi_spec_validator import validate as validate_openapi
from build_analytics_contracts import artifacts, schemas, build


def require(condition, message):
    if not condition:
        raise ValueError(message)


def query(value):
    require(set(value) == {'estateId', 'blockId', 'from', 'to'}, 'Unknown/missing query')
    definitions = schemas()['DailyProductionHistory']['properties']
    for key, item in value.items():
        Draft202012Validator(definitions[key], format_checker=FormatChecker()).validate(item)
    start, end = date.fromisoformat(value['from']), date.fromisoformat(value['to'])
    require(0 <= (end - start).days <= 366, 'Query range')


def history(value, expected_query=None):
    Draft202012Validator(schemas()['DailyProductionHistory'], format_checker=FormatChecker()).validate(value)
    query({key: value[key] for key in ['estateId', 'blockId', 'from', 'to']})
    if expected_query is not None:
        query(expected_query)
        require(all(value[k] == expected_query[k] for k in expected_query), 'Response request-scope mismatch')
    start, end = date.fromisoformat(value['from']), date.fromisoformat(value['to'])
    require([x['date'] for x in value['days']] == [(start + timedelta(days=n)).isoformat() for n in range((end - start).days + 1)], 'Missing/duplicate/out-of-order day')
    roots = 0
    by_day = {}
    for row in value['days']:
        m = row['metrics']
        require((m is None) == (row['availability'] == 'NONE'), 'Absence semantics')
        if m is None:
            by_day[row['date']] = 0
            continue
        a, p, c, v = [m[k] for k in ['activeCollectionCount', 'pendingDrcCount', 'calculatedCollectionCount', 'voidedCollectionCount']]
        require(a == p + c and a + v > 0, 'Count arithmetic')
        roots += a + v
        by_day[row['date']] = a + v
        wet, pending, calculated = [Decimal(m[k]) for k in ['totalWetLatexKg', 'pendingWetLatexKg', 'calculatedWetLatexKg']]
        require(wet == pending + calculated and (pending > 0) == (p > 0) and (calculated > 0) == (c > 0), 'Wet mass partition')
        require((m['knownDryRubberKg'] is None) == (c == 0), 'Unknown DRC is not zero')
        if c:
            require(Decimal(m['knownDryRubberKg']) <= calculated, 'Dry mass exceeds calculated wet mass')
        require(m['isComplete'] == (p == 0), 'DRC coverage semantics')
    sample = value['sourceVersionSample']
    require(len(sample) == min(roots, 100) and value['sourceVersionSampleTruncated'] == (roots > 100), 'Source sample bound/coverage')
    keys = [x['collectionId'] for x in sample]
    require(keys == sorted(set(keys)), 'Source ordering/duplicates')
    require(all(x['collectionDate'] in by_day and by_day[x['collectionDate']] > 0 for x in sample), 'Source outside observed query dates')
    for day, count in by_day.items():
        require(sum(x['collectionDate'] == day for x in sample) <= count, 'Source day count')
    incomplete = int(value['missingSourceVersionCount']) > 0 or value['conflictCount'] > 0 or value['unsupportedCount'] > 0
    require(value['projectionState'] == ('INCOMPLETE' if incomplete else 'OBSERVED_ONLY'), 'Observed is not stream completeness')
    if sample:
        require(value['lastProcessedAt'] is not None and value['latestSourceEventAt'] is not None, 'Missing source metadata')
    instant = lambda x: datetime.fromisoformat(x.replace('Z', '+00:00'))
    if value['lastProcessedAt'] is not None:
        require(instant(value['lastProcessedAt']) <= instant(value['generatedAt']), 'Processing clock ahead of response')
    if value['latestSourceEventAt'] is not None:
        require(all(instant(x['sourceEventAt']) <= instant(value['latestSourceEventAt']) for x in sample), 'Source metadata clock')


def run():
    build(check=True)
    values = artifacts()
    validate_openapi(values['openapi/analytics-service.yaml'])
    for name, value in values.items():
        if not name.startswith('examples/'):
            continue
        if value.get('status') in [403, 503]:
            Draft202012Validator(schemas()['Problem'], format_checker=FormatChecker()).validate(value)
        else:
            history(value)
    print('PASS: isolated ANL-01 API, nine examples, decimal/absence/coverage/source semantics; no release')
    from analytics_release_compatibility import validate_release
    validate_release()


if __name__ == '__main__':
    run()
