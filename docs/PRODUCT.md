# Product

## Problem

Tracking knee recovery or movement quality manually makes longitudinal changes difficult to quantify.

Knee Twin provides a visual and quantitative record of movement over time.

## Core user flow

1. User selects an exercise.
2. User records or uploads a standardized movement video.
3. System checks capture quality.
4. System extracts pose information.
5. System computes supported kinematic measurements.
6. System identifies repetitions.
7. System displays synchronized visualizations.
8. System stores the session.
9. User compares the session against prior sessions.

## MVP exercise

Squat.

## Initial MVP outputs

* knee flexion through time;
* left/right values;
* range of motion;
* repetition segmentation;
* per-repetition metrics;
* simple asymmetry;
* pose confidence;
* session comparison.

## Future exercises

* single-leg squat;
* step-down;
* lunge;
* knee extension;
* walking/gait.

Exercise-specific functionality should eventually be configuration or strategy built on a generic motion-analysis engine rather than entirely duplicated pipelines.

## Explicit non-goals for early versions

* diagnosis;
* treatment recommendations presented as medical advice;
* exact tissue loading;
* exact ligament forces;
* exact cartilage pressure;
* replacing physical examination;
* pretending monocular pose estimation is equivalent to laboratory motion capture.

## Long-term vision

A personal movement digital twin that becomes increasingly calibrated to the individual and may later use:

* richer camera setups;
* personal anthropometrics;
* calibration sessions;
* musculoskeletal models;
* OpenSim;
* force estimates where scientifically justified.
