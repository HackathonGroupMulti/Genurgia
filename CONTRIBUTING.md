# Contributing to Knee Twin

Knee Twin is an Apache-2.0 research platform for reproducible knee evidence and exploratory simulation. Contributions that make a model easier to inspect, reproduce, falsify, compare, or replace are valuable even when they do not improve numerical accuracy.

## Scientific boundary

Always distinguish observed, reconstructed, expert-assumed, and simulated values. A converged solver run is not proof of anatomical, biomechanical, or clinical accuracy. Do not add diagnosis, treatment advice, injury-risk labels, or claims that virtual testing replaces required examination or physical measurement.

Every numerical contribution must state units, coordinates, algorithm/solver version, sources, limitations, missing-data behavior, and validation tier. Population or literature values must be explicit assumptions with ranges; they must never silently become patient measurements.

## Extension points

- Simulation adapters consume canonical experiment and simulation-model contracts. Solver-native records remain artifacts rather than canonical database types.
- Benchmark cases should be redistributable, versioned, immutable, and traceable to their license and source.
- New materials, contacts, boundary conditions, and result fields require Python tests, JSON Schema export, TypeScript parity, and visible evidence-class labeling.
- Failed and non-convergent cases are useful fixtures. Preserve their diagnostics instead of filtering them from a benchmark.

## Workflow

1. Read `AGENTS.md`, `CONTEXT.md`, `TASKS.md`, and the relevant documentation.
2. Keep domain calculations outside HTTP handlers and UI components.
3. Add pure numerical tests and corrupt/incomplete/incompatible cases.
4. Run backend Ruff and pytest plus frontend lint, typecheck, tests, and build.
5. Update `TASKS.md`, rewrite `docs/CURRENT_STATE.md`, and update the biomechanics or ADR documentation when meaning changes.

Generated fixtures under `data/samples/febio-flexion-demo` are CC0-1.0. FEBio is an external dependency and is not redistributed by Knee Twin; contributors must comply with the terms of the FEBio build or binary they use.
