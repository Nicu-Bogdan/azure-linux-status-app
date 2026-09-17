from app import app


def test_health_live():
    client = app.test_client()

    response = client.get("/health/live")

    assert response.status_code == 200

def test_health_ready():
    client = app.test_client()

    response = client.get("/health/ready")

    assert response.status_code == 200

    data = response.get_json()

    assert data["status"] == "ok"
    assert data["database"] == "ok"


def test_create_snapshot():
    client = app.test_client()

    response = client.post("/snapshot")

    assert response.status_code == 201

    data = response.get_json()

    assert "id" in data
    assert "cpu_percent" in data
    assert "memory_percent" in data
    assert "uptime_seconds" in data

def test_get_history():
    client = app.test_client()

    snapshot_response = client.post("/snapshot")

    assert snapshot_response.status_code == 201

    snapshot_data = snapshot_response.get_json()
    snapshot_id = snapshot_data["id"]

    history_response = client.get("/history")

    assert history_response.status_code == 200

    history = history_response.get_json()

    assert isinstance(history, list)
    assert any(item["id"] == snapshot_id for item in history)
