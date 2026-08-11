# Current State

Last updated:
2026-08-10

## Working

* Milestones 0 through 5 are complete as a local squat-analysis vertical slice.
* Upload and timestamped MediaPipe raw-observation preservation.
* Annotated pose-overlay playback.
* Confidence-aware three-dimensional modeled left/right knee flexion.
* Bilateral squat repetition boundaries and per-repetition ROM.
* SQLite-backed session history and exact longitudinal comparison metrics.
* One browser playback clock shared by video, chart cursor, current measurements, repetition context, and skeleton frame.
* Pointer and keyboard seeking on the knee-flexion timeline.
* Lightweight rotatable SVG replay of preserved MediaPipe world landmarks with no 3D framework dependency.
* Versioned Pydantic, TypeScript, and JSON Schema contracts across API boundaries.

## Partially working

* Capture-quality checks are limited to landmark confidence and missing-data behavior.
* Session time represents upload time; source capture time and capture setup metadata are not collected.
* SQLite/local artifact storage and synchronous analysis target a local single-user MVP.
* The 3D skeleton is a model-relative visualization, not calibrated reconstruction.

## Broken

Nothing known.

## Important files

* `apps/web/components/video-upload.tsx` — upload orchestration and shared playback clock.
* `apps/web/components/knee-flexion-chart.tsx` — synchronized, seekable metric timeline.
* `apps/web/components/current-frame-metrics.tsx` — nearest timestamped left/right measurements.
* `apps/web/components/skeleton-replay.tsx` — rotatable world-landmark projection.
* `apps/web/lib/pose-contracts.ts` — raw pose artifact validation and frame lookup.
* `apps/web/lib/knee-flexion-contracts.ts` — analysis validation and sample lookup.
* `services/biomechanics/analysis/` — framework-independent biomechanics and repetition logic.
* `services/biomechanics/app/persistence.py` — durable local session metadata.

## Tests

Verified locally on 2026-08-10:

* backend: 53 tests passed;
* backend Ruff lint: passed;
* frontend: 19 tests passed, including synchronized nearest-frame/sample selection;
* frontend ESLint: passed with zero warnings;
* frontend TypeScript check: passed;
* frontend production build: passed.

## Current task

All defined MVP milestones are complete. The next work is product hardening rather than an unfinished milestone.

## Next

1. Define capture-quality checks and actionable recording guidance.
2. Add capture timestamp and setup metadata.
3. Extract exercise-specific configuration behind a generic movement-analysis strategy.
4. Evaluate calibrated/multi-view reconstruction before interpreting the skeleton beyond visualization.
5. Add authentication and production persistence only when moving beyond the local single-user scope.

## Do not redo

* Keep raw observations separate from derived measurements and relational metadata.
* Keep biomechanics calculations out of the browser; nearest-sample selection and SVG projection are presentation only.
* Treat MediaPipe world depth and skeleton scale as model-relative.
* Keep all modeled values explicitly non-diagnostic.
