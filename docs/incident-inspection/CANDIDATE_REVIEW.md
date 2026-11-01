# II-1 executable candidate — 2026-10-31

Status: REVIEW PENDING; unreleased. The owner accepted the design on 2026-10-31, exact package SHA-256 `79944183a963bdddd4008557e2a8eb1e15acff739b612fb0d2e95d9d4f7da8e8`. This gate concerns the executable artifacts now created, not repeating design approval. Current Contracts VERSION remains 0.6.0; proposed next local release is 0.7.0, not yet authorized. No producer/Web pin changed.

## Exact review inventory

[Manifest](CANDIDATE_MANIFEST.json) fingerprints **eleven artifacts** under candidate/:

- [Operations OpenAPI](candidate/openapi/operations-service.yaml): 58 operations, preserving all 42 current operations/components/metadata and adding the accepted sixteen inspection/incident operations. JSON serialization is valid YAML/OpenAPI 3.1; legacy info.version stays 0.2.0, distinct from proposed repository release 0.7.0.
- Four closed self-contained schemas in candidate/events/operations/crop-health/v1: FieldInspectionRecorded, FieldInspectionChanged, CropHealthIncidentReported and CropHealthIncidentChanged.
- Four corresponding SIMULATED event examples, [seven request shapes](candidate/examples/operations/crop-health/v1/requests.json) and [fourteen persisted negative events](candidate/examples/operations/crop-health/v1/negative.json).

The new namespace/event names preserve foundation CropHealthIncidentDetected v1 and every other existing schema/example. No dual publication, notification delivery, consumer or live route is introduced by this candidate. [Compatibility baseline](compatibility-baseline.json) fingerprints all **82** currently released OpenAPI/event/example/VERSION files. Independent producer release pins and migration bytes are additionally protected in Architecture increment evidence.

## Wire behavior to review

Every new operation requires bearer authentication; every POST requires a UUID Idempotency-Key. Existing-root commands require expectedVersion, except inspection commands use inspectionVersion. All linked incident commands additionally require inspectionVersion; linked inspection commands require incidentVersion. These conditional paired-version rules depend on stored identity and are explicitly runtime constraints, not claims of JSON Schema cross-record validation.

Create inspection requires estateId,blockId,dataProvenance,observedAt,outcome,findings. CLEAR forbids incident input. FOLLOW_UP requires category,severity,summary,details in a nested incident object; its observedAt is the inspection time. Creation returns inspection plus nullable incident with a stable Location. Inspection correction returns the same paired result, since CLEAR→first FOLLOW_UP can create an incident. Direct incident create cannot supply inspectionId. New mutations and event snapshots are SIMULATED-only; future REAL enablement requires a separately reviewed implemented policy, not a config switch.

Correction/amendment inputs are complete mutable replacements. Incident amendment is allowed only OPEN/IN_REVIEW; correction also permits RESOLVED and preserves closure chronology. No identity/link/provenance/status editing through those bodies. Fresh-key no-op and illegal transitions conflict. VOIDED is terminal. Inspection CLEAR may retain its historical link only after the linked incident is VOIDED; it cannot create a second linked incident. Active Estate validation is repeated for newly created linked evidence. Existing historical corrections/transitions use retained canonical context and do not require geometry or active master records.

OPEN→IN_REVIEW triage; OPEN/IN_REVIEW→RESOLVED with resolution time/note; RESOLVED→OPEN clears current resolution fields and retains immutable history. Void retains prior resolution metadata if present, and never cascades automatically. Observation correction may not invalidate any retained resolution, including after multiple reopen/resolve cycles; Operations keeps a private earliest retained resolution boundary for this check, excluded from wire snapshots.

Reads require one explicit estate on list operations and SIMULATED provenance. Page defaults 0/25, size 1–100, offset <= int32 maximum. Observation bounds are both-or-neither and half-open; newest observedAt then UUID descending. Incident status accepts repeated query values (OpenAPI form/explode), default OPEN+IN_REVIEW. History is paged, separately restricted. Unknown fields/filters are rejected. Current inspection views include linkedIncidentStatus/version as contextual latest data; immutable inspection history snapshots contain its own root/link only, not mutable linked status. A linked incident change does not rewrite inspection history or increment the inspection version.

Explicit offset input instants allow up to six fractional digits; canonical responses/events use UTC and at most microseconds. Excess precision, including additional trailing zeros, is rejected in this new feature, independently of retained legacy collection behavior. Supervisors create only estate-today; manager past-date create requires backdateReason. Later corrections require reason. IANA zone validity, local dates/DST, current-clock and reference/lifecycle conditions are application acceptance checks; the schema validator does not approximate an IANA zone with an offset.

Positive permissions: PLATFORM_ADMIN globally (explicit estate list), scoped ESTATE_ADMIN/ESTATE_MANAGER manage, FIELD_SUPERVISOR current read/today-create, AUDITOR current/history read. PLANTATION_ADMIN/FIELD_WORKER/VIEWER alone grant no access. Current views omit actor/revision reasons; protected history has them. Minimal ownership before protected reads; missing/foreign object ID uniformly 404 after feature-role validation, explicit denied estate 403. Reauthorize before original-success replay; permission downgrade denies old fuller response. Errors are Problem Details and sanitized; exact status meanings are in each operation.

Minimal events carry canonical root/estate/block IDs, timezone/observation/provenance/version, inspection outcome/state/link or incident category/severity/status/link/nullable resolution time. They omit all findings, report summaries/details, reasons, resolution notes and actor subjects. Changed events carry adjacent previousVersion/changeKind. A private-only change still advances the minimal version. Paired events may reorder; consumers must deduplicate and reconcile, never assume two-root transport atomicity.

## Actual verification and limits

PASS: main validator (legacy collections/workforce plus this candidate), OpenAPI validation, all event/request positives and fourteen negatives, deterministic builder --check for all three increments, and **36 contract tests** (24 retained + 12 new). The new tests cover closed/request-required fields, conditional linked create, authentication/key/scope declarations, SIMULATED restrictions, offset/precision/text rules, privacy views/events, identity/version/lifecycle/chronology and compatibility. These are executable contract checks, not evidence of HTTP/JWT/DB/broker/UI enforcement.

Commands (repository virtual environment):

```powershell
.venv\Scripts\python.exe scripts/validate.py
.venv\Scripts\python.exe scripts/build_collection_contracts.py --check
.venv\Scripts\python.exe scripts/build_workforce_contracts.py --check
.venv\Scripts\python.exe scripts/build_crop_health_contracts.py --check
.venv\Scripts\python.exe -m unittest discover -s scripts -p 'test_*contracts.py' -v
```

No HTTP, migrations, broker bindings, generated Web types, deployment or hosted CI result is asserted. Existing versions/pins/records/volumes/configuration are preserved. II-D07/08 and WA D08/D09 remain open, as does M2 performance. No contract authoring here authorizes REAL collection, role/credential mutation, Git publication or AEO changes.

## Requested independent decision

Accept or revise the eleven exact artifacts identified by the manifest. If accepted, authorize their independent **local Contracts 0.7.0 promotion/release metadata and Operations/Web pinning**, preserving current 0.6.0 OpenAPI in a byte-verifiable archive and all old event bytes. Record reviewer/date/exact manifest hash/conditions before promotion. Existing II-T01–09 design/implementation authorization persists; no repeated per-task approval is required. Remote release/commit/tag/push, production and existing-stack upgrade remain excluded.
