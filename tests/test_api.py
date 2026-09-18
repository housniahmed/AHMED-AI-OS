from fastapi.testclient import TestClient
from apps.api.main import app
client = TestClient(app)
def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
def test_create_user_and_read_context():
    response = client.post("/v1/users", json={"display_name":"Test User","timezone":"Africa/Casablanca","locale":"fr-MA"})
    assert response.status_code == 201
    user_id = response.json()["user_id"]
    context = client.get(f"/v1/users/{user_id}/context")
    assert context.status_code == 200
    assert context.json()["identity"]["display_name"] == "Test User"
def test_missing_user_is_404():
    response = client.get("/v1/users/00000000-0000-0000-0000-000000000000/context")
    assert response.status_code == 404
