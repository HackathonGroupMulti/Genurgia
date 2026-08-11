from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.dependencies import SessionRepositoryDependency
from app.persistence import SessionNotFound
from app.schemas.sessions import (
    SessionComparisonResponse,
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


@router.get("/{session_id}", response_model=SessionSummary)
def get_session(
    session_id: UUID,
    repository: SessionRepositoryDependency,
) -> SessionSummary:
    try:
        return repository.get_session(session_id)
    except SessionNotFound as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
