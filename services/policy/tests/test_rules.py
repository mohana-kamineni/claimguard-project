from decimal import Decimal

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app
from app.rules import evaluate


def test_allow_travel_under_global_max():
    result = evaluate(Decimal("100.00"), "travel", "EUR", Settings())
    assert result.decision == "allowed"
    assert result.reasons == []
    assert result.messages == []


def test_deny_global_max():
    result = evaluate(Decimal("500.01"), "travel", "EUR", Settings())
    assert result.decision == "denied"
    assert "GLOBAL_MAX" in result.reasons
    assert result.messages


def test_deny_meals_category_cap():
    result = evaluate(Decimal("80.01"), "meals", "EUR", Settings())
    assert result.decision == "denied"
    assert result.reasons == ["MEALS_MAX"]


def test_allow_meals_at_cap():
    result = evaluate(Decimal("80.00"), "meals", "EUR", Settings())
    assert result.decision == "allowed"


def test_deny_other_category_cap():
    result = evaluate(Decimal("25.01"), "other", "EUR", Settings())
    assert result.decision == "denied"
    assert result.reasons == ["OTHER_MAX"]


def test_allow_other_at_cap():
    result = evaluate(Decimal("25.00"), "other", "EUR", Settings())
    assert result.decision == "allowed"


def test_deny_unknown_category():
    result = evaluate(Decimal("10.00"), "entertainment", "EUR", Settings())
    assert result.decision == "denied"
    assert result.reasons == ["UNKNOWN_CATEGORY"]


def test_api_evaluate_allow_and_deny():
    with TestClient(app) as client:
        allowed = client.post(
            "/api/evaluate",
            json={"amount": "40.00", "category": "office", "currency": "EUR"},
        )
        denied = client.post(
            "/api/evaluate",
            json={"amount": "26.00", "category": "other", "currency": "EUR"},
        )
    assert allowed.status_code == 200
    assert allowed.json()["decision"] == "allowed"
    assert denied.status_code == 200
    assert denied.json()["decision"] == "denied"
    assert denied.json()["reasons"] == ["OTHER_MAX"]


def test_thresholds_come_from_environment(monkeypatch):
    monkeypatch.setenv("POLICY_MAX_CLAIM_EUR", "10")
    monkeypatch.setenv("POLICY_MAX_MEALS_EUR", "5")
    monkeypatch.setenv("POLICY_MAX_OTHER_EUR", "3")
    settings = Settings()
    assert evaluate(Decimal("10.00"), "travel", "EUR", settings).decision == "allowed"
    assert evaluate(Decimal("10.01"), "travel", "EUR", settings).decision == "denied"
    assert evaluate(Decimal("5.01"), "meals", "EUR", settings).reasons == ["MEALS_MAX"]
