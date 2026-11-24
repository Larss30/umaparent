import collections
import re

from app.scoring.config import load_races
from app.scoring.engine import race_affinity, score_all
from app.scoring.models import Parent, SparkBlock


def lineage(own, gp1=(), gp2=(), **kw):
    return Parent("t", [SparkBlock("self", g1_wins=list(own)), SparkBlock("grandparent_1", g1_wins=list(gp1)),
                        SparkBlock("grandparent_2", g1_wins=list(gp2))], **kw)


def test_calendar_has_the_expected_unique_races():
    races = load_races()
    assert len(races) == 34 and len({r["id"] for r in races}) == 34
    per_year = collections.Counter(s.split("-")[0] for r in races for s in r["slots"])
    assert dict(per_year) == {"junior": 4, "classic": 22, "senior": 22}
    for r in races:
        assert r["surface"] in ("turf", "dirt") and r["category"] in ("sprint", "mile", "medium", "long")
        assert all(re.fullmatch(r"(junior|classic|senior)-(early|late)-[a-z]{3}", s) for s in r["slots"])


def test_race_affinity_counts_shared_unique_wins_with_each_grandparent():
    ra = race_affinity(lineage(["arima-kinen", "japan-cup", "oka-sho"], ["arima-kinen", "japan-cup"], ["japan-cup", "teio-sho"]))
    assert ra["shared"] == {"grandparent_1": 2, "grandparent_2": 1} and ra["points"] == 9


def test_unknown_race_ids_are_ignored_and_no_wins_means_no_race_affinity():
    assert race_affinity(lineage([], ["arima-kinen"])) is None          # parent's wins not entered yet
    assert race_affinity(lineage(["arima-kinen"])) is None              # grandparents' wins not entered yet
    assert race_affinity(lineage(["not-a-race"], ["not-a-race"])) is None


def test_affinity_adds_race_points_to_the_entered_number():
    own = ["arima-kinen", "japan-cup"]
    out = score_all(lineage(own, own, own, affinity=50, affinity_target="Oguri Cap"))["overall"]["affinity"]
    assert (out["base"], out["races"], out["value"], out["target"]) == (50, 12, 62, "Oguri Cap")
    only_races = score_all(lineage(own, own))["overall"]["affinity"]
    assert only_races["base"] is None and only_races["value"] == 6


def test_more_shared_wins_raise_the_score():
    few = score_all(lineage(["arima-kinen"], ["arima-kinen"]))["overall"]["score"]
    many = score_all(lineage(["arima-kinen", "japan-cup", "oka-sho"], ["arima-kinen", "japan-cup", "oka-sho"]))["overall"]["score"]
    assert many > few
