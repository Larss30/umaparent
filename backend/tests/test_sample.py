import json
from pathlib import Path

from app.scoring.config import load_styles, norm
from app.scoring.engine import score_all
from app.scoring.models import Parent, Spark, SparkBlock

SAMPLE = Path(__file__).resolve().parents[1] / "app" / "static" / "inari-one.json"


def load_sample(style=None):
    d = json.loads(SAMPLE.read_text(encoding="utf-8"))
    blocks = [SparkBlock(b["role"], [Spark(**s) for s in b["sparks"]], b.get("character"))
              for b in d["blocks"]]
    return Parent(d["name"], blocks, d.get("outfit"), style or d.get("style"))


def test_inari_one_sample_scores_and_has_every_S_tier_skill():
    p = load_sample()
    out = score_all(p)
    assert out["overall"]["score"] > 0
    have = {norm(s.name) for b in p.blocks for s in b.sparks}
    s_tier = load_styles()["pace-chaser"]["tiers"]["S"]
    core = ["Nimble Navigator", "Uma Stan", "Racing Spirit: Stamina"]
    assert all(n in s_tier and norm(n) in have for n in core)


def test_inari_one_dirt_pink_hurts_turf_event_but_not_generic():
    out = score_all(load_sample())
    assert out["events"][0]["categories"]["pink"] < 100
