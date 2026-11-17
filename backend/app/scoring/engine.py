import copy

from .config import load_profiles, load_ranks, load_styles, norm
from .models import KINDS, Parent, Spark
from .ranks import grade_for

GENERIC_ID = "generic"
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


def apply_style(profile: dict, style: dict) -> dict:
    """Return a NEW profile with a running style layered on top (input is not changed)."""
    p = copy.deepcopy(profile)
    p["id"] = f"{profile['id']}:{style['id']}"
    p["label"] = f"{profile['label']} \u00b7 {style['label']}"
    for k in STYLE_PINKS:
        p["pink"][k] = 0.0
    p["pink"][norm(style["aptitude"])] = 1.0
    for k, w in style["_weights"].items():
        p["white"]["skills"][k] = max(p["white"]["skills"].get(k, 0.0), w)
    if "white_target" in style:
        p["targets"]["white"] = style["white_target"]
    return p


def style_checklist(parent: Parent, style: dict) -> dict:
    found: dict[str, dict[str, int]] = {}
    for b in parent.blocks:
        for s in b.sparks:
            if s.kind == "white":
                d = found.setdefault(norm(s.name), {})
                d[b.role] = max(d.get(b.role, 0), s.stars)
    tiers, milestones = [], []
    cum_have = cum_of = 0
    for t in style["tiers"]:
        have, missing = [], []
        for name in t["skills"]:
            blocks = found.get(norm(name))
            if blocks:
                have.append({"name": name, "blocks": blocks})
            else:
                missing.append(name)
        tiers.append({"id": t["id"], "label": t["label"], "have": have, "missing": missing})
        if t.get("milestone"):
            cum_have += len(have)
            cum_of += len(t["skills"])
            milestones.append({"label": t["label"], "have": cum_have, "of": cum_of})
    return {"style": style["id"], "label": style["label"],
            "milestones": milestones, "tiers": tiers}


def score_parent(parent: Parent, profile: dict, ranks: dict | None = None) -> dict:
    ranks = ranks or load_ranks()
    raw = {k: 0.0 for k in KINDS}
    contributions = []
    for block in parent.blocks:
        block_w = profile["block_weights"][block.role]
        for s in block.sparks:
            points = block_w * spark_weight(profile, s) * s.stars
            raw[s.kind] += points
            if points > 0:
                contributions.append(
                    {"block": block.role, "kind": s.kind, "name": s.name,
                     "stars": s.stars, "points": round(points, 2)}
                )
    sub = {k: min(100.0, 100.0 * raw[k] / profile["targets"][k]) for k in KINDS}
    weights = profile["category_weights"]
    total = sum(weights[k] * sub[k] for k in KINDS) / sum(weights.values())
    contributions.sort(key=lambda c: -c["points"])
    return {
        "profile": profile["id"],
        "label": profile["label"],
        "score": round(total, 1),
        "grade": grade_for(total, ranks),
        "categories": {k: round(v, 1) for k, v in sub.items()},
        "top_contributors": contributions[:8],
    }


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
        return apply_style(p, style) if style else p

    overall = score_parent(parent, prepared(profiles[GENERIC_ID]), ranks)
    events = [score_parent(parent, prepared(p), ranks)
              for pid, p in profiles.items() if pid != GENERIC_ID]
    out = {"overall": overall, "events": events}
    if style:
        out["style"] = style_checklist(parent, style)
    return out
