# Product

## What Knee Twin is

Knee Twin is a longitudinal, patient-specific digital representation of a knee. Its intended scope is the complete knee system: external movement, internal anatomy, tissue condition, intervention history, and simulated mechanical behavior over time.

Squat analysis is the first implemented observation workflow, not the product boundary. It proves that Knee Twin can ingest evidence, preserve raw observations, derive versioned measurements, replay them in context, and compare timepoints. Later workflows should apply the same principles to additional movements, medical images, internal knee imagery, 3D anatomical models, and validated simulations.

Knee Twin is currently a research and engineering system, not a diagnostic medical device. Derived outputs must identify their source evidence, assumptions, uncertainty, algorithm version, and validation status.

Its early value is not numerical authority. Knee Twin is an open hypothesis machine: it should make a structurally valid attempt when a researcher explicitly supplies the missing physics assumptions, preserve failures and non-convergence, and expose enough provenance for another contributor to replace any weak model. Engineering reproducibility and scientific accuracy are separate gates.

## Product goal

Create a living knee record that can answer, at a specific point in time:

* What evidence exists for this knee?
* What anatomy and motion can be reconstructed from that evidence?
* What changed between timepoints, such as before and after an injury or intervention?
* Which quantities were directly observed, estimated, inferred, or simulated?
* How confident is each result, and what evidence is missing?
* Which virtual scenarios can be explored without exposing the person to unnecessary physical loading?

Virtual testing is intended to reduce avoidable risk and narrow physical testing, not automatically replace clinical examination or validated physical measurements. A simulation result is only as trustworthy as its inputs, model assumptions, calibration, and validation.

## Evidence domains

Knee Twin should support multiple evidence types without pretending they are interchangeable.

### External movement evidence

* monocular and multi-view video;
* markerless or marker-based motion capture;
* depth cameras;
* force plates, pressure data, and instrumented equipment;
* wearable and rehabilitation sensor data;
* standardized movement protocols such as squats, gait, running, jumping, cutting, and stairs.

### Internal and anatomical evidence

* MRI and CT image series where lawfully available;
* ultrasound and other supported imaging;
* arthroscopy or other internal imagery supplied through an authorized clinical/research workflow;
* clinician-authored landmarks, segmentations, and operative observations;
* implant, graft, injury, and procedure metadata with provenance.

Internal footage can provide valuable direct surface observations, but it does not by itself produce exact whole-knee geometry, material properties, loads, or tissue mechanics. Those require registration with other evidence and must remain explicitly estimated where they are not directly measured.

## Twin layers

The product should mature as composable layers:

1. **Evidence record** — immutable source observations, consent/provenance, capture context, and quality.
2. **Measurement layer** — versioned kinematics, morphology, tissue annotations, and longitudinal changes.
3. **Anatomical twin** — patient-specific 3D geometry reconstructed from appropriate imaging and reviewed segmentations.
4. **Functional twin** — external movement registered to anatomy using calibrated coordinate systems and boundary conditions.
5. **Simulation twin** — validated musculoskeletal and/or finite-element models for explicitly defined virtual experiments.

Every layer must remain usable without claiming that a later layer exists. The UI must distinguish observed, reconstructed, estimated, and simulated data.

## Core longitudinal workflow

1. Establish the person, left/right knee, episode, and timepoint.
2. Import an authorized source observation and retain it unchanged.
3. Record provenance, capture protocol, coordinate system, consent, and quality.
4. Derive versioned measurements without overwriting source evidence.
5. Register compatible observations into a common patient/knee coordinate context.
6. Construct or update the appropriate 3D representation.
7. Compare compatible timepoints and expose uncertainty or missing inputs.
8. Configure a named virtual experiment with explicit assumptions and boundary conditions.
9. Run a versioned solver and preserve inputs, outputs, validation status, and reproducibility metadata.
10. Inspect unsuccessful or low-tier experiments without mistaking them for absent evidence or validated predictions.
11. Present results as research or decision-support evidence appropriate to their validation level.

## First implementation slice: squat movement analysis

The repository implements the initial squat workflow:

* video upload and decoding;
* timestamped raw pose-landmark preservation;
* annotated replay;
* modeled left/right knee flexion;
* confidence and unavailable states;
* repetition boundaries, per-repetition ROM, and exact bilateral differences;
* capture-quality signals and actionable recording guidance;
* capture time, view/orientation, knee context, and notes;
* local session persistence, explicit compatible comparison, historical replay, and reanalysis;
* synchronized video, charts, and a model-relative skeleton.

Participant-diverse validation remains open. The implemented slice establishes engineering patterns for evidence provenance and longitudinal analysis; it does not complete the Knee Twin product.

## Safety and claims boundary

Until a capability has an approved validation and regulatory path, Knee Twin must not claim:

* diagnosis or treatment selection;
* exact internal tissue forces or failure thresholds;
* guaranteed injury prediction;
* equivalence to MRI, CT, arthroscopy, motion capture, force measurement, or clinical examination;
* that a virtual test is safe enough to replace a required real-world or clinical test;
* that generated 3D geometry is patient-specific when it is only a generic visualization.

The long-term ambition is a high-fidelity, evidence-linked knee twin. Scientific uncertainty is part of that product, not something to hide.
