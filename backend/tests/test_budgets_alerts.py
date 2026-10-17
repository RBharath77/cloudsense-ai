import uuid
import io
from fastapi.testclient import TestClient
from app.main import app
from app.models import Budget, Alert, CloudResource
from app.database import SessionLocal

client = TestClient(app)

def create_user_and_token(prefix="ba_user"):
    email = f"{prefix}_{uuid.uuid4().hex[:8]}@cloudsense.ai"
    res = client.post("/api/auth/register", json={"email": email, "password": "Password123!"})
    assert res.status_code == 200
    return res.json()["access_token"]

def test_budget_crud_lifecycle():
    token = create_user_and_token("crud_b")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create Budget
    payload = {
        "name": "Production EC2 Cap",
        "scope": "SERVICE",
        "target": "EC2",
        "amount": 2500.0,
        "threshold": 0.8,
        "period": "MONTHLY"
    }
    create_res = client.post("/api/budgets", headers=headers, json=payload)
    assert create_res.status_code == 201
    b_data = create_res.json()
    b_id = b_data["id"]
    assert b_data["name"] == "Production EC2 Cap"
    assert b_data["amount"] == 2500.0
    assert b_data["threshold"] == 0.8
    assert b_data["status"] == "OK"

    # 2. List Budgets
    list_res = client.get("/api/budgets", headers=headers)
    assert list_res.status_code == 200
    budgets = list_res.json()
    assert len(budgets) == 1
    assert budgets[0]["id"] == b_id

    # 3. Get Detail
    detail_res = client.get(f"/api/budgets/{b_id}", headers=headers)
    assert detail_res.status_code == 200
    assert detail_res.json()["target"] == "EC2"
    assert "daily_trend" in detail_res.json()

    # 4. Update Budget
    update_res = client.put(f"/api/budgets/{b_id}", headers=headers, json={"amount": 3000.0, "threshold": 0.85})
    assert update_res.status_code == 200
    assert update_res.json()["amount"] == 3000.0
    assert update_res.json()["threshold"] == 0.85

    # 5. Delete Budget
    del_res = client.delete(f"/api/budgets/{b_id}", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"

    # Verify 404 after delete
    get_after = client.get(f"/api/budgets/{b_id}", headers=headers)
    assert get_after.status_code == 404

def test_budget_validation_errors():
    token = create_user_and_token("val_b")
    headers = {"Authorization": f"Bearer {token}"}

    # Negative or 0 amount
    res1 = client.post("/api/budgets", headers=headers, json={"amount": 0, "threshold": 0.8})
    assert res1.status_code == 400

    # Invalid threshold > 1.0
    res2 = client.post("/api/budgets", headers=headers, json={"amount": 100, "threshold": 1.5})
    assert res2.status_code == 400

    # Invalid scope
    res3 = client.post("/api/budgets", headers=headers, json={"amount": 100, "threshold": 0.8, "scope": "INVALID"})
    assert res3.status_code == 400

def test_budget_spend_evaluation_and_status_transitions():
    token = create_user_and_token("eval_b")
    headers = {"Authorization": f"Bearer {token}"}

    # Create budget for AWS with limit $100 and threshold 0.8 (80%)
    b_res = client.post("/api/budgets", headers=headers, json={
        "name": "AWS Budget",
        "scope": "PROVIDER",
        "target": "AWS",
        "amount": 100.0,
        "threshold": 0.8,
        "period": "ALL"
    })
    assert b_res.status_code == 201
    b_id = b_res.json()["id"]
    assert b_res.json()["status"] == "OK"

    # Ingest costs: $50 (50% -> OK)
    csv_1 = "date,provider,service,amount\n2026-03-01,AWS,EC2,50.00\n"
    client.post("/api/billing/import", headers=headers, files={"file": ("1.csv", io.BytesIO(csv_1.encode()), "text/csv")})

    eval_1 = client.get(f"/api/budgets/{b_id}", headers=headers).json()
    assert eval_1["actual_spend"] == 50.0
    assert eval_1["status"] == "OK"

    # Ingest costs: +$35 -> $85 (85% -> WARNING)
    csv_2 = "date,provider,service,amount\n2026-03-02,AWS,S3,35.00\n"
    client.post("/api/billing/import", headers=headers, files={"file": ("2.csv", io.BytesIO(csv_2.encode()), "text/csv")})

    eval_2 = client.get(f"/api/budgets/{b_id}", headers=headers).json()
    assert eval_2["actual_spend"] == 85.0
    assert eval_2["status"] == "WARNING"

    # Ingest costs: +$25 -> $110 (110% -> EXCEEDED)
    csv_3 = "date,provider,service,amount\n2026-03-03,AWS,RDS,25.00\n"
    client.post("/api/billing/import", headers=headers, files={"file": ("3.csv", io.BytesIO(csv_3.encode()), "text/csv")})

    eval_3 = client.get(f"/api/budgets/{b_id}", headers=headers).json()
    assert eval_3["actual_spend"] == 110.0
    assert eval_3["status"] == "EXCEEDED"

def test_alert_evaluation_and_deduplication():
    token = create_user_and_token("dedup_alerts")
    headers = {"Authorization": f"Bearer {token}"}

    # Set up budget and exceeded spend
    client.post("/api/budgets", headers=headers, json={
        "name": "Exceeded Alert Test",
        "scope": "ORGANIZATION",
        "target": "ALL",
        "amount": 50.0,
        "threshold": 0.8,
        "period": "ALL"
    })
    csv_data = "date,provider,service,amount\n2026-03-01,AWS,EC2,75.00\n"
    client.post("/api/billing/import", headers=headers, files={"file": ("spend.csv", io.BytesIO(csv_data.encode()), "text/csv")})

    # First evaluation -> creates alert
    eval_res_1 = client.post("/api/alerts/evaluate", headers=headers)
    assert eval_res_1.status_code == 200
    res_1 = eval_res_1.json()
    assert res_1["created_alerts"] == 1
    assert res_1["updated_alerts"] == 0

    alerts_list_1 = client.get("/api/alerts", headers=headers).json()
    assert len(alerts_list_1) == 1
    assert alerts_list_1[0]["type"] == "BUDGET_EXCEEDED"
    assert alerts_list_1[0]["severity"] == "CRITICAL"

    # Second evaluation -> must NOT duplicate! Updates existing alert.
    eval_res_2 = client.post("/api/alerts/evaluate", headers=headers)
    assert eval_res_2.status_code == 200
    res_2 = eval_res_2.json()
    assert res_2["created_alerts"] == 0
    assert res_2["updated_alerts"] == 1

    alerts_list_2 = client.get("/api/alerts", headers=headers).json()
    assert len(alerts_list_2) == 1  # Still exactly 1 alert! Deduplication invariant confirmed.

def test_alert_triage_workflows():
    token = create_user_and_token("triage_alerts")
    headers = {"Authorization": f"Bearer {token}"}

    # Trigger alert
    client.post("/api/budgets", headers=headers, json={"amount": 10.0, "threshold": 0.5, "period": "ALL"})
    client.post("/api/billing/import", headers=headers, files={"file": ("b.csv", io.BytesIO(b"date,provider,service,amount\n2026-03-01,AWS,EC2,20.0\n"), "text/csv")})
    client.post("/api/alerts/evaluate", headers=headers)

    alerts = client.get("/api/alerts", headers=headers).json()
    assert len(alerts) >= 1
    alert_id = alerts[0]["id"]
    assert alerts[0]["read"] is False

    # Mark single alert as read
    read_res = client.post(f"/api/alerts/{alert_id}/read", headers=headers)
    assert read_res.status_code == 200

    unread_alerts = client.get("/api/alerts?unread=true", headers=headers).json()
    assert all(a["id"] != alert_id for a in unread_alerts)

    # Mark all as read
    mark_all_res = client.post("/api/alerts/read-all", headers=headers)
    assert mark_all_res.status_code == 200

    # Delete alert
    del_res = client.delete(f"/api/alerts/{alert_id}", headers=headers)
    assert del_res.status_code == 200

    after_del = client.get("/api/alerts", headers=headers).json()
    assert all(a["id"] != alert_id for a in after_del)

def test_tag_governance_and_resource_compliance():
    token = create_user_and_token("tag_gov")
    headers = {"Authorization": f"Bearer {token}"}

    # Seeding creates resources in org
    gov_res = client.get("/api/governance/tags", headers=headers)
    assert gov_res.status_code == 200
    data = gov_res.json()
    assert "compliance_rate" in data
    assert "required_tags" in data

    # Add a mock resource for this user
    db = SessionLocal()
    from app.models import User, CloudResource
    from app.config import settings
    from jose import jwt
    try:
        uid = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])["sub"]
        u = db.get(User, uid)
        assert u is not None
        org_id = u.organization_id
        assert org_id is not None
        res = CloudResource(
            organization_id=org_id,
            account_id="acc-test",
            provider="AWS",
            name="untagged-server",
            type="compute",
            region="us-east-1",
            monthly_cost=150.0,
            tags=None
        )
        db.add(res)
        db.commit()
        db.refresh(res)
        res_id = res.id
    finally:
        db.close()

    # Re-evaluate
    gov_after = client.get("/api/governance/tags", headers=headers).json()
    assert gov_after["total_resources"] >= 1
    assert gov_after["untagged_count"] >= 1

    # Update tags on resource
    update_tags_res = client.put(f"/api/resources/{res_id}/tags", headers=headers, json={
        "tags": {
            "Environment": "Production",
            "Owner": "FinOps",
            "CostCenter": "CC-99",
            "Project": "CloudSense"
        }
    })
    assert update_tags_res.status_code == 200
    assert update_tags_res.json()["tags"]["Environment"] == "Production"

    # Re-evaluate governance: compliant count increased!
    gov_final = client.get("/api/governance/tags", headers=headers).json()
    assert gov_final["compliant_count"] >= 1

def test_empty_organization_budgets_and_alerts():
    token = create_user_and_token("empty_b_a")
    headers = {"Authorization": f"Bearer {token}"}

    # Budgets
    b_res = client.get("/api/budgets", headers=headers)
    assert b_res.status_code == 200
    assert b_res.json() == []

    # Alerts
    a_res = client.get("/api/alerts", headers=headers)
    assert a_res.status_code == 200
    assert a_res.json() == []

    # Evaluate on empty org
    eval_res = client.post("/api/alerts/evaluate", headers=headers)
    assert eval_res.status_code == 200
    assert eval_res.json()["created_alerts"] == 0

    # Tag Governance on empty org
    gov_res = client.get("/api/governance/tags", headers=headers)
    assert gov_res.status_code == 200
    assert gov_res.json()["total_resources"] == 0
    assert gov_res.json()["compliance_rate"] == 100.0

def test_multi_tenant_isolation_budgets_alerts():
    token_a = create_user_and_token("tenant_a_b")
    token_b = create_user_and_token("tenant_b_b")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Org A creates budget
    res_a = client.post("/api/budgets", headers=headers_a, json={"amount": 5000.0, "threshold": 0.8})
    b_id = res_a.json()["id"]

    # Org B cannot view Org A's budget
    get_b = client.get(f"/api/budgets/{b_id}", headers=headers_b)
    assert get_b.status_code == 404

    # Org B cannot update or delete Org A's budget
    put_b = client.put(f"/api/budgets/{b_id}", headers=headers_b, json={"amount": 9999.0})
    assert put_b.status_code == 404
    del_b = client.delete(f"/api/budgets/{b_id}", headers=headers_b)
    assert del_b.status_code == 404
