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

* [x] Define and document a versioned `CaptureQualityReport` contract.
* [x] Define tested quality signals: decode validity, pose-detection coverage, bilateral valid-knee coverage, maximum unavailable gap, and body-framing checks.
* [x] Separate blocking failures from warnings and informational limitations.
* [x] Provide actionable recording guidance in the upload flow.
* [x] Persist the quality report and expose it in session detail/history.

#### Exact left/right differences

* [x] Approve exact v1 definitions in `docs/BIOMECHANICS.md` before implementation.
* [x] Implement pure, tested per-repetition signed and absolute ROM differences in degrees.
* [x] Implement pure, tested maximum-flexion differences in degrees.
* [x] Add versioned artifact/API/TypeScript/JSON Schema fields without a generic clinical “score.”
* [x] Persist and display session-level summaries with confidence and units.

#### Capture and validation completeness

* [x] Record source capture time separately from upload time when available.
* [x] Record protocol/exercise, camera view/orientation, laterality context, and optional notes.
* [x] Add synthetic success/failure coverage and a licensed real-fixture framing failure.
* [ ] Add participant-diverse licensed real fixtures across views, clothing, lighting, and body types.
* [x] Run MediaPipe-backed integration tests in CI instead of silently skipping them when the model is absent.
* [x] Define the explicit acceptance checklist in `docs/SQUAT_ACCEPTANCE.md`.
* [ ] Complete the participant-diversity evidence gate in that checklist.

### Milestone 7 — Longitudinal movement workflows

* [x] Add a frontend session-detail route backed by the existing `GET /sessions/{id}` API.
* [x] Reopen historical evidence, overlay, charts, repetitions, quality, and provenance.
* [x] Let users select compatible sessions instead of only the immediately preceding session.
* [x] Define compatibility rules for local subject scope, knee/laterality, protocol, view, coordinate convention, and analysis version.
* [x] Reanalyze preserved raw observations into new versioned outputs without overwriting prior results.
* [x] Add session export and artifact-integrity reporting.

### Milestone 8 — Reliable local research product

* [x] Stream uploads to bounded temporary storage.
* [x] Add a SQLite schema-migration mechanism before changing persisted schemas. (Delivered early in Milestone 6.)
* [x] Define artifact deletion, retention, cleanup, backup, and recovery behavior.
* [x] Add frontend component and browser tests for critical presentation and degraded-workstation paths.
* [x] Add structured and visible analysis-operation failure provenance.
* [x] Measure processing cost; retain synchronous processing while current measurements support it.
* [x] Document the offline privacy/security baseline and keep identifiable/medical ingestion prohibited.
* [ ] Add authentication and production persistence only when a connected or multi-user deployment is authorized.

## Program B — knee evidence foundation

### Milestone 9 — Canonical knee and evidence model

* [x] Model subject, knee/laterality, episode, timepoint, observation, annotation, reconstruction, registration, derivation, experiment, and result relationships.
* [x] Require source provenance, authorization context, capture time, coordinate context, units/quality metadata where applicable, and explicit unknown legacy hashes.
* [x] Distinguish immutable source evidence from annotations, reviewed corrections, derived measurements, reconstructions, registrations, and simulations.
* [x] Prevent incompatible subject, knee, episode/timepoint, and registration data from being silently combined.
* [x] Define and enforce the de-identified research-code/import boundary before medical evidence ingestion.
* [x] Add checksummed migration 4 and ADR-016 for the canonical graph.

### Milestone 10 — Multimodal observation ingestion

* [x] Define typed adapters/manifests for MRI DICOM series, authorized arthroscopy video, and calibrated four-camera RGB captures.
* [x] Preserve exact source files and acquisition metadata in immutable, SHA-256-manifested bundles without lossy conversion.
* [x] Validate MRI identity/orientation/spacing/de-identification subset, arthroscopy timing/calibration evidence, and four-view calibration/synchronization evidence.
* [x] Start with generated synthetic fixtures and keep clinical-system connectivity prohibited by default.
* [x] Keep expert annotations in the separately versioned canonical annotation model rather than modifying observations.
* [x] Publish versioned Pydantic, JSON Schema, and TypeScript acquisition contracts and fail-closed API tests.
* [ ] Add selected sensor adapters only after a supported sensor protocol and scientific purpose are approved.
* [ ] Obtain approved, paired MRI, arthroscopy, and calibrated multi-view human cases through a research partner.
* [ ] Pass the human paired-data acquisition and modality-quality evidence gate; synthetic validation alone cannot close it.

## Program C — patient-specific anatomical and functional twin

### Milestone 11 — Reviewed 3D anatomical reconstruction

* [x] Define the complete 22-structure target for bones, cartilage, menisci, cruciate/collateral ligaments, tendons, and approved major knee-crossing musculotendon groups.
* [x] Implement a versioned manual-segmentation package with correction history and independent reviewer provenance.
* [x] Preserve reviewed and independent label maps, computational volume, scientific PLY meshes, web GLB meshes, landmarks, and DICOM patient-LPS coordinates separately.
* [x] Implement pure Dice, average symmetric surface distance, and Hausdorff-95 evaluation in physical millimetres against a reference label map.
* [x] Require complete structure coverage and attribute generic, fitted, machine-segmented, expert-reviewed, and patient-specific geometry distinctly in TypeScript contracts.
* [x] Keep arthroscopy registration/refinement outside anatomy import; it remains a separate Milestone 12 reconstruction/registration layer.
* [ ] Obtain domain-expert approval for the exact structure taxonomy, landmark protocol, and per-structure acceptance thresholds.
* [ ] Evaluate independent experts and inter-rater variation on approved human reference cases.
* [ ] Add a replaceable machine-assisted segmentation adapter only after training/reference data and validation exist.
* [ ] Close the patient-specific validation gate; draft thresholds keep imported geometry `expert-reviewed` and `in_review`.

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
