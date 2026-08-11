# Biomechanics

This document defines conventions before numerical implementation. Milestone 0 intentionally contains no biomechanical calculations.

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

## Confidence

A derived knee-flexion value requires valid hip, knee, and ankle landmarks.

Initial confidence may be derived conservatively from the contributing landmark confidences. Missing required landmarks must produce an unavailable result rather than an invented measurement.

This confidence describes input/model quality and does not represent clinical accuracy.

## Filtering

Raw landmark measurements may be noisy.

Filtering must:

* preserve timestamps;
* document the chosen filter;
* avoid excessive smoothing;
* be tested on synthetic signals;
* remain distinct from raw observations.

## Asymmetry

Do not create a generic clinically meaningful “asymmetry score” without defining it.

Every asymmetry metric must state exactly what is being compared. Examples include:

* difference in maximum knee flexion;
* difference in ROM;
* temporal difference between repetition phases.

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
