import os
import threading
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pytesseract import TesseractNotFoundError
from sqlalchemy import create_engine, text

from .schemas import ParentIn
from .vision import ImageError, read_screenshots
from .scoring.config import load_affinity, load_profiles, load_races, load_skills, load_styles, load_tiers
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


@app.get("/api/races")
def races():
    return {"races": load_races(), "points_per_shared_g1": load_affinity()["points_per_shared_g1"]}


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


_READER = threading.BoundedSemaphore(2)      # at most two screenshot reads at once
MAX_SHOTS, MAX_SHOT_BYTES = 8, 8 * 1024 * 1024


@app.post("/api/read-screenshots")
def read_shots(files: list[UploadFile] = File(...)):
    """Read Inspiration-tab screenshots (in scroll order) into a parent. Nothing is stored."""
    if not 1 <= len(files) <= MAX_SHOTS:
        raise HTTPException(status_code=400, detail=f"Upload between 1 and {MAX_SHOTS} screenshots.")
    data = []
    for f in files:
        raw = f.file.read(MAX_SHOT_BYTES + 1)
        if len(raw) > MAX_SHOT_BYTES:
            raise HTTPException(status_code=413, detail=f"{f.filename} is over 8 MB.")
        data.append((f.filename or "screenshot", raw))
    if not _READER.acquire(blocking=False):
        raise HTTPException(status_code=429, detail="The reader is busy. Try again in a moment.")
    try:
        return read_screenshots(data)
    except ImageError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except TesseractNotFoundError:
        raise HTTPException(status_code=503, detail="The screenshot reader is not available on this server.")
    finally:
        _READER.release()
