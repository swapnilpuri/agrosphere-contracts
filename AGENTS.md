# Repository instructions

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
