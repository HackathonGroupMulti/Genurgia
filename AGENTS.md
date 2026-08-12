# Knee Twin — Agent Instructions

Before modifying code:

1. Read `CONTEXT.md`.
2. Read `TASKS.md`.
3. Read `docs/CURRENT_STATE.md`.
4. Read `docs/PRODUCT.md`.
5. Read `docs/ARCHITECTURE.md` when touching system boundaries.
6. Read `docs/BIOMECHANICS.md` whenever changing a biomechanical or mathematical calculation.
7. Read `docs/DECISIONS.md` before reversing an existing architectural decision.

## Product rule

Knee Twin is a longitudinal, patient-specific digital-twin system for the complete knee.

It is intended to combine external movement, internal/anatomical evidence, 3D reconstruction, and validated virtual experiments over time. Squat movement analysis is the first implemented slice, not the product boundary.

It is NOT a diagnostic medical device.

Do not present estimated quantities as medically validated measurements.
Do not describe reconstructed or simulated quantities as exact unless the evidence and validation explicitly support that claim.
Distinguish directly observed, reconstructed, estimated, and simulated data.

## Engineering rules

* Prefer simple architecture.
* Do not introduce infrastructure without a concrete need.
* Keep biomechanics calculations independent from HTTP/API code.
* Preserve raw pose observations so derived metrics can be recalculated later.
* Every biomechanics calculation requires tests.
* Every derived metric must document units and coordinate conventions.
* Never silently invent missing measurements.
* Propagate confidence and quality information.
* Prefer pure functions for numerical analysis.
* Avoid magic constants.
* Preserve functioning code unless there is a concrete reason to replace it.
* Do not rewrite an entire module to make a small change.
* Keep domain logic out of UI components and HTTP route handlers.
* Version analysis algorithms when their meaning changes.

## Required workflow

Before substantial implementation:

* inspect relevant code;
* state the implementation plan;
* identify affected interfaces;
* check existing architectural decisions.

After implementation:

* run relevant tests;
* update `TASKS.md`;
* rewrite `docs/CURRENT_STATE.md`;
* update `docs/DECISIONS.md` if a meaningful architectural decision changed;
* update `docs/BIOMECHANICS.md` if mathematical behavior changed.
