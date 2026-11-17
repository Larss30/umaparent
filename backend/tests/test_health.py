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
