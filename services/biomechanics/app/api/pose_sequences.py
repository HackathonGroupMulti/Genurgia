from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from analysis.pose import PoseExtractionError
from app.dependencies import (
    ArtifactStoreDependency,
    KinematicsServiceDependency,
    PoseServiceDependency,
)
from app.schemas.kinematics import KneeFlexionAnalysis
from app.schemas.pose import PoseAnalysisResponse
from app.services.kinematics import PoseSequenceNotFound
from app.services.pose_analysis import InvalidVideoUpload

router = APIRouter(tags=["pose sequences"])
UPLOAD_CHUNK_BYTES = 1024 * 1024


@router.post(
    "/pose-sequences",
    response_model=PoseAnalysisResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_pose_sequence(
    service: PoseServiceDependency,
    video: Annotated[UploadFile, File()],
) -> PoseAnalysisResponse:
    content = bytearray()
    while chunk := await video.read(UPLOAD_CHUNK_BYTES):
        content.extend(chunk)
        if len(content) > service.max_upload_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"The uploaded video exceeds the {service.max_upload_bytes}-byte limit.",
            )

    try:
        return service.analyze(video.filename, video.content_type, bytes(content))
    except InvalidVideoUpload as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error


@router.post(
    "/pose-sequences/{pose_sequence_id}/knee-flexion",
    response_model=KneeFlexionAnalysis,
)
def create_knee_flexion_analysis(
    pose_sequence_id: UUID,
    service: KinematicsServiceDependency,
) -> KneeFlexionAnalysis:
    try:
        return service.analyze_knee_flexion(pose_sequence_id)
    except PoseSequenceNotFound as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except PoseExtractionError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error


@router.get("/artifacts/{pose_sequence_id}/{filename}", response_class=FileResponse)
def get_artifact(
    pose_sequence_id: UUID,
    filename: str,
    artifacts: ArtifactStoreDependency,
) -> FileResponse:
    try:
        artifact = artifacts.path_for(pose_sequence_id, filename)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from error

    if not artifact.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found.")

    media_type = {
        ".json": "application/json",
        ".mp4": "video/mp4",
        ".mov": "video/quicktime",
        ".webm": "video/webm",
    }.get(Path(filename).suffix.lower(), "application/octet-stream")
    return FileResponse(artifact, media_type=media_type)
