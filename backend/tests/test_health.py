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
