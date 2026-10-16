from datetime import datetime,timedelta
import random
from sqlalchemy.orm import Session
from .database import Base, engine, SessionLocal
from .models import *
from .auth import hash_password

def seed():
    Base.metadata.create_all(engine); db=SessionLocal()
    try:
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
                save=r.monthly_cost*.55; db.add(Recommendation(organization_id=org.id,resource_id=r.id,current_cost=r.monthly_cost,problem="Underutilized resource",recommendation="Downsize or schedule this resource during idle periods.",monthly_saving=save,yearly_saving=save*12,risk="LOW",confidence=.89))
        for r in resources[:8]: db.add(SecurityFinding(organization_id=org.id,provider=r.provider,resource_id=r.id,severity="HIGH" if r.id==resources[0].id else "MEDIUM",risk="Configuration exposure",description="Demo finding: resource configuration requires review.",recommendation="Restrict public access and enforce encryption.",status="OPEN"))
        for p in ["AWS","Azure","GCP"]: db.add(SLARecord(organization_id=org.id,service=f"{p} platform",availability=random.choice([99.9,99.95,99.99]),latency=random.uniform(40,120),downtime=random.uniform(2,20),incidents=random.randint(0,3),breached=False,timestamp=now))
        for p,c in [("AWS",28.45),("Azure",10.24),("GCP",4.16)]: db.add(CarbonRecord(organization_id=org.id,provider=p,region="primary",service="all",co2_kg=c,recorded_at=now))
        db.add(Budget(organization_id=org.id,scope="organization",target="NovaTech Solutions",amount=50000,threshold=.9))
        db.add(Alert(organization_id=org.id,type="Cost Spike",severity="HIGH",title="AWS cost spike detected",message="A cost anomaly was detected in the demo workload."))
        db.commit()
    finally: db.close()

if __name__=="__main__": seed()
