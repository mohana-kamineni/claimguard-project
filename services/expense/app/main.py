from datetime import date, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.claims import ClaimRejected, submit_claim
from app.config import Settings, get_settings
from app.database import engine, get_db, init_schema
from app.models import Claim
from app.policy_client import PolicyClient
from app.schemas import ClaimCreate, ClaimRead

APP_DIR = Path(__file__).resolve().parent
app = FastAPI(title="ClaimGuard Expense")
app.mount("/static", StaticFiles(directory=str(APP_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(APP_DIR / "templates"))


def get_policy_client(settings: Settings = Depends(get_settings)) -> PolicyClient:
    return PolicyClient(settings)


@app.on_event("startup")
def on_startup() -> None:
    # Synchronous def: init_schema() (create_all under the advisory lock)
    # returns before FastAPI starts serving requests.
    init_schema()


@app.get("/health")
def health() -> JSONResponse:
    """Own-process + database check. Never calls Policy. 503 if SELECT 1 fails."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(status_code=503, content={"status": "unavailable"})
    return JSONResponse(status_code=200, content={"status": "ok"})


@app.get("/api/claims", response_model=list[ClaimRead])
def list_claims(db: Session = Depends(get_db)) -> list[ClaimRead]:
    rows = db.scalars(select(Claim).order_by(Claim.created_at.desc())).all()
    return [_to_read(row) for row in rows]


@app.get("/api/claims/{claim_id}", response_model=ClaimRead)
def get_claim(claim_id: str, db: Session = Depends(get_db)) -> ClaimRead:
    row = db.get(Claim, claim_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Claim not found")
    return _to_read(row)


@app.post("/api/claims", response_model=ClaimRead, status_code=201)
def create_claim_api(
    payload: ClaimCreate,
    db: Session = Depends(get_db),
    policy: PolicyClient = Depends(get_policy_client),
) -> ClaimRead:
    try:
        claim = submit_claim(db, payload, policy)
    except ClaimRejected as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return _to_read(claim)


@app.get("/", response_class=HTMLResponse)
def ui_index(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    rows = db.scalars(select(Claim).order_by(Claim.created_at.desc())).all()
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "claims": rows,
            "error": request.query_params.get("error"),
            "today": date.today().isoformat(),
        },
    )


@app.post("/submit", response_class=RedirectResponse)
def ui_submit(
    db: Session = Depends(get_db),
    policy: PolicyClient = Depends(get_policy_client),
    employee_id: str = Form(...),
    amount: str = Form(...),
    category: str = Form(...),
    description: str = Form(""),
    claim_date: str = Form(...),
) -> RedirectResponse:
    try:
        payload = ClaimCreate(
            employee_id=employee_id,
            amount=amount,
            category=category,
            description=description,
            claim_date=claim_date,
        )
    except ValidationError:
        return RedirectResponse(url="/?error=invalid", status_code=303)
    try:
        submit_claim(db, payload, policy)
    except ClaimRejected:
        return RedirectResponse(url="/?error=policy", status_code=303)
    return RedirectResponse(url="/", status_code=303)


def _to_read(row: Claim) -> ClaimRead:
    created = row.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return ClaimRead(
        id=str(row.id),
        employee_id=row.employee_id,
        amount=row.amount,
        currency=row.currency,
        category=row.category,
        description=row.description,
        claim_date=row.claim_date,
        status=row.status,
        policy_reasons=list(row.policy_reasons),
        created_at=created.isoformat(),
    )
