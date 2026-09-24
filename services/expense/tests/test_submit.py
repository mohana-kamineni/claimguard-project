from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.claims import ClaimRejected, submit_claim
from app.main import app
from app.policy_client import PolicyUnavailable
from app.schemas import ClaimCreate, PolicyDecision


def _payload(**overrides) -> ClaimCreate:
    data = {
        "employee_id": "e1",
        "amount": Decimal("10.00"),
        "category": "travel",
        "description": "train",
        "claim_date": date(2026, 9, 19),
    }
    data.update(overrides)
    return ClaimCreate(**data)


def test_invalid_amount_rejected_before_policy():
    with pytest.raises(Exception):
        ClaimCreate(
            employee_id="e1",
            amount=Decimal("0"),
            category="travel",
            claim_date=date(2026, 9, 19),
        )


def test_unknown_category_rejected_before_policy():
    with pytest.raises(Exception):
        ClaimCreate(
            employee_id="e1",
            amount=Decimal("10"),
            category="entertainment",
            claim_date=date(2026, 9, 19),
        )


def test_persist_after_policy_allow():
    db = MagicMock()
    policy = MagicMock()
    policy.evaluate.return_value = PolicyDecision(decision="allowed", reasons=[])
    claim = submit_claim(db, _payload(), policy)
    assert claim.status == "allowed"
    assert claim.policy_reasons == []
    db.add.assert_called_once()
    db.commit.assert_called_once()
    policy.evaluate.assert_called_once()


def test_persist_after_policy_deny_snapshot():
    db = MagicMock()
    policy = MagicMock()
    policy.evaluate.return_value = PolicyDecision(decision="denied", reasons=["GLOBAL_MAX"])
    claim = submit_claim(db, _payload(amount=Decimal("999")), policy)
    assert claim.status == "denied"
    assert claim.policy_reasons == ["GLOBAL_MAX"]
    db.commit.assert_called_once()


def test_no_persist_when_policy_unavailable():
    db = MagicMock()
    policy = MagicMock()
    policy.evaluate.side_effect = PolicyUnavailable("timeout")
    with pytest.raises(ClaimRejected) as exc:
        submit_claim(db, _payload(), policy)
    assert exc.value.status_code == 503
    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_api_rejects_invalid_payload_without_policy(monkeypatch):
    monkeypatch.setattr("app.main.init_schema", lambda: None)
    with TestClient(app) as client:
        response = client.post(
            "/api/claims",
            json={
                "employee_id": "e1",
                "amount": 0,
                "category": "travel",
                "claim_date": "2026-09-19",
            },
        )
    assert response.status_code == 422
