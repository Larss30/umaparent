import copy

from .config import load_profiles, load_ranks, load_requires, load_styles, load_tiers, norm
from .models import KINDS, Parent, Spark
from .ranks import grade_for, next_grade

GENERIC_ID = "generic"
HIGHLIGHT_MIN = 0.5   # a white spark weighted at least this is flagged important
_NEED = {
    "style": lambda a: "needs the " + " or ".join(x.replace("-", " ") for x in a) + " style",
    "distance": lambda a: "needs a " + " or ".join(a) + " race",
    "surface": lambda a: "needs " + " or ".join(a),
    "direction": lambda a: "needs " + " or ".join(a) + "-handed tracks",
    "course": lambda a: "needs the " + " or ".join(a) + " racecourse",
    "season": lambda a: "needs " + " or ".join(a),
    "weather": lambda a: "needs " + " or ".join(a) + " weather",
    "ground": lambda a: "needs " + " or ".join(a) + " ground",
}
STYLE_PINKS = ("front runner", "pace chaser", "late surger", "end closer")


def spark_weight(profile: dict, spark: Spark) -> float:
    n = norm(spark.name)
    if spark.kind == "blue":
        return profile["blue"].get(n, 0.0)
    if spark.kind == "pink":
        return profile["pink"].get(n, 0.0)
    if spark.kind == "green":
        g = profile["green"]
        return g["unique"].get(n, g["default"])
    w = profile["white"]
    explicit = w["skills"].get(n)       # named skills win for every white category
    if explicit is not None:
        return explicit
    category = spark.category or "skill"
    if category == "race":
        return w["races"].get(n, w["race_default"])
    if category == "scenario":
        return w["scenario_default"]
    return w["skill_default"]


def context_of(profile: dict) -> dict:
    """What we know about the race and style. Unknown values (None) never block a skill."""
    race = profile.get("race") or {}
    ground = race.get("ground")
    return {
        "style": profile.get("active_style"),
        "distance": race.get("category"),
        "surface": race.get("surface"),
        "direction": race.get("direction"),
        "course": (race.get("course") or "").lower() or None,
        "season": race.get("season"),
        "weather": race.get("weather"),
        "ground": None if not ground else ("firm" if ground == "firm" else "wet"),
    }


def blocked_reason(profile: dict, name: str) -> str | None:
    """Why this skill cannot trigger here, or None. Any one requirement block that fits is enough."""
    blocks = load_requires().get(norm(name))
    if not blocks:
        return None
    ctx, reasons = context_of(profile), []
    for blk in blocks:
        miss = [(k, a) for k, a in blk.items() if ctx.get(k) is not None and ctx[k] not in a]
        if not miss:
            return None
        reasons.append(" and ".join(_NEED[k](a) for k, a in miss))
    return "; or ".join(dict.fromkeys(reasons))


def effective_weight(profile: dict, spark: Spark, auto_zero: bool = True) -> tuple[float, str | None]:
    why = blocked_reason(profile, spark.name) if auto_zero and spark.kind != "blue" else None
    return (0.0, why) if why else (spark_weight(profile, spark), None)


def apply_style(profile: dict, style: dict) -> dict:
    """Return a NEW profile with a running style layered on top (input is not changed)."""
    p = copy.deepcopy(profile)
    p["id"] = f"{profile['id']}:{style['id']}"
    p["active_style"] = style["id"]
    p["label"] = f"{profile['label']} \u00b7 {style['label']}"
    for k in STYLE_PINKS:
        p["pink"][k] = 0.0
    p["pink"][norm(style["aptitude"])] = 1.0
    for k, w in style["_weights"].items():
        p["white"]["skills"].setdefault(k, w)      # the event's own tier wins over the style's
    if "white_target" in style:
        p["targets"]["white"] = style["white_target"]
    return p


def apply_custom(profile: dict, custom: dict) -> dict:
    """Return a NEW profile with the user's own skill weights (None removes a weight)."""
    p = copy.deepcopy(profile)
    for name, w in custom.items():
        k = norm(name)
        if w is None:
            p["white"]["skills"].pop(k, None)
            p["green"]["unique"].pop(k, None)
        else:
            p["white"]["skills"][k] = float(w)
            p["green"]["unique"][k] = float(w)
    return p


def apply_overrides(profile: dict, parent: Parent) -> dict:
    p = profile
    if parent.custom_blue or parent.custom_pink or parent.custom_green_default is not None:
        p = copy.deepcopy(p)
        for k, w in (parent.custom_blue or {}).items():
            p["blue"][norm(k)] = float(w)
        for k, w in (parent.custom_pink or {}).items():
            p["pink"][norm(k)] = float(w)
        if parent.custom_green_default is not None:
            p["green"]["default"] = float(parent.custom_green_default)
    if parent.custom_weights:
        p = apply_custom(p, parent.custom_weights)
    ctx = (parent.context_weights or {}).get(profile["base_id"])
    return apply_custom(p, ctx) if ctx else p


def checklists(style_id: str | None = None, auto_zero: bool = True) -> dict:
    """Per-context tiered checklists: style skills + that event's own skills (event wins)."""
    style = None
    if style_id:
        style = load_styles().get(style_id)
        if style is None:
            raise ValueError(f"Unknown running style: {style_id}")
    order = list(load_tiers())
    profiles = load_profiles()
    out = {}
    for pid in [GENERIC_ID] + [i for i in profiles if i != GENERIC_ID]:
        p = profiles[pid]
        entries: dict[str, tuple[str, str]] = {}
        for source in ([style["tiers"]] if style else []) + [p.get("tiers") or {}]:
            for letter, skills in source.items():
                for s in skills or []:
                    entries[norm(s)] = (letter, s)
        grouped: dict[str, list[str]] = {t: [] for t in order}
        blocked, pc = [], {**p, "active_style": style_id}
        for letter, name in entries.values():
            why = blocked_reason(pc, name) if auto_zero else None
            if why:
                blocked.append({"name": name, "reason": why})
            grouped["Z" if why else letter].append(name)
        out[pid] = {"label": p["label"], "tiers": grouped, "blocked": blocked}
    return out


def important_sparks(parent: Parent, profiles: list[dict]) -> list[str]:
    found: dict[str, str] = {}
    for b in parent.blocks:
        for s in b.sparks:
            if s.kind == "white" and norm(s.name) not in found:
                if max(effective_weight(p, s, parent.auto_zero)[0] for p in profiles) >= HIGHLIGHT_MIN:
                    found[norm(s.name)] = s.name
    return sorted(found.values())


def default_skill_weights(style_id: str | None = None) -> list[dict]:
    """Default white-skill weights (best across events), for seeding the tier list."""
    style = None
    if style_id:
        style = load_styles().get(style_id)
        if style is None:
            raise ValueError(f"Unknown running style: {style_id}")
    best: dict[str, float] = {}
    names: dict[str, str] = {}
    for p in load_profiles().values():
        q = apply_style(p, style) if style else p
        names.update(p["white"].get("_names", {}))
        for k, w in q["white"]["skills"].items():
            best[k] = max(best.get(k, 0.0), w)
    if style:
        names.update(style["_names"])
    rows = [{"name": names.get(k, k), "weight": w} for k, w in best.items() if w > 0]
    return sorted(rows, key=lambda r: (-r["weight"], r["name"]))


def score_parent(parent: Parent, profile: dict, ranks: dict | None = None) -> dict:
    ranks = ranks or load_ranks()
    raw = {k: 0.0 for k in KINDS}
    contributions, blocked = [], {}
    for block in parent.blocks:
        block_w = profile["block_weights"][block.role]
        for s in block.sparks:
            weight, why = effective_weight(profile, s, parent.auto_zero)
            if why:
                blocked.setdefault(norm(s.name), {"name": s.name, "block": block.role, "reason": why})
            points = block_w * weight * s.stars
            raw[s.kind] += points
            if points > 0:
                contributions.append(
                    {"block": block.role, "kind": s.kind, "name": s.name,
                     "stars": s.stars, "points": round(points, 2)}
                )
    sub = {k: 100.0 * raw[k] / profile["targets"][k] for k in KINDS}   # uncapped
    cw = profile["category_weights"]
    weights = {k: cw[k] for k in KINDS}
    if parent.affinity is not None and "affinity" in cw:
        sub["affinity"] = 100.0 * parent.affinity / profile["targets"]["affinity"]
        weights["affinity"] = cw["affinity"]
    total = sum(weights[k] * sub[k] for k in sub) / sum(weights.values())
    contributions.sort(key=lambda c: -c["points"])
    result = {
        "profile": profile["id"],
        "label": profile["label"],
        "score": round(total, 1),
        "grade": grade_for(total, ranks),
        "next_grade": next_grade(total, ranks),
        "categories": {k: round(v, 1) for k, v in sub.items()},
        "top_contributors": contributions[:8],
        "blocked": list(blocked.values()),
    }
    if "affinity" in sub:
        result["affinity"] = {"value": parent.affinity, "target": parent.affinity_target,
                              "source": "manual"}
    return result


def score_all(parent: Parent, style_id: str | None = None) -> dict:
    profiles = load_profiles()
    ranks = load_ranks()
    style_id = style_id or parent.style
    style = None
    if style_id:
        style = load_styles().get(style_id)
        if style is None:
            raise ValueError(f"Unknown running style: {style_id}")

    def prepared(p: dict) -> dict:
        return apply_overrides(apply_style(p, style) if style else p, parent)

    overall_p = prepared(profiles[GENERIC_ID])
    event_ps = [prepared(p) for pid, p in profiles.items() if pid != GENERIC_ID]
    overall = score_parent(parent, overall_p, ranks)
    events = [score_parent(parent, p, ranks) for p in event_ps]
    out = {"overall": overall, "events": events,
           "important": important_sparks(parent, [overall_p, *event_ps])}
    return out
