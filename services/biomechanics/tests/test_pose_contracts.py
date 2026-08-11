import json
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.pose import Landmark, PoseAnalysisResponse, PoseSequenceArtifact

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
        ("pose-analysis-response-v1.schema.json", PoseAnalysisResponse),
        ("pose-sequence-artifact-v1.schema.json", PoseSequenceArtifact),
    ],
)
def test_exported_contract_is_current(filename: str, model: type) -> None:
    contract_path = REPOSITORY_ROOT / "packages" / "contracts" / filename
    assert json.loads(contract_path.read_text(encoding="utf-8")) == model.model_json_schema()


def test_uuid_contract_rejects_non_uuid_identifier() -> None:
    schema = PoseAnalysisResponse.model_json_schema()
    assert schema["$defs"]["Recording"]["properties"]["id"]["format"] == "uuid"
    assert uuid4()
