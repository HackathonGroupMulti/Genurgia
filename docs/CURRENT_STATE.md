# Current State

Last updated: 2026-08-14

## Product position

Knee Twin is an offline, open-source research pipeline for turning longitudinal knee evidence into inspectable 3D hypotheses. It preserves immutable observations, reconstructions, registrations, assumptions, solver inputs, outputs, failures, and later alternatives. Its usefulness does not depend on the first physics model being accurate; it depends on making every attempt reproducible and replaceable so evidence and contributors can strengthen it.

Knee Twin is not a diagnostic medical device. Observed, reconstructed, expert-assumed, estimated, and simulated information is labeled separately. Numerical convergence is not scientific or clinical validation.

## Implemented platform

Engineering Milestones 0–13 are technically complete. Existing squat workflows remain operational with bounded/atomic uploads, raw MediaPipe observations, bilateral flexion and repetition derivations, capture quality, exact left-minus-right differences, historical replay, explicit compatible comparisons, reanalysis, artifact integrity, deletion/recovery behavior, and offline-workstation guidance.

The additive canonical graph models de-identified subjects, left/right knees, episodes, timepoints, immutable observations, annotations, reconstructions, registrations, derivations, virtual experiments, and simulation results. Legacy session IDs, endpoints, and artifacts are preserved. Controlled MRI DICOM, arthroscopy, and calibrated four-camera imports preserve native coordinate meaning. Manual complete-knee reconstruction packages, synthetic calibrated registration, registered evidence contracts, durable single-worker SQLite jobs, and solver-neutral motion replay are implemented; their human scientific gates remain open.

## Milestone 14 engineering implementation

Migration 6 and the canonical API add immutable `SimulationModel` records linked to reconstructions. `FiniteElementModelPackageV1` imports contributor-prepared volumetric nodes/tetrahedra, named anatomical parts, contact surfaces, attachment/boundary sets, right-handed millimetre coordinates, laterality, structure coverage, provenance, licensing, and mesh quality. The HTTP boundary streams each bounded ZIP into a verified intake bundle and returns a durable `febio-model-import-v1` job. The worker validates hashes, topology, positive tetrahedral volume, complete required flexion structures, and source-reconstruction compatibility before atomically publishing the model and derivation. Existing PLY surfaces are not treated as finite-element meshes.

`ExperimentDefinitionV2` adds one named question: under a manually specified compressive load, how do simulated tibiofemoral contact and strain fields change from 0° to 90° of prescribed flexion? Materials, ligament connectors, contacts, load, boundary controls, convergence controls, units, sources, ranges, rationales, individual-measurement state, software versions, outputs, and validation tier are all explicit. Missing values, unknown units, non-finite values, unsafe topology, incompatible knee/timepoint/laterality/coordinates, or a model-hash mismatch refuse execution.

The SQLite job runner now dispatches through an adapter registry. `febio-flexion-sweep-v1` preflights an external FEBio 4.12 executable, records its exact version and hash, deterministically generates `.feb` inputs, invokes it without a shell, checks cancellation, independently preserves each fixed pose as converged/nonconverged/failed/cancelled, normalizes named mechanical fields, and atomically publishes verified inputs, configuration, stdout/stderr, logs, FEBio VTK fields, normalized field manifests, result JSON, and a SHA-256 manifest. Canonical `SimulationResult` and derivation records are created only after bundle verification.

The `/lab` workspace exposes solver availability and model completeness, FE package import, knee/timepoint/reconstruction/model selection, full JSON assumption editing/import/export, canonical experiment creation, run/cancel/retry state, immutable run history, pose scrubbing, partial/failure states, and VTK field viewing. Persistent labels distinguish `Observed`, `Reconstructed`, `Expert assumption`, and `Simulated`. Only the versioned CC0 synthetic fixture may preload its fixture-only assumptions.

Public local interfaces now include:

* `POST /simulation-models/imports/febio`, returning a durable import job;
* `GET /simulation-models` and `GET /simulation-models/{id}`;
* `GET /simulation-adapters`;
* `POST /jobs` with `febio-flexion-sweep-v1`, plus existing job state, cancellation, retry, and worker execution;
* existing `/experiments`, `/simulation-results`, `/derivations/{id}`, evidence, session, and artifact APIs.

Python models are exported as committed JSON Schemas with matching TypeScript contracts/parsers. The project is Apache-2.0 licensed; the generated synthetic fixture is dedicated under CC0-1.0. Contribution rules establish adapter, benchmark, citation, contract, and claim boundaries.

## Evidence and verification state

Automated coverage includes migration from Milestone 13, pure tetrahedral-volume calculation, mesh/set/laterality/coordinate/model completeness, deterministic XML and hashes, contract parity, API import/preflight, explicit-value refusal, unknown units, safe subprocess arguments, fake-executable convergence/output/failure/cancellation/partial behavior, durable canonical results, frontend contract/component behavior, and production build/browser workflows.

Verification recorded on 2026-08-14:

* Ruff passed over the biomechanics service and contract-export script.
* Pytest passed all 139 backend tests.
* ESLint and TypeScript type checking passed with zero warnings or errors.
* Vitest passed 37 frontend contract/component tests.
* The optimized Next.js production build completed successfully, including `/lab`.
* Playwright passed both offline-workstation browser workflows.
* Markdownlint passed all 21 project Markdown files in scope.
* `git diff --check` passed before the local milestone commit.

The compact CC0 model is mechanically minimal, overlapping, and non-anatomical. It is an integration fixture, not human evidence, and its values cannot flow into other experiments automatically.

FEBio 4.12 is not installed on the current workstation. Docker's engine is unavailable, the local WSL distribution cannot start, and the available native toolchain lacks the supported Visual Studio compiler path. Therefore the required real-FEBio run—finite outputs, configured convergence, load/reaction balance, reproducible manifests, and verified artifacts—has not been recorded. Milestone 14's engineering path is implemented, but its completion gate remains open. Human mechanical accuracy and validation are also deliberately unclaimed.

## Current priority

Install or build FEBio 4.12 separately, point `FEBIO_EXECUTABLE` to it, run the generated CC0 fixture through the complete local workflow, and record the exact executable hash and validation evidence. After that, formalize the fixture as a public benchmark, add sensitivity batches as explicit child experiments, and add alternative adapters behind the same canonical boundary while paired human-data validation progresses independently.
