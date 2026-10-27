# Milestone 1C compatibility verification

Contract documentation release 0.3.1 preserves the schema bytes/semantics of contract release 0.3.0. Estate API and estate v2 snapshots remain the 0.2.0 contract set; Spatial REST/spatial v1 remain the 0.3.0 additions. No Java implementation classes or persistence entities are shared. Infrastructure/service validators pin local schema snapshots and never read sibling source at build/runtime.

Estate publishes EstateCreated, EstateUpdated, PlantationBlockCreated and PlantationBlockUpdated as version 2 on agrosphere.<EventType>.v2, with eventId, eventType, eventVersion, occurredAt, correlationId, sourceService, estateId, entityId, explicit dataProvenance and full payload revision; block events also carry blockId. Spatial validates schema/UUID/format/envelope-payload identity, transactionally deduplicates eventId and rejects stale revisions. Legacy foundation v1 envelopes are deliberately preserved; they are not silently substituted for v2. Canonical IDs remain UUID strings across APIs/events/GeoJSON properties.

Spatial's five spatial v1 events remain in events/spatial/v1 and use the existing sourceService/referenceEntityId/geometryVersion semantics. Version namespaces are explicit; consumers bind only supported keys. Feature events identify geometry versions; they do not transport geometry blobs. A contract-breaking change requires a coordinated independent major event version/release and migration; documentation changes and transport metadata do not change schema version.

Milestone 1C V3 service migrations persist W3C traceparent/tracestate beside the outbox payload. AMQP observation adds transport headers and message correlation identifiers. The event JSON stays unchanged; no consumer must understand the tracing headers to process its supported envelope. Existing outbox rows remain valid and publish without an initiating trace when that transport metadata is absent.

No division lifecycle event exists. Spatial may infer division membership from block snapshots but cannot claim authoritative division status. Child-first delivery retains block/reference IDs durably; later authoritative Estate snapshots reconcile the missing parent. Geometry mutation waits for a valid parent reference. Schema-invalid or conflicting events follow bounded retry/DLQ instead of silent deletion. See infrastructure docs/INTEGRATION_TESTING.md and the owning service README for operator-controlled replay.

Validated with python scripts/validate.py, both services' actual runtime OpenAPI/event validators, and infrastructure's real Keycloak/two-division/ten-block GeoJSON workflow. Runtime API operation sets match pinned OpenAPI; all four Estate event types and spatial envelopes validate. No schema/route changes were needed for the integrated workflow. No remote release or push was performed.

## Collection contract release 0.5.0

Locally accepted by the owner on 2026-10-27. Adds nine collection operations under /api/v1/tapping/collections and four events/operations/v2 snapshot schemas using eventVersion=2. Foundation collection v1 and all tapping v1 bytes remain unchanged. No dual publication. Runtime producer copies use version-specific directories; no sibling runtime dependency is introduced. See milestone-3b/RELEASE_0_5_0.json for accepted artifact hashes and publication exclusions.
