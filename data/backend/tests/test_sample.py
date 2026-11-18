import json
from pathlib import Path

from app.scoring.engine import score_all
from app.scoring.models import Parent, Spark, SparkBlock

SAMPLE = Path(__file__).resolve().parents[1] / "app" / "static" / "inari-one.json"


def load_sample(style=None):
    d = json.loads(SAMPLE.read_text(encoding="utf-8"))
    blocks = [SparkBlock(b["role"], [Spark(**s) for s in b["sparks"]], b.get("character"))
              for b in d["blocks"]]
    return Parent(d["name"], blocks, d.get("outfit"), style or d.get("style"))


def test_inari_one_sample_scores_and_core_three_complete():
    out = score_all(load_sample())
    assert out["overall"]["score"] > 0
    assert out["style"]["milestones"][0] == {"label": "Core three", "have": 3, "of": 3}


def test_inari_one_dirt_pink_hurts_turf_event_but_not_generic():
    out = score_all(load_sample())
    assert out["events"][0]["categories"]["pink"] < 100
