# Current State

Last updated:
2026-08-10

## Working

* Milestone 0 frontend/backend skeleton and health-check vertical slice.
* Milestone 1 upload, MediaPipe extraction, timestamped raw landmark preservation, and overlay replay.
* Pure three-dimensional vector and included-angle primitives.
* Versioned `0° = modeled extension` knee-flexion calculation from MediaPipe world landmarks.
* Left and right series with original timestamps and explicit unavailable states.
* Conservative hip/knee/ankle confidence propagation and a documented `0.5` validity threshold.
* Five-sample centered moving-average output that excludes missing and low-confidence centers.
* Separate versioned `knee_flexion.json` artifact derived from preserved raw observations.
* FastAPI knee-flexion endpoint and Next.js proxy.
* Frontend left/right SVG graph with gaps for unavailable observations.
* Versioned Pydantic, TypeScript, and JSON Schema contracts.

## Partially working

* Local artifacts are not yet represented by persistent relational session metadata.
* Pose extraction and derived analysis are synchronous for the local first vertical slice.
* The committed media fixture validates extraction but is not biomechanical ground truth or a squat repetition fixture.

## Broken

Nothing known.

## Important files

* `analysis/angles.py` — pure vector and knee-flexion math.
* `analysis/confidence.py` — conservative confidence propagation.
* `analysis/filtering.py` — timestamp-preserving smoothing behavior.
* `analysis/kinematics.py` — left/right series derivation and quality states.
* `app/services/kinematics.py` — raw-artifact to derived-artifact orchestration.
* `app/schemas/kinematics.py` — versioned API/artifact contract.
* `app/api/pose_sequences.py` — pose extraction, knee flexion, and artifact routes.
* `apps/web/components/knee-flexion-chart.tsx` — valid-sample graph.
* `packages/contracts/knee-flexion-analysis-v1.schema.json` — shared schema.

## Tests

Verified locally on 2026-08-10:

* backend: 37 tests passed, including exact synthetic angles and real MediaPipe extraction;
* backend Ruff lint: passed;
* frontend: 11 tests passed;
* frontend ESLint: passed with zero warnings;
* frontend TypeScript check: passed;
* frontend production build: passed;
* live production proxies: 12/12 valid left samples, 12/12 valid right samples, and derived artifact HTTP 200.

The MediaPipe integration test skips only where the external model has not been downloaded. Numerical, confidence, filtering, orchestration, schema, and API tests always run.

## Current task

Milestone 3: detect squat repetitions and calculate per-repetition ROM.

## Next

1. Define a squat phase state model against synthetic signals.
2. Establish named thresholds and minimum durations without hiding magic constants.
3. Detect start, bottom, and end timestamps.
4. Calculate per-repetition left/right ROM with quality information.
5. Validate against deterministic pose-series fixtures before using real recordings.

## Do not redo

* Preserve raw observations independently from derived values.
* Keep biomechanics calculations in framework-independent Python modules.
* Keep `0° = modeled extension` unless a new version explicitly supersedes it.
* Never substitute normalized image coordinates when world landmarks are unavailable.
* Do not graph low-confidence values as valid measurements.
