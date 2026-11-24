import copy

import pytest

from app.scoring.config import load_profiles, load_styles, norm
from app.scoring.engine import apply_style, blocked_reason, checklists, score_all, score_parent
from app.scoring.models import Parent, Spark, SparkBlock

PROFILE = load_profiles()["aries-cup"]
PACE = load_styles()["pace-chaser"]
STYLED = apply_style(PROFILE, PACE)


def parent(*sparks, role="self", style=None):
    return Parent("t", [SparkBlock(role, list(sparks))], style=style)


def white(name, stars=2, category="skill"):
    return Spark("white", name, stars, category)


def white_score(name, **kw):
    return score_parent(parent(white(name, **kw)), STYLED)["categories"]["white"]


def test_tiers_are_ordered_by_weight():
    names = ["Nimble Navigator", "Tail Held High", "Risky Business", "Groundwork", "On the Attack"]
    scores = [white_score(n) for n in names]
    assert scores == sorted(scores, reverse=True)
    assert len(set(scores)) == len(scores)


def test_style_skill_beats_unlisted_skill():
    assert white_score("Nimble Navigator") > white_score("Some Unlisted Skill")


def test_scenario_spark_named_in_style_counts():
    assert white_score("Racing Spirit: Stamina", category="scenario") > \
        white_score("Unity Cup", category="scenario")


def test_name_matching_ignores_exclamation_and_curly_apostrophe():
    a = white_score("Playtime's Over!")
    assert white_score("Playtime's Over") == a
    assert white_score("Playtime\u2019s Over!") == a


def test_only_chosen_style_pink_counts():
    pace = parent(Spark("pink", "Pace Chaser", 3))
    front = parent(Spark("pink", "Front Runner", 3))
    assert score_parent(pace, STYLED)["categories"]["pink"] > 0
    assert score_parent(front, STYLED)["categories"]["pink"] == 0


def test_apply_style_does_not_mutate_base_profile():
    before = copy.deepcopy(PROFILE)
    apply_style(PROFILE, PACE)
    assert PROFILE == before


def test_event_checklist_adds_event_skills_to_style_skills():
    cl = checklists("pace-chaser")
    assert "Medium Corners \u25cb" in cl["aries-cup"]["tiers"]["S"]
    assert "Medium Corners \u25cb" not in cl["generic"]["tiers"]["S"]
    assert "Right-Handed \u25cb" in cl["aries-cup"]["tiers"]["A"]
    assert "Nimble Navigator" in cl["generic"]["tiers"]["S"]
    assert "Nimble Navigator" in cl["aries-cup"]["tiers"]["S"]
    assert "Left-Handed \u25cb" in cl["aries-cup"]["tiers"]["Z"]


def test_each_style_has_its_own_global_skills():
    assert "Groundwork" in checklists("front-runner")["generic"]["tiers"]["S"]
    assert "Uma Stan" in checklists("late-surger")["generic"]["tiers"]["A"]
    assert "Groundwork" not in checklists("late-surger")["generic"]["tiers"]["S"]


def test_checklists_without_style_only_have_event_skills():
    cl = checklists(None)
    names = {n for tier in cl["generic"]["tiers"].values() for n in tier}
    assert names <= {"Speed", "Stamina", "Power", "Guts", "Wit", "Turf", "Dirt", "Sprint", "Mile",
                     "Medium", "Long", "Front Runner", "Pace Chaser", "Late Surger", "End Closer"}
    assert "Medium Corners \u25cb" in cl["aries-cup"]["tiers"]["S"]


def test_tier_letters_set_the_weights():
    skills = load_profiles()["aries-cup"]["white"]["skills"]
    assert skills[norm("Right-Handed \u25cb")] == 0.8
    assert skills[norm("Left-Handed \u25cb")] == 0.0


def test_event_tier_wins_over_style_tier():
    style = {"id": "x", "label": "X", "aptitude": "Pace Chaser",
             "_weights": {norm("Left-Handed \u25cb"): 1.0}}
    p = apply_style(PROFILE, style)
    assert p["white"]["skills"][norm("Left-Handed \u25cb")] == 0.0


def test_score_all_with_style_adds_label():
    out = score_all(parent(white("Uma Stan"), style="pace-chaser"))
    assert "Pace Chaser" in out["events"][0]["label"]
    assert out["events"][0]["profile_label"] == "Aries Cup"
    assert out["events"][0]["style_label"] == "Pace Chaser"
    assert score_all(parent(white("Uma Stan")))["events"][0]["style_label"] is None


def test_unknown_style_raises():
    with pytest.raises(ValueError):
        score_all(parent(white("Uma Stan")), style_id="nope")


def test_no_style_lists_a_skill_its_own_style_cannot_use():
    for sid, style in load_styles().items():
        prof = apply_style(load_profiles()["generic"], style)
        for letter, names in style["tiers"].items():
            if letter != "Z":
                for n in names:
                    assert blocked_reason(prof, n) is None, (sid, letter, n)


def test_ramp_up_and_risky_business_stay_in_the_good_tier_for_every_style():
    for sid in load_styles():
        tier_b = checklists(sid)["generic"]["tiers"]["B"]
        assert "Ramp Up" in tier_b and "Risky Business" in tier_b, sid


def test_event_layer_can_demote_a_style_skill_for_one_track():
    cl = checklists("end-closer")
    assert "Straightaway Spurt" in cl["generic"]["tiers"]["S"]
    assert "Straightaway Spurt" in cl["aries-cup"]["tiers"]["D"]
    assert "Straightaway Spurt" not in cl["aries-cup"]["tiers"]["S"]
