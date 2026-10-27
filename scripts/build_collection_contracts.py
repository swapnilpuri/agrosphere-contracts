"""Build the unreleased 3B candidate; --check verifies deterministic artifacts.

No version bump, publication or producer pin is performed. Legacy API members and
event files are protected separately by the committed compatibility baseline.
"""
import argparse
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "/api/v1/tapping/collections"
TIMESTAMP = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.[0-9]{1,6}0*)?(?:Z|[+-]\d{2}:\d{2})$"


def obj(properties, required=None, **kwargs):
    return dict(type="object", additionalProperties=False, properties=properties,
                required=list(properties) if required is None else required, **kwargs)


def text(limit=200):
    return dict(type="string", minLength=1, maxLength=limit, pattern=r"\S")


def nullable(schema):
    return {"anyOf": [schema, {"type": "null"}]}


def enum(*values):
    return dict(type="string", enum=list(values))


def integer(minimum=0):
    return dict(type="integer", format="int64", minimum=minimum, maximum=9223372036854775807)


def definitions(ref):
    uuid = dict(type="string", format="uuid")
    instant = dict(type="string", format="date-time", pattern=TIMESTAMP,
                   description="Explicit offset; exact microsecond representation. Extra trailing zeros permitted; nonzero digits beyond position six rejected.")
    utc = dict(instant, pattern=TIMESTAMP.replace("(?:Z|[+-]\\d{2}:\\d{2})$", "Z$"))
    date = dict(type="string", format="date")
    kg = dict(type="number", minimum=0.001, maximum=999999.999, multipleOf=0.001)
    percent = dict(type="number", minimum=0, maximum=100, multipleOf=0.01)
    mass = dict(type="number", minimum=0, multipleOf=0.001)
    provenance = enum("REAL", "SIMULATED")
    d = {}
    d["CollectionWeightEvidence"] = obj({"method": enum("SCALE", "MANUAL_ENTRY"),
        "sourceReference": text(), "instrumentReference": nullable(text())}, ["method", "sourceReference"])
    d["CollectionDrcInput"] = obj({"drcPercent": percent, "measuredAt": instant,
        "method": enum("LAB_REPORTED", "FIELD_TEST"), "sourceReference": text(),
        "dataProvenance": provenance, "sampleReference": nullable(text()),
        "instrumentReference": nullable(text())},
        ["drcPercent", "measuredAt", "method", "sourceReference", "dataProvenance"],
        allOf=[{"if": {"properties": {"method": {"const": "LAB_REPORTED"}}, "required": ["method"]},
                "then": {"required": ["sampleReference"], "properties": {"sampleReference": text()}}}])
    d["CollectionCreate"] = obj({"tappingRecordId": uuid,
        "collectionReference": dict(type="string", pattern=r"^\s*[A-Za-z0-9][A-Za-z0-9_-]{0,63}\s*$",
                                    description="Trim and uppercase ASCII before reference uniqueness and idempotency comparison."),
        "collectedAt": instant, "wetLatexKg": kg, "weightEvidence": ref("CollectionWeightEvidence"),
        "dataProvenance": provenance, "backdateReason": nullable(text(2000)),
        "replacementOfCollectionId": uuid},
        ["tappingRecordId", "collectionReference", "collectedAt", "wetLatexKg", "weightEvidence", "dataProvenance"])
    d["CollectionInitialDrcWrite"] = obj({"version": integer(), "measurement": ref("CollectionDrcInput")})
    d["CollectionCorrection"] = obj({"version": integer(), "reason": text(2000),
        "wetLatexKg": kg, "collectedAt": instant, "weightEvidence": ref("CollectionWeightEvidence"),
        "backdateReason": nullable(text(2000)), "replacementMeasurement": ref("CollectionDrcInput")},
        ["version", "reason"], anyOf=[{"required": [k]} for k in ["wetLatexKg", "collectedAt", "weightEvidence", "backdateReason", "replacementMeasurement"]],
        description="At least one actual change, or a replacement observation. Omission means unchanged; null only clears backdateReason when resulting date is not historical. Domain validation rejects no-op corrections.")
    d["CollectionVoid"] = obj({"version": integer(), "reason": text(2000)})
    measurement = copy.deepcopy(d["CollectionDrcInput"])
    measurement["properties"].update({"id": uuid, "collectionId": uuid, "introducedVersion": integer(1),
        "recordedAt": utc, "recordedBy": text()})
    measurement["properties"]["measuredAt"] = utc
    measurement["required"] = list(measurement["properties"])
    d["CollectionDrcMeasurementView"] = measurement
    weight = copy.deepcopy(d["CollectionWeightEvidence"])
    weight["required"] = list(weight["properties"])
    d["CollectionWeightEvidenceView"] = weight
    context = {k: uuid for k in ["id", "tappingRecordId", "assignmentId", "estateId", "blockId", "divisionIdSnapshot"]}
    context.update({"workerId": text(), "tappingDate": date, "estateTimezone": text(100),
        "estateVersionSnapshot": integer(), "blockVersionSnapshot": integer(), "masterValidatedAt": utc,
        "collectionReference": dict(type="string", pattern=r"^[A-Z0-9][A-Z0-9_-]{0,63}$"),
        "replacementOfCollectionId": nullable(uuid), "dataProvenance": provenance,
        "collectedAt": utc, "collectionDate": date, "wetLatexKg": kg,
        "weightEvidence": ref("CollectionWeightEvidenceView"), "backdateReason": nullable(text(2000)),
        "currentMeasurement": nullable(ref("CollectionDrcMeasurementView")),
        "status": enum("PENDING_DRC", "CALCULATED", "VOIDED"),
        "dryRubberExactKg": nullable(dict(type="number", minimum=0, maximum=999999.999, multipleOf=0.0000001)),
        "dryRubberKg": nullable(dict(mass, maximum=999999.999)),
        "calculationPolicy": nullable({"const": "DRC_KG_V1", "type": "string"}),
        "version": integer(), "createdAt": utc, "updatedAt": utc, "createdBy": text(), "updatedBy": text()})
    pending = {k: {"type": "null"} for k in ["currentMeasurement", "dryRubberExactKg", "dryRubberKg", "calculationPolicy"]}
    calculated = {k: {"not": {"type": "null"}} for k in pending}
    d["CollectionView"] = obj(context, allOf=[
        {"if": {"properties": {"status": {"const": "PENDING_DRC"}}}, "then": {"properties": pending}},
        {"if": {"properties": {"status": {"const": "CALCULATED"}}}, "then": {"properties": calculated}},
        {"if": {"properties": {"status": {"const": "VOIDED"}}},
         "then": {"anyOf": [{"properties": pending}, {"properties": calculated}]}}])
    d["CollectionAdjustmentView"] = obj({"id": uuid, "kind": enum("CORRECT", "VOID"),
        "beforeVersion": integer(), "afterVersion": integer(1), "reason": text(2000),
        "approvedAt": utc, "approvedBy": text(), "correlationId": uuid})
    d["CollectionHistoryEntry"] = obj({"collectionId": uuid, "version": integer(),
        "commandKind": enum("CREATE", "DRC", "CORRECT", "VOID"), "recordedAt": utc,
        "recordedBy": text(), "correlationId": uuid, "snapshot": ref("CollectionView"),
        "adjustment": nullable(ref("CollectionAdjustmentView"))})
    for name, entry in [("CollectionPage", "CollectionView"), ("CollectionHistoryPage", "CollectionHistoryEntry"),
                        ("CollectionDrcMeasurementPage", "CollectionDrcMeasurementView")]:
        d[name] = obj({"content": dict(type="array", items=ref(entry)), "page": integer(),
            "size": dict(type="integer", minimum=1, maximum=100), "totalElements": integer()})
    row = {"groupKey": nullable(text()), "dataProvenance": provenance}
    row.update({k: integer() for k in ["activeCollectionCount", "pendingDrcCount", "calculatedCollectionCount", "voidedCollectionCount"]})
    row.update({k: mass for k in ["totalWetLatexKg", "pendingWetLatexKg", "calculatedWetLatexKg", "knownDryRubberKg"]})
    row.update({"weightedDrcPercent": nullable(percent), "isComplete": dict(type="boolean")})
    d["CollectionSummaryRow"] = obj(row)
    d["CollectionSummary"] = obj({"groupBy": enum("total", "estate", "division", "block", "worker", "date"),
        "from": date, "to": date, "content": dict(type="array", items=ref("CollectionSummaryRow")),
        "page": integer(), "size": dict(type="integer", minimum=1, maximum=100), "totalElements": integer(),
        "aggregationPolicy": {"type": "string", "const": "SUM_ROUNDED_COLLECTION_KG_V1"}})
    return d


def add_operations(api):
    ref = lambda name: {"$ref": "#/components/schemas/" + name}
    defs = definitions(ref)
    api["components"]["schemas"].update(defs)
    def parameter(name, schema, where="query", required=False, **kwargs):
        return dict(name=name, schema=schema, **{"in": where}, required=required, **kwargs)
    page = [parameter("page", dict(type="integer", minimum=0, default=0)),
            parameter("size", dict(type="integer", minimum=1, maximum=100, default=20))]
    filters = [parameter(k, dict(type="string", format="uuid")) for k in ["estateId", "divisionId", "blockId", "tappingRecordId"]]
    filters += [parameter("workerId", text()), parameter("collectionReference", defs["CollectionCreate"]["properties"]["collectionReference"]),
                parameter("dataProvenance", enum("REAL", "SIMULATED"))]
    id_param = parameter("id", dict(type="string", format="uuid"), "path", True)
    key = parameter("Idempotency-Key", dict(type="string", format="uuid"), "header", True,
                    description="Durable actor/key receipt across write routes. Replay original success after current authorization; changed normalized command conflicts.")
    correlation = parameter("X-Correlation-ID", dict(type="string", format="uuid"), "header")
    error_text = {400:"Invalid input, precision, filter or lifecycle",401:"Invalid or absent JWT",403:"Role, estate or worker scope denied",404:"Unknown local reference",409:"Version, reference or idempotency conflict",422:"Invalid canonical master reference",503:"Unavailable or malformed master response",500:"Sanitized persistence failure; no partial commit"}
    entries = [
        ("", "post", "createLatexCollection", "CollectionCreate", "CollectionView"),
        ("", "get", "listLatexCollections", None, "CollectionPage"),
        ("/{id}", "get", "getLatexCollection", None, "CollectionView"),
        ("/{id}/history", "get", "getLatexCollectionHistory", None, "CollectionHistoryPage"),
        ("/{id}/drc-measurements", "get", "listDrcMeasurements", None, "CollectionDrcMeasurementPage"),
        ("/{id}/drc-measurements", "post", "recordDrcMeasurement", "CollectionInitialDrcWrite", "CollectionView"),
        ("/{id}/corrections", "post", "correctLatexCollection", "CollectionCorrection", "CollectionView"),
        ("/{id}/void", "post", "voidLatexCollection", "CollectionVoid", "CollectionView"),
        ("/summary", "get", "summarizeLatexCollections", None, "CollectionSummary")]
    for suffix, method, name, request, response in entries:
        params = [correlation] + ([id_param] if "{id}" in suffix else [])
        description = "Unknown request fields and unsupported filters rejected. Authorization applies before pagination/aggregation and receipt replay."
        description += {
            "createLatexCollection": " Worker: own execution in trusted estate; supervisor/management: scoped. Replacement requires manager/admin.",
            "recordDrcMeasurement": " Supervisor/management only, within trusted scope; workers/read-only roles denied.",
            "correctLatexCollection": " Estate manager/admin only, within trusted scope; no four-eyes workflow.",
            "voidLatexCollection": " Estate manager/admin only; terminal void retains evidence.",
        }.get(name, " Trusted estate reads; worker-only read policy also restricts execution worker. Global admins cross estates.")
        if request:
            params += [key]
            description += " Success is an immutable command receipt; GET returns current state. Non-create writes require observed version. No new event or revision on exact replay."
        if name in ["listLatexCollections", "summarizeLatexCollections"]:
            summary = name == "summarizeLatexCollections"
            params += copy.deepcopy(filters + page)
            params += [parameter(k, dict(type="string", format="date"), required=summary) for k in ["from", "to"]]
            description += " Dates are inclusive and ordered with difference <=366 days. Lists may omit both bounds, reject a single bound; summaries require both."
            if summary:
                params += [parameter("groupBy", dict(enum("total", "estate", "division", "block", "worker", "date"), default="total"))]
                description += " No status filter. Provenance always separates groups; weighted DRC measured-only. Sum per-lot rounded kg; pending coverage explicit."
            else:
                params += [parameter("status", enum("PENDING_DRC", "CALCULATED", "VOIDED"))]
        elif response.endswith("Page"):
            params += page
        status = "201" if name == "createLatexCollection" else "200"
        headers = {"X-Correlation-ID": {"schema": {"type": "string", "format": "uuid"}}}
        if status == "201":
            headers["Location"] = {"schema": {"type": "string"}, "description": BASE + "/{id}; preserved on replay"}
        responses = {status: {"description": "Command receipt" if request else "Authorized resource/query", "headers": headers,
                               "content": {"application/json": {"schema": ref(response)}}}}
        for code, detail in error_text.items():
            responses[str(code)] = {"description": detail, "content": {"application/problem+json": {"schema": ref("ProblemDetail")}}}
        operation = dict(tags=["latex-collections"], operationId=name, security=[{"bearerAuth": []}],
                         description=description, parameters=params, responses=responses)
        if name in ["listLatexCollections", "summarizeLatexCollections"]:
            operation["x-query-constraints"] = {"dateBounds": "both-required" if name == "summarizeLatexCollections" else "both-or-neither",
                                                "maximumDateDifferenceDays": 366, "unknownFilters": "reject"}
        if request:
            operation["requestBody"] = {"required": True, "content": {"application/json": {"schema": ref(request)}}}
        api["paths"].setdefault(BASE + suffix, {})[method] = operation


def event_schema(name):
    ref = lambda n: {"$ref": "#/$defs/" + n}
    defs = definitions(ref)
    version = {"type": "integer", "const": 0} if name == "LatexCollectionRecorded" else integer(1)
    payload = {"collection": ref("CollectionView")}
    if name == "LatexCollectionRecorded":
        payload["reason"] = nullable(text(2000))
    elif name == "DrcMeasurementRecorded":
        payload["measurementId"] = dict(type="string", format="uuid")
    else:
        payload.update(previousVersion=integer(), adjustment=ref("CollectionAdjustmentView"))
    status = {"LatexCollectionRecorded": ["PENDING_DRC"], "DrcMeasurementRecorded": ["CALCULATED"],
              "LatexCollectionAdjusted": ["PENDING_DRC", "CALCULATED"], "LatexCollectionVoided": ["VOIDED"]}[name]
    schema = obj({"eventId": dict(type="string", format="uuid"), "eventType": {"type": "string", "const": name},
        "eventVersion": {"type": "integer", "const": 2},
        "timestamp": dict(type="string", format="date-time", pattern=TIMESTAMP.replace("(?:Z|[+-]\\d{2}:\\d{2})$", "Z$")),
        "source": {"type": "string", "const": "agrosphere-operations-service"},
        "correlationId": dict(type="string", format="uuid"), "estateId": dict(type="string", format="uuid"),
        "blockId": dict(type="string", format="uuid"), "dataProvenance": enum("REAL", "SIMULATED"),
        "aggregateId": dict(type="string", format="uuid"), "aggregateVersion": version,
        "payload": obj(payload)},
        **{"$schema": "https://json-schema.org/draft/2020-12/schema",
           "$id": "https://schemas.agrosphere.invalid/operations/v2/" + name + ".schema.json",
           "title": name, "$defs": defs})
    schema["properties"]["payload"]["properties"]["collection"] = {"allOf": [ref("CollectionView"),
        {"properties": {"status": enum(*status)}}]}
    if name in ["LatexCollectionAdjusted", "LatexCollectionVoided"]:
        payload_schema = schema["properties"]["payload"]["properties"]
        payload_schema["adjustment"] = {"allOf": [ref("CollectionAdjustmentView"),
            {"properties": {"kind": {"const": "CORRECT" if name.endswith("Adjusted") else "VOID"}}}]}
    return schema


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    api_path = ROOT / "openapi/operations-service.yaml"
    api = json.loads(api_path.read_text())
    add_operations(api)
    artifacts = {api_path: api}
    for name in ["LatexCollectionRecorded", "DrcMeasurementRecorded", "LatexCollectionAdjusted", "LatexCollectionVoided"]:
        artifacts[ROOT / "events/operations/v2" / (name + ".schema.json")] = event_schema(name)
    for file, content in artifacts.items():
        # YAML 1.1 loaders interpret JSON's bare exponent form as a string.
        serialized = json.dumps(content, indent=2).replace("1e-07", "0.0000001") + "\n"
        if args.check:
            assert file.read_text() == serialized, f"Generated contract drift: {file}"
        else:
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(serialized, encoding="utf-8")
    print(f"PASS: {'checked' if args.check else 'built'} five collection candidate artifacts (unreleased)")


if __name__ == "__main__":
    main()
