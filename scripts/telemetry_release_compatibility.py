"""Keep historical byte checks against the exact archived pre-TLM Telemetry API."""
from pathlib import Path
import json
from telemetry_contract_validation import validate_release
from analytics_release_compatibility import prior_analytics, analytics_inventory
from environmental_release_compatibility import environmental_inventory
from m4_release_compatibility import prior_m4, m4_inventory

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / 'docs/telemetry-poc/RELEASE_0_10_0.json'


def prior_telemetry(path):
    if RELEASE.exists() and path == ROOT / 'openapi/telemetry-service.yaml':
        validate_release()
        return ROOT / 'docs/telemetry-poc/previous-0.9.0/openapi/telemetry-service.yaml'
    return prior_m4(prior_analytics(path))


def telemetry_inventory():
    if not RELEASE.exists():
        return set()
    validate_release()
    return {p for p in json.loads(RELEASE.read_text())['files']
            if p.startswith(('openapi/', 'events/', 'examples/'))} | analytics_inventory() | environmental_inventory() | m4_inventory()
