from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.dependencies import ReconstructionImportServiceDependency
from app.schemas.reconstruction import ReconstructionImportResultV1
from app.services.reconstructions import InvalidReconstructionPackage

router = APIRouter(prefix="/reconstructions/imports", tags=["reconstruction imports"])
UPLOAD_CHUNK_BYTES = 1024 * 1024


@router.post(
    "/manual",
    response_model=ReconstructionImportResultV1,
    status_code=status.HTTP_201_CREATED,
)
async def import_manual_reconstruction(
    service: ReconstructionImportServiceDependency,
    package: Annotated[UploadFile, File()],
) -> ReconstructionImportResultV1:
    if Path(package.filename or "").suffix.lower() != ".zip":
        raise HTTPException(status_code=422, detail="Reconstruction package must be a ZIP.")
    temporary = service.create_temporary_upload()
    try:
        size = 0
        with temporary.open("xb") as destination:
            while chunk := await package.read(UPLOAD_CHUNK_BYTES):
                size += len(chunk)
                if size > service.max_upload_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                        detail=(
                            "The reconstruction package exceeds the configured upload limit."
                        ),
                    )
                destination.write(chunk)
        if size == 0:
            raise InvalidReconstructionPackage("The reconstruction package is empty.")
        return service.import_manual_package(temporary)
    except InvalidReconstructionPackage as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    finally:
        service.delete_temporary_upload(temporary)
