import uuid
from datetime import datetime
from jose import jwt
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.models import Anomaly, CostRecord, CloudResource, User
from app.database import SessionLocal

client = TestClient(app)

def create_user_and_token(prefix="fa_user"):
    email = f"{prefix}_{uuid.uuid4().hex[:8]}@cloudsense.ai"
    res = client.post("/api/auth/register", json={"email": email, "password": "Password123!"})
    assert res.status_code == 200
    token = res.json()["access_token"]
    uid = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])["sub"]
    db = SessionLocal()
    try:
        user = db.get(User, uid)
        org_id = user.organization_id
    finally:
        db.close()
    return token, org_id

def get_demo_token():
    res = client.post("/api/auth/login", json={"email": "admin@cloudsense.ai", "password": "CloudSense@123"})
    assert res.status_code == 200
    return res.json()["access_token"]

def test_multi_horizon_forecasting():
    token = get_demo_token()
    headers = {"Authorization": f"Bearer {token}"}

    for horizon in [7, 14, 30, 60, 90]:
        res = client.get(f"/api/forecast?horizon={horizon}", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert len(data["predictions"]) == horizon
        assert len(data["lower"]) == horizon
        assert len(data["upper"]) == horizon
        assert len(data["forecast_series"]) == horizon
        assert data["horizon"] == horizon

        # Non-negative guardrail assertion
        assert all(p >= 0.0 for p in data["predictions"]), f"Negative prediction found in horizon {horizon}"
        assert all(l >= 0.0 for l in data["lower"]), f"Negative lower bound found in horizon {horizon}"
        assert all(u >= l for l, u in zip(data["lower"], data["upper"])), "Upper bound lower than lower bound"

def test_forecasting_evaluation_metrics_and_baseline():
    token = get_demo_token()
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/forecast?horizon=30&confidence=0.80", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["mae"] >= 0.0
    assert data["rmse"] >= 0.0
    assert data["baseline_mae"] >= 0.0
    assert data["baseline_rmse"] >= 0.0
    assert "improvement_pct" in data
    assert data["model_name"] == "Polynomial Trend with Non-Negative Bounds"
    assert data["training_samples"] > 0
    assert data["total_predicted_spend"] >= 0.0
    assert data["daily_average_predicted"] >= 0.0
    assert "historical_series" in data
    assert len(data["historical_series"]) > 0

def test_provider_filtered_forecasting():
    token = get_demo_token()
    headers = {"Authorization": f"Bearer {token}"}

    res_aws = client.get("/api/forecast?provider=AWS&horizon=14", headers=headers)
    assert res_aws.status_code == 200
    data_aws = res_aws.json()
    assert len(data_aws["predictions"]) == 14

    res_gcp = client.get("/api/forecast?provider=GCP&horizon=14", headers=headers)
    assert res_gcp.status_code == 200
    data_gcp = res_gcp.json()
    assert len(data_gcp["predictions"]) == 14

    # Both forecasts should produce valid non-negative predictions
    assert all(p >= 0.0 for p in data_aws["predictions"])
    assert all(p >= 0.0 for p in data_gcp["predictions"])

def test_empty_organization_forecast_graceful():
    token, _ = create_user_and_token("empty_fc")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/forecast?horizon=30", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data["predictions"]) == 30
    assert all(p == 0.0 for p in data["predictions"])
    assert all(l == 0.0 for l in data["lower"])
    assert data["total_predicted_spend"] == 0.0
    assert data["daily_average_predicted"] == 0.0
    assert len(data["historical_series"]) == 0

def test_list_anomalies_and_filtering():
    token = get_demo_token()
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/anomalies", headers=headers)
    assert res.status_code == 200
    anomalies = res.json()
    assert isinstance(anomalies, list)
    assert len(anomalies) > 0

    first = anomalies[0]
    for required_key in ["id", "provider", "resource_id", "severity", "financial_impact", "score", "reason", "recommendation"]:
        assert required_key in first

    # Severity filtering
    res_crit = client.get("/api/anomalies?severity=CRITICAL", headers=headers)
    assert res_crit.status_code == 200
    for a in res_crit.json():
        assert a["severity"] == "CRITICAL"

    # Provider filtering
    res_aws = client.get("/api/anomalies?provider=AWS", headers=headers)
    assert res_aws.status_code == 200
    for a in res_aws.json():
        assert a["provider"] == "AWS"

def test_dynamic_anomaly_detection_execution():
    token = get_demo_token()
    headers = {"Authorization": f"Bearer {token}"}

    res_before = client.get("/api/anomalies", headers=headers)
    initial_ids = {a["id"] for a in res_before.json()}

    try:
        res = client.post("/api/anomalies/detect?contamination=0.08", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert "anomalies_detected" in data
        assert "anomalies" in data
        assert "total_spend_evaluated" in data
        assert data["total_spend_evaluated"] >= 0.0

        for a in data["anomalies"]:
            assert a["financial_impact"] >= 0.0
            assert a["severity"] in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
            assert len(a["reason"]) > 0
    finally:
        db = SessionLocal()
        try:
            demo_user = db.query(User).filter_by(email="admin@cloudsense.ai").first()
            if demo_user:
                db.query(Anomaly).filter(
                    Anomaly.organization_id == demo_user.organization_id,
                    ~Anomaly.id.in_(initial_ids)
                ).delete(synchronize_session=False)
                db.commit()
        finally:
            db.close()

def test_root_cause_analysis_endpoint():
    token = get_demo_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Fetch existing anomaly ID
    res = client.get("/api/anomalies", headers=headers)
    assert res.status_code == 200
    anomalies = res.json()
    assert len(anomalies) > 0
    anomaly_id = anomalies[0]["id"]

    rca_res = client.get(f"/api/rca/{anomaly_id}", headers=headers)
    assert rca_res.status_code == 200
    rca = rca_res.json()

    assert "root_cause" in rca
    assert "evidence" in rca
    assert isinstance(rca["evidence"], list)
    assert len(rca["evidence"]) >= 1
    assert "timeline" in rca
    assert isinstance(rca["timeline"], list)
    assert "recommendation" in rca
    assert "financial_impact" in rca

    # Non-existent ID returns 404
    non_existent = client.get("/api/rca/non_existent_id_999", headers=headers)
    assert non_existent.status_code == 404

def test_multi_tenant_isolation_forecast_and_anomalies():
    token_a, org_a = create_user_and_token("org_a_fa")
    token_b, org_b = create_user_and_token("org_b_fa")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Inject an anomaly directly into Org A
    db = SessionLocal()
    try:
        anomaly_a = Anomaly(
            organization_id=org_a,
            resource_id="i-test-org-a-1234",
            provider="AWS",
            metric="cpu_spike_spend",
            severity="CRITICAL",
            financial_impact=1450.00,
            score=0.96,
            reason="Org A dedicated cluster spike",
            recommendation="Inspect Org A auto-scaling group",
            timestamp=datetime.utcnow()
        )
        db.add(anomaly_a)
        db.commit()
        db.refresh(anomaly_a)
        target_id = anomaly_a.id
    finally:
        db.close()

    # Org A can read it
    res_a = client.get(f"/api/rca/{target_id}", headers=headers_a)
    assert res_a.status_code == 200
    assert res_a.json()["root_cause"] == "Org A dedicated cluster spike"

    # Org B CANNOT read Org A's anomaly (multi-tenant 404 isolation)
    res_b = client.get(f"/api/rca/{target_id}", headers=headers_b)
    assert res_b.status_code == 404

    # Org B list anomalies does NOT contain Org A's anomaly
    list_b = client.get("/api/anomalies", headers=headers_b).json()
    assert all(a["id"] != target_id for a in list_b)
