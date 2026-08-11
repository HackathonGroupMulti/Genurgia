# Knee Twin Context

Knee Twin reconstructs and analyzes a user's lower-body movement from video to create a longitudinal digital twin.

Primary pipeline:

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
OpenSim or similar musculoskeletal simulation may be integrated later.

Primary MVP:

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

CURRENT MILESTONE:

Milestone 5 — synchronized movement visualization.

CURRENT BLOCKER:

None.

NEXT ACTION:

Synchronize annotated video time with the knee-flexion chart and current-frame measurements.

Keep this file short. Future agents should update only the bottom status fields when appropriate rather than turning this into a giant project history.
