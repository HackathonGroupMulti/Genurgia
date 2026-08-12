import json
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.evidence import (
    AnnotationList,
    DerivationList,
    EpisodeList,
    KneeList,
    ObservationList,
    ReconstructionList,
    RegistrationList,
    SimulationResultList,
    SubjectList,
    TimepointList,
    VirtualExperimentList,
)
from app.schemas.imports import (
    ArthroscopyManifestV1,
    DicomSeriesManifestV1,
    MultiViewCaptureManifestV1,
    ObservationImportResultV1,
)
from app.schemas.kinematics import KneeFlexionAnalysis
from app.schemas.operations import ProcessingOperationList
from app.schemas.pose import Landmark, PoseAnalysisResponse, PoseSequenceArtifact
from app.schemas.quality import CaptureQualityReport
from app.schemas.reconstruction import ReconstructionImportResultV1
from app.schemas.repetitions import SquatRepetitionAnalysis
from app.schemas.sessions import (
    ReanalysisResponse,
    SelectedSessionComparison,
    SessionComparisonResponse,
    SessionDeletionResponse,
    SessionExportManifest,
    SessionListResponse,
    SessionSummary,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def test_landmark_confidence_must_be_in_unit_interval() -> None:
    with pytest.raises(ValidationError):
        Landmark(
            index=0,
            name="nose",
            x=0.5,
            y=0.5,
            z=0.0,
            visibility=1.1,
            presence=0.5,
        )


@pytest.mark.parametrize(
    ("filename", "model"),
    [
        ("pose-analysis-response-v3.schema.json", PoseAnalysisResponse),
        ("pose-sequence-artifact-v2.schema.json", PoseSequenceArtifact),
        ("knee-flexion-analysis-v1.schema.json", KneeFlexionAnalysis),
        ("squat-repetition-analysis-v2.schema.json", SquatRepetitionAnalysis),
        ("capture-quality-v1.schema.json", CaptureQualityReport),
        ("session-list-v3.schema.json", SessionListResponse),
        ("session-comparison-v1.schema.json", SessionComparisonResponse),
        ("session-detail-v1.schema.json", SessionSummary),
        ("selected-session-comparison-v2.schema.json", SelectedSessionComparison),
        ("session-reanalysis-response-v1.schema.json", ReanalysisResponse),
        ("session-export-manifest-v2.schema.json", SessionExportManifest),
        ("processing-operation-list-v1.schema.json", ProcessingOperationList),
        ("session-deletion-response-v1.schema.json", SessionDeletionResponse),
        ("subject-list-v1.schema.json", SubjectList),
        ("knee-list-v1.schema.json", KneeList),
        ("episode-list-v1.schema.json", EpisodeList),
        ("timepoint-list-v1.schema.json", TimepointList),
        ("observation-list-v1.schema.json", ObservationList),
        ("annotation-list-v1.schema.json", AnnotationList),
        ("reconstruction-list-v1.schema.json", ReconstructionList),
        ("registration-list-v1.schema.json", RegistrationList),
        ("derivation-list-v1.schema.json", DerivationList),
        ("virtual-experiment-list-v1.schema.json", VirtualExperimentList),
        ("simulation-result-list-v1.schema.json", SimulationResultList),
        ("dicom-series-manifest-v1.schema.json", DicomSeriesManifestV1),
        ("arthroscopy-manifest-v1.schema.json", ArthroscopyManifestV1),
        ("multi-view-capture-manifest-v1.schema.json", MultiViewCaptureManifestV1),
        ("observation-import-result-v1.schema.json", ObservationImportResultV1),
        ("reconstruction-import-result-v1.schema.json", ReconstructionImportResultV1),
    ],
)
def test_exported_contract_is_current(filename: str, model: type) -> None:
    contract_path = REPOSITORY_ROOT / "packages" / "contracts" / filename
    assert json.loads(contract_path.read_text(encoding="utf-8")) == model.model_json_schema()


def test_uuid_contract_rejects_non_uuid_identifier() -> None:
    schema = PoseAnalysisResponse.model_json_schema()
    assert schema["$defs"]["Recording"]["properties"]["id"]["format"] == "uuid"
    assert uuid4()
