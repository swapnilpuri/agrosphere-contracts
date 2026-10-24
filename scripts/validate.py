"""Validate all schemas, examples, envelope constraints and OpenAPI placeholders offline."""
import copy
import json
from decimal import Decimal
from pathlib import Path
import yaml
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
from openapi_spec_validator import validate

ROOT = Path(__file__).resolve().parents[1]
schemas = [json.loads(p.read_text(), parse_float=Decimal) for p in (ROOT / "events/v1").glob("*.json")]
registry = Registry().with_resources((s["$id"], Resource.from_contents(s)) for s in schemas)
for schema in schemas:
    Draft202012Validator.check_schema(schema)
    if schema["title"].endswith("envelope v1"):
        continue
    validator = Draft202012Validator(schema, registry=registry, format_checker=FormatChecker())
    event = json.loads((ROOT / "examples" / (schema["title"] + ".json")).read_text(), parse_float=Decimal)
    validator.validate(event)
    invalids = []
    for key in ("eventId", "correlationId", "estateId", "payload"):
        bad = copy.deepcopy(event)
        del bad[key]
        invalids.append(bad)
    for key, value in (("eventId", "not-a-uuid"), ("source", "other-service"), ("unexpected", True), ("eventVersion", 2)):
        bad = copy.deepcopy(event)
        bad[key] = value
        invalids.append(bad)
    bad = copy.deepcopy(event)
    bad["payload"]["unexpected"] = True
    invalids.append(bad)
    assert all(not validator.is_valid(bad) for bad in invalids), schema["title"]
for file in (ROOT / "openapi").glob("*.yaml"):
    validate(yaml.safe_load(file.read_text()))
v2_count = 0
for file in (ROOT / "events/v2").glob("*.schema.json"):
    schema = json.loads(file.read_text(), parse_float=Decimal)
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    example = json.loads((ROOT / "examples/v2" / (file.name.replace(".schema", ""))).read_text(), parse_float=Decimal)
    validator.validate(example)
    for key in schema["required"]:
        bad = copy.deepcopy(example)
        del bad[key]
        assert not validator.is_valid(bad), key
    for key, value in (("eventVersion", 1), ("sourceService", "wrong"), ("estateId", "invalid"), ("unexpected", True)):
        bad = copy.deepcopy(example)
        bad[key] = value
        assert not validator.is_valid(bad), key
    v2_count += 1
# Optional actual serialized envelopes exported by EstateServiceIT.
import sys
for directory in sys.argv[1:]:
    for file in Path(directory).glob("*.json"):
        event = json.loads(file.read_text(), parse_float=Decimal)
        schema = json.loads((ROOT / "events/v2" / (event["eventType"] + ".schema.json")).read_text(), parse_float=Decimal)
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(event)
print(f"PASS: v1 compatibility, {v2_count} v2 schemas/examples and negative cases, all OpenAPI documents")

spatial_count = 0
for file in (ROOT / "events/spatial/v1").glob("*.schema.json"):
    schema = json.loads(file.read_text())
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    event = json.loads((ROOT / "examples/spatial/v1" / file.name.replace(".schema", "")).read_text())
    validator.validate(event)
    for key in schema["required"]:
        bad = copy.deepcopy(event)
        del bad[key]
        assert not validator.is_valid(bad), key
    spatial_count += 1
print(f"PASS: {spatial_count} spatial event schemas/examples and required-field negative cases")
