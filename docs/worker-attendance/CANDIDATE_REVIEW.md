# WA-1 executable contract candidate — independent review pending

Date: 2026-10-29. The owner accepted the business/API/event design in Architecture WORKER_ATTENDANCE_APPROVAL.md. This is the resulting concrete executable candidate, not a new business-design approval request. Authoring is complete; independent executable acceptance/local release/pinning is still pending under the approved plan.

## Candidate and compatibility

All new executable artifacts are isolated under [candidate](candidate/openapi/operations-service.yaml). The OpenAPI contains the same 27 released Operations operations plus 15 new worker/attendance operations, closed request/view/history shapes, role policies, required command keys, pagination/date/error and replay rules. Its inherited info.version remains 0.5.0 to avoid modifying released metadata during authoring; that is not a claim that the new operations are released as 0.5.0. New schemas/examples have the intended `operations/workforce/v1` namespace but are not in the released event tree or any producer pin.

Four self-contained JSON Schema 2020-12 events: WorkerRegistrationCreated, WorkerRegistrationChanged, WorkerAttendanceRecorded, WorkerAttendanceChanged. They contain minimal versioned snapshots, no names/codes/free-text reasons/actor subjects, and need no fabricated block. Shared broker identifiers still require D09 privacy treatment. Seven write shapes serve the eight write operations (correction/re-record share AttendanceChange). Four positive event examples and nine persisted negatives use SIMULATED identifiers; no real people or estate counts are asserted.

All 71 pre-existing event/example/OpenAPI files remain byte-identical, checked against [compatibility baseline](compatibility-baseline.json); candidate legacy paths/components/security/top-level metadata are semantically equal to the current release. Contracts VERSION stays 0.5.0. Operations pinned copies remain at 0.5.0. No release record, producer pin, Gateway route or Web client has changed.

Builder: `python scripts/build_workforce_contracts.py`; deterministic check: same with `--check`. This only writes/checks isolated candidate artifacts. `scripts/validate.py` now runs existing checks plus candidate schema/semantic/compatibility checks, and CI adds candidate generation-drift and unit tests. Existing collection builder/validator and all released bytes remain unchanged.

## Field and policy resolution

- Registry resource `id` and new `workerRegistrationId` are UUIDs; legacy tapping `workerId` remains signed-sub text. No automatic person/account linkage.
- Current views have minimal profile/context/version/createdAt/updatedAt fields. Actors and backdate/correction reasons exist only in protected history; supervisors never receive them. WorkerRosterItem uses `code`/`provenance` as specified in the reviewed screen contract; full WorkerView uses `workerCode`/`dataProvenance`.
- Identity, estate, worker code and provenance are fixed. Attendance identity/date cannot be corrected; void then record the right identity. Re-record uses the same daily UUID and current eligibility/context in a new revision while preserving earlier evidence.
- Zero/missing evidence is not a status: UNMARKED is an absent current observation, not ABSENT. VOIDED evidence remains queryable. Same-day counters are roster coverage, not employee totals or hours.
- Role unions grant only explicit workforce permissions. PLANTATION_ADMIN alone is denied; PLATFORM_ADMIN is explicitly global. ESTATE_ADMIN/MANAGER are scoped; supervisors record today only; manager/auditor histories are restricted.
- Past dates require manager authority/reason; close end is exclusive and at most estate-local tomorrow. Domain and later HTTP/DB integration enforce cross-field/timezone/state rules beyond JSON Schema.
- Both REAL/SIMULATED are representable for future compatibility, but REAL collection is denied until D09 is accepted/implemented/verified. Current Operations pure-domain code unconditionally permits only SIMULATED mutations; no new endpoint is enabled.

## Executed checks

Using repository `.venv/Scripts/python.exe` on Windows:

| Command | Result |
|---|---|
| scripts/validate.py | PASS legacy families, collection precision/compatibility, candidate 42-operation API/four events/seven request shapes/nine negatives/71 old artifact hashes |
| scripts/build_collection_contracts.py --check | PASS, old generator unchanged |
| scripts/build_workforce_contracts.py --check | PASS, eleven deterministic isolated artifacts |
| -m unittest discover -s scripts -p test_collection_contracts.py -v | 12 passed |
| -m unittest discover -s scripts -p test_workforce_contracts.py -v | 12 passed |

These are executable contract checks, not proof of runtime route/security/database/broker/UI behavior. No hosted CI, local release/pinning, production or actual personal-data collection occurred. Review exact artifacts using [candidate manifest](CANDIDATE_MANIFEST.json); the manifest is a review fingerprint, not an approval/release record.

## Required next decision

Accept or revise the exact eleven executable artifacts in the manifest. Recommended next independent local Contracts release is 0.6.0, with additive promotion of these artifacts, unchanged legacy namespaces/semantics, explicit -text handling of exact byte-pinned artifacts, a release manifest and validated Operations pinning. This version/release/pinning recommendation is not yet approved by candidate authoring. No remote publication, tag, commit or push is requested.

The source gate is the owner's approved [WA-T01 plan](../../../agrosphere-architecture/docs/milestones/WORKER_ATTENDANCE_REVIEW.md): "Independent review/accepted local release with exact hashes before T04/T07 pins". Prepare/review the candidate first; do not ask for this review without concrete artifacts. Pure domain/ports and persistence preparation have proceeded independently, with source/test evidence in the Architecture checkpoint. D08 workload acceptance and D09 REAL-data enablement remain distinct later gates.
