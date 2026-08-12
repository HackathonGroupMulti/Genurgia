import hashlib
import json
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

ARTIFACT_MANIFEST_FILENAME = "artifact_manifest_v1.json"


class LocalArtifactStore:
    """Atomic local storage boundary for immutable evidence and derived artifacts."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._staging_root = self.root / ".staging"
        self._upload_root = self.root / ".uploads"
        self._trash_root = self.root / ".trash"
        self._staging_root.mkdir(exist_ok=True)
        self._upload_root.mkdir(exist_ok=True)
        self._trash_root.mkdir(exist_ok=True)

    def create_temporary_upload(self, extension: str = ".upload") -> Path:
        safe_extension = (
            extension.lower()
            if extension.lower() in {".mp4", ".mov", ".webm", ".zip", ".dcm"}
            else ".upload"
        )
        return self._upload_root / f"{uuid4()}{safe_extension}"

    def delete_temporary_upload(self, path: Path) -> None:
        resolved = path.resolve()
        if resolved.parent != self._upload_root:
            raise ValueError("Temporary upload escapes the configured upload directory.")
        resolved.unlink(missing_ok=True)

    def begin_bundle(self, bundle_id: UUID) -> Path:
        staging = (self._staging_root / f"{bundle_id}-{uuid4()}").resolve()
        if staging.parent != self._staging_root:
            raise ValueError("Artifact staging path escapes the configured storage root.")
        staging.mkdir(parents=False, exist_ok=False)
        return staging

    def staging_path(self, staging: Path, filename: str) -> Path:
        staging = staging.resolve()
        if staging.parent != self._staging_root or not staging.is_dir():
            raise ValueError("Unknown artifact staging directory.")
        return self._safe_child(staging, filename)

    def copy_to_staging(self, staging: Path, filename: str, source: Path) -> Path:
        target = self.staging_path(staging, filename)
        shutil.copyfile(source, target)
        return target

    def write_staged_json(self, staging: Path, filename: str, value: Any) -> Path:
        target = self.staging_path(staging, filename)
        self._write_json_file(target, value)
        return target

    def publish_bundle(self, bundle_id: UUID, staging: Path) -> Path:
        staging = staging.resolve()
        if staging.parent != self._staging_root or not staging.is_dir():
            raise ValueError("Unknown artifact staging directory.")
        target = self._bundle_path(bundle_id)
        if target.exists():
            raise FileExistsError(f"Artifact bundle {bundle_id} already exists.")
        self._write_manifest(staging, bundle_id)
        os.replace(staging, target)
        return target

    def abort_bundle(self, staging: Path) -> None:
        staging = staging.resolve()
        if staging.parent != self._staging_root:
            raise ValueError("Artifact staging path escapes the configured storage root.")
        if staging.is_dir():
            shutil.rmtree(staging)

    def write_bytes(self, bundle_id: UUID, filename: str, content: bytes) -> Path:
        target = self.path_for(bundle_id, filename)
        temporary = target.with_name(f".{target.name}.{uuid4()}.tmp")
        try:
            temporary.write_bytes(content)
            os.replace(temporary, target)
            self._refresh_manifest(bundle_id)
        finally:
            temporary.unlink(missing_ok=True)
        return target

    def write_json(self, bundle_id: UUID, filename: str, value: Any) -> Path:
        target = self.path_for(bundle_id, filename)
        temporary = target.with_name(f".{target.name}.{uuid4()}.tmp")
        try:
            self._write_json_file(temporary, value)
            os.replace(temporary, target)
            self._refresh_manifest(bundle_id)
        finally:
            temporary.unlink(missing_ok=True)
        return target

    def path_for(self, bundle_id: UUID, filename: str) -> Path:
        bundle = self._bundle_path(bundle_id)
        return self._safe_child(bundle, filename)

    def verify_bundle(self, bundle_id: UUID) -> list[dict[str, Any]]:
        bundle = self._bundle_path(bundle_id)
        manifest_path = self._safe_child(bundle, ARTIFACT_MANIFEST_FILENAME)
        if not manifest_path.is_file():
            return []
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        results: list[dict[str, Any]] = []
        tracked_names: set[str] = set()
        for expected in manifest.get("artifacts", []):
            tracked_names.add(expected["filename"])
            path = self._safe_child(bundle, expected["filename"])
            exists = path.is_file()
            actual_hash = _sha256(path) if exists else None
            results.append(
                {
                    **expected,
                    "exists": exists,
                    "actual_sha256": actual_hash,
                    "integrity": (
                        "verified"
                        if exists and actual_hash == expected["sha256"]
                        else "checksum_mismatch"
                        if exists
                        else "missing"
                    ),
                }
            )
        for path in bundle.iterdir():
            if (
                not path.is_file()
                or path.name == ARTIFACT_MANIFEST_FILENAME
                or path.name in tracked_names
                or (path.name.startswith(".") and path.name.endswith(".tmp"))
            ):
                continue
            results.append(
                {
                    "filename": path.name,
                    "size_bytes": path.stat().st_size,
                    "sha256": None,
                    "exists": True,
                    "actual_sha256": _sha256(path),
                    "integrity": "untracked",
                }
            )
        return results

    def delete_bundle(self, bundle_id: UUID) -> None:
        bundle = self._bundle_path(bundle_id)
        if bundle.is_dir():
            shutil.rmtree(bundle)

    def stage_bundle_deletion(self, bundle_id: UUID) -> Path:
        bundle = self._bundle_path(bundle_id)
        if not bundle.is_dir():
            raise FileNotFoundError(f"Artifact bundle {bundle_id} was not found.")
        staged = (self._trash_root / f"{bundle_id}-{uuid4()}").resolve()
        if staged.parent != self._trash_root:
            raise ValueError("Artifact deletion path escapes the configured storage root.")
        os.replace(bundle, staged)
        return staged

    def restore_staged_deletion(self, bundle_id: UUID, staged: Path) -> None:
        staged = staged.resolve()
        if staged.parent != self._trash_root:
            raise ValueError("Artifact deletion path escapes the configured storage root.")
        os.replace(staged, self._bundle_path(bundle_id))

    def finalize_staged_deletion(self, staged: Path) -> None:
        staged = staged.resolve()
        if staged.parent != self._trash_root:
            raise ValueError("Artifact deletion path escapes the configured storage root.")
        if staged.is_dir():
            shutil.rmtree(staged)

    def cleanup_abandoned_work(self) -> int:
        removed = 0
        for directory in (self._staging_root, self._upload_root):
            for child in directory.iterdir():
                if child.is_dir():
                    shutil.rmtree(child)
                else:
                    child.unlink()
                removed += 1
        return removed

    @staticmethod
    def reference(bundle_id: UUID, filename: str) -> str:
        return f"/artifacts/{bundle_id}/{filename}"

    def _bundle_path(self, bundle_id: UUID) -> Path:
        bundle = (self.root / str(bundle_id)).resolve()
        if bundle.parent != self.root:
            raise ValueError("Artifact bundle escapes the configured storage root.")
        return bundle

    @staticmethod
    def _safe_child(parent: Path, filename: str) -> Path:
        if Path(filename).name != filename:
            raise ValueError("Artifact filename must not contain path segments.")
        target = (parent / filename).resolve()
        if target.parent != parent.resolve():
            raise ValueError("Artifact path escapes its bundle.")
        return target

    @staticmethod
    def _write_json_file(path: Path, value: Any) -> None:
        path.write_text(
            json.dumps(value, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def _refresh_manifest(self, bundle_id: UUID) -> None:
        self._write_manifest(self._bundle_path(bundle_id), bundle_id)

    def _write_manifest(self, bundle: Path, bundle_id: UUID) -> None:
        artifacts = []
        for path in sorted(bundle.iterdir(), key=lambda item: item.name):
            if not path.is_file() or path.name == ARTIFACT_MANIFEST_FILENAME:
                continue
            if path.name.startswith(".") and path.name.endswith(".tmp"):
                continue
            artifacts.append(
                {
                    "filename": path.name,
                    "size_bytes": path.stat().st_size,
                    "sha256": _sha256(path),
                }
            )
        manifest = {
            "schema_version": "1.0.0",
            "bundle_id": str(bundle_id),
            "generated_at": datetime.now(UTC).isoformat(),
            "artifacts": artifacts,
        }
        target = self._safe_child(bundle, ARTIFACT_MANIFEST_FILENAME)
        temporary = target.with_name(f".{target.name}.{uuid4()}.tmp")
        try:
            self._write_json_file(temporary, manifest)
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
