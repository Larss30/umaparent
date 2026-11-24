import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_score_endpoint():
    body = {
        "name": "Inari One",
        "blocks": [{"role": "self", "sparks": [
            {"kind": "pink", "name": "Dirt", "stars": 2},
            {"kind": "blue", "name": "Guts", "stars": 1},
        ]}],
    }
    r = client.post("/api/score", json=body)
    assert r.status_code == 200
    assert "overall" in r.json() and r.json()["events"]


def test_styles_checklists_tiers_and_skills_endpoints():
    assert any(s["id"] == "pace-chaser" for s in client.get("/api/styles").json())
    cl = client.get("/api/checklists?style=pace-chaser").json()
    assert "Nimble Navigator" in cl["generic"]["tiers"]["S"]
    assert client.get("/api/checklists?style=nope").status_code == 400
    assert [t["id"] for t in client.get("/api/tiers").json()][-1] == "Z"
    assert any(s["name"] == "Nimble Navigator" for s in client.get("/api/skills").json())
    body = {"name": "x", "style": "pace-chaser",
            "context_weights": {"aries-cup": {"Uma Stan": 1.0, "Old Skill": None}},
            "custom_blue": {"Guts": 1.0},
            "blocks": [{"role": "self", "sparks": [
                {"kind": "white", "name": "Uma Stan", "stars": 2, "category": "skill", "skill_id": 1}]}]}
    assert client.post("/api/score", json=body).status_code == 200
    body["style"] = "nope"
    assert client.post("/api/score", json=body).status_code == 400


def test_index_page_served():
    r = client.get("/")
    assert r.status_code == 200 and "UmaParent" in r.text


def test_custom_weights_and_skill_weights_endpoints():
    body = {"name": "x", "custom_weights": {"Obscure Skill": 1.0},
            "blocks": [{"role": "self", "sparks": [
                {"kind": "white", "name": "Obscure Skill", "stars": 1, "category": "skill"}]}]}
    r = client.post("/api/score", json=body)
    assert r.status_code == 200 and "Obscure Skill" in r.json()["important"]
    body["custom_weights"] = {"Obscure Skill": 99}
    assert client.post("/api/score", json=body).status_code == 422
    rows = client.get("/api/skill-weights?style=pace-chaser").json()
    assert any(x["name"] == "Nimble Navigator" for x in rows)
    assert client.get("/api/skill-weights?style=nope").status_code == 400


def test_auto_zero_flag_and_checklist_param():
    body = {"name": "x", "auto_zero": False, "blocks": [{"role": "self", "sparks": [
        {"kind": "white", "name": "Long Corners \u25cb", "stars": 2, "category": "skill"}]}]}
    assert client.post("/api/score", json=body).status_code == 200
    cl = client.get("/api/checklists?auto_zero=false").json()
    assert cl["aries-cup"]["blocked"] == []


def test_read_screenshots_rejects_junk_and_too_many_files():
    junk = ("files", ("x.png", b"not an image", "image/png"))
    r = client.post("/api/read-screenshots", files=[junk])
    assert r.status_code == 400 and "readable image" in r.json()["detail"]
    assert client.post("/api/read-screenshots", files=[junk] * 9).status_code == 400


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="tesseract is not installed")
def test_read_screenshots_endpoint_returns_a_parent():
    png = (Path(__file__).parent / "fixtures" / "inspiration-top.png").read_bytes()
    r = client.post("/api/read-screenshots", files=[("files", ("top.png", png, "image/png"))])
    assert r.status_code == 200
    block = r.json()["parent"]["blocks"][0]
    assert block["role"] == "self" and any(s["name"] == "Guts" for s in block["sparks"])


def test_races_endpoint_and_g1_wins_in_scoring():
    data = client.get("/api/races").json()
    assert len(data["races"]) == 34 and data["points_per_shared_g1"] == 3
    wins = ["arima-kinen", "japan-cup"]
    body = {"name": "x", "blocks": [{"role": r, "sparks": [], "g1_wins": wins}
                                    for r in ("self", "grandparent_1", "grandparent_2")]}
    aff = client.post("/api/score", json=body).json()["overall"]["affinity"]
    assert aff["races"] == 12 and aff["shared"] == {"grandparent_1": 2, "grandparent_2": 2}
