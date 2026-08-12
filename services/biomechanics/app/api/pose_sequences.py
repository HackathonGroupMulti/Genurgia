from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from analysis.pose import PoseExtractionError
from app.dependencies import (
    ArtifactStoreDependency,
    KinematicsServiceDependency,
    PoseServiceDependency,
)
from app.schemas.kinematics import KneeFlexionAnalysis
from app.schemas.pose import PoseAnalysisResponse
from app.schemas.quality import CaptureQualityReport
from app.schemas.repetitions import SquatRepetitionAnalysis
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
    captured_at: Annotated[datetime | None, Form()] = None,
    camera_view: Annotated[
        Literal["front", "rear", "left_side", "right_side", "oblique", "unknown"], Form()
    ] = "unknown",
    orientation: Annotated[Literal["portrait", "landscape", "unknown"], Form()] = "unknown",
    laterality_context: Annotated[
        Literal["bilateral", "left", "right", "unknown"], Form()
    ] = "bilateral",
    capture_notes: Annotated[str | None, Form(max_length=1000)] = None,
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
        return service.analyze(
            video.filename,
            video.content_type,
            bytes(content),
            captured_at=captured_at,
            camera_view=camera_view,
            orientation=orientation,
            laterality_context=laterality_context,
            capture_notes=capture_notes,
        )
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


@router.post(
    "/pose-sequences/{pose_sequence_id}/squat-repetitions",
    response_model=SquatRepetitionAnalysis,
)
def create_squat_repetition_analysis(
    pose_sequence_id: UUID,
    service: KinematicsServiceDependency,
) -> SquatRepetitionAnalysis:
    try:
        return service.analyze_squat_repetitions(pose_sequence_id)
    except PoseSequenceNotFound as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except PoseExtractionError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error


@router.post(
    "/pose-sequences/{pose_sequence_id}/capture-quality",
    response_model=CaptureQualityReport,
)
def create_capture_quality_analysis(
    pose_sequence_id: UUID,
    service: KinematicsServiceDependency,
) -> CaptureQualityReport:
    try:
        return service.analyze_capture_quality(pose_sequence_id)
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
