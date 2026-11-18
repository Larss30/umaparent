import copy

from .config import load_profiles, load_ranks, load_styles, norm
from .models import KINDS, Parent, Spark
from .ranks import grade_for, next_grade

GENERIC_ID = "generic"
HIGHLIGHT_MIN = 0.5   # a white spark weighted at least this is flagged important
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


def apply_custom(profile: dict, custom: dict) -> dict:
    """Return a NEW profile where the user's own weights replace white-spark weights."""
    p = copy.deepcopy(profile)
    for name, w in custom.items():
        p["white"]["skills"][norm(name)] = float(w)
    return p


def important_sparks(parent: Parent, profiles: list[dict]) -> list[str]:
    found: dict[str, str] = {}
    for b in parent.blocks:
        for s in b.sparks:
            if s.kind == "white" and norm(s.name) not in found:
                if max(spark_weight(p, s) for p in profiles) >= HIGHLIGHT_MIN:
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
        q = apply_style(p, style) if style else p
        return apply_custom(q, parent.custom_weights) if parent.custom_weights else q

    overall_p = prepared(profiles[GENERIC_ID])
    event_ps = [prepared(p) for pid, p in profiles.items() if pid != GENERIC_ID]
    overall = score_parent(parent, overall_p, ranks)
    events = [score_parent(parent, p, ranks) for p in event_ps]
    out = {"overall": overall, "events": events,
           "important": important_sparks(parent, [overall_p, *event_ps])}
    if style:
        out["style"] = style_checklist(parent, style)
    return out
