from fastapi.testclient import TestClient
import pytest

from api.database.connection import Base, SessionLocal, engine
from api.database import schemas
from api.main import app
from ml.predict import get_predictor


@pytest.fixture(scope="module")
def client():
    Base.metadata.create_all(bind=engine)
    test_client = TestClient(app)
    yield test_client
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


@pytest.fixture(autouse=True)
def clean_db():
    predictor = get_predictor()
    if hasattr(predictor.model, "n_jobs"):
        predictor.model.n_jobs = 1

    db = SessionLocal()
    try:
        db.query(schemas.AlertRecord).delete()
        db.query(schemas.PredictionRecord).delete()
        db.query(schemas.SensorReading).delete()
        db.query(schemas.MaintenanceLog).delete()
        db.commit()
    finally:
        db.close()


@pytest.fixture
def sample_sensor_payload():
    return {
        "udi": 999,
        "product_id": "TEST001",
        "type": "M",
        "air_temp_k": 298.1,
        "process_temp_k": 308.6,
        "rotational_speed_rpm": 1551,
        "torque_nm": 42.8,
        "tool_wear_min": 0,
    }


@pytest.fixture
def high_risk_payload():
    return {
        "udi": 998,
        "product_id": "TEST_HIGH",
        "type": "H",
        "air_temp_k": 305.0,
        "process_temp_k": 315.0,
        "rotational_speed_rpm": 1200,
        "torque_nm": 75.0,
        "tool_wear_min": 220,
    }


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert "version" in payload
    assert "timestamp" in payload


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()


def test_ingest_sensor_data(client, sample_sensor_payload):
    response = client.post("/ingest/sensor-data", json=sample_sensor_payload)
    assert response.status_code == 201
    payload = response.json()
    assert "sensor_id" in payload
    assert payload["sensor_id"] > 0


def test_ingest_high_risk_creates_alert(client, high_risk_payload):
    response = client.post("/ingest/sensor-data", json=high_risk_payload)
    assert response.status_code == 201
    payload = response.json()
    assert payload["alert_created"] is True
    assert payload["alert_severity"] in {"HIGH", "CRITICAL"}


def test_get_sensor_readings(client, sample_sensor_payload):
    client.post("/ingest/sensor-data", json=sample_sensor_payload)
    response = client.get("/ingest/sensor-data")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert len(payload) >= 1


def test_get_sensor_by_id(client, sample_sensor_payload):
    create_resp = client.post("/ingest/sensor-data", json=sample_sensor_payload)
    sensor_id = create_resp.json()["sensor_id"]
    response = client.get(f"/ingest/sensor-data/{sensor_id}")
    assert response.status_code == 200
    assert response.json()["id"] == sensor_id


def test_sensor_not_found(client):
    response = client.get("/ingest/sensor-data/99999")
    assert response.status_code == 404


def test_prediction_endpoint(client, high_risk_payload):
    response = client.post(
        "/predict/failure",
        json={"sensor_data": high_risk_payload, "save_to_db": True},
    )
    assert response.status_code == 201
    payload = response.json()
    assert "failure_predicted" in payload
    assert "failure_probability" in payload
    assert "risk_level" in payload
    assert payload["risk_level"] in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}


def test_prediction_high_risk(client, high_risk_payload):
    response = client.post(
        "/predict/failure",
        json={"sensor_data": high_risk_payload, "save_to_db": True},
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["failure_probability"] > 0.5
    assert payload["risk_level"] in {"HIGH", "CRITICAL"}


def test_search_endpoint(client):
    response = client.get("/search/documents?q=bearing+replacement")
    assert response.status_code == 200
    payload = response.json()
    assert "results" in payload
    assert "query" in payload


def test_agent_status_endpoint(client):
    response = client.get("/agent/status")
    assert response.status_code == 200
    payload = response.json()
    assert "agents_initialized" in payload
    assert "available_agents" in payload
    assert len(payload["available_agents"]) == 3


def test_agent_query_fallback(client):
    response = client.post("/agent/query", json={"question": "test question"})
    assert response.status_code == 200
    payload = response.json()
    assert "answer" in payload
    assert "status" in payload


def test_system_config_endpoint(client):
    response = client.get("/system/config")
    assert response.status_code == 200
    payload = response.json()
    assert "environment" in payload
    assert "azure_openai_configured" in payload
    assert "your_" not in str(payload)


def test_ingest_validation(client):
    bad_payload = {
        "udi": 997,
        "product_id": "TEST_BAD",
        "type": "X",
        "air_temp_k": 298.1,
        "process_temp_k": 308.6,
        "rotational_speed_rpm": 1551,
        "torque_nm": 42.8,
        "tool_wear_min": 0,
    }
    response = client.post("/ingest/sensor-data", json=bad_payload)
    assert response.status_code == 422


def test_batch_prediction(client, sample_sensor_payload, high_risk_payload):
    payload = [
        sample_sensor_payload,
        high_risk_payload,
        {
            "udi": 996,
            "product_id": "TEST002",
            "type": "L",
            "air_temp_k": 300.0,
            "process_temp_k": 310.0,
            "rotational_speed_rpm": 1400,
            "torque_nm": 35.0,
            "tool_wear_min": 10,
        },
    ]
    response = client.post("/predict/batch", json=payload)
    assert response.status_code == 200
    results = response.json()
    assert isinstance(results, list)
    assert len(results) == 3
