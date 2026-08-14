from pathlib import Path
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.dependencies import (
    ArtifactStoreDependency,
    EvidenceRepositoryDependency,
    JobRunnerDependency,
)
from app.schemas.evidence import SimulationModel, SimulationModelList
from app.schemas.jobs import JobCreateV1, JobV1
from app.schemas.simulation import SimulationAdapterListV1
from app.settings import febio_executable, max_observation_upload_bytes
from app.simulation_adapters import febio_preflight

router = APIRouter(tags=["simulation"])
UPLOAD_CHUNK_BYTES = 1024 * 1024


@router.post(
    "/simulation-models/imports/febio",
    response_model=JobV1,
    status_code=status.HTTP_202_ACCEPTED,
)
async def import_febio_simulation_model(
    artifacts: ArtifactStoreDependency,
    jobs: JobRunnerDependency,
    package: Annotated[UploadFile, File()],
) -> JobV1:
    if Path(package.filename or "").suffix.lower() != ".zip":
        raise HTTPException(status_code=422, detail="FE model package must be a ZIP.")
    temporary = artifacts.create_temporary_upload(".zip")
    upload_bundle_id: UUID | None = None
    try:
        size = 0
        with temporary.open("xb") as destination:
            while chunk := await package.read(UPLOAD_CHUNK_BYTES):
                size += len(chunk)
                if size > max_observation_upload_bytes():
                    raise HTTPException(
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                        detail="The FE model package exceeds the configured upload limit.",
                    )
                destination.write(chunk)
        if size == 0:
            raise HTTPException(status_code=422, detail="The FE model package is empty.")
        upload_bundle_id = uuid4()
        staging = artifacts.begin_bundle(upload_bundle_id)
        try:
            artifacts.copy_to_staging(staging, "source_fe_model_package.zip", temporary)
            artifacts.publish_bundle(upload_bundle_id, staging)
        except Exception:
            artifacts.abort_bundle(staging)
            raise
        try:
            return jobs.create(
                JobCreateV1(
                    job_type="febio-model-import-v1",
                    request={"upload_bundle_id": str(upload_bundle_id)},
                )
            )
        except Exception:
            artifacts.delete_bundle(upload_bundle_id)
            raise
    finally:
        artifacts.delete_temporary_upload(temporary)


@router.get("/simulation-models", response_model=SimulationModelList)
def list_simulation_models(
    repository: EvidenceRepositoryDependency,
) -> SimulationModelList:
    return SimulationModelList(simulation_models=repository.list_simulation_models())


@router.get("/simulation-models/{model_id}", response_model=SimulationModel)
def get_simulation_model(
    model_id: UUID,
    repository: EvidenceRepositoryDependency,
) -> SimulationModel:
    return repository.get_simulation_model(model_id)


@router.get("/simulation-adapters", response_model=SimulationAdapterListV1)
def list_simulation_adapters(
    artifacts: ArtifactStoreDependency,
) -> SimulationAdapterListV1:
    return SimulationAdapterListV1(
        adapters=[febio_preflight(febio_executable(), artifacts.root)]
    )
