"""Download the pinned MediaPipe Pose Landmarker model with checksum verification."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import urllib.request
from pathlib import Path

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_full/float16/1/pose_landmarker_full.task"
)
MODEL_SHA256 = "5134a3aad27a58b93da0088d431f366da362b44e3ccfbe3462b3827a839011b1"
DEFAULT_DESTINATION = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "models"
    / "pose_landmarker_full.task"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as model_file:
        for chunk in iter(lambda: model_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_file() and sha256(destination) == MODEL_SHA256:
        print(f"Model already verified: {destination}")
        return

    temporary = destination.with_suffix(".download")
    try:
        with urllib.request.urlopen(MODEL_URL) as response, temporary.open("wb") as output:
            shutil.copyfileobj(response, output)
        actual_hash = sha256(temporary)
        if actual_hash != MODEL_SHA256:
            raise RuntimeError(
                f"Model checksum mismatch: expected {MODEL_SHA256}, received {actual_hash}"
            )
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)

    print(f"Downloaded and verified: {destination}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", type=Path, default=DEFAULT_DESTINATION)
    arguments = parser.parse_args()
    download(arguments.destination.resolve())


if __name__ == "__main__":
    main()
