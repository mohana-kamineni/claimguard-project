from decimal import Decimal

from app.config import Settings
from app.schemas import ALLOWED_CATEGORIES, EvaluateResponse


def evaluate(amount: Decimal, category: str, currency: str, settings: Settings) -> EvaluateResponse:
    """Deterministic allow/deny. Stateless. Collects every matching reason."""
    reasons: list[str] = []
    messages: list[str] = []

    if currency != "EUR":
        reasons.append("CURRENCY")
        messages.append("Only EUR claims are supported.")

    if category not in ALLOWED_CATEGORIES:
        reasons.append("UNKNOWN_CATEGORY")
        messages.append("Category must be travel, meals, office, or other.")

    if amount > settings.max_claim_eur:
        reasons.append("GLOBAL_MAX")
        messages.append(f"Amount exceeds the global maximum of {settings.max_claim_eur} EUR.")

    if category == "meals" and amount > settings.max_meals_eur:
        reasons.append("MEALS_MAX")
        messages.append(f"Meals exceed the category maximum of {settings.max_meals_eur} EUR.")

    if category == "other" and amount > settings.max_other_eur:
        reasons.append("OTHER_MAX")
        messages.append(f"Category other exceeds the maximum of {settings.max_other_eur} EUR.")

    if reasons:
        return EvaluateResponse(decision="denied", reasons=reasons, messages=messages)
    return EvaluateResponse(decision="allowed", reasons=[], messages=[])
