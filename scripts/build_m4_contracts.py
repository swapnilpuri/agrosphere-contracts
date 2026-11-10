"""Independent deterministic M4 read/closed-intent contract; no service-source dependency."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "docs/m4"
PATH = "/api/v1/ai/estates/{estateId}/blocks/{blockId}"
ID = {"type": "string", "format": "uuid"}
HASH = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
UTC = {"type": "string", "format": "date-time", "pattern": "Z$|\\+00:00$"}
DAY = {"type": "string", "format": "date"}
MASS = {"type": "string", "pattern": r"^-?(?:0|[1-9][0-9]*)\.[0-9]{3}$"}
METRIC = {"type": "string", "pattern": r"^(?:0|[1-9][0-9]*)\.[0-9]{6}$"}
TEXT = {"type": "string", "maxLength": 500}
COUNT = {"type": "integer", "minimum": 0, "maximum": 1000}
MODE = {"type": "string", "enum": ["GENERATED_POINT_IN_TIME", "LIVE_FIRST_RECEIPT"]}


def enum(*values):
    return {"type": "string", "enum": list(values)}


def obj(properties):
    return {"type": "object", "additionalProperties": False, "properties": properties, "required": list(properties)}


def nullable(schema):
    return {"anyOf": [schema, {"type": "null"}]}


def array(schema, maximum):
    return {"type": "array", "items": schema, "maxItems": maximum}


def ref(name):
    return {"$ref": "#/components/schemas/" + name}


def document():
    scope = obj({"estateId": ID, "blockId": ID})
    source = obj({"eventId": ID, "collectionId": ID, "version": {"type": "integer", "minimum": 0},
                  "bodyHash": HASH, "collectionDate": DAY, "sourceAt": UTC, "availableAt": UTC})
    model = obj({"algorithm": enum("WET_KG_MEAN_7_V1", "DRY_KG_MEAN_7_V1", "WET_KG_LAST_DAY_V1", "DRY_KG_LAST_DAY_V1"),
                 "target": enum("WET", "DRY"), "featurePolicy": enum("SOURCE_AND_AVAILABILITY_BEFORE_LOCAL_MIDNIGHT_V1"),
                 "labelPolicy": enum("AS_KNOWN_AT_NEXT_LOCAL_MIDNIGHT_V1"), "rounding": enum("SOURCE_ROUNDED_SUM_OUTPUT_HALF_UP_3_V1"),
                 "coverage": enum("OBSERVED_ONLY"), "uncertainty": enum("UNCALIBRATED"), "stage": enum("DEMO_ONLY"),
                 "windowDays": {"type": "integer", "enum": [1, 7]}, "policyVersion": enum("M4_BASELINES_V1"),
                 "anomalyPolicy": enum("ABSOLUTE_FROZEN_RESIDUAL_STRICT_GREATER_V1"), "thresholdKg": enum("1.000", "5.000")})
    target = obj({"target": enum("WET", "DRY"), "modelId": HASH, "comparatorModelId": HASH,
                  "status": enum("ELIGIBLE", "INSUFFICIENT_HISTORY", "INCOMPLETE_SOURCE", "PENDING_DRC"),
                  "predictedKg": nullable(MASS), "comparatorKg": nullable(MASS), "sources": array(ref("SourceRef"), 1000),
                  "anomalyStatus": enum("NOT_EVALUATED", "UNSCORED", "FLAGGED", "NOT_FLAGGED"),
                  "actualKg": nullable(MASS), "residualKg": nullable(MASS), "thresholdKg": enum("1.000", "5.000"),
                  "labelStatus": enum("NOT_EVALUATED", "ELIGIBLE", "INSUFFICIENT_HISTORY", "INCOMPLETE_SOURCE", "PENDING_DRC"),
                  "labelSources": array(ref("SourceRef"), 1000)})
    forecast = obj({"scope": ref("Scope"), "datasetId": HASH, "mode": MODE, "asOf": UTC,
                    "targetDate": DAY, "estateTimezone": TEXT, "labelAsOf": nullable(UTC),
                    "targets": {**array(ref("TargetResult"), 2), "minItems": 2},
                    "sourceDataProvenance": enum("SIMULATED"), "forecastProvenance": enum("PREDICTED"),
                    "coverage": enum("OBSERVED_ONLY"), "uncertainty": enum("UNCALIBRATED")})
    metric = obj({"target": enum("WET", "DRY"), "split": enum("TRAIN", "VALIDATION", "TEST"),
                  "algorithm": enum("MEAN_7", "LAST_DAY"), "scored": COUNT, "withheld": COUNT,
                  "sumAbsoluteErrorKg": MASS, "maeKg": nullable(METRIC),
                  "withheldReasons": array({"type": "array", "prefixItems": [TEXT, COUNT], "minItems": 2, "maxItems": 2}, 4)})
    confusion = obj({"target": enum("WET", "DRY"), "split": enum("TRAIN", "VALIDATION", "TEST"),
                     **{k: COUNT for k in ["truePositive", "falsePositive", "trueNegative", "falseNegative", "unscored"]},
                     "precision": nullable(METRIC), "recall": nullable(METRIC)})
    evaluation = obj({"evaluationId": HASH, "scope": ref("Scope"), "datasetId": HASH,
                      "sourceContracts": array({"type": "array", "prefixItems": [TEXT, HASH], "minItems": 2, "maxItems": 2}, 4),
                      "startDate": DAY, "endDate": DAY,
                      "splitBoundaries": array({"type": "array", "prefixItems": [TEXT, DAY, DAY], "minItems": 3, "maxItems": 3}, 3),
                      "models": array(ref("ModelRecord"), 4), "metrics": array(ref("Metric"), 12),
                      "anomalyCounts": array(ref("Confusion"), 6), "syntheticTruthHash": HASH,
                      "mode": enum("GENERATED_POINT_IN_TIME"), "splitPolicy": enum("FORWARD_7_28_14_14_NO_TUNING_V1"), "stage": enum("DEMO_ONLY")})
    request = obj({"intent": enum("PRODUCTION_SUMMARY", "FORECAST_EXPLANATION", "ANOMALY_EXPLANATION", "EVIDENCE_INSPECTION"),
                   "asOf": UTC, "labelAsOf": nullable(UTC), "mode": MODE, "datasetId": HASH,
                   "environmentFrom": nullable(UTC), "environmentTo": nullable(UTC)})
    evidence = obj({"kind": enum("PRODUCTION", "ENVIRONMENT", "MODEL", "FORECAST", "EVALUATION"), "id": TEXT,
                    "href": {"type": "string", "pattern": "^/api/v1/(ai|analytics)/", "maxLength": 1000}})
    assistant = obj({"scope": ref("Scope"), "provider": enum("DETERMINISTIC_EVIDENCE_V1"), "templateVersion": enum("M4_EVIDENCE_TEMPLATES_V1"),
                     "status": enum("ANSWERED", "PARTIAL", "REFUSED"), "intent": request["properties"]["intent"],
                     "statements": array(obj({"text": TEXT, "evidenceRefs": array(ref("EvidenceRef"), 50)}), 10),
                     "limitations": array(TEXT, 12)})
    schemas = dict(Scope=scope, SourceRef=source, TargetResult=target, Forecast=forecast, ModelRecord=model,
                   Metric=metric, Confusion=confusion, Evaluation=evaluation, AssistantRequest=request,
                   EvidenceRef=evidence, AssistantAnswer=assistant,
                   Problem=obj({"type": TEXT, "title": TEXT, "status": {"type": "integer", "enum": [400, 401, 403, 404, 409, 413, 429, 503]}, "detail": TEXT}))
    paths = {}
    for suffix, method, name in [("/production/baselines", "get", "Forecast"), ("/models/{modelId}", "get", "ModelRecord"),
                                  ("/evaluations/{evaluationId}", "get", "Evaluation"), ("/assistant", "post", "AssistantAnswer")]:
        parameters = [{"name": key, "in": "path", "required": True, "schema": ID} for key in ("estateId", "blockId")]
        for key in ("modelId", "evaluationId"):
            if "{" + key + "}" in suffix:
                parameters.append({"name": key, "in": "path", "required": True, "schema": HASH})
        if method == "get":
            query = {"datasetId": HASH}
            if name == "Forecast":
                query.update(asOf=UTC, mode=MODE, labelAsOf=UTC)
            parameters += [{"name": key, "in": "query", "required": key != "labelAsOf", "schema": value} for key, value in query.items()]
        responses = {str(code): {"description": "Successful scoped read" if code == 200 else "Bounded Problem Details",
                     "content": {"application/json" if code == 200 else "application/problem+json": {"schema": ref(name if code == 200 else "Problem")}}}
                     for code in (200, 400, 401, 403, 404, 409, 413, 429, 503)}
        operation = {"operationId": "read" + name, "parameters": parameters, "responses": responses,
                     "description": "SIMULATED only. Independent JWT then role/estate and active block validation before all evidence. Closed queries; no unknown or repeated query keys. Local-midnight cutoff and separate next-midnight label cutoff; generated availability is not historical receipt evidence."}
        if method == "post":
            operation["requestBody"] = {"required": True, "content": {"application/json": {"schema": ref("AssistantRequest")}}}
        paths[PATH + suffix] = {method: operation}
    return {"openapi": "3.1.0", "info": {"title": "AgroSphere bounded M4 AI", "version": "0.2.0"},
            "servers": [{"url": "https://api.agrosphere.invalid"}], "paths": paths, "security": [{"bearerAuth": []}],
            "components": {"securitySchemes": {"bearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}}, "schemas": schemas}}


def artifacts():
    return {"ai-service.openapi.json": (json.dumps(document(), indent=2) + "\n").encode()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    BASE.mkdir(parents=True, exist_ok=True)
    for name, content in artifacts().items():
        path = BASE / name
        if args.check:
            assert path.read_bytes() == content, name
        else:
            path.write_bytes(content)
    print("PASS: independent deterministic four-operation M4 contract" if args.check else "Generated isolated M4 API candidate")


if __name__ == "__main__":
    main()
