# Current State

Last updated:
2026-08-11

## Product and implementation verdict

Knee Twin's intended scope is a complete longitudinal, patient-specific knee twin combining external movement, internal/anatomical evidence, 3D reconstruction, and validated virtual experiments. The repository currently implements only the first external-observation slice: a working local prototype for longitudinal squat movement analysis.

Engineering Milestones 0–5 are implemented, but the squat slice is not yet feature-complete because explicit capture-quality reporting and named left/right difference metrics are absent. Historical comparison exists, but historical sessions cannot yet be reopened in the UI.

The current “digital twin” is a versioned movement record and synchronized replay. It is not yet a patient-specific anatomical model, registered functional twin, medical device, or musculoskeletal/finite-element simulation.

## Working and verified

### Video and raw observations

* Upload MP4, MOV, or WebM with a configurable `100 MiB` limit.
* Decode video and run MediaPipe Pose Landmarker in video mode.
* Preserve original media, timestamped normalized-image landmarks, model-relative world landmarks, confidence signals, and explicit missing-pose frames.
* Export and serve an annotated MP4 overlay.

### Derived biomechanics

* Calculate `knee-flexion-world-3d-v1` from same-frame hip, knee, and ankle world landmarks.
* Report `0°` as modeled extension and increasing values as modeled flexion.
* Propagate conservative landmark confidence and label missing, low-confidence, invalid, or degenerate samples explicitly.
* Apply the timestamp-preserving `centered-moving-average-v1` filter without filling unavailable centers.
* Detect complete bilateral squat cycles with the versioned phase state machine.
* Report rep start, peak-flexion bottom, end, duration, per-side maximum flexion, and per-side/mean ROM.

### Persistence and API

* Store raw and derived artifacts separately from relational metadata.
* Persist local session, recording, pose-sequence, analysis-version, and compact metric metadata in SQLite.
* Expose health, upload, artifact, knee-flexion, repetition, session-list, session-detail, and comparison endpoints.
* Preserve analysis provenance in Pydantic, TypeScript, and exported JSON Schema contracts.

### User interface

* Upload and analyze one squat recording.
* Replay the annotated overlay.
* Synchronize video time with knee curves, current-frame values, repetition context, and nearest skeleton frame.
* Seek with pointer or keyboard on the chart.
* Display repetition metrics, session history, and mean-ROM change from the preceding stored session.
* Display a rotatable, presentation-only world-landmark skeleton.

## Initial squat-slice requirements not implemented

* No versioned capture-quality report or actionable capture guidance.
* No explicit left/right asymmetry metric. `analysis/symmetry.py` remains a TODO placeholder.
* No historical session-detail/replay UI despite the backend detail endpoint.
* No user-selected comparison; comparison is fixed to the preceding stored squat session.
* No source capture timestamp, camera view/orientation, or standardized capture metadata.

## Major product capabilities not started

* Canonical person, knee/laterality, episode, timepoint, observation, and derivation model.
* Medical-image or authorized internal-imagery ingestion and governance.
* Reviewed patient-specific anatomical segmentation and 3D reconstruction.
* Multimodal spatial/temporal registration between anatomy, movement, and sensors.
* Tissue/property and loading models with explicit uncertainty.
* Solver-independent virtual-experiment contracts and simulation adapters.
* Scientific or clinical validation supporting diagnostic, predictive, or treatment claims.

## Prototype constraints and technical debt

* Analysis is synchronous and the upload route accumulates the complete file in memory before processing.
* SQLite schema creation has no migration/version mechanism.
* Artifact retention, deletion, integrity checking, backup, and recovery are undefined.
* Local storage has no authentication, user ownership, privacy controls, or multi-user isolation.
* The pose model is absent in CI, so MediaPipe-backed tests skip there; local deterministic math and contract tests still run.
* Real-video validation uses one short attributed squat fixture. It is integration evidence, not accuracy validation or population coverage.
* Frontend tests focus on parsers and timestamp selection; interactive upload/playback/history behavior lacks component and browser-level tests.
* Fixed repetition thresholds and the `0.5` confidence threshold are initial heuristics, not individualized or clinically validated cutoffs.
* Session `recorded_at` currently means upload time.

## Known failures

No confirmed runtime defect is currently recorded. The items above are scope gaps, validation gaps, or scale limitations rather than evidence that the implemented local happy path is broken.

## Verification baseline

Last verified locally on 2026-08-11:

* backend: 53 tests passed with the MediaPipe model installed;
* backend Ruff lint: passed;
* frontend: 19 tests passed;
* frontend ESLint: passed with zero warnings;
* frontend TypeScript check: passed;
* frontend production build: passed.

CI runs the same lint/build/unit suites, but currently does not download the MediaPipe model, so the model-backed extraction and real-video repetition tests skip in CI.

## Current priority

Milestone 6: complete the initial squat evidence pipeline with capture-quality reporting, exact named left/right difference metrics, richer capture metadata, and broader real-video validation. New schemas should anticipate later attachment to a specific knee, timepoint, observation, and coordinate context without prematurely implementing the complete medical-data model.

## Next actions

1. Specify `CaptureQualityReport` signals, thresholds, status semantics, units, and version.
2. Specify exact signed and absolute ROM/max-flexion difference metrics in `BIOMECHANICS.md`.
3. Implement those calculations as pure tested backend functions and versioned contracts.
4. Persist and display quality and left/right difference outputs.
5. Expand fixtures and make model-backed integration tests execute in CI.
6. Write the canonical knee/evidence ADR and privacy threat model before accepting internal or medical imagery.

## Important files

* `TASKS.md` — active implementation queue.
* `docs/ROADMAP.md` — scope review and phased delivery plan.
* `analysis/kinematics.py` — knee-flexion series and quality states.
* `analysis/reps.py` — bilateral squat segmentation and ROM.
* `analysis/symmetry.py` — unimplemented asymmetry placeholder.
* `app/services/pose_analysis.py` — synchronous upload/extraction orchestration.
* `app/services/kinematics.py` — derived artifact and metric orchestration.
* `app/persistence.py` — local SQLite metadata repository.
* `apps/web/components/video-upload.tsx` — current single-page analysis workflow.

## Preserve

* Raw observations remain separate from derived measurements and relational metadata.
* Python remains authoritative for biomechanical calculations.
* Missing measurements remain unavailable rather than interpolated or substituted silently.
* Analysis meaning remains explicitly versioned.
* All modeled values remain non-diagnostic.
