from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator

ALLOWED_CATEGORIES = ("travel", "meals", "office", "other")


class EvaluateRequest(BaseModel):
    amount: Decimal
    category: str
    currency: str = "EUR"

    @field_validator("category")
    @classmethod
    def normalize_category(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.strip().upper()


class EvaluateResponse(BaseModel):
    decision: Literal["allowed", "denied"]
    reasons: list[str] = Field(default_factory=list)
    messages: list[str] = Field(default_factory=list)
