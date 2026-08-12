# Knee Twin Tasks

This is the active implementation queue. Knee Twin's product scope is a complete longitudinal knee twin. The completed squat milestones are the first external-movement analysis slice and must not be described as completion of the overall product.

## Completed foundation

### Milestone 0 — Foundation

* [x] Next.js and FastAPI skeleton, health-check vertical slice, tests, lint, CI, and setup documentation.

### Milestone 1 — Video to landmarks

* [x] Upload supported video formats.
* [x] Extract timestamped MediaPipe image and world landmarks.
* [x] Preserve raw observations, original recording, and annotated overlay.
* [x] Version contracts and test extraction with deterministic media.

### Milestone 2 — Knee-flexion series

* [x] Implement and test 3D vector-angle primitives.
* [x] Calculate confidence-aware left/right modeled knee flexion.
* [x] Preserve timestamps, explicit unavailable states, and filter provenance.
* [x] Expose and graph versioned knee-flexion series.

### Milestone 3 — Repetition detection

* [x] Define and test the bilateral squat phase state machine.
* [x] Detect complete repetitions and start/bottom/end timestamps.
* [x] Calculate per-repetition left/right and mean ROM.
* [x] Validate synthetic signals and one attributed real-video fixture.

### Milestone 4 — Sessions

* [x] Persist local session, recording, pose-sequence, analysis-version, and summary-metric metadata.
* [x] Keep videos and large analysis artifacts outside SQLite.
* [x] Display session history and comparison with the preceding session.

### Milestone 5 — Visualization

* [x] Synchronize annotated video, chart cursor, current measurements, and skeleton frame.
* [x] Display repetition boundaries and per-repetition metrics.
* [x] Add a presentation-only rotatable world-landmark skeleton.

## Program A — reliable external movement evidence

### Milestone 6 — Complete the initial squat analysis slice

#### Capture quality

* [ ] Define and document a versioned `CaptureQualityReport` contract.
* [ ] Define tested quality signals: decode validity, pose-detection coverage, bilateral valid-knee coverage, maximum unavailable gap, and body-framing checks.
* [ ] Separate blocking failures from warnings and informational limitations.
* [ ] Provide actionable recording guidance in the upload flow.
* [ ] Persist the quality report and expose it in session detail/history.

#### Exact left/right differences

* [ ] Approve exact v1 definitions in `docs/BIOMECHANICS.md` before implementation.
* [ ] Implement pure, tested per-repetition signed and absolute ROM differences in degrees.
* [ ] Implement pure, tested maximum-flexion differences in degrees.
* [ ] Add versioned artifact/API/TypeScript/JSON Schema fields without a generic clinical “score.”
* [ ] Persist and display session-level summaries with confidence and units.

#### Capture and validation completeness

* [ ] Record source capture time separately from upload time when available.
* [ ] Record protocol/exercise, camera view/orientation, laterality context, and optional notes.
* [ ] Expand real fixtures across capture conditions and failure cases with clear licenses/consent.
* [ ] Run MediaPipe-backed integration tests in CI instead of silently skipping them when the model is absent.
* [ ] Define and complete an explicit acceptance checklist.

### Milestone 7 — Longitudinal movement workflows

* [ ] Add a frontend session-detail route backed by the existing `GET /sessions/{id}` API.
* [ ] Reopen historical evidence, overlay, charts, repetitions, quality, and provenance.
* [ ] Let users select compatible sessions instead of only the immediately preceding session.
* [ ] Define compatibility rules for person, knee/laterality, protocol, view, coordinate convention, and analysis version.
* [ ] Reanalyze preserved raw observations into new versioned outputs without overwriting prior results.
* [ ] Add session export and artifact-integrity reporting.

### Milestone 8 — Reliable local research product

* [ ] Stream uploads to bounded temporary storage.
* [ ] Add a SQLite schema-migration mechanism before changing persisted schemas.
* [ ] Define artifact deletion, retention, cleanup, backup, and recovery behavior.
* [ ] Add frontend component and browser tests for critical happy and degraded paths.
* [ ] Add structured logging and visible analysis-failure provenance.
* [ ] Measure processing cost; introduce background jobs only if justified.
* [ ] Complete a privacy/security review before storing identifiable or medical data.
* [ ] Add authentication and production persistence only when a connected or multi-user deployment is authorized.

## Program B — knee evidence foundation

### Milestone 9 — Canonical knee and evidence model

* [ ] Model person, knee/laterality, episode, timepoint, observation, protocol, modality, and derivation relationships.
* [ ] Require source provenance, authorization/consent context, capture time, coordinate system, units, and quality status where applicable.
* [ ] Distinguish immutable source evidence from annotations, reviewed corrections, derived measurements, reconstructions, and simulations.
* [ ] Prevent incompatible identity, laterality, timepoint, modality, or coordinate data from being silently combined.
* [ ] Define de-identification and research-import rules before accepting medical evidence.
* [ ] Write ADRs and migrations for the canonical model before implementation.

### Milestone 10 — Multimodal observation ingestion

* [ ] Define modality adapters and manifests for external video/sensors, volumetric imaging, and authorized internal imagery.
* [ ] Preserve original files and essential acquisition metadata without lossy conversion.
* [ ] Implement modality-specific validation, quality, coverage, and failure reports.
* [ ] Start with offline de-identified research fixtures; do not connect clinical systems by default.
* [ ] Add expert annotations as versioned overlays rather than modifications to source evidence.

## Program C — patient-specific anatomical and functional twin

### Milestone 11 — Reviewed 3D anatomical reconstruction

* [ ] Select the first supported imaging protocol and anatomical structures with domain-expert input.
* [ ] Implement or integrate versioned segmentation with manual review/correction provenance.
* [ ] Generate patient-specific surfaces/volumes with anatomical landmarks and explicit coordinate systems.
* [ ] Quantify reconstruction quality against appropriate reference data.
* [ ] Label generic, fitted, reconstructed, and directly observed geometry distinctly in the UI.
* [ ] Register partial internal imagery to anatomy only when evidence supports the transform and coverage is visible.

### Milestone 12 — Functional multimodal registration

* [ ] Add calibrated multi-view motion and selected sensor inputs.
* [ ] Define transforms from capture coordinates to anatomical coordinates with error estimates.
* [ ] Register compatible movement timepoints to versioned anatomical twins.
* [ ] Define supported joint coordinate systems and test every transformation/calculation.
* [ ] Report uncertainty and refuse unsupported registration rather than inventing alignment.

## Program D — virtual knee experiments

### Milestone 13 — Solver-independent experiment contracts

* [ ] Define anatomy, properties, loading, boundary conditions, solver, output, validation-tier, and reproducibility contracts.
* [ ] Require every assumed property and load to state its source; prohibit silent population defaults.
* [ ] Preserve complete experiment inputs and outputs as a derivation graph.
* [ ] Add sensitivity and uncertainty analysis as first-class outputs.

### Milestone 14 — First validated simulation adapter

* [ ] Choose one narrow scientific question and reference dataset before selecting a solver.
* [ ] Integrate a replaceable musculoskeletal or finite-element adapter appropriate to that question.
* [ ] Compare outputs with defined reference measurements and document error and applicability.
* [ ] Present results as simulated hypotheses unless validation supports stronger language.
* [ ] Do not use simulation output as autonomous diagnosis or treatment advice.

## Program E — validation and responsible use

### Milestone 15 — Intended-use validation pathway

* [ ] Select narrowly defined research or decision-support uses with clinical/biomechanics experts.
* [ ] Establish representative datasets, independent evaluation, and acceptance thresholds.
* [ ] Define human review, audit, cybersecurity, governance, and incident procedures.
* [ ] Determine regulatory obligations before clinical claims or prospective care use.
* [ ] Ensure every public product claim matches the demonstrated validation tier.

## Research questions

* Which internal-imaging modalities and acquisition protocols provide the geometry needed for the first anatomical twin?
* Which tissue properties and boundary conditions can be measured for an individual versus represented only as uncertain assumptions?
* How should arthroscopy/internal imagery be registered to preoperative imaging and what surface coverage can be demonstrated?
* Which virtual experiment can deliver useful evidence with the fewest unsupported inputs?
* What longitudinal changes can be distinguished from acquisition, segmentation, registration, or solver variation?
