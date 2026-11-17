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


def test_style_endpoint_and_scoring():
    assert any(s["id"] == "pace-chaser" for s in client.get("/api/styles").json())
    body = {"name": "x", "style": "pace-chaser",
            "blocks": [{"role": "self", "sparks": [
                {"kind": "white", "name": "Uma Stan", "stars": 2, "category": "skill"}]}]}
    r = client.post("/api/score", json=body)
    assert r.status_code == 200 and r.json()["style"]["milestones"]
    body["style"] = "nope"
    assert client.post("/api/score", json=body).status_code == 400
