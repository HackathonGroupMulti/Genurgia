import json
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import ValidationError

from app.dependencies import ObservationImportServiceDependency
from app.schemas.imports import (
    ArthroscopyImportMetadataV1,
    MultiViewCaptureInputV1,
    ObservationImportResultV1,
)
from app.services.imports import InvalidObservationImport, parse_json_object

router = APIRouter(prefix="/observations/imports", tags=["observation imports"])
UPLOAD_CHUNK_BYTES = 1024 * 1024


@router.post(
    "/mri",
    response_model=ObservationImportResultV1,
    status_code=status.HTTP_201_CREATED,
)
async def import_mri(
    service: ObservationImportServiceDependency,
    archive: Annotated[UploadFile, File()],
    timepoint_id: Annotated[UUID, Form()],
    knee_target_ids: Annotated[str, Form()],
    authorization: Annotated[str, Form()],
) -> ObservationImportResultV1:
    temporary = service.create_temporary_upload(".zip")
    try:
        await _stream_upload(archive, temporary, service.max_upload_bytes)
        return service.import_mri_zip(
            temporary,
            timepoint_id=timepoint_id,
            knee_target_ids=_uuid_list(knee_target_ids),
            authorization=_authorization(authorization),
        )
    except InvalidObservationImport as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    finally:
        service.delete_temporary_upload(temporary)


@router.post(
    "/arthroscopy",
    response_model=ObservationImportResultV1,
    status_code=status.HTTP_201_CREATED,
)
async def import_arthroscopy(
    service: ObservationImportServiceDependency,
    video: Annotated[UploadFile, File()],
    timepoint_id: Annotated[UUID, Form()],
    knee_target_ids: Annotated[str, Form()],
    authorization: Annotated[str, Form()],
    metadata: Annotated[str, Form()],
) -> ObservationImportResultV1:
    temporary = service.create_temporary_upload(Path(video.filename or "").suffix)
    try:
        await _stream_upload(video, temporary, service.max_upload_bytes)
        return service.import_arthroscopy(
            temporary,
            _model(ArthroscopyImportMetadataV1, metadata, "metadata"),
            timepoint_id=timepoint_id,
            knee_target_ids=_uuid_list(knee_target_ids),
            authorization=_authorization(authorization),
        )
    except InvalidObservationImport as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    finally:
        service.delete_temporary_upload(temporary)


@router.post(
    "/multi-view",
    response_model=ObservationImportResultV1,
    status_code=status.HTTP_201_CREATED,
)
async def import_multi_view(
    service: ObservationImportServiceDependency,
    front: Annotated[UploadFile, File()],
    rear: Annotated[UploadFile, File()],
    left_side: Annotated[UploadFile, File()],
    right_side: Annotated[UploadFile, File()],
    timepoint_id: Annotated[UUID, Form()],
    knee_target_ids: Annotated[str, Form()],
    authorization: Annotated[str, Form()],
    manifest: Annotated[str, Form()],
) -> ObservationImportResultV1:
    uploads = [front, rear, left_side, right_side]
    temporary_paths = [
        service.create_temporary_upload(Path(upload.filename or "").suffix)
        for upload in uploads
    ]
    try:
        for upload, temporary in zip(uploads, temporary_paths, strict=True):
            await _stream_upload(upload, temporary, service.max_upload_bytes)
        parsed = _model(MultiViewCaptureInputV1, manifest, "manifest")
        expected_order = ["front", "rear", "left_side", "right_side"]
        sources_by_view = dict(zip(expected_order, temporary_paths, strict=True))
        ordered_sources = [sources_by_view[camera.view] for camera in parsed.cameras]
        return service.import_multiview(
            ordered_sources,
            parsed,
            timepoint_id=timepoint_id,
            knee_target_ids=_uuid_list(knee_target_ids),
            authorization=_authorization(authorization),
        )
    except InvalidObservationImport as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    finally:
        for temporary in temporary_paths:
            service.delete_temporary_upload(temporary)


async def _stream_upload(upload: UploadFile, target: Path, limit: int) -> None:
    size = 0
    with target.open("xb") as destination:
        while chunk := await upload.read(UPLOAD_CHUNK_BYTES):
            size += len(chunk)
            if size > limit:
                raise HTTPException(
                    status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                    detail=f"The uploaded source exceeds the {limit}-byte per-file limit.",
                )
            destination.write(chunk)
    if size == 0:
        raise InvalidObservationImport("An uploaded source file is empty.")


def _authorization(raw: str) -> dict[str, object]:
    value = parse_json_object(raw, "authorization")
    if not isinstance(value.get("basis"), str) or not value["basis"].strip():
        raise InvalidObservationImport("authorization.basis is required.")
    if value.get("deidentified_confirmed") is not True:
        raise InvalidObservationImport("authorization.deidentified_confirmed must be true.")
    return value


def _uuid_list(raw: str) -> list[UUID]:
    try:
        values = json.loads(raw)
        if not isinstance(values, list) or not values:
            raise ValueError
        return [UUID(value) for value in values]
    except (json.JSONDecodeError, TypeError, ValueError, AttributeError) as error:
        raise InvalidObservationImport(
            "knee_target_ids must be a non-empty JSON array of UUID strings."
        ) from error


def _model(model_type, raw: str, label: str):
    try:
        return model_type.model_validate(parse_json_object(raw, label))
    except ValidationError as error:
        raise InvalidObservationImport(f"Invalid {label}: {error}") from error
