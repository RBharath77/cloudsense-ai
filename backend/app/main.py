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
    evaluate_budget,
    list_budgets,
    get_budget_detail,
    create_budget,
    update_budget,
    delete_budget,
    evaluate_organization_alerts,
    list_alerts,
    mark_alert_read,
    mark_all_alerts_read,
    delete_alert,
    evaluate_tag_governance,
    update_resource_tags,
    generate_cost_forecast,
    list_anomalies,
    run_anomaly_detection,
    get_anomaly_rca,
    list_carbon_factors,
    get_carbon_summary,
    list_carbon_records,
    import_carbon_csv,
    list_carbon_budgets,
    create_carbon_budget,
    delete_carbon_budget,
    get_recommendations_with_priority,
    run_what_if_simulation,
    get_simulation_scenarios,
    get_savings_ledger_summary,
    get_savings_ledger_entries,
    create_savings_ledger_entry,
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
    try:
        _conn.execute(text("ALTER TABLE budgets ADD COLUMN name VARCHAR"))
        _conn.commit()
    except Exception: pass
    try:
        _conn.execute(text("ALTER TABLE budgets ADD COLUMN period VARCHAR DEFAULT 'MONTHLY'"))
        _conn.commit()
    except Exception: pass
    try:
        _conn.execute(text("ALTER TABLE budgets ADD COLUMN created_at DATETIME"))
        _conn.commit()
    except Exception: pass
    try:
        _conn.execute(text("ALTER TABLE alerts ADD COLUMN fingerprint VARCHAR"))
        _conn.commit()
    except Exception: pass
    try:
        _conn.execute(text("ALTER TABLE cloud_resources ADD COLUMN tags TEXT"))
        _conn.commit()
    except Exception: pass
    try:
        _conn.execute(text("ALTER TABLE carbon_records ADD COLUMN source VARCHAR DEFAULT 'Provider Report'"))
        _conn.commit()
    except Exception: pass
    try:
        _conn.execute(text("ALTER TABLE carbon_records ADD COLUMN unit VARCHAR DEFAULT 'kgCO2e'"))
        _conn.commit()
    except Exception: pass
    try:
        _conn.execute(text("ALTER TABLE carbon_records ADD COLUMN reporting_period VARCHAR"))
        _conn.commit()
    except Exception: pass
    try:
        _conn.execute(text("ALTER TABLE carbon_records ADD COLUMN record_type VARCHAR DEFAULT 'ESTIMATED'"))
        _conn.commit()
    except Exception: pass
    try:
        _conn.execute(text("ALTER TABLE carbon_records ADD COLUMN scope VARCHAR DEFAULT 'Scope 2'"))
        _conn.commit()
    except Exception: pass
    try:
        _conn.execute(text("ALTER TABLE carbon_records ADD COLUMN methodology TEXT"))
        _conn.commit()
    except Exception: pass
    try:
        _conn.execute(text("ALTER TABLE optimization_recommendations ADD COLUMN category VARCHAR DEFAULT 'RIGHTSIZING'"))
        _conn.commit()
    except Exception: pass
    try:
        _conn.execute(text("ALTER TABLE optimization_recommendations ADD COLUMN action TEXT"))
        _conn.commit()
    except Exception: pass
    try:
        _conn.execute(text("ALTER TABLE optimization_recommendations ADD COLUMN evidence TEXT"))
        _conn.commit()
    except Exception: pass
    try:
        _conn.execute(text("ALTER TABLE optimization_recommendations ADD COLUMN assumptions TEXT"))
        _conn.commit()
    except Exception: pass
    try:
        _conn.execute(text("ALTER TABLE optimization_recommendations ADD COLUMN trade_offs TEXT"))
        _conn.commit()
    except Exception: pass
    try:
        _conn.execute(text("ALTER TABLE optimization_recommendations ADD COLUMN monthly_carbon_saving_kg FLOAT DEFAULT 0.0"))
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

class BudgetCreate(BaseModel):
    name: str | None = None
    scope: str = "ORGANIZATION"
    target: str = "ALL"
    amount: float
    threshold: float = 0.9
    period: str = "MONTHLY"

class BudgetUpdate(BaseModel):
    name: str | None = None
    scope: str | None = None
    target: str | None = None
    amount: float | None = None
    threshold: float | None = None
    period: str | None = None

class ResourceTagsUpdate(BaseModel):
    tags: dict[str, str]

class CarbonBudgetCreate(BaseModel):
    name: str
    target_kg: float
    threshold: float = 0.9
    period: str = "ANNUAL"
    year: int = 2026

class SimulationRequest(BaseModel):
    scenario_type: str = "RECOMMENDATION"
    name: str | None = None
    recommendation_id: str | None = None
    downsize_percentage: float | None = 40.0
    target_resource_count: int | None = None
    off_hours_per_week: float | None = 56.0
    term_years: int | None = 1
    coverage_pct: float | None = 75.0
    target_region: str | None = "us-west-2"
    payment_option: str | None = "NO_UPFRONT"

class SavingsLedgerCreate(BaseModel):
    title: str
    resource_id: str = "res-manual"
    recommendation_id: str | None = None
    category: str = "RIGHTSIZING"
    savings_type: str = "EXPECTED"
    status: str = "PLANNED"
    expected_monthly_cost_saving: float = 0.0
    expected_monthly_carbon_saving_kg: float = 0.0
    verified_cost_saving: float = 0.0
    verified_carbon_saving_kg: float = 0.0
    measurement_window_start: str | None = None
    measurement_window_end: str | None = None
    caveats: str | None = None
    notes: str | None = None

class SavingsLedgerUpdate(BaseModel):
    status: str | None = None
    verified_cost_saving: float | None = None
    verified_carbon_saving_kg: float | None = None
    measurement_window_start: str | None = None
    measurement_window_end: str | None = None
    caveats: str | None = None
    notes: str | None = None

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
def forecast_api(
    horizon: int = Query(30, ge=1, le=180),
    provider: str | None = None,
    confidence: float = Query(0.95, ge=0.5, le=0.99),
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    return generate_cost_forecast(
        db,
        organization_id=org(user),
        horizon=horizon,
        provider=provider,
        confidence_level=confidence,
    )

@app.get("/api/anomalies")
def anomalies(
    severity: str | None = None,
    provider: str | None = None,
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    return list_anomalies(db, org(user), severity=severity, provider=provider)

@app.post("/api/anomalies/detect")
def detect_anomalies(
    contamination: float = Query(0.05, ge=0.01, le=0.3),
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    return run_anomaly_detection(db, org(user), contamination=contamination)

@app.get("/api/optimization")
def optimization(
    priority: str = "BALANCE",
    category: str | None = None,
    action_status: str | None = None,
    legacy: bool = False,
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    data = get_recommendations_with_priority(
        db,
        org(user),
        priority=priority,
        category=category,
        action_status=action_status,
    )
    if legacy:
        return data["recommendations"]
    return data

@app.get("/api/optimization/recommendations/{id}")
def get_recommendation_detail(id: str, user=Depends(current_user), db: Session = Depends(get_db)):
    r = db.get(Recommendation, id)
    if not r or r.organization_id != org(user):
        raise HTTPException(404, "Recommendation not found")
    parsed_evidence = None
    if r.evidence:
        try:
            parsed_evidence = json.loads(r.evidence)
        except Exception:
            parsed_evidence = {"raw": r.evidence}
    return {
        "id": r.id,
        "resource_id": r.resource_id,
        "category": r.category or "RIGHTSIZING",
        "current_cost": r.current_cost,
        "problem": r.problem,
        "action": r.action or r.recommendation,
        "recommendation": r.recommendation,
        "monthly_saving": r.monthly_saving,
        "yearly_saving": r.yearly_saving,
        "monthly_carbon_saving_kg": r.monthly_carbon_saving_kg or 0.0,
        "risk": r.risk,
        "confidence": r.confidence,
        "action_status": r.action_status,
        "evidence": parsed_evidence,
        "assumptions": r.assumptions,
        "trade_offs": r.trade_offs,
    }

@app.post("/api/optimization/{id}/simulate")
def simulate(id: str, user=Depends(current_user), db: Session = Depends(get_db)):
    r = db.get(Recommendation, id)
    if not r or r.organization_id != org(user):
        raise HTTPException(404, "Recommendation not found")
    r.action_status = "SIMULATED"
    db.commit()
    sim_result = run_what_if_simulation(
        db,
        org(user),
        user.id,
        {
            "scenario_type": "RECOMMENDATION",
            "name": f"Simulation: {r.category} for {r.resource_id}",
            "recommendation_id": r.id,
        },
    )
    return {
        "status": "simulation_successful",
        "message": "DEMO / SIMULATION: no real cloud resource was modified.",
        "simulation": sim_result,
    }

@app.post("/api/optimization/simulate")
def simulate_scenario(
    data: SimulationRequest,
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    try:
        return run_what_if_simulation(db, org(user), user.id, data.dict())
    except ValueError as e:
        raise HTTPException(400, str(e))

@app.get("/api/optimization/simulations")
def list_simulations(user=Depends(current_user), db: Session = Depends(get_db)):
    return get_simulation_scenarios(db, org(user))

@app.get("/api/optimization/simulations/{id}")
def get_simulation(id: str, user=Depends(current_user), db: Session = Depends(get_db)):
    scenario = db.get(SimulationScenario, id)
    if not scenario or scenario.organization_id != org(user):
        raise HTTPException(404, "Simulation scenario not found")
    return {
        "id": scenario.id,
        "name": scenario.name,
        "scenario_type": scenario.scenario_type,
        "created_at": scenario.created_at.isoformat(),
        "pricing_source": scenario.pricing_source,
        "factor_source": scenario.factor_source,
        "inputs": json.loads(scenario.inputs) if scenario.inputs else {},
        "assumptions": json.loads(scenario.assumptions) if scenario.assumptions else {},
        "results": json.loads(scenario.results) if scenario.results else {},
    }

@app.get("/api/optimization/ledger/summary")
def get_savings_summary(user=Depends(current_user), db: Session = Depends(get_db)):
    return get_savings_ledger_summary(db, org(user))

@app.get("/api/optimization/ledger")
def list_savings_ledger(
    status: str | None = None,
    savings_type: str | None = None,
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    return get_savings_ledger_entries(
        db,
        org(user),
        status=status,
        savings_type=savings_type,
    )

@app.post("/api/optimization/ledger")
def create_savings_entry(
    data: SavingsLedgerCreate,
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    return create_savings_ledger_entry(db, org(user), data.dict())

@app.patch("/api/optimization/ledger/{id}")
def update_savings_entry(
    id: str,
    data: SavingsLedgerUpdate,
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    entry = db.get(SavingsLedger, id)
    if not entry or entry.organization_id != org(user):
        raise HTTPException(404, "Savings ledger entry not found")
    if data.status:
        entry.status = data.status.upper()
    if data.verified_cost_saving is not None:
        entry.verified_cost_saving = float(data.verified_cost_saving)
    if data.verified_carbon_saving_kg is not None:
        entry.verified_carbon_saving_kg = float(data.verified_carbon_saving_kg)
    if data.caveats is not None:
        entry.caveats = data.caveats
    if data.notes is not None:
        entry.notes = data.notes
    if data.measurement_window_start:
        try:
            entry.measurement_window_start = datetime.fromisoformat(data.measurement_window_start)
        except Exception:
            pass
    if data.measurement_window_end:
        try:
            entry.measurement_window_end = datetime.fromisoformat(data.measurement_window_end)
        except Exception:
            pass
    entry.updated_at = datetime.utcnow()
    db.commit()
    return {"status": "updated", "id": entry.id}

@app.get("/api/security")
def security(user=Depends(current_user),db:Session=Depends(get_db)):
    return [{k:v for k,v in f.__dict__.items() if not k.startswith('_')} for f in db.query(SecurityFinding).filter_by(organization_id=org(user)).all()]
@app.get("/api/sla")
def sla(user=Depends(current_user),db:Session=Depends(get_db)): return [{k:v for k,v in x.__dict__.items() if not k.startswith('_')} for x in db.query(SLARecord).filter_by(organization_id=org(user)).all()]
@app.get("/api/carbon/summary")
def get_carbon_summary_api(user=Depends(current_user), db: Session = Depends(get_db)):
    return get_carbon_summary(db, org(user))

@app.get("/api/carbon")
def carbon(
    provider: str | None = None,
    scope: str | None = None,
    record_type: str | None = None,
    limit: int = 100,
    user=Depends(current_user),
    db: Session = Depends(get_db),
):
    return list_carbon_records(
        db,
        org(user),
        provider=provider,
        scope=scope,
        record_type=record_type,
        limit=limit,
    )

@app.post("/api/carbon/import")
def post_carbon_csv(file: UploadFile = File(...), user=Depends(current_user), db: Session = Depends(get_db)):
    content = file.file.read()
    res = import_carbon_csv(db, org(user), content)
    if not res.get("success"):
        raise HTTPException(400, detail={"errors": res.get("errors", ["Failed to parse carbon CSV."])})
    return res

@app.get("/api/carbon/factors")
def get_carbon_factors(user=Depends(current_user)):
    return list_carbon_factors()

@app.get("/api/carbon/budgets")
def get_carbon_budgets(user=Depends(current_user), db: Session = Depends(get_db)):
    return list_carbon_budgets(db, org(user))

@app.post("/api/carbon/budgets", status_code=201)
def post_carbon_budget(data: CarbonBudgetCreate, user=Depends(current_user), db: Session = Depends(get_db)):
    try:
        return create_carbon_budget(db, org(user), data.model_dump())
    except ValueError as e:
        raise HTTPException(400, str(e))

@app.delete("/api/carbon/budgets/{id}")
def delete_carbon_budget_api(id: str, user=Depends(current_user), db: Session = Depends(get_db)):
    success = delete_carbon_budget(db, org(user), id)
    if not success:
        raise HTTPException(404, "Carbon budget not found")
    return {"status": "deleted", "id": id}
@app.get("/api/budgets")
def get_budgets(user=Depends(current_user), db: Session = Depends(get_db)):
    return list_budgets(db, org(user))

@app.post("/api/budgets", status_code=201)
def post_budget(data: BudgetCreate, user=Depends(current_user), db: Session = Depends(get_db)):
    try:
        return create_budget(db, org(user), data.model_dump())
    except ValueError as e:
        raise HTTPException(400, str(e))

@app.get("/api/budgets/{id}")
def get_budget(id: str, user=Depends(current_user), db: Session = Depends(get_db)):
    b = get_budget_detail(db, org(user), id)
    if not b:
        raise HTTPException(404, "Budget not found")
    return b

@app.put("/api/budgets/{id}")
def put_budget(id: str, data: BudgetUpdate, user=Depends(current_user), db: Session = Depends(get_db)):
    try:
        b = update_budget(db, org(user), id, data.model_dump(exclude_unset=True))
        if not b:
            raise HTTPException(404, "Budget not found")
        return b
    except ValueError as e:
        raise HTTPException(400, str(e))

@app.delete("/api/budgets/{id}")
def remove_budget(id: str, user=Depends(current_user), db: Session = Depends(get_db)):
    success = delete_budget(db, org(user), id)
    if not success:
        raise HTTPException(404, "Budget not found")
    return {"status": "deleted", "id": id}

@app.get("/api/alerts")
def get_alerts(unread: bool = False, severity: str | None = None, user=Depends(current_user), db: Session = Depends(get_db)):
    return list_alerts(db, org(user), unread_only=unread, severity=severity)

@app.post("/api/alerts/evaluate")
def evaluate_alerts(user=Depends(current_user), db: Session = Depends(get_db)):
    return evaluate_organization_alerts(db, org(user))

@app.post("/api/alerts/{id}/read")
def read_alert(id: str, user=Depends(current_user), db: Session = Depends(get_db)):
    success = mark_alert_read(db, org(user), id)
    if not success:
        raise HTTPException(404, "Alert not found")
    return {"status": "marked_read", "id": id}

@app.post("/api/alerts/read-all")
def read_all_alerts(user=Depends(current_user), db: Session = Depends(get_db)):
    count = mark_all_alerts_read(db, org(user))
    return {"status": "marked_all_read", "updated_count": count}

@app.delete("/api/alerts/{id}")
def remove_alert(id: str, user=Depends(current_user), db: Session = Depends(get_db)):
    success = delete_alert(db, org(user), id)
    if not success:
        raise HTTPException(404, "Alert not found")
    return {"status": "deleted", "id": id}

@app.get("/api/governance/tags")
def get_tag_governance(user=Depends(current_user), db: Session = Depends(get_db)):
    return evaluate_tag_governance(db, org(user))

@app.put("/api/resources/{id}/tags")
def put_resource_tags(id: str, data: ResourceTagsUpdate, user=Depends(current_user), db: Session = Depends(get_db)):
    res = update_resource_tags(db, org(user), id, data.tags)
    if not res:
        raise HTTPException(404, "Resource not found")
    return res
@app.get("/api/rca/{id}")
def rca(id: str, user=Depends(current_user), db: Session = Depends(get_db)):
    rca_data = get_anomaly_rca(db, org(user), id)
    if not rca_data:
        raise HTTPException(404, "Anomaly not found")
    return rca_data
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
