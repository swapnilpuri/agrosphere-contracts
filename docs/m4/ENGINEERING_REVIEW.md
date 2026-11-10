# M4 conforming executable review — 2026-11-09

Owner approval: Architecture M4_DELIVERY_APPROVAL_2026_11_09.json, package SHA-256 `befbee78062c2fcef6af0ea394fcc81be3e7638053deca142f136c66bc7cc93d`. D04 delegates this engineering gate; no new owner approval is required for conforming artifacts.

Reviewed four scoped operations: read frozen forecast/anomaly, model, evaluation, and closed-intent evidence composition. No public training/import/promotion/provider endpoint. Explicit dataset/mode, local-midnight cutoff and separate label cutoff, exact decimal strings, provenance/coverage/uncertainty, withheld/refused results and source references match D01–D10. Existing JWT/role/active-scope validation remains mandatory in implementations. No contract alone establishes signed-token enforcement.

One isolated OpenAPI candidate and eight positive forecast examples cover eligibility, withheld source/history, pending DRC, absent label, observed zero, threshold equality and flagged anomaly. Strict schemas, semantic negatives and intent injection tests executed. Before release, main validator PASS and all **97 tests PASS**, including the retained 92 tests. Initial M4 semantic tests required adding independently pinned timezone data on Windows; no source contract changed. Candidate OpenAPI validation and deterministic generation PASS.

Compatibility: AI was an empty foundation placeholder; archive its exact bytes and prior VERSION. All four collection-v2 schemas stay unchanged; no producer changes or shared event family. Old validators resolve the old AI placeholder and version through the new exact archive, while validating both releases. Preserve old manifests/reviews/candidates and all other APIs/events/examples. Local Contracts 0.13.0 only; no remote publication. Record exact candidate/example/input/archive hashes in MANIFEST.json and RELEASE_0_13_0.json. Re-run the full suite after promotion; any mismatch blocks consumer pins.

Cross-field runtime enforcement, authorization, persistence, browser and connected-demo acceptance remain E03–E10 requirements; this review does not count them as passed.
