# Data Model

The following entities describe the current movement-analysis slice and the target knee-evidence domain. The first implementation does not need every conceptual entity represented as a separate SQL table. Persistence choices should follow practical access patterns while keeping source observations distinct from annotations, derived results, reconstructions, and simulations.

Implementation status as of 2026-08-14:

| Concept | Current representation |
| --- | --- |
| User | Not implemented; local single-user assumption. |
| Session | SQLite row plus API summary. |
| Recording | SQLite metadata plus referenced media artifact. |
| PoseSequence/PoseFrame | SQLite sequence metadata plus referenced versioned JSON artifact. |
| Analysis | SQLite version/provenance row plus referenced derived JSON artifact. |
| JointSeries | Stored inside the knee-flexion artifact, not relational rows. |
| Repetition | Stored inside the repetition artifact; compact means copied to session metrics. |
| SessionMetric | SQLite rows sourced from a named analysis version. |
| CalibrationProfile | Not implemented. |
| CaptureQualityReport | Versioned JSON artifact plus session status and compact numeric signals. |
| ProcessingOperation | SQLite operation status, stage, timing, input size, output identity, and sanitized failure provenance. |
| ArtifactManifest | Per-bundle JSON containing SHA-256 and size for every published artifact. |

## Canonical identity and evidence graph

Migration 4 and the canonical evidence API now explicitly model:

* `Subject` — a de-identified research code only;
* `Knee` — left/right laterality belonging to one person;
* `Episode` — injury, procedure, study, or longitudinal context;
* `Timepoint` — when evidence or a modeled state applies;
* `Observation` — immutable source evidence with modality, acquisition, provenance, authorization, and quality;
* `Annotation` — versioned machine or expert interpretation of an observation;
* `Reconstruction` — versioned geometry derived from named observations/annotations;
* `Registration` — an explicit transform between coordinate systems with method, error, and coverage;
* `SimulationModel` — an immutable, solver-ready model package linked to a reconstruction, with volumetric topology, named sets, structure coverage, quality, hashes, adapter, and validation state;
* `VirtualExperiment` — versioned anatomy, properties, loads, boundary conditions, solver configuration, and validation tier;
* `SimulationResult` — immutable outputs linked to the complete experiment definition.

These form a derivation graph rather than one mutable “twin” record. A new segmentation, transform, material assumption, or solver version creates a new derived object and never overwrites its source.

Every object must state whether its values are directly observed, expert-authored, reconstructed, estimated, or simulated. Unknown individual properties remain unknown or assumption ranges; they are never silently populated from a generic template.

## Milestone 9 implementation

The additive canonical tables are `subjects`, `knees`, `episodes`, `timepoints`, `observations`, `observation_knees`, `annotations`, `reconstructions`, `registrations`, `derivations`, `virtual_experiments`, and `simulation_results`.

Legacy squat migration preserves all original tables, IDs, endpoints, and artifacts. It creates one timepoint per session using the session UUID and one immutable video observation per recording using the recording UUID. Both default knees are explicit targets. New squat sessions create the same relationships transactionally. Confirmed session deletion cascades through its migrated timepoint and observation but does not delete the shared default subject or knees.

Observation creation requires a source reference, explicit SHA-256 state, acquisition manifest, authorization, quality, and at least one knee target. Subject ownership constraints prevent a timepoint from targeting another subject's knee. Annotation supersession must remain within one observation. Reconstruction and experiment knee/timepoint subjects must match. Registration stores coordinate descriptions, its 4×4 transform, method, coverage, error, and uncertainty without interpreting those fields as validated alignment.

Milestone 10 import observations use their observation UUID as the immutable artifact-bundle UUID. `source_artifact_reference` identifies the primary exact source (or the multi-view acquisition manifest), `source_sha256` records its durable hash, and the complete per-file hashes remain in `artifact_manifest_v1.json`. `acquisition_manifest` is one of the versioned MRI, arthroscopy, or calibrated multi-view contracts; `quality` repeats its status/signals for modality-neutral querying.

Milestone 11 reconstruction imports likewise share a reconstruction/artifact-bundle UUID. The canonical row preserves knee, timepoint, version, `expert-reviewed` geometry class, complete structure list, coordinate system, review state, and typed references to distinct label maps, computational volume, scientific meshes, web meshes, and quality report. Package review/correction/landmark and threshold metadata remain in the immutable source package and derivation configuration.

## Milestone 14 simulation models

Migration 6 adds `simulation_models` without changing reconstruction or experiment records. A row stores its reconstruction ID, version, adapter ID, canonical model SHA-256, full validated package manifest, artifact references, mesh-quality report, included/excluded structures, validation state, and creation time. The immutable model artifact bundle retains the contributor ZIP, canonical JSON, mesh quality, and integrity manifest. The separate durable import-job bundle retains the typed import result.

`FiniteElementModelPackageV1` contains right-handed millimetre coordinates, nodes, four-node tetrahedral elements, named contact surfaces, named node sets, ligament attachment pairs, provenance, and licensing. It requires positive element orientation and explicit compatibility with the source reconstruction. A PLY surface or reviewed anatomical mesh is not itself a `SimulationModel`.

`ExperimentDefinitionV2` points to a simulation-model ID and hash. Its exact JSON is preserved in `virtual_experiments`; the durable job additionally checks that the queued copy equals the canonical copy. Successful or partial adapter output publishes as a new immutable `SimulationResult` and a typed derivation. Failed attempts remain in the durable job ledger with sanitized failure provenance and any deliberately published partial pose evidence.

## User

The person whose movement history is being tracked.

## Session

* `id`
* `user_id`
* `exercise_type`
* `recorded_at`
* `created_at`
* `status`

## Recording

* `id`
* `session_id`
* `storage_reference`
* `duration`
* `fps`
* `width`
* `height`
* capture metadata

## PoseSequence

* `id`
* `session_id`
* `pose_model`
* `pose_model_version`
* `coordinate_convention`
* `created_at`

## PoseFrame

* `frame_index`
* `timestamp`
* `landmarks`
* `confidence`

## Analysis

* `id`
* `session_id`
* `analysis_version`
* `created_at`
* `quality_score`

Every analysis must carry enough version information to determine which algorithm produced it and to support reproducible reanalysis.

## JointSeries

* `analysis_id`
* `joint`
* `side`
* `metric`
* `unit`
* `time_series`

## Repetition

* `analysis_id`
* `rep_number`
* `start_time`
* `bottom_time`
* `end_time`
* `metrics`

## SessionMetric

* `analysis_id`
* `name`
* `value`
* `unit`
* `confidence`

## CalibrationProfile

* `user_id`
* `version`
* `height`
* optional anthropometrics
* capture/calibration metadata

## Persistence approach

Structured application entities and searchable metrics belong in a relational database. Videos and large pose or analysis artifacts belong behind a file/object-storage abstraction, with only their references and metadata stored relationally. Local development should use simple local persistence when these capabilities are introduced.

## Milestone 1 representation

Milestone 1 implements `Recording` and `PoseSequence` as versioned Pydantic contracts rather than SQL tables. Each frame preserves:

* zero-based frame index;
* derived millisecond timestamp based on decoded frame order and source FPS;
* an explicit empty pose list when no person is detected;
* all MediaPipe normalized-image landmarks;
* all MediaPipe world landmarks returned by the model;
* raw landmark visibility and presence values where available.

The raw JSON artifact is separate from the original recording and annotated overlay. Every artifact records the schema version, pose-model name, pose-model/package version, and coordinate convention.

## Milestone 2 representation

`KneeFlexionAnalysis` is a versioned derived artifact linked to its source `PoseSequence`. It contains exactly named `JointSeries` for left and right knee flexion. Each sample records:

* source timestamp in milliseconds;
* raw modeled flexion in degrees when calculable;
* filtered value when the filter has sufficient valid support;
* conservative contributing-landmark confidence;
* explicit quality state.

Quality states distinguish valid, low-confidence, missing pose, missing landmark, invalid coordinate, and degenerate geometry. Unavailable measurements remain JSON `null`; they are not replaced with zero or carried forward.

## Milestone 3 representation

`SquatRepetitionAnalysis` is a separate versioned artifact linked to a source `PoseSequence` and `knee-flexion-analysis-v1`. Each accepted `Repetition` records:

* one-based repetition index;
* start, bottom, and end timestamps in milliseconds;
* duration in milliseconds;
* maximum modeled left and right flexion in degrees;
* left, right, and mean within-repetition ROM in degrees;
* minimum bilateral input confidence across contributing valid samples.

The artifact embeds the full phase-model configuration and algorithm version so acceptance behavior is reproducible. An empty repetition list is a valid result and is distinct from analysis failure.

## Milestone 4 representation

The conceptual session graph now has a local SQLite representation:

* `sessions` stores exercise, upload-time `recorded_at`, creation time, and monotonic processing status;
* `recordings` stores identity, schema version, media metadata, and an artifact reference;
* `pose_sequences` stores identity, schema/model versions, frame counts, and raw/overlay references;
* `analyses` stores every distinct analysis type/version and its artifact reference;
* `session_metrics` stores compact named values, units, and their source analysis version.

Detailed time series, raw landmarks, and media do not enter SQLite. A repeated run of the same analysis version updates that version's artifact reference and replaces its metric set. A new analysis version creates a new analysis row. Session comparisons use metrics from the newest repetition-analysis version and define change as current mean modeled ROM minus the preceding stored squat session's mean modeled ROM.

## Milestone 6 additions

### CaptureQualityReport

A versioned derived artifact records:

* source pose-sequence and model versions;
* overall status such as `pass`, `warning`, or `fail`;
* named signals with value, unit, threshold, status, and explanation;
* actionable capture guidance;
* unavailable checks and the reason they could not be calculated.

Only compact status/summary fields are duplicated into relational metadata.

### Exact left/right difference metrics

Per-repetition difference fields live in `squat-repetition-analysis-v2`, which produced their operands. Session-level means are copied into `session_metrics` with exact names, degrees, and source analysis version. No generic unlabeled asymmetry score is stored.

### Capture metadata

Recording schema `1.1.0` distinguishes:

* source capture time from upload/creation time;
* declared exercise;
* camera view and orientation;
* optional user capture notes;
* future calibration profile reference when calibration exists.

### Schema evolution

SQLite uses ordered, checksummed migrations with an upgrade regression from the legacy schema. Existing recording rows receive explicit `unknown`/`bilateral` defaults without modifying their raw artifacts.

## Milestone 8 additions

`processing_operations` records synchronous extraction runs independently from completed sessions. Failed or interrupted work therefore remains inspectable even when no session or artifact bundle is published. Operation records store no raw media or exception traceback.

Every artifact bundle contains `artifact_manifest_v1.json`. It inventories source and derived filenames, byte sizes, and SHA-256 digests; the manifest itself is excluded to avoid recursive hashing. Session export compares expected hashes with current files and reports verified, missing, checksum-mismatch, or untracked states.
