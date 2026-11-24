import json
import os
from functools import lru_cache
from pathlib import Path

import yaml


def norm(name: str) -> str:
    """Normalise a spark/skill name for lookups: case, spacing, "!" and curly quotes."""
    name = name.replace("\u2019", "'").replace("!", "")
    return " ".join(name.casefold().split())


def data_dir() -> Path:
    default = Path(__file__).resolve().parents[3] / "data"
    return Path(os.getenv("DATA_DIR", default))


def _norm_keys(d: dict | None) -> dict:
    return {norm(k): v for k, v in (d or {}).items()}


@lru_cache
def load_tiers() -> dict[str, dict]:
    t = yaml.safe_load((data_dir() / "tiers.yaml").read_text(encoding="utf-8"))
    return {x["id"]: x for x in t["tiers"]}


@lru_cache
def load_skills() -> list[dict]:
    f = data_dir() / "skills.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else []


@lru_cache
def load_requires() -> dict[str, list]:
    """norm skill name -> list of alternative requirement blocks (any one block can trigger)."""
    return {norm(s["name"]): s["requires"] for s in load_skills() if s.get("requires")}


@lru_cache
def load_races() -> list[dict]:
    return yaml.safe_load((data_dir() / "races.yaml").read_text(encoding="utf-8"))["races"]


@lru_cache
def load_affinity() -> dict:
    return yaml.safe_load((data_dir() / "affinity.yaml").read_text(encoding="utf-8"))


def tier_weights(tiers: dict | None) -> tuple[dict, dict]:
    """{letter: [skill names]} -> ({norm name: weight}, {norm name: display name})."""
    table, weights, names = load_tiers(), {}, {}
    for letter, skills in (tiers or {}).items():
        for s in skills or []:
            weights[norm(s)] = table[letter]["weight"]
            names[norm(s)] = s
    return weights, names


@lru_cache
def load_profiles() -> dict[str, dict]:
    profiles = {}
    for f in sorted((data_dir() / "profiles").glob("*.yaml")):
        p = yaml.safe_load(f.read_text(encoding="utf-8"))
        p["base_id"] = p["id"]
        p["blue"] = {**_norm_keys(p.get("blue")), **tier_weights(p.get("blue_tiers"))[0]}
        p["pink"] = {**_norm_keys(p.get("pink")), **tier_weights(p.get("pink_tiers"))[0]}
        p["green"]["unique"] = _norm_keys(p["green"].get("unique"))
        explicit = p["white"].get("skills") or {}
        tw, tn = tier_weights(p.get("tiers"))
        p["white"]["_names"] = {**{norm(k): k for k in explicit}, **tn}
        p["white"]["skills"] = {**_norm_keys(explicit), **tw}
        p["white"]["races"] = _norm_keys(p["white"].get("races"))
        profiles[p["id"]] = p
    return profiles


@lru_cache
def load_styles() -> dict[str, dict]:
    styles = {}
    for f in sorted((data_dir() / "styles").glob("*.yaml")):
        if f.name.startswith("_"):
            continue
        s = yaml.safe_load(f.read_text(encoding="utf-8"))
        s["_weights"], s["_names"] = tier_weights(s["tiers"])
        styles[s["id"]] = s
    return styles


@lru_cache
def load_ranks() -> dict:
    ranks = yaml.safe_load((data_dir() / "ranks.yaml").read_text(encoding="utf-8"))
    ranks["grades"] = sorted(ranks["grades"], key=lambda g: g["min"])
    return ranks
