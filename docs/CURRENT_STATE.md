# Current State

Last updated: 2026-08-12

## Product and implementation verdict

Knee Twin is intended to become a complete longitudinal, patient-specific knee twin combining external movement, internal/anatomical evidence, reviewed 3D reconstruction, registration, and validated virtual experiments. The repository currently implements the first external-observation slice: a local, research-only squat movement-analysis workflow.

Engineering Milestones 0–7 are technically complete. A researcher can preserve a squat recording and raw pose observations, inspect quality-aware derived metrics, reopen the synchronized historical evidence, explicitly select compatible sessions for comparison, derive missing current analysis versions without replacing older versions, and export an artifact integrity manifest.

The current “digital twin” is a versioned movement evidence record. It is not yet a patient-specific anatomical model, registered functional twin, medical device, or musculoskeletal/finite-element simulation. Milestone 6's participant-diversity evidence gate remains open.

## Working and verified

### Evidence and biomechanics

* Upload MP4, MOV, or WebM and preserve the original media, timestamped image/world landmarks, confidence, missing frames, and annotated overlay.
* Calculate versioned, confidence-aware bilateral modeled knee flexion with explicit unavailable states and timestamp-preserving filtering.
* Detect complete squat repetitions and report boundaries, duration, per-side flexion/ROM, exact signed and absolute left-minus-right differences, and confidence.
* Produce `capture-quality-v1` from decode, pose coverage, bilateral availability, gap, framing, and complete-cycle evidence.
* Preserve source capture time, protocol, camera view/orientation, knee context, and notes.

### Persistence and longitudinal workflows

* Store large immutable artifacts outside SQLite and relational session, recording, pose-sequence, analysis-version, and metric metadata inside SQLite.
* Apply ordered, checksummed migrations while preserving legacy local sessions.
* Reopen any stored session at `/sessions/{id}` with original evidence, overlay, charts, repetition summaries, quality, provenance, and model-relative skeleton.
* Compare an explicitly selected baseline/current pair only when local subject scope, knee context, protocol, view, orientation, coordinate convention, pose model, and repetition-analysis meaning are compatible.
* Add missing current derivations without overwriting earlier versioned artifacts.
* Export session manifests containing artifact roles, references, sizes, versions, missing states, and SHA-256 hashes.

### Contracts and UI

* Python/Pydantic remains authoritative for domain contracts and biomechanics.
* Versioned JSON Schemas cover pose, kinematics, repetitions, quality, session detail/list, comparisons, reanalysis, and export manifests.
* TypeScript validates browser inputs and renders server-derived values without recalculating biomechanics.
* Playback time synchronizes annotated video, curves, current measurements, repetition boundaries, and the presentation-only rotatable skeleton.

## Open evidence and product gaps

* Participant-diverse, consented or redistributable squat fixtures across views, clothing, lighting, and body types are not present.
* Upload handling still buffers the bounded request in memory; artifact bundles are not yet atomically published with durable manifests.
* Retention, deletion, encrypted backup, recovery, and cancellation-safe cleanup behavior remain to be implemented.
* Interactive component/browser coverage and structured operational failure provenance remain limited.
* The canonical subject, knee, episode, timepoint, observation, annotation, reconstruction, registration, derivation, and experiment graph is not implemented.
* MRI, DICOM, arthroscopy, calibrated multi-view capture, reviewed anatomical reconstruction, registration, jobs, motion replay on anatomy, solver adapters, and scientific validation are not implemented.

## Safety and operating boundary

* The application is a local, single-user research prototype with no authentication or multi-user isolation.
* Current values are monocular MediaPipe model estimates, not medically validated measurements.
* Fixed repetition and confidence thresholds are initial versioned heuristics, not individualized clinical cutoffs.
* Identifiable or medical research data must not be imported until Milestone 8 security/governance controls and the modality-specific authorization rules are satisfied.

## Verification baseline

Last verified locally on 2026-08-12:

* backend: 66 tests passed with contract synchronization and longitudinal workflow coverage;
* backend Ruff lint: passed;
* frontend: 22 tests passed;
* frontend ESLint: passed with zero warnings;
* frontend TypeScript check: passed;
* frontend production build: passed.

CI downloads and checksum-verifies the pinned MediaPipe model before running the complete backend suite.

## Current priority

Milestone 8: reliable offline workstation behavior—bounded temporary uploads, atomic artifact publication, durable integrity verification, retention/recovery controls, structured failures, and broader UI/workflow testing. Participant-diverse fixture acquisition continues as a parallel Milestone 6 evidence gate.

## Preserve

* Raw observations remain separate from derived measurements and relational metadata.
* Missing measurements remain unavailable rather than silently interpolated or substituted.
* Analysis meaning and coordinate conventions remain explicit and versioned.
* Comparison and registration fail closed when compatibility is not established.
* Observed, reconstructed, estimated, and simulated values remain visibly distinct.
* All outputs remain research-only and non-diagnostic.
