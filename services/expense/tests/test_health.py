from unittest.mock import MagicMock

import httpx
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app
from app.policy_client import PolicyClient, PolicyUnavailable


def test_health_ok_select_1_never_calls_policy(monkeypatch):
    monkeypatch.setattr("app.main.init_schema", lambda: None)
    connection = MagicMock()
    context = MagicMock()
    context.__enter__.return_value = connection
    context.__exit__.return_value = False
    monkeypatch.setattr("app.main.engine.connect", lambda: context)

    policy = MagicMock()
    monkeypatch.setattr("app.main.PolicyClient", MagicMock(return_value=policy))

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    policy.evaluate.assert_not_called()
    connection.execute.assert_called()


def test_health_503_when_database_fails(monkeypatch):
    monkeypatch.setattr("app.main.init_schema", lambda: None)

    def boom():
        raise OSError("connection refused")

    monkeypatch.setattr("app.main.engine.connect", boom)

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}


def test_policy_client_timeout_is_three_seconds(monkeypatch):
    captured = {}

    class DummyClient:
        def __init__(self, timeout=None):
            captured["timeout"] = timeout

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, *args, **kwargs):
            raise httpx.TimeoutException("simulated")

    monkeypatch.setattr("app.policy_client.httpx.Client", DummyClient)
    settings = Settings()
    assert settings.policy_http_timeout_seconds == 3.0
    client = PolicyClient(settings)
    try:
        client.evaluate("10.00", "meals", "EUR")
        raise AssertionError("expected PolicyUnavailable")
    except PolicyUnavailable:
        pass
    assert captured["timeout"] == httpx.Timeout(3.0)
