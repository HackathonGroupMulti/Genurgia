import os
from pathlib import Path
from urllib.parse import urlparse

DEFAULT_ALLOWED_ORIGINS = ("http://localhost:3000",)
DEFAULT_MAX_VIDEO_UPLOAD_BYTES = 100 * 1024 * 1024


def repository_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _configured_path(variable: str, default: Path) -> Path:
    configured = os.getenv(variable)
    path = Path(configured) if configured else default
    if not path.is_absolute():
        path = repository_root() / path
    return path.resolve()


def allowed_origins() -> list[str]:
    configured = os.getenv("CORS_ALLOWED_ORIGINS")
    if configured is None:
        return list(DEFAULT_ALLOWED_ORIGINS)

    origins = [origin.strip() for origin in configured.split(",") if origin.strip()]
    for origin in origins:
        if urlparse(origin).hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise ValueError("CORS_ALLOWED_ORIGINS must contain only loopback origins.")
    return origins


def artifact_root() -> Path:
    return _configured_path("KNEE_TWIN_ARTIFACT_DIR", repository_root() / "data" / "local")


def session_database_path() -> Path:
    return _configured_path(
        "KNEE_TWIN_DATABASE_PATH",
        repository_root() / "data" / "local" / "knee_twin.sqlite3",
    )


def pose_model_path() -> Path:
    return _configured_path(
        "POSE_LANDMARKER_MODEL_PATH",
        repository_root() / "data" / "models" / "pose_landmarker_full.task",
    )


def max_video_upload_bytes() -> int:
    configured = os.getenv("MAX_VIDEO_UPLOAD_BYTES")
    if configured is None:
        return DEFAULT_MAX_VIDEO_UPLOAD_BYTES

    value = int(configured)
    if value <= 0:
        raise ValueError("MAX_VIDEO_UPLOAD_BYTES must be a positive integer.")
    return value
