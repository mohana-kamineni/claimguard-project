import os
from decimal import Decimal


class Settings:
    """Thresholds from environment (Kubernetes ConfigMap). Not secrets."""

    def __init__(self) -> None:
        self.max_claim_eur = Decimal(os.environ.get("POLICY_MAX_CLAIM_EUR", "500"))
        self.max_meals_eur = Decimal(os.environ.get("POLICY_MAX_MEALS_EUR", "80"))
        self.max_other_eur = Decimal(os.environ.get("POLICY_MAX_OTHER_EUR", "25"))


def get_settings() -> Settings:
    return Settings()
