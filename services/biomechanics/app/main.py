from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.pose_sequences import router as pose_sequences_router
from app.services.kinematics import KinematicsService
from app.services.pose_analysis import PoseAnalysisService
from app.settings import (
    allowed_origins,
    artifact_root,
    max_video_upload_bytes,
    pose_model_path,
)
from app.storage import LocalArtifactStore


class _AutoConfigurePoseService:
    pass


AUTO_CONFIGURE_POSE_SERVICE = _AutoConfigurePoseService()


def create_app(
    pose_analysis_service: PoseAnalysisService | None | _AutoConfigurePoseService = (
        AUTO_CONFIGURE_POSE_SERVICE
    ),
    artifact_store: LocalArtifactStore | None = None,
) -> FastAPI:
    application = FastAPI(
        title="Knee Twin Biomechanics API",
        description="Kinematic movement-analysis services for Knee Twin.",
        version="0.1.0",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins(),
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    store = artifact_store or LocalArtifactStore(artifact_root())
    if isinstance(pose_analysis_service, _AutoConfigurePoseService):
        if pose_model_path().is_file():
            from analysis.mediapipe_pose import MediaPipePoseProvider

            configured_pose_service: PoseAnalysisService | None = PoseAnalysisService(
                artifact_store=store,
                pose_provider=MediaPipePoseProvider(pose_model_path()),
                max_upload_bytes=max_video_upload_bytes(),
            )
        else:
            configured_pose_service = None
    else:
        configured_pose_service = pose_analysis_service
    application.state.artifact_store = store
    application.state.pose_analysis_service = configured_pose_service
    application.state.kinematics_service = KinematicsService(store)
    application.include_router(health_router)
    application.include_router(pose_sequences_router)
    return application


app = create_app()
