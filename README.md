# Knee Twin

Knee Twin is intended to become a longitudinal, patient-specific digital representation of a complete knee. Its target scope combines external movement, internal/anatomical evidence, reviewed 3D reconstruction, and validated virtual experiments over time. It is currently a research and engineering system, not a diagnostic medical device.

This repository contains the first external-observation slice: a working local squat-analysis prototype that preserves timestamped MediaPipe observations, exports an annotated replay, calculates confidence-aware modeled knee flexion, repetitions, and exact bilateral differences, reports capture quality, stores session summaries, reopens historical evidence, and compares explicitly selected compatible sessions. Squats are a foundation and validation protocol, not the product boundary. Patient-specific anatomy, medical/internal imagery, multimodal registration, and simulation are planned stages and are not implemented today.

## Architecture

```text
Next.js UI → FastAPI → application services → analysis/domain modules
```

Python owns numerical and biomechanics logic. Raw pose observations are preserved independently from derived metrics so historical sessions can be reanalyzed. Videos and large artifacts use an atomic, SHA-256-manifested local storage boundary; SQLite stores structured session, analysis, migration, and processing-operation metadata. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/ROADMAP.md](docs/ROADMAP.md), and [docs/DECISIONS.md](docs/DECISIONS.md).

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

Open <http://localhost:3000>. The homepage displays backend connectivity and provides a video upload form. Successful analysis displays the annotated video, a seekable synchronized knee-flexion graph, current measurements, repetition metrics, a rotatable model-relative skeleton, session history, and links to preserved raw artifacts.

Keep both processes bound to loopback. Do not add `--host 0.0.0.0`. Research evidence must reside on an approved encrypted workstation volume; follow [docs/OFFLINE_SECURITY.md](docs/OFFLINE_SECURITY.md) before using local cases.

## Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `BIOMECHANICS_API_URL` | `http://127.0.0.1:8000` | Backend URL used by the Next.js server |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:3000` | Comma-separated origins accepted by FastAPI |
| `KNEE_TWIN_ARTIFACT_DIR` | `./data/local` | Local recording and artifact storage root |
| `KNEE_TWIN_DATABASE_PATH` | `./data/local/knee_twin.sqlite3` | Local SQLite session-metadata database |
| `POSE_LANDMARKER_MODEL_PATH` | `./data/models/pose_landmarker_full.task` | MediaPipe full float16 model path |
| `MAX_VIDEO_UPLOAD_BYTES` | `104857600` | Maximum accepted upload size |

## Validate

From the repository root:

```powershell
npm run test:web
npm run lint:web
npm run typecheck:web
npm run build:web
npm run test:browser
```

From `services/biomechanics`:

```powershell
..\..\.venv\Scripts\python -m pytest
..\..\.venv\Scripts\python -m ruff check . ..\..\scripts
```

GitHub Actions runs the same backend, frontend, production-build, and Chromium smoke validations on pushes to `main` and pull requests.

## Current status

Engineering Milestones 0–8 are technically complete, proving a quality-aware, version-preserving, integrity-checked local longitudinal pipeline. This is a technical prototype rather than a completed product. Pose extraction remains synchronous; SQLite and local artifacts assume one local user on an encrypted offline volume. Historical sessions can be replayed and compatibility-checked, but real-video validation is not participant-diverse. Reported values are monocular model estimates, not clinical measurements.

Milestone 6's participant-diversity evidence gate remains open. Milestone 9 now establishes the canonical knee evidence model before multimodal ingestion, patient-specific 3D anatomy, functional registration, and validated simulation. See [TASKS.md](TASKS.md), [docs/CURRENT_STATE.md](docs/CURRENT_STATE.md), [docs/OFFLINE_SECURITY.md](docs/OFFLINE_SECURITY.md), [docs/PROCESSING_EVIDENCE.md](docs/PROCESSING_EVIDENCE.md), and [docs/ROADMAP.md](docs/ROADMAP.md).
