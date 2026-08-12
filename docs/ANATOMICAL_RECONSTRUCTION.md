# Anatomical Reconstruction v1

Milestone 11 implements a review and evidence package, not an automatic segmenter. It accepts manually segmented synthetic/reference packages and keeps them below patient-specific validation until independent experts approve the taxonomy, landmark protocol, per-structure thresholds, and representative human evidence.

## Complete structure target

The v1 package requires exactly these 22 structures:

* femur, tibia, fibula, and patella;
* femoral, medial tibial, lateral tibial, and patellar cartilage;
* medial and lateral menisci;
* ACL, PCL, MCL, and LCL;
* quadriceps and patellar tendons;
* quadriceps, medial/lateral hamstrings, medial/lateral gastrocnemius, and popliteus musculotendon structures and attachment regions.

This taxonomy is a software target pending multidisciplinary approval. Additional knee-crossing structures require an approved version change; they cannot be silently added to v1.

## Package and evidence classes

`POST /reconstructions/imports/manual` accepts one bounded ZIP containing:

* `package_manifest.json`;
* `reviewed_label_map.npz` and `independent_reference_label_map.npz`;
* a distinct `computational_volume.npz`;
* one scientific PLY and one web GLB for every required structure;
* approved landmark positions, correction history, primary/independent reviewer identities, and a threshold profile in the manifest.

The original ZIP and each unpacked artifact publish atomically with SHA-256 integrity. The label maps and computational volume must share one 3D shape. Every declared nonzero label must appear in both label maps, and unknown labels are refused. The source must be an MRI observation for the same knee and timepoint.

Generic, fitted, machine-segmented, expert-reviewed, and validated patient-specific geometry are distinct evidence labels. The manual v1 importer emits `expert-reviewed`. A draft threshold profile forces `in_review` and `thresholds-unapproved`; identical synthetic maps do not bypass that gate.

## Quality calculations

For each structure, v1 reports:

```text
Dice = 2 × |candidate ∩ reference| / (|candidate| + |reference|)
```

It also extracts exposed voxel centers, scales them using the declared `(axis 0, axis 1, axis 2)` voxel spacing in millimetres, and reports average symmetric surface distance and the 95th percentile of bidirectional nearest-surface distances. Empty structures, mismatched shapes, missing units, or non-positive spacing fail rather than producing invented metrics.

An approved profile must provide `dice_min`, `asd_max_mm`, and `hd95_max_mm` for every structure and name its approving authority. Threshold values are not supplied by the software team as clinical facts. Until experts approve them, acceptance is `not-evaluated` and validation is `thresholds-unapproved`.

## Open scientific gates

The current tests use synthetic voxel phantoms and opaque fixture meshes. They verify packaging, provenance, coordinate units, complete coverage, metric mathematics, and failure behavior. They do not validate segmentation accuracy, mesh topology, anatomical landmarks, inter-rater performance on people, or clinical meaning. A machine-assisted adapter remains prohibited until suitable training/reference evidence exists.
