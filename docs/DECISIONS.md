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
