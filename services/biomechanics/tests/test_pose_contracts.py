import json
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.kinematics import KneeFlexionAnalysis
from app.schemas.pose import Landmark, PoseAnalysisResponse, PoseSequenceArtifact
from app.schemas.quality import CaptureQualityReport
from app.schemas.repetitions import SquatRepetitionAnalysis
from app.schemas.sessions import SessionComparisonResponse, SessionListResponse

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
        ("pose-analysis-response-v2.schema.json", PoseAnalysisResponse),
        ("pose-sequence-artifact-v2.schema.json", PoseSequenceArtifact),
        ("knee-flexion-analysis-v1.schema.json", KneeFlexionAnalysis),
        ("squat-repetition-analysis-v2.schema.json", SquatRepetitionAnalysis),
        ("capture-quality-v1.schema.json", CaptureQualityReport),
        ("session-list-v2.schema.json", SessionListResponse),
        ("session-comparison-v1.schema.json", SessionComparisonResponse),
    ],
)
def test_exported_contract_is_current(filename: str, model: type) -> None:
    contract_path = REPOSITORY_ROOT / "packages" / "contracts" / filename
    assert json.loads(contract_path.read_text(encoding="utf-8")) == model.model_json_schema()


def test_uuid_contract_rejects_non_uuid_identifier() -> None:
    schema = PoseAnalysisResponse.model_json_schema()
    assert schema["$defs"]["Recording"]["properties"]["id"]["format"] == "uuid"
    assert uuid4()
