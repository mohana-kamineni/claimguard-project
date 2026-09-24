import httpx
from pydantic import ValidationError

from app.config import Settings
from app.schemas import PolicyDecision


class PolicyUnavailable(Exception):
    """Policy did not return a successful evaluation. Expense must not persist."""


class PolicyClient:
    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.policy_base_url
        self._timeout = httpx.Timeout(settings.policy_http_timeout_seconds)

    def evaluate(self, amount: str, category: str, currency: str) -> PolicyDecision:
        url = f"{self._base_url}/api/evaluate"
        payload = {"amount": amount, "category": category, "currency": currency}
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                return PolicyDecision.model_validate(response.json())
        except (httpx.TimeoutException, httpx.HTTPError, ValidationError, ValueError) as exc:
            raise PolicyUnavailable(str(exc)) from exc
