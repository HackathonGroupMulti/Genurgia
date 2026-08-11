# Current State

Last updated:
2026-08-10

## Working

* Milestones 0 through 3: local upload, raw pose preservation, modeled knee flexion, and squat repetition analysis.
* Versioned bilateral squat state machine with standing, descending, bottom, and ascending phases.
* Named thresholds, hysteresis, duration limits, per-side minimum ROM, and bounded missing-data gaps.
* Complete-cycle start, peak-flexion bottom, and end timestamps.
* Per-repetition left/right maximum flexion, left/right and mean ROM, duration, and conservative confidence.
* Separate `squat_repetitions.json` artifact linked to the source knee-flexion analysis.
* FastAPI repetition endpoint and matching Next.js proxy/client contract.
* Frontend rep spans and bottom markers on the angle chart plus a per-repetition metrics table.
* Synthetic exact-signal tests and a CC BY 3.0 real-person squat integration fixture.

## Partially working

* Local artifacts are durable files but do not yet have persistent relational session metadata.
* Pose extraction and derived analyses remain synchronous for the local first vertical slice.
* Fixed phase thresholds are initial product heuristics, not individualized or clinically validated thresholds.

## Broken

Nothing known.

## Important files

* `analysis/reps.py` — pure bilateral phase state machine and per-repetition calculations.
* `app/schemas/repetitions.py` — versioned repetition artifact/API contract.
* `app/services/kinematics.py` — raw pose to knee series to repetition artifact orchestration.
* `app/api/pose_sequences.py` — extraction and derived-analysis endpoints.
* `apps/web/components/knee-flexion-chart.tsx` — angle series with repetition boundaries.
* `apps/web/components/repetition-summary.tsx` — per-repetition metrics.
* `data/fixtures/squat-real.webm` — attributed real-video integration fixture.

## Tests

Verified locally on 2026-08-10:

* backend: 46 tests passed, including exact synthetic state transitions and two repetitions from a real MediaPipe video;
* backend Ruff lint: passed;
* frontend: 14 tests passed;
* frontend ESLint: passed with zero warnings;
* frontend TypeScript check: passed;
* frontend production build: passed.

The MediaPipe integration tests skip only where the external model has not been downloaded. Pure numerical, state-machine, orchestration, schema, and API tests always run.

## Current task

Milestone 4: persist session metadata and enable historical session comparison.

## Next

1. Define the smallest Session, Recording, and Analysis metadata persistence model.
2. Add local relational persistence without moving large artifacts into the database.
3. Associate the existing upload and analyses with sessions.
4. Expose session history and comparison interfaces.
5. Display session history and a reproducible comparison in the frontend.

## Do not redo

* Preserve raw observations independently from derived values.
* Keep biomechanics calculations in framework-independent Python modules.
* Keep `0° = modeled extension` unless a new version explicitly supersedes it.
* Require bilateral valid filtered values for the v1 squat state machine.
* Do not interpolate across missing values or present estimates as clinical measurements.
