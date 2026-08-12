# Current State

Last updated: 2026-08-12

## Product and implementation verdict

Knee Twin is an offline, expert-facing research platform intended to create a longitudinal, patient-specific knee twin from immutable evidence, reviewed anatomy, functional registration, and reproducible virtual experiments. It is not a diagnostic medical device.

Engineering Milestones 0–13 are technically complete. The repository implements movement evidence, a canonical knee graph, multimodal imports, anatomy review packages, synthetic registration, durable local jobs, solver-neutral experiments, and reproducible synthetic motion-replay summaries. Existing squat sessions remain operational.

The current “digital twin” is still an evidence/review system, not a validated or simulated patient knee. Synthetic packages demonstrate complete structure handling but not anatomical accuracy. No human patient-specific segmentation, arthroscopy-to-MRI registration, calibrated motion replay, or mechanical experiment has been validated. Milestones 6, 10, and 11 retain external evidence gates.

## Working and verified

### Movement and longitudinal evidence

* Preserve original media, raw image/world landmarks, overlays, quality, confidence, missing states, repetition/ROM metrics, and exact named left-minus-right differences.
* Reopen synchronized historical evidence, compare explicitly selected compatible sessions, and reanalyze without replacing earlier outputs.
* Export expected/actual SHA-256 artifact integrity and missing/corrupt state.

### Canonical knee evidence graph

* `Subject` contains a de-identified research code and owns explicit left/right `Knee` records.
* `Episode` and `Timepoint` preserve longitudinal context and timezone-aware observation time.
* Immutable `Observation` records preserve modality, exact source reference/hash, acquisition manifest, authorization, quality, and knee targets.
* Versioned `Annotation`, `Reconstruction`, `Registration`, `Derivation`, `VirtualExperiment`, and `SimulationResult` records remain separate evidence classes.
* Subject ownership prevents cross-subject knee/timepoint combinations.
* Migration 4 maps legacy squat sessions into stable canonical records without changing legacy identifiers or artifacts.

### Multimodal acquisition

* `POST /observations/imports/mri` streams and preserves one exact DICOM ZIP, validates one MR series, checks declared DICOM laterality against the selected knee, records patient-LPS spatial metadata in millimetres, and rejects detected populated direct identifiers from the declared subset.
* `POST /observations/imports/arthroscopy` preserves video plus procedure, scope/camera, calibration, decoded timing, and expert visible-region metadata.
* `POST /observations/imports/multi-view` requires four decoded 1080p/60 fps views, per-camera intrinsic/extrinsic calibration, a visible synchronization event, capture-volume validation, and a standardized anatomical calibration pose.
* Each import publishes the source and typed acquisition manifest atomically, verifies SHA-256 integrity, then creates the canonical observation. Metadata failure rolls back the bundle.
* The DICOM research screen explicitly does not claim complete PS3.15 confidentiality-profile conformance.
* Imports use generated synthetic fixtures only. Approved paired human evidence has not been acquired.

### Offline reliability and operating controls

* Multipart uploads stream to bounded hidden temporary storage; observation imports have a configurable 2 GiB per-file default.
* Artifact bundles publish atomically with durable SHA-256 manifests.
* SQLite owns canonical/operation metadata, migrations are checksummed, and recovery/deletion behavior is tested.
* Both tiers reject non-loopback service configuration; sensitive research data requires an approved encrypted volume.

### Complete-anatomy review package

* `POST /reconstructions/imports/manual` requires all 22 v1 bone, cartilage, meniscus, ligament, tendon, and major knee-crossing musculotendon structures.
* It preserves reviewed/reference label maps, computational volume, per-structure PLY/GLB meshes, approved landmarks, corrections, and different primary/independent reviewers.
* Pure Dice, average symmetric surface distance, and Hausdorff-95 calculations preserve physical millimetre units and refuse missing structures.
* Draft structure thresholds force `thresholds-unapproved`, `expert-reviewed`, and `in_review` even for a perfect synthetic fixture.

### Synthetic registration core

* Calibrated DLT triangulation recovers capture-space points and refuses insufficient/degenerate camera evidence.
* Proper rigid landmark fitting records anatomy-from-capture transforms and residuals in millimetres; deterministic perturbation reports 95% translation/rotation sensitivity.
* Calibrated expert-seeded arthroscopy PnP reports anatomy-from-camera transforms and reprojection errors in pixels.
* Functional frames preserve coverage, confidence, exclusions, residuals, uncertainty, and validation tier.
* Arthroscopy refinement is refused without calibration, parallax, coverage, and residual evidence; research tissue scoring requires independent raters and is non-diagnostic.

### Durable jobs and replay

* Migration 5 stores queued/running/succeeded/failed/cancelled state, progress, request, result, logs, attempts, cancellation, timestamps, and failure detail.
* A single immediate-transaction claimant, interruption recovery, cancellation/retry, and SHA-256-verified atomic result publication are tested.
* `ExperimentDefinitionV1` requires immutable hashes, coordinates/transforms, sourced units/assumptions, software/container versions, outputs, sensitivity, and validation tier.
* Synthetic replay records residual RMS, exclusions, transform uncertainty, anatomical constraint violations, and registration sensitivity plus a canonical definition hash.

## Open evidence and product gaps

* Participant-diverse squat fixtures and approved paired MRI/arthroscopy/multi-view cases are absent.
* The identifier-tag screen does not detect private-tag, pixel, filename, structured-content, or indirect identifiers; upstream governed de-identification remains mandatory.
* MRI import preserves original DICOM but does not yet create a separately versioned computational volume.
* The current reconstruction, registration, experiment, and result records are contracts, not demonstrated scientific outputs.
* The package validates synthetic/review artifacts but does not generate segmentation or meshes; no domain-approved human reference workflow, taxonomy/landmark protocol, or structure thresholds exist.
* Numerical registration/replay exists only for synthetic evidence; no approved human overlay/refinement or animated anatomical replay and no mechanical solver adapter exists.
* Authentication, roles, connected clinical systems, identifiable-data handling, and clinical use remain unauthorized.

## API surface

Existing `/pose-sequences`, `/artifacts`, `/sessions`, and `/operations` endpoints remain. Canonical APIs include `/subjects`, `/knees`, `/episodes`, `/timepoints`, `/observations`, `/annotations`, `/reconstructions`, `/registrations`, `/derivations`, `/experiments`, and `/simulation-results`.

Multimodal imports are:

* `/observations/imports/mri`;
* `/observations/imports/arthroscopy`;
* `/observations/imports/multi-view`.

They currently execute synchronously and explicitly report that the durable job runner is deferred to Milestone 13.

Reviewed reconstruction packages use `/reconstructions/imports/manual`.

## Verification baseline

Milestone 13 verification: 125 backend tests, Ruff, JSON Schema parity, Markdown lint, 34 frontend tests, ESLint, TypeScript, production build, and `git diff --check` pass locally. New tests cover migration upgrade, queue/claim/cancel/retry/recovery/failure, result integrity, replay evidence, definition hashes, and evidence-tier contracts.

## Current priority

Milestone 14: add solver-neutral kinematic, musculoskeletal, contact-hypothesis, finite-element, and intervention adapter contracts in increasing claim order, with strict input capability/refusal checks and no silent population constants.

## Preserve

* Source evidence remains immutable and separate from annotations and every derived artifact.
* Observed, reconstructed, estimated, and simulated quantities remain visually and contractually distinct.
* Unknown provenance, individual properties, coordinate context, and validation remain explicit unknowns.
* Unsupported registration, comparison, or simulation fails closed.
* All outputs remain research-only and non-diagnostic.
