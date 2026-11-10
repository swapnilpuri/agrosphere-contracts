"""Tampering must fail in current release, accepted candidate, inputs and prior archive."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import environmental_release_compatibility as release


class EnvironmentalReleaseTests(unittest.TestCase):
    def test_exact_release_and_inventory(self):
        release.validate_release()
        self.assertEqual(14, len(release.environmental_inventory()))
        self.assertEqual('0.12.0', release.original_environmental_input('VERSION').read_text().strip())

    def test_changed_released_candidate_input_or_archive_bytes_fail(self):
        original = Path.read_bytes
        for name in ['openapi/analytics-service.yaml', 'examples/analytics/environment/v1/none.json',
                     'docs/analytics-environment-poc/candidate/openapi/analytics-service.yaml',
                     'docs/analytics-environment-poc/CANDIDATE_MANIFEST.json',
                     'docs/analytics-environment-poc/previous-0.11.0/openapi/analytics-service.yaml',
                     'docs/analytics-environment-poc/previous-0.11.0/VERSION',
                     'events/telemetry/v1/TelemetryObservationRecorded.schema.json']:
            victim = release.ROOT / name
            with self.subTest(victim=name), patch.object(Path, 'read_bytes', lambda p: b'{}\n' if p == victim else original(p)):
                with self.assertRaises(AssertionError): release.validate_release()

    def test_changed_metadata_or_version_fail(self):
        path = release.ROOT / 'docs/analytics-environment-poc/RELEASE_0_12_0.json'
        original = Path.read_text
        for field in ['files', 'archive', 'inputsSha256', 'sourceManifestSha256', 'reviewSha256', 'release']:
            value = json.loads(original(path)); value[field] = {} if isinstance(value[field], dict) else 'changed'
            with self.subTest(field=field), patch.object(Path, 'read_text', lambda p, *a, **k: json.dumps(value) if p == path else original(p, *a, **k)):
                with self.assertRaises(AssertionError): release.validate_release()
        with patch.object(Path, 'read_text', lambda p, *a, **k: '0.11.0\n' if p == release.ROOT / 'VERSION' else original(p, *a, **k)):
            with self.assertRaises(AssertionError): release.validate_release()


if __name__ == '__main__': unittest.main()
