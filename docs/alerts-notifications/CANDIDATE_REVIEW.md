# AN-1 executable contract candidate review

Status: UNRELEASED REVIEW CANDIDATE, 2026-10-31. The owner accepted the design and dependency-ordered tasks in Architecture ALERTS_NOTIFICATIONS_APPROVAL.md; that does not accept these newly authored executable artifacts. No release/promotion/pinning has occurred.

## Exact scope for review

Four candidate artifacts, manifest SHA-256 `d96a5885a60e4e16e2b6e196806d26c8e50a8b58d0243d06a8a6651962b3274c`:

| Artifact (relative to Contracts root) | SHA-256 |
|---|---|
| `docs/alerts-notifications/candidate/openapi/operations-service.yaml` | `12daf94f17e8b4fded507c1f9a27a72deb7244c9a8b20013df131e748213e937` |
| `docs/alerts-notifications/candidate/examples/requests.json` | `0de7958a381051cf3c65ad6338fbb0833179ba249a69db9a9c2f662ad34089c7` |
| `docs/alerts-notifications/candidate/examples/responses.json` | `a66a17ad57ba767d113cf10ba892be977f17ced4659e70f1508b1d49b2b6864b` |
| `docs/alerts-notifications/candidate/examples/negative.json` | `4deffc3ea902c3e707cc68d324de1ae8f4d08161feb5d53aca90dff88a6fef58` |

The full candidate OpenAPI preserves all 58 released Operations operations/metadata/components and adds six alert operations (64 total). Two closed commands: own read with attentionVersion, shared manager acknowledgement with expectedAlertVersion/attentionVersion. Nine positive response fixtures and twenty persisted negative fixtures exercise privacy, SIMULATED provenance, integer bounds, attention/read/ack/state/time semantics. No shared event family, new producer fields, broker binding or recipient/contact API.

All old released OpenAPI/events/examples and VERSION are raw-byte fingerprinted in compatibility-baseline.json. Existing Contracts VERSION remains 0.7.0; producer/Web pins and all earlier reviewed candidates/manifests remain unchanged. The independent builder checks exact raw candidate/manifest bytes. Main validation uses Draft 2020-12 + format checks + OpenAPI validation + explicit cross-field semantics. Twelve new contract tests supplement the retained 36. These checks do not prove future HTTP authorization/database/broker/UI behavior.

## Contract semantics fixed for executable review

- Explicit estate on list/count; positive crop-health role matrix, history restricted to manager/auditor, shared acknowledgement manager only. PLATFORM_ADMIN still selects estate. Current issuer/subject/role/scope checked before receipt replay.
- All responses no-store; unknown fields/filters rejected, size 1–100 default 20, page*size <=10000. Stable inbox order attentionAt DESC,id DESC, history alertVersion DESC. Counts use one scoped consistent snapshot and include generatedAt.
- Initial alertVersion/attentionVersion=1; sourceVersion follows source (starts at zero for a new incident). Source revisions advance alertVersion even without new attention. Shared acknowledgement advances alertVersion; personal read does not. Same attention already read under a fresh key succeeds without a new effect. A second shared acknowledgement under a different key conflicts.
- Read and acknowledgement return the original successful AlertView on identical-key retry, even if current source later changes, only after reauthorization. The UI must refresh current state afterward; original success is not evidence that the returned snapshot is still current.
- Ordinary views contain minimal source facts, caller read state and shared acknowledgement boolean/time, never report text, identities of acknowledgers or others' read markers. Only protected acknowledgement history carries trusted issuer/opaque subject. No delivered flag or absent-user guarantee.
- Rule evaluation is local in the source transaction, future accepted incident revisions only. Eligibility/requalification/HIGH-to-CRITICAL reset attention; same-severity changes do not. Inactive alerts may be explicitly marked read; only ACTIVE alerts may be acknowledged. Existing source events/outbox are unchanged.
- Source timestamps remain distinct from raisedAt/attentionAt; canonical UTC microseconds in responses. No policy, real recipient, diagnosis or plantation fact is invented.

## Review decision needed

Accept/revise these exact four artifacts and authorize an independent local additive Contracts release (recommend 0.8.0), prior-0.7.0 API/VERSION archival, exact local promotion/release evidence and Operations/Web pins. This is a distinct executable acceptance gate, not repeated AN-D01–10 design approval. No remote publication or Git action is requested.

Persistence remains at schema/locking/test preparation until the candidate's schema is independently reviewed and stable. Pure domain/ports are independently prepared. After acceptance refresh the repository baseline, promote only the exact reviewed bytes, then continue AN-T03 onward by dependency. No existing-stack upgrade, REAL data, non-generated account rollout, external delivery, role/credential/private-configuration or AEO action follows.

AN-D07/08, WA D08/D09, II-D07/08, M2 and owner functional acceptance remain open. Generated-only test identities/resources require no private configuration. Existing accounts and the completed II-1 stack upgrade remain untouched.
