from fastapi import APIRouter, Query

from app.dependencies import SessionRepositoryDependency
from app.schemas.operations import ProcessingOperationList

router = APIRouter(prefix="/operations", tags=["operations"])


@router.get("", response_model=ProcessingOperationList)
def list_operations(
    repository: SessionRepositoryDependency,
    limit: int = Query(default=50, ge=1, le=200),
) -> ProcessingOperationList:
    return ProcessingOperationList(operations=repository.list_processing_operations(limit))
