from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.evidence import router as evidence_router
from app.api.health import router as health_router
from app.api.imports import router as imports_router
from app.api.operations import router as operations_router
from app.api.pose_sequences import router as pose_sequences_router
from app.api.sessions import router as sessions_router
from app.evidence_repository import EvidenceConflict, EvidenceNotFound, SQLiteEvidenceRepository
from app.persistence import SQLiteSessionRepository
from app.services.imports import ObservationImportService
from app.services.kinematics import KinematicsService
from app.services.pose_analysis import PoseAnalysisService
from app.services.sessions import SessionWorkflowService
from app.settings import (
    allowed_origins,
    artifact_root,
    max_observation_upload_bytes,
    max_video_upload_bytes,
    pose_model_path,
    session_database_path,
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
    session_repository: SQLiteSessionRepository | None = None,
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
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["*"],
    )
    store = artifact_store or LocalArtifactStore(artifact_root())
    store.cleanup_abandoned_work()
    sessions = session_repository or SQLiteSessionRepository(
        session_database_path() if artifact_store is None else store.root / "knee_twin.sqlite3"
    )
    evidence = SQLiteEvidenceRepository(sessions.database_path)
    evidence.reconcile_legacy_source_hashes(store)
    if isinstance(pose_analysis_service, _AutoConfigurePoseService):
        if pose_model_path().is_file():
            from analysis.mediapipe_pose import MediaPipePoseProvider

            configured_pose_service: PoseAnalysisService | None = PoseAnalysisService(
                artifact_store=store,
                pose_provider=MediaPipePoseProvider(pose_model_path()),
                max_upload_bytes=max_video_upload_bytes(),
                session_repository=sessions,
            )
        else:
            configured_pose_service = None
    else:
        configured_pose_service = pose_analysis_service
    application.state.artifact_store = store
    application.state.pose_analysis_service = configured_pose_service
    kinematics = KinematicsService(store, sessions)
    application.state.kinematics_service = kinematics
    application.state.session_repository = sessions
    application.state.evidence_repository = evidence
    application.state.observation_import_service = ObservationImportService(
        store,
        evidence,
        max_observation_upload_bytes(),
    )
    application.state.session_workflow_service = SessionWorkflowService(
        sessions,
        store,
        kinematics,
    )
    application.include_router(health_router)
    application.include_router(imports_router)
    application.include_router(evidence_router)
    application.include_router(operations_router)
    application.include_router(pose_sequences_router)
    application.include_router(sessions_router)
    application.add_exception_handler(
        EvidenceNotFound,
        lambda _request, error: JSONResponse(
            status_code=404,
            content={"detail": str(error)},
        ),
    )
    application.add_exception_handler(
        EvidenceConflict,
        lambda _request, error: JSONResponse(
            status_code=409,
            content={"detail": str(error)},
        ),
    )
    return application


app = create_app()
