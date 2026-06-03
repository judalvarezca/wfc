from fastapi.testclient import TestClient

from wfc.web.app import app

client = TestClient(app)

EASY = (
    "530070000"
    "600195000"
    "098000060"
    "800060003"
    "400803001"
    "700020006"
    "060000280"
    "000419005"
    "000080079"
)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_index_html_served():
    r = client.get("/")
    assert r.status_code == 200
    assert "<title>WFC Sudoku</title>" in r.text


def test_static_assets_served():
    r = client.get("/static/app.js")
    assert r.status_code == 200
    assert "function buildGrid" in r.text


def test_generate_returns_81_char_board():
    r = client.post("/api/generate", json={"givens": 30, "seed": 42})
    assert r.status_code == 200
    body = r.json()
    assert len(body["board"]) == 81
    assert body["givens"] == 30
    assert body["seed"] == 42
    givens = sum(1 for c in body["board"] if c in "123456789")
    assert givens == 30


def test_generate_invalid_givens_rejected():
    r = client.post("/api/generate", json={"givens": 100})
    assert r.status_code == 422  # Pydantic validation


def test_validate_easy():
    r = client.post("/api/validate", json={"board": EASY})
    assert r.status_code == 200
    body = r.json()
    assert body["givens"] == 30
    assert body["consistent"] is True
    assert body["solved"] is False


def test_validate_invalid_board():
    r = client.post("/api/validate", json={"board": "garbage"})
    assert r.status_code == 400


def test_solve_easy_returns_solution_and_events():
    r = client.post("/api/solve", json={"board": EASY, "seed": 0})
    assert r.status_code == 200
    body = r.json()
    assert body["solution"] is not None
    assert len(body["solution"]) == 81
    assert all(c in "123456789" for c in body["solution"])
    assert len(body["events"]) > 0
    # Last event should be Solved.
    assert body["events"][-1]["type"] == "Solved"
    # At least one Collapsed.
    assert any(e["type"] == "Collapsed" for e in body["events"])


def test_solve_unsolvable_returns_null_with_contradiction():
    r = client.post("/api/solve", json={"board": "55" + "0" * 79})
    assert r.status_code == 200
    body = r.json()
    assert body["solution"] is None
    assert body["events"] == [{"type": "Contradiction"}]


def test_solve_event_shape():
    """Each event has a 'type' discriminator and the expected fields."""
    r = client.post("/api/solve", json={"board": EASY, "seed": 0})
    body = r.json()
    for e in body["events"]:
        assert "type" in e
        if e["type"] == "Collapsed":
            assert "var" in e and len(e["var"]) == 2
            assert "state" in e and 1 <= e["state"] <= 9
        elif e["type"] == "Observed":
            assert "var" in e and len(e["var"]) == 2
        elif e["type"] == "Backtracked":
            assert "var" in e and "state" in e and "undid_vars" in e
            assert isinstance(e["undid_vars"], list)
