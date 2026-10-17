import uuid
import io
from jose import jwt
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.models import CarbonRecord, CarbonBudget, User
from app.database import SessionLocal

client = TestClient(app)

def create_user_and_token(prefix="cs_user"):
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

def test_carbon_summary_aggregation():
    token = get_demo_token()
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/carbon/summary", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert data["total_co2_kg"] > 0
    assert data["total_co2_mt"] == round(data["total_co2_kg"] / 1000.0, 3)
    assert len(data["provider_breakdown"]) >= 3
    providers = {p["provider"] for p in data["provider_breakdown"]}
    assert "AWS" in providers
    assert "Azure" in providers
    assert "GCP" in providers

    assert len(data["scope_breakdown"]) >= 3
    assert "data_coverage" in data
    assert "methodology" in data
    assert "GHG Protocol" in data["methodology"]["standard"]
    assert "spend alone" in data["methodology"]["limitations"]

def test_carbon_records_filtering():
    token = get_demo_token()
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/carbon?provider=AWS", headers=headers)
    assert res.status_code == 200
    records = res.json()
    assert len(records) > 0
    for r in records:
        assert r["provider"] == "AWS"
        assert "source" in r
        assert "unit" in r
        assert "scope" in r
        assert "record_type" in r
        assert "co2_kg" in r
        assert "co2_mt" in r
        assert r["co2_mt"] == round(r["co2_kg"] / 1000.0, 3)

def test_carbon_factors_registry():
    token = get_demo_token()
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/carbon/factors", headers=headers)
    assert res.status_code == 200
    factors = res.json()
    assert isinstance(factors, list)
    assert len(factors) >= 8

    regions = {f["region"] for f in factors}
    assert "us-east-1" in regions
    assert "europe-north1" in regions

    for f in factors:
        assert f["intensity_g_per_kwh"] > 0
        assert f["unit"] == "gCO2e/kWh"
        assert len(f["source_name"]) > 0
        assert f["source_url"].startswith("http")
        assert f["year"] >= 2023

def test_carbon_csv_import_success():
    token, _ = create_user_and_token("import_cs")
    headers = {"Authorization": f"Bearer {token}"}

    csv_data = (
        "date,provider,region,service,co2_kg,unit,scope,record_type,source\n"
        "2026-10-01,AWS,us-east-1,EC2,15.50,kgCO2e,Scope 2,REPORTED,AWS Carbon Footprint Tool\n"
        "2026-10-02,AWS,us-east-1,S3,4.25,kgCO2e,Scope 2,REPORTED,AWS Carbon Footprint Tool\n"
        "2026-10-03,GCP,europe-north1,GKE,1.25,kgCO2e,Scope 2,REPORTED,Google Cloud Carbon Tool\n"
    )

    files = {"file": ("emissions_report.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}
    res = client.post("/api/carbon/import", headers=headers, files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["imported_rows"] == 3
    assert data["total_co2_kg"] == 21.0
    assert data["total_co2_mt"] == 0.021

    # Verify summary reflects imported data
    sum_res = client.get("/api/carbon/summary", headers=headers)
    assert sum_res.status_code == 200
    summary = sum_res.json()
    assert summary["total_co2_kg"] == 21.0
    assert summary["data_coverage"]["total_records"] == 3

def test_carbon_csv_import_validation_errors():
    token, _ = create_user_and_token("invalid_cs")
    headers = {"Authorization": f"Bearer {token}"}

    # Negative co2_kg value
    bad_csv = (
        "date,provider,region,service,co2_kg,unit,scope,record_type,source\n"
        "2026-10-01,AWS,us-east-1,EC2,-10.00,kgCO2e,Scope 2,REPORTED,AWS Tool\n"
    )
    files = {"file": ("bad_emissions.csv", io.BytesIO(bad_csv.encode("utf-8")), "text/csv")}
    res = client.post("/api/carbon/import", headers=headers, files=files)
    assert res.status_code == 400
    detail = res.json()["detail"]
    assert "errors" in detail
    assert any("non-negative" in err for err in detail["errors"])

    # Verify zero records were written
    list_res = client.get("/api/carbon", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) == 0

def test_carbon_budget_lifecycle_and_status_transitions():
    token, _ = create_user_and_token("budget_cs")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create Carbon Budget with 50 kg target and 80% threshold (40 kg)
    payload = {
        "name": "Q4 Cloud Scope 2 Target",
        "target_kg": 50.0,
        "threshold": 0.80,
        "period": "QUARTERLY",
        "year": 2026
    }
    create_res = client.post("/api/carbon/budgets", headers=headers, json=payload)
    assert create_res.status_code == 201
    b_data = create_res.json()
    b_id = b_data["id"]
    assert b_data["name"] == "Q4 Cloud Scope 2 Target"
    assert b_data["target_kg"] == 50.0
    assert b_data["target_mt"] == 0.05

    # Initial status is OK
    list_res = client.get("/api/carbon/budgets", headers=headers)
    assert list_res.status_code == 200
    budgets = list_res.json()
    assert len(budgets) == 1
    assert budgets[0]["status"] == "OK"
    assert budgets[0]["actual_kg"] == 0.0

    # 2. Import 42.0 kg emissions -> triggers WARNING (84% >= 80%)
    csv_warning = (
        "date,provider,region,service,co2_kg,unit,scope,record_type,source\n"
        "2026-10-01,AWS,us-east-1,EC2,42.00,kgCO2e,Scope 2,REPORTED,AWS Tool\n"
    )
    client.post("/api/carbon/import", headers=headers, files={"file": ("w.csv", io.BytesIO(csv_warning.encode("utf-8")), "text/csv")})

    list_res2 = client.get("/api/carbon/budgets", headers=headers)
    assert list_res2.json()[0]["status"] == "WARNING"
    assert list_res2.json()[0]["percentage_used"] == 84.0

    # 3. Import 15.0 kg more (total 57.0 kg) -> triggers EXCEEDED (114% >= 100%)
    csv_exceeded = (
        "date,provider,region,service,co2_kg,unit,scope,record_type,source\n"
        "2026-10-02,Azure,eastus,VM,15.00,kgCO2e,Scope 2,REPORTED,Azure Tool\n"
    )
    client.post("/api/carbon/import", headers=headers, files={"file": ("e.csv", io.BytesIO(csv_exceeded.encode("utf-8")), "text/csv")})

    list_res3 = client.get("/api/carbon/budgets", headers=headers)
    assert list_res3.json()[0]["status"] == "EXCEEDED"
    assert list_res3.json()[0]["percentage_used"] == 114.0

    # 4. Delete Carbon Budget
    del_res = client.delete(f"/api/carbon/budgets/{b_id}", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"

    list_res4 = client.get("/api/carbon/budgets", headers=headers)
    assert len(list_res4.json()) == 0

def test_empty_organization_carbon_safety():
    token, _ = create_user_and_token("empty_cs")
    headers = {"Authorization": f"Bearer {token}"}

    summary = client.get("/api/carbon/summary", headers=headers).json()
    assert summary["total_co2_kg"] == 0.0
    assert summary["total_co2_mt"] == 0.0
    assert len(summary["provider_breakdown"]) == 0
    assert summary["data_coverage"]["total_records"] == 0

    records = client.get("/api/carbon", headers=headers).json()
    assert records == []

    budgets = client.get("/api/carbon/budgets", headers=headers).json()
    assert budgets == []

def test_multi_tenant_isolation_carbon():
    token_a, _ = create_user_and_token("org_a_cs")
    token_b, _ = create_user_and_token("org_b_cs")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Org A imports carbon records
    csv_a = (
        "date,provider,region,service,co2_kg,unit,scope,record_type,source\n"
        "2026-10-01,AWS,us-east-1,EC2,99.00,kgCO2e,Scope 2,REPORTED,Org A Tool\n"
    )
    client.post("/api/carbon/import", headers=headers_a, files={"file": ("a.csv", io.BytesIO(csv_a.encode("utf-8")), "text/csv")})

    # Org A creates a carbon budget
    b_res = client.post("/api/carbon/budgets", headers=headers_a, json={"name": "Org A Cap", "target_kg": 200.0})
    b_id = b_res.json()["id"]

    # Org B sees ZERO of Org A's emissions
    summary_b = client.get("/api/carbon/summary", headers=headers_b).json()
    assert summary_b["total_co2_kg"] == 0.0

    records_b = client.get("/api/carbon", headers=headers_b).json()
    assert len(records_b) == 0

    # Org B cannot delete Org A's carbon budget (404)
    del_res = client.delete(f"/api/carbon/budgets/{b_id}", headers=headers_b)
    assert del_res.status_code == 404
