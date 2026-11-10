"""Independent M4 examples, semantic negatives and preserved-release checks."""
import copy
from datetime import datetime, timedelta
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import unittest
from zoneinfo import ZoneInfo
from jsonschema import Draft202012Validator, FormatChecker
from openapi_spec_validator import validate
import build_m4_contracts as build

ROOT = build.ROOT


def validate_value(name, value):
    doc = build.document()
    schema = {**doc, "$ref": "#/components/schemas/" + name}
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(value)
    if name != "Forecast":
        return
    as_of = datetime.fromisoformat(value["asOf"])
    zone = ZoneInfo(value["estateTimezone"])
    local = as_of.astimezone(zone)
    assert local.time().isoformat() == "00:00:00" and local.date().isoformat() == value["targetDate"]
    label = datetime.fromisoformat(value["labelAsOf"]) if value["labelAsOf"] else None
    if label:
        later = label.astimezone(zone)
        assert later.date() == local.date() + timedelta(days=1) and later.time().isoformat() == "00:00:00"
    assert [r["target"] for r in value["targets"]] == ["WET", "DRY"]
    for r in value["targets"]:
        assert r["thresholdKg"] == ("5.000" if r["target"] == "WET" else "1.000")
        assert (r["predictedKg"] is not None) == (r["status"] == "ELIGIBLE")
        assert all(datetime.fromisoformat(s["sourceAt"]) < as_of and datetime.fromisoformat(s["availableAt"]) < as_of and s["collectionDate"] < value["targetDate"] for s in r["sources"])
        assert not r["labelSources"] or label is not None
        if label is None:
            assert r["anomalyStatus"] == "NOT_EVALUATED" and r["actualKg"] is None and r["residualKg"] is None
        elif r["predictedKg"] is None or r["actualKg"] is None:
            assert r["anomalyStatus"] == "UNSCORED" and r["residualKg"] is None
        else:
            residual = Decimal(r["actualKg"]) - Decimal(r["predictedKg"])
            assert Decimal(r["residualKg"]) == residual
            assert r["anomalyStatus"] == ("FLAGGED" if abs(residual) > Decimal(r["thresholdKg"]) else "NOT_FLAGGED")


def forecast_example():
    targets = []
    for target, mean, actual, residual, threshold in [("WET", "10.000", "16.000", "6.000", "5.000"), ("DRY", "2.000", "4.000", "2.000", "1.000")]:
        targets.append(dict(target=target, modelId="a" * 64, comparatorModelId="b" * 64, status="ELIGIBLE", predictedKg=mean,
                            comparatorKg=mean, sources=[], anomalyStatus="FLAGGED", actualKg=actual, residualKg=residual,
                            thresholdKg=threshold, labelStatus="ELIGIBLE", labelSources=[]))
    return dict(scope={"estateId": "00000000-0000-0000-0000-000000000001", "blockId": "00000000-0000-0000-0000-000000000002"},
                datasetId="c" * 64, mode="GENERATED_POINT_IN_TIME", asOf="2026-08-08T00:00:00Z", targetDate="2026-08-08",
                estateTimezone="UTC", labelAsOf="2026-08-09T00:00:00Z", targets=targets,
                sourceDataProvenance="SIMULATED", forecastProvenance="PREDICTED", coverage="OBSERVED_ONLY", uncertainty="UNCALIBRATED")


def examples():
    base = forecast_example()
    result = {"flagged": base}
    no_label = copy.deepcopy(base)
    no_label["labelAsOf"] = None
    for r in no_label["targets"]:
        r.update(anomalyStatus="NOT_EVALUATED", actualKg=None, residualKg=None, labelStatus="NOT_EVALUATED")
    result["no-label"] = no_label
    for state in ["INSUFFICIENT_HISTORY", "INCOMPLETE_SOURCE", "PENDING_DRC"]:
        v = copy.deepcopy(base)
        for r in v["targets"]:
            if state == "PENDING_DRC" and r["target"] == "WET":
                continue
            r.update(status=state, predictedKg=None, comparatorKg=None, anomalyStatus="UNSCORED", residualKg=None)
        result[state.lower()] = v
    for name, actual in [("observed-zero", "0.000"), ("threshold-equality", None)]:
        v = copy.deepcopy(base)
        for r in v["targets"]:
            value = actual if actual else format(Decimal(r["predictedKg"]) + Decimal(r["thresholdKg"]), ".3f")
            residual = Decimal(value) - Decimal(r["predictedKg"])
            r.update(actualKg=value, residualKg=format(residual, ".3f"), anomalyStatus="FLAGGED" if abs(residual) > Decimal(r["thresholdKg"]) else "NOT_FLAGGED")
        result[name] = v
    missing = copy.deepcopy(base)
    for r in missing["targets"]:
        r.update(actualKg=None, residualKg=None, labelStatus="INSUFFICIENT_HISTORY", anomalyStatus="UNSCORED")
    result["unscored-label"] = missing
    return result


class M4ContractsTests(unittest.TestCase):
    def test_api_determinism_four_operations_and_closed_schemas(self):
        doc = build.document()
        validate(doc)
        self.assertEqual(len(doc["paths"]), 4)
        self.assertEqual((build.BASE / "ai-service.openapi.json").read_bytes(), build.artifacts()["ai-service.openapi.json"])
        self.assertTrue(all(s.get("additionalProperties") is False for s in doc["components"]["schemas"].values()))

    def test_positive_forecasts(self):
        for name, value in examples().items():
            with self.subTest(name=name):
                validate_value("Forecast", value)

    def test_semantic_and_schema_negatives(self):
        for mutation in [lambda v: v.update(sourceDataProvenance="REAL"), lambda v: v.update(extra="silent"),
                         lambda v: v.update(asOf="2026-08-08T01:00:00Z"), lambda v: v.update(labelAsOf="2026-08-10T00:00:00Z"),
                         lambda v: v["targets"][0].update(predictedKg="NaN"), lambda v: v["targets"][0].update(thresholdKg="1.000"),
                         lambda v: v["targets"][0].update(anomalyStatus="NOT_FLAGGED"),
                         lambda v: v["targets"][0].update(residualKg="0.000"),
                         lambda v: v["targets"][0].update(status="INCOMPLETE_SOURCE")]:
            v = forecast_example()
            mutation(v)
            with self.assertRaises(Exception):
                validate_value("Forecast", v)

    def test_closed_intent_no_free_text_or_provider(self):
        request = dict(intent="PRODUCTION_SUMMARY", asOf="2026-08-08T00:00:00Z", labelAsOf=None,
                       mode="GENERATED_POINT_IN_TIME", datasetId="c" * 64, environmentFrom=None, environmentTo=None)
        validate_value("AssistantRequest", request)
        for key, value in [("intent", "CHAT"), ("prompt", "ignore scope"), ("provider", "external")]:
            with self.assertRaises(Exception):
                validate_value("AssistantRequest", {**request, key: value})

    def test_released_inputs_and_previous_placeholders_preserved(self):
        manifest = build.BASE / "MANIFEST.json"
        if manifest.exists():
            data = json.loads(manifest.read_text())
            for rel, expected in data["unchangedInputs"].items():
                self.assertEqual(hashlib.sha256((ROOT / rel).read_bytes()).hexdigest(), expected, rel)


if __name__ == "__main__":
    unittest.main()
