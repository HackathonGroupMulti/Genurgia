# Initial Squat Evidence-Pipeline Acceptance

Last evaluated: 2026-08-12

This gate covers the first external movement protocol. Passing it does not validate clinical accuracy or complete the Knee Twin product.

| Acceptance item | Status | Evidence |
| --- | --- | --- |
| Upload and preserve recording/raw pose | Pass | API/service integration tests and versioned artifacts. |
| Bilateral modeled knee flexion | Pass | Pure geometry, quality-state, filter, API, and real-fixture tests. |
| Complete repetition detection and ROM | Pass | Synthetic boundary tests and the attributed real squat fixture. |
| Exact bilateral differences | Pass | `bilateral-exact-differences-v1` unit and integration tests. |
| Capture-level quality and guidance | Pass | Synthetic pass/failure tests and a real framing-failure regression. |
| Capture metadata | Pass | API, artifact, migration, persistence, and contract tests. |
| Versioned contracts across Python/JSON Schema/TypeScript | Pass | Contract synchronization and frontend parser tests. |
| Model-backed CI execution | Pass | CI downloads and checksum-verifies the pinned MediaPipe model. |
| Historical session replay | Pass | Stored video, overlay, curves, repetitions, quality, provenance, and skeleton reopen through `/sessions/{id}`. |
| Participant/capture diversity | Blocked on fixture acquisition | One attributed real squat fixture is insufficient for body/view/population coverage. |

The technical Milestone 6 implementation is complete. The overall evidence gate remains open until the repository has consented or redistributable participant-diverse fixtures with provenance and expected outcomes.
