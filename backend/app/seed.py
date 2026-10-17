from datetime import datetime,timedelta
import random
from sqlalchemy.orm import Session
from .database import Base, engine, SessionLocal
from .models import *
from .auth import hash_password

def seed():
    Base.metadata.create_all(engine); db=SessionLocal()
    try:
        org=db.query(Organization).first()
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
