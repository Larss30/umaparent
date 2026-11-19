import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, text

from .schemas import ParentIn
from .scoring.config import load_profiles, load_skills, load_styles, load_tiers
from .scoring.engine import GENERIC_ID, checklists, default_skill_weights, score_all

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+psycopg://uma:uma@localhost:5432/umaparent"
)

app = FastAPI(title="UmaParent API (unofficial fan tool)")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

STATIC = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC / "index.html")


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


@app.get("/api/styles")
def styles():
    return [{"id": s["id"], "label": s["label"]} for s in load_styles().values()]


@app.get("/api/tiers")
def tiers():
    return list(load_tiers().values())


@app.get("/api/skills")
def skills():
    return load_skills()


@app.get("/api/checklists")
def get_checklists(style: str | None = None, auto_zero: bool = True):
    try:
        return checklists(style, auto_zero)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/skill-weights")
def skill_weights(style: str | None = None):
    try:
        return default_skill_weights(style)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/score")
def score(parent: ParentIn):
    try:
        return score_all(parent.to_domain())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
