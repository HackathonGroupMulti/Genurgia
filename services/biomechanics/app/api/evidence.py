from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import ValidationError

from app.dependencies import EvidenceRepositoryDependency
from app.schemas.evidence import (
    Annotation,
    AnnotationCreate,
    AnnotationList,
    Derivation,
    DerivationCreate,
    DerivationList,
    Episode,
    EpisodeCreate,
    EpisodeList,
    KneeList,
    Observation,
    ObservationCreate,
    ObservationList,
    Reconstruction,
    ReconstructionCreate,
    ReconstructionList,
    Registration,
    RegistrationCreate,
    RegistrationList,
    SimulationResult,
    SimulationResultCreate,
    SimulationResultList,
    Subject,
    SubjectCreate,
    SubjectList,
    Timepoint,
    TimepointCreate,
    TimepointList,
    VirtualExperiment,
    VirtualExperimentCreate,
    VirtualExperimentList,
)
from app.schemas.simulation import ExperimentDefinitionV2

router = APIRouter(tags=["canonical evidence"])


@router.post("/subjects", response_model=Subject, status_code=status.HTTP_201_CREATED)
def create_subject(request: SubjectCreate, repository: EvidenceRepositoryDependency) -> Subject:
    return repository.create_subject(request)


@router.get("/subjects", response_model=SubjectList)
def list_subjects(repository: EvidenceRepositoryDependency) -> SubjectList:
    return SubjectList(subjects=repository.list_subjects())


@router.get("/knees", response_model=KneeList)
def list_knees(
    repository: EvidenceRepositoryDependency,
    subject_id: Annotated[UUID | None, Query()] = None,
) -> KneeList:
    return KneeList(knees=repository.list_knees(subject_id))


@router.post("/episodes", response_model=Episode, status_code=status.HTTP_201_CREATED)
def create_episode(request: EpisodeCreate, repository: EvidenceRepositoryDependency) -> Episode:
    return repository.create_episode(request)


@router.get("/episodes", response_model=EpisodeList)
def list_episodes(
    repository: EvidenceRepositoryDependency,
    subject_id: Annotated[UUID | None, Query()] = None,
) -> EpisodeList:
    return EpisodeList(episodes=repository.list_episodes(subject_id))


@router.post("/timepoints", response_model=Timepoint, status_code=status.HTTP_201_CREATED)
def create_timepoint(
    request: TimepointCreate,
    repository: EvidenceRepositoryDependency,
) -> Timepoint:
    return repository.create_timepoint(request)


@router.get("/timepoints", response_model=TimepointList)
def list_timepoints(
    repository: EvidenceRepositoryDependency,
    subject_id: Annotated[UUID | None, Query()] = None,
) -> TimepointList:
    return TimepointList(timepoints=repository.list_timepoints(subject_id))


@router.post("/observations", response_model=Observation, status_code=status.HTTP_201_CREATED)
def create_observation(
    request: ObservationCreate,
    repository: EvidenceRepositoryDependency,
) -> Observation:
    return repository.create_observation(request)


@router.get("/observations", response_model=ObservationList)
def list_observations(
    repository: EvidenceRepositoryDependency,
    timepoint_id: Annotated[UUID | None, Query()] = None,
) -> ObservationList:
    return ObservationList(observations=repository.list_observations(timepoint_id))


@router.get("/observations/{observation_id}", response_model=Observation)
def get_observation(
    observation_id: UUID,
    repository: EvidenceRepositoryDependency,
) -> Observation:
    return repository.get_observation(observation_id)


@router.post("/annotations", response_model=Annotation, status_code=status.HTTP_201_CREATED)
def create_annotation(
    request: AnnotationCreate,
    repository: EvidenceRepositoryDependency,
) -> Annotation:
    return repository.create_annotation(request)


@router.get("/annotations", response_model=AnnotationList)
def list_annotations(
    repository: EvidenceRepositoryDependency,
    observation_id: Annotated[UUID | None, Query()] = None,
) -> AnnotationList:
    return AnnotationList(annotations=repository.list_annotations(observation_id))


@router.post(
    "/reconstructions",
    response_model=Reconstruction,
    status_code=status.HTTP_201_CREATED,
)
def create_reconstruction(
    request: ReconstructionCreate,
    repository: EvidenceRepositoryDependency,
) -> Reconstruction:
    return repository.create_reconstruction(request)


@router.get("/reconstructions", response_model=ReconstructionList)
def list_reconstructions(repository: EvidenceRepositoryDependency) -> ReconstructionList:
    return ReconstructionList(reconstructions=repository.list_reconstructions())


@router.post(
    "/registrations",
    response_model=Registration,
    status_code=status.HTTP_201_CREATED,
)
def create_registration(
    request: RegistrationCreate,
    repository: EvidenceRepositoryDependency,
) -> Registration:
    return repository.create_registration(request)


@router.get("/registrations", response_model=RegistrationList)
def list_registrations(repository: EvidenceRepositoryDependency) -> RegistrationList:
    return RegistrationList(registrations=repository.list_registrations())


@router.post("/derivations", response_model=Derivation, status_code=status.HTTP_201_CREATED)
def create_derivation(
    request: DerivationCreate,
    repository: EvidenceRepositoryDependency,
) -> Derivation:
    return repository.create_derivation(request)


@router.get("/derivations", response_model=DerivationList)
def list_derivations(repository: EvidenceRepositoryDependency) -> DerivationList:
    return DerivationList(derivations=repository.list_derivations())


@router.get("/derivations/{derivation_id}", response_model=Derivation)
def get_derivation(
    derivation_id: UUID,
    repository: EvidenceRepositoryDependency,
) -> Derivation:
    return repository.get_derivation(derivation_id)


@router.post(
    "/experiments",
    response_model=VirtualExperiment,
    status_code=status.HTTP_201_CREATED,
)
def create_experiment(
    request: VirtualExperimentCreate,
    repository: EvidenceRepositoryDependency,
) -> VirtualExperiment:
    if request.definition_version == "experiment-definition-v2":
        try:
            definition = ExperimentDefinitionV2.model_validate(request.definition)
        except ValidationError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=error.errors(include_url=False, include_context=False),
            ) from error
        simulation_model = repository.get_simulation_model(definition.simulation_model_id)
        reconstruction = repository.get_reconstruction(simulation_model.reconstruction_id)
        if reconstruction.knee_id != request.knee_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Experiment and simulation model refer to different knees.",
            )
        if reconstruction.timepoint_id != request.timepoint_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Experiment and simulation model refer to different timepoints.",
            )
        request = request.model_copy(
            update={"definition": definition.model_dump(mode="json")}
        )
    return repository.create_experiment(request)


@router.get("/experiments", response_model=VirtualExperimentList)
def list_experiments(repository: EvidenceRepositoryDependency) -> VirtualExperimentList:
    return VirtualExperimentList(experiments=repository.list_experiments())


@router.post(
    "/simulation-results",
    response_model=SimulationResult,
    status_code=status.HTTP_201_CREATED,
)
def create_simulation_result(
    request: SimulationResultCreate,
    repository: EvidenceRepositoryDependency,
) -> SimulationResult:
    return repository.create_simulation_result(request)


@router.get("/simulation-results", response_model=SimulationResultList)
def list_simulation_results(repository: EvidenceRepositoryDependency) -> SimulationResultList:
    return SimulationResultList(results=repository.list_simulation_results())
