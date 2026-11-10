"""M4 exact local release and preserved pre-M4 placeholder/version."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "docs/m4"


def validate_release():
    release = BASE / "RELEASE_0_13_0.json"
    if not release.exists():
        return
    r = json.loads(release.read_text())
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    assert r["release"] == "0.13.0" and (ROOT / "VERSION").read_text().strip() == "0.13.0"
    assert r["manifestSha256"] == sha(BASE / "MANIFEST.json")
    assert r["engineeringReviewSha256"] == sha(BASE / "ENGINEERING_REVIEW.md")
    m = json.loads((BASE / "MANIFEST.json").read_text())
    assert r["files"] == {"openapi/ai-service.yaml": m["candidate"]["ai-service.openapi.json"],
                         **{"examples/ai/v1/" + k: v for k, v in m["examples"].items()}}
    assert r["archive"] == {"docs/m4/previous-0.12.0/" + k: v for k, v in m["previous"].items()}
    for name, digest in m["candidate"].items():
        assert sha(BASE / name) == digest, name
    for name, digest in m["examples"].items():
        assert sha(BASE / "examples" / name) == digest, name
    for name, digest in {**r["files"], **r["archive"], **m["unchangedInputs"]}.items():
        assert sha(ROOT / name) == digest, name


def prior_m4(path):
    if (BASE / "RELEASE_0_13_0.json").exists() and path == ROOT / "openapi/ai-service.yaml":
        validate_release()
        return BASE / "previous-0.12.0/openapi/ai-service.yaml"
    return path


def m4_inventory():
    if not (BASE / "RELEASE_0_13_0.json").exists():
        return set()
    validate_release()
    return set(json.loads((BASE / "RELEASE_0_13_0.json").read_text())["files"])
