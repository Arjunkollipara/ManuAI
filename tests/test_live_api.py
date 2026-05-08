import requests
import json

BASE = "http://localhost:8000"

def test(name, method, url, body=None):
    try:
        if method == "GET":
            r = requests.get(BASE + url, timeout=10)
        else:
            r = requests.post(
                BASE + url, 
                json=body, 
                timeout=30
            )
        status = "PASS" if r.status_code in [
            200, 201
        ] else "FAIL"
        print(f"{status} [{r.status_code}] {name}")
        return r.json()
    except Exception as e:
        print(f"ERROR {name}: {e}")
        return None

print("\n=== BACKEND LIVE TEST ===\n")

# Health
test("Health Check", "GET", "/health")
test("Root", "GET", "/")
test("System Config", "GET", "/system/config")

# Ingest
sensor = test("Ingest Sensor Data", "POST",
    "/ingest/sensor-data", {
        "udi": 100,
        "product_id": "TEST001",
        "type": "M",
        "air_temp_k": 298.1,
        "process_temp_k": 308.6,
        "rotational_speed_rpm": 1551,
        "torque_nm": 42.8,
        "tool_wear_min": 0
    })

test("Ingest High Risk", "POST",
    "/ingest/sensor-data", {
        "udi": 101,
        "product_id": "H99999",
        "type": "H",
        "air_temp_k": 305.0,
        "process_temp_k": 315.0,
        "rotational_speed_rpm": 1200,
        "torque_nm": 75.0,
        "tool_wear_min": 220
    })

test("Get Sensor Readings", "GET",
    "/ingest/sensor-data?limit=5")
test("Get Stats", "GET", "/ingest/stats")

# Predict
pred = test("Predict Failure", "POST",
    "/predict/failure", {
        "sensor_data": {
            "type": "H",
            "air_temp_k": 305.0,
            "process_temp_k": 315.0,
            "rotational_speed_rpm": 1200,
            "torque_nm": 75.0,
            "tool_wear_min": 220
        },
        "save_to_db": True
    })
if pred:
    print(f"   Risk Level: {pred.get('risk_level')}")
    print(f"   Probability: {pred.get('failure_probability')}")

test("Predict History", "GET",
    "/predict/history?limit=5")
test("Get Alerts", "GET",
    "/predict/alerts?limit=5")

# Search
search = test("Document Search", "GET",
    "/search/documents?q=bearing+replacement")
if search:
    print(f"   Results: {search.get('total_results')}")
    print(f"   Status: {search.get('status')}")

test("Search Health", "GET",
    "/search/documents/health")

# Agent
print("\n--- Agent Tests (may take 30-60s) ---")
agent_status = test("Agent Status", "GET",
    "/agent/status")
if agent_status:
    print(f"   Credentials: {agent_status.get('credentials_configured')}")

agent1 = test("Agent - Maintenance Query", "POST",
    "/agent/query", {
        "question": "How do I replace a bearing?"
    })
if agent1:
    print(f"   Agent used: {agent1.get('agent_used')}")
    print(f"   Status: {agent1.get('status')}")
    print(f"   Answer preview: {str(agent1.get('answer',''))[:100]}")

agent2 = test("Agent - Analytics Query", "POST",
    "/agent/query", {
        "question": "What are the recent production alerts?"
    })
if agent2:
    print(f"   Agent used: {agent2.get('agent_used')}")
    print(f"   Status: {agent2.get('status')}")

agent3 = test("Agent - Multi Agent Query", "POST",
    "/agent/query", {
        "question": "Machine H99999 is critical, what should I do?"
    })
if agent3:
    print(f"   Agent used: {agent3.get('agent_used')}")
    print(f"   Status: {agent3.get('status')}")

print("\n=== TEST COMPLETE ===\n")
