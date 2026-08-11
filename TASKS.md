# Knee Twin Tasks

## Milestone 0 — Foundation

* [x] Initialize Next.js frontend.
* [x] Initialize Python/FastAPI backend.
* [x] Establish local development commands.
* [x] Add `GET /health` endpoint.
* [x] Make frontend successfully call backend.
* [x] Add backend tests.
* [x] Add frontend tests where appropriate.
* [x] Add lint/type-check commands.
* [x] Add CI.
* [x] Document setup in README.
* [x] Verify clean install from repository instructions.
* [x] Update `CURRENT_STATE.md`.

## Milestone 1 — Video to landmarks

* [x] Define Recording and PoseSequence contracts.
* [x] Add video upload.
* [x] Add MediaPipe pose adapter.
* [x] Extract timestamped landmarks.
* [x] Preserve raw pose data.
* [x] Add fixture video.
* [x] Render or export annotated pose overlay.
* [x] Add extraction tests.

## Milestone 2 — Knee-flexion series

* [x] Implement tested vector-angle primitives.
* [x] Implement knee-flexion calculation.
* [x] Establish coordinate convention.
* [x] Add confidence propagation.
* [x] Add filtering.
* [x] Expose knee-flexion time series through API.
* [x] Graph left/right knee flexion in frontend.

## Milestone 3 — Repetition detection

* [x] Define squat phase state model.
* [x] Detect squat repetitions.
* [x] Calculate rep start/bottom/end.
* [x] Calculate ROM per repetition.
* [x] Add synthetic and real fixture tests.

## Milestone 4 — Sessions

* [x] Persist sessions.
* [x] Persist recordings.
* [x] Persist pose sequences.
* [x] Persist analyses and versions.
* [x] Display historical sessions.
* [x] Compare sessions.

## Milestone 5 — Visualization

* [ ] Synchronize video with metrics chart.
* [ ] Render pose overlay.
* [ ] Display current-frame measurements.
* [x] Add rep boundaries.
* [ ] Explore 3D skeleton replay.

## Later

* exercise abstraction;
* calibration;
* anthropometrics;
* improved multi-view reconstruction;
* richer confidence modeling;
* gait;
* OpenSim adapter;
* higher-fidelity simulation.
