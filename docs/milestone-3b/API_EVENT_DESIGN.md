# Milestone 3B — Proposed REST and event contract specification

Status: ACCEPTED wire design by project owner, 2026-10-27, with R01/R02; see [owner approval record](../../../agrosphere-architecture/docs/milestones/MILESTONE_3B_APPROVAL.md). Executable contract authoring, validation, independent review and release gates remain outstanding. This document is not a released OpenAPI or JSON Schema artifact. Existing OpenAPI, examples, VERSION, pinned copies and every released schema remain unchanged. It defines the additions authorized for T01 authoring after T00 baseline completion; design approval does not publish or validate executable artifacts. Business policy, persistence and review decisions are in [Architecture design](../../../agrosphere-architecture/docs/milestones/MILESTONE_3B_DESIGN.md) and [requirements](../../../agrosphere-architecture/docs/milestones/MILESTONE_3B_REQUIREMENTS.md).

## REST operations

Base /api/v1/tapping/collections deliberately reuses the existing authenticated Gateway route /api/v1/tapping/**. URI API v1 remains additive; this is independent of event v2. All operations require bearerAuth; issuer/signature/lifetime and operations-service audience are checked in Operations. Current identity realm supplies Estate audience for delegated validation. Correlation request/response X-Correlation-ID retains existing UUID semantics. JSON request content type application/json. Writes require UUID Idempotency-Key header, with observed nonnegative version in every non-create body. No If-Match/ETag concurrency convention is introduced.

| Method/path relative to base | operationId | Request | Success |
|---|---|---|---|
| POST / | createLatexCollection | CollectionCreate | 201 CollectionView and Location=base/{id} |
| GET / | listLatexCollections | CollectionFilter | 200 CollectionPage |
| GET /{id} | getLatexCollection | UUID id | 200 CollectionView |
| GET /{id}/history | getLatexCollectionHistory | UUID id, page/size | 200 CollectionHistoryPage |
| GET /{id}/drc-measurements | listDrcMeasurements | UUID id, page/size | 200 DrcMeasurementPage |
| POST /{id}/drc-measurements | recordDrcMeasurement | InitialDrcWrite | 200 CollectionView |
| POST /{id}/corrections | correctLatexCollection | CollectionCorrection | 200 CollectionView |
| POST /{id}/void | voidLatexCollection | CollectionVoid | 200 CollectionView |
| GET /summary | summarizeLatexCollections | SummaryFilter | 200 CollectionSummary |

Define /summary as a literal route; do not attempt UUID conversion before route selection. id is canonical UUID; no DELETE/PUT/generic PATCH or bulk import. Corrections are approved/applied atomically by manager authorization, not queued review requests. An idempotent replay returns original success status/body/Location even if current root changed; GET is the current resource. A new key after a first DRC cannot append another initial measurement: use corrections.

## Shared types and request shapes

All newly defined objects are closed (additionalProperties=false) except established ProblemDetail. Required fields must not be null; optional text may be absent or null. Trim reason/evidence/reference text before nonblank validation; preserve meaningful content. UUIDs remain UUID strings; worker/actor IDs are opaque signed sub strings of length 1..200, not necessarily UUIDs. Timestamp input requires an explicit offset and exact microsecond representability (R01): digits after the sixth fractional position must all be zero. Extra trailing zeros may be normalized without loss; any nonzero digit beyond the sixth position is rejected. Responses are UTC Z. Dates use ISO date; monetary/float formatting is irrelevant. Decimal fields are JSON number with OpenAPI type number (no float/double format), kg multipleOf 0.001, DRC multipleOf 0.01; decode directly to BigDecimal. Do not pass through binary floating point. Precision/range validation uses mathematical decimal value; trailing zero normalization is allowed.

| Shape | Fields |
|---|---|
| WeightEvidence | Required method enum SCALE/MANUAL_ENTRY, sourceReference string 1..200; optional instrumentReference string 1..200. MANUAL_ENTRY documents transcription, not an invented observation. |
| DrcInput | Required drcPercent number 0..100 inclusive / max 2 decimal places, measuredAt timestamp, method enum LAB_REPORTED/FIELD_TEST, sourceReference string 1..200, dataProvenance REAL/SIMULATED; optional sampleReference/instrumentReference string 1..200. LAB_REPORTED requires sampleReference. No certification flag. |
| CollectionCreate | Required tappingRecordId UUID, collectionReference string pattern [A-Z0-9][A-Z0-9_-]{0,63} after trim/uppercase normalization, collectedAt timestamp, wetLatexKg number 0.001..999999.999 / max 3 decimal places, weightEvidence, dataProvenance REAL/SIMULATED; optional backdateReason string 1..2000, replacementOfCollectionId UUID. No DRC or client actor/estate/block/worker/date/derived output fields. |
| InitialDrcWrite | Required version integer int64 >=0 and measurement DrcInput. |
| CollectionCorrection | Required version integer int64 >=0, reason string 1..2000; optional wetLatexKg, collectedAt, weightEvidence, backdateReason, replacementMeasurement DrcInput. At least one permitted field must actually change or a replacement measurement must be supplied; null cannot erase required values/evidence. No arbitrary JSON Patch. Identity/provenance/attribution/reference cannot be corrected. |
| CollectionVoid | Required version integer int64 >=0, reason string 1..2000. |

For optional correction fields: omission means unchanged. Null is accepted only for backdateReason if the resulting collection date is not historical; required source/input fields reject null, including replacementMeasurement. A replacement measurement is a new declared observation/evidence record even if percent matches the old value. Reason is mandatory for every correction. First DRC must match collection provenance and its chronology; initial requests cannot batch-create collection plus DRC. Precision violations are 400 rather than rounding input. All date/source/business checks apply equally to corrections.

Synthetic request examples (illustrations, not approval or runtime evidence):

~~~json
{
  "tappingRecordId": "00000000-0000-0000-0000-000000000301",
  "collectionReference": "LOT-01",
  "collectedAt": "2026-10-27T10:00:00+05:30",
  "wetLatexKg": 125.500,
  "weightEvidence": {"method": "SCALE", "sourceReference": "SIMULATED-WEIGH-01"},
  "dataProvenance": "SIMULATED"
}
~~~

~~~json
{
  "version": 0,
  "measurement": {
    "drcPercent": 32.40,
    "measuredAt": "2026-10-27T12:00:00+05:30",
    "method": "FIELD_TEST",
    "sourceReference": "SIMULATED-TEST-01",
    "dataProvenance": "SIMULATED"
  }
}
~~~

## Response shapes

CollectionView requires every listed property; nullable properties are emitted explicitly as null. New objects use camelCase consistently.

- Identity/context: id, tappingRecordId, assignmentId, estateId, blockId, divisionIdSnapshot (UUIDs); workerId, tappingDate; estateTimezone; estateVersionSnapshot, blockVersionSnapshot (int64 >=0); masterValidatedAt; collectionReference; replacementOfCollectionId (nullable UUID); dataProvenance.
- Observation: collectedAt, collectionDate, wetLatexKg, weightEvidence, backdateReason (nullable string); currentMeasurement (nullable DrcMeasurementView).
- Calculation: status PENDING_DRC/CALCULATED/VOIDED; dryRubberExactKg (nullable number, scale 7); dryRubberKg (nullable number, scale 3); calculationPolicy (nullable literal DRC_KG_V1).
- Audit/concurrency: version (int64 >=0), createdAt, updatedAt, createdBy, updatedBy.

DrcMeasurementView requires id, collectionId, introducedVersion (int64 >=1), drcPercent, measuredAt, method, sourceReference, sampleReference (nullable), instrumentReference (nullable), dataProvenance, recordedAt, recordedBy. It contains no mutable current flag: selection comes from CollectionView.currentMeasurement.id. A historical measurement can remain valid evidence without being selected. Pending view has null measurement and calculation outputs. Voided view retains the previous measurement/calculation state; void status controls contribution.

CollectionHistoryEntry requires collectionId, version, commandKind CREATE/DRC/CORRECT/VOID, recordedAt, recordedBy, correlationId, snapshot CollectionView and adjustment (nullable AdjustmentView). AdjustmentView requires id, kind CORRECT/VOID, beforeVersion, afterVersion, reason, approvedAt, approvedBy, correlationId. History uses one entry per version, never duplicates snapshot fields through flattened ambiguous merges. Command result cache and internal request hash are not exposed through history. Read roles are the same as collection reads; source references are authorized evidence, never bearer secrets.

New page shapes use content array, page (>=0), size (1..100), totalElements (int64 >=0). Stable root ordering collectedAt DESC,id ASC; history version ASC; measurements introducedVersion ASC,id ASC. Paging uses a single scoped SQL snapshot per request, not a guaranteed stable traversal during concurrent corrections. Summary ordering is group key ASC then provenance ASC. Audit pagination must not alter totals. No result exposes references/rows outside authorized scope.

## Filters and summary

CollectionFilter: optional collectionReference (exact normalized reference), estateId/divisionId/blockId/tappingRecordId UUID, workerId string, from/to inclusive collectionDate, status enum, dataProvenance enum; page default 0, size default 20/max100. If one of from/to is supplied both are required, from <= to and DAYS.between(from,to)<=366 (at most 367 inclusive dates, matching the 3A interval convention). List may omit both dates. Snapshot division is used. Histories accept page/size only.

SummaryFilter: same scope/reference/worker/provenance filters, required from/to with the same bound; groupBy enum total/estate/division/block/worker/date default total, page/size as above; status filter not supported because pending coverage and void counts are part of the result. Reject unsupported filter names in new endpoints. Validate explicit filters against authorization; an unauthorized estate/worker request is 403, not a global scan. Block/division filters only narrow authorized root snapshots; no live hierarchy lookup alters historical totals.

CollectionSummary requires groupBy, from, to, content array of SummaryRow, page, size, totalElements (group count before pagination), aggregationPolicy literal SUM_ROUNDED_COLLECTION_KG_V1. A total query has one row per requested provenance or both REAL/SIMULATED if no provenance filter, including zero-valued rows. SummaryRow requires groupKey (nullable string: null for total; UUID string for estate/division/block; subject for worker; date for date), dataProvenance, activeCollectionCount, pendingDrcCount, calculatedCollectionCount, voidedCollectionCount (nonnegative int64); totalWetLatexKg, pendingWetLatexKg, calculatedWetLatexKg, knownDryRubberKg (nonnegative decimal scale 3); weightedDrcPercent (nullable decimal scale 2); isComplete boolean. Kg summary values have arbitrary decimal magnitude subject to operational DB capacity; do not cap sums at the individual collection maximum. No grand total merges different provenances.

## Error and replay contracts

Retain application/problem+json with existing ProblemDetail status/title/detail/type/instance behavior and correlationId extension. New explanatory details must not contain other actors' idempotency results, dependency payloads, credentials or SQL. 400: syntax/unknown fields, scale/range, absent Idempotency-Key, chronology, unsupported state, forbidden immutable-field correction. 401: missing/invalid token. 403: valid token denied role/estate/worker or delegated master read. 404: missing local execution/root/replacement. 409: stale version, permanent duplicate reference, actor/key with different normalized command, bounded concurrent-command lock timeout. 422: canonical master absent/inactive/nonrubber/wrong ownership. 503: bounded dependency timeout, malformed required master metadata or unexpected response. Unexpected persistence failures return the existing sanitized 5xx boundary and roll back; do not expose database internals. Auth errors need not include a domain body.

Only successful command responses are persisted. Same actor/key/normalized request replays original result after current permission check and before stale-version/state checks; different body/method/path/version conflicts. Different actor uses a separate key namespace but cannot bypass permanent reference uniqueness. Never regenerate a key after ambiguous response. Subsequent GET returns current state even if a replay returns an older version. Replays carry a current request correlation header; event/revision correlations remain original. Create conflicts can be reconciled using scoped tappingRecordId and collectionReference; do not expose cross-estate duplicate payloads.

## Event schemas, versions and compatibility

Foundation events/v1/LatexCollectionRecorded.schema.json has eventVersion=1, source=operations-service, required nonnullable drcPercent, no execution/history/concurrency context. It cannot express pending collections. Preserve its bytes and example. Preserve all six Operations v1 tapping schemas and routes. Introduce the collection family in events/operations/v2 with eventVersion=2 and examples/operations/v2. Independent Contracts release candidate 0.5.0 must be reviewed; runtime pin follows that independent release, never sibling file dependencies. Do not advertise this documentation as that release or bump VERSION here.

All four new envelopes are closed objects requiring: eventId UUID; eventType literal; eventVersion literal 2; timestamp UTC server instant of applied command; source literal agrosphere-operations-service; correlationId UUID; estateId/blockId UUID; dataProvenance REAL/SIMULATED; aggregateId UUID = collection id; aggregateVersion int64 >=0; payload object below. No envelope rename to occurredAt/sourceService. Transport tracing stays outside JSON. Each schema is self-contained for pinning/offline validation; snapshots follow CollectionView with required nullable properties. Envelope and payload identity/provenance/version equivalence are semantic application/validator checks in addition to JSON Schema.

| Event/schema filename | Trigger / version | Required payload (closed object) | Routing on durable agrosphere.domain |
|---|---|---|---|
| LatexCollectionRecorded.schema.json | Create / aggregateVersion=0 | collection CollectionView PENDING_DRC; reason nullable string (backdateReason or null) | agrosphere.LatexCollectionRecorded.v2 |
| DrcMeasurementRecorded.schema.json | First DRC / version>=1 | collection CALCULATED; measurementId UUID equals current measurement | agrosphere.DrcMeasurementRecorded.v2 |
| LatexCollectionAdjusted.schema.json | Manager correction / version>=1 | collection current pending/calculated; previousVersion int64 = version-1; adjustment AdjustmentView matching versions | agrosphere.LatexCollectionAdjusted.v2 |
| LatexCollectionVoided.schema.json | Void / version>=1 | collection VOIDED; previousVersion int64 = version-1; adjustment AdjustmentView kind VOID | agrosphere.LatexCollectionVoided.v2 |

One event per command/revision (correction with replacement DRC emits Adjusted only). Events contain full post-command snapshot so correction, date movement and void reconcile deterministically. Old input revisions remain in authorized history; future consumers retain their own previous projection row to reverse old grouping contribution. Do not dual-publish legacy v1 collection messages or invent DRC to satisfy them. Existing legacy consumers require explicit migration to the v2 key; new collection routes are not enabled until v2 schemas and producer pins are available.

Events are written with the state/revision/idempotency result in the same local transaction. Event ID is generated once and equals AMQP messageId; relay uses stored event_version for routing, persistent delivery, mandatory routing and positive confirm with no return before marking PUBLISHED. Existing v1 tapping emitter remains unchanged; add a version-aware method for 3B envelopes. Broker outage or timeout never rolls back an already committed business response. Capped retry (existing max delay 3600s), finite attempt exhaustion, FAILED retention and operator-controlled same-ID reset remain in force. No exactly-once claim.

Future consumer contract: insert (consumer_name,event_id) atomically with service-owned projection update, ACK only after commit. Duplicate ID changes nothing. Only replace a collection projection if aggregateVersion is greater than stored; equal version/different event/snapshot is quarantined as conflict, never added twice; lower versions have no effect. Full snapshots permit higher versions arriving before creation; record the version gap for reconciliation while applying the snapshot. Voided rows remain tombstones with highest version and zero contribution. Unsupported versions/invalid schema use bounded retry then DLQ, with explicit operator replay. Analytics/Web consumers are out of 3B scope. Infrastructure's durable acceptance sink verifies publication; it is not an implemented business consumer.

## Contract verification required before release

Extend scripts/validate.py with strict JSON Schema Draft 2020-12, offline registry, UUID/date formats, all four positive/negative examples, semantic envelope/payload equivalence, exact decimal validation and preserved-old-schema hashes. Runtime export must match all existing 18 plus 9 added operations including body/header/query constraints and success/error responses. Python decimal parsing must be explicit (not binary floating arithmetic for precision assertions). New OpenAPI retains existing schemas/operations and uses distinct collection schema names. Add SIMULATED pending, zero DRC, correction and void examples; examples do not certify production measurements. Pin release artifacts into Operations only after independent contract release; copy schemas into version-specific subdirectories so v1/v2 names cannot collide. Retain legacy validators and 3A runtime exports/tests.
