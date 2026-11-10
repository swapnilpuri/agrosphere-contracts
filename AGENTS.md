# Repository instructions

## II-1 exact local release accepted - 2026-10-31

The owner explicitly accepted the eleven artifacts and local Contracts 0.7.0 promotion/release metadata plus Operations/Web pins. See docs/incident-inspection/RELEASE_0_7_0.json and Architecture INCIDENT_INSPECTION_CONTRACT_APPROVAL.md. Preserve reviewed bytes/manifest, prior 0.6.0 archive and old events. This satisfies historical pending release labels for these exact artifacts only. No remote publication or REAL/production/AEO/credential/role action is authorized.

Work only within this independent Git repository. No parent repository, submodules, shared persistence models, cross-service SQL or multi-service Maven parent.

Current scope: Estate/Spatial contracts through Milestone 1C compatibility verification. Preserve existing schema bytes and version namespaces; tracing metadata belongs to transport, not a silent event-envelope change.

Use ports/adapters and service-owned migrations. APIs and events are designed in agrosphere-contracts; coordinate breaking changes through a versioned contract release, never a source path dependency. UUID estateId/blockId remain stable across clients. Mark data REAL, SIMULATED, ESTIMATED or PREDICTED. GeoJSON is WGS84 longitude/latitude (RFC 7946). Procedural trees are illustrative.

Never commit credentials, local environment files, generated datasets or large geospatial assets. Use environment examples containing placeholders only. No remote creation, push or cloud deployment is authorized.

Run repository checks documented in README.md. Report actual checks separately from unavailable checks. Version independently using SemVer and CHANGELOG.md; changes to 0.x contracts can still break consumers and require review.

## Owner-authorized Milestone 3B candidate

The 2026-10-27 owner approval authorizes T01 contract authoring, including nine additive Operations REST operations and four v2 collection event schemas. Preserve all old schemas/examples and existing API semantics. Candidate 0.5.0 is unreleased: independent contract review/release must precede Operations pinning; no VERSION bump, publication or remote mutation is authorized by authoring alone. Follow the Architecture approval/checkpoint.

The owner accepted the executable candidate and authorized local release 0.5.0 metadata and Operations artifact pinning on 2026-10-27. RELEASE_0_5_0.json records the exact artifact hashes. The earlier unreleased restriction has been satisfied for local release/pinning only; no remote publication is authorized.

## Owner-approved WA-1 authoring — 2026-10-29

The subsequent explicit executable-candidate approval authorizes exact local 0.6.0 promotion/pinning. See docs/worker-attendance/RELEASE_0_6_0.json and Architecture WORKER_ATTENDANCE_CONTRACT_APPROVAL.md. This satisfies the historical pending gate below for these eleven artifacts only. Preserve candidate/manifest bytes, prior 0.5.0 archive and old event bytes. No publication/remote mutation is authorized.

The owner accepted the worker/attendance design and authorized dependency-ordered WA-T01–T09; see Architecture docs/milestones/WORKER_ATTENDANCE_APPROVAL.md. Author/test the fifteen additive REST operations and four minimal workforce events as an isolated executable candidate. Preserve released artifacts/VERSION and producer pins until exact candidate acceptance and independent local release are recorded. No remote publication or REAL worker data; no names/codes/reasons in shared events. See docs/worker-attendance/CANDIDATE_REVIEW.md for the new gate, not repeated 3B approval.

## Owner-approved II-1 authoring — 2026-10-31

Architecture INCIDENT_INSPECTION_APPROVAL.md accepts II-D01–10 and II-T01–09 in dependency order. Author/test the isolated sixteen-operation/four-minimal-event candidate under docs/incident-inspection, preserving released 0.6.0 bytes, legacy placeholder and producer/Web pins. Exact candidate acceptance precedes local release/promotion/pinning; 0.7.0 remains proposed. New mutations SIMULATED-only; no report text or actor identifiers in shared events. II-D07/08 and WA D08/D09 remain open. No publication, existing-stack/role/credential/production/AEO operation follows from authoring.

## Owner-approved AN-1 authoring — 2026-10-31

Architecture ALERTS_NOTIFICATIONS_APPROVAL.md accepts the six-operation in-app alert package. Author/test an isolated executable candidate under docs/alerts-notifications; no new shared event family. Preserve released 0.7.0 artifacts/VERSION, prior candidates/manifests and producer/Web pins. Exact executable acceptance and independent local release precede promotion/pinning. Generated-only development; subject-policy/workload and WA/II gates remain open. No publication, private configuration/live-stack, role/credential, REAL, external delivery or AEO action.

## AN-1 exact executable accepted — 2026-10-31

Architecture ALERTS_NOTIFICATIONS_CONTRACT_APPROVAL.md records owner acceptance of the exact four artifacts, local Contracts 0.8.0 release and Operations/Web pins. Continue accepted AN-T03–09 by dependency; preserve prior features/artifacts and reviewed bytes. Generated-only verification; AN-D07/08 and WA/II/M2 gates remain open. No non-generated account rollout, REAL, existing-stack/private configuration/role/credential/external delivery/Git/deployment/destructive/data-reset/AEO action. Gateway adds only /api/v1/alerts/**; Infrastructure generated-only drills reuse existing topology without a new alert queue.

## AN-1 local verification state — 2026-10-31

Architecture ALERTS_NOTIFICATIONS_VERIFICATION.md records local implementation and generated-only checks after exact executable acceptance. Earlier preparation labels are historical. Preserve 0.8.0 pins/old bytes/V1–V5/Web config/index and existing data/volumes. Default-disabled subject-policy gate, AN-D07/08, WA/II/M2 and no non-generated rollout/REAL/live-stack/private configuration/role/credential/Git/deployment/AEO exclusions remain.

## Owner-approved AN privacy extension — 2026-10-31

Architecture ALERTS_PRIVACY_APPROVAL.md records exact five-artifact privacy candidate acceptance (manifest ea6402a205d1da7a0801090b0acabac58ae164ba6544b474d709d8a4a608286b), local independent Contracts 0.9.0 release/archive/pins and generated-only AP-T02–07 implementation. Preserve accepted bytes, V1–V6, old events/records and all staged work/Web config. Additive privacy storage and narrowly scoped maintenance may be tested only in separately owned disposable generated databases. No existing-stack/private configuration/actual-account/REAL/existing role or credential/destructive migration/historical conversion/external delivery/Git publication/deployment/AEO action. AP-T08 local-stack execution remains separately gated; do not repeat II-1. Prior approval/pending labels remain historical within their scope; do not ask again for this exact acceptance.


## Owner-approved TLM-01 preparation — 2026-11-01

Architecture docs/milestones/MQTT_POC_APPROVAL.md records acceptance of exact MQTT_POC_REVIEW.md SHA-256 84ba22535e81de2296d76746c612325571ea6364962bb42d7fe2138716dd3dbd. Authorizes isolated Contracts candidate and Telemetry pure domain/ports/tests only, SIMULATED. Exact executable acceptance/local release precedes promotion/pins/adapters; broker ACL/provisioning/migrations need later scoped review. Preserve all old release bytes, V1, indexes/config/data and independent builds. No live MQTT, database, actual account, role/credential, private configuration, REAL, Git publication/deployment or AEO action.


## TLM-01 exact local release/pins approved — 2026-11-01

Architecture MQTT_POC_CONTRACT_APPROVAL.md records owner acceptance of all eight artifacts in manifest 174140bc1db129ab879d9e431e9065a6715746c31c70fa0ec2bb7992063f01b0 and local Contracts 0.10.0 archive/promotion/release metadata plus exact Telemetry API/MQTT/event pins. Historical pending labels are satisfied only for this scope. Preserve exact candidate/review/archive/old artifacts and all existing indexes/config/data. Prepare broker ACL/provisioning/migration review before adapters; no live stack, role/credential, private configuration, REAL, Git publication/deployment or AEO action.


## Owner-approved ANL-01 preparation — 2026-11-05

Architecture ANALYTICS_POC_APPROVAL.md records acceptance of exact review SHA-256 3f4b8ee7c521502e0a29196ab647d84598dcb09aa91700856ef1bdc36e452342. Isolated Contracts candidate/validation and Analytics pure domain/ports/tests only, SIMULATED. Preserve reviewed/released bytes, V1, configuration/data/indexes and independent builds. Exact executable acceptance/local release precedes promotion/pins; runtime SQL/consumer/queue/security/provisioning needs subsequent bounded review. No adapters, running API/broker/database, existing-stack/role/credential/private configuration, REAL, Git publication/deployment or AEO action.


## ANL-01 exact local release/pins approved — 2026-11-05

Architecture ANALYTICS_POC_CONTRACT_APPROVAL.md accepts exact manifest 43d9e5f7b328002c735cdf85da3f6ed5e0c9ff41a2f74aaccdcc0b8e8a396998 for ten artifacts/four unchanged inputs, local Contracts 0.11.0 archive/promotion and independent Analytics pins only. Preserve old bytes/reviews/data/config/indexes. Concrete runtime SQL/consumer/queue/security/provisioning review remains required; no runtime/Gateway/Web/existing-stack/REAL/Git/deployment/AEO authority. Do not repeat satisfied preparation/executable approvals.


## ANL-02 approved preparation — 2026-11-05

Architecture ANALYTICS_ENVIRONMENT_POC_APPROVAL.md accepts exact preparation review c15ac50638feb09b176a44b5b16033d50e1b7365cbbe4467550f25d5910a17e9. Owner resumed in the new session. Isolated Contracts environmental candidate and Analytics pure rules/ports/tests only, SIMULATED; no repeated preparation approval. Current 0.11.0 release/pins and old reviewed bytes remain unchanged. Exact executable/local release/pins and subsequent runtime SQL/queue/security/provisioning remain separate gates; no existing-target/private config/data/role/credential, REAL, Git publication/deployment or AEO authority. See current Architecture checkpoint/verification.


## ANL-02 exact local release/pins approved — 2026-11-05

Architecture ANALYTICS_ENVIRONMENT_CONTRACT_APPROVAL.md records owner acceptance of manifest 1759e5d95fb3602b623b995e4650f035b67dbb550760116587f46c031ca7d111: fourteen artifacts/three unchanged inputs, local independent Contracts 0.12.0 archive/promotion/release metadata and Analytics API/Telemetry input pins only. Preserve old candidates/reviews/releases, four collection-v2 inputs, V1/V2/config/data/indexes. Preparation/executable gates satisfied; runtime/SQL/AMQP/HTTP/Web/queue/security/provisioning remains separately gated under ANL02_ADAPTER_REVIEW.md. No existing-target/private config/account/role/credential, REAL, Git publication/deployment or AEO authority.
