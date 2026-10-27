# Collection contract candidate 0.5.0 — independent review required

Prepared: 2026-10-27 (America/Chicago). Status: AUTHORING AND LOCAL VALIDATION COMPLETE; NOT RELEASED OR PINNED. The current Contracts VERSION remains 0.4.0. No publication, tag, commit or push occurred.

## Concrete candidate

- [Operations OpenAPI](../../openapi/operations-service.yaml): nine new collection operations alongside all eighteen existing tapping operations. Every new operation declares bearer authorization, documented scope rules, correlation, exact request/response/filter/error shapes and required idempotency headers for writes. Literal `/collections/summary` is distinct from UUID paths. List date bounds are both-or-neither; summary requires both.
- Four self-contained Draft 2020-12 schemas under events/operations/v2: LatexCollectionRecorded, DrcMeasurementRecorded, LatexCollectionAdjusted and LatexCollectionVoided. Envelopes use eventVersion=2, stable collection identity/version and full post-command snapshots. Existing collection/tapping v1 artifacts are preserved; no dual publishing is introduced.
- SIMULATED creation, first DRC, correction and void fixtures; measured-zero and half-up edge fixtures; seven persisted negative fixtures; four REST command examples.
- [Compatibility baseline](compatibility-baseline.json): all 47 pre-existing event/example SHA-256 values, existing Operations paths/components and metadata. The validator checks old file bytes and semantic API compatibility before accepting additions.
- [Exact candidate inventory](CANDIDATE_0_5_0.json): hashes of the executable contract artifacts, fixtures, builder, validator and boundary tests. This manifest identifies this candidate independently of an unchanged Git HEAD.

## Validation actually performed

From the Contracts root using its existing isolated environment:

```powershell
.venv/Scripts/python.exe scripts/validate.py
.venv/Scripts/python.exe scripts/build_collection_contracts.py --check
.venv/Scripts/python.exe -m unittest discover -s scripts -p test_collection_contracts.py -v
git diff --check
```

All passed. Twelve test methods include parameterized subcases for required/unknown fields, exact decimal bounds, missing versus zero DRC, offset/microsecond precision including extra trailing zeros, provenance, laboratory evidence, correction null/no-op shapes, receipt headers, paired date filters, event/aggregate/measurement identity, revision consistency and calculation semantics. Persisted negatives include malformed UUID, unsupported version, lossy timestamp, wrong formula, mixed provenance, wrong root identity and measurement chronology.

The independent Operations domain suite supplies Java timezone/DST/local-date tests. The Python wire validator does not approximate IANA timezone rules; that remains a domain/runtime invariant. It checks chronology, formula, snapshot identity and version consistency. OpenAPI query constraints are documented and exposed through x-query-constraints; actual HTTP enforcement remains T06, not a claim established by schema tests. Authorization, duplicate-lot uniqueness, durable replay and transaction guarantees require their application/database integration tests.

Initial failures were resolved: YAML's treatment of bare exponent literals was avoided by emitting 0.0000001; unsupported/missing event-type validation was represented correctly in the negative assertions. A proposed extra Python timezone dependency could not be installed and was removed; requirements-dev.txt is unchanged. No new dependency is needed for the passing candidate checks.

## Requested disposition

Review and accept this exact executable candidate (or identify requested changes) through the project's independent contract review process. The owner's earlier design acceptance did not release executable artifacts that did not yet exist. If the owner is also the applicable contract reviewer, an explicit acceptance here may record that role; otherwise identify the reviewer and their disposition.

Upon acceptance, authorize **local Contracts release 0.5.0 metadata and versioned artifact pinning into Operations**. This does not request remote publication, tagging/pushing, deployment, production migration or secret-handling changes. Do not copy candidate schemas into a producer runtime or enable endpoints before this gate is satisfied.

Next implementation: T03 persistence/migration and T04 reference/security after the contract gate, following their dependencies and the owner's retained exclusions. Docker Desktop is currently unavailable; the owner must make its Linux engine available before disposable PostgreSQL/RabbitMQ integration and container packaging checks can run. No authoritative database may be used as a fixture.

## Subsequent disposition - 2026-10-27

The project owner accepted the exact executable candidate and authorized local Contracts 0.5.0 metadata and Operations artifact pinning. See [release record](RELEASE_0_5_0.json). All 26 candidate hashes matched before release/pinning; candidate and earlier validation records remain historical. Docker is available through approved command escalation. The contract review gate described above is satisfied; secret-handling exclusions remain in effect.
