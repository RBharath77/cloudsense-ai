from datetime import datetime,timedelta
import random
import json
from sqlalchemy.orm import Session
from .database import Base, engine, SessionLocal
from .models import *
from .auth import hash_password

def seed_supplemental_entities(db: Session, org_id: str, user_id: str | None = None):
    now = datetime.utcnow()
    # 1. System Jobs (Phase 11)
    if not db.query(SystemJobExecution).filter_by(organization_id=org_id).first():
        db.add(SystemJobExecution(
            organization_id=org_id,
            job_type="ANOMALY_SWEEP",
            status="SUCCEEDED",
            triggered_by="SYSTEM_SCHEDULER",
            payload='{"lookback_days": 14}',
            result='{"anomalies_evaluated": 120, "anomalies_detected": 7}',
            execution_time_ms=342,
            created_at=now - timedelta(hours=2),
            started_at=now - timedelta(hours=2),
            completed_at=now - timedelta(hours=2) + timedelta(milliseconds=342),
        ))
        db.add(SystemJobExecution(
            organization_id=org_id,
            job_type="BUDGET_AUDIT",
            status="SUCCEEDED",
            triggered_by="SYSTEM_SCHEDULER",
            payload='{}',
            result='{"budgets_audited": 3, "breaches_flagged": 0}',
            execution_time_ms=189,
            created_at=now - timedelta(hours=6),
            started_at=now - timedelta(hours=6),
            completed_at=now - timedelta(hours=6) + timedelta(milliseconds=189),
        ))

    # 2. Webhook Endpoint (Phase 11)
    if not db.query(WebhookEndpoint).filter_by(organization_id=org_id).first():
        db.add(WebhookEndpoint(
            organization_id=org_id,
            name="FinOps Incident Slack Webhook",
            url="https://hooks.slack.com/services/T00000000/B00000000/mock_finops_alert_token",
            secret_token="c10ud53n53_hmac_53cr37_70k3n_32by735",
            events='["ANOMALY_DETECTED","BUDGET_BREACHED","ACTION_PROPOSED"]',
            is_active=True,
            last_dispatched_at=now - timedelta(hours=1),
            last_status_code=200,
        ))

    # 3. Automated Remediation Action (Phase 11)
    if not db.query(AutomatedAction).filter_by(organization_id=org_id).first():
        db.add(AutomatedAction(
            organization_id=org_id,
            created_by_user_id=user_id,
            action_type="RIGHTSIZE_UNDERUTILIZED_EC2",
            target_resource_id="aws-prod-compute-001",
            target_resource_name="aws-001",
            provider="AWS",
            estimated_monthly_saving_usd=145.0,
            risk_level="LOW",
            status="PROPOSED",
            is_simulation=True,
            rollback_plan=json.dumps({
                "type": "REVERT_INSTANCE_TYPE",
                "original_type": "m5.2xlarge",
                "proposed_type": "m5.xlarge",
                "steps": ["Stop instance", "Modify attribute instance_type to m5.2xlarge", "Start instance"]
            }),
            execution_notes="Proposed based on 90-day peak CPU utilization below 28%.",
        ))

    # 4. Terraform Plan Analysis (Phase 12)
    if not db.query(TerraformPlanAnalysis).filter_by(organization_id=org_id).first():
        db.add(TerraformPlanAnalysis(
            organization_id=org_id,
            created_by_user_id=user_id,
            plan_name="Q4 Web Infrastructure Expansion",
            provider="aws",
            resources_created=3,
            resources_updated=1,
            resources_deleted=0,
            monthly_cost_before_usd=120.50,
            monthly_cost_after_usd=197.24,
            monthly_cost_delta_usd=76.74,
            monthly_emissions_delta_kgco2e=18.2,
            policy_status="PASSED",
            policy_violations="[]",
            raw_plan_summary=json.dumps({
                "changes_count": 4,
                "is_simulated_benchmark": True,
                "pricing_source": "AWS 2025/2026 On-Demand Catalog",
                "carbon_source": "EPA eGRID 2024 / EEA 2023",
            }),
        ))

    # 5. Kubernetes Container Allocations (Phase 12)
    if not db.query(KubernetesCostAllocation).filter_by(organization_id=org_id).first():
        today = now.strftime("%Y-%m-%d")
        for item in [
            {"ns": "ingress-system", "w": "ingress-nginx-controller", "t": "DaemonSet", "c_a": 2.0, "c_u": 1.4, "m_a": 4294967296, "m_u": 3006477107, "cost": 128.50, "eff": 70.0, "idle": 38.55},
            {"ns": "payments", "w": "payment-processing-engine", "t": "Deployment", "c_a": 8.0, "c_u": 2.1, "m_a": 17179869184, "m_u": 6657199308, "cost": 486.20, "eff": 32.5, "idle": 328.19},
            {"ns": "frontend", "w": "customer-portal-spa", "t": "Deployment", "c_a": 4.0, "c_u": 2.9, "m_a": 8589934592, "m_u": 6012954214, "cost": 242.00, "eff": 71.2, "idle": 69.70},
            {"ns": "analytics", "w": "spark-worker-daemon", "t": "StatefulSet", "c_a": 12.0, "c_u": 4.2, "m_a": 34359738368, "m_u": 15569256448, "cost": 765.40, "eff": 40.1, "idle": 458.47},
        ]:
            db.add(KubernetesCostAllocation(
                organization_id=org_id,
                cluster_name="production-eks-cluster",
                namespace=item["ns"],
                workload_name=item["w"],
                workload_type=item["t"],
                cpu_allocated_cores=item["c_a"],
                cpu_usage_cores=item["c_u"],
                memory_allocated_bytes=item["m_a"],
                memory_usage_bytes=item["m_u"],
                efficiency_score=item["eff"],
                monthly_allocated_cost_usd=item["cost"],
                monthly_idle_cost_usd=item["idle"],
                is_simulated=True,
                recorded_date=today,
            ))

    db.commit()

def seed():
    Base.metadata.create_all(engine); db=SessionLocal()
    try:
        org=db.query(Organization).first()
        u=db.query(User).filter_by(role="ADMIN").first()
        if org:
            seed_supplemental_entities(db, org.id, u.id if u else None)
        if org and not db.query(SavingsLedger).filter_by(organization_id=org.id).first():
            now=datetime.utcnow()
            db.add(SavingsLedger(
                organization_id=org.id,
                resource_id="aws-prod-compute-001",
                title="Q3 EC2 Rightsizing Initiative (US-East-1)",
                category="RIGHTSIZING",
                savings_type="VERIFIED",
                status="REALIZED",
                expected_monthly_cost_saving=640.0,
                verified_cost_saving=612.50,
                expected_monthly_carbon_saving_kg=48.0,
                verified_carbon_saving_kg=46.2,
                measurement_window_start=now-timedelta(days=60),
                measurement_window_end=now-timedelta(days=30),
                caveats="Excludes 3-day stress test window in August where temporary larger instance was booted.",
                notes="Successfully downsized 8 worker nodes from c5.2xlarge to c5.xlarge."
            ))
            db.add(SavingsLedger(
                organization_id=org.id,
                resource_id="azure-db-staging-002",
                title="Azure Non-Prod Off-Hours Shutdown Schedule",
                category="IDLE_RESOURCE",
                savings_type="VERIFIED",
                status="REALIZED",
                expected_monthly_cost_saving=320.0,
                verified_cost_saving=345.0,
                expected_monthly_carbon_saving_kg=28.5,
                verified_carbon_saving_kg=30.1,
                measurement_window_start=now-timedelta(days=45),
                measurement_window_end=now-timedelta(days=15),
                caveats="Savings exceeded forecast due to holiday weekend shutdown.",
                notes="Automated runbooks stop dev VMs between 8pm and 7am."
            ))
            db.add(SavingsLedger(
                organization_id=org.id,
                resource_id="gcp-analytics-pool-003",
                title="GCP BigQuery Slot Commitment / 1-Yr Reservation",
                category="COMMITMENT_PURCHASE",
                savings_type="EXPECTED",
                status="PLANNED",
                expected_monthly_cost_saving=1150.0,
                verified_cost_saving=0.0,
                expected_monthly_carbon_saving_kg=0.0,
                verified_carbon_saving_kg=0.0,
                caveats="Financial pricing discount; zero direct hardware energy reduction.",
                notes="Pending FinOps executive approval for 1-year commitment."
            ))
            db.commit()
        if db.query(User).first(): return
        org=Organization(name="NovaTech Solutions"); db.add(org); db.flush()
        user=User(email="admin@cloudsense.ai",password_hash=hash_password("CloudSense@123"),role="ADMIN",organization_id=org.id); db.add(user)
        accounts=[]
        for p,n,c,r in [("AWS","AWS Production",28450,"us-east-1"),("Azure","Azure Analytics",10240,"eastus"),("GCP","GCP ML Platform",4160,"us-central1")]:
            a=CloudAccount(organization_id=org.id,provider=p,name=n,identifier=f"demo-{p.lower()}-001",region=r,last_sync=datetime.utcnow()); db.add(a); db.flush(); accounts.append((a,c))
        random.seed(42); now=datetime.utcnow()
        services={"AWS":["EC2","S3","RDS","Lambda"],"Azure":["VM","Blob Storage","SQL Database","Functions"],"GCP":["Compute Engine","Cloud Storage","BigQuery","GKE"]}
        resources=[]
        for a,total in accounts:
            for i in range(40):
                util=random.uniform(10,95); cost=total/40*random.uniform(.5,1.5)
                res=CloudResource(organization_id=org.id,account_id=a.id,provider=a.provider,name=f"{a.provider.lower()}-{i+1:03}",type=random.choice(["compute","database","storage"]),region=a.region,status="RUNNING",cpu=util,memory=random.uniform(20,90),utilization=util,monthly_cost=cost,health=random.uniform(82,100)); db.add(res); db.flush(); resources.append(res)
                for d in range(90):
                    dt=now-timedelta(days=89-d)
                    base=util*(1+0.12*random.sin(d/7)) if False else util
                    db.add(MetricRecord(resource_id=res.id,timestamp=dt,cpu=max(1,min(100,base+random.uniform(-8,8))),memory=max(1,min(100,res.memory+random.uniform(-8,8))),network=random.uniform(10,100),requests=random.uniform(100,10000)))
                    db.add(CostRecord(organization_id=org.id,provider=a.provider,service=random.choice(services[a.provider]),region=a.region,resource_id=res.id,amount=max(.5,cost/30*random.uniform(.7,1.3)),recorded_at=dt))
        for i in range(7):
            r=resources[i*7]; db.add(Anomaly(organization_id=org.id,provider=r.provider,resource_id=r.id,metric="cost",severity=random.choice(["HIGH","MEDIUM","CRITICAL"]),timestamp=now-timedelta(hours=i*7),score=random.uniform(.7,1),financial_impact=random.uniform(120,900),reason="Cost/utilization pattern deviates from learned baseline.",recommendation="Review recent resource and traffic changes."))
        for r in resources:
            if r.utilization<30:
                save=round(r.monthly_cost*.45,2)
                cat="IDLE_RESOURCE" if r.utilization<15 else "RIGHTSIZING"
                action_text="Stop or decommission idle instance during off-hours." if cat=="IDLE_RESOURCE" else "Downsize instance family by one tier to rightsize compute."
                evidence_json=json.dumps({
                    "metric": "cpu",
                    "avg_cpu_pct": round(r.utilization, 1),
                    "max_cpu_pct": round(r.utilization * 1.3, 1),
                    "sample_count": 90,
                    "observation_window": "90d",
                    "resource_name": r.name,
                    "provider": r.provider,
                    "region": r.region,
                })
                carbon_save=round(save * 0.08, 2)
                db.add(Recommendation(
                    organization_id=org.id,
                    resource_id=r.id,
                    current_cost=r.monthly_cost,
                    problem=f"Underutilized compute capacity ({r.utilization:.1f}% avg utilization)",
                    recommendation=action_text,
                    action=action_text,
                    monthly_saving=save,
                    yearly_saving=round(save*12,2),
                    risk="LOW",
                    confidence=.89,
                    category=cat,
                    evidence=evidence_json,
                    assumptions="Workload CPU steady-state remains under 35%; peak memory fits in smaller tier.",
                    trade_offs="Reduces burst CPU buffer by ~50%; requires brief maintenance window to apply.",
                    monthly_carbon_saving_kg=carbon_save
                ))
        db.add(SavingsLedger(
            organization_id=org.id,
            resource_id="aws-prod-compute-001",
            title="Q3 EC2 Rightsizing Initiative (US-East-1)",
            category="RIGHTSIZING",
            savings_type="VERIFIED",
            status="REALIZED",
            expected_monthly_cost_saving=640.0,
            verified_cost_saving=612.50,
            expected_monthly_carbon_saving_kg=48.0,
            verified_carbon_saving_kg=46.2,
            measurement_window_start=now-timedelta(days=60),
            measurement_window_end=now-timedelta(days=30),
            caveats="Excludes 3-day stress test window in August where temporary larger instance was booted.",
            notes="Successfully downsized 8 worker nodes from c5.2xlarge to c5.xlarge."
        ))
        db.add(SavingsLedger(
            organization_id=org.id,
            resource_id="azure-db-staging-002",
            title="Azure Non-Prod Off-Hours Shutdown Schedule",
            category="IDLE_RESOURCE",
            savings_type="VERIFIED",
            status="REALIZED",
            expected_monthly_cost_saving=320.0,
            verified_cost_saving=345.0,
            expected_monthly_carbon_saving_kg=28.5,
            verified_carbon_saving_kg=30.1,
            measurement_window_start=now-timedelta(days=45),
            measurement_window_end=now-timedelta(days=15),
            caveats="Savings exceeded forecast due to holiday weekend shutdown.",
            notes="Automated runbooks stop dev VMs between 8pm and 7am."
        ))
        db.add(SavingsLedger(
            organization_id=org.id,
            resource_id="gcp-analytics-pool-003",
            title="GCP BigQuery Slot Commitment / 1-Yr Reservation",
            category="COMMITMENT_PURCHASE",
            savings_type="EXPECTED",
            status="PLANNED",
            expected_monthly_cost_saving=1150.0,
            verified_cost_saving=0.0,
            expected_monthly_carbon_saving_kg=0.0,
            verified_carbon_saving_kg=0.0,
            caveats="Financial pricing discount; zero direct hardware energy reduction.",
            notes="Pending FinOps executive approval for 1-year commitment."
        ))
        for r in resources[:8]: db.add(SecurityFinding(organization_id=org.id,provider=r.provider,resource_id=r.id,severity="HIGH" if r.id==resources[0].id else "MEDIUM",risk="Configuration exposure",description="Demo finding: resource configuration requires review.",recommendation="Restrict public access and enforce encryption.",status="OPEN"))
        for p in ["AWS","Azure","GCP"]: db.add(SLARecord(organization_id=org.id,service=f"{p} platform",availability=random.choice([99.9,99.95,99.99]),latency=random.uniform(40,120),downtime=random.uniform(2,20),incidents=random.randint(0,3),breached=False,timestamp=now))
        for p,c in [("AWS",28.45),("Azure",10.24),("GCP",4.16)]: db.add(CarbonRecord(organization_id=org.id,provider=p,region="primary",service="all",co2_kg=c,recorded_at=now,source=f"{p} Carbon Footprint Tool",scope="Scope 2",record_type="DEMO",unit="kgCO2e",reporting_period="2026-10",methodology="Initial baseline demonstration snapshot"))
        db.add(CarbonBudget(organization_id=org.id,name="2026 Cloud Emissions Cap",target_kg=100.0,threshold=0.85,period="ANNUAL",year=2026))
        db.add(Budget(organization_id=org.id,scope="organization",target="NovaTech Solutions",amount=50000,threshold=.9))
        db.add(Alert(organization_id=org.id,type="Cost Spike",severity="HIGH",title="AWS cost spike detected",message="A cost anomaly was detected in the demo workload."))
        db.commit()
    finally: db.close()

if __name__=="__main__": seed()
