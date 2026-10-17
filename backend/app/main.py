from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Header, Response, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
import os
import json
from .database import Base, engine, get_db
from .models import *
from .auth import *
from .seed import seed
from .ml import forecast
from .services import (
    process_billing_csv,
    get_cost_summary,
    get_daily_costs,
    get_dashboard_metrics,
    generate_costs_csv,
    get_cost_lineage,
)

app=FastAPI(title="CloudSense AI API", version="1.0.0")
app.add_middleware(CORSMiddleware,allow_origins=["http://localhost:3000"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
Base.metadata.create_all(engine)

with engine.connect() as _conn:
    from sqlalchemy import text
    try:
        _conn.execute(text("ALTER TABLE cost_records ADD COLUMN currency VARCHAR DEFAULT 'USD'"))
        _conn.commit()
    except Exception: pass
    try:
        _conn.execute(text("ALTER TABLE cost_records ADD COLUMN import_id VARCHAR"))
        _conn.commit()
    except Exception: pass

@app.on_event("startup")
def startup():
    seed()

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
def dashboard(user=Depends(current_user), db: Session = Depends(get_db), days: int = 30):
    return get_dashboard_metrics(db, org(user), days=days)

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
def costs(
    start_date: str | None = None,
    end_date: str | None = None,
    provider: str | None = None,
    service: str | None = None,
    region: str | None = None,
    group_by: str = "provider",
    user=Depends(current_user),
    db: Session = Depends(get_db)
):
    return get_cost_summary(
        db,
        organization_id=org(user),
        start_date=start_date,
        end_date=end_date,
        provider=provider,
        service=service,
        region=region,
        group_by=group_by,
    )

@app.get("/api/costs")
def costs_data(
    start_date: str | None = None,
    end_date: str | None = None,
    provider: str | None = None,
    service: str | None = None,
    region: str | None = None,
    user=Depends(current_user),
    db: Session = Depends(get_db)
):
    return get_daily_costs(
        db,
        organization_id=org(user),
        start_date=start_date,
        end_date=end_date,
        provider=provider,
        service=service,
        region=region,
    )

@app.get("/api/costs/export")
def export_costs(
    start_date: str | None = None,
    end_date: str | None = None,
    provider: str | None = None,
    service: str | None = None,
    region: str | None = None,
    user=Depends(current_user),
    db: Session = Depends(get_db)
):
    csv_content, total_cost, count = generate_costs_csv(
        db,
        organization_id=org(user),
        start_date=start_date,
        end_date=end_date,
        provider=provider,
        service=service,
        region=region,
    )
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"cloudsense_costs_{timestamp}.csv"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "X-Total-Cost": f"{total_cost:.2f}",
            "X-Record-Count": str(count),
        }
    )

@app.get("/api/costs/lineage")
def cost_lineage(
    start_date: str | None = None,
    end_date: str | None = None,
    provider: str | None = None,
    service: str | None = None,
    region: str | None = None,
    user=Depends(current_user),
    db: Session = Depends(get_db)
):
    return get_cost_lineage(
        db,
        organization_id=org(user),
        start_date=start_date,
        end_date=end_date,
        provider=provider,
        service=service,
        region=region,
    )

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

@app.post("/api/billing/import")
async def import_billing_csv(
    file: UploadFile = File(...),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    user=Depends(current_user),
    db: Session = Depends(get_db)
):
    content = await file.read()
    result = process_billing_csv(
        db=db,
        organization_id=org(user),
        user_id=user.id,
        filename=file.filename or "uploaded.csv",
        content=content,
        idempotency_key=idempotency_key
    )
    if result.get("status") == "FAILED":
        status_code = 400
    elif result.get("idempotent_replay") or result.get("status") == "DUPLICATE":
        status_code = 200
    else:
        status_code = 201
    return JSONResponse(status_code=status_code, content=result)

@app.get("/api/billing/imports")
def get_billing_imports(user=Depends(current_user), db: Session = Depends(get_db)):
    imports = db.query(BillingImport).filter_by(organization_id=org(user)).order_by(BillingImport.created_at.desc()).all()
    return [
        {
            "id": imp.id,
            "filename": imp.filename,
            "status": imp.status,
            "total_rows": imp.total_rows,
            "imported_rows": imp.imported_rows,
            "error_count": imp.error_count,
            "created_at": imp.created_at.isoformat(),
            "completed_at": imp.completed_at.isoformat() if imp.completed_at else None
        }
        for imp in imports
    ]

@app.get("/api/billing/imports/{id}")
def get_billing_import_detail(id: str, user=Depends(current_user), db: Session = Depends(get_db)):
    imp = db.get(BillingImport, id)
    if not imp or imp.organization_id != org(user):
        raise HTTPException(404, "Billing import not found")
    errors = json.loads(imp.errors_summary) if imp.errors_summary else []
    return {
        "id": imp.id,
        "filename": imp.filename,
        "status": imp.status,
        "file_hash": imp.file_hash,
        "idempotency_key": imp.idempotency_key,
        "total_rows": imp.total_rows,
        "imported_rows": imp.imported_rows,
        "error_count": imp.error_count,
        "errors": errors,
        "created_at": imp.created_at.isoformat(),
        "completed_at": imp.completed_at.isoformat() if imp.completed_at else None
    }
