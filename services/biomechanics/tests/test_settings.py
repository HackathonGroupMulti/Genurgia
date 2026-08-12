from app.settings import DEFAULT_ALLOWED_ORIGINS, allowed_origins


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

    import pytest

    with pytest.raises(ValueError, match="loopback"):
        allowed_origins()
