import uuid
import io
from fastapi.testclient import TestClient
from app.main import app
from app.models import CostRecord, BillingImport
from app.database import SessionLocal

client = TestClient(app)

def create_user_and_token(prefix="user"):
    email = f"{prefix}_{uuid.uuid4().hex[:8]}@cloudsense.ai"
    res = client.post("/api/auth/register", json={"email": email, "password": "Password123!"})
    assert res.status_code == 200
    return res.json()["access_token"]

def test_valid_billing_csv_import():
    token = create_user_and_token("valid_import")
    headers = {"Authorization": f"Bearer {token}"}
    
    csv_content = (
        "date,provider,service,amount,region,resource_id,currency\n"
        "2026-03-01,AWS,EC2,150.50,us-east-1,i-12345678,USD\n"
        "2026-03-02,Azure,Virtual Machines,85.25,eastus,vm-001,USD\n"
        "2026-03-03,GCP,Compute Engine,42.10,us-central1,inst-999,USD\n"
    )
    
    files = {"file": ("march_billing.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    res = client.post("/api/billing/import", headers=headers, files=files)
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "COMPLETED"
    assert data["total_rows"] == 3
    assert data["imported_rows"] == 3
    assert data["error_count"] == 0
    assert "import_id" in data
    
    # Verify records in database
    db = SessionLocal()
    try:
        records = db.query(CostRecord).filter_by(import_id=data["import_id"]).all()
        assert len(records) == 3
        providers = {r.provider for r in records}
        assert providers == {"AWS", "AZURE", "GCP"}
    finally:
        db.close()

def test_duplicate_file_rejection():
    token = create_user_and_token("dup_import")
    headers = {"Authorization": f"Bearer {token}"}
    
    csv_content = (
        "date,provider,service,amount\n"
        f"2026-03-10,AWS,RDS,{uuid.uuid4().int % 500}.00\n"
    )
    files1 = {"file": ("invoice.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    res1 = client.post("/api/billing/import", headers=headers, files=files1)
    assert res1.status_code == 201
    import_id = res1.json()["import_id"]
    
    # Upload exact same file again
    files2 = {"file": ("invoice.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    res2 = client.post("/api/billing/import", headers=headers, files=files2)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["status"] == "DUPLICATE"
    assert data2["duplicate"] is True
    assert data2["imported_rows"] == 0
    assert "Duplicate file detected" in data2["message"]

def test_idempotency_key_replay():
    token = create_user_and_token("idempotent")
    key = f"key-{uuid.uuid4().hex}"
    headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": key}
    
    csv_content = (
        "date,provider,service,amount\n"
        "2026-03-15,AWS,S3,12.50\n"
        "2026-03-16,AWS,Lambda,4.20\n"
    )
    files1 = {"file": ("batch.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    res1 = client.post("/api/billing/import", headers=headers, files=files1)
    assert res1.status_code == 201
    orig_id = res1.json()["import_id"]
    
    # Second request with the same idempotency key
    files2 = {"file": ("batch.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    res2 = client.post("/api/billing/import", headers=headers, files=files2)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["idempotent_replay"] is True
    assert data2["import_id"] == orig_id
    assert data2["imported_rows"] == 2

def test_invalid_rows_reporting_and_zero_partial_writes():
    token = create_user_and_token("invalid_rows")
    headers = {"Authorization": f"Bearer {token}"}
    
    csv_content = (
        "date,provider,service,amount\n"
        "2026-03-01,AWS,EC2,50.00\n"              # Line 2: valid
        "not-a-date,Azure,VM,25.00\n"             # Line 3: invalid date
        "2026-03-02,GCP,Storage,10.00\n"          # Line 4: valid
        "2026-03-03,AWS,RDS,-15.00\n"             # Line 5: negative amount
        "2026-03-04,AWS,,30.00\n"                 # Line 6: missing service
    )
    
    files = {"file": ("corrupt.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    res = client.post("/api/billing/import", headers=headers, files=files)
    assert res.status_code == 400
    data = res.json()
    assert data["status"] == "FAILED"
    assert data["imported_rows"] == 0
    assert data["error_count"] == 3
    
    error_lines = {e["line"]: e["error"] for e in data["errors"]}
    assert 3 in error_lines
    assert "Invalid date" in error_lines[3]
    assert 5 in error_lines
    assert "non-negative number" in error_lines[5]
    assert 6 in error_lines
    assert "required field 'service'" in error_lines[6]
    
    # Assert transactional guarantee: ZERO rows were written to CostRecord
    db = SessionLocal()
    try:
        records = db.query(CostRecord).filter_by(import_id=data["import_id"]).all()
        assert len(records) == 0
    finally:
        db.close()

def test_empty_csv_rejection():
    token = create_user_and_token("empty_csv")
    headers = {"Authorization": f"Bearer {token}"}
    
    files = {"file": ("empty.csv", io.BytesIO(b""), "text/csv")}
    res = client.post("/api/billing/import", headers=headers, files=files)
    assert res.status_code == 400
    assert res.json()["status"] == "FAILED"
    assert "empty" in res.json()["errors"][0]["error"].lower()

def test_missing_required_headers():
    token = create_user_and_token("headers_csv")
    headers = {"Authorization": f"Bearer {token}"}
    
    csv_content = "date,provider,amount\n2026-03-01,AWS,50.00\n"
    files = {"file": ("missing_service.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    res = client.post("/api/billing/import", headers=headers, files=files)
    assert res.status_code == 400
    assert "Missing required column" in res.json()["errors"][0]["error"]

def test_multi_tenant_isolation_billing_imports():
    token_a = create_user_and_token("tenant_a")
    token_b = create_user_and_token("tenant_b")
    
    csv_content = "date,provider,service,amount\n2026-03-01,AWS,EC2,100.00\n"
    files = {"file": ("tenant_a.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    
    # Tenant A imports
    res_a = client.post("/api/billing/import", headers={"Authorization": f"Bearer {token_a}"}, files=files)
    assert res_a.status_code == 201
    import_id_a = res_a.json()["import_id"]
    
    # Tenant B queries imports list
    list_b = client.get("/api/billing/imports", headers={"Authorization": f"Bearer {token_b}"})
    assert list_b.status_code == 200
    ids_b = [x["id"] for x in list_b.json()]
    assert import_id_a not in ids_b
    
    # Tenant B queries Tenant A's import ID directly -> 404
    detail_b = client.get(f"/api/billing/imports/{import_id_a}", headers={"Authorization": f"Bearer {token_b}"})
    assert detail_b.status_code == 404
