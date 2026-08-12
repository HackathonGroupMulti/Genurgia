# Knee Twin Roadmap

Last reviewed: 2026-08-12

## Executive scope

Knee Twin is intended to become a complete longitudinal digital representation of an individual knee. The system should combine external motion, internal/anatomical evidence, 3D reconstruction, and validated virtual experiments. Squat analysis is the first implemented evidence-to-measurement slice, not the final application.

The present repository is a local technical prototype. It demonstrates raw-evidence preservation, versioned derivation, synchronized replay, and longitudinal metadata for one movement protocol. It does not yet contain patient-specific anatomy, internal imaging ingestion, anatomical registration, tissue models, or a simulation engine.

## Capability map

| Capability | Current status | Target role |
| --- | --- | --- |
| Squat video and pose extraction | Implemented | First external-observation protocol. |
| Knee flexion, repetitions, ROM | Implemented | Initial versioned kinematic measurements. |
| Capture-level quality and left/right differences | Implemented | Versioned observable signals and exact degree differences; diverse validation remains open. |
| Longitudinal session history | Partial | Foundation for timepoints and episodes. |
| Other movement and sensor protocols | Not implemented | Broader functional evidence. |
| Medical image and internal-imagery ingestion | Not implemented | Preserve authorized anatomical evidence and provenance. |
| Patient/knee identity and laterality model | Not implemented | Prevent cross-person, cross-knee, and cross-timepoint mixing. |
| Patient-specific segmentation and 3D anatomy | Not implemented | Reconstruct reviewable anatomical geometry. |
| Multimodal spatial/temporal registration | Not implemented | Align motion and anatomy in explicit coordinate systems. |
| Musculoskeletal or finite-element simulation | Not implemented | Run named virtual experiments with controlled assumptions. |
| Scientific and clinical validation | Not established | Determine permitted interpretation and claims. |

## Delivery plan

### Stage 1 — finish the first external-analysis slice

Complete Milestones 6–8 in `TASKS.md`: capture quality, named bilateral differences, historical replay/reanalysis, bounded processing, migrations, artifact integrity, test coverage, and privacy controls appropriate to the deployment model.

Exit gate: the squat workflow is repeatable, provenance-rich, failure-aware, and reliable enough to serve as a reference implementation. This is a platform foundation, not a declaration that the knee twin is complete.

### Stage 2 — establish the knee evidence platform

Introduce a canonical person → knee/laterality → episode → timepoint → observation model. Define modality-neutral provenance, consent/authorization metadata, immutable source artifacts, coordinate-system descriptors, quality, annotations, and derivation graphs.

Begin with offline, de-identified research imports. Add DICOM or clinical-system integration only after privacy, security, governance, and deployment requirements are explicitly authorized.

Exit gate: the system cannot silently mix people, knees, timepoints, modalities, coordinate systems, or algorithm versions, and every derived object is traceable to source evidence.

### Stage 3 — patient-specific 3D anatomical twin

Ingest supported volumetric imaging and authorized internal imagery. Add reviewed segmentation workflows for bones and selected soft-tissue structures, mesh generation, anatomical landmarks, morphology measurements, and visualization that clearly identifies generic versus patient-specific geometry.

Internal imagery must be registered as partial observations; it must not be treated as a complete geometrical or mechanical measurement of the knee.

Exit gate: representative reconstructions are reproducible, reviewable, quality-controlled, and evaluated against defined reference data with documented error.

### Stage 4 — functional multimodal twin

Add calibrated multi-view motion and supported sensor inputs. Register external kinematics to patient-specific anatomy, define joint coordinate systems, estimate boundary conditions only where inputs support them, and compare compatible longitudinal timepoints.

Exit gate: transformations, calibration errors, uncertainty, and data gaps are visible; results are validated for each supported capture protocol rather than generalized across all footage.

### Stage 5 — virtual experiment and simulation platform

Define a solver-independent experiment contract containing anatomy version, material/property assumptions, loading and boundary conditions, solver version, outputs, sensitivity settings, and validation tier. Integrate replaceable musculoskeletal and finite-element adapters only for named questions supported by available evidence.

Candidate experiments may include motion replay, load-distribution hypotheses, intervention comparisons, implant/graft configuration research, and sensitivity analysis. They must not be described as exact predictions or treatment recommendations without evidence and authorization supporting those claims.

Exit gate: a simulation is reproducible, its uncertainty and sensitivity are reported, and its predictions have been compared against an appropriate reference for the claimed use.

### Stage 6 — validated decision-support pathways

Select narrowly defined intended uses and study them with domain experts, representative datasets, and independent evaluation. Establish data governance, cybersecurity, auditability, human review, and the relevant regulatory strategy before any clinical claims or prospective care use.

Exit gate: product claims match demonstrated evidence and the approved operating context.

## Cross-cutting workstreams

* **Data governance:** consent, de-identification, access, retention, deletion, audit, and research/clinical boundaries.
* **Evidence quality:** modality-specific quality reports and explicit missing/unusable states.
* **Uncertainty:** observed versus inferred values, confidence intervals or sensitivity ranges where scientifically valid.
* **Versioning:** algorithms, segmentations, coordinate transforms, anatomy, material assumptions, experiments, and solvers.
* **Validation:** integration tests are distinct from numerical accuracy, clinical validity, and outcome utility.
* **Interoperability:** use established medical and biomechanical formats where justified; avoid premature infrastructure.
* **Human review:** support expert correction and approval without overwriting machine or source evidence.

## Principal risks

| Risk | Consequence | Control |
| --- | --- | --- |
| Calling estimates “exact” | Unsafe confidence in reconstruction or simulation. | Label evidence class, uncertainty, validation tier, and unsupported quantities. |
| Incomplete internal view | Visible surfaces may be mistaken for whole-knee state. | Register partial observations and display coverage limitations. |
| Registration error | Motion or tissue data can be mapped to the wrong place/time. | Explicit transforms, quality metrics, review, and provenance. |
| Unknown material/loading inputs | Simulation results can look precise while being assumption-driven. | Sensitivity analysis and named assumptions; no silent defaults. |
| Identity/laterality mistakes | Data from the wrong person or knee could be combined. | Canonical identity, laterality, episode, and timepoint constraints. |
| Sensitive medical data | Privacy or safety harm. | Local/de-identified research first; governance before connected clinical use. |
| Scope outruns validation | Impressive visualization may be mistaken for a reliable twin. | Stage gates tied to reference evidence and permitted claims. |

## Immediate priority

Finish the first squat evidence pipeline while designing its new schemas so they can later attach to a specific knee, episode, timepoint, observation, coordinate system, and derivation. Do not add a simulation engine before trustworthy anatomical inputs and validation targets exist.
