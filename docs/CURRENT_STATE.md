# Current State

Last updated:
2026-08-10

## Working

* Milestone 0 frontend/backend skeleton and health-check vertical slice.
* Browser video upload through a Next.js server proxy.
* FastAPI `POST /pose-sequences` for MP4, MOV, and WebM inputs up to a configurable limit.
* Replaceable `PoseProvider` protocol with a MediaPipe Pose Landmarker video adapter.
* Monotonic timestamped extraction of normalized-image and world landmarks.
* Explicit empty pose lists when a frame has no detection.
* Local preservation of original recording, versioned raw pose JSON, and annotated MP4.
* Artifact download/streaming API and annotated replay in the frontend.
* Versioned Pydantic/TypeScript contracts and exported JSON Schemas.
* Checksum-verified MediaPipe model download script.
* Deterministic small MP4 fixture and real MediaPipe integration coverage when the model is present.
* GitHub Actions frontend and backend validation.

## Partially working

* Local artifacts are not yet represented by persistent relational session metadata.
* Pose extraction is synchronous and intended for the local first vertical slice.

## Broken

Nothing known.

## Important files

* `analysis/pose.py` — provider-independent raw observation types.
* `analysis/mediapipe_pose.py` — MediaPipe video adapter and overlay export.
* `app/services/pose_analysis.py` — upload-to-artifact orchestration.
* `app/schemas/pose.py` — versioned recording and pose contracts.
* `app/storage.py` — local artifact-storage boundary.
* `app/api/pose_sequences.py` — upload and artifact HTTP routes.
* `apps/web/components/video-upload.tsx` — upload and extraction result UI.
* `packages/contracts/*.schema.json` — exported cross-boundary schemas.
* `scripts/download_pose_model.py` — pinned model acquisition.

## Tests

Verified locally on 2026-08-10:

* backend: 18 tests passed, including real MediaPipe extraction with the local model;
* backend Ruff lint: passed;
* frontend: 8 tests passed;
* frontend ESLint: passed with zero warnings;
* frontend TypeScript check: passed;
* frontend production build: passed.
* live Next.js-proxied upload: 12/12 fixture frames detected; raw JSON and overlay both returned HTTP 200.

The MediaPipe integration test skips in environments where the external model has not been downloaded. Deterministic provider, persistence, contract, and API tests always run.

## Current task

Milestone 2: derive tested, confidence-aware left/right knee-flexion series from raw pose observations.

## Next

1. Implement pure vector-angle primitives with synthetic exact-geometry tests.
2. Implement `0° = full modeled extension` knee flexion.
3. Define missing/low-confidence behavior without fabricating values.
4. Add filtering as a distinct derived layer.
5. Expose and graph left/right series only after numerical behavior is verified.

## Do not redo

* Preserve raw observations independently from derived values.
* Keep biomechanics calculations in framework-independent Python modules.
* Keep MediaPipe and future simulation systems behind adapters.
* Do not introduce queues or cloud artifact storage without measured need.
