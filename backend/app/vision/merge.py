"""Combine several screenshots into one parent, removing duplicate sparks."""
import difflib

from ..scoring.config import norm
from .match import alnum
from .imaging import ImageError

ROLES = ["self", "grandparent_1", "grandparent_2"]


def _close(a: str, b: str) -> bool:
    x, y = alnum(a), alnum(b)
    return x == y or difflib.SequenceMatcher(None, x, y).ratio() >= 0.72


def _same_block(a: dict, b: dict) -> bool:
    pairs = [(a[k], b[k]) for k in ("blue", "pink", "green") if a[k] and b[k]]
    return len(pairs) >= 2 and all(_close(x["name"], y["name"]) for x, y in pairs)


def _find(whites: dict, w: dict) -> str | None:
    """Existing entry for the same spark. A misread copy of a name still counts as the same."""
    k = norm(w["name"])
    if k in whites:
        return k
    for k2, old in whites.items():
        if (w["check"] or old["check"]) and difflib.SequenceMatcher(None, alnum(w["name"]), alnum(old["name"])).ratio() >= 0.8:
            return k2
    return None


def _absorb(target: dict, block: dict) -> None:
    for k in ("blue", "pink", "green"):
        if block[k] and (not target[k] or (target[k]["check"] and not block[k]["check"])):
            target[k] = block[k]
    for w in block["whites"]:                              # a spark appears once per parent
        k = _find(target["whites"], w)
        old = target["whites"].get(k) if k else None
        if old is None:
            target["whites"][norm(w["name"])] = w
        elif (not w["check"], w["stars"]) > (not old["check"], old["stars"]):
            del target["whites"][k]
            target["whites"][norm(w["name"])] = w


def merge(results: list[dict]) -> dict:
    blocks: list[dict] = []
    cur, header, notes = None, {}, []
    for res in results:
        header = header or res.get("header") or {}
        for b in res["blocks"]:
            if b["anchored"]:
                cur = next((x for x in blocks if x["anchored"] and _same_block(x, b)), None)
                if cur is None:
                    cur = {"anchored": True, "blue": None, "pink": None, "green": None, "whites": {}}
                    blocks.append(cur)
            elif cur is None:
                cur = {"anchored": False, "blue": None, "pink": None, "green": None, "whites": {}}
                blocks.append(cur)
            _absorb(cur, b)
    if not blocks:
        raise ImageError("No spark rows found. Use the Inspiration tab of the Umamusume Details screen.")
    if not blocks[0]["anchored"]:
        notes.append("The first screenshot starts partway down the list, so the first block may be incomplete.")
    if len(blocks) > 3:
        notes.append(f"Found {len(blocks)} blocks; only the first 3 were kept. Upload in scroll order.")
    out = []
    for role, b in zip(ROLES, blocks):
        sparks = [s for s in (b["blue"], b["pink"], b["green"]) if s] + list(b["whites"].values())
        out.append({"role": role, "sparks": sparks})
    checks = sum(s["check"] for blk in out for s in blk["sparks"])
    if checks:
        notes.append(f"{checks} spark{'s' if checks != 1 else ''} marked with an amber outline should be checked.")
    parent = {"name": header.get("name", ""), "outfit": header.get("outfit"), "blocks": out}
    return {"parent": parent, "notes": notes}
