import os

DEFAULT_ALLOWED_ORIGINS = ("http://localhost:3000",)


def allowed_origins() -> list[str]:
    configured = os.getenv("CORS_ALLOWED_ORIGINS")
    if configured is None:
        return list(DEFAULT_ALLOWED_ORIGINS)

    return [origin.strip() for origin in configured.split(",") if origin.strip()]
