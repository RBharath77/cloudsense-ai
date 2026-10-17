import pytest
import uuid
import json
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import User, Organization, CloudResource, SystemJobExecution, WebhookEndpoint, AutomatedAction
from app.auth import hash_password, create_token
from app.services.webhook_service import compute_webhook_signature

client = TestClient(app)

@pytest.fixture
def setup_tenants():
    db = SessionLocal()
    try:
        org_a = Organization(name=f"Ops Org A {uuid.uuid4().hex[:6]}")
        org_b = Organization(name=f"Ops Org B {uuid.uuid4().hex[:6]}")
        db.add_all([org_a, org_b])
        db.flush()

        admin_a = User(
            email=f"admin_ops_a_{uuid.uuid4().hex[:6]}@test.com",
            password_hash=hash_password("Pass123!"),
            role="ADMIN",
            organization_id=org_a.id,
        )
        finops_a = User(
            email=f"finops_ops_a_{uuid.uuid4().hex[:6]}@test.com",
            password_hash=hash_password("Pass123!"),
            role="FINOPS_ENGINEER",
            organization_id=org_a.id,
        )
        viewer_a = User(
            email=f"viewer_ops_a_{uuid.uuid4().hex[:6]}@test.com",
            password_hash=hash_password("Pass123!"),
            role="VIEWER",
            organization_id=org_a.id,
        )
        admin_b = User(
            email=f"admin_ops_b_{uuid.uuid4().hex[:6]}@test.com",
            password_hash=hash_password("Pass123!"),
            role="ADMIN",
            organization_id=org_b.id,
        )
        db.add_all([admin_a, finops_a, viewer_a, admin_b])

        # Seed mock resources for Org A
        res1 = CloudResource(
            organization_id=org_a.id,
            account_id="acc-1234",
            provider="AWS",
            name="i-0abcd1234ef567890",
            type="AmazonEC2",
            region="us-east-1",
            monthly_cost=85.0,
            status="running",
        )
        res2 = CloudResource(
            organization_id=org_a.id,
            account_id="acc-1234",
            provider="AWS",
            name="vol-0987654321fedcba0",
            type="AmazonEBS",
            region="us-east-1",
            monthly_cost=25.0,
            status="available",
        )
        db.add_all([res1, res2])
        db.commit()

        token_admin_a = create_token(admin_a.id)
        token_finops_a = create_token(finops_a.id)
        token_viewer_a = create_token(viewer_a.id)
        token_admin_b = create_token(admin_b.id)

        return {
            "org_a": org_a.id,
            "org_b": org_b.id,
            "admin_a_headers": {"Authorization": f"Bearer {token_admin_a}"},
            "finops_a_headers": {"Authorization": f"Bearer {token_finops_a}"},
            "viewer_a_headers": {"Authorization": f"Bearer {token_viewer_a}"},
            "admin_b_headers": {"Authorization": f"Bearer {token_admin_b}"},
        }
    finally:
        db.close()


def test_health_and_detailed_diagnostics(setup_tenants):
    # 1. Public Health Check
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ["ok", "healthy", "degraded"]
    assert "latency_ms" in data
    assert "uptime_seconds" in data
    assert data["database"] == "healthy"

    # 2. Detailed Health Check (Admin authorized)
    admin_headers = setup_tenants["admin_a_headers"]
    res_det = client.get("/health/detailed", headers=admin_headers)
    assert res_det.status_code == 200
    det_data = res_det.json()
    assert "subsystems" in det_data
    assert "database" in det_data["subsystems"]
    assert "background_workers" in det_data["subsystems"]
    assert "memory" in det_data["subsystems"]

    # 3. Detailed Health Check (Viewer forbidden)
    viewer_headers = setup_tenants["viewer_a_headers"]
    res_viewer = client.get("/health/detailed", headers=viewer_headers)
    assert res_viewer.status_code == 403


def test_prometheus_metrics_export():
    res = client.get("/metrics")
    assert res.status_code == 200
    assert "text/plain" in res.headers["content-type"]
    text_content = res.text
    assert "cloudsense_health_status" in text_content
    assert "cloudsense_uptime_seconds" in text_content
    assert "cloudsense_cost_records_total" in text_content
    assert "cloudsense_database_latency_seconds" in text_content


def test_system_observability_api(setup_tenants):
    headers = setup_tenants["admin_a_headers"]
    res = client.get("/api/system/observability", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "db_latency_ms" in data
    assert "uptime_seconds" in data
    assert "pending_actions_count" in data
    assert "realized_monthly_savings_usd" in data
    assert "recent_jobs" in data


def test_background_jobs_execution_lifecycle(setup_tenants):
    headers = setup_tenants["admin_a_headers"]

    # Trigger Anomaly Sweep Job
    res_sweep = client.post(
        "/api/jobs/trigger",
        json={"job_type": "ANOMALY_SWEEP", "payload": {"contamination": 0.05}},
        headers=headers,
    )
    assert res_sweep.status_code == 200, res_sweep.text
    sweep_job = res_sweep.json()
    assert sweep_job["status"] == "SUCCEEDED"
    assert sweep_job["job_type"] == "ANOMALY_SWEEP"
    assert sweep_job["execution_time_ms"] >= 0
    assert sweep_job["result"] is not None

    # Trigger Budget Audit Job
    res_audit = client.post(
        "/api/jobs/trigger",
        json={"job_type": "BUDGET_AUDIT"},
        headers=headers,
    )
    assert res_audit.status_code == 200
    audit_job = res_audit.json()
    assert audit_job["status"] == "SUCCEEDED"
    assert audit_job["job_type"] == "BUDGET_AUDIT"

    # Trigger Storage Orphan Scan Job
    res_storage = client.post(
        "/api/jobs/trigger",
        json={"job_type": "STORAGE_ORPHAN_SCAN"},
        headers=headers,
    )
    assert res_storage.status_code == 200
    storage_job = res_storage.json()
    assert storage_job["status"] == "SUCCEEDED"
    assert "potential_monthly_savings_usd" in storage_job["result"]

    # List jobs
    res_list = client.get("/api/jobs", headers=headers)
    assert res_list.status_code == 200
    job_ids = [j["id"] for j in res_list.json()]
    assert sweep_job["id"] in job_ids

    # Trigger invalid job type
    res_invalid = client.post(
        "/api/jobs/trigger",
        json={"job_type": "INVALID_JOB_TYPE"},
        headers=headers,
    )
    assert res_invalid.status_code == 400


def test_webhook_registration_and_hmac_signing(setup_tenants):
    headers = setup_tenants["admin_a_headers"]

    # 1. Register Webhook
    res_create = client.post(
        "/api/webhooks",
        json={
            "name": "FinOps Slack Incident Channel",
            "url": "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX",
            "events": ["ANOMALY_DETECTED", "BUDGET_BREACHED"],
            "secret_token": "my-secret-signing-key-12345",
        },
        headers=headers,
    )
    assert res_create.status_code == 200, res_create.text
    webhook = res_create.json()
    webhook_id = webhook["id"]
    assert webhook["name"] == "FinOps Slack Incident Channel"
    assert "my-secret" in webhook["secret_token"]

    # 2. List Webhooks
    res_list = client.get("/api/webhooks", headers=headers)
    assert res_list.status_code == 200
    assert any(w["id"] == webhook_id for w in res_list.json())

    # 3. Test HMAC-SHA256 signature verification
    payload_sample = b'{"event":"ANOMALY_DETECTED","amount":450.0}'
    sig = compute_webhook_signature("my-secret-signing-key-12345", payload_sample)
    assert sig.startswith("sha256=")

    # 4. Dispatch Test Ping
    res_test = client.post(f"/api/webhooks/{webhook_id}/test", headers=headers)
    assert res_test.status_code == 200
    test_data = res_test.json()
    assert test_data["status"] == "test_ping_dispatched"
    assert len(test_data["deliveries"]) >= 1
    assert test_data["deliveries"][0]["signature"].startswith("sha256=")

    # 5. Check delivery logs
    res_logs = client.get(f"/api/webhooks/logs?endpoint_id={webhook_id}", headers=headers)
    assert res_logs.status_code == 200
    assert len(res_logs.json()) >= 1

    # 6. Delete Webhook
    res_del = client.delete(f"/api/webhooks/{webhook_id}", headers=headers)
    assert res_del.status_code == 200
    assert res_del.json()["status"] == "deleted"


def test_automated_action_remediation_lifecycle(setup_tenants):
    headers = setup_tenants["admin_a_headers"]

    # 1. Propose remediation actions based on resources
    res_propose = client.post("/api/actions/propose", headers=headers)
    assert res_propose.status_code == 200, res_propose.text
    actions = res_propose.json()
    assert len(actions) >= 1

    action = actions[0]
    action_id = action["id"]
    assert action["status"] == "PROPOSED"
    assert action["estimated_monthly_saving_usd"] > 0
    assert "rollback_plan" in action
    assert action["rollback_plan"] is not None

    # 2. Approve and Execute action
    res_approve = client.post(
        f"/api/actions/{action_id}/approve",
        json={"execution_notes": "Approved by FinOps Lead for non-prod savings."},
        headers=headers,
    )
    assert res_approve.status_code == 200, res_approve.text
    approved = res_approve.json()
    assert approved["status"] == "EXECUTED"
    assert approved["decided_at"] is not None
    assert approved["executed_at"] is not None

    # 3. Execute Rollback
    res_rollback = client.post(f"/api/actions/{action_id}/rollback", headers=headers)
    assert res_rollback.status_code == 200, res_rollback.text
    rolled_back = res_rollback.json()
    assert rolled_back["status"] == "ROLLED_BACK"

    # 4. Propose again and test rejection
    res_propose2 = client.post("/api/actions/propose", headers=headers)
    actions2 = res_propose2.json()
    open_actions = [a for a in actions2 if a["status"] == "PROPOSED"]
    if open_actions:
        target_to_reject = open_actions[0]
        res_reject = client.post(
            f"/api/actions/{target_to_reject['id']}/reject",
            json={"reason": "Resource needed for quarterly load test."},
            headers=headers,
        )
        assert res_reject.status_code == 200
        assert res_reject.json()["status"] == "REJECTED"


def test_rbac_actions_and_jobs_enforcement(setup_tenants):
    finops_headers = setup_tenants["finops_a_headers"]
    viewer_headers = setup_tenants["viewer_a_headers"]

    # 1. VIEWER cannot trigger jobs (403)
    res_v_job = client.post("/api/jobs/trigger", json={"job_type": "BUDGET_AUDIT"}, headers=viewer_headers)
    assert res_v_job.status_code == 403

    # 2. VIEWER cannot propose actions (403)
    res_v_propose = client.post("/api/actions/propose", headers=viewer_headers)
    assert res_v_propose.status_code == 403

    # 3. FINOPS can trigger jobs (200)
    res_f_job = client.post("/api/jobs/trigger", json={"job_type": "BUDGET_AUDIT"}, headers=finops_headers)
    assert res_f_job.status_code == 200

    # 4. FINOPS cannot delete webhooks (only ADMIN can delete)
    res_f_del_hook = client.delete("/api/webhooks/dummy-id", headers=finops_headers)
    assert res_f_del_hook.status_code == 403

    # 5. FINOPS cannot rollback actions (only ADMIN can rollback)
    res_f_rollback = client.post("/api/actions/dummy-id/rollback", headers=finops_headers)
    assert res_f_rollback.status_code == 403


def test_multitenant_jobs_webhooks_actions_isolation(setup_tenants):
    headers_a = setup_tenants["admin_a_headers"]
    headers_b = setup_tenants["admin_b_headers"]

    # Create webhook in Org A
    res_hook_a = client.post(
        "/api/webhooks",
        json={
            "name": "Org A Webhook",
            "url": "https://example.com/org-a-webhook",
        },
        headers=headers_a,
    )
    assert res_hook_a.status_code == 200
    hook_a_id = res_hook_a.json()["id"]

    # Org B user cannot delete Org A webhook (404 Not Found)
    res_b_del_hook = client.delete(f"/api/webhooks/{hook_a_id}", headers=headers_b)
    assert res_b_del_hook.status_code == 404

    # Org B user cannot see Org A webhook in list
    res_b_list_hooks = client.get("/api/webhooks", headers=headers_b)
    assert res_b_list_hooks.status_code == 200
    assert not any(w["id"] == hook_a_id for w in res_b_list_hooks.json())

    # Org B user cannot inspect Org A action detail (404 Not Found)
    res_propose_a = client.post("/api/actions/propose", headers=headers_a)
    assert res_propose_a.status_code == 200
    actions_a = res_propose_a.json()
    if actions_a:
        action_a_id = actions_a[0]["id"]
        res_b_get_act = client.get(f"/api/actions/{action_a_id}", headers=headers_b)
        assert res_b_get_act.status_code == 404
