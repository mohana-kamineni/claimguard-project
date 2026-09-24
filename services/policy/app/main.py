import logging

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse

from app.config import Settings, get_settings
from app.rules import evaluate
from app.schemas import EvaluateRequest, EvaluateResponse

logger = logging.getLogger("claimguard.policy")

app = FastAPI(title="ClaimGuard Policy")


@app.get("/health")
def health() -> JSONResponse:
    """Process-only. Does not use a database and does not call Expense."""
    return JSONResponse(status_code=200, content={"status": "ok"})


@app.post("/api/evaluate", response_model=EvaluateResponse)
def evaluate_claim(
    payload: EvaluateRequest,
    settings: Settings = Depends(get_settings),
) -> EvaluateResponse:
    result = evaluate(payload.amount, payload.category, payload.currency, settings)
    # stdout so a local uvicorn run shows the live Expense→Policy JSON contract
    print(
        "POLICY_CONTRACT request="
        f"{payload.model_dump(mode='json')} response={result.model_dump()}",
        flush=True,
    )
    logger.info(
        "evaluate request=%s response=%s",
        payload.model_dump(mode="json"),
        result.model_dump(),
    )
    return result
