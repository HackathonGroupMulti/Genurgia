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

Knee Twin is a personal movement-analysis and digital-twin system.

It analyzes recorded human movement and tracks changes over time.

It is NOT a diagnostic medical device.

Do not present estimated quantities as medically validated measurements.

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
