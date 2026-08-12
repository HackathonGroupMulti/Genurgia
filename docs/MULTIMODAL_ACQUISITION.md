# Multimodal Acquisition Protocols

Knee Twin accepts only authorized, de-identified research evidence on an encrypted offline workstation. An accepted import means the source passed the listed technical checks; it does not establish anatomical accuracy, clinical validity, or fitness for diagnosis.

## Immutable import rule

Every import creates one canonical `Observation` and one atomic artifact bundle. The exact source bytes, a typed `acquisition_manifest.json`, and a generated `artifact_manifest_v1.json` remain separate from annotations and derived artifacts. SHA-256 verifies storage integrity. No import rewrites an earlier observation.

## MRI DICOM series v1

Input is one ZIP containing one pre-de-identified MR series. V1:

* requires `Modality=MR`, unique SOP Instance UIDs, and one consistent Study, Series, and Frame of Reference UID;
* requires consistent Rows, Columns, Pixel Spacing, Image Orientation (Patient), and ordered Image Position (Patient);
* checks orthonormal row/column direction cosines and slice-spacing consistency;
* checks `ImageLaterality`/`Laterality`, when present, against exactly one selected knee;
* records row/column pixel spacing and derived adjacent-slice spacing in millimetres;
* rejects populated values in the explicitly reported direct-identifier subset;
* preserves the ZIP exactly and records that no computational volume was generated.

The coordinate convention is `dicom-patient-lps-mm`. Image Position (Patient), Image Orientation (Patient), and Pixel Spacing follow the DICOM Image Plane Module. Pixel Spacing is recorded in row-then-column order. See the [official DICOM Image Plane Module](https://dicom.nema.org/medical/dicom/current/output/chtml/part03/sect_c.7.6.2.html).

The de-identification check is `knee-twin-research-screen-v1`. It is deliberately not a DICOM PS3.15 Basic Application Confidentiality Profile conformance claim: private tags, burned-in pixels, structured content, filenames, and indirect identifiers require an approved upstream de-identification workflow and human governance review. A passing report only means none of the checked direct-identifier tags were populated.

## Arthroscopy video v1

Input is one authorized video plus procedure time, scope/camera manufacturer and model, scope angle, calibration method/reference/error, and optional expert visible-region intervals. V1 decodes container metadata, verifies that annotated intervals stay inside the decoded duration, and records timestamps as derived from frame index and container FPS. This timing basis is not hardware synchronization.

The coordinate convention is `arthroscope-image-pixels`. Calibration evidence is preserved but not independently certified by the importer. Arthroscopy registration, surface refinement, and research tissue scoring remain separate, versioned Milestone 12 derivations.

## Calibrated four-camera RGB v1

The `calibrated-four-camera-rgb-v1` protocol requires:

* exactly four unique front, rear, left-side, and right-side cameras;
* decoded resolution of at least 1920×1080 and frame rate of at least 60 fps;
* a 3×3 intrinsic matrix, distortion coefficients, and image calibration error for each camera;
* a 4×4 capture-from-camera transform and spatial calibration error for each camera;
* a visible synchronization event with measured maximum offset;
* capture-volume validation with RMS error and timestamp;
* `standard-anatomical-pose-v1`, visible in all cameras, with a declared landmark set.

The coordinate convention is `capture-volume-right-handed-mm`. Import validates that decoded video dimensions/rates match the manifest, but does not yet triangulate landmarks or validate anatomical registration. Those are Milestone 12 gates.

## Execution boundary and open evidence gate

Imports currently run synchronously on the single-user workstation and return `execution=synchronous-local-import` plus `job_runner_status=deferred-to-milestone-13`. The durable local worker, progress, cancellation, retry, and job recovery arrive in Milestone 13 before production-scale reconstruction or simulation work.

Generated synthetic fixtures validate parsing, coordinates, consistency, corruption handling, identifier refusal, timing, calibration contracts, artifact hashing, and subject/knee ownership. No approved paired human MRI/arthroscopy/multi-view dataset is present. Milestone 10's scientific evidence gate therefore remains open even though its software slice is complete.
