# Architectural Decisions

## ADR-001 — Preserve raw pose observations

Status:
Accepted

Decision:

Store raw pose-landmark output separately from derived biomechanical metrics.

Reason:

Analysis algorithms will improve.

Historical sessions should be capable of being reanalyzed without losing the original pose observations.

Rejected alternative:

Store only final metrics.

Why rejected:

It destroys useful information and tightly couples recorded sessions to the original analysis algorithm.

---

## ADR-002 — Python owns biomechanics calculations

Status:
Accepted

Decision:

Biomechanical and numerical-analysis code lives in the Python backend and does not live in Next.js.

Reason:

Python has the stronger scientific/numerical ecosystem and keeps numerical domain logic centralized.

---

## ADR-003 — Start as a modular monolith

Status:
Accepted

Decision:

Use one Next.js frontend and one FastAPI backend.

Do not create distributed microservices for the MVP.

Reason:

The current domain does not justify distributed-system complexity.

---

## ADR-004 — OpenSim is a future adapter

Status:
Accepted

Decision:

Do not make OpenSim a dependency of the MVP architecture.

Design normalized motion outputs so a future musculoskeletal-simulation adapter can consume them.

Reason:

The initial problem is movement reconstruction and longitudinal kinematics.
