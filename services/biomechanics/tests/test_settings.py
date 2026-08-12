import pytest

from app.settings import (
    DEFAULT_ALLOWED_ORIGINS,
    DEFAULT_MAX_OBSERVATION_UPLOAD_BYTES,
    allowed_origins,
    max_observation_upload_bytes,
)


def test_allowed_origins_uses_local_frontend_by_default(monkeypatch) -> None:
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)

    assert allowed_origins() == list(DEFAULT_ALLOWED_ORIGINS)


def test_allowed_origins_parses_comma_separated_values(monkeypatch) -> None:
    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:3000, http://127.0.0.1:3001",
    )

    assert allowed_origins() == ["http://localhost:3000", "http://127.0.0.1:3001"]


def test_allowed_origins_rejects_non_loopback_origin(monkeypatch) -> None:
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://example.test")

    with pytest.raises(ValueError, match="loopback"):
        allowed_origins()


def test_observation_upload_limit_is_bounded_and_configurable(monkeypatch) -> None:
    monkeypatch.delenv("MAX_OBSERVATION_UPLOAD_BYTES", raising=False)
    assert max_observation_upload_bytes() == DEFAULT_MAX_OBSERVATION_UPLOAD_BYTES

    monkeypatch.setenv("MAX_OBSERVATION_UPLOAD_BYTES", "4096")
    assert max_observation_upload_bytes() == 4096

    monkeypatch.setenv("MAX_OBSERVATION_UPLOAD_BYTES", "0")
    with pytest.raises(ValueError, match="positive"):
        max_observation_upload_bytes()
