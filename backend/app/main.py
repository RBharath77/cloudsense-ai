from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
import os
from .database import Base, engine, get_db
from .models import *
from .auth import *
from .seed import seed
from .ml import forecast

app=FastAPI(title="CloudSense AI API", version="1.0.0")
app.add_middleware(CORSMiddleware,allow_origins=["http://localhost:3000"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])

@app.on_event("startup")
def startup():
    Base.metadata.create_all(engine); seed()

@app.get("/health")
def health(): return {"status":"ok","cloud_mode":"mock"}

class Register(BaseModel): email:str; password:str; role:str="ADMIN"
class Login(BaseModel): email:str; password:str
class Chat(BaseModel): message:str

@app.post("/api/auth/register")
def register(data:Register,db:Session=Depends(get_db)):
    if db.query(User).filter_by(email=data.email).first(): raise HTTPException(400,"Email already registered")
    org=Organization(name=f"{data.email.split('@')[0]}'s Organization"); db.add(org); db.flush()
    u=User(email=data.email,password_hash=hash_password(data.password),role=data.role if data.role in {"ADMIN","MANAGER","DEVELOPER","VIEWER"} else "VIEWER",organization_id=org.id); db.add(u); db.commit(); return {"access_token":create_token(u.id),"token_type":"bearer"}

@app.post("/api/auth/login")
def login(data:Login,db:Session=Depends(get_db)):
    u=db.query(User).filter_by(email=data.email).first()
    if not u or not verify_password(data.password,u.password_hash): raise HTTPException(401,"Invalid email or password")
    return {"access_token":create_token(u.id),"token_type":"bearer","role":u.role}

def org(user): return user.organization_id

@app.get("/api/dashboard/summary")
def dashboard(user=Depends(current_user),db:Session=Depends(get_db)):
    oid=org(user)
    spend=db.query(func.sum(CostRecord.amount)).filter(CostRecord.organization_id==oid,CostRecord.recorded_at>=datetime.utcnow()-timedelta(days=30)).scalar() or 0
    total=db.query(func.sum(CloudResource.monthly_cost)).filter(CloudResource.organization_id==oid).scalar() or 0
    display_spend=spend if spend > 0 else total
    savings=db.query(func.sum(Recommendation.monthly_saving)).filter(Recommendation.organization_id==oid,Recommendation.action_status=="PENDING").scalar() or 0
    res_count=db.query(CloudResource).filter_by(organization_id=oid).count()
    avg_health=db.query(func.avg(CloudResource.health)).filter_by(organization_id=oid).scalar()
    health_val=round(avg_health, 1) if avg_health is not None else 100.0
    return {
        "total_spend": round(display_spend, 2),
        "current_month_spend": round(display_spend, 2),
        "predicted_month_end": round(display_spend * 1.102, 2),
        "potential_savings": round(savings, 2),
        "active_resources": res_count,
        "anomalies": db.query(Anomaly).filter_by(organization_id=oid).count(),
        "cloud_health": health_val,
        "carbon_kg": round(db.query(func.sum(CarbonRecord.co2_kg)).filter_by(organization_id=oid).scalar() or 0, 2)
    }

@app.get("/api/cloud/accounts")
def accounts(user=Depends(current_user),db:Session=Depends(get_db)): return [{"id":a.id,"provider":a.provider,"name":a.name,"identifier":a.identifier,"region":a.region,"status":a.status,"last_sync":a.last_sync} for a in db.query(CloudAccount).filter_by(organization_id=org(user)).all()]

@app.post("/api/cloud/accounts/{id}/sync")
def sync(id:str,user=Depends(current_user),db:Session=Depends(get_db)):
    a=db.get(CloudAccount,id)
    if not a or a.organization_id!=org(user): raise HTTPException(404,"Account not found")
    a.last_sync=datetime.utcnow(); db.add(AuditLog(organization_id=org(user),user_id=user.id,action="cloud_sync",status="success",detail=a.provider)); db.commit(); return {"status":"simulated_sync_complete","demo":True}

@app.get("/api/resources")
def resources(user=Depends(current_user),db:Session=Depends(get_db)):
    return [r.__dict__|{} for r in db.query(CloudResource).filter_by(organization_id=org(user)).limit(200).all()]

@app.get("/api/costs/summary")
def costs(user=Depends(current_user),db:Session=Depends(get_db)):
    rows=db.query(CostRecord.provider,func.sum(CostRecord.amount)).filter_by(organization_id=org(user)).group_by(CostRecord.provider).all()
    return {"providers":[{"provider":p,"cost":round(float(v),2)} for p,v in rows]}

@app.get("/api/costs")
def costs_data(user=Depends(current_user),db:Session=Depends(get_db)):
    rows=db.query(CostRecord.recorded_at,func.sum(CostRecord.amount)).filter_by(organization_id=org(user)).group_by(CostRecord.recorded_at).order_by(CostRecord.recorded_at).all()
    return [{"date":d.strftime("%Y-%m-%d"),"cost":round(float(v),2)} for d,v in rows]

@app.get("/api/forecast")
def forecast_api(user=Depends(current_user),db:Session=Depends(get_db)):
    rows=db.query(CostRecord.recorded_at,func.sum(CostRecord.amount)).filter_by(organization_id=org(user)).group_by(CostRecord.recorded_at).order_by(CostRecord.recorded_at).all()
    result=forecast([float(v) for _,v in rows],30)
    return result

@app.get("/api/anomalies")
def anomalies(user=Depends(current_user),db:Session=Depends(get_db)):
    return [{"id":a.id,"provider":a.provider,"resource_id":a.resource_id,"metric":a.metric,"severity":a.severity,"timestamp":a.timestamp,"score":a.score,"financial_impact":a.financial_impact,"reason":a.reason,"recommendation":a.recommendation} for a in db.query(Anomaly).filter_by(organization_id=org(user)).order_by(Anomaly.timestamp.desc()).all()]

@app.get("/api/optimization")
def optimization(user=Depends(current_user),db:Session=Depends(get_db)):
    return [{"id":r.id,"resource_id":r.resource_id,"current_cost":r.current_cost,"problem":r.problem,"recommendation":r.recommendation,"monthly_saving":r.monthly_saving,"yearly_saving":r.yearly_saving,"risk":r.risk,"confidence":r.confidence,"action_status":r.action_status} for r in db.query(Recommendation).filter_by(organization_id=org(user)).all()]

@app.post("/api/optimization/{id}/simulate")
def simulate(id:str,user=Depends(current_user),db:Session=Depends(get_db)):
    r=db.get(Recommendation,id)
    if not r or r.organization_id!=org(user): raise HTTPException(404,"Recommendation not found")
    r.action_status="SIMULATED"; db.add(AuditLog(organization_id=org(user),user_id=user.id,action="recommendation_simulation",status="success",detail=r.id)); db.commit(); return {"status":"simulation_successful","message":"DEMO / SIMULATION: no real cloud resource was modified."}

@app.get("/api/security")
def security(user=Depends(current_user),db:Session=Depends(get_db)):
    return [{k:v for k,v in f.__dict__.items() if not k.startswith('_')} for f in db.query(SecurityFinding).filter_by(organization_id=org(user)).all()]
@app.get("/api/sla")
def sla(user=Depends(current_user),db:Session=Depends(get_db)): return [{k:v for k,v in x.__dict__.items() if not k.startswith('_')} for x in db.query(SLARecord).filter_by(organization_id=org(user)).all()]
@app.get("/api/carbon")
def carbon(user=Depends(current_user),db:Session=Depends(get_db)): return [{"provider":x.provider,"region":x.region,"service":x.service,"co2_kg":x.co2_kg,"recorded_at":x.recorded_at} for x in db.query(CarbonRecord).filter_by(organization_id=org(user)).all()]
@app.get("/api/budgets")
def budgets(user=Depends(current_user),db:Session=Depends(get_db)): return [{k:v for k,v in x.__dict__.items() if not k.startswith('_')} for x in db.query(Budget).filter_by(organization_id=org(user)).all()]
@app.get("/api/alerts")
def alerts(user=Depends(current_user),db:Session=Depends(get_db)): return [{k:v for k,v in x.__dict__.items() if not k.startswith('_')} for x in db.query(Alert).filter_by(organization_id=org(user)).order_by(Alert.created_at.desc()).all()]
@app.get("/api/rca/{id}")
def rca(id:str,user=Depends(current_user),db:Session=Depends(get_db)):
    a=db.get(Anomaly,id)
    if not a or a.organization_id!=org(user): raise HTTPException(404,"Anomaly not found")
    return {"root_cause":a.reason,"evidence":[f"{a.metric} anomaly score {a.score:.2f}",f"Estimated impact ${a.financial_impact:.2f}"],"impact":f"Estimated financial impact ${a.financial_impact:.2f}","timeline":[{"time":a.timestamp,"event":"Anomaly detected"}],"recommendation":a.recommendation}
@app.get("/api/scaling")
def scaling(user=Depends(current_user),db:Session=Depends(get_db)):
    rs=db.query(CloudResource).filter_by(organization_id=org(user)).order_by(CloudResource.utilization.desc()).limit(8).all()
    return [{"resource":r.name,"current_capacity":2,"predicted_capacity":3 if r.utilization>75 else 2,"expected_traffic":round(r.utilization*100),"recommendation":"Scale before predicted peak" if r.utilization>75 else "Capacity is currently adequate","expected_cost":round(r.monthly_cost*(1.5 if r.utilization>75 else 1),2)} for r in rs]

@app.post("/api/assistant/chat")
def assistant(data:Chat,user=Depends(current_user),db:Session=Depends(get_db)):
    q=data.message.lower(); oid=org(user); summary=dashboard(user,db)
    if "spend" in q or "cost" in q: answer=f"Your current demo cloud spend is ${summary['current_month_spend']:,.0f}. Potential savings are ${summary['potential_savings']:,.0f}/month."
    elif "anomal" in q: answer=f"There are {summary['anomalies']} open anomalies. I can drill into provider, resource and financial impact."
    elif "save" in q or "optim" in q: answer=f"The optimization engine identifies about ${summary['potential_savings']:,.0f}/month in estimated savings."
    elif "security" in q: answer=f"There are {db.query(SecurityFinding).filter_by(organization_id=oid,status='OPEN').count()} open security findings in demo data."
    elif "carbon" in q: answer=f"Estimated emissions are {summary['carbon_kg']:.1f} kg CO₂ in the seeded demo snapshot."
    else: answer="I can answer questions about cloud spend, resources, anomalies, optimization, security, SLA and carbon using the application's live database data."
    return {"answer":answer,"mode":"deterministic_application_data"}

@app.post("/api/reports/generate")
def report(user=Depends(current_user),db:Session=Depends(get_db)):
    from reportlab.pdfgen import canvas
    path=f"/tmp/cloudsense-{user.id}.pdf"; s=dashboard(user,db); c=canvas.Canvas(path); c.setTitle("CloudSense AI Report"); y=800
    c.setFont("Helvetica-Bold",18); c.drawString(50,y,"CloudSense AI — Executive Report"); y-=35; c.setFont("Helvetica",11)
    for k,v in s.items(): c.drawString(60,y,f"{k.replace('_',' ').title()}: {v}"); y-=20
    c.drawString(60,y,"Demo values are generated from the seeded mock cloud environment."); c.save()
    r=Report(organization_id=org(user),name="Executive Report",file_path=path); db.add(r); db.commit(); return {"id":r.id,"download":"/api/reports/download/"+r.id,"status":"generated"}
@app.get("/api/reports/download/{id}")
def download_report(id:str,user=Depends(current_user),db:Session=Depends(get_db)):
    r=db.get(Report,id)
    if not r or r.organization_id!=org(user): raise HTTPException(404,"Report not found")
    return FileResponse(r.file_path,media_type="application/pdf",filename="cloudsense-report.pdf")
