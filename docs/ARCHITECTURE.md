# Architecture

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
* Future OpenSim integration sits behind a biomechanics/simulation adapter rather than spreading into application code.
* Persistence models are not required to be identical to API response models.
* Large video and artifact storage remains conceptually separate from relational metadata.

Milestone 1 uses a local filesystem implementation of the artifact-storage boundary. Each successful extraction bundle contains the original recording, a versioned raw pose-sequence JSON artifact, and an annotated MP4. Relational session persistence remains deferred.

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
