# AN privacy executable candidate review

Date: 2026-10-31. Status: UNRELEASED, exact new acceptance required; no promotion/pinning/runtime change.

The owner delegated provisional privacy choices and requested next steps. Original Contracts 0.8.0 acceptance remains valid. This is a separate compatibility extension, proposed local release **0.9.0**, not repeated AN-1 approval. See the [Architecture implementation review](../../../agrosphere-architecture/docs/milestones/ALERTS_PRIVACY_EXTENSION_REVIEW.md), its AP-01–11 criteria/AP-T01–08 plan and [single client decision register](../../../agrosphere-architecture/docs/milestones/ALERTS_NOTIFICATIONS_CLIENT_DECISIONS.md).

## Exact artifacts

Manifest `CANDIDATE_MANIFEST.json` SHA-256: `ea6402a205d1da7a0801090b0acabac58ae164ba6544b474d709d8a4a608286b`.

| Artifact | SHA-256 |
|---|---|
| `candidate/openapi/operations-service.yaml` | `f8a862a4f4d1cc397999fc5a47f763a23140eb7d72b38a4e2ec9c036315b71bc` |
| `candidate/examples/requests.json` | `0de7958a381051cf3c65ad6338fbb0833179ba249a69db9a9c2f662ad34089c7` |
| `candidate/examples/responses.json` | `11e24ba8bfabeaaa64839d562e9f33e668e26929eaada0e284c82d08f83989c7` |
| `candidate/examples/negative.json` | `84ff1c8fdf81698127922cc64f40ccbc788317cc4e9ccad3517fb0b217970a5a` |
| `candidate/semantics.json` | `072d3fa0bbf80556b93cb085b0bd3d8326cae0d03927624a0e3b20eee734f4c4` |

Baseline released API SHA-256 `12daf94f17e8b4fded507c1f9a27a72deb7244c9a8b20013df131e748213e937`; released VERSION hash `9330aed58d10936f589760929172cc76c9d8b14ef40ee8f63f05d822ae2e14d7`. Both remain unchanged, as do all prior candidates/manifests/events and Operations/Web pins. The candidate contains 70 operations: retained 58 non-alert operations, six legacy alert operations and six new v2 alert operations. Existing component definitions are unchanged; legacy alert operations gain explicit deprecated/privacy-mode retirement metadata and 410, not silent mutation of their success schemas.

## New decisions for exact review

- Six `/api/v2/alerts` routes and explicit privacy states for expired read markers, acknowledgement attribution redaction and expired/partial history. No external delivery or shared event additions. Scope/positive roles/no-store/SIMULATED and default-disabled actual-account gates persist.
- UUIDv7 command keys with +/- five-minute fresh-key admission, hard key timestamp + 30-day retry ceiling, earlier server completion/personal-copy deadlines, no indefinite identifying tombstones. Existing live exact success replays only after current authorization. Absent older keys return 409 inside their lifetime; expired keys return 410, never execute as new. Malformed/v4/excess-future keys return 400. The timestamp layout follows [RFC 9562 section 5.7](https://www.rfc-editor.org/rfc/rfc9562.html#section-5.7); admission/retention rules are AgroSphere proposals, not RFC requirements.
- 410 codes `ALERT_API_RETIRED`, `ALERT_COMMAND_EXPIRED`, `ALERT_READ_RETENTION_EXPIRED`; no expired inactive marker creation or implicit new retry. The fresh-key window deliberately excludes replay of missing recent receipts beyond five minutes even if under 30 days. Clients must explain unknown outcome instead of claiming success.
- Legacy alert routes retire in privacy mode; no fallback to UUIDv4/unexpired replay semantics. Legacy generated tests may use an isolated mutually exclusive legacy mode. No actual accounts enabled and no source/geometry/data recreation.
- Proposed additive privacy persistence, cutoff/removal metadata, copy removal and scoped maintenance are specified in Architecture. They are not implemented by this candidate. V1–V6 immutable evidence/roles/grants remain unchanged. Nonempty legacy alert storage prevents privacy enablement until a separate data plan is reviewed.

## Validation and reproducibility

Use the existing independent Contracts virtual environment:

```powershell
.\.venv\Scripts\python.exe scripts/build_alert_privacy_contracts.py
.\.venv\Scripts\python.exe scripts/alert_privacy_contract_validation.py
.\.venv\Scripts\python.exe -m unittest discover -s scripts -p test_alert_privacy_contracts.py
```

Builder writes only this candidate and manifest. Validator checks exact/reproducible bytes, released baseline, OpenAPI 3.1, Draft 2020-12 with format checking, all old component definitions/58 non-alert operations, permitted legacy deltas, role/no-store headers, bounded key schema, positive and negative examples. Tests include no ordinary actor leaks, expired marker/ack/history states, key skew/admission/expiry boundaries authorization-before-replay and a removal cutoff that covers previously admitted future-skew keys. Eleven new tests pass. Key-decision routines are contract test oracles; no HTTP/database implementation is claimed.

First system-Python validation could not import `openapi_spec_validator`; using the pre-existing Contracts `.venv` resolved it without installing/changing dependencies. Exact checks/evidence are recorded in the Architecture checkpoint. No database, browser/platform or existing-stack check is implied by schema/contract tests.

## Decision requested

Accept/revise these exact five artifacts and the Architecture technical package, authorizing generated-only implementation and an independent local 0.9.0 promotion/archive/pin step. Do not authorize new runtime semantics against an existing stack, automatic historical conversion, broad app DELETE/DDL, existing role/credential changes, REAL, external notifications, destructive migrations, private configuration access, Git publication/deployment or AEO changes. The local-stack plan is conditional preparation only and needs its own exact execution review later.

Final result: existing Contracts validation PASS; all 59 contract tests PASS (48 retained + 11 new); diff check PASS. All pre-edit Contracts file hashes and HEAD/raw index unchanged. No release, VERSION/pin modification or runtime deployment performed.
