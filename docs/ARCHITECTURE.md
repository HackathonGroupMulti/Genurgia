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

Milestone 0 has no persistence layer and no analysis orchestration implementation. The health endpoint establishes connectivity without inventing domain abstractions before their requirements are known.

## Dependency Direction

Preferred:

UI → API → Application services → Analysis/domain modules

Analysis/domain modules must NOT depend on FastAPI or Next.js.

## Milestone 0 interface

`GET /health` returns a typed JSON response with `status` and `service`. The Next.js server reads the backend base URL from `BIOMECHANICS_API_URL`, calls this route, validates the response shape, and renders the connection state. This server-side call avoids exposing internal service URLs to browser code.
