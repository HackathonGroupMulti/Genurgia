from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.dependencies import SessionRepositoryDependency, SessionWorkflowDependency
from app.persistence import SessionNotFound
from app.schemas.sessions import (
    ReanalysisRequest,
    ReanalysisResponse,
    SelectedSessionComparison,
    SessionComparisonResponse,
    SessionExportManifest,
    SessionListResponse,
    SessionSummary,
)

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("", response_model=SessionListResponse)
def list_sessions(
    repository: SessionRepositoryDependency,
    limit: int = Query(default=50, ge=1, le=200),
) -> SessionListResponse:
    return SessionListResponse(sessions=repository.list_sessions(limit))


@router.get("/comparison", response_model=SessionComparisonResponse)
def compare_sessions(
    repository: SessionRepositoryDependency,
    limit: int = Query(default=10, ge=2, le=50),
) -> SessionComparisonResponse:
    return SessionComparisonResponse(sessions=repository.compare_sessions(limit))


@router.get("/selected-comparison", response_model=SelectedSessionComparison)
def compare_selected_sessions(
    repository: SessionRepositoryDependency,
    baseline_id: Annotated[UUID, Query()],
    current_id: Annotated[UUID, Query()],
) -> SelectedSessionComparison:
    try:
        return repository.compare_selected_sessions(baseline_id, current_id)
    except SessionNotFound as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/{session_id}", response_model=SessionSummary)
def get_session(
    session_id: UUID,
    repository: SessionRepositoryDependency,
) -> SessionSummary:
    try:
        return repository.get_session(session_id)
    except SessionNotFound as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.post("/{session_id}/reanalysis", response_model=ReanalysisResponse)
def reanalyze_session(
    session_id: UUID,
    request: ReanalysisRequest,
    service: SessionWorkflowDependency,
) -> ReanalysisResponse:
    try:
        return service.reanalyze(session_id, list(dict.fromkeys(request.analyses)))
    except SessionNotFound as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/{session_id}/export-manifest", response_model=SessionExportManifest)
def export_session_manifest(
    session_id: UUID,
    service: SessionWorkflowDependency,
) -> SessionExportManifest:
    try:
        return service.export_manifest(session_id)
    except SessionNotFound as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
