# Architectural Decisions

## ADR-001 — Preserve raw pose observations

Status:
Accepted

Decision:

Store raw pose-landmark output separately from derived biomechanical metrics.

Reason:

Analysis algorithms will improve.

Historical sessions should be capable of being reanalyzed without losing the original pose observations.

Rejected alternative:

Store only final metrics.

Why rejected:

It destroys useful information and tightly couples recorded sessions to the original analysis algorithm.

---

## ADR-002 — Python owns biomechanics calculations

Status:
Accepted

Decision:

Biomechanical and numerical-analysis code lives in the Python backend and does not live in Next.js.

Reason:

Python has the stronger scientific/numerical ecosystem and keeps numerical domain logic centralized.

---

## ADR-003 — Start as a modular monolith

Status:
Accepted

Decision:

Use one Next.js frontend and one FastAPI backend.

Do not create distributed microservices for the MVP.

Reason:

The current domain does not justify distributed-system complexity.

---

## ADR-004 — OpenSim is a future adapter

Status:
Accepted

Decision:

Do not make OpenSim a dependency of the MVP architecture.

Design normalized motion outputs so a future musculoskeletal-simulation adapter can consume them.

Reason:

The initial problem is movement reconstruction and longitudinal kinematics.

---

## ADR-005 — Local artifact storage behind a boundary

Status:
Accepted

Decision:

Store Milestone 1 recordings, raw pose JSON, and annotated videos in a local filesystem implementation addressed through artifact references.

Reason:

Local development needs durable, inspectable artifacts without introducing cloud infrastructure. `LocalArtifactStore` isolates filesystem details so object storage can replace it later without changing pose extraction.

Rejected alternative:

Store videos and frame-level landmark arrays directly in a relational database.

Why rejected:

Large binary and time-series artifacts have different access patterns from searchable relational metadata.

---

## ADR-006 — Synchronous pose extraction for the first vertical slice

Status:
Accepted

Decision:

Run pose extraction inside the upload request during Milestone 1.

Reason:

The local single-user slice does not yet justify a queue or background-job system. The analysis service boundary allows asynchronous execution to be introduced later if measured video duration or concurrency requires it.

---

## ADR-007 — Initial knee flexion uses MediaPipe world landmarks

Status:
Accepted

Decision:

Calculate `knee-flexion-world-3d-v1` from same-frame hip, knee, and ankle world landmarks. Do not silently fall back to normalized image coordinates when world landmarks are missing.

Reason:

World landmarks provide one internally consistent three-dimensional coordinate space and avoid mixing normalized image x/y with model-relative image depth. Explicit unavailability is safer and more reproducible than changing coordinate systems per frame.

Known limitation:

MediaPipe world landmarks remain monocular model estimates and are not calibrated motion-capture measurements.

---

## ADR-008 — Initial squat segmentation requires bilateral valid measurements

Status:
Accepted

Decision:

Drive `bilateral-squat-state-machine-v1` with the mean of aligned, valid, filtered left and right knee-flexion values. Reject candidates that cross excessive missing-data gaps; do not substitute one knee for the other or interpolate unavailable measurements.

Reason:

Repetition boundaries and per-side ROM should have one reproducible meaning. Silently changing from bilateral to unilateral evidence would make results incomparable and hide capture-quality failures.

Rejected alternative:

Continue a repetition from whichever side remains visible.

Why rejected:

It changes the phase signal according to availability and can create boundaries or ROM metrics from asymmetrical evidence without telling the consumer.

---

## ADR-009 — SQLite owns local session metadata, not large artifacts

Status:
Accepted

Decision:

Use a local SQLite repository for Milestone 4 session, recording, pose-sequence, analysis-version, and compact metric metadata. Continue storing videos and detailed JSON artifacts behind `LocalArtifactStore` and retain only their references relationally.

Reason:

The local single-user MVP needs durable relationships and queryable history, but does not need a database server. SQLite provides transactions and portable relational queries while respecting the existing artifact-storage boundary.

Rejected alternative:

Derive session history by scanning artifact directories on every request.

Why rejected:

Directory structure is not a reliable metadata model, does not naturally represent analysis-version history, and makes longitudinal queries increasingly brittle.

Operational boundary:

This choice is for local MVP persistence. Multi-user deployment, concurrent workers, authentication, and remote backup would require a production persistence design.

---

## ADR-010 — Keep initial synchronized 3D replay presentation-only

Status:
Accepted

Decision:

Render the current MediaPipe world-landmark frame as a lightweight rotatable SVG in the browser. Use video time as the shared playback clock and do not create a second biomechanics or persistence pipeline for this view.

Reason:

Milestone 5 needs synchronized inspection, not a calibrated simulation engine. Reusing preserved raw observations proves the interaction and keeps numerical analysis authoritative in Python without adding a heavy 3D dependency.

Rejected alternative:

Introduce Three.js or OpenSim as a requirement for the first skeleton replay.

Why rejected:

Neither dependency improves the underlying monocular evidence by itself. Both would add substantial complexity before capture calibration or musculoskeletal-simulation requirements exist.

Limitation:

SVG perspective, rotation, depth, and scale are visualization choices. They are not biomechanical outputs and must not be interpreted as calibrated anatomy.

---

## ADR-011 — Model the complete knee as a versioned evidence and derivation graph

Status:
Accepted

Decision:

Treat squat pose analysis as the first external-observation workflow, not the boundary of Knee Twin. Future internal/anatomical observations, reviewed segmentations, 3D reconstructions, registrations, virtual experiments, and simulation results remain distinct versioned objects linked to immutable source evidence for a specific person, knee/laterality, episode, and timepoint.

Reason:

A patient-specific knee twin will combine modalities with different coverage, coordinate systems, uncertainty, and authority. One mutable model would hide provenance and make it easy to confuse observed, reconstructed, estimated, and simulated quantities.

Rejected alternative:

Store a single current 3D knee object and update it in place as new data or algorithms arrive.

Why rejected:

It prevents reproducibility, obscures which evidence supported a result, and cannot safely represent competing segmentations, registrations, assumptions, or solver versions.

Operational boundary:

This decision establishes the target domain direction; it does not authorize connected clinical ingestion or diagnostic claims. The current squat slice remains a local research prototype. Medical-data handling, simulation intended uses, and clinical deployment require separate governance, security, validation, and regulatory decisions.

---

## ADR-012 — Capture quality uses named observable signals

Status:
Accepted

Decision:

Implement `capture-quality-v1` as named decode, detection-coverage, bilateral-validity, unavailable-interval, framing, and complete-cycle signals. Derive one overall pass/warning/fail result from the individual statuses and preserve every signal, threshold criterion, explanation, and guidance item.

Reason:

A single opaque quality score would hide why a recording is unusable and imply precision unsupported by the evidence. Named signals can be tested, versioned, recalibrated, and explained to the researcher.

Operational boundary:

V1 thresholds are initial product heuristics. Passing the report means the capture met configured input criteria; it does not validate kinematic or clinical accuracy.

---

## ADR-013 — Bilateral comparisons are exact left-minus-right differences

Status:
Accepted

Decision:

Report signed and absolute ROM and maximum-flexion differences in degrees. Signed values are always left minus right. Do not emit a generic asymmetry score or percentage in v1.

Reason:

Exact named operands, direction, and units are reproducible and avoid suggesting a clinically meaningful normalized score without a validated denominator or interpretation.

---

## ADR-014 — Longitudinal comparisons fail closed and reanalysis is additive

Status:
Accepted

Decision:

Compare only explicitly selected sessions that share the declared subject scope, target context, protocol, camera view, orientation, pose model, coordinate convention, and repetition-analysis meaning. Return named incompatibilities instead of a numeric delta when compatibility is not established. Reanalysis may reuse an existing current version or add a missing current version, but it must not overwrite earlier algorithm versions.

Reason:

Longitudinal changes are interpretable only when the compared evidence and algorithms mean the same thing. Additive derivation preserves reproducibility and lets future algorithms be evaluated against the exact earlier result.

Temporary boundary:

The current repository has one local research-subject scope rather than canonical subject and knee records. Unknown capture context therefore fails compatibility. Milestone 9 replaces this temporary identity basis with explicit subject, knee, episode, and timepoint relationships.

---

## ADR-015 — Publish local artifact bundles atomically with durable hashes

Status:
Accepted

Decision:

Stream uploads into bounded hidden temporary files, build initial evidence bundles in hidden staging directories, write `artifact_manifest_v1.json`, and expose the bundle with one atomic rename. Atomically replace later derived artifacts and refresh the manifest. Persist processing-operation status and sanitized failure stage in SQLite. Keep short squat extraction synchronous until measurements justify a durable job boundary.

Reason:

An interrupted request must not expose a bundle that looks complete, and silent file corruption must be distinguishable from a missing or untracked artifact. The measured short-fixture workload does not justify a queue, broker, or distributed worker for this local single-user stage.

Operational boundary:

Startup cleanup assumes one local worker. Long anatomical, registration, and simulation work requires the durable job runner planned for Milestone 13 rather than extending this synchronous mechanism.

---

## ADR-016 — Add the canonical graph without replacing legacy sessions

Status:
Accepted

Decision:

Add canonical `Subject`, `Knee`, `Episode`, `Timepoint`, `Observation`, `Annotation`, `Reconstruction`, `Registration`, `Derivation`, `VirtualExperiment`, and `SimulationResult` records alongside the existing squat-session model. Reuse legacy session and recording UUIDs for migrated timepoints and observations, target both default knees explicitly, and keep existing endpoints and artifacts operational.

Reason:

The movement slice is useful evidence and must remain available while the domain expands. An additive migration avoids a high-risk rewrite, preserves reproducibility, and provides explicit identity/laterality/provenance constraints for every future modality.

Rejected alternative:

Replace sessions with the new graph and regenerate identifiers.

Why rejected:

That would break stored URLs, artifact references, comparisons, and external records while providing no scientific benefit. Canonical relationships can mature independently and legacy adapters can be removed only after a separately tested compatibility plan.

---

## ADR-017 — Preserve multimodal sources and their native coordinate meaning

Status:
Accepted

Decision:

Import MRI DICOM series, arthroscopy video, and calibrated four-camera capture through modality-specific adapters. Preserve exact sources and typed acquisition manifests in immutable atomic bundles. Keep `dicom-patient-lps-mm`, `arthroscope-image-pixels`, and `capture-volume-right-handed-mm` distinct; require a later versioned registration to combine them. Refuse DICOM with populated values in the declared direct-identifier subset and explicitly avoid claiming full PS3.15 de-identification conformance.

Reason:

Lossy normalization at ingestion would destroy evidence needed for future reconstruction and recalculation. Treating different coordinate systems as interchangeable would create unsupported alignment. A narrow, visible identifier screen is safer than overstating a partial implementation as formal confidentiality-profile compliance.

Rejected alternative:

Convert every source directly into one current knee model during upload and discard the input-specific representation.

Why rejected:

That would couple ingestion to immature segmentation/registration algorithms, hide uncertainty and correction history, and make new algorithms impossible to reproduce against the exact original evidence.

Operational boundary:

Synthetic tests close the software gate only. Approved paired human-data acquisition, governed de-identification review, and modality-specific scientific validation remain open evidence gates. Imports remain synchronous until the durable local job runner is introduced in Milestone 13.
