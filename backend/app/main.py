import os

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, text

from .schemas import ParentIn
from .scoring.config import load_profiles
from .scoring.engine import GENERIC_ID, score_all

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+psycopg://uma:uma@localhost:5432/umaparent"
)

app = FastAPI(title="UmaParent API (unofficial fan tool)")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/db")
def health_db():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"db": "ok"}
    except Exception:
        return JSONResponse(status_code=503, content={"db": "unreachable"})


@app.get("/api/profiles")
def profiles():
    return [
        {"id": p["id"], "label": p["label"], "status": p.get("status")}
        for pid, p in load_profiles().items()
        if pid != GENERIC_ID
    ]


@app.post("/api/score")
def score(parent: ParentIn):
    return score_all(parent.to_domain())
