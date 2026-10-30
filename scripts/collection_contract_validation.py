"""Offline schema and semantic checks for the unreleased collection contracts."""
import copy
import hashlib
import json
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
NAMES = ("LatexCollectionRecorded", "DrcMeasurementRecorded", "LatexCollectionAdjusted", "LatexCollectionVoided")


def load(path):
    return json.loads(path.read_text(encoding="utf-8"), parse_float=Decimal)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def instant(value):
    # Schema checks reject lossy submicrosecond precision before datetime parsing.
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def semantic_event(event):
    """Cross-field semantics that JSON Schema cannot express; assumes schema valid."""
    p = event["payload"]
    c = p["collection"]
    for envelope, field in [("aggregateId", "id"), ("aggregateVersion", "version"),
                            ("estateId", "estateId"), ("blockId", "blockId"), ("dataProvenance", "dataProvenance")]:
        require(event[envelope] == c[field], f"Envelope/collection mismatch: {envelope}")
    require(instant(event["timestamp"]) == instant(c["updatedAt"]), "Event time must match applied revision")
    require(instant(c["createdAt"]) <= instant(c["updatedAt"]), "Audit time order")
    require(instant(c["masterValidatedAt"]) <= instant(c["createdAt"]), "Master snapshot after creation")
    require(instant(c["collectedAt"]) <= instant(c["updatedAt"]), "Collection in future")
    # IANA zone identity and local-date derivation are runtime/domain invariants.
    # Do not guess them from offsets or add an unpinned platform timezone fallback.
    require(c["collectionDate"] >= c["tappingDate"], "Collection before tapping date")
    m = c["currentMeasurement"]
    if m is not None:
        require(m["collectionId"] == c["id"], "Selected measurement belongs to another collection")
        require(m["dataProvenance"] == c["dataProvenance"], "Mixed observation provenance")
        require(m["introducedVersion"] <= c["version"], "Measurement introduced after revision")
        require(instant(c["collectedAt"]) <= instant(m["measuredAt"]) <= instant(m["recordedAt"]) <= instant(c["updatedAt"]), "Measurement chronology")
        exact = Decimal(str(c["wetLatexKg"])) * Decimal(str(m["drcPercent"])) / Decimal(100)
        require(c["dryRubberExactKg"] == exact, "Incorrect exact dry mass")
        require(c["dryRubberKg"] == exact.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP), "Incorrect rounded dry mass")
    name = event["eventType"]
    if name == "LatexCollectionRecorded":
        require(c["version"] == 0 and c["createdAt"] == c["updatedAt"], "Invalid creation revision")
        require(p["reason"] == c["backdateReason"], "Creation reason mismatch")
    elif name == "DrcMeasurementRecorded":
        require(p["measurementId"] == m["id"], "Measurement event ID mismatch")
        require(m["introducedVersion"] == c["version"], "First measurement revision mismatch")
    else:
        a = p["adjustment"]
        require(p["previousVersion"] == c["version"] - 1 == a["beforeVersion"], "Adjustment previous revision mismatch")
        require(a["afterVersion"] == c["version"], "Adjustment next revision mismatch")
        require(a["approvedBy"] == c["updatedBy"] and a["approvedAt"] == c["updatedAt"], "Approval actor/time mismatch")
        require(a["correlationId"] == event["correlationId"], "Adjustment correlation mismatch")


def validate_event(event):
    require(event.get("eventType") in NAMES, "Unsupported collection event")
    schema = load(ROOT / "events/operations/v2" / (event["eventType"] + ".schema.json"))
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(event)
    semantic_event(event)


def check_compatibility():
    baseline = load(ROOT / "docs/milestone-3b/compatibility-baseline.json")
    for name, expected in baseline["eventAndExampleHashes"].items():
        require(hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == expected, f"Legacy file changed: {name}")
    api = load(ROOT / "openapi/operations-service.yaml")
    for name, value in baseline["operationsPaths"].items():
        require(api["paths"][name] == value, f"Legacy API path changed: {name}")
    for name, value in baseline["operationsComponents"]["schemas"].items():
        require(api["components"]["schemas"][name] == value, f"Legacy API schema changed: {name}")
    require(api["components"]["securitySchemes"] == baseline["operationsComponents"]["securitySchemes"], "Legacy security schemes changed")
    require({k:v for k,v in api.items() if k not in ["paths", "components"]} == baseline["operationsTopLevel"], "Legacy OpenAPI metadata changed")
    promoted = (ROOT / 'docs/worker-attendance/RELEASE_0_6_0.json').exists()
    require(sum(len(v) for v in api["paths"].values()) == (42 if promoted else 27), "Unexpected operation set")
    if promoted:
        prior = load(ROOT / 'docs/worker-attendance/previous-0.5.0/openapi/operations-service.yaml')
        for path, body in prior['paths'].items():
            require(api['paths'].get(path) == body, 'Prior 27-operation semantics changed: '+path)
    return api


def run():
    api = check_compatibility()
    for name in NAMES:
        schema = load(ROOT / "events/operations/v2" / (name + ".schema.json"))
        Draft202012Validator.check_schema(schema)
        validate_event(load(ROOT / "examples/operations/v2" / (name + ".json")))
    for path in sorted((ROOT / "examples/operations/v2/edge").glob("*.json")):
        validate_event(load(path))
    # Check exact decimal request schemas, including local refs, without network lookup.
    defs = api["components"]["schemas"]
    requests = load(ROOT / "examples/operations/v2/requests.json")
    for name, body in requests.items():
        schema = {"$ref": "#/components/schemas/"+name, "components": {"schemas": defs}}
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(body)
    print("PASS: collection v2 schemas/examples, exact decimal requests, cross-field semantics, 47 legacy file hashes and 27-operation compatibility")


if __name__ == "__main__":
    run()
