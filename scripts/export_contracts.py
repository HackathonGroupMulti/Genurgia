"""Export versioned JSON Schemas from the backend contract source of truth."""

import json
from pathlib import Path

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
from app.schemas.pose import PoseAnalysisResponse, PoseSequenceArtifact
from app.schemas.quality import CaptureQualityReport
from app.schemas.reconstruction import ReconstructionImportResultV1
from app.schemas.registration import (
    ArthroscopyOverlayResultV1,
    ArthroscopyRefinementGateV1,
    FunctionalRegistrationResultV1,
    TissueScoreAnnotationV1,
)
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

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_ROOT = REPOSITORY_ROOT / "packages" / "contracts"
CONTRACTS = {
    "pose-analysis-response-v3.schema.json": PoseAnalysisResponse,
    "pose-sequence-artifact-v2.schema.json": PoseSequenceArtifact,
    "knee-flexion-analysis-v1.schema.json": KneeFlexionAnalysis,
    "squat-repetition-analysis-v2.schema.json": SquatRepetitionAnalysis,
    "capture-quality-v1.schema.json": CaptureQualityReport,
    "session-list-v3.schema.json": SessionListResponse,
    "session-comparison-v1.schema.json": SessionComparisonResponse,
    "session-detail-v1.schema.json": SessionSummary,
    "selected-session-comparison-v2.schema.json": SelectedSessionComparison,
    "session-reanalysis-response-v1.schema.json": ReanalysisResponse,
    "session-export-manifest-v2.schema.json": SessionExportManifest,
    "processing-operation-list-v1.schema.json": ProcessingOperationList,
    "session-deletion-response-v1.schema.json": SessionDeletionResponse,
    "subject-list-v1.schema.json": SubjectList,
    "knee-list-v1.schema.json": KneeList,
    "episode-list-v1.schema.json": EpisodeList,
    "timepoint-list-v1.schema.json": TimepointList,
    "observation-list-v1.schema.json": ObservationList,
    "annotation-list-v1.schema.json": AnnotationList,
    "reconstruction-list-v1.schema.json": ReconstructionList,
    "registration-list-v1.schema.json": RegistrationList,
    "derivation-list-v1.schema.json": DerivationList,
    "virtual-experiment-list-v1.schema.json": VirtualExperimentList,
    "simulation-result-list-v1.schema.json": SimulationResultList,
    "dicom-series-manifest-v1.schema.json": DicomSeriesManifestV1,
    "arthroscopy-manifest-v1.schema.json": ArthroscopyManifestV1,
    "multi-view-capture-manifest-v1.schema.json": MultiViewCaptureManifestV1,
    "observation-import-result-v1.schema.json": ObservationImportResultV1,
    "reconstruction-import-result-v1.schema.json": ReconstructionImportResultV1,
    "functional-registration-result-v1.schema.json": FunctionalRegistrationResultV1,
    "arthroscopy-overlay-result-v1.schema.json": ArthroscopyOverlayResultV1,
    "arthroscopy-refinement-gate-v1.schema.json": ArthroscopyRefinementGateV1,
    "tissue-score-annotation-v1.schema.json": TissueScoreAnnotationV1,
}


def main() -> None:
    CONTRACT_ROOT.mkdir(parents=True, exist_ok=True)
    for filename, model in CONTRACTS.items():
        target = CONTRACT_ROOT / filename
        target.write_text(
            json.dumps(model.model_json_schema(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"Exported {target.relative_to(REPOSITORY_ROOT)}")


if __name__ == "__main__":
    main()
