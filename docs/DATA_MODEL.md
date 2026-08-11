# Data Model

The following entities describe the intended domain. The first implementation does not need every conceptual entity represented as a separate SQL table. Persistence choices should follow practical access patterns while keeping raw observations distinct from derived results.

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
