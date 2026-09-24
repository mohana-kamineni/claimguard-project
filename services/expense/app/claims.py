from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Claim
from app.policy_client import PolicyClient, PolicyUnavailable
from app.schemas import ClaimCreate, PolicyDecision


class ClaimRejected(Exception):
    def __init__(self, message: str, status_code: int = 503) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def submit_claim(db: Session, payload: ClaimCreate, policy: PolicyClient) -> Claim:
    """Call Policy first; persist only after a successful (allow or deny) response."""
    try:
        decision: PolicyDecision = policy.evaluate(
            amount=str(payload.amount),
            category=payload.category,
            currency=payload.currency,
        )
    except PolicyUnavailable as exc:
        raise ClaimRejected(
            "Policy service is unavailable; the claim was not stored.",
            status_code=503,
        ) from exc

    claim = Claim(
        employee_id=payload.employee_id,
        amount=Decimal(payload.amount),
        currency=payload.currency,
        category=payload.category,
        description=payload.description,
        claim_date=payload.claim_date,
        status=decision.decision,
        policy_reasons=list(decision.reasons),
    )
    db.add(claim)
    db.commit()
    db.refresh(claim)
    return claim
