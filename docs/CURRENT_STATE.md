# Current State

Last updated: 2026-08-12

## Product and implementation verdict

Knee Twin is an offline, expert-facing research platform intended to create a longitudinal, patient-specific knee twin from immutable evidence, reviewed anatomy, functional registration, and reproducible virtual experiments. It is not a diagnostic medical device.

Engineering Milestones 0–10 are technically complete. The repository now implements a reliable squat evidence workflow, an additive canonical subject/knee evidence graph, and controlled imports for pre-de-identified MRI DICOM series, authorized arthroscopy video, and standardized calibrated four-camera RGB captures. Existing squat sessions and endpoints remain operational.

The current “digital twin” is still an evidence system, not a reconstructed or simulated patient knee. No complete patient-specific segmentation, anatomical surface set, arthroscopy-to-MRI registration, calibrated motion replay on anatomy, or mechanical experiment has been validated. Milestone 6's participant-diversity gate and Milestone 10's paired-human-data gate remain open.

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

## Open evidence and product gaps

* Participant-diverse squat fixtures and approved paired MRI/arthroscopy/multi-view cases are absent.
* The identifier-tag screen does not detect private-tag, pixel, filename, structured-content, or indirect identifiers; upstream governed de-identification remains mandatory.
* MRI import preserves original DICOM but does not yet create a separately versioned computational volume.
* The current reconstruction, registration, experiment, and result records are contracts, not demonstrated scientific outputs.
* No complete-knee segmentation/reference workflow, scientific/web mesh generation, independent expert review, inter-rater evaluation, or surface-distance acceptance gate exists.
* Arthroscopy overlay/refinement/scoring, calibrated triangulation/anatomical registration, motion replay, durable jobs, and solver adapters remain unimplemented.
* Authentication, roles, connected clinical systems, identifiable-data handling, and clinical use remain unauthorized.

## API surface

Existing `/pose-sequences`, `/artifacts`, `/sessions`, and `/operations` endpoints remain. Canonical APIs include `/subjects`, `/knees`, `/episodes`, `/timepoints`, `/observations`, `/annotations`, `/reconstructions`, `/registrations`, `/derivations`, `/experiments`, and `/simulation-results`.

Multimodal imports are:

* `/observations/imports/mri`;
* `/observations/imports/arthroscopy`;
* `/observations/imports/multi-view`.

They currently execute synchronously and explicitly report that the durable job runner is deferred to Milestone 13.

## Verification baseline

Milestone 10 verification: 104 backend tests, Ruff, JSON Schema parity, Markdown lint, 30 frontend tests, ESLint, TypeScript, production build, one Playwright Chromium smoke test, and `git diff --check` pass locally. Generated fixtures cover spatial conventions, byte/hash preservation, identifiers, laterality, wrong modality, corrupt/inconsistent sources, timing bounds, calibration contracts, and API authorization.

## Current priority

Milestone 11: implement a reviewed manual-segmentation reference workflow, structure-complete reconstruction contracts, distinct label-map/scientific-mesh/web-mesh artifacts, anatomical landmarks/coordinates, correction provenance, independent review, and structure-specific evaluation gates. Paired-data acquisition proceeds as an external evidence track.

## Preserve

* Source evidence remains immutable and separate from annotations and every derived artifact.
* Observed, reconstructed, estimated, and simulated quantities remain visually and contractually distinct.
* Unknown provenance, individual properties, coordinate context, and validation remain explicit unknowns.
* Unsupported registration, comparison, or simulation fails closed.
* All outputs remain research-only and non-diagnostic.
