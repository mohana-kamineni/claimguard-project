from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator

ALLOWED_CATEGORIES = ("travel", "meals", "office", "other")
ALLOWED_CURRENCY = "EUR"


class ClaimCreate(BaseModel):
    employee_id: str = Field(min_length=1, max_length=64)
    amount: Decimal
    currency: Literal["EUR"] = "EUR"
    category: str
    description: str = ""
    claim_date: date

    @field_validator("employee_id")
    @classmethod
    def strip_employee_id(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("employee_id must not be empty")
        return stripped

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("amount must be greater than 0")
        return value.quantize(Decimal("0.01"))

    @field_validator("category")
    @classmethod
    def category_must_be_known(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in ALLOWED_CATEGORIES:
            raise ValueError(f"category must be one of: {', '.join(ALLOWED_CATEGORIES)}")
        return normalized


class ClaimRead(BaseModel):
    id: str
    employee_id: str
    amount: Decimal
    currency: str
    category: str
    description: str
    claim_date: date
    status: str
    policy_reasons: list[str]
    created_at: str

    model_config = {"from_attributes": True}


class PolicyDecision(BaseModel):
    decision: Literal["allowed", "denied"]
    reasons: list[str] = Field(default_factory=list)
