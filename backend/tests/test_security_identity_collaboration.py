import pytest
import uuid
import io
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import User, Organization, AuditLog, RevokedToken
from app.auth import hash_password, create_token

client = TestClient(app)

@pytest.fixture
def seeded_admin_headers():
    from app.seed import seed
    seed()
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(email="admin@cloudsense.ai").first()
        token = create_token(user.id)
        return {"Authorization": f"Bearer {token}", "user_id": user.id, "org_id": user.organization_id}
    finally:
        db.close()

@pytest.fixture
def tenant_fixture():
    db = SessionLocal()
    try:
        org_a = Organization(name=f"Security Org A {uuid.uuid4().hex[:6]}")
        org_b = Organization(name=f"Security Org B {uuid.uuid4().hex[:6]}")
        db.add_all([org_a, org_b])
        db.flush()

        admin_a = User(
            email=f"admin_a_{uuid.uuid4().hex[:6]}@test.com",
            password_hash=hash_password("Pass123!"),
            role="ADMIN",
            organization_id=org_a.id,
        )
        finops_a = User(
            email=f"finops_a_{uuid.uuid4().hex[:6]}@test.com",
            password_hash=hash_password("Pass123!"),
            role="FINOPS_ENGINEER",
            organization_id=org_a.id,
        )
        auditor_a = User(
            email=f"auditor_a_{uuid.uuid4().hex[:6]}@test.com",
            password_hash=hash_password("Pass123!"),
            role="AUDITOR",
            organization_id=org_a.id,
        )
        viewer_a = User(
            email=f"viewer_a_{uuid.uuid4().hex[:6]}@test.com",
            password_hash=hash_password("Pass123!"),
            role="VIEWER",
            organization_id=org_a.id,
        )
        admin_b = User(
            email=f"admin_b_{uuid.uuid4().hex[:6]}@test.com",
            password_hash=hash_password("Pass123!"),
            role="ADMIN",
            organization_id=org_b.id,
        )

        db.add_all([admin_a, finops_a, auditor_a, viewer_a, admin_b])
        db.commit()

        return {
            "org_a_id": org_a.id,
            "org_b_id": org_b.id,
            "admin_a": {"headers": {"Authorization": f"Bearer {create_token(admin_a.id)}"}, "id": admin_a.id, "email": admin_a.email},
            "finops_a": {"headers": {"Authorization": f"Bearer {create_token(finops_a.id)}"}, "id": finops_a.id, "email": finops_a.email},
            "auditor_a": {"headers": {"Authorization": f"Bearer {create_token(auditor_a.id)}"}, "id": auditor_a.id, "email": auditor_a.email},
            "viewer_a": {"headers": {"Authorization": f"Bearer {create_token(viewer_a.id)}"}, "id": viewer_a.id, "email": viewer_a.email},
            "admin_b": {"headers": {"Authorization": f"Bearer {create_token(admin_b.id)}"}, "id": admin_b.id, "email": admin_b.email},
        }
    finally:
        db.close()

def test_rbac_role_enforcement_budgets(tenant_fixture):
    tf = tenant_fixture
    budget_payload = {
        "name": "Production Compute",
        "scope": "ORGANIZATION",
        "target": "ALL",
        "amount": 5000.0,
        "threshold": 0.85,
        "period": "MONTHLY",
    }

    # VIEWER attempting to create budget -> 403 Forbidden
    res_viewer = client.post("/api/budgets", json=budget_payload, headers=tf["viewer_a"]["headers"])
    assert res_viewer.status_code == 403
    assert "Insufficient permissions" in res_viewer.json()["detail"]

    # AUDITOR attempting to create budget -> 403 Forbidden
    res_auditor = client.post("/api/budgets", json=budget_payload, headers=tf["auditor_a"]["headers"])
    assert res_auditor.status_code == 403

    # FINOPS_ENGINEER creating budget -> 201 Created
    res_finops = client.post("/api/budgets", json=budget_payload, headers=tf["finops_a"]["headers"])
    assert res_finops.status_code == 201
    created_id = res_finops.json()["id"]

    # AUDITOR attempting to delete budget -> 403 Forbidden
    res_del_auditor = client.delete(f"/api/budgets/{created_id}", headers=tf["auditor_a"]["headers"])
    assert res_del_auditor.status_code == 403

    # ADMIN deleting budget -> 200 OK
    res_del_admin = client.delete(f"/api/budgets/{created_id}", headers=tf["admin_a"]["headers"])
    assert res_del_admin.status_code == 200

def test_rbac_billing_import(tenant_fixture):
    tf = tenant_fixture
    csv_content = b"AccountID,LineItemType,ProductCode,UsageAmount,Cost,Currency\nacc-1,Usage,EC2,10.0,50.0,USD\n"
    files = {"file": ("test.csv", io.BytesIO(csv_content), "text/csv")}

    # VIEWER attempting billing import -> 403 Forbidden
    res_viewer = client.post("/api/billing/import", files=files, headers=tf["viewer_a"]["headers"])
    assert res_viewer.status_code == 403

    # AUDITOR attempting billing import -> 403 Forbidden
    files["file"] = ("test.csv", io.BytesIO(csv_content), "text/csv")
    res_auditor = client.post("/api/billing/import", files=files, headers=tf["auditor_a"]["headers"])
    assert res_auditor.status_code == 403

def test_session_revocation_logout(tenant_fixture):
    tf = tenant_fixture
    admin_headers = tf["admin_a"]["headers"]

    # Valid authenticated call
    res_pre = client.get("/api/dashboard/summary", headers=admin_headers)
    assert res_pre.status_code == 200

    # Logout
    res_logout = client.post("/api/auth/logout", headers=admin_headers)
    assert res_logout.status_code == 200
    assert res_logout.json()["status"] == "success"

    # Subsequent call with the revoked token -> 401 Unauthorized
    res_post = client.get("/api/dashboard/summary", headers=admin_headers)
    assert res_post.status_code == 401
    assert "revoked" in res_post.json()["detail"].lower()

def test_workspace_users_list_and_invite(tenant_fixture):
    tf = tenant_fixture
    admin_headers = tf["admin_a"]["headers"]
    viewer_headers = tf["viewer_a"]["headers"]

    # List workspace users
    res_list = client.get("/api/users", headers=admin_headers)
    assert res_list.status_code == 200
    users = res_list.json()
    assert len(users) >= 4

    # VIEWER attempting to invite member -> 403 Forbidden
    res_inv_viewer = client.post(
        "/api/users/invite",
        json={"email": "new_dev@test.com", "role": "FINOPS_ENGINEER"},
        headers=viewer_headers,
    )
    assert res_inv_viewer.status_code == 403

    # ADMIN inviting member -> 201 Created
    new_email = f"invited_{uuid.uuid4().hex[:6]}@test.com"
    res_inv_admin = client.post(
        "/api/users/invite",
        json={"email": new_email, "role": "FINOPS_ENGINEER"},
        headers=admin_headers,
    )
    assert res_inv_admin.status_code == 201
    inv_data = res_inv_admin.json()
    assert inv_data["email"] == new_email
    assert inv_data["role"] == "FINOPS_ENGINEER"
    assert inv_data["is_active"] is True

def test_last_active_admin_protection(tenant_fixture):
    tf = tenant_fixture
    admin_a_id = tf["admin_a"]["id"]
    admin_headers = tf["admin_a"]["headers"]

    # Attempt to demote sole active admin to VIEWER -> 400 Bad Request
    res_demote = client.patch(
        f"/api/users/{admin_a_id}/role",
        json={"role": "VIEWER"},
        headers=admin_headers,
    )
    assert res_demote.status_code == 400
    assert "last active admin" in res_demote.json()["detail"].lower()

    # Invite a second admin
    sec_admin_email = f"second_admin_{uuid.uuid4().hex[:6]}@test.com"
    res_inv = client.post(
        "/api/users/invite",
        json={"email": sec_admin_email, "role": "ADMIN"},
        headers=admin_headers,
    )
    assert res_inv.status_code == 201
    second_admin_id = res_inv.json()["id"]

    # Now demoting the first admin succeeds because a second admin exists
    res_demote_ok = client.patch(
        f"/api/users/{admin_a_id}/role",
        json={"role": "FINOPS_ENGINEER"},
        headers={"Authorization": f"Bearer {create_token(second_admin_id)}"},
    )
    assert res_demote_ok.status_code == 200
    assert res_demote_ok.json()["role"] == "FINOPS_ENGINEER"

def test_user_deactivation_and_login_denial(tenant_fixture):
    tf = tenant_fixture
    admin_headers = tf["admin_a"]["headers"]
    finops_id = tf["finops_a"]["id"]
    finops_email = tf["finops_a"]["email"]

    # Admin cannot deactivate self
    res_self = client.delete(f"/api/users/{tf['admin_a']['id']}", headers=admin_headers)
    assert res_self.status_code == 400
    assert "own account" in res_self.json()["detail"].lower()

    # Admin deactivates finops member -> 200
    res_deact = client.delete(f"/api/users/{finops_id}", headers=admin_headers)
    assert res_deact.status_code == 200
    assert res_deact.json()["is_active"] is False

    # Deactivated user cannot login
    res_login = client.post(
        "/api/auth/login",
        json={"email": finops_email, "password": "Pass123!"},
    )
    assert res_login.status_code == 401
    assert "inactive" in res_login.json()["detail"].lower()

def test_audit_logs_rbac_and_querying(tenant_fixture):
    tf = tenant_fixture
    admin_headers = tf["admin_a"]["headers"]
    auditor_headers = tf["auditor_a"]["headers"]
    finops_headers = tf["finops_a"]["headers"]

    # Trigger some audited actions
    client.post(
        "/api/budgets",
        json={"name": "Audited Budget", "amount": 1000.0, "threshold": 0.8},
        headers=admin_headers,
    )

    # FINOPS_ENGINEER attempting to view audit logs -> 403 Forbidden
    res_finops = client.get("/api/audit/logs", headers=finops_headers)
    assert res_finops.status_code == 403

    # AUDITOR querying audit logs -> 200 OK
    res_auditor = client.get("/api/audit/logs", headers=auditor_headers)
    assert res_auditor.status_code == 200
    auditor_logs = res_auditor.json()
    assert len(auditor_logs) >= 1
    actions = {l["action"] for l in auditor_logs}
    assert any("budget" in a or "user" in a for a in actions)

    # Filter by action
    res_filt = client.get("/api/audit/logs?action=budget", headers=admin_headers)
    assert res_filt.status_code == 200
    for l in res_filt.json():
        assert "budget" in l["action"].lower()

def test_multi_tenant_user_management_denial(tenant_fixture):
    tf = tenant_fixture
    admin_a_headers = tf["admin_a"]["headers"]
    admin_b_headers = tf["admin_b"]["headers"]
    admin_b_id = tf["admin_b"]["id"]

    # Admin A attempts to change role of Admin B in Org B -> 400 Not Found in workspace
    res_cross_role = client.patch(
        f"/api/users/{admin_b_id}/role",
        json={"role": "VIEWER"},
        headers=admin_a_headers,
    )
    assert res_cross_role.status_code == 400
    assert "not found in this workspace" in res_cross_role.json()["detail"].lower()

    # Admin A attempts to deactivate user in Org B -> 400
    res_cross_del = client.delete(f"/api/users/{admin_b_id}", headers=admin_a_headers)
    assert res_cross_del.status_code == 400

def test_multi_tenant_audit_log_isolation(tenant_fixture):
    tf = tenant_fixture
    admin_a_headers = tf["admin_a"]["headers"]
    admin_b_headers = tf["admin_b"]["headers"]
    auditor_a_headers = tf["auditor_a"]["headers"]

    # Org B performs audited action
    client.post(
        "/api/budgets",
        json={"name": "Org B Secret Budget", "amount": 99999.0, "threshold": 0.9},
        headers=admin_b_headers,
    )

    # Auditor A queries logs in Org A
    res_a = client.get("/api/audit/logs", headers=auditor_a_headers)
    assert res_a.status_code == 200
    logs_a = res_a.json()

    # Verify none of Org B's details appear in Org A's audit stream
    for log in logs_a:
        assert log["organization_id"] == tf["org_a_id"]
        assert "Org B Secret Budget" not in (log["detail"] or "")

def test_workspace_profile_and_settings_update(tenant_fixture):
    tf = tenant_fixture
    admin_headers = tf["admin_a"]["headers"]
    viewer_headers = tf["viewer_a"]["headers"]

    # Get workspace profile
    res_get = client.get("/api/workspace", headers=viewer_headers)
    assert res_get.status_code == 200
    prof = res_get.json()
    assert "name" in prof
    assert "currency" in prof
    assert prof["currency"] == "USD"
    assert prof["summary"]["active_members"] >= 4

    # VIEWER attempting to update settings -> 403 Forbidden
    res_patch_viewer = client.patch(
        "/api/workspace/settings",
        json={"name": "Hacked Name"},
        headers=viewer_headers,
    )
    assert res_patch_viewer.status_code == 403

    # ADMIN updating settings
    res_patch_admin = client.patch(
        "/api/workspace/settings",
        json={"name": "Enterprise FinOps Cloud", "currency": "EUR", "timezone": "Europe/London"},
        headers=admin_headers,
    )
    assert res_patch_admin.status_code == 200
    updated = res_patch_admin.json()
    assert updated["name"] == "Enterprise FinOps Cloud"
    assert updated["currency"] == "EUR"
    assert updated["timezone"] == "Europe/London"
