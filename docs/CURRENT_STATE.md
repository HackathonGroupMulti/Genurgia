# Current State

Last updated:
2026-08-10

## Working

* Milestones 0 through 4: upload, pose extraction, modeled knee flexion, squat repetitions, and durable session history.
* SQLite metadata persistence for sessions, recordings, pose sequences, analysis versions, and searchable summary metrics.
* Original videos and time-series JSON remain in the separate local artifact store rather than SQLite.
* Monotonic session status from pose extraction through complete repetition analysis.
* Idempotent same-version reanalysis that replaces summary metrics without duplicating analysis metadata.
* `GET /sessions`, `GET /sessions/{id}`, and `GET /sessions/comparison` read interfaces.
* Newest-first historical session table with rep count, modeled mean ROM, change from the preceding session, and confidence.
* Versioned Pydantic, TypeScript, and JSON Schema session contracts.

## Partially working

* Session time currently represents upload/analysis time because capture timestamps are not collected yet.
* SQLite and local artifacts are appropriate for a local single-user MVP, not multi-user deployment.
* Pose extraction and derived analyses remain synchronous.
* The video and metric chart are not yet time-synchronized.

## Broken

Nothing known.

## Important files

* `app/persistence.py` — SQLite schema and session repository.
* `app/schemas/sessions.py` — session history and comparison contracts.
* `app/api/sessions.py` — session read endpoints.
* `app/services/pose_analysis.py` — persists recording and pose-sequence metadata.
* `app/services/kinematics.py` — persists analysis versions and summary metrics.
* `apps/web/components/session-history.tsx` — historical comparison table.
* `packages/contracts/session-list-v1.schema.json` — shared history contract.
* `packages/contracts/session-comparison-v1.schema.json` — shared comparison contract.

## Tests

Verified locally on 2026-08-10:

* backend: 53 tests passed, including persistence graph, reanalysis, resource cleanup, API history, and comparison behavior;
* backend Ruff lint: passed;
* frontend: 17 tests passed;
* frontend ESLint: passed with zero warnings;
* frontend TypeScript check: passed;
* frontend production build: passed.

## Current task

Milestone 5: synchronize video playback and movement metrics.

## Next

1. Share video current time with the metric visualization.
2. Render a current-time cursor and current left/right measurements.
3. Make existing pose overlay playback the primary synchronized replay.
4. Evaluate a small 3D world-landmark skeleton replay without adding heavy infrastructure.
5. Verify interaction behavior and responsive presentation.

## Do not redo

* Keep raw observations and derived artifacts outside relational metadata.
* Preserve versioned analysis records and source-version metric labels.
* Keep comparison definitions exact: v1 change is current mean modeled ROM minus the preceding stored session's mean modeled ROM.
* Do not present longitudinal changes as diagnoses or treatment conclusions.
