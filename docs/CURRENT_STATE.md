# Current State

Last updated: 2026-08-12

## Product and implementation verdict

Knee Twin is intended to become a complete longitudinal, patient-specific knee twin combining external movement, internal/anatomical evidence, reviewed 3D reconstruction, registration, and validated virtual experiments. The repository currently implements the first external-observation slice: a reliable local, research-only squat movement-analysis workflow.

Engineering Milestones 0–8 are technically complete. A researcher can preserve a recording and raw observations, inspect quality-aware derived metrics, reopen synchronized historical evidence, compare explicitly selected compatible sessions, derive missing current analysis versions without replacing older versions, and export integrity results. Upload, publication, cleanup, operation provenance, backup/recovery, deletion, and loopback-only operating behavior now have explicit controls and tests.

The current “digital twin” is a versioned movement evidence record. It is not yet a patient-specific anatomical model, registered functional twin, medical device, or musculoskeletal/finite-element simulation. Milestone 6's participant-diversity evidence gate remains open.

## Working and verified

### Movement evidence

* Preserve original MP4, MOV, or WebM media, timestamped image/world landmarks, confidence, missing frames, and annotated overlay.
* Calculate versioned bilateral modeled knee flexion, complete repetitions, ROM, exact signed/absolute left-minus-right differences, and capture quality.
* Preserve source capture time, protocol, camera view/orientation, knee context, notes, coordinate conventions, units, confidence, and unavailable states.

### Longitudinal workflows

* Reopen any stored session with video, overlay, charts, repetition summaries, quality, provenance, and the model-relative skeleton.
* Compare a selected baseline/current pair only when local subject scope, knee context, protocol, view, orientation, model, coordinate convention, and analysis meaning match.
* Add missing current derivations without overwriting previous algorithm versions.
* Export actual/expected SHA-256, sizes, roles, versions, and verified/missing/mismatch/untracked states.

### Offline workstation reliability

* Stream request bodies in bounded chunks to hidden temporary files instead of accumulating the video in application memory.
* Extract into a hidden staging bundle and publish source, overlay, raw observations, and `artifact_manifest_v1.json` with one atomic directory rename.
* Atomically replace derived JSON and refresh the durable bundle manifest.
* Remove temporary/staging work on failure and startup; mark abandoned running operations as interrupted.
* Persist operation identifiers, input size, timing, stage, success/failure, and sanitized failure detail in SQLite; expose them through `GET /operations`.
* Require explicit confirmation for session deletion and stage filesystem removal around relational deletion.
* Enforce loopback CORS/frontend backend configuration and document encrypted-volume, de-identification, retention, backup, recovery, and incident requirements.
* Restore a copied database/artifact set in tests and verify every expected artifact hash.

### Contracts and testing

* Python/Pydantic remains authoritative for domain contracts and biomechanics; TypeScript validates browser inputs.
* Versioned JSON Schemas cover pose, kinematics, repetitions, quality, sessions, comparisons, reanalysis, and integrity export.
* Pure numerical, persistence, migration, API, corruption, cleanup, recovery, component-rendering, and real-Chromium degraded-workstation paths are tested.
* A measured 7.1-second, 213-frame fixture processed in 4,318 ms (49.3 frames/s) on the local Windows development workstation, supporting the current synchronous decision without establishing a capacity guarantee.

## Open evidence and product gaps

* Participant-diverse, consented or redistributable squat fixtures across views, clothing, lighting, and body types are not present.
* The current component/browser suite covers critical labeling and degraded operation, but not a full MediaPipe upload through a browser.
* Mid-extraction user cancellation is unavailable; process interruption reconciles on the next startup.
* Authentication, roles, multi-user isolation, remote access, connected clinical systems, and identifiable medical-data handling are intentionally not implemented or authorized.
* The canonical subject, knee, episode, timepoint, observation, annotation, reconstruction, registration, derivation, and experiment graph is not implemented.
* MRI, DICOM, arthroscopy, calibrated multi-view capture, reviewed anatomical reconstruction, functional registration, durable jobs, motion replay on anatomy, solver adapters, and independent scientific validation are not implemented.

## Safety and operating boundary

* Run one local worker and bind FastAPI and Next.js to loopback only.
* Store research cases only on an approved encrypted workstation volume and follow `docs/OFFLINE_SECURITY.md`.
* Import de-identified authorized research evidence only; this milestone does not approve identifiable or clinical data.
* Current values are monocular MediaPipe model estimates, not medically validated measurements.
* Observed, reconstructed, estimated, and simulated values must remain distinct; only observed/estimated movement values exist today.

## Verification baseline

Last verified locally on 2026-08-12:

* backend: 77 tests passed, including migrations, integrity, deletion, and recovery;
* backend Ruff lint: passed;
* frontend: 26 unit/component tests passed;
* frontend ESLint and TypeScript: passed;
* frontend production build: passed;
* Playwright Chromium: 1 offline/degraded workstation test passed.

CI downloads and checksum-verifies the pinned MediaPipe model and installs Chromium before executing the complete suites.

## Current priority

Milestone 9: introduce the additive canonical subject/knee/evidence and derivation graph, migrate every existing squat session into a default de-identified research subject with explicit bilateral observation targets, and retain every existing ID, endpoint, and artifact.

## Preserve

* Raw observations remain separate from derived measurements and relational metadata.
* Published evidence is immutable; derived versions are additive and hash-verifiable.
* Missing measurements remain unavailable rather than silently substituted.
* Comparison and registration fail closed when compatibility is not established.
* All outputs remain research-only and non-diagnostic.
