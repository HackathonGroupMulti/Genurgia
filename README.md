# Knee Twin

Knee Twin is a personal biomechanics and recovery-tracking application that builds a longitudinal representation of lower-body movement from recorded video. The MVP begins with squat kinematics and is explicitly a movement-analysis tool, not a medical diagnostic device.

Milestones 0 and 1 are complete. The application accepts a video, extracts timestamped MediaPipe pose landmarks, preserves the original and raw observation artifact, and exports an annotated MP4 for visual verification. Knee-angle calculations are intentionally deferred to Milestone 2.

## Architecture

```text
Next.js UI → FastAPI → application services → analysis/domain modules
```

Python owns numerical and biomechanics logic. Raw pose observations are preserved independently from derived metrics so historical sessions can be reanalyzed. Videos and large artifacts use a replaceable local storage boundary, separate from future relational metadata. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/DECISIONS.md](docs/DECISIONS.md).

## Repository layout

```text
apps/web/                    Next.js App Router frontend
services/biomechanics/app/   FastAPI application and API schemas
services/biomechanics/analysis/
                             Framework-independent analysis modules
services/biomechanics/tests/ Backend tests
packages/contracts/          Cross-boundary contracts
data/fixtures/                Deterministic test media
data/local/                   Ignored local recordings and artifacts
data/models/                  Ignored downloaded MediaPipe model
docs/                        Product, architecture, data, and state docs
scripts/                     Model download and contract export tools
```

## Prerequisites

* Node.js 20.9 or newer (Node.js 22 is used in CI)
* npm 10 or newer
* Python 3.11 or newer (Python 3.13 is used in CI)

The setup below uses PowerShell from the repository root.

## Install

Install the frontend workspace:

```powershell
npm ci
```

Create an isolated Python environment and install the backend with development tools:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -e ".\services\biomechanics[dev]"
.\.venv\Scripts\python scripts\download_pose_model.py
```

Optionally copy the local environment template. The defaults work without these files:

```powershell
Copy-Item .env.example .env
Copy-Item .env.example apps\web\.env.local
```

On macOS or Linux, use `.venv/bin/python` in place of `.venv\Scripts\python` and `cp` in place of `Copy-Item`.

## Run locally

Start the backend in one terminal:

```powershell
Set-Location services\biomechanics
..\..\.venv\Scripts\python -m uvicorn app.main:app --reload --env-file ..\..\.env
```

If you did not create `.env`, omit `--env-file ..\..\.env`. The API is available at <http://127.0.0.1:8000>; its OpenAPI UI is at <http://127.0.0.1:8000/docs>.

Start the frontend from the repository root in another terminal:

```powershell
npm run dev:web
```

Open <http://localhost:3000>. The homepage displays backend connectivity and provides a video upload form. Successful extraction displays the annotated video and a link to the preserved raw landmark JSON.

## Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `BIOMECHANICS_API_URL` | `http://127.0.0.1:8000` | Backend URL used by the Next.js server |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:3000` | Comma-separated origins accepted by FastAPI |
| `KNEE_TWIN_ARTIFACT_DIR` | `./data/local` | Local recording and artifact storage root |
| `POSE_LANDMARKER_MODEL_PATH` | `./data/models/pose_landmarker_full.task` | MediaPipe full float16 model path |
| `MAX_VIDEO_UPLOAD_BYTES` | `104857600` | Maximum accepted upload size |

## Validate

From the repository root:

```powershell
npm run test:web
npm run lint:web
npm run typecheck:web
npm run build:web
```

From `services/biomechanics`:

```powershell
..\..\.venv\Scripts\python -m pytest
..\..\.venv\Scripts\python -m ruff check . ..\..\scripts
```

GitHub Actions runs the same test, lint, type-check, and frontend build validations on pushes to `main` and pull requests.

## Current status

Milestone 1 is complete. Pose extraction runs synchronously for the first local vertical slice and stores artifacts under `data/local`; no database, knee-angle calculations, repetition logic, or OpenSim integration has been introduced.

The next task is Milestone 2: implement tested vector-angle primitives and the documented `0° = modeled extension` knee-flexion convention before exposing a left/right time series.
