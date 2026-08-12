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
Patient-specific anatomy, multimodal registration, and replaceable musculoskeletal or finite-element simulation adapters are planned product stages. They require trustworthy inputs, uncertainty reporting, and validation before stronger claims.

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

Milestone 10 — multimodal acquisition and ingestion.

PARALLEL EVIDENCE GAP:

Participant-diverse, redistributable squat fixtures are not yet available. Milestone 6's implementation is complete, but its population/capture-diversity evidence gate remains open.

NEXT ACTION:

Implement de-identified MRI/DICOM and arthroscopy import manifests plus the calibrated four-camera protocol, beginning with synthetic or appropriately licensed fixtures.

Keep this file short. Future agents should update only the bottom status fields when appropriate rather than turning this into a giant project history.
