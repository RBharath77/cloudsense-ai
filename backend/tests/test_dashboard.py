from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["cloud_mode"] == "mock"

def get_demo_token():
    res = client.post("/api/auth/login", json={"email": "admin@cloudsense.ai", "password": "CloudSense@123"})
    assert res.status_code == 200
    return res.json()["access_token"]

def test_login_demo_user():
    token = get_demo_token()
    assert token is not None

def test_dashboard_seeded_organization():
    token = get_demo_token()
    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/api/dashboard/summary", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_spend"] > 0
    assert data["current_month_spend"] > 0
    assert data["predicted_month_end"] > 0
    assert data["potential_savings"] > 0
    assert data["active_resources"] == 120
    assert data["anomalies"] == 7
    assert data["cloud_health"] > 0
    assert data["carbon_kg"] > 0

def test_dashboard_empty_organization_regression():
    import uuid
    email = f"empty_org_{uuid.uuid4().hex[:8]}@cloudsense.ai"
    res = client.post("/api/auth/register", json={"email": email, "password": "TestPassword@123"})
    assert res.status_code == 200
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    dash_res = client.get("/api/dashboard/summary", headers=headers)
    assert dash_res.status_code == 200
    data = dash_res.json()
    assert data["total_spend"] == 0.0
    assert data["current_month_spend"] == 0.0
    assert data["active_resources"] == 0
    assert data["anomalies"] == 0
    assert data["potential_savings"] == 0.0
    assert data["cloud_health"] == 100.0

def test_forecast_endpoint():
    token = get_demo_token()
    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/api/forecast", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "predictions" in data
    assert len(data["predictions"]) == 30
    assert data["mae"] is not None and data["mae"] >= 0
    assert data["rmse"] is not None and data["rmse"] >= 0
    assert len(data["lower"]) == 30
    assert len(data["upper"]) == 30
