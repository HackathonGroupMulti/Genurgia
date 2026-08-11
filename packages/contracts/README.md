# API Contracts

This package contains versioned JSON Schemas shared across application boundaries.

The backend Pydantic models are the source of truth. Regenerate schemas from the repository root after a contract change:

```powershell
$env:PYTHONPATH = "services/biomechanics"
.\.venv\Scripts\python scripts\export_contracts.py
```

Tests verify that the committed schemas remain synchronized. Do not place biomechanics calculations in this package.
