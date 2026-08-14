import asyncio
from pathlib import Path

from httpx import ASGITransport, AsyncClient

from app.main import create_app
from app.storage import LocalArtifactStore
from tests.simulation_fixtures import (
    finite_element_manifest,
    flexion_experiment,
    simulation_context,
    write_fe_package,
)


def test_simulation_model_import_list_get_and_missing_febio_preflight(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.delenv("FEBIO_EXECUTABLE", raising=False)
    store = LocalArtifactStore(tmp_path / "artifacts")
    app = create_app(pose_analysis_service=None, artifact_store=store)
    knee, timepoint, reconstruction = simulation_context(app.state.evidence_repository)
    package = write_fe_package(
        tmp_path / "synthetic-fe.zip",
        finite_element_manifest(str(reconstruction.id)),
    )

    async def exercise() -> None:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            with package.open("rb") as source:
                response = await client.post(
                    "/simulation-models/imports/febio",
                    files={"package": (package.name, source, "application/zip")},
                )
            assert response.status_code == 202, response.text
            queued = response.json()
            assert queued["job_type"] == "febio-model-import-v1"
            completed = await client.post("/jobs/worker/run-next")
            assert completed.status_code == 200, completed.text
            completed_job = completed.json()
            assert completed_job["status"] == "succeeded"
            result = await client.get(completed_job["result_artifact_reference"])
            assert result.status_code == 200, result.text
            model = result.json()["simulation_model"]
            listed = await client.get("/simulation-models")
            assert listed.json()["simulation_models"][0]["id"] == model["id"]
            fetched = await client.get(f"/simulation-models/{model['id']}")
            assert fetched.json() == model
            definition = flexion_experiment(model["id"], model["model_sha256"])
            invalid_definition = {**definition, "boundary": {"rotation_axis": "x"}}
            invalid = await client.post(
                "/experiments",
                json={
                    "knee_id": str(knee.id),
                    "timepoint_id": str(timepoint.id),
                    "definition_version": "experiment-definition-v2",
                    "definition": invalid_definition,
                    "validation_tier": "synthetic",
                },
            )
            assert invalid.status_code == 422
            created = await client.post(
                "/experiments",
                json={
                    "knee_id": str(knee.id),
                    "timepoint_id": str(timepoint.id),
                    "definition_version": "experiment-definition-v2",
                    "definition": definition,
                    "validation_tier": "synthetic",
                },
            )
            assert created.status_code == 201, created.text
            adapters = (await client.get("/simulation-adapters")).json()["adapters"]
            assert adapters[0]["available"] is False
            assert "FEBio was not found" in adapters[0]["unavailable_reasons"][0]

    asyncio.run(exercise())
