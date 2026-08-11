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
