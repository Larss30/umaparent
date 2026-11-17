import os
from functools import lru_cache
from pathlib import Path

import yaml


def norm(name: str) -> str:
    """Normalise a spark/skill name for lookups (case + whitespace only)."""
    return " ".join(name.casefold().split())


def data_dir() -> Path:
    default = Path(__file__).resolve().parents[3] / "data"
    return Path(os.getenv("DATA_DIR", default))


def _norm_keys(d: dict | None) -> dict:
    return {norm(k): v for k, v in (d or {}).items()}


@lru_cache
def load_profiles() -> dict[str, dict]:
    profiles = {}
    for f in sorted((data_dir() / "profiles").glob("*.yaml")):
        p = yaml.safe_load(f.read_text(encoding="utf-8"))
        p["blue"] = _norm_keys(p.get("blue"))
        p["pink"] = _norm_keys(p.get("pink"))
        p["green"]["unique"] = _norm_keys(p["green"].get("unique"))
        p["white"]["skills"] = _norm_keys(p["white"].get("skills"))
        p["white"]["races"] = _norm_keys(p["white"].get("races"))
        profiles[p["id"]] = p
    return profiles


@lru_cache
def load_ranks() -> dict:
    return yaml.safe_load((data_dir() / "ranks.yaml").read_text(encoding="utf-8"))
