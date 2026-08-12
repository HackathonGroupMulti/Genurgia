# Durable Jobs and Motion Replay

Migration 5 adds a local SQLite job ledger. `POST /jobs` queues work, `GET /jobs/{id}` exposes state, cancellation and retry are explicit, and one local worker claims the oldest queued job using an immediate transaction. Startup returns interrupted running work to the queue with a recovery log. This is a single-workstation worker, not a distributed queue.

`ExperimentDefinitionV1` is solver-neutral. It preserves anatomy and motion-registration identifiers, every immutable input SHA-256, coordinate systems/transforms, sourced values with units/ranges/individual-measurement state, loading/boundary conditions, software/container versions, requested outputs, sensitivity configuration, and validation tier. Missing individual inputs cannot be silently replaced with population constants.

`anatomical-motion-replay-v1` currently summarizes a supplied synthetic registered motion sequence. It records included/excluded frames, projected-landmark residual RMS in millimetres, maximum transform uncertainty in millimetres, anatomical constraint violations, and sensitivity configuration. The result embeds the SHA-256 of canonicalized experiment JSON and publishes only after its artifact manifest verifies.

The runner does not yet perform segmentation, registration, OpenSim, FEBio, contact, force, or tissue-strain calculation. A replay result describes supplied registered transforms and their evidence. Human anatomical animation remains blocked by the open anatomy/registration gates.
