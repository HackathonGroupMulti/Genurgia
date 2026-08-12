from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from app.persistence import SQLiteSessionRepository
from app.services.kinematics import KinematicsService
from app.services.pose_analysis import PoseAnalysisService
from app.services.sessions import SessionWorkflowService
from app.storage import LocalArtifactStore


def get_pose_analysis_service(request: Request) -> PoseAnalysisService:
    service = request.app.state.pose_analysis_service
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Pose analysis is unavailable because the MediaPipe model is missing. "
                "Run: python scripts/download_pose_model.py"
            ),
        )
    return service


def get_artifact_store(request: Request) -> LocalArtifactStore:
    return request.app.state.artifact_store


def get_kinematics_service(request: Request) -> KinematicsService:
    return request.app.state.kinematics_service


def get_session_repository(request: Request) -> SQLiteSessionRepository:
    return request.app.state.session_repository


def get_session_workflow_service(request: Request) -> SessionWorkflowService:
    return request.app.state.session_workflow_service


PoseServiceDependency = Annotated[PoseAnalysisService, Depends(get_pose_analysis_service)]
ArtifactStoreDependency = Annotated[LocalArtifactStore, Depends(get_artifact_store)]
KinematicsServiceDependency = Annotated[KinematicsService, Depends(get_kinematics_service)]
SessionRepositoryDependency = Annotated[
    SQLiteSessionRepository,
    Depends(get_session_repository),
]
SessionWorkflowDependency = Annotated[
    SessionWorkflowService,
    Depends(get_session_workflow_service),
]
