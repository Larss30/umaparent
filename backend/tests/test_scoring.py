from app.scoring.config import load_profiles, load_ranks
from app.scoring.engine import score_all, score_parent
from app.scoring.models import Parent, Spark, SparkBlock
from app.scoring.ranks import grade_for

ARIES = load_profiles()["aries-cup"]


def parent(*blocks):
    return Parent(name="test", blocks=list(blocks))


def block(role, *sparks):
    return SparkBlock(role=role, sparks=list(sparks))


def test_turf_pink_beats_dirt_pink_for_turf_race():
    turf = parent(block("self", Spark("pink", "Turf", 3)))
    dirt = parent(block("self", Spark("pink", "Dirt", 3)))
    assert score_parent(turf, ARIES)["categories"]["pink"] > \
        score_parent(dirt, ARIES)["categories"]["pink"]


def test_right_handed_counts_left_handed_does_not():
    right = parent(block("self", Spark("white", "Right-Handed ○", 2, "skill")))
    left = parent(block("self", Spark("white", "Left-Handed ○", 2, "skill")))
    assert score_parent(right, ARIES)["categories"]["white"] > \
        score_parent(left, ARIES)["categories"]["white"]


def test_name_lookup_ignores_case_and_spacing():
    a = parent(block("self", Spark("white", "right-handed  ○", 1, "skill")))
    assert score_parent(a, ARIES)["categories"]["white"] > 0


def test_own_sparks_worth_more_than_grandparent_sparks():
    own = parent(block("self", Spark("blue", "Speed", 3)))
    gp = parent(block("grandparent_1", Spark("blue", "Speed", 3)))
    assert score_parent(own, ARIES)["categories"]["blue"] > \
        score_parent(gp, ARIES)["categories"]["blue"]


def test_scores_bounded_and_more_sparks_never_lower_score():
    base = parent(block("self", Spark("blue", "Speed", 1)))
    more = parent(block("self", Spark("blue", "Speed", 1), Spark("blue", "Stamina", 3)))
    for _ in range(1):
        s1, s2 = score_parent(base, ARIES)["score"], score_parent(more, ARIES)["score"]
    assert 0 <= s1 <= s2 <= 100


def test_grade_ladder_is_monotonic_and_covers_extremes():
    ranks = load_ranks()
    order = {g: i for i, g in enumerate(ranks["grades"])}
    seen = [order[grade_for(s, ranks)] for s in range(0, 101)]
    assert seen == sorted(seen)
    assert grade_for(0, ranks) == ranks["grades"][0]
    assert grade_for(100, ranks) == ranks["grades"][-1]


def test_score_all_returns_overall_and_events():
    out = score_all(parent(block("self", Spark("blue", "Speed", 2))))
    assert out["overall"]["profile"] == "generic"
    assert any(e["profile"] == "aries-cup" for e in out["events"])
