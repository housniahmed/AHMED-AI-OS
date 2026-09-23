from fastapi.testclient import TestClient
from apps.api.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["system_composed"] is True


def test_create_user_and_read_context():
    r = client.post("/v1/users", json={"display_name": "Test User", "timezone": "Africa/Casablanca", "locale": "fr-MA"})
    assert r.status_code == 201
    uid = r.json()["user_id"]
    context = client.get(f"/v1/users/{uid}/context")
    assert context.status_code == 200
    assert context.json()["identity"]["display_name"] == "Test User"


def test_missing_user_is_404():
    assert client.get("/v1/users/00000000-0000-0000-0000-000000000000/context").status_code == 404


def test_conversation_routes_through_composed_orchestrator():
    user = client.post("/v1/users", json={"display_name": "Conversation User"})
    assert user.status_code == 201
    uid = user.json()["user_id"]

    r = client.post("/v1/conversations", json={"user_id": uid, "title": "Test"})
    assert r.status_code == 201
    cid = r.json()["conversation_id"]

    r = client.post(f"/v1/conversations/{cid}/messages", json={"content": "Bonjour"})
    assert r.status_code == 200
    assert r.json()["provider_configured"] is True
    assert r.json()["status"] == "completed"
    assert client.get(f"/v1/conversations/{cid}/messages").status_code == 200
