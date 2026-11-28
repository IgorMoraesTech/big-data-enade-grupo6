"""Impede regressão em que a suíte passa, mas a API nem consegue importar."""
from fastapi.testclient import TestClient
from app.main import app


def test_import_api_and_health():
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_public_openapi():
    spec = TestClient(app).get("/openapi.json")
    assert spec.status_code == 200
    paths = spec.json()["paths"]
    assert "/api/questions" in paths
    assert "/api/cart/export.pdf" in paths
