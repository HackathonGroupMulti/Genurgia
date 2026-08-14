# Durable Jobs and Exploratory Experiments

Migration 5 adds a local SQLite job ledger. `POST /jobs` queues work, `GET /jobs/{id}` exposes state, cancellation and retry are explicit, and one local worker claims the oldest queued job using an immediate transaction. Startup returns interrupted running work to the queue with a recovery log. This is a single-workstation worker, not a distributed queue.

## Canonical experiment definitions

`ExperimentDefinitionV1` remains solver-neutral. It preserves anatomy and motion-registration identifiers, every immutable input SHA-256, coordinate systems/transforms, sourced values with units/ranges/individual-measurement state, loading/boundary conditions, software/container versions, requested outputs, sensitivity configuration, and validation tier. Missing individual inputs cannot be silently replaced with population constants.

`ExperimentDefinitionV2` is an additive, typed contract for `febio-tibiofemoral-flexion-sweep`. It points to one immutable `SimulationModel` and requires manually authored values for every material, ligament connector, contact, load, boundary, and convergence setting. Each value carries its unit, source, range, rationale, evidence class, and individual-measurement flag. The API validates V2 before storing the canonical experiment and refuses a knee/timepoint mismatch with its source reconstruction.

## Adapter registry

The durable runner dispatches through a registry rather than a hard-coded replay branch. `anatomical-motion-replay-v1` remains available. `febio-flexion-sweep-v1` declares its capability through `GET /simulation-adapters`, requires a separately installed FEBio 4.12 executable, and records the executable path, detected version, and SHA-256. Unsupported or missing executables remain unavailable rather than silently substituting another solver.

The FEBio adapter validates the model and experiment, writes deterministic `.feb` inputs, launches FEBio with an argument vector and no shell, checks cancellation, and solves `0, 15, 30, 45, 60, 75, and 90°` independently. Its atomic result bundle includes the definition, generated inputs, configuration, stdout/stderr, solver logs, FEBio VTK field files, per-pose normalized field manifests, normalized result JSON, and a verified SHA-256 manifest. Every pose remains `converged`, `nonconverged`, `failed`, or `cancelled`, so one bad pose does not erase other evidence.

Normalized outputs retain exploratory mechanical names: contact pressure, contact area, displacement, cartilage/meniscus strain, ligament strain, reaction force, and convergence residual. They are not injury risk, diagnosis, or predicted outcome. Numerical convergence is not validation.

## Implemented experiments

`anatomical-motion-replay-v1` summarizes a supplied synthetic registered motion sequence. It records included/excluded frames, projected-landmark residual RMS in millimetres, maximum transform uncertainty in millimetres, anatomical constraint violations, and sensitivity configuration. The result embeds the SHA-256 of canonicalized experiment JSON and publishes only after its artifact manifest verifies.

`febio-flexion-sweep-v1` provides the first executable mechanical adapter boundary. The repository ships a compact CC0 package generator for a deliberately non-anatomical integration fixture. Fixture assumptions may be preloaded only for that fixture version. Contributor or patient models receive no automatic population defaults.

The software path is covered by deterministic and fake-executable tests, including malformed output, failure, cancellation, corruption, and partial convergence. A real FEBio 4.12 executable is not present on the current workstation, so the required real-solver fixture evidence remains open. Human anatomical replay, biomechanics accuracy, and clinical claims also remain outside the completed engineering evidence.

Adapter implementation is checked against the [FEBio 4.12 release](https://github.com/febiosoftware/FEBio/releases/tag/v4.12), the official [FEBio feature manual](https://febiosoftware.github.io/febio-feature-manual/), and version-4 examples from the [official FEBio TestSuite](https://github.com/febiosoftware/TestSuite). The source repository is MIT-licensed; Knee Twin does not redistribute separately obtained binaries.
