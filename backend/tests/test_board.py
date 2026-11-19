from app.scoring.config import load_profiles
from app.scoring.engine import checklists, score_all
from app.scoring.models import Parent, Spark, SparkBlock


def test_blue_and_pink_weights_come_from_tiers():
    p = load_profiles()["aries-cup"]
    assert p["blue"]["power"] == 0.8 and p["pink"]["turf"] == 1.0 and p["pink"]["dirt"] == 0.0


def test_checklist_has_blue_and_pink_cards_in_tiers():
    tiers = checklists(None)["aries-cup"]["tiers"]
    assert "Speed" in tiers["S"] and "Turf" in tiers["S"] and "Dirt" in tiers["Z"]


def test_style_aptitude_card_follows_the_chosen_style():
    tiers = checklists("pace-chaser")["aries-cup"]["tiers"]
    assert "Pace Chaser" in tiers["S"] and "Front Runner" in tiers["Z"]


def test_context_weights_can_retier_blue_pink_and_green_sparks_for_one_event():
    sparks = [Spark("blue", "Guts", 3), Spark("pink", "Dirt", 3), Spark("green", "Some Unique", 2)]
    tuned = {"aries-cup": {"Guts": 1.0, "Dirt": 1.0, "Some Unique": 1.0}}
    a = score_all(Parent("t", [SparkBlock("self", list(sparks))]))
    b = score_all(Parent("t", [SparkBlock("self", list(sparks))], context_weights=tuned))
    for cat in ("blue", "pink", "green"):
        assert b["events"][0]["categories"][cat] > a["events"][0]["categories"][cat]
        assert b["overall"]["categories"][cat] == a["overall"]["categories"][cat]


def test_each_green_spark_can_have_its_own_weight():
    p = Parent("t", [SparkBlock("self", [Spark("green", "Strong One", 2), Spark("green", "Weak One", 2)])],
               context_weights={"aries-cup": {"Strong One": 1.0, "Weak One": 0.1}})
    one = Parent("t", [SparkBlock("self", [Spark("green", "Strong One", 2)])],
                 context_weights={"aries-cup": {"Strong One": 1.0}})
    two = Parent("t", [SparkBlock("self", [Spark("green", "Weak One", 2)])],
                 context_weights={"aries-cup": {"Weak One": 0.1}})
    g = lambda x: score_all(x)["events"][0]["categories"]["green"]  # noqa: E731
    assert g(one) > g(two) and g(p) > g(one)
