import pytest
import uuid
from datetime import datetime, timedelta
from jose import jwt
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings
from app.database import SessionLocal, Base, engine
from app.models import (
    User,
    Organization,
    CloudAccount,
    CloudResource,
    MetricRecord,
    Recommendation,
    SavingsLedger,
    SimulationScenario,
)
from app.auth import hash_password, create_token
from app.services.optimization_service import (
    calculate_priority_score,
    PRIORITY_CONFIGS,
    get_grid_intensity_for_region,
    calculate_instance_carbon_kg,
)

client = TestClient(app)

def create_user_and_token(prefix="opt_user"):
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
        org = Organization(name=f"Empty Optimization Org {uuid.uuid4().hex[:6]}")
        db.add(org)
        db.flush()
        user = User(
            email=f"opt_empty_{uuid.uuid4().hex[:8]}@cloudsense.ai",
            password_hash=hash_password("Pass123!"),
            role="ADMIN",
            organization_id=org.id,
        )
        db.add(user)
        db.commit()
        token = create_token(user.id)
        return {"Authorization": f"Bearer {token}", "org_id": org.id}
    finally:
        db.close()

def test_hardware_carbon_and_grid_factor_calculations():
    # us-east-1 factor is 379.2 g/kWh
    intensity = get_grid_intensity_for_region("us-east-1")
    assert intensity == 379.2

    # Oregon us-west-2 hydro clean factor is 152.4 g/kWh
    hydro_intensity = get_grid_intensity_for_region("us-west-2")
    assert hydro_intensity == 152.4

    # Power: 100W for 730 hrs, PUE 1.15 in us-east-1
    # 0.1 kW * 730 * 1.15 = 83.95 kWh * 379.2 / 1000 = 31.83 kgCO2e
    co2 = calculate_instance_carbon_kg(100.0, 730.0, "us-east-1")
    assert co2 > 30.0 and co2 < 33.0

def test_priority_score_weighting_transparency():
    # Verify priority configuration dictionary
    assert "BALANCE" in PRIORITY_CONFIGS
    assert "COST" in PRIORITY_CONFIGS
    assert "EMISSIONS" in PRIORITY_CONFIGS
    assert "RISK_AVOIDANT" in PRIORITY_CONFIGS

    # When priority is COST, high dollar saving gets high score
    cost_score = calculate_priority_score(
        monthly_saving=900.0,
        carbon_saving_kg=10.0,
        risk="LOW",
        confidence=0.9,
        priority="COST",
        max_saving=1000.0,
        max_carbon=100.0,
    )
    # When priority is EMISSIONS, low carbon gets lower score
    emissions_score = calculate_priority_score(
        monthly_saving=900.0,
        carbon_saving_kg=10.0,
        risk="LOW",
        confidence=0.9,
        priority="EMISSIONS",
        max_saving=1000.0,
        max_carbon=100.0,
    )
    assert cost_score > emissions_score

def test_recommendations_evidence_and_grounding(auth_headers):
    res = client.get("/api/optimization?priority=BALANCE", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()

    assert "priority" in data
    assert data["priority"] == "BALANCE"
    assert "scoring_weights" in data
    assert "scoring_formula" in data
    assert "summary" in data
    assert "recommendations" in data

    recs = data["recommendations"]
    assert len(recs) > 0

    first = recs[0]
    assert "id" in first
    assert "resource_id" in first
    assert "monthly_saving" in first
    assert "monthly_carbon_saving_kg" in first
    assert "priority_score" in first
    assert "evidence" in first
    assert "assumptions" in first
    assert "trade_offs" in first

    # Grounded evidence check:
    evidence = first["evidence"]
    if evidence:
        assert "metric" in evidence
        assert "avg_cpu_pct" in evidence

def test_recommendation_detail_endpoint(auth_headers):
    # Fetch list
    list_res = client.get("/api/optimization", headers=auth_headers)
    assert list_res.status_code == 200
    recs = list_res.json()["recommendations"]
    target_id = recs[0]["id"]

    detail_res = client.get(f"/api/optimization/recommendations/{target_id}", headers=auth_headers)
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["id"] == target_id
    assert "action" in detail
    assert "assumptions" in detail
    assert "trade_offs" in detail

def test_priority_modes_switch(auth_headers):
    cost_res = client.get("/api/optimization?priority=COST", headers=auth_headers)
    assert cost_res.status_code == 200
    assert cost_res.json()["priority"] == "COST"
    assert cost_res.json()["scoring_weights"]["cost"] == 0.70

    emissions_res = client.get("/api/optimization?priority=EMISSIONS", headers=auth_headers)
    assert emissions_res.status_code == 200
    assert emissions_res.json()["priority"] == "EMISSIONS"
    assert emissions_res.json()["scoring_weights"]["emissions"] == 0.70

def test_what_if_simulator_single_recommendation(auth_headers):
    list_res = client.get("/api/optimization", headers=auth_headers)
    target_id = list_res.json()["recommendations"][0]["id"]

    # Test backward-compatible endpoint
    post_res = client.post(f"/api/optimization/{target_id}/simulate", headers=auth_headers)
    assert post_res.status_code == 200
    sim_data = post_res.json()
    assert sim_data["status"] == "simulation_successful"
    assert "simulation" in sim_data
    sim = sim_data["simulation"]
    assert sim["results"]["is_read_only_simulation"] is True
    assert sim["results"]["live_resources_modified"] is False
    assert sim["results"]["monthly_cost_saving"] > 0

def test_what_if_simulator_custom_scenarios(auth_headers):
    # 1. Rightsizing scenario
    payload_rightsizing = {
        "scenario_type": "RIGHTSIZING",
        "name": "Fleet 35% Downsizing Scenario",
        "downsize_percentage": 35.0,
        "target_resource_count": 5,
    }
    res = client.post("/api/optimization/simulate", json=payload_rightsizing, headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["scenario_type"] == "RIGHTSIZING"
    assert data["results"]["monthly_cost_saving"] > 0
    assert data["results"]["monthly_carbon_saving_kg"] > 0
    sim_id = data["id"]

    # 2. Scheduled Idle scenario
    payload_idle = {
        "scenario_type": "SCHEDULED_IDLE",
        "name": "Weekend and Night Non-Prod Shutdown",
        "off_hours_per_week": 60.0,
        "target_resource_count": 8,
    }
    res_idle = client.post("/api/optimization/simulate", json=payload_idle, headers=auth_headers)
    assert res_idle.status_code == 200
    assert res_idle.json()["results"]["monthly_carbon_saving_kg"] > 0

    # 3. Savings Plan scenario
    payload_sp = {
        "scenario_type": "SAVINGS_PLAN",
        "name": "3-Year Compute Savings Plan (All Upfront)",
        "term_years": 3,
        "coverage_pct": 80.0,
    }
    res_sp = client.post("/api/optimization/simulate", json=payload_sp, headers=auth_headers)
    assert res_sp.status_code == 200
    assert res_sp.json()["results"]["monthly_cost_saving"] > 0
    # Financial plan does not physically reduce carbon without hardware change
    assert res_sp.json()["results"]["monthly_carbon_saving_kg"] == 0.0

    # 4. List simulations
    sim_list = client.get("/api/optimization/simulations", headers=auth_headers)
    assert sim_list.status_code == 200
    sims = sim_list.json()
    assert len(sims) >= 3

    # 5. Detail simulation
    sim_detail = client.get(f"/api/optimization/simulations/{sim_id}", headers=auth_headers)
    assert sim_detail.status_code == 200
    assert sim_detail.json()["id"] == sim_id

def test_savings_ledger_lifecycle_and_caveats(auth_headers):
    # 1. Summary
    sum_res = client.get("/api/optimization/ledger/summary", headers=auth_headers)
    assert sum_res.status_code == 200
    sum_data = sum_res.json()
    assert "total_expected_monthly_cost_saving" in sum_data
    assert "total_verified_monthly_cost_saving" in sum_data
    assert "cost_realization_rate_pct" in sum_data
    assert "entries_with_caveats_count" in sum_data

    # 2. List entries
    list_res = client.get("/api/optimization/ledger", headers=auth_headers)
    assert list_res.status_code == 200
    entries = list_res.json()
    assert len(entries) >= 2
    # Verify caveats field is populated
    assert any(e.get("caveats") for e in entries)

    # 3. Create entry
    new_entry_payload = {
        "title": "Automated S3 Lifecycle Policy Rule",
        "category": "STORAGE_OPTIMIZATION",
        "resource_id": "s3-analytics-data-lake",
        "savings_type": "EXPECTED",
        "status": "PLANNED",
        "expected_monthly_cost_saving": 450.0,
        "expected_monthly_carbon_saving_kg": 0.0,
        "caveats": "Requires 90-day cold object lifecycle verification before transitioning to Glacier Deep Archive.",
    }
    create_res = client.post("/api/optimization/ledger", json=new_entry_payload, headers=auth_headers)
    assert create_res.status_code == 200
    created_id = create_res.json()["id"]

    # 4. Patch with verified measurements
    patch_payload = {
        "status": "REALIZED",
        "verified_cost_saving": 425.0,
        "caveats": "30-day initial transition cycle completed with 94.4% realized savings.",
        "notes": "Verified by DevOps lead.",
    }
    patch_res = client.patch(f"/api/optimization/ledger/{created_id}", json=patch_payload, headers=auth_headers)
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "updated"

def test_empty_organization_optimization(empty_org_headers):
    # Recommendations for empty org
    res = client.get("/api/optimization", headers=empty_org_headers)
    assert res.status_code == 200
    assert res.json()["recommendations"] == []
    assert res.json()["summary"]["total_recommendations"] == 0

    # Ledger summary for empty org
    ledger_sum = client.get("/api/optimization/ledger/summary", headers=empty_org_headers)
    assert ledger_sum.status_code == 200
    assert ledger_sum.json()["total_entries"] == 0
    assert ledger_sum.json()["cost_realization_rate_pct"] == 0.0

    # Simulations for empty org
    sims = client.get("/api/optimization/simulations", headers=empty_org_headers)
    assert sims.status_code == 200
    assert sims.json() == []

def test_multi_tenant_isolation_optimization(auth_headers, empty_org_headers):
    # Org A creates a simulation
    sim_res = client.post(
        "/api/optimization/simulate",
        json={"scenario_type": "RIGHTSIZING", "name": "Org A Confidential Scenario"},
        headers=auth_headers,
    )
    assert sim_res.status_code == 200
    org_a_sim_id = sim_res.json()["id"]

    # Org B (empty org) attempts to view Org A's simulation
    res_b = client.get(f"/api/optimization/simulations/{org_a_sim_id}", headers=empty_org_headers)
    assert res_b.status_code == 404

    # Org A creates a ledger entry
    ledger_res = client.post(
        "/api/optimization/ledger",
        json={"title": "Org A Secret Savings", "resource_id": "res-secret"},
        headers=auth_headers,
    )
    assert ledger_res.status_code == 200
    org_a_ledger_id = ledger_res.json()["id"]

    # Org B attempts to patch Org A's ledger entry
    patch_b = client.patch(
        f"/api/optimization/ledger/{org_a_ledger_id}",
        json={"status": "REALIZED"},
        headers=empty_org_headers,
    )
    assert patch_b.status_code == 404
