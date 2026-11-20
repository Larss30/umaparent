"""Match OCR text to the known spark names (skills.json plus the fixed stat and aptitude lists).

Comparison ignores case, spaces and punctuation, so "Crutzen !" still finds "Cruisin'!".
White sparks are always the base-level ○ skill: Tesseract cannot reliably tell ○ from ◎ at this size.
"""
import difflib
import re
from functools import lru_cache

from ..scoring.config import load_skills, norm

BLUES = ["Speed", "Stamina", "Power", "Guts", "Wit"]
PINKS = ["Turf", "Dirt", "Sprint", "Mile", "Medium", "Long", "Front Runner", "Pace Chaser",
         "Late Surger", "End Closer"]
_TAIL = re.compile(r"^(.*\S)\s+([○◎oO0°¢<>«»©®@])$")
_RACE_WORDS = re.compile(r"(Sho|Kinen|Cup|Stakes|Derby|Daishoten|Hai|Ch\.|C\.|F\.S\.|Oaks|Mile|Futurity)\b")


def clean(raw: str) -> str:
    return raw.replace("\u2019", "'").strip(" |_~`")


def alnum(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", norm(s))


def split_symbol(name: str) -> tuple[str, str]:
    m = _TAIL.match(clean(name))
    if not m:
        return clean(name), ""
    return m.group(1), "◎" if m.group(2) in "◎©®@" else "○"


@lru_cache
def _index() -> dict[str, dict[str, dict]]:
    """alnum base name -> {'○'/'◎'/'': skills.json entry}"""
    idx: dict[str, dict[str, dict]] = {}
    for e in load_skills():
        base, sym = split_symbol(e["name"])
        idx.setdefault(alnum(base), {}).setdefault(sym, e)
    return idx


def _ratio(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a, b).ratio()


def _closest(key: str, pool: list[str], cutoff: float) -> tuple[str | None, float, bool]:
    """Best match, its similarity, and whether it clearly beats the runner-up."""
    if key in pool:
        return key, 1.0, True
    hits = difflib.get_close_matches(key, pool, n=2, cutoff=cutoff)
    if not hits:
        return None, 0.0, False
    r1 = _ratio(key, hits[0])
    r2 = _ratio(key, hits[1]) if len(hits) > 1 else 0.0
    return hits[0], r1, r1 - r2 >= 0.06


def vocab_best(raw: str, vocab: list[str]) -> tuple[str, float]:
    """Closest stat or aptitude word. Junk after the word (OCR noise) is ignored."""
    key = alnum(raw)
    score, name = max((max(_ratio(key, alnum(v)), _ratio(key[:len(v)], alnum(v))), v) for v in vocab)
    return (name, score) if score >= 0.6 else (clean(raw), score)


def match_vocab(raw: str, vocab: list[str]) -> tuple[str, bool]:
    name, score = vocab_best(raw, vocab)
    return name, score >= 0.85


def match_skill(raw: str, types: set[str]) -> dict:
    """Match a white or green spark. Returns {name, category, sure, score}."""
    base, _ = split_symbol(raw)
    key = alnum(base)
    pool = {k: {s: e for s, e in v.items() if e["type"] in types} for k, v in _index().items()}
    pool = {k: v for k, v in pool.items() if v}
    cutoff = 0.74 if "unique" in types else 0.82       # unique names are long and distinctive
    hit, ratio, clear = _closest(key, list(pool), cutoff) if key else (None, 0.0, False)
    if hit is None:
        cat = "race" if _RACE_WORDS.search(base) else "scenario" if ":" in base else "skill"
        return {"name": clean(raw), "category": cat, "sure": False, "score": 0.0}
    variants = pool[hit]
    pick = variants.get("○") or variants.get("") or next(iter(variants.values()))
    return {"name": pick["name"], "category": pick["type"], "sure": ratio >= min(cutoff, 0.8) and clear, "score": ratio}


def match_spark(kind: str, raw: str) -> dict:
    if kind in ("blue", "pink"):
        name, score = vocab_best(raw, BLUES if kind == "blue" else PINKS)
        return {"kind": kind, "name": name, "sure": score >= 0.85, "score": score}
    if kind == "green":
        m = match_skill(raw, {"unique"})
        return {"kind": "green", "name": m["name"], "sure": m["sure"], "score": m["score"]}
    m = match_skill(raw, {"skill", "race", "scenario"})
    return {"kind": "white", "name": m["name"], "category": m["category"], "sure": m["sure"], "score": m["score"]}
