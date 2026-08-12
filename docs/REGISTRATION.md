# Multimodal Registration v1

Milestone 12 provides tested numerical primitives and evidence contracts. It does not claim that a human knee, arthroscopy sequence, or movement capture has been registered accurately.

## Calibrated motion

`calibrated-dlt-kabsch-v1` uses at least two finite 3×4 projection matrices for each visible landmark. Linear homogeneous triangulation produces points in `capture-volume-right-handed-mm`; degenerate camera geometry fails. At least three non-collinear calibration landmarks are required to estimate a proper rigid transform into `dicom-patient-lps-mm` using SVD/Kabsch. Reflection is rejected through the proper-rotation correction.

The result contract preserves calibration and per-frame 4×4 transforms, timestamp, triangulated count, residual RMS in millimetres, confidence, excluded intervals and reasons, total coverage, uncertainty, and validation tier. Missing views or landmarks are unavailable; generic scaling is never substituted.

`synthetic-perturbation` uncertainty repeats the rigid fit after deterministic Gaussian landmark perturbation and reports the 95th percentile translation magnitude in millimetres and rotation angle in degrees. Its configured input error is an assumption, not a measured confidence interval.

## Arthroscopy overlay

`expert-seed-pnp-v1` requires at least four expert-authored 3D anatomy-to-2D image correspondences plus calibrated intrinsics and distortion. Perspective-n-point optimization returns an anatomy-from-camera transform and per-seed/RMS reprojection errors in pixels. Visible coverage and uncertainty remain explicit evidence, not implied by a low seed residual.

Geometry refinement is a separate gate. A new arthroscopy-refined reconstruction is permitted only when calibration, parallax, positive coverage, and a configured residual check pass. The MRI reconstruction is never modified. V1 defines and tests this refusal contract but has no approved human refinement dataset.

Research tissue scoring preserves at least two independent expert labels, taxonomy version, optional adjudication, and inter-rater results. It is explicitly non-diagnostic. Automated scoring remains unsupported until a separately validated labeled dataset exists.

## Validation state

Known synthetic camera, rigid, and arthroscopy transforms test direction, units, residuals, degeneracy, and reproducible uncertainty. Paired human cases, independent laboratory/biplanar motion reference, expert arthroscopy coverage, refinement accuracy, and tissue taxonomy acceptance remain open gates.
