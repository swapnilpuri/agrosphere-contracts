# agrosphere-contracts

## WA-1 local status — 2026-10-29

The owner accepted the exact eleven WA-1 executable artifacts for local Contracts 0.6.0 promotion/pinning on 2026-10-29. See docs/worker-attendance/RELEASE_0_6_0.json. Candidate/manifest bytes remain intact; earlier pending candidate labels are historical. Prior 0.5.0 OpenAPI is archived for byte verification. Approved info.version remains 0.2.0; repository release metadata records 0.6.0. No remote release was published.

AgroSphere API and event contracts, including Milestone 1A Estate Service.

This is an independent project and Git root. Version: 0.5.0; use independent SemVer tags and CHANGELOG.md. License decision: LICENSE.md (all rights reserved pending selection).

See AGENTS.md for scope and engineering rules. Estate Service now defines Milestone 1A business operations; Spatial Service defines Milestone 1B; other service APIs remain foundation placeholders. Architecture lives in the sibling agrosphere-architecture repository; versioned API/event definitions live in agrosphere-contracts. Do not add path dependencies to sibling projects.

## Validate

Python 3.12+: python -m pip install -r requirements-dev.txt; python scripts/validate.py. JSON Schema Draft 2020-12, offline reference registry and format checks are mandatory. Estate OpenAPI defines Milestone 1A operations; Spatial OpenAPI defines Milestone 1B; other OpenAPI files remain placeholders. No generated persistence models are shared.

Event major version lives in events/v1 and eventVersion=1; release this repository independently. Routing keys use agrosphere.<EventType>.v1 on the durable topic exchange agrosphere.domain. envelope.schema.json defines eventId, eventVersion, UTC timestamp, correlationId, source and canonical estateId; block events also require blockId. dataProvenance is explicit. Source names are logical service names without the agrosphere- prefix. UUIDs in examples are synthetic.

Coordinates must follow RFC 7946 WGS84 [longitude, latitude, optional altitude metres]. Geometry contracts will be added with spatial APIs in Milestone 1. .invalid schema IDs identify schemas only and must be resolved locally; they are not hosted endpoints.

Consumer transaction: insert (consumer_name,event_id) with ON CONFLICT DO NOTHING; apply projection only when inserted, in the same transaction; commit before ACK. Publisher writes outbox with domain mutation; relay publishes persistent messages with confirms and marks published only after confirmation. Duplicates are expected. Bounded retries and DLQ handling are required before consumers ship. Estate Service implements its v2 relay in Milestone 1A; consumer handlers remain separate work. Validate forecast period ordering and business semantics in applications as JSON Schema cannot enforce them.

## Milestone 1A contract release 0.2.0

Estate OpenAPI now defines sixteen business operations and Problem Details, JWT scope, pagination and optimistic versions. Four new self-contained events/v2 snapshot schemas use occurredAt/sourceService, canonical estateId/entityId and optional blockId as applicable. Every v1 contract remains byte-for-byte preserved. V1 EstateCreated requires companyId, which M1A does not own; v2 avoids inventing that identity. V1 block update fields cannot express status/count changes. Estate Service publishes only v2; existing v1 consumers must explicitly migrate to agrosphere.<EventType>.v2. There is no dual publishing.

Run python scripts/validate.py for v1/v2 examples, negative cases and all OpenAPI schemas. Optionally supply a directory of actual v2 envelopes as an argument. The service includes a pinned 0.2.0 schema snapshot and its own envelope verification script, so independent builds never require sibling source paths.

## Milestone 1B contract release 0.3.0

Spatial REST now defines 22 operations, bounded GeoJSON, feature/layer revisions, JWT estate scope and Problem Details. Service release 0.2.0 pins this independent contract release. Five new schemas under events/spatial/v1 use eventVersion=1, sourceService=spatial-service and agrosphere.<EventType>.v1 routing. This namespace preserves every foundation events/v1 and estate events/v2 schema. Feature events carry identifiers and geometryVersion, with geometry retrieved through REST. Examples are SIMULATED. No remote release or push has been performed.

The spatial projection consumes the existing estate v2 snapshots. No division lifecycle events exist in M1A; spatial can infer division membership from block snapshots, and must not claim authoritative division lifecycle. Expanding that contract requires a future coordinated release.

Milestone 1C compatibility verification and unchanged-schema/transport rules are recorded in docs/COMPATIBILITY.md. Release 0.3.1 changes documentation only; service/platform snapshots remain pinned to schema release 0.3.0.

## Proposed Milestone 3B design (unreleased)

[Collection REST/event design](docs/milestone-3b/API_EVENT_DESIGN.md) specifies nine additive Operations endpoints and a collection v2 event family. This is documentation for review only; runtime OpenAPI, schema bytes, examples, release version and service pins remain unchanged. Legacy LatexCollectionRecorded.v1 is preserved.

## Milestone 3B design acceptance

The owner accepted the [REST/event wire design](docs/milestone-3b/API_EVENT_DESIGN.md), including R01/R02, and authorized dependency-ordered implementation on 2026-10-27. See [approval scope](../agrosphere-architecture/docs/milestones/MILESTONE_3B_APPROVAL.md). Executable OpenAPI/schema authoring, validation, independent contract review and release remain outstanding. Existing published artifacts/VERSION are unchanged.

## Milestone 3B executable candidate — review pending

T01 now supplies nine additive REST operations (27 total), four self-contained collection v2 event schemas, SIMULATED pending/calculated/correction/void examples and seven persisted negative fixtures. This supersedes the earlier design-only description above. VERSION remains 0.4.0; candidate 0.5.0 has not been released or pinned. See [candidate review](docs/milestone-3b/CANDIDATE_REVIEW.md).

Run python scripts/validate.py, python scripts/build_collection_contracts.py --check and python -m unittest discover -s scripts -p test_collection_contracts.py -v in the repository virtual environment. CI runs all three. Decimal checks use Decimal; artifacts contain no float/double formats. IANA zone/local-date behavior is verified in the owning Java domain, not approximated by Python offsets.

## Local contract release 0.5.0

The project owner accepted the exact executable candidate and authorized local release metadata and Operations artifact pinning on 2026-10-27. See [release acceptance](docs/milestone-3b/RELEASE_0_5_0.json). Earlier candidate/review-pending statements describe the pre-release state. No remote publication, tag, commit or push occurred.

## WA-1 isolated executable candidate

The owner accepted worker/attendance design on 2026-10-29. See [candidate review](docs/worker-attendance/CANDIDATE_REVIEW.md) for fifteen additive REST operations, four minimal workforce events, exact hashes and retained independent release/pinning gate. Current release files/VERSION remain 0.5.0. Candidate artifacts are isolated under docs/worker-attendance/candidate; validate with `python scripts/build_workforce_contracts.py --check` and `python -m unittest discover -s scripts -p test_workforce_contracts.py -v` in addition to existing checks. This candidate does not enable runtime routes or REAL worker collection.
