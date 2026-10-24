# agrosphere-contracts

AgroSphere API and event contracts, including Milestone 1A Estate Service.

This is an independent project and Git root. Version: 0.3.1; use independent SemVer tags and CHANGELOG.md. License decision: LICENSE.md (all rights reserved pending selection).

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
