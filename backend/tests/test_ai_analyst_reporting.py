import pytest
import uuid
from jose import jwt
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.database import SessionLocal
from app.models import (
    User,
    Organization,
    Report,
    ReportJob,
    ChatSession,
    ChatMessage,
)
from app.auth import hash_password, create_token
from app.services.analyst_service import ALLOWLISTED_TOOLS, get_analyst_tools_registry

client = TestClient(app)

@pytest.fixture
def auth_headers():
    from app.seed import seed
    seed()
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(email="admin@cloudsense.ai").first()
        token = create_token(user.id)
        return {"Authorization": f"Bearer {token}"}
    finally:
        db.close()

@pytest.fixture
def empty_org_headers():
    db = SessionLocal()
    try:
        org = Organization(name=f"Analyst Empty Org {uuid.uuid4().hex[:6]}")
        db.add(org)
        db.flush()
        user = User(
            email=f"analyst_empty_{uuid.uuid4().hex[:8]}@cloudsense.ai",
            password_hash=hash_password("Password123!"),
            role="ADMIN",
            organization_id=org.id,
        )
        db.add(user)
        db.commit()
        token = create_token(user.id)
        return {"Authorization": f"Bearer {token}", "org_id": org.id}
    finally:
        db.close()

def test_allowlisted_tools_registry(auth_headers):
    tools = get_analyst_tools_registry()
    assert len(tools) >= 7
    tool_names = {t["name"] for t in tools}
    assert "get_cost_summary" in tool_names
    assert "get_forecast" in tool_names
    assert "get_anomalies" in tool_names
    assert "get_carbon_summary" in tool_names
    assert "get_optimization_recommendations" in tool_names

    # Check tools endpoint
    res = client.get("/api/assistant/tools", headers=auth_headers)
    assert res.status_code == 200
    endpoint_tools = res.json()
    assert len(endpoint_tools) >= 7

def test_ai_analyst_spend_intent(auth_headers):
    res = client.post(
        "/api/assistant/chat",
        json={"message": "What is our current monthly cloud spend?"},
        headers=auth_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert "answer" in data
    assert "tools_invoked" in data
    assert "get_cost_summary" in data["tools_invoked"]
    assert data["mode"] == "deterministic_grounded_tool_execution"
    assert len(data["citations"]) > 0
    assert "$" in data["answer"]

def test_ai_analyst_forecast_intent(auth_headers):
    res = client.post(
        "/api/assistant/chat",
        json={"message": "What is our projected cloud spend forecast for next month?"},
        headers=auth_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert "tools_invoked" in data
    assert "get_forecast" in data["tools_invoked"]
    assert "projected" in data["answer"].lower() or "forecast" in data["answer"].lower()

def test_ai_analyst_anomalies_intent(auth_headers):
    res = client.post(
        "/api/assistant/chat",
        json={"message": "Are there any recent cost spikes or anomalies?"},
        headers=auth_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert "get_anomalies" in data["tools_invoked"]
    assert "anomal" in data["answer"].lower()

def test_ai_analyst_carbon_intent(auth_headers):
    res = client.post(
        "/api/assistant/chat",
        json={"message": "What is our cloud carbon footprint and greenhouse gas emissions?"},
        headers=auth_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert "get_carbon_summary" in data["tools_invoked"]
    assert "kgco2e" in data["answer"].lower() or "carbon" in data["answer"].lower()

def test_ai_analyst_optimization_intent(auth_headers):
    res = client.post(
        "/api/assistant/chat",
        json={"message": "How can we optimize and save money on idle or over-provisioned instances?"},
        headers=auth_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert "get_optimization_recommendations" in data["tools_invoked"]
    assert "saving" in data["answer"].lower() or "recommendation" in data["answer"].lower()

def test_ai_analyst_missing_data_acknowledgement(empty_org_headers):
    # Empty organization queries spend
    res_spend = client.post(
        "/api/assistant/chat",
        json={"message": "Show me our cloud spend"},
        headers=empty_org_headers,
    )
    assert res_spend.status_code == 200
    data_spend = res_spend.json()
    assert data_spend["missing_data_acknowledged"] is True
    assert "zero" in data_spend["answer"].lower() or "no records" in data_spend["answer"].lower()

    # Empty organization queries carbon
    res_carbon = client.post(
        "/api/assistant/chat",
        json={"message": "What are our carbon emissions?"},
        headers=empty_org_headers,
    )
    assert res_carbon.status_code == 200
    data_carbon = res_carbon.json()
    assert data_carbon["missing_data_acknowledged"] is True
    assert "zero" in data_carbon["answer"].lower() or "no recorded" in data_carbon["answer"].lower()

def test_multi_tenant_isolation_ai_analyst(auth_headers, empty_org_headers):
    # Org A (seeded) has spend > $0
    res_a = client.post(
        "/api/assistant/chat",
        json={"message": "What is our cloud spend?"},
        headers=auth_headers,
    )
    assert res_a.status_code == 200
    assert res_a.json()["missing_data_acknowledged"] is False

    # Org B (empty) has 0 spend and acknowledges missing data
    res_b = client.post(
        "/api/assistant/chat",
        json={"message": "What is our cloud spend?"},
        headers=empty_org_headers,
    )
    assert res_b.status_code == 200
    assert res_b.json()["missing_data_acknowledged"] is True

def test_pdf_report_generation_and_reconciliation(auth_headers):
    payload = {
        "report_type": "EXECUTIVE_DIGEST",
        "format": "PDF",
        "period_days": 30,
    }
    res = client.post("/api/reports/generate", json=payload, headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["format"] == "PDF"
    assert data["file_size_bytes"] > 0
    assert "download_url" in data
    report_id = data["id"]

    # Verify download endpoint
    dl_res = client.get(f"/api/reports/{report_id}/download", headers=auth_headers)
    assert dl_res.status_code == 200
    assert dl_res.headers["content-type"] == "application/pdf"
    assert len(dl_res.content) > 1000  # valid PDF binary

def test_csv_report_generation_and_formula_injection(auth_headers):
    payload = {
        "report_type": "COST_BREAKDOWN",
        "format": "CSV",
        "period_days": 30,
    }
    res = client.post("/api/reports/generate", json=payload, headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["format"] == "CSV"
    report_id = data["id"]

    # Download CSV
    dl_res = client.get(f"/api/reports/{report_id}/download", headers=auth_headers)
    assert dl_res.status_code == 200
    csv_text = dl_res.text
    assert "# CloudSense AI — Cost Breakdown Report" in csv_text
    assert "Provider,Current Spend ($),Prior Spend ($),Variance (%)" in csv_text
    # Verify no unescaped formula injection characters at start of lines
    lines = csv_text.splitlines()
    for line in lines:
        if line and not line.startswith("#"):
            first_cell = line.split(",")[0]
            # Ensure cell does not start with executable formula
            assert not (first_cell.startswith("=") or first_cell.startswith("+") or first_cell.startswith("-") and not first_cell.lstrip("-").replace(".", "").isdigit())

def test_report_download_authorization(auth_headers, empty_org_headers):
    # Org A generates report
    gen_res = client.post(
        "/api/reports/generate",
        json={"format": "PDF", "period_days": 30},
        headers=auth_headers,
    )
    assert gen_res.status_code == 200
    org_a_report_id = gen_res.json()["id"]

    # Org B attempts to download Org A's report
    cross_res = client.get(f"/api/reports/{org_a_report_id}/download", headers=empty_org_headers)
    assert cross_res.status_code == 404

def test_background_digest_jobs_lifecycle(auth_headers):
    payload = {
        "job_type": "EXECUTIVE_DIGEST",
        "delivery_channel": "EMAIL_SIMULATED",
        "period_days": 30,
    }
    schedule_res = client.post("/api/reports/digest/schedule", json=payload, headers=auth_headers)
    assert schedule_res.status_code == 200
    job_data = schedule_res.json()

    assert job_data["status"] == "SUCCEEDED"
    assert job_data["delivery_channel"] == "EMAIL_SIMULATED"
    # Transparent disclosure of simulated delivery
    assert "No SMTP server configured" in job_data["delivery_status"]
    assert job_data["report_id"] is not None

    # List jobs
    list_res = client.get("/api/reports/jobs", headers=auth_headers)
    assert list_res.status_code == 200
    jobs = list_res.json()
    assert len(jobs) >= 1
    assert any(j["id"] == job_data["id"] for j in jobs)

def test_ai_analyst_actionable_task_execution(auth_headers):
    # 1. Command: Run anomaly detection scan
    res_scan = client.post(
        "/api/assistant/chat",
        json={"message": "Please run anomaly detection scan on our cloud billing"},
        headers=auth_headers,
    )
    assert res_scan.status_code == 200
    data_scan = res_scan.json()
    assert data_scan["task_executed"] is True
    assert data_scan["action_performed"] == "run_anomaly_detection"
    assert "Task Completed: Anomaly Detection Scan Executed" in data_scan["answer"]
    assert "run_anomaly_detection" in data_scan["tools_invoked"]

    # 2. Command: Create budget
    res_budget = client.post(
        "/api/assistant/chat",
        json={"message": "Create budget for AWS amount $4500"},
        headers=auth_headers,
    )
    assert res_budget.status_code == 200
    data_b = res_budget.json()
    assert data_b["task_executed"] is True
    assert data_b["action_performed"] == "create_budget"
    assert "Task Completed: Budget Provisioned" in data_b["answer"]
    assert "4,500" in data_b["answer"]

    # 3. Command: Generate executive report
    res_rep = client.post(
        "/api/assistant/chat",
        json={"message": "Generate executive finops report pdf for 30 days"},
        headers=auth_headers,
    )
    assert res_rep.status_code == 200
    data_r = res_rep.json()
    assert data_r["task_executed"] is True
    assert data_r["action_performed"] == "generate_report"
    assert "Task Completed: Executive FinOps Report Compiled" in data_r["answer"]

    # 4. Command: Mark all alerts as read
    res_clear = client.post(
        "/api/assistant/chat",
        json={"message": "Please mark all alerts as read"},
        headers=auth_headers,
    )
    assert res_clear.status_code == 200
    data_c = res_clear.json()
    assert data_c["task_executed"] is True
    assert data_c["action_performed"] == "mark_all_alerts_read"
    assert "Task Completed: Alerts Acknowledged" in data_c["answer"]

