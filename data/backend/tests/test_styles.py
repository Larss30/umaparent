import copy

import pytest

from app.scoring.config import load_profiles, load_styles
from app.scoring.engine import apply_style, score_all, score_parent, style_checklist
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
    names = ["Nimble Navigator", "Tail Held High", "Risky Business", "Head-on", "On the Attack"]
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


def test_checklist_milestones_are_cumulative():
    p = parent(white("Nimble Navigator"), white("Uma Stan"),
               white("Racing Spirit: Stamina", category="scenario"), white("Tail Held High"))
    m = style_checklist(p, PACE)["milestones"]
    assert [(x["have"], x["of"]) for x in m] == [(3, 3), (4, 6), (4, 8)]


def test_checklist_reports_missing_and_blocks():
    p = Parent("t", [SparkBlock("grandparent_1", [white("Slipstream", 3)])])
    good = style_checklist(p, PACE)["tiers"][1]
    assert good["have"] == [{"name": "Slipstream", "blocks": {"grandparent_1": 3}}]
    assert "Tail Held High" in good["missing"]


def test_score_all_with_style_adds_checklist_and_label():
    out = score_all(parent(white("Uma Stan"), style="pace-chaser"))
    assert "Pace Chaser" in out["events"][0]["label"]
    assert out["style"]["style"] == "pace-chaser"


def test_unknown_style_raises():
    with pytest.raises(ValueError):
        score_all(parent(white("Uma Stan")), style_id="nope")
