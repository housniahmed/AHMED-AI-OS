from fastapi.testclient import TestClient
from apps.api.main import app, authenticated_owner
from uuid import uuid4
import pytest

@pytest.fixture(autouse=True)
def owner(monkeypatch):
    uid = uuid4()
    monkeypatch.setenv('AHMED_OWNER_ID', str(uid))
    monkeypatch.setenv('AHMED_API_TOKEN', 'test-token-' + 'x'*32)
    client.headers['Authorization'] = 'Bearer test-token-' + 'x'*32
    yield uid
    client.headers.pop('Authorization', None)

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


def test_missing_user_is_404(owner):
    assert client.get(f'/v1/users/{owner}/context').status_code == 404


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


def test_unauthenticated_and_cross_user_denied(owner):
    assert TestClient(app).get('/v1/business/snapshot').status_code == 401
    assert client.get(f'/v1/users/{uuid4()}/context').status_code == 403
    assert client.post('/v1/conversations', json={'user_id':str(uuid4())}).status_code == 403
