import json
import shutil
from pathlib import Path
from typing import Any
from uuid import UUID


class LocalArtifactStore:
    """Simple local storage boundary for videos and analysis artifacts."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def create_bundle(self, bundle_id: UUID) -> Path:
        bundle = self.root / str(bundle_id)
        bundle.mkdir(parents=False, exist_ok=False)
        return bundle

    def write_bytes(self, bundle_id: UUID, filename: str, content: bytes) -> Path:
        target = self.path_for(bundle_id, filename)
        target.write_bytes(content)
        return target

    def write_json(self, bundle_id: UUID, filename: str, value: Any) -> Path:
        target = self.path_for(bundle_id, filename)
        target.write_text(
            json.dumps(value, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return target

    def path_for(self, bundle_id: UUID, filename: str) -> Path:
        if Path(filename).name != filename:
            raise ValueError("Artifact filename must not contain path segments.")

        bundle = (self.root / str(bundle_id)).resolve()
        target = (bundle / filename).resolve()
        if target.parent != bundle or self.root not in target.parents:
            raise ValueError("Artifact path escapes the configured storage root.")
        return target

    def delete_bundle(self, bundle_id: UUID) -> None:
        bundle = (self.root / str(bundle_id)).resolve()
        if bundle.parent != self.root:
            raise ValueError("Artifact bundle escapes the configured storage root.")
        if bundle.is_dir():
            shutil.rmtree(bundle)

    @staticmethod
    def reference(bundle_id: UUID, filename: str) -> str:
        return f"/artifacts/{bundle_id}/{filename}"
