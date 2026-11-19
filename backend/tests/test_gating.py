from app.scoring.config import load_profiles, load_skills, load_styles
from app.scoring.engine import apply_style, blocked_reason, checklists, score_all, score_parent
from app.scoring.models import Parent, Spark, SparkBlock

ARIES = load_profiles()["aries-cup"]
GENERIC = load_profiles()["generic"]
KEYS = {"style": {"front-runner", "pace-chaser", "late-surger", "end-closer"},
        "distance": {"sprint", "mile", "medium", "long"}, "surface": {"dirt", "turf"},
        "direction": {"left", "right"}, "season": {"spring", "summer", "fall", "winter"},
        "weather": {"sunny", "cloudy", "rainy", "snowy"}, "ground": {"firm", "wet"}, "course": None}


def skill_named(prefix):
    return next(s["name"] for s in load_skills() if s["name"].startswith(prefix))


def parent(*names, **kw):
    sparks = [Spark("white", n, 2, "skill") for n in names]
    return Parent("t", [SparkBlock("self", sparks)], **kw)


def white(p, profile):
    return score_parent(p, profile)["categories"]["white"]


def test_requirements_use_known_keys_and_values():
    for s in load_skills():
        for blk in s.get("requires", []):
            for k, vals in blk.items():
                assert k in KEYS and (KEYS[k] is None or set(vals) <= KEYS[k]), (s["name"], blk)


def test_other_distances_are_zero_for_a_medium_race():
    for prefix in ("Sprint Corners", "Mile Straightaways", "Long Corners"):
        assert white(parent(skill_named(prefix)), ARIES) == 0
    assert white(parent("Medium Corners \u25cb"), ARIES) > 0


def test_style_skills_are_zero_for_other_styles_only_when_a_style_is_chosen():
    name = skill_named("Front Runner Savvy")
    pace = apply_style(ARIES, load_styles()["pace-chaser"])
    front = apply_style(ARIES, load_styles()["front-runner"])
    assert white(parent(name), pace) == 0
    assert white(parent(name), front) > 0
    assert white(parent(name), ARIES) > 0          # no style chosen: unknown, not zeroed


def test_dirt_only_skills_are_zero_on_a_turf_event():
    name = next(s["name"] for s in load_skills()
                if any(b.get("surface") == ["dirt"] for b in s.get("requires", [])))
    assert white(parent(name), ARIES) == 0


def test_unknown_conditions_never_block():
    assert blocked_reason(GENERIC, skill_named("Long Corners")) is None


def test_gate_beats_user_weights_until_auto_zero_is_off():
    name = skill_named("Left-Handed")
    tuned = {"aries-cup": {name: 1.0}}
    assert score_all(parent(name, context_weights=tuned))["events"][0]["categories"]["white"] == 0
    off = score_all(parent(name, context_weights=tuned, auto_zero=False))
    assert off["events"][0]["categories"]["white"] > 0


def test_blocked_skills_are_reported_with_a_reason():
    name = skill_named("Long Corners")
    out = score_all(parent(name))
    b = out["events"][0]["blocked"][0]
    assert b["name"] == name and "race" in b["reason"]
    assert out["overall"]["blocked"] == []


def test_checklist_moves_blocked_skills_to_the_zero_tier():
    cl = checklists(None)["aries-cup"]
    assert any(b["name"] == "Left-Handed \u25cb" for b in cl["blocked"])
    assert "Left-Handed \u25cb" in cl["tiers"]["Z"]
    assert checklists(None, auto_zero=False)["aries-cup"]["blocked"] == []
