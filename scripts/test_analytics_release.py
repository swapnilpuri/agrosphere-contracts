import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import analytics_release_compatibility as release


class AnalyticsReleaseTests(unittest.TestCase):
    def test_exact_release_and_original_placeholder(self):
        release.validate_release()
        original = release.prior_analytics(release.ROOT / 'openapi/analytics-service.yaml')
        self.assertEqual({}, __import__('yaml').safe_load(original.read_text())['paths'])

    def test_approved_inventory_is_additive(self):
        self.assertEqual(10, len(release.analytics_inventory()))
        self.assertTrue(all(p.startswith(('openapi/analytics-service.yaml', 'examples/analytics/v1/')) for p in release.analytics_inventory()))

    def test_modified_release_archive_and_input_bytes_fail(self):
        (release.ROOT / 'target').mkdir(exist_ok=True)
        metadata = json.loads((release.BASE / 'RELEASE_0_11_0.json').read_text())
        for victim in ['openapi/analytics-service.yaml', 'docs/analytics-poc/previous-0.10.0/openapi/analytics-service.yaml', 'events/operations/v2/LatexCollectionRecorded.schema.json']:
            with self.subTest(victim=victim), tempfile.TemporaryDirectory(dir=release.ROOT / 'target', prefix='anl-release-') as temp:
                root = Path(temp)
                paths = set(metadata['files']) | set(metadata['archive']) | set(metadata['inputSchemasSha256'])
                paths |= {'VERSION', 'docs/analytics-poc/RELEASE_0_11_0.json', 'docs/analytics-poc/CANDIDATE_MANIFEST.json', 'docs/analytics-poc/CANDIDATE_REVIEW.md'}
                for path in paths:
                    p = root / path; p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_bytes(release.original_analytics_input(path).read_bytes())
                with patch.object(release, 'ROOT', root), patch.object(release, 'BASE', root / 'docs/analytics-poc'):
                    release.validate_release()
                    (root / victim).write_bytes(b'{}\n')
                    with self.assertRaises(AssertionError): release.validate_release()
