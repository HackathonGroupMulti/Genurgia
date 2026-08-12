# Architecture

Knee Twin's target architecture supports a complete longitudinal knee twin. The currently implemented modular monolith is the first external-video analysis slice; it should evolve through explicit evidence, reconstruction, registration, and simulation boundaries rather than treating squat analysis as the whole domain.

Knee Twin begins as a modular monolith with one web application and one biomechanics API:

Client / Next.js
↓
FastAPI application
↓
Analysis orchestration
↓
Biomechanics analysis modules
↓
Stored raw observations + derived metrics

The preferred data pipeline is:

Raw Video
↓
Pose Detection
↓
Raw Pose Sequence
↓
Normalization / Filtering
↓
Joint Kinematics
↓
Repetition Segmentation
↓
Per-Rep Metrics
↓
Session Metrics
↓
Interpretation / Visualization

## Boundaries

* HTTP routes must not contain biomechanics math.
* Analysis functions should be independently testable.
* Raw observations and derived values are separate layers.
* The UI consumes API/domain results rather than recreating biomechanics calculations.
* External pose-estimation systems sit behind a replaceable adapter boundary.
* Musculoskeletal and finite-element solvers sit behind replaceable simulation adapters rather than spreading into application code.
* Persistence models are not required to be identical to API response models.
* Large video and artifact storage remains conceptually separate from relational metadata.
* Every derived object is traceable through a versioned derivation graph to immutable source evidence.
* Person, knee/laterality, episode, timepoint, modality, and coordinate context must be explicit before multimodal evidence is combined.
* Direct observations, expert annotations, reconstructions, estimates, and simulations are separate data classes.

The local filesystem implementation of the artifact-storage boundary stores each extraction bundle: original recording, versioned raw pose-sequence JSON, annotated MP4, and separate derived JSON artifacts. SQLite stores structured session, source, analysis-version, and compact metric metadata with references to those artifacts.

Pose extraction is synchronous in the first local vertical slice. `PoseAnalysisService` owns orchestration, while the HTTP route handles multipart transport and maps explicit domain failures to API errors. The `PoseProvider` protocol keeps MediaPipe replaceable.

## Dependency Direction

Preferred:

UI → API → Application services → Analysis/domain modules

Analysis/domain modules must NOT depend on FastAPI or Next.js.

## Milestone 0 interface

`GET /health` returns a typed JSON response with `status` and `service`. The Next.js server reads the backend base URL from `BIOMECHANICS_API_URL`, calls this route, validates the response shape, and renders the connection state. This server-side call avoids exposing internal service URLs to browser code.

## Milestone 1 interfaces

* `POST /pose-sequences` accepts one MP4, MOV, or WebM multipart upload and returns recording metadata plus a pose-sequence summary.
* `GET /artifacts/{pose_sequence_id}/{filename}` serves locally preserved artifacts through the storage boundary.
* Next.js proxies uploads and artifact reads so the browser does not need the backend service address.
* Versioned JSON Schemas in `packages/contracts` describe both the summary response and full raw artifact.

## Milestone 2 interfaces

* `POST /pose-sequences/{id}/knee-flexion` derives a versioned analysis from the preserved pose artifact.
* The resulting `knee_flexion.json` is stored separately from `pose_sequence.json` and includes calculation, confidence, filtering, coordinate, and source-model versions.
* The Next.js upload flow invokes the derived-analysis endpoint only after raw pose preservation succeeds.
* The frontend validates the response and graphs valid left/right samples. Missing and low-confidence samples remain visible as gaps rather than being interpolated.

## Milestone 3 interfaces

* `POST /pose-sequences/{id}/squat-repetitions` derives a versioned repetition analysis from the separately stored knee-flexion artifact. It regenerates knee flexion from raw pose observations if that intermediate artifact is absent.
* The pure analysis layer owns phase transitions, acceptance thresholds, boundaries, ROM, and confidence propagation; HTTP and UI code only orchestrate and present those results.
* The resulting `squat_repetitions.json` remains separate from both `pose_sequence.json` and `knee_flexion.json`.
* The frontend calls the repetition endpoint after knee-flexion analysis, validates the versioned response, and presents boundaries and metrics without recalculating them.

## Milestone 4 interfaces

* SQLite stores relational metadata for sessions, recordings, pose sequences, analysis versions, and compact summary metrics. Videos, frame series, overlays, and derived JSON remain behind `LocalArtifactStore`.
* Pose extraction creates one squat session and links its recording and pose sequence in one database transaction after artifacts are safely written.
* Derived-analysis services register versioned artifact references and update session status. Same-version reanalysis replaces its metrics; completed status does not regress.
* `GET /sessions` returns newest-first history, `GET /sessions/{id}` returns one stored graph, and `GET /sessions/comparison` returns exact longitudinal metric comparisons.
* Next.js proxies the session endpoints. The browser validates their contracts and displays server-computed metrics rather than reading SQLite or analysis artifacts directly.

## Milestone 5 visualization

* The annotated video element is the playback-clock source. Its current time drives a chart cursor, nearest timestamped knee samples, repetition context, and nearest raw pose frame.
* Seeking the SVG chart updates the video time; arrow keys provide accessible `100 ms` timeline steps.
* The browser fetches and validates the already-preserved raw pose artifact for visualization. It does not calculate biomechanical metrics.
* `SkeletonReplay` rotates and projects MediaPipe world landmarks into SVG with a small presentation-only transform. It adds no Three.js/WebGL dependency and does not persist a new derived artifact.
* Model-relative 3D replay is visually separated from calibrated measurement claims.

## Current runtime characteristics

The current request path is synchronous:

```text
browser upload
→ Next.js proxy
→ FastAPI buffers the bounded upload
→ MediaPipe decodes and extracts all frames
→ artifacts and session metadata are written
→ browser requests knee-flexion and repetition derivations
```

This is acceptable for a local single-user prototype, but it creates three explicit limits:

* the full upload is retained in request memory before analysis;
* the client coordinates multiple sequential analysis requests;
* there is no job identity, progress, cancellation, retry, or worker isolation.

Background jobs are not automatically required. First measure supported duration, resolution, memory, latency, failure recovery, and concurrency. Introduce an asynchronous job boundary only when those measurements justify it.

## Planned initial-slice completion boundaries

Milestone 6 should add the following without putting domain logic in HTTP or UI layers:

* a pure/versioned capture-quality analysis consuming pose/video metadata and existing quality states;
* pure/versioned exact left/right difference calculations consuming accepted repetition outputs;
* application-service orchestration that persists new artifacts and compact session metrics;
* API and frontend contracts that expose statuses, units, provenance, and actionable guidance.

Additional movement protocols should use a strategy boundary for protocol-specific landmarks, phases, metrics, and quality rules while reusing evidence, artifact, persistence, and visualization infrastructure.

## Target knee-twin boundaries

The broader system should add capabilities in this dependency order:

```text
immutable multimodal evidence
→ reviewed annotations and segmentations
→ patient-specific anatomical reconstruction
→ explicit coordinate transforms and multimodal registration
→ functional measurements and boundary conditions
→ solver-independent virtual experiment
→ replaceable simulation adapter
→ versioned outputs, uncertainty, and validation evidence
```

* An evidence-ingestion boundary owns modality-specific parsing, acquisition metadata, quality, authorization context, and original artifacts.
* A reconstruction boundary owns segmentations, meshes, anatomical landmarks, review state, and reconstruction quality. A renderer does not make geometry patient-specific.
* A registration boundary owns transformations and their error/coverage. No consumer may infer alignment from matching timestamps or labels alone.
* A virtual-experiment boundary owns anatomy versions, assumed properties, loads, boundary conditions, solver settings, sensitivity analysis, and reproducibility.
* Solver adapters may target OpenSim or finite-element tools, but solver-native types must not become the canonical domain model.
* Clinical connectivity, identifiable medical storage, and prospective decision support require separately authorized security, governance, validation, and deployment designs.

## Persistence evolution

SQLite currently initializes tables with `CREATE TABLE IF NOT EXISTS`; it has no migration ledger. Any persisted-schema change must first introduce a migration/version mechanism and upgrade tests. Artifact schemas and analysis meanings remain separately versioned and should not be conflated with database migration versions.
