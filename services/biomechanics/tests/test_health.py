import asyncio

from httpx import ASGITransport, AsyncClient, Response

from app.main import app


def get(path: str) -> Response:
    async def request() -> Response:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            return await client.get(path)

    return asyncio.run(request())


def test_health_returns_service_status() -> None:
    response = get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "biomechanics"}


def test_health_contract_is_in_openapi_schema() -> None:
    response = get("/openapi.json")

    assert response.status_code == 200
    assert "/health" in response.json()["paths"]
