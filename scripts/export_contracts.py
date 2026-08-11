"""Export versioned JSON Schemas from the backend contract source of truth."""

import json
from pathlib import Path

from app.schemas.kinematics import KneeFlexionAnalysis
from app.schemas.pose import PoseAnalysisResponse, PoseSequenceArtifact

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_ROOT = REPOSITORY_ROOT / "packages" / "contracts"
CONTRACTS = {
    "pose-analysis-response-v1.schema.json": PoseAnalysisResponse,
    "pose-sequence-artifact-v1.schema.json": PoseSequenceArtifact,
    "knee-flexion-analysis-v1.schema.json": KneeFlexionAnalysis,
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
