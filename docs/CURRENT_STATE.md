# Current State

Last updated:
2026-08-10

## Working

* Repository initialized.
* Project documentation exists.
* Next.js 16 App Router frontend runs from `apps/web`.
* FastAPI backend runs from `services/biomechanics`.
* `GET /health` returns the typed biomechanics service status.
* The server-rendered homepage calls the backend and renders connected or unavailable state.
* Root npm workspace commands cover frontend development and validation.
* The Python project installs in editable mode with test and lint tools.
* GitHub Actions validates frontend and backend jobs.

## Partially working

* Analysis modules document their future responsibilities but intentionally contain no implementation.

## Broken

Nothing known.

## Important files

* `AGENTS.md`
* `CONTEXT.md`
* `TASKS.md`
* `docs/PRODUCT.md`
* `docs/ARCHITECTURE.md`
* `docs/DATA_MODEL.md`
* `docs/BIOMECHANICS.md`
* `docs/DECISIONS.md`
* `apps/web/app/page.tsx`
* `apps/web/lib/biomechanics-api.ts`
* `services/biomechanics/app/main.py`
* `services/biomechanics/app/api/health.py`
* `.github/workflows/ci.yml`

## Tests

Verified locally on 2026-08-10:

* backend: 4 tests passed;
* backend Ruff lint: passed;
* frontend: 5 tests passed;
* frontend ESLint: passed with zero warnings;
* frontend TypeScript check: passed;
* frontend production build: passed;
* live production vertical slice: API health payload, frontend HTTP 200, and rendered connected state all passed.

## Current task

Milestone 1: Define the video-to-landmarks boundary without implementing downstream kinematics.

## Next

1. Define Recording and PoseSequence contracts.
2. Specify coordinate, timestamp, landmark, confidence, model-name, and model-version fields.
3. Add contract validation tests.
4. Only then add video upload and the MediaPipe pose-provider adapter.

## Do not redo

The foundational architectural decisions documented in `DECISIONS.md` should not be casually replaced.
