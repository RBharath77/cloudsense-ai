import uuid
import io
import csv
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.models import CostRecord
from app.database import SessionLocal

client = TestClient(app)

def create_user_and_token(prefix="cost_user"):
    email = f"{prefix}_{uuid.uuid4().hex[:8]}@cloudsense.ai"
    res = client.post("/api/auth/register", json={"email": email, "password": "Password123!"})
    assert res.status_code == 200
    return res.json()["access_token"]

def test_reconciliation_invariant():
    """Invariant: API total_cost == sum(breakdown items) == CSV export total."""
    token = create_user_and_token("reconcile")
    headers = {"Authorization": f"Bearer {token}"}
    
    csv_content = (
        "date,provider,service,amount,region,resource_id,currency\n"
        "2026-03-01,AWS,EC2,120.50,us-east-1,i-01,USD\n"
        "2026-03-02,AWS,RDS,80.25,us-east-1,db-01,USD\n"
        "2026-03-03,GCP,Compute Engine,45.75,us-central1,inst-01,USD\n"
        "2026-03-04,Azure,Storage,23.50,eastus,st-01,USD\n"
    )
    res_import = client.post(
        "/api/billing/import",
        headers=headers,
        files={"file": ("batch.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    )
    assert res_import.status_code == 201
    expected_sum = 120.50 + 80.25 + 45.75 + 23.50  # 270.00
    
    # 1. API Summary
    res_sum = client.get("/api/costs/summary", headers=headers)
    assert res_sum.status_code == 200
    summary_data = res_sum.json()
    api_total = summary_data["total_cost"]
    assert round(api_total, 2) == round(expected_sum, 2)
    
    items_sum = sum(item["cost"] for item in summary_data["items"])
    assert round(items_sum, 2) == round(expected_sum, 2)
    
    # 2. CSV Export
    res_csv = client.get("/api/costs/export", headers=headers)
    assert res_csv.status_code == 200
    assert "attachment; filename=" in res_csv.headers["content-disposition"]
    assert res_csv.headers["x-total-cost"] == f"{expected_sum:.2f}"
    assert int(res_csv.headers["x-record-count"]) == 4
    
    # Parse CSV content and sum amount column
    csv_reader = csv.DictReader(io.StringIO(res_csv.text))
    csv_total = sum(float(row["amount"]) for row in csv_reader)
    assert round(csv_total, 2) == round(expected_sum, 2)
    
    # Invariant: 100% exact match
    assert api_total == items_sum == csv_total

def test_cost_filtering_and_grouping():
    token = create_user_and_token("filtering")
    headers = {"Authorization": f"Bearer {token}"}
    
    csv_content = (
        "date,provider,service,amount,region,resource_id\n"
        "2026-03-01,AWS,EC2,100.00,us-east-1,i-100\n"
        "2026-03-02,AWS,RDS,50.00,us-west-2,db-200\n"
        "2026-03-03,GCP,Compute Engine,75.00,us-central1,g-300\n"
    )
    client.post(
        "/api/billing/import",
        headers=headers,
        files={"file": ("cloud.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    )
    
    # Filter by AWS
    res_aws = client.get("/api/costs/summary?provider=AWS", headers=headers)
    assert res_aws.status_code == 200
    data_aws = res_aws.json()
    assert data_aws["total_cost"] == 150.00
    assert data_aws["record_count"] == 2
    for item in data_aws["items"]:
        assert item["key"] == "AWS"
        
    # Group by service
    res_svc = client.get("/api/costs/summary?provider=AWS&group_by=service", headers=headers)
    assert res_svc.status_code == 200
    data_svc = res_svc.json()
    svc_keys = {item["key"]: item["cost"] for item in data_svc["items"]}
    assert svc_keys["EC2"] == 100.00
    assert svc_keys["RDS"] == 50.00
    
    # Daily costs
    res_daily = client.get("/api/costs?provider=AWS", headers=headers)
    assert res_daily.status_code == 200
    daily_items = res_daily.json()
    assert len(daily_items) == 2
    assert daily_items[0]["cost"] == 100.00
    assert daily_items[1]["cost"] == 50.00

def test_cost_data_lineage():
    token = create_user_and_token("lineage")
    headers = {"Authorization": f"Bearer {token}"}
    
    csv_content = (
        "date,provider,service,amount,region\n"
        "2026-03-01,AWS,S3,12.50,us-east-1\n"
    )
    import_res = client.post(
        "/api/billing/import",
        headers=headers,
        files={"file": ("s3_billing.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    )
    import_id = import_res.json()["import_id"]
    
    # Call lineage endpoint
    res_lineage = client.get("/api/costs/lineage", headers=headers)
    assert res_lineage.status_code == 200
    lineage_data = res_lineage.json()
    
    assert lineage_data["total_cost"] == 12.50
    assert lineage_data["record_count"] == 1
    assert lineage_data["import_coverage_count"] >= 1
    
    found_import = False
    for imp in lineage_data["contributing_imports"]:
        if imp["id"] == import_id:
            assert imp["filename"] == "s3_billing.csv"
            assert imp["status"] == "COMPLETED"
            found_import = True
    assert found_import is True

def test_formula_injection_sanitization_in_csv_export():
    token = create_user_and_token("injection_test")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Formula characters in provider, service, region
    csv_content = (
        "date,provider,service,amount,region\n"
        "2026-03-01,=cmd|' /C calc'!A0,+sum(1+1),55.00,@malicious_region\n"
    )
    import_res = client.post(
        "/api/billing/import",
        headers=headers,
        files={"file": ("payload.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    )
    assert import_res.status_code == 201
    
    export_res = client.get("/api/costs/export", headers=headers)
    assert export_res.status_code == 200
    csv_text = export_res.text
    
    # Ensure formula characters are sanitized with leading single quote
    assert "'=cmd|" in csv_text or "'+sum" in csv_text or "'@malicious" in csv_text

def test_empty_org_costs_and_dashboard():
    token = create_user_and_token("empty_org")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Cost summary for empty org
    res = client.get("/api/costs/summary", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_cost"] == 0.0
    assert data["previous_cost"] == 0.0
    assert data["change_percentage"] is None
    assert data["items"] == []
    assert data["record_count"] == 0
    
    # CSV export for empty org
    res_csv = client.get("/api/costs/export", headers=headers)
    assert res_csv.status_code == 200
    assert res_csv.headers["x-total-cost"] == "0.00"
    assert res_csv.headers["x-record-count"] == "0"
    
    # Lineage for empty org
    res_lineage = client.get("/api/costs/lineage", headers=headers)
    assert res_lineage.status_code == 200
    assert res_lineage.json()["contributing_imports"] == []

def test_multi_tenant_isolation_costs():
    token_a = create_user_and_token("tenant_a")
    token_b = create_user_and_token("tenant_b")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}
    
    csv_a = "date,provider,service,amount\n2026-03-01,AWS,EC2,999.00\n"
    client.post(
        "/api/billing/import",
        headers=headers_a,
        files={"file": ("a.csv", io.BytesIO(csv_a.encode("utf-8")), "text/csv")}
    )
    
    # Org B should see 0.00
    res_b = client.get("/api/costs/summary", headers=headers_b)
    assert res_b.status_code == 200
    assert res_b.json()["total_cost"] == 0.0
    assert res_b.json()["items"] == []
    
    # Org B export should have 0 records
    export_b = client.get("/api/costs/export", headers=headers_b)
    assert export_b.status_code == 200
    assert export_b.headers["x-total-cost"] == "0.00"
    assert export_b.headers["x-record-count"] == "0"
