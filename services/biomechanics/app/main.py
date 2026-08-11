from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.settings import allowed_origins


def create_app() -> FastAPI:
    application = FastAPI(
        title="Knee Twin Biomechanics API",
        description="Kinematic movement-analysis services for Knee Twin.",
        version="0.1.0",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins(),
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["*"],
    )
    application.include_router(health_router)
    return application


app = create_app()
