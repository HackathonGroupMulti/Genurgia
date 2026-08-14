# Synthetic FEBio flexion fixture

This directory defines the CC0 public fixture workflow for Milestone 14. The generated topology is intentionally tiny and non-anatomical. It exists to exercise import, provenance, FEBio generation, independent pose execution, partial failures, and result rendering. It is not evidence about a human knee.

Create or import a reconstruction containing the complete Knee Twin structure taxonomy, then build the solver-ready ZIP with its real identity and coordinate convention:

```powershell
cd services/biomechanics
..\..\.venv\Scripts\python.exe ..\..\scripts\build_synthetic_fe_fixture.py `
  --reconstruction-id RECONSTRUCTION_UUID `
  --laterality left `
  --coordinate-system synthetic-knee-right-handed-mm `
  --output ..\..\data\samples\febio-flexion-demo\cc0-synthetic-flexion-v1.zip
```

Import the ZIP through `POST /simulation-models/imports/febio` or the Knee Lab. The Lab exposes its fixture-only assumption manifest only for a model with version `cc0-synthetic-flexion-v1`.

The generated files are offered under CC0 1.0 Universal. See [LICENSE.md](LICENSE.md).
