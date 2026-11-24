from app.scoring.config import load_profiles, load_ranks
from app.scoring.engine import score_all, score_parent
from app.scoring.models import Parent, Spark, SparkBlock
from app.scoring.ranks import grade_for, next_grade

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


def test_more_sparks_never_lower_score():
    base = parent(block("self", Spark("blue", "Speed", 1)))
    more = parent(block("self", Spark("blue", "Speed", 1), Spark("blue", "Stamina", 3)))
    assert 0 <= score_parent(base, ARIES)["score"] <= score_parent(more, ARIES)["score"]


def test_scores_are_not_capped_at_100():
    sparks = [Spark(k, n, 3, "skill" if k == "white" else None)
              for k, n in (("blue", "Speed"), ("pink", "Turf"),
                           ("green", "X"), ("white", "Right-Handed ○"))] * 5
    assert score_parent(parent(block("self", *sparks)), ARIES)["score"] > 100


def test_grade_ladder_is_monotonic_with_thresholds():
    ranks = load_ranks()
    names = [g["grade"] for g in ranks["grades"]]
    order = {g: i for i, g in enumerate(names)}
    seen = [order[grade_for(s / 2, ranks)] for s in range(0, 800)]
    assert seen == sorted(seen)
    assert grade_for(-5, ranks) == names[0]
    assert grade_for(10**6, ranks) == names[-1]


def test_next_grade_reports_gap_and_none_at_top():
    ranks = load_ranks()
    nxt = next_grade(0, ranks)
    assert nxt["grade"] == ranks["grades"][1]["grade"] and nxt["needed"] > 0
    assert next_grade(10**6, ranks) is None


def test_affinity_is_optional_and_raises_score():
    base = parent(block("self", Spark("blue", "Speed", 2)))
    with_aff = Parent("t", base.blocks, affinity=200, affinity_target="Oguri Cap")
    r0, r1 = score_parent(base, ARIES), score_parent(with_aff, ARIES)
    assert "affinity" not in r0 and "affinity" not in r0["categories"]
    a = r1["affinity"]
    assert (a["value"], a["base"], a["races"], a["target"]) == (200, 200, 0, "Oguri Cap")
    assert r1["score"] > r0["score"]


def test_score_all_returns_overall_and_events():
    out = score_all(parent(block("self", Spark("blue", "Speed", 2))))
    assert out["overall"]["profile"] == "generic"
    assert any(e["profile"] == "aries-cup" for e in out["events"])
