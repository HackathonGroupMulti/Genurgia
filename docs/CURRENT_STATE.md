# Current State

Last updated: 2026-08-12

## Product and implementation verdict

Knee Twin is intended to become a complete longitudinal, patient-specific knee twin combining external movement, internal/anatomical evidence, reviewed 3D reconstruction, registration, and validated virtual experiments. The repository implements a reliable local squat evidence workflow plus the additive canonical knee-evidence and derivation graph required to expand beyond movement video.

Engineering Milestones 0–9 are technically complete. Existing squat sessions and artifacts remain operational and now map to explicit de-identified subject, left/right knee, timepoint, and immutable video-observation records. The API can also store separately versioned annotations, reconstructions, registrations, derivations, experiment definitions, and simulation-result records, with subject/knee compatibility checks.

The current “digital twin” remains a versioned movement evidence record and empty-capable canonical graph. No patient-specific anatomical reconstruction, arthroscopy evidence, calibrated multi-view registration, or mechanical simulation has been produced or validated. Milestone 6's participant-diversity evidence gate remains open.

## Working and verified

### Movement and longitudinal evidence

* Preserve original media, raw image/world landmarks, overlay, quality, confidence, missing states, repetition/ROM metrics, and exact named left-minus-right differences.
* Reopen synchronized historical evidence and compare explicitly selected compatible sessions.
* Derive missing current versions without overwriting old artifacts and export expected/actual SHA-256 integrity state.

### Canonical knee evidence graph

* `Subject` stores a de-identified research code only and automatically owns one left and one right `Knee`.
* `Episode` and `Timepoint` enforce subject ownership and timezone-aware observation time.
* `Observation` is immutable and records modality, source reference/hash state, acquisition manifest, authorization, quality, and explicit knee targets.
* `Annotation` preserves author class, taxonomy/version payload, review state, and same-observation supersession.
* `Reconstruction` preserves knee/timepoint, geometry evidence class, structures, artifacts, coordinate system, and review state.
* `Registration` requires source/target references and coordinate systems, a 4×4 transform, method, coverage, error, and uncertainty.
* `Derivation` records typed inputs/outputs, algorithm/version, configuration, code revision, and environment.
* `VirtualExperiment` and `SimulationResult` records preserve definitions, validation tier, outputs, sensitivity, validation evidence, and artifacts without claiming a solver has run.
* Subject ownership prevents cross-subject knee/timepoint observations, reconstructions, and experiments.

### Legacy migration and compatibility

* Checksummed migration 4 creates canonical tables without replacing session tables.
* The default subject code is `LOCAL-RESEARCH-SUBJECT`; its left/right knees have stable UUIDs.
* Each existing/new squat session reuses its UUID for a canonical timepoint and its recording UUID for a bilateral video observation.
* Existing IDs, endpoints, artifact references, and replay behavior remain unchanged.
* Durable bundle hashes populate canonical video-observation source hashes when verifiable; an absent legacy hash remains explicit `null`.
* Selected comparison now checks canonical subject and knee targets in addition to capture and analysis meaning.

### Offline reliability and operating controls

* Multipart uploads stream through Next.js and FastAPI to bounded hidden temporary storage.
* Initial bundles and derived artifacts publish atomically with durable SHA-256 manifests.
* SQLite retains operation timing and sanitized success/failure provenance; interrupted work reconciles on startup.
* Confirmed deletion, encrypted-volume requirements, retention, whole-set backup, recovery, and incident handling are documented and tested.
* Both tiers reject non-loopback service configuration.

## Open evidence and product gaps

* Participant-diverse squat fixtures and approved paired MRI/arthroscopy/multi-view cases are not present.
* MRI/DICOM and arthroscopy import validation, de-identification reports, calibration evidence, and modality-specific quality are not implemented.
* The current canonical reconstruction, registration, experiment, and simulation-result tables contain contract fixtures only in tests; they do not demonstrate scientific capability.
* No complete knee segmentation, scientific/web mesh workflow, anatomical landmark review, arthroscopy overlay/refinement, calibrated movement registration, anatomical replay, or solver adapter exists.
* Authentication, roles, multi-user isolation, connected clinical systems, identifiable medical-data handling, and clinical use remain unauthorized.

## API surface

Existing `/pose-sequences`, `/artifacts`, `/sessions`, and `/operations` endpoints remain. Canonical endpoints now include:

* `/subjects`, `/knees`, `/episodes`, and `/timepoints`;
* `/observations` and `/observations/{id}`;
* `/annotations`, `/reconstructions`, and `/registrations`;
* `/derivations` and `/derivations/{id}`;
* `/experiments` and `/simulation-results`.

Milestone 10 adds `/observations/imports` jobs only after modality validation and safe publication exist.

## Verification baseline

Last verified locally on 2026-08-12:

* backend: 90 numerical, migration, canonical API, integrity, deletion, and recovery tests passed;
* backend Ruff lint and Pydantic/JSON Schema synchronization: passing;
* frontend: 28 TypeScript contract/unit/component tests, ESLint, and production build passed;
* Playwright Chromium offline-workstation smoke test: retained from Milestone 8.

## Current priority

Milestone 10: implement de-identified MRI/DICOM and arthroscopy imports, calibration/acquisition manifests, modality-specific validation/quality reports, and the standardized calibrated four-camera protocol using synthetic or appropriately licensed fixtures. Approved paired human cases remain an external evidence dependency.

## Preserve

* Raw/source evidence remains immutable and separate from annotations and every derived class.
* Unknown provenance, hashes, coordinate context, and individual properties remain explicit unknowns.
* Existing identifiers and artifacts remain stable across canonical migration.
* Registration and comparison fail closed when compatibility is not established.
* All outputs remain research-only and non-diagnostic.
