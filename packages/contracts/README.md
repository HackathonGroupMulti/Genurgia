# API Contracts

This package contains versioned JSON Schemas shared across application boundaries.

The backend Pydantic models are the source of truth. Regenerate schemas from the repository root after a contract change:

```powershell
$env:PYTHONPATH = "services/biomechanics"
.\.venv\Scripts\python scripts\export_contracts.py
```

Tests verify that the committed schemas remain synchronized. Do not place biomechanics calculations in this package.

Milestone 14 exports additive schemas for immutable simulation-model listings, the contributor-authored finite-element package, queued import request/result, `ExperimentDefinitionV2`, per-pose results, normalized field manifests, FEBio sweep results, and adapter capability/preflight reports. `ExperimentDefinitionV1` remains supported. Corresponding TypeScript contracts and runtime parsers live in `apps/web/lib/simulation-contracts.ts`; the parser keeps server payloads at the trust boundary.
