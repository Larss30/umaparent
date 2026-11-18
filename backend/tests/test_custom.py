import copy

import pytest

from app.scoring.config import load_profiles
from app.scoring.engine import apply_custom, default_skill_weights, score_all, score_parent
from app.scoring.models import Parent, Spark, SparkBlock

PROFILE = load_profiles()["aries-cup"]


def parent(*sparks, **kw):
    return Parent("t", [SparkBlock("self", list(sparks))], **kw)


def white_of(p, profile):
    return score_parent(p, profile)["categories"]["white"]


def test_custom_weight_raises_an_unlisted_skill():
    p = parent(Spark("white", "Obscure Skill", 2, "skill"))
    assert white_of(p, apply_custom(PROFILE, {"obscure skill": 1.0})) > white_of(p, PROFILE)


def test_custom_weight_applies_to_race_and_scenario_sparks():
    p = parent(Spark("white", "Arima Kinen", 2, "race"), Spark("white", "Unity Cup", 2, "scenario"))
    assert white_of(p, apply_custom(PROFILE, {"Arima Kinen": 1.0, "Unity Cup": 1.0})) > white_of(p, PROFILE)


def test_zero_weight_ignores_a_skill_and_base_is_untouched():
    before = copy.deepcopy(PROFILE)
    p = parent(Spark("white", "Medium Corners \u25cb", 3, "skill"))
    assert white_of(p, apply_custom(PROFILE, {"Medium Corners \u25cb": 0.0})) == 0
    assert PROFILE == before


def test_important_flags_event_and_style_skills_only():
    p = parent(Spark("white", "Medium Corners \u25cb", 1, "skill"),
               Spark("white", "Nimble Navigator", 1, "skill"),
               Spark("white", "Obscure Skill", 1, "skill"), style="pace-chaser")
    imp = score_all(p)["important"]
    assert "Medium Corners \u25cb" in imp and "Nimble Navigator" in imp
    assert "Obscure Skill" not in imp


def test_custom_weights_flow_through_score_all():
    p = parent(Spark("white", "Obscure Skill", 1, "skill"), custom_weights={"Obscure Skill": 1.0})
    assert "Obscure Skill" in score_all(p)["important"]


def test_default_skill_weights_keep_display_names():
    rows = {r["name"]: r["weight"] for r in default_skill_weights("pace-chaser")}
    assert rows["Nimble Navigator"] == 1.0 and "Right-Handed \u25cb" in rows
    with pytest.raises(ValueError):
        default_skill_weights("nope")


def test_context_weights_only_change_that_event():
    base = parent(Spark("white", "Obscure Skill", 2, "skill"))
    tuned = parent(Spark("white", "Obscure Skill", 2, "skill"),
                   context_weights={"aries-cup": {"Obscure Skill": 1.0}})
    a, b = score_all(base), score_all(tuned)
    assert b["events"][0]["categories"]["white"] > a["events"][0]["categories"]["white"]
    assert b["overall"]["categories"]["white"] == a["overall"]["categories"]["white"]


def test_null_context_weight_removes_the_event_weight():
    p = parent(Spark("white", "Medium Corners \u25cb", 3, "skill"))
    q = parent(Spark("white", "Medium Corners \u25cb", 3, "skill"),
               context_weights={"aries-cup": {"Medium Corners \u25cb": None}})
    assert score_all(q)["events"][0]["categories"]["white"] < score_all(p)["events"][0]["categories"]["white"]


def test_custom_blue_pink_and_green_default():
    base = parent(Spark("blue", "Guts", 3), Spark("pink", "Dirt", 3), Spark("green", "Some Unique", 2))
    tuned = parent(*base.blocks[0].sparks, custom_blue={"Guts": 1.0}, custom_pink={"Dirt": 1.0},
                   custom_green_default=1.0)
    a, b = score_all(base)["events"][0]["categories"], score_all(tuned)["events"][0]["categories"]
    assert b["blue"] > a["blue"] and b["pink"] > a["pink"] and b["green"] > a["green"]
