import pytest
import uuid
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import User, Organization, CloudAccount, CloudSyncJob, CostRecord
from app.auth import hash_password, create_token
from app.providers import get_cloud_connector

client = TestClient(app)

@pytest.fixture
def test_setup():
    db = SessionLocal()
    try:
        org_a = Organization(name=f"Connector Org A {uuid.uuid4().hex[:6]}")
        org_b = Organization(name=f"Connector Org B {uuid.uuid4().hex[:6]}")
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
        db.add_all([admin_a, finops_a, viewer_a, admin_b])
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


def test_aws_connector_credential_validation():
    connector = get_cloud_connector("AWS")

    # Valid Role ARN
    is_valid, err, masked = connector.validate_credentials(
        {"role_arn": "arn:aws:iam::123456789012:role/CloudSenseFinOpsRole", "external_id": "ext-12345"},
        auth_type="ROLE_ARN",
    )
    assert is_valid is True
    assert err is None
    assert "role_arn" in masked
    assert masked["role_arn"].startswith("arn:aws:iam:")
    assert "****" in masked["role_arn"]
    assert masked["external_id"] != "ext-12345"  # Masked

    # Malformed Role ARN
    is_valid, err, _ = connector.validate_credentials(
        {"role_arn": "not-an-arn"},
        auth_type="ROLE_ARN",
    )
    assert is_valid is False
    assert "IAM Role ARN" in err

    # Valid Access Keys
    is_valid, err, masked = connector.validate_credentials(
        {"access_key_id": "AKIAIOSFODNN7EXAMPLE", "secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"},
        auth_type="ACCESS_KEY",
    )
    assert is_valid is True
    assert masked["access_key_id"].startswith("AKIA")
    assert "****" in masked["access_key_id"]
    assert masked["secret_access_key"] == "****************"

    # Invalid Access Key ID
    is_valid, err, _ = connector.validate_credentials(
        {"access_key_id": "INVALIDKEY", "secret_access_key": "short"},
        auth_type="ACCESS_KEY",
    )
    assert is_valid is False
    assert "AKIA" in err


def test_azure_connector_credential_validation():
    connector = get_cloud_connector("AZURE")

    # Valid Service Principal UUIDs
    is_valid, err, masked = connector.validate_credentials(
        {
            "tenant_id": "c1f72849-0f0c-4b68-bf0f-7b0f69f268b8",
            "client_id": "8489f6b2-65f5-41e9-b501-1e967a1fb4d9",
            "subscription_id": "11111111-2222-3333-4444-555555555555",
            "client_secret": "my-azure-secret-value-12345",
        },
        auth_type="SERVICE_PRINCIPAL",
    )
    assert is_valid is True
    assert err is None
    assert masked["client_id"].startswith("8489f6b2")
    assert "****" in masked["client_id"]
    assert "****" in masked["client_secret"]

    # Invalid non-UUID tenant ID
    is_valid, err, _ = connector.validate_credentials(
        {
            "tenant_id": "not-a-uuid",
            "client_id": "8489f6b2-65f5-41e9-b501-1e967a1fb4d9",
            "subscription_id": "11111111-2222-3333-4444-555555555555",
            "client_secret": "my-azure-secret-value-12345",
        },
        auth_type="SERVICE_PRINCIPAL",
    )
    assert is_valid is False
    assert "UUID" in err


def test_gcp_connector_credential_validation():
    connector = get_cloud_connector("GCP")

    # Valid GCP Service Account
    is_valid, err, masked = connector.validate_credentials(
        {
            "project_id": "cloudsense-prod-99",
            "client_email": "cloudsense-ingest@cloudsense-prod-99.iam.gserviceaccount.com",
            "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASC...\n-----END PRIVATE KEY-----",
        },
        auth_type="SERVICE_ACCOUNT",
    )
    assert is_valid is True
    assert err is None
    assert masked["project_id"] == "cloudsense-prod-99"
    assert masked["client_email"].startswith("cloudsen")
    assert masked["client_email"].endswith("ount.com")
    assert "****" in masked["private_key"]

    # Invalid email format
    is_valid, err, _ = connector.validate_credentials(
        {
            "project_id": "cloudsense-prod-99",
            "client_email": "not-a-service-account@gmail.com",
            "private_key": "some-key",
        },
        auth_type="SERVICE_ACCOUNT",
    )
    assert is_valid is False
    assert "gserviceaccount.com" in err


def test_connect_account_duplicate_identifier_rejection(test_setup):
    headers = test_setup["admin_a_headers"]

    payload = {
        "provider": "AWS",
        "name": "Production Core AWS",
        "identifier": "123456789012",
        "region": "us-east-1",
        "auth_type": "ROLE_ARN",
        "credentials": {
            "role_arn": "arn:aws:iam::123456789012:role/CloudSenseRole",
            "external_id": "ext-unique-1",
        },
        "sync_frequency": "DAILY",
    }

    # First connection succeeds
    res1 = client.post("/api/cloud/accounts", json=payload, headers=headers)
    assert res1.status_code == 200, res1.text
    data1 = res1.json()
    assert data1["provider"] == "AWS"
    assert data1["status"] == "CONNECTED"

    # Duplicate connection with same identifier in same org fails
    res2 = client.post("/api/cloud/accounts", json=payload, headers=headers)
    assert res2.status_code == 400
    assert "already connected" in res2.json()["detail"]


def test_trigger_account_sync_idempotence(test_setup):
    headers = test_setup["admin_a_headers"]
    org_id = test_setup["org_a"]

    # Connect Azure account
    connect_res = client.post(
        "/api/cloud/accounts",
        json={
            "provider": "AZURE",
            "name": "Enterprise Azure Subscription",
            "identifier": "11111111-2222-3333-4444-555555555555",
            "region": "eastus",
            "auth_type": "SERVICE_PRINCIPAL",
            "credentials": {
                "tenant_id": "c1f72849-0f0c-4b68-bf0f-7b0f69f268b8",
                "client_id": "8489f6b2-65f5-41e9-b501-1e967a1fb4d9",
                "subscription_id": "11111111-2222-3333-4444-555555555555",
                "client_secret": "sec-1234567890",
            },
            "sync_frequency": "DAILY",
        },
        headers=headers,
    )
    assert connect_res.status_code == 200, connect_res.text
    account_id = connect_res.json()["id"]

    # Run initial sync (30 days)
    sync1_res = client.post(
        f"/api/cloud/accounts/{account_id}/sync",
        json={"sync_type": "BILLING_CUR", "days": 30},
        headers=headers,
    )
    assert sync1_res.status_code == 200, sync1_res.text
    sync1_data = sync1_res.json()
    assert sync1_data["status"] == "COMPLETED"
    ingested_count = sync1_data["records_ingested"]
    assert ingested_count > 0

    # Verify count in database
    db = SessionLocal()
    try:
        count_after_sync1 = (
            db.query(CostRecord)
            .filter_by(organization_id=org_id, provider="AZURE")
            .count()
        )
        assert count_after_sync1 == ingested_count

        # Run identical second sync over the same time window
        sync2_res = client.post(
            f"/api/cloud/accounts/{account_id}/sync",
            json={"sync_type": "BILLING_CUR", "days": 30},
            headers=headers,
        )
        assert sync2_res.status_code == 200, sync2_res.text

        # Verify idempotence: count in database MUST NOT double
        count_after_sync2 = (
            db.query(CostRecord)
            .filter_by(organization_id=org_id, provider="AZURE")
            .count()
        )
        assert count_after_sync2 == count_after_sync1, "Sync must be idempotent; duplicate records were found!"
    finally:
        db.close()


def test_sync_job_simulation_disclosure(test_setup):
    headers = test_setup["admin_a_headers"]

    # Connect GCP account
    connect_res = client.post(
        "/api/cloud/accounts",
        json={
            "provider": "GCP",
            "name": "CloudSense GCP BigQuery",
            "identifier": "cloudsense-analytics-demo",
            "region": "us-central1",
            "auth_type": "SERVICE_ACCOUNT",
            "credentials": {
                "project_id": "cloudsense-analytics-demo",
                "client_email": "ingest@cloudsense-analytics-demo.iam.gserviceaccount.com",
                "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASC\n-----END PRIVATE KEY-----",
            },
            "sync_frequency": "DAILY",
        },
        headers=headers,
    )
    assert connect_res.status_code == 200, connect_res.text
    account_id = connect_res.json()["id"]

    # Trigger sync
    sync_res = client.post(
        f"/api/cloud/accounts/{account_id}/sync",
        json={"sync_type": "BILLING_CUR", "days": 14},
        headers=headers,
    )
    assert sync_res.status_code == 200
    sync_data = sync_res.json()

    assert sync_data["is_simulated"] is True
    assert "simulation_disclosure" in sync_data
    assert "structurally validated" in sync_data["simulation_disclosure"]
    assert "telemetry" in sync_data["simulation_disclosure"]

    # Check sync jobs listing endpoint
    jobs_res = client.get(f"/api/cloud/accounts/{account_id}/jobs", headers=headers)
    assert jobs_res.status_code == 200
    jobs = jobs_res.json()
    assert len(jobs) >= 1
    assert jobs[0]["is_simulated"] is True


def test_multicloud_connectors_rbac_enforcement(test_setup):
    admin_headers = test_setup["admin_a_headers"]
    finops_headers = test_setup["finops_a_headers"]
    viewer_headers = test_setup["viewer_a_headers"]

    # 1. VIEWER cannot connect account (403 Forbidden)
    res_viewer_connect = client.post(
        "/api/cloud/accounts",
        json={
            "provider": "AWS",
            "name": "Unauthorized AWS",
            "identifier": "999999999999",
            "region": "us-west-2",
            "auth_type": "ROLE_ARN",
            "credentials": {
                "role_arn": "arn:aws:iam::999999999999:role/TestRole",
                "external_id": "ext-test-123",
            },
        },
        headers=viewer_headers,
    )
    assert res_viewer_connect.status_code == 403

    # 2. FINOPS_ENGINEER can connect account (200 OK)
    res_finops_connect = client.post(
        "/api/cloud/accounts",
        json={
            "provider": "AWS",
            "name": "FinOps AWS Ingestion",
            "identifier": "888888888888",
            "region": "us-west-2",
            "auth_type": "ROLE_ARN",
            "credentials": {
                "role_arn": "arn:aws:iam::888888888888:role/TestRole",
                "external_id": "ext-finops-888",
            },
        },
        headers=finops_headers,
    )
    assert res_finops_connect.status_code == 200
    account_id = res_finops_connect.json()["id"]

    # 3. VIEWER cannot trigger sync (403 Forbidden)
    res_viewer_sync = client.post(
        f"/api/cloud/accounts/{account_id}/sync",
        json={"days": 7},
        headers=viewer_headers,
    )
    assert res_viewer_sync.status_code == 403

    # 4. VIEWER can view accounts and sync jobs (200 OK)
    res_viewer_list = client.get("/api/cloud/accounts", headers=viewer_headers)
    assert res_viewer_list.status_code == 200
    assert any(a["id"] == account_id for a in res_viewer_list.json())

    res_viewer_jobs = client.get(f"/api/cloud/accounts/{account_id}/jobs", headers=viewer_headers)
    assert res_viewer_jobs.status_code == 200

    # 5. FINOPS_ENGINEER cannot delete account (403 Forbidden - only ADMIN can delete)
    res_finops_delete = client.delete(f"/api/cloud/accounts/{account_id}", headers=finops_headers)
    assert res_finops_delete.status_code == 403

    # 6. ADMIN can delete account (200 OK)
    res_admin_delete = client.delete(f"/api/cloud/accounts/{account_id}", headers=admin_headers)
    assert res_admin_delete.status_code == 200
    assert res_admin_delete.json()["status"] == "disconnected"


def test_multitenant_account_and_sync_isolation(test_setup):
    headers_a = test_setup["admin_a_headers"]
    headers_b = test_setup["admin_b_headers"]

    # Create account in Org A
    res_create = client.post(
        "/api/cloud/accounts",
        json={
            "provider": "GCP",
            "name": "Org A GCP Project",
            "identifier": "org-a-gcp-isolated",
            "region": "us-central1",
            "auth_type": "SERVICE_ACCOUNT",
            "credentials": {
                "project_id": "org-a-gcp-isolated",
                "client_email": "sa@org-a-gcp-isolated.iam.gserviceaccount.com",
                "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASC\n-----END PRIVATE KEY-----",
            },
        },
        headers=headers_a,
    )
    assert res_create.status_code == 200, res_create.text
    account_a_id = res_create.json()["id"]

    # Org B user cannot get account detail (404 Not Found)
    res_b_get = client.get(f"/api/cloud/accounts/{account_a_id}", headers=headers_b)
    assert res_b_get.status_code == 404

    # Org B user does not see Org A account in list
    res_b_list = client.get("/api/cloud/accounts", headers=headers_b)
    assert res_b_list.status_code == 200
    assert not any(a["id"] == account_a_id for a in res_b_list.json())

    # Org B user cannot trigger sync on Org A account (404 Not Found)
    res_b_sync = client.post(
        f"/api/cloud/accounts/{account_a_id}/sync",
        headers=headers_b,
    )
    assert res_b_sync.status_code == 404

    # Org B user cannot delete Org A account (404 Not Found)
    res_b_delete = client.delete(f"/api/cloud/accounts/{account_a_id}", headers=headers_b)
    assert res_b_delete.status_code == 404
