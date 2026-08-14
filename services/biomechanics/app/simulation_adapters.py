import hashlib
import os
import re
import shutil
import subprocess
from pathlib import Path

from app.schemas.simulation import SimulationAdapterCapabilityV1

FEBIO_VERSION_PATTERN = re.compile(r"(?:FEBio[^0-9]*)?(4\.12)(?:\.\d+)?", re.IGNORECASE)


def febio_preflight(
    configured_executable: str | None,
    workspace: Path,
) -> SimulationAdapterCapabilityV1:
    reasons: list[str] = []
    executable = _resolve_executable(configured_executable)
    detected_version: str | None = None
    executable_sha256: str | None = None
    if executable is None:
        reasons.append(
            "FEBio was not found. Set FEBIO_EXECUTABLE to a separately installed 4.12 binary."
        )
    else:
        executable_sha256 = _sha256(executable)
        detected_version = _detect_version(executable)
        if detected_version != "4.12":
            reasons.append(
                "The first adapter requires FEBio 4.12; "
                f"detected {detected_version or 'an unreadable version'}."
            )
    if not workspace.is_dir() or not os.access(workspace, os.W_OK):
        reasons.append("The configured artifact workspace is not writable.")
    return SimulationAdapterCapabilityV1(
        available=not reasons,
        executable_path=str(executable) if executable else None,
        executable_sha256=executable_sha256,
        detected_version=detected_version,
        unavailable_reasons=reasons,
    )


def _resolve_executable(configured: str | None) -> Path | None:
    if configured:
        candidate = Path(configured)
        if not candidate.is_absolute() or not candidate.is_file():
            return None
        return candidate.resolve()
    discovered = shutil.which("febio4") or shutil.which("febio")
    return Path(discovered).resolve() if discovered else None


def _detect_version(executable: Path) -> str | None:
    for argument in ("--version", "-v"):
        try:
            completed = subprocess.run(
                [str(executable), argument],
                capture_output=True,
                check=False,
                text=True,
                timeout=5,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        match = FEBIO_VERSION_PATTERN.search(completed.stdout + "\n" + completed.stderr)
        if match:
            return match.group(1)
    return None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
