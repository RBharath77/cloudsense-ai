import json
from datetime import datetime
from typing import Any
from sqlalchemy.orm import Session
from ..models import TerraformPlanAnalysis, AuditLog
from .carbon_service import REGIONAL_EMISSION_FACTORS

# Standard hyperscaler benchmark on-demand pricing catalog (2025/2026 baseline, 730h/mo)
INSTANCE_CATALOG_RATES: dict[str, dict[str, float]] = {
    # AWS
    "t3.nano": {"monthly_cost": 3.80, "tdp_watts": 10.0},
    "t3.micro": {"monthly_cost": 7.60, "tdp_watts": 15.0},
    "t3.small": {"monthly_cost": 15.20, "tdp_watts": 30.0},
    "t3.medium": {"monthly_cost": 30.37, "tdp_watts": 60.0},
    "t3.large": {"monthly_cost": 60.74, "tdp_watts": 120.0},
    "t3.xlarge": {"monthly_cost": 121.47, "tdp_watts": 240.0},
    "t3.2xlarge": {"monthly_cost": 242.94, "tdp_watts": 480.0},
    "t4g.nano": {"monthly_cost": 3.07, "tdp_watts": 8.0},
    "t4g.micro": {"monthly_cost": 6.13, "tdp_watts": 12.0},
    "t4g.small": {"monthly_cost": 12.26, "tdp_watts": 24.0},
    "t4g.medium": {"monthly_cost": 24.53, "tdp_watts": 48.0},
    "t4g.large": {"monthly_cost": 49.06, "tdp_watts": 96.0},
    "m5.large": {"monthly_cost": 70.08, "tdp_watts": 110.0},
    "m5.xlarge": {"monthly_cost": 140.16, "tdp_watts": 220.0},
    "m5.2xlarge": {"monthly_cost": 280.32, "tdp_watts": 440.0},
    "m5.4xlarge": {"monthly_cost": 560.64, "tdp_watts": 880.0},
    "c5.large": {"monthly_cost": 62.05, "tdp_watts": 100.0},
    "c5.xlarge": {"monthly_cost": 124.10, "tdp_watts": 200.0},
    "c5.2xlarge": {"monthly_cost": 248.20, "tdp_watts": 400.0},
    "r5.large": {"monthly_cost": 91.98, "tdp_watts": 130.0},
    "r5.xlarge": {"monthly_cost": 183.96, "tdp_watts": 260.0},
    "p4d.24xlarge": {"monthly_cost": 23922.10, "tdp_watts": 3200.0},
    # GCP
    "e2-micro": {"monthly_cost": 6.11, "tdp_watts": 12.0},
    "e2-small": {"monthly_cost": 12.23, "tdp_watts": 24.0},
    "e2-medium": {"monthly_cost": 24.46, "tdp_watts": 48.0},
    "e2-standard-2": {"monthly_cost": 48.92, "tdp_watts": 96.0},
    "e2-standard-4": {"monthly_cost": 97.85, "tdp_watts": 192.0},
    "n2-standard-2": {"monthly_cost": 71.18, "tdp_watts": 110.0},
    "n2-standard-4": {"monthly_cost": 142.35, "tdp_watts": 220.0},
    # Azure
    "Standard_B1s": {"monthly_cost": 7.59, "tdp_watts": 15.0},
    "Standard_B2s": {"monthly_cost": 30.37, "tdp_watts": 60.0},
    "Standard_D2s_v5": {"monthly_cost": 70.08, "tdp_watts": 110.0},
    "Standard_D4s_v5": {"monthly_cost": 140.16, "tdp_watts": 220.0},
}

DEFAULT_POLICIES = {
    "max_monthly_cost_delta_usd": 500.0,
    "max_single_resource_cost_usd": 1000.0,
    "disallowed_instance_types": ["p4d.24xlarge", "m5.24xlarge", "c5.24xlarge"],
    "require_cost_tags": ["Environment", "Owner"],
    "disallowed_regions": [],
}

def get_grid_intensity(region: str) -> float:
    reg = region.lower().strip()
    for factor in REGIONAL_EMISSION_FACTORS:
        if factor["region"].lower() == reg:
            return float(factor["intensity_g_per_kwh"])
    return 370.0  # US national average baseline

def estimate_resource_pricing(resource_type: str, values: dict[str, Any], region: str = "us-east-1") -> dict[str, float]:
    """Calculate benchmark monthly cost and carbon footprint for resource attributes."""
    if not values:
        return {"monthly_cost": 0.0, "monthly_emissions_kg": 0.0}

    res_type = resource_type.lower()
    instance_type = (
        values.get("instance_type")
        or values.get("machine_type")
        or values.get("size")
        or values.get("vm_size")
        or ""
    )
    
    cost = 0.0
    power_watts = 0.0

    # 1. Compute Instances
    if "instance" in res_type or "virtual_machine" in res_type:
        lookup = INSTANCE_CATALOG_RATES.get(instance_type, {"monthly_cost": 55.0, "tdp_watts": 90.0})
        cost = lookup["monthly_cost"]
        power_watts = lookup["tdp_watts"]

    # 2. Storage / Volumes
    elif "ebs_volume" in res_type or "managed_disk" in res_type or "compute_disk" in res_type:
        size_gb = float(values.get("size") or values.get("disk_size_gb") or 100.0)
        vol_type = str(values.get("type") or "gp3").lower()
        unit_rate = 0.08 if "gp3" in vol_type else (0.10 if "gp2" in vol_type else 0.12)
        cost = round(size_gb * unit_rate, 2)
        power_watts = max(1.0, size_gb * 0.015)

    # 3. Object Storage Buckets
    elif "s3_bucket" in res_type or "storage_bucket" in res_type or "storage_account" in res_type:
        cost = 5.0  # Baseline storage maintenance cost
        power_watts = 2.0

    # 4. Databases
    elif "db_instance" in res_type or "sql_database" in res_type:
        db_class = str(values.get("instance_class") or instance_type or "db.t3.medium")
        clean_class = db_class.replace("db.", "")
        lookup = INSTANCE_CATALOG_RATES.get(clean_class, {"monthly_cost": 65.0, "tdp_watts": 100.0})
        cost = lookup["monthly_cost"] * 1.5  # Managed DB license and management overhead
        power_watts = lookup["tdp_watts"]

    # 5. Load Balancers / NAT Gateways
    elif "nat_gateway" in res_type:
        cost = 32.85
        power_watts = 15.0
    elif "lb" in res_type or "alb" in res_type or "load_balancer" in res_type:
        cost = 16.42
        power_watts = 10.0
    else:
        # Default nominal benchmark
        cost = 10.0
        power_watts = 10.0

    # Compute monthly carbon emissions: (Watts / 1000) * 730h * PUE(1.15) * Intensity / 1000
    grid_intensity = get_grid_intensity(region)
    kwh = (power_watts / 1000.0) * 730.0 * 1.15
    emissions_kg = round((kwh * grid_intensity) / 1000.0, 2)

    return {"monthly_cost": round(cost, 2), "monthly_emissions_kg": emissions_kg}


def evaluate_ci_cd_policies(
    cost_delta_usd: float,
    emissions_delta_kgco2e: float,
    resource_changes: list[dict[str, Any]],
    policies: dict[str, Any] | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    """
    Evaluate shift-left FinOps & GreenOps policies on pre-deployment plan changes.
    Returns (status, violations), where status is PASSED, WARNING, or BLOCKED.
    """
    active_policies = dict(DEFAULT_POLICIES)
    if policies:
        active_policies.update(policies)

    violations: list[dict[str, Any]] = []

    # 1. Budget Max Delta Policy
    max_budget_delta = float(active_policies.get("max_monthly_cost_delta_usd", 500.0))
    if cost_delta_usd > max_budget_delta:
        violations.append({
            "rule": "MAX_MONTHLY_BUDGET_EXCEEDED",
            "severity": "BLOCKING" if cost_delta_usd > (max_budget_delta * 2) else "WARNING",
            "message": f"Projected monthly cost delta (+${cost_delta_usd:.2f}) exceeds policy budget limit of +${max_budget_delta:.2f}/month.",
            "target": "Plan Summary",
        })

    # 2. Disallowed Oversized Instance Types
    disallowed_types = [t.lower() for t in active_policies.get("disallowed_instance_types", [])]
    for change in resource_changes:
        after_vals = change.get("after") or {}
        inst_type = str(
            after_vals.get("instance_type")
            or after_vals.get("machine_type")
            or after_vals.get("vm_size")
            or ""
        ).lower()
        if inst_type and inst_type in disallowed_types:
            violations.append({
                "rule": "DISALLOWED_EXPENSIVE_INSTANCE_TYPE",
                "severity": "BLOCKING",
                "message": f"Resource '{change.get('address')}' requests unapproved expensive instance type '{inst_type}'. Requires FinOps architecture approval.",
                "target": change.get("address", "Resource"),
            })

    # 3. Mandatory Cost-Allocation Tags
    required_tags = active_policies.get("require_cost_tags", [])
    for change in resource_changes:
        if "create" in change.get("actions", []) or "update" in change.get("actions", []):
            after_vals = change.get("after") or {}
            tags = after_vals.get("tags") or after_vals.get("labels") or {}
            missing_tags = [t for t in required_tags if t not in tags]
            if missing_tags:
                violations.append({
                    "rule": "MISSING_MANDATORY_COST_TAGS",
                    "severity": "WARNING",
                    "message": f"Resource '{change.get('address')}' is missing mandatory FinOps allocation tags: {', '.join(missing_tags)}.",
                    "target": change.get("address", "Resource"),
                })

    # 4. Regional Restrictions
    disallowed_regions = [r.lower() for r in active_policies.get("disallowed_regions", [])]
    if disallowed_regions:
        for change in resource_changes:
            after_vals = change.get("after") or {}
            reg = str(after_vals.get("region") or after_vals.get("location") or "").lower()
            if reg and reg in disallowed_regions:
                violations.append({
                    "rule": "DISALLOWED_DEPLOYMENT_REGION",
                    "severity": "BLOCKING",
                    "message": f"Resource '{change.get('address')}' deployed to disallowed region '{reg}'.",
                    "target": change.get("address", "Resource"),
                })

    # Calculate overall status
    if any(v["severity"] == "BLOCKING" for v in violations):
        status = "BLOCKED"
    elif any(v["severity"] == "WARNING" for v in violations):
        status = "WARNING"
    else:
        status = "PASSED"

    return status, violations


def parse_and_analyze_terraform_plan(
    db: Session,
    organization_id: str,
    user_id: str | None,
    plan_payload: dict[str, Any],
    plan_name: str | None = None,
    policies: dict[str, Any] | None = None,
) -> TerraformPlanAnalysis:
    """
    Ingest, parse, calculate cost & carbon delta, evaluate policies,
    and persist TerraformPlanAnalysis for an organization.
    """
    resource_changes_raw = plan_payload.get("resource_changes", [])
    
    created_count = 0
    updated_count = 0
    deleted_count = 0
    
    total_cost_before = 0.0
    total_cost_after = 0.0
    total_emissions_before = 0.0
    total_emissions_after = 0.0

    parsed_changes = []

    for rc in resource_changes_raw:
        actions = rc.get("change", {}).get("actions", [])
        res_type = rc.get("type", "unknown_resource")
        address = rc.get("address", rc.get("name", "unknown"))
        provider_name = rc.get("provider_name", "aws")
        
        before_vals = rc.get("change", {}).get("before") or {}
        after_vals = rc.get("change", {}).get("after") or {}

        # Default region detection
        region = (
            after_vals.get("region")
            or before_vals.get("region")
            or after_vals.get("location")
            or before_vals.get("location")
            or "us-east-1"
        )

        cost_before_calc = 0.0
        emissions_before_calc = 0.0
        cost_after_calc = 0.0
        emissions_after_calc = 0.0

        if "no-op" in actions or actions == ["read"]:
            continue

        if "create" in actions:
            created_count += 1
            after_pricing = estimate_resource_pricing(res_type, after_vals, region)
            cost_after_calc = after_pricing["monthly_cost"]
            emissions_after_calc = after_pricing["monthly_emissions_kg"]
        elif "delete" in actions:
            deleted_count += 1
            before_pricing = estimate_resource_pricing(res_type, before_vals, region)
            cost_before_calc = before_pricing["monthly_cost"]
            emissions_before_calc = before_pricing["monthly_emissions_kg"]
        elif "update" in actions:
            updated_count += 1
            before_pricing = estimate_resource_pricing(res_type, before_vals, region)
            after_pricing = estimate_resource_pricing(res_type, after_vals, region)
            cost_before_calc = before_pricing["monthly_cost"]
            emissions_before_calc = before_pricing["monthly_emissions_kg"]
            cost_after_calc = after_pricing["monthly_cost"]
            emissions_after_calc = after_pricing["monthly_emissions_kg"]

        total_cost_before += cost_before_calc
        total_cost_after += cost_after_calc
        total_emissions_before += emissions_before_calc
        total_emissions_after += emissions_after_calc

        parsed_changes.append({
            "address": address,
            "type": res_type,
            "actions": actions,
            "provider": provider_name,
            "region": region,
            "cost_before": cost_before_calc,
            "cost_after": cost_after_calc,
            "cost_delta": round(cost_after_calc - cost_before_calc, 2),
            "emissions_before": emissions_before_calc,
            "emissions_after": emissions_after_calc,
            "emissions_delta": round(emissions_after_calc - emissions_before_calc, 2),
            "before": before_vals,
            "after": after_vals,
        })

    cost_delta = round(total_cost_after - total_cost_before, 2)
    emissions_delta = round(total_emissions_after - total_emissions_before, 2)

    # Evaluate Policies
    policy_status, violations = evaluate_ci_cd_policies(
        cost_delta_usd=cost_delta,
        emissions_delta_kgco2e=emissions_delta,
        resource_changes=parsed_changes,
        policies=policies,
    )

    name = plan_name or f"Plan Analysis {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
    provider_detected = "aws"
    if any("google" in c.get("provider", "") for c in parsed_changes):
        provider_detected = "gcp"
    elif any("azure" in c.get("provider", "") for c in parsed_changes):
        provider_detected = "azure"

    analysis = TerraformPlanAnalysis(
        organization_id=organization_id,
        created_by_user_id=user_id,
        plan_name=name,
        provider=provider_detected,
        resources_created=created_count,
        resources_updated=updated_count,
        resources_deleted=deleted_count,
        monthly_cost_before_usd=round(total_cost_before, 2),
        monthly_cost_after_usd=round(total_cost_after, 2),
        monthly_cost_delta_usd=cost_delta,
        monthly_emissions_delta_kgco2e=emissions_delta,
        policy_status=policy_status,
        policy_violations=json.dumps(violations),
        raw_plan_summary=json.dumps({
            "changes_count": len(parsed_changes),
            "changes": parsed_changes[:50],  # Keep top 50 in summary
            "is_simulated_benchmark": True,
            "pricing_source": "AWS/GCP/Azure 2025/2026 On-Demand Public Catalog Benchmarks",
            "carbon_source": "EPA eGRID 2024 / EEA 2023 Grid Intensity Factors",
        }),
    )

    db.add(analysis)

    # Audit Log
    db.add(
        AuditLog(
            organization_id=organization_id,
            user_id=user_id,
            action="TERRAFORM_PLAN_ANALYZED",
            resource_type="TerraformPlanAnalysis",
            resource_id=analysis.id,
            detail=json.dumps({
                "plan_name": name,
                "cost_delta_usd": cost_delta,
                "emissions_delta_kgco2e": emissions_delta,
                "policy_status": policy_status,
                "violations_count": len(violations),
            }),
            status="SUCCESS",
        )
    )

    db.commit()
    db.refresh(analysis)
    return analysis


def list_terraform_analyses(db: Session, organization_id: str) -> list[dict[str, Any]]:
    analyses = (
        db.query(TerraformPlanAnalysis)
        .filter(TerraformPlanAnalysis.organization_id == organization_id)
        .order_by(TerraformPlanAnalysis.created_at.desc())
        .limit(100)
        .all()
    )
    result = []
    for a in analyses:
        violations = []
        try:
            violations = json.loads(a.policy_violations)
        except Exception:
            pass

        result.append({
            "id": a.id,
            "plan_name": a.plan_name,
            "provider": a.provider,
            "resources_created": a.resources_created,
            "resources_updated": a.resources_updated,
            "resources_deleted": a.resources_deleted,
            "monthly_cost_before_usd": a.monthly_cost_before_usd,
            "monthly_cost_after_usd": a.monthly_cost_after_usd,
            "monthly_cost_delta_usd": a.monthly_cost_delta_usd,
            "monthly_emissions_delta_kgco2e": a.monthly_emissions_delta_kgco2e,
            "policy_status": a.policy_status,
            "violations": violations,
            "created_at": a.created_at.isoformat(),
        })
    return result


def get_terraform_analysis_detail(db: Session, organization_id: str, analysis_id: str) -> dict[str, Any] | None:
    analysis = (
        db.query(TerraformPlanAnalysis)
        .filter(
            TerraformPlanAnalysis.id == analysis_id,
            TerraformPlanAnalysis.organization_id == organization_id,
        )
        .first()
    )
    if not analysis:
        return None

    violations = []
    summary = {}
    try:
        violations = json.loads(analysis.policy_violations)
    except Exception:
        pass
    try:
        summary = json.loads(analysis.raw_plan_summary)
    except Exception:
        pass

    return {
        "id": analysis.id,
        "plan_name": analysis.plan_name,
        "provider": analysis.provider,
        "resources_created": analysis.resources_created,
        "resources_updated": analysis.resources_updated,
        "resources_deleted": analysis.resources_deleted,
        "monthly_cost_before_usd": analysis.monthly_cost_before_usd,
        "monthly_cost_after_usd": analysis.monthly_cost_after_usd,
        "monthly_cost_delta_usd": analysis.monthly_cost_delta_usd,
        "monthly_emissions_delta_kgco2e": analysis.monthly_emissions_delta_kgco2e,
        "policy_status": analysis.policy_status,
        "violations": violations,
        "summary": summary,
        "created_at": analysis.created_at.isoformat(),
    }
