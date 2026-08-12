# Biomechanics

This document defines conventions for implemented and planned numerical behavior. The current calculations use external pose evidence only. Patient-specific anatomical reconstruction, tissue mechanics, and simulation require separate inputs, coordinate systems, validation, and versions.

## Evidence and model tiers

Knee Twin must label numerical results by how they were produced:

* **observed** — supplied directly by an instrument or source artifact, with its acquisition limits;
* **annotated** — identified by a model or expert on source evidence;
* **reconstructed** — geometry or state derived from observations and explicit transforms;
* **estimated** — a quantity inferred by a named mathematical/statistical model;
* **simulated** — an output of explicit governing equations, properties, loads, and boundary conditions.

Internal imagery is not automatically ground truth for the whole knee. Arthroscopic imagery, for example, may directly show only a limited visible surface and still requires calibration and registration to relate pixels to anatomical geometry. Material properties, internal forces, and failure behavior remain unknown unless measured or represented as explicit assumptions with sensitivity analysis.

Simulation precision must not be confused with accuracy. Each virtual experiment must identify its anatomy version, coordinate transforms, material/property sources, loads, boundary conditions, solver and settings, sensitivity/uncertainty results, and validation tier.

## Raw pose observations

MediaPipe image landmarks are stored under the `mediapipe-normalized-image-v1` convention:

* origin at the image top-left;
* positive x points right;
* positive y points down;
* x and y are normalized by image dimensions;
* z remains MediaPipe model-relative depth, with smaller values closer to the camera.

MediaPipe world landmarks are stored separately under `mediapipe-pose-world-v1`, in meters relative to MediaPipe's model-defined midpoint-of-hips origin. They are model estimates, not calibrated laboratory coordinates.

Raw landmark `visibility` and `presence` values are retained when the provider supplies them. A frame with no detected pose stores an empty pose list. Knee Twin does not interpolate, fabricate, or silently carry forward missing landmarks at this stage.

## General principles

Every metric must specify:

* required landmarks;
* coordinate space;
* mathematical formula;
* units;
* anatomical convention;
* confidence derivation;
* known limitations.

## Initial knee-flexion calculation

Inputs:

* hip coordinate;
* knee coordinate;
* ankle coordinate.

For the knee joint:

```text
femur_vector = hip - knee
tibia_vector = ankle - knee

included_angle = acos(
  dot(femur_vector, tibia_vector)
  / (norm(femur_vector) * norm(tibia_vector))
)
```

Knee Twin will prefer this reporting convention:

```text
flexion = 180 degrees - included_angle
```

Therefore, `0 degrees` means full modeled extension and increasing values mean greater modeled knee flexion. The implementation must handle degenerate vectors and numerical clamping explicitly and must test this convention before use.

Milestone 2 implements this formula in three-dimensional MediaPipe world coordinates only. Required landmarks are hip, knee, and ankle from the same side and frame. The first detected pose (`pose_index = 0`) is used. There is no silent fallback to normalized image coordinates.

The calculation:

* rejects missing or non-finite coordinates;
* rejects zero-length femur or tibia vectors;
* clamps the cosine to `[-1, 1]` before `acos` to handle floating-point drift;
* reports degrees;
* is versioned as `knee-flexion-world-3d-v1`.

These values are modeled kinematic estimates. MediaPipe world landmarks are inferred from monocular images and are not equivalent to calibrated motion-capture coordinates.

## Confidence

A derived knee-flexion value requires valid hip, knee, and ankle landmarks.

Initial confidence may be derived conservatively from the contributing landmark confidences. Missing required landmarks must produce an unavailable result rather than an invented measurement.

This confidence describes input/model quality and does not represent clinical accuracy.

Milestone 2 first takes the lower of each landmark's available visibility and presence values, then takes the minimum across hip, knee, and ankle. If any required landmark has no confidence signal, joint confidence is unavailable. A configurable initial threshold of `0.5` separates valid from low-confidence samples. Low-confidence angles may be retained for auditability, but they are excluded from filtering and graph display.

## Filtering

Raw landmark measurements may be noisy.

Filtering must:

* preserve timestamps;
* document the chosen filter;
* avoid excessive smoothing;
* be tested on synthetic signals;
* remain distinct from raw observations.

Milestone 2 uses `centered-moving-average-v1` for offline visualization:

* five-sample centered window;
* at least three valid values required;
* only samples labeled valid contribute;
* a missing or low-confidence center remains unavailable;
* timestamps and raw values are unchanged;
* no interpolation or forward filling occurs.

This is a deliberately simple initial filter. Any future filter that changes numerical meaning requires a new version and synthetic-signal tests.

## Asymmetry

Status: implemented as `bilateral-exact-differences-v1` in repetition-analysis v2.

Do not create a generic clinically meaningful “asymmetry score” without defining it.

Every asymmetry metric must state exactly what is being compared. Examples include:

* difference in maximum knee flexion;
* difference in ROM;
* temporal difference between repetition phases.

Implemented v1 squat metrics:

```text
signed_rom_difference_degrees = left_rom_degrees - right_rom_degrees
absolute_rom_difference_degrees = abs(signed_rom_difference_degrees)

signed_max_flexion_difference_degrees =
    left_max_flexion_degrees - right_max_flexion_degrees

absolute_max_flexion_difference_degrees =
    abs(signed_max_flexion_difference_degrees)
```

Positive signed values mean the modeled left operand is greater; negative values mean the modeled right operand is greater. Absolute values communicate magnitude only. These are exact differences in degrees, not percentages, normalized indices, diagnoses, or evidence of impairment. Session aggregates should state whether they are arithmetic means, maxima, or another named operation and must retain their source analysis version.

Do not introduce a percentage difference until its denominator, zero behavior, interpretation, and validation are explicitly agreed.

## Capture quality

Status: implemented as `capture-quality-v1`. It consumes preserved pose observations, filtered bilateral knee series, and accepted repetition count.

The capture-quality report uses named observable signals rather than a vague quality score:

* decoded duration, frame rate, dimensions, and frame count;
* fraction of frames with a detected pose;
* fraction of frames with valid bilateral knee-flexion inputs;
* maximum consecutive unavailable bilateral interval in milliseconds;
* whether required body landmarks remain inside configured image margins;
* whether a complete standing-to-bottom-to-standing cycle is observable.

V1 thresholds are:

* pose detection: pass at `>= 0.90`, warning at `>= 0.70`, otherwise fail;
* valid filtered bilateral knees: pass at `>= 0.85`, warning at `>= 0.60`, otherwise fail;
* maximum consecutive unavailable bilateral interval: pass at `<= 250 ms`, warning at `<= 500 ms`, otherwise fail;
* required hip/knee/ankle image landmarks inside a `5%` image margin: pass for `>= 0.95` of evaluable frames, warning at `>= 0.80`, otherwise fail;
* at least one complete configured squat cycle is required for a protocol pass.

Thresholds are versioned product heuristics, not validated clinical cutoffs. A capture-quality pass means the recording met the system's input criteria; it does not mean the resulting kinematics are clinically accurate.

## Initial squat repetition segmentation

Milestone 3 implements `bilateral-squat-state-machine-v1` over the filtered output of `knee-flexion-analysis-v1`. It requires aligned, valid, filtered measurements from both knees. The phase-driving value is the arithmetic mean of left and right flexion; one side is never substituted for missing data.

The state order is:

```text
standing → descending → bottom → ascending → standing
```

Initial configuration:

* standing: bilateral mean flexion at or below `25°`;
* descent started: bilateral mean at or above `35°` after a standing observation;
* bottom reached: bilateral mean at or above `70°`;
* bottom exited: bilateral mean at or below `60°`, providing `10°` hysteresis;
* duration: `800–10,000 ms` inclusive;
* maximum gap between valid bilateral samples inside a candidate: `500 ms`;
* minimum ROM independently required on each side: `35°`.

Rep start is the most recent standing timestamp before descent. Bottom is the timestamp of maximum bilateral mean flexion in the candidate. End is the first return to standing after bottom exit. A cycle is omitted if it is incomplete, too shallow, outside the duration limits, has insufficient ROM on either side, or crosses an excessive invalid-data gap. Missing samples are not interpolated.

For each accepted repetition:

```text
left_rom = maximum_left_flexion - minimum_left_flexion
right_rom = maximum_right_flexion - minimum_right_flexion
mean_rom = (left_rom + right_rom) / 2
```

Rep confidence is the minimum of the contributing bilateral knee-flexion confidences. This conservative value describes pose-input quality, not confidence in clinical accuracy. Fixed v1 thresholds are product heuristics validated against deterministic signals and a small real-video fixture; they are not individualized, diagnostic, or biomechanical ground truth.

## Known limitations

* monocular depth uncertainty;
* occlusion;
* camera perspective;
* clothing;
* lighting;
* landmark-estimation errors;
* capture-angle dependence;
* absence of direct force measurement.

These limitations prevent early Knee Twin outputs from being treated as diagnoses or exact estimates of tissue, ligament, muscle, or joint-contact forces.
