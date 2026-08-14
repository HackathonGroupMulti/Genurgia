# Knee Twin Context

Knee Twin is intended to create a longitudinal, patient-specific digital representation of a complete knee. It should combine external movement evidence, internal/anatomical observations, versioned 3D reconstruction, and validated virtual experiments over time.

Squat video analysis is the first implemented evidence-to-measurement slice, not the product boundary.

Current implemented pipeline:

video
→ pose extraction
→ raw landmarks
→ normalization/filtering
→ kinematics
→ repetition analysis
→ session metrics
→ historical comparison
→ visualization

Frontend:
Next.js + TypeScript

Backend:
Python + FastAPI

Initial pose system:
MediaPipe Pose Landmarker

Advanced biomechanics:
Complete-knee review packages, synthetic multimodal registration, immutable finite-element model imports, and the first replaceable FEBio adapter are implemented engineering stages. Approved human evidence, real-solver integration evidence, uncertainty studies, and independent validation remain required before stronger claims.

Initial external-analysis MVP:

Upload a squat video and obtain:

* annotated replay;
* left/right knee-flexion curves;
* ROM;
* detected repetitions;
* basic asymmetry metrics;
* measurement confidence;
* stored session results;
* comparison against historical sessions.

Critical architectural principle:

Raw observations must be stored separately from derived measurements.

The system should retain raw pose landmarks so improved analysis algorithms can be applied to previous sessions without rerunning pose detection when possible.

LONG-TERM PRODUCT DIRECTION:

evidence record → anatomical twin → functional twin → validated simulation twin.

CURRENT MILESTONE:

Milestone 14 — open exploratory FEBio simulation pipeline; real-solver evidence gate open.

PARALLEL EVIDENCE GAP:

Participant-diverse, redistributable squat fixtures are not yet available. Milestone 6's implementation is complete, but its population/capture-diversity evidence gate remains open.

NEXT ACTION:

Install or build a separately licensed FEBio 4.12 executable, run the CC0 seven-pose fixture through the implemented adapter, correct any solver-format incompatibility, and record equilibrium/convergence evidence. Do not close Milestone 14 from fake-adapter tests alone.

Keep this file short. Future agents should update only the bottom status fields when appropriate rather than turning this into a giant project history.
