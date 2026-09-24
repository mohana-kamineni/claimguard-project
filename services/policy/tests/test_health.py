from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app


def test_health_is_process_only():
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_does_not_call_expense_or_database():
    with (
        patch("httpx.Client", MagicMock()) as http_client,
        TestClient(app) as client,
    ):
        response = client.get("/health")
    assert response.status_code == 200
    http_client.assert_not_called()
