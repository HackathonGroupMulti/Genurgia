from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.dependencies import JobRunnerDependency
from app.job_runner import JobConflict, JobNotFound
from app.schemas.jobs import JobCreateV1, JobListV1, JobV1

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobV1, status_code=status.HTTP_202_ACCEPTED)
def create_job(request: JobCreateV1, runner: JobRunnerDependency) -> JobV1:
    return runner.create(request)


@router.get("", response_model=JobListV1)
def list_jobs(runner: JobRunnerDependency) -> JobListV1:
    return JobListV1(jobs=runner.list())


@router.post("/worker/run-next", response_model=JobV1 | None)
def run_next_job(runner: JobRunnerDependency) -> JobV1 | None:
    return runner.run_next()


@router.get("/{job_id}", response_model=JobV1)
def get_job(job_id: UUID, runner: JobRunnerDependency) -> JobV1:
    try:
        return runner.get(job_id)
    except JobNotFound as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/{job_id}/cancel", response_model=JobV1)
def cancel_job(job_id: UUID, runner: JobRunnerDependency) -> JobV1:
    try:
        return runner.cancel(job_id)
    except JobNotFound as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except JobConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/{job_id}/retry", response_model=JobV1)
def retry_job(job_id: UUID, runner: JobRunnerDependency) -> JobV1:
    try:
        return runner.retry(job_id)
    except JobNotFound as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except JobConflict as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
