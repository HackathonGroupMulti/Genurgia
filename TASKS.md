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

* [ ] Define Recording and PoseSequence contracts.
* [ ] Add video upload.
* [ ] Add MediaPipe pose adapter.
* [ ] Extract timestamped landmarks.
* [ ] Preserve raw pose data.
* [ ] Add fixture video.
* [ ] Render or export annotated pose overlay.
* [ ] Add extraction tests.

## Milestone 2 — Knee-flexion series

* [ ] Implement tested vector-angle primitives.
* [ ] Implement knee-flexion calculation.
* [ ] Establish coordinate convention.
* [ ] Add confidence propagation.
* [ ] Add filtering.
* [ ] Expose knee-flexion time series through API.
* [ ] Graph left/right knee flexion in frontend.

## Milestone 3 — Repetition detection

* [ ] Define squat phase state model.
* [ ] Detect squat repetitions.
* [ ] Calculate rep start/bottom/end.
* [ ] Calculate ROM per repetition.
* [ ] Add synthetic and real fixture tests.

## Milestone 4 — Sessions

* [ ] Persist sessions.
* [ ] Persist recordings.
* [ ] Persist pose sequences.
* [ ] Persist analyses and versions.
* [ ] Display historical sessions.
* [ ] Compare sessions.

## Milestone 5 — Visualization

* [ ] Synchronize video with metrics chart.
* [ ] Render pose overlay.
* [ ] Display current-frame measurements.
* [ ] Add rep boundaries.
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
