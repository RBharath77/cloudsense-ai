import pytest
import uuid
import json
from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import User, Organization, TerraformPlanAnalysis, KubernetesCostAllocation
from app.auth import hash_password, create_token

client = TestClient(app)

@pytest.fixture
def setup_iac_tenants():
    db = SessionLocal()
    try:
        org_a = Organization(name=f"IaC Org A {uuid.uuid4().hex[:6]}")
        org_b = Organization(name=f"IaC Org B {uuid.uuid4().hex[:6]}")
        db.add_all([org_a, org_b])
        db.flush()

        admin_a = User(
            email=f"admin_iac_a_{uuid.uuid4().hex[:6]}@test.com",
            password_hash=hash_password("Pass123!"),
            role="ADMIN",
            organization_id=org_a.id,
        )
        finops_a = User(
            email=f"finops_iac_a_{uuid.uuid4().hex[:6]}@test.com",
            password_hash=hash_password("Pass123!"),
            role="FINOPS_ENGINEER",
            organization_id=org_a.id,
        )
        viewer_a = User(
            email=f"viewer_iac_a_{uuid.uuid4().hex[:6]}@test.com",
            password_hash=hash_password("Pass123!"),
            role="VIEWER",
            organization_id=org_a.id,
        )
        admin_b = User(
            email=f"admin_iac_b_{uuid.uuid4().hex[:6]}@test.com",
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
            "admin_a": token_admin_a,
            "finops_a": token_finops_a,
            "viewer_a": token_viewer_a,
            "admin_b": token_admin_b,
        }
    finally:
        db.close()

def test_terraform_plan_parsing_and_cost_delta(setup_iac_tenants):
    token = setup_iac_tenants["admin_a"]
    
    # Terraform Plan JSON creating a t3.large EC2 instance and a 200GB gp3 EBS volume
    plan_json = {
        "format_version": "1.0",
        "terraform_version": "1.8.2",
        "resource_changes": [
            {
                "address": "aws_instance.web_app",
                "type": "aws_instance",
                "name": "web_app",
                "provider_name": "registry.terraform.io/hashicorp/aws",
                "change": {
                    "actions": ["create"],
                    "before": None,
                    "after": {
                        "instance_type": "t3.large",
                        "region": "us-east-1",
                        "tags": {
                            "Environment": "Production",
                            "Owner": "DevOps",
                        },
                    },
                },
            },
            {
                "address": "aws_ebs_volume.data",
                "type": "aws_ebs_volume",
                "name": "data",
                "provider_name": "registry.terraform.io/hashicorp/aws",
                "change": {
                    "actions": ["create"],
                    "before": None,
                    "after": {
                        "size": 200,
                        "type": "gp3",
                        "region": "us-east-1",
                        "tags": {
                            "Environment": "Production",
                            "Owner": "DevOps",
                        },
                    },
                },
            },
        ],
    }

    res = client.post(
        "/api/iac/terraform/analyze",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "plan_name": "Web Infrastructure Expansion",
            "plan_data": plan_json,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["plan_name"] == "Web Infrastructure Expansion"
    assert data["provider"] == "aws"
    assert data["resources_created"] == 2
    assert data["monthly_cost_before_usd"] == 0.0
    # t3.large ($60.74) + 200GB gp3 @ $0.08 ($16.00) = $76.74
    assert data["monthly_cost_after_usd"] == 76.74
    assert data["monthly_cost_delta_usd"] == 76.74
    assert data["monthly_emissions_delta_kgco2e"] > 0
    assert data["policy_status"] == "PASSED"
    assert len(data["violations"]) == 0

def test_terraform_plan_policy_blocked_disallowed_instance(setup_iac_tenants):
    token = setup_iac_tenants["finops_a"]
    
    # Terraform Plan requesting an unapproved $23k/mo p4d.24xlarge GPU instance
    plan_json = {
        "resource_changes": [
            {
                "address": "aws_instance.ml_training",
                "type": "aws_instance",
                "name": "ml_training",
                "change": {
                    "actions": ["create"],
                    "before": None,
                    "after": {
                        "instance_type": "p4d.24xlarge",
                        "region": "us-east-1",
                        "tags": {"Environment": "Research", "Owner": "ML-Team"},
                    },
                },
            }
        ]
    }

    res = client.post(
        "/api/iac/terraform/analyze",
        headers={"Authorization": f"Bearer {token}"},
        json={"plan_name": "GPU Model Training Node", "plan_data": plan_json},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["policy_status"] == "BLOCKED"
    violations = data["violations"]
    assert any(v["rule"] == "DISALLOWED_EXPENSIVE_INSTANCE_TYPE" for v in violations)

def test_terraform_plan_policy_warning_missing_tags(setup_iac_tenants):
    token = setup_iac_tenants["admin_a"]
    
    # Instance created without mandatory Environment/Owner tags
    plan_json = {
        "resource_changes": [
            {
                "address": "aws_instance.shadow_service",
                "type": "aws_instance",
                "name": "shadow_service",
                "change": {
                    "actions": ["create"],
                    "before": None,
                    "after": {
                        "instance_type": "t3.medium",
                        "tags": {},
                    },
                },
            }
        ]
    }

    res = client.post(
        "/api/iac/terraform/analyze",
        headers={"Authorization": f"Bearer {token}"},
        json={"plan_name": "Untagged Test VM", "plan_data": plan_json},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["policy_status"] == "WARNING"
    violations = data["violations"]
    assert any(v["rule"] == "MISSING_MANDATORY_COST_TAGS" for v in violations)

def test_terraform_plan_history_and_detail_endpoint(setup_iac_tenants):
    token = setup_iac_tenants["viewer_a"]
    admin_token = setup_iac_tenants["admin_a"]

    # Create a plan as admin
    plan_json = {
        "resource_changes": [
            {
                "address": "aws_instance.worker",
                "type": "aws_instance",
                "name": "worker",
                "change": {
                    "actions": ["create"],
                    "after": {"instance_type": "t3.small", "tags": {"Environment": "Dev", "Owner": "Ops"}},
                },
            }
        ]
    }
    create_res = client.post(
        "/api/iac/terraform/analyze",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"plan_name": "Worker Node", "plan_data": plan_json},
    )
    plan_id = create_res.json()["id"]

    # Viewer queries list
    list_res = client.get(
        "/api/iac/terraform/analyses",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_res.status_code == 200
    items = list_res.json()
    assert any(p["id"] == plan_id for p in items)

    # Viewer queries detail
    detail_res = client.get(
        f"/api/iac/terraform/analyses/{plan_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["id"] == plan_id
    assert "summary" in detail
    assert detail["summary"]["pricing_source"] is not None

def test_kubernetes_cost_allocations_and_idle_waste_math(setup_iac_tenants):
    token = setup_iac_tenants["viewer_a"]

    res = client.get(
        "/api/containers/kubernetes/allocations",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    allocations = res.json()
    assert len(allocations) > 0

    first = allocations[0]
    assert "monthly_allocated_cost_usd" in first
    assert "monthly_idle_cost_usd" in first
    assert "efficiency_score" in first
    # Idle cost + active cost must reconcile with monthly_allocated_cost_usd
    assert round(first["active_cost_usd"] + first["monthly_idle_cost_usd"], 2) == first["monthly_allocated_cost_usd"]

def test_kubernetes_cluster_summary_aggregation(setup_iac_tenants):
    token = setup_iac_tenants["viewer_a"]

    res = client.get(
        "/api/containers/kubernetes/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total_allocated_cost_usd"] > 0
    assert data["total_idle_waste_cost_usd"] >= 0
    assert data["total_active_cost_usd"] > 0
    assert 0 <= data["overall_efficiency_pct"] <= 100
    assert len(data["namespace_breakdown"]) > 0
    assert data["is_simulated_benchmark"] is True

def test_kubernetes_telemetry_ingestion_api(setup_iac_tenants):
    token = setup_iac_tenants["admin_a"]

    payload = {
        "cluster_name": "custom-k8s-cluster",
        "recorded_date": "2026-10-17",
        "allocations": [
            {
                "namespace": "checkout",
                "workload_name": "checkout-api",
                "workload_type": "Deployment",
                "cpu_allocated_cores": 4.0,
                "cpu_usage_cores": 3.0,
                "memory_allocated_bytes": 8589934592,  # 8 GiB
                "memory_usage_bytes": 6442450944,     # 6 GiB
                "monthly_allocated_cost_usd": 210.0,
            }
        ],
    }

    res = client.post(
        "/api/containers/kubernetes/ingest",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["cluster_name"] == "custom-k8s-cluster"
    assert data[0]["namespace"] == "checkout"
    assert data[0]["workload_name"] == "checkout-api"
    # Efficiency: (3/4 * 50) + (6/8 * 50) = 37.5 + 37.5 = 75.0%
    assert data[0]["efficiency_score"] == 75.0
    # Idle cost: 210.0 * (1 - 0.75) = 52.5
    assert data[0]["monthly_idle_cost_usd"] == 52.5

def test_iac_container_rbac_enforcement(setup_iac_tenants):
    token = setup_iac_tenants["viewer_a"]

    # VIEWER cannot analyze terraform plans
    res_plan = client.post(
        "/api/iac/terraform/analyze",
        headers={"Authorization": f"Bearer {token}"},
        json={"plan_name": "Denied Plan", "plan_data": {"resource_changes": []}},
    )
    assert res_plan.status_code == 403

    # VIEWER cannot ingest kubernetes metrics
    res_k8s = client.post(
        "/api/containers/kubernetes/ingest",
        headers={"Authorization": f"Bearer {token}"},
        json={"cluster_name": "c1", "allocations": []},
    )
    assert res_k8s.status_code == 403

def test_multitenant_iac_and_container_isolation(setup_iac_tenants):
    token_a = setup_iac_tenants["admin_a"]
    token_b = setup_iac_tenants["admin_b"]

    # Org A creates a Terraform plan
    res_a = client.post(
        "/api/iac/terraform/analyze",
        headers={"Authorization": f"Bearer {token_a}"},
        json={
            "plan_name": "Org A Confidential Plan",
            "plan_data": {
                "resource_changes": [
                    {
                        "address": "aws_instance.secret_vm",
                        "type": "aws_instance",
                        "change": {"actions": ["create"], "after": {"instance_type": "t3.micro"}},
                    }
                ]
            },
        },
    )
    plan_id_a = res_a.json()["id"]

    # Org B attempts to fetch Org A's plan directly -> 404
    res_b_direct = client.get(
        f"/api/iac/terraform/analyses/{plan_id_a}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_b_direct.status_code == 404

    # Org B lists plans -> must not contain Org A's plan
    res_b_list = client.get(
        "/api/iac/terraform/analyses",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_b_list.status_code == 200
    ids_b = [p["id"] for p in res_b_list.json()]
    assert plan_id_a not in ids_b
