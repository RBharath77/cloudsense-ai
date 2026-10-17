import uuid
from datetime import datetime
from sqlalchemy import String, Float, Integer, DateTime, ForeignKey, Text, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column
from ..database import Base

def uid(): return str(uuid.uuid4())

def common():
    return {"created_at": mapped_column(DateTime, default=datetime.utcnow), "updated_at": mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)}

class User(Base):
    __tablename__="users"
    id: Mapped[str]=mapped_column(String, primary_key=True, default=uid)
    email: Mapped[str]=mapped_column(String, unique=True, index=True)
    password_hash: Mapped[str]=mapped_column(String)
    role: Mapped[str]=mapped_column(String, default="VIEWER")
    organization_id: Mapped[str|None]=mapped_column(String, ForeignKey("organizations.id"), nullable=True)
    is_active: Mapped[bool]=mapped_column(Boolean, default=True)
    created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)

class Organization(Base):
    __tablename__="organizations"
    id: Mapped[str]=mapped_column(String, primary_key=True, default=uid)
    name: Mapped[str]=mapped_column(String, index=True)
    created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)

class CloudAccount(Base):
    __tablename__="cloud_accounts"
    id: Mapped[str]=mapped_column(String, primary_key=True, default=uid)
    organization_id: Mapped[str]=mapped_column(String, index=True)
    provider: Mapped[str]=mapped_column(String, index=True)
    name: Mapped[str]=mapped_column(String)
    identifier: Mapped[str]=mapped_column(String)
    region: Mapped[str]=mapped_column(String)
    status: Mapped[str]=mapped_column(String, default="CONNECTED")
    last_sync: Mapped[datetime|None]=mapped_column(DateTime, nullable=True)

class CloudResource(Base):
    __tablename__="cloud_resources"
    id: Mapped[str]=mapped_column(String, primary_key=True, default=uid)
    organization_id: Mapped[str]=mapped_column(String, index=True)
    account_id: Mapped[str]=mapped_column(String, index=True)
    provider: Mapped[str]=mapped_column(String, index=True)
    name: Mapped[str]=mapped_column(String, index=True)
    type: Mapped[str]=mapped_column(String)
    region: Mapped[str]=mapped_column(String)
    status: Mapped[str]=mapped_column(String, default="RUNNING")
    cpu: Mapped[float]=mapped_column(Float, default=0)
    memory: Mapped[float]=mapped_column(Float, default=0)
    utilization: Mapped[float]=mapped_column(Float, default=0)
    monthly_cost: Mapped[float]=mapped_column(Float, default=0)
    health: Mapped[float]=mapped_column(Float, default=100)
    tags: Mapped[str|None]=mapped_column(Text, nullable=True)

class CostRecord(Base):
    __tablename__="cost_records"
    id: Mapped[str]=mapped_column(String, primary_key=True, default=uid)
    organization_id: Mapped[str]=mapped_column(String, index=True)
    provider: Mapped[str]=mapped_column(String, index=True)
    service: Mapped[str]=mapped_column(String, index=True)
    region: Mapped[str]=mapped_column(String, default="global")
    resource_id: Mapped[str|None]=mapped_column(String, index=True, nullable=True)
    amount: Mapped[float]=mapped_column(Float)
    recorded_at: Mapped[datetime]=mapped_column(DateTime, index=True)
    currency: Mapped[str]=mapped_column(String, default="USD")
    import_id: Mapped[str|None]=mapped_column(String, ForeignKey("billing_imports.id"), index=True, nullable=True)

class MetricRecord(Base):
    __tablename__="resource_metrics"
    id: Mapped[str]=mapped_column(String, primary_key=True, default=uid)
    resource_id: Mapped[str]=mapped_column(String, index=True)
    timestamp: Mapped[datetime]=mapped_column(DateTime, index=True)
    cpu: Mapped[float]=mapped_column(Float)
    memory: Mapped[float]=mapped_column(Float)
    network: Mapped[float]=mapped_column(Float)
    requests: Mapped[float]=mapped_column(Float)

class Anomaly(Base):
    __tablename__="anomalies"
    id: Mapped[str]=mapped_column(String, primary_key=True, default=uid)
    organization_id: Mapped[str]=mapped_column(String, index=True)
    provider: Mapped[str]=mapped_column(String)
    resource_id: Mapped[str|None]=mapped_column(String)
    metric: Mapped[str]=mapped_column(String)
    severity: Mapped[str]=mapped_column(String)
    timestamp: Mapped[datetime]=mapped_column(DateTime)
    score: Mapped[float]=mapped_column(Float)
    financial_impact: Mapped[float]=mapped_column(Float)
    reason: Mapped[str]=mapped_column(Text)
    recommendation: Mapped[str]=mapped_column(Text)

class Recommendation(Base):
    __tablename__="optimization_recommendations"
    id: Mapped[str]=mapped_column(String, primary_key=True, default=uid)
    organization_id: Mapped[str]=mapped_column(String, index=True)
    resource_id: Mapped[str]=mapped_column(String)
    current_cost: Mapped[float]=mapped_column(Float)
    problem: Mapped[str]=mapped_column(Text)
    recommendation: Mapped[str]=mapped_column(Text)
    monthly_saving: Mapped[float]=mapped_column(Float)
    yearly_saving: Mapped[float]=mapped_column(Float)
    risk: Mapped[str]=mapped_column(String)
    confidence: Mapped[float]=mapped_column(Float)
    action_status: Mapped[str]=mapped_column(String, default="PENDING")
    category: Mapped[str|None]=mapped_column(String, nullable=True, default="RIGHTSIZING")
    action: Mapped[str|None]=mapped_column(Text, nullable=True)
    evidence: Mapped[str|None]=mapped_column(Text, nullable=True)
    assumptions: Mapped[str|None]=mapped_column(Text, nullable=True)
    trade_offs: Mapped[str|None]=mapped_column(Text, nullable=True)
    monthly_carbon_saving_kg: Mapped[float|None]=mapped_column(Float, nullable=True, default=0.0)

class SecurityFinding(Base):
    __tablename__="security_findings"
    id: Mapped[str]=mapped_column(String, primary_key=True, default=uid)
    organization_id: Mapped[str]=mapped_column(String, index=True)
    provider: Mapped[str]=mapped_column(String)
    resource_id: Mapped[str]=mapped_column(String)
    severity: Mapped[str]=mapped_column(String)
    risk: Mapped[str]=mapped_column(String)
    description: Mapped[str]=mapped_column(Text)
    recommendation: Mapped[str]=mapped_column(Text)
    status: Mapped[str]=mapped_column(String, default="OPEN")

class SLARecord(Base):
    __tablename__="sla_records"
    id: Mapped[str]=mapped_column(String, primary_key=True, default=uid)
    organization_id: Mapped[str]=mapped_column(String, index=True)
    service: Mapped[str]=mapped_column(String)
    availability: Mapped[float]=mapped_column(Float)
    latency: Mapped[float]=mapped_column(Float)
    downtime: Mapped[float]=mapped_column(Float)
    incidents: Mapped[int]=mapped_column(Integer)
    breached: Mapped[bool]=mapped_column(Boolean, default=False)
    timestamp: Mapped[datetime]=mapped_column(DateTime)

class CarbonRecord(Base):
    __tablename__="carbon_records"
    id: Mapped[str]=mapped_column(String, primary_key=True, default=uid)
    organization_id: Mapped[str]=mapped_column(String, index=True)
    provider: Mapped[str]=mapped_column(String)
    region: Mapped[str]=mapped_column(String)
    service: Mapped[str]=mapped_column(String)
    co2_kg: Mapped[float]=mapped_column(Float)
    recorded_at: Mapped[datetime]=mapped_column(DateTime)
    source: Mapped[str]=mapped_column(String, default="Provider Report")
    unit: Mapped[str]=mapped_column(String, default="kgCO2e")
    reporting_period: Mapped[str|None]=mapped_column(String, nullable=True)
    record_type: Mapped[str]=mapped_column(String, default="ESTIMATED")
    scope: Mapped[str]=mapped_column(String, default="Scope 2")
    methodology: Mapped[str|None]=mapped_column(String, nullable=True)

class CarbonBudget(Base):
    __tablename__="carbon_budgets"
    id: Mapped[str]=mapped_column(String, primary_key=True, default=uid)
    organization_id: Mapped[str]=mapped_column(String, index=True)
    name: Mapped[str]=mapped_column(String)
    target_kg: Mapped[float]=mapped_column(Float)
    threshold: Mapped[float]=mapped_column(Float, default=0.9)
    period: Mapped[str]=mapped_column(String, default="ANNUAL")
    year: Mapped[int]=mapped_column(Integer, default=2026)
    created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)

class Budget(Base):
    __tablename__="budgets"
    id: Mapped[str]=mapped_column(String, primary_key=True, default=uid)
    organization_id: Mapped[str]=mapped_column(String, index=True)
    name: Mapped[str|None]=mapped_column(String, nullable=True)
    scope: Mapped[str]=mapped_column(String)
    target: Mapped[str]=mapped_column(String)
    amount: Mapped[float]=mapped_column(Float)
    threshold: Mapped[float]=mapped_column(Float, default=0.9)
    period: Mapped[str]=mapped_column(String, default="MONTHLY")
    created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)

class Alert(Base):
    __tablename__="alerts"
    id: Mapped[str]=mapped_column(String, primary_key=True, default=uid)
    organization_id: Mapped[str]=mapped_column(String, index=True)
    type: Mapped[str]=mapped_column(String)
    severity: Mapped[str]=mapped_column(String)
    title: Mapped[str]=mapped_column(String)
    message: Mapped[str]=mapped_column(Text)
    fingerprint: Mapped[str|None]=mapped_column(String, nullable=True, index=True)
    read: Mapped[bool]=mapped_column(Boolean, default=False)
    created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)

class Incident(Base):
    __tablename__="incidents"
    id: Mapped[str]=mapped_column(String, primary_key=True, default=uid)
    organization_id: Mapped[str]=mapped_column(String, index=True)
    title: Mapped[str]=mapped_column(String)
    impact: Mapped[str]=mapped_column(Text)
    started_at: Mapped[datetime]=mapped_column(DateTime)
    resolved_at: Mapped[datetime|None]=mapped_column(DateTime, nullable=True)

class ChatSession(Base):
    __tablename__="chat_sessions"
    id: Mapped[str]=mapped_column(String, primary_key=True, default=uid)
    organization_id: Mapped[str]=mapped_column(String, index=True)
    user_id: Mapped[str]=mapped_column(String)
    created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)

class ChatMessage(Base):
    __tablename__="chat_messages"
    id: Mapped[str]=mapped_column(String, primary_key=True, default=uid)
    session_id: Mapped[str]=mapped_column(String, index=True)
    role: Mapped[str]=mapped_column(String)
    content: Mapped[str]=mapped_column(Text)
    sources: Mapped[str|None]=mapped_column(Text, nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)

class Report(Base):
    __tablename__="reports"
    id: Mapped[str]=mapped_column(String, primary_key=True, default=uid)
    organization_id: Mapped[str]=mapped_column(String, index=True)
    name: Mapped[str]=mapped_column(String)
    report_type: Mapped[str]=mapped_column(String, default="EXECUTIVE_DIGEST")
    format: Mapped[str]=mapped_column(String, default="PDF")
    period_days: Mapped[int]=mapped_column(Integer, default=30)
    file_size_bytes: Mapped[int]=mapped_column(Integer, default=0)
    parameters: Mapped[str|None]=mapped_column(Text, nullable=True)
    status: Mapped[str]=mapped_column(String, default="GENERATED")
    file_path: Mapped[str|None]=mapped_column(String, nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)

class ReportJob(Base):
    __tablename__="report_jobs"
    id: Mapped[str]=mapped_column(String, primary_key=True, default=uid)
    organization_id: Mapped[str]=mapped_column(String, index=True)
    user_id: Mapped[str]=mapped_column(String)
    report_id: Mapped[str|None]=mapped_column(String, nullable=True)
    job_type: Mapped[str]=mapped_column(String, default="EXECUTIVE_DIGEST")
    status: Mapped[str]=mapped_column(String, default="QUEUED")  # QUEUED | RUNNING | SUCCEEDED | FAILED
    delivery_channel: Mapped[str]=mapped_column(String, default="DOWNLOAD")  # DOWNLOAD | EMAIL_SIMULATED | WEBHOOK
    delivery_status: Mapped[str]=mapped_column(String, default="READY_FOR_DOWNLOAD")
    error_message: Mapped[str|None]=mapped_column(Text, nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime|None]=mapped_column(DateTime, nullable=True)

class AuditLog(Base):
    __tablename__="audit_logs"
    id: Mapped[str]=mapped_column(String, primary_key=True, default=uid)
    organization_id: Mapped[str]=mapped_column(String, index=True)
    user_id: Mapped[str|None]=mapped_column(String, nullable=True)
    action: Mapped[str]=mapped_column(String)
    status: Mapped[str]=mapped_column(String)
    detail: Mapped[str|None]=mapped_column(Text, nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)

class BillingImport(Base):
    __tablename__="billing_imports"
    id: Mapped[str]=mapped_column(String, primary_key=True, default=uid)
    organization_id: Mapped[str]=mapped_column(String, ForeignKey("organizations.id"), index=True)
    user_id: Mapped[str|None]=mapped_column(String, ForeignKey("users.id"), nullable=True)
    filename: Mapped[str]=mapped_column(String)
    file_hash: Mapped[str]=mapped_column(String, index=True)
    idempotency_key: Mapped[str|None]=mapped_column(String, index=True, nullable=True)
    status: Mapped[str]=mapped_column(String, default="PENDING")
    total_rows: Mapped[int]=mapped_column(Integer, default=0)
    imported_rows: Mapped[int]=mapped_column(Integer, default=0)
    error_count: Mapped[int]=mapped_column(Integer, default=0)
    errors_summary: Mapped[str|None]=mapped_column(Text, nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime|None]=mapped_column(DateTime, nullable=True)

class SavingsLedger(Base):
    __tablename__="savings_ledger"
    id: Mapped[str]=mapped_column(String, primary_key=True, default=uid)
    organization_id: Mapped[str]=mapped_column(String, index=True)
    recommendation_id: Mapped[str|None]=mapped_column(String, nullable=True)
    resource_id: Mapped[str]=mapped_column(String)
    title: Mapped[str]=mapped_column(String)
    category: Mapped[str]=mapped_column(String, default="RIGHTSIZING")
    savings_type: Mapped[str]=mapped_column(String, default="EXPECTED")  # EXPECTED | VERIFIED
    status: Mapped[str]=mapped_column(String, default="PLANNED")  # PLANNED | REALIZED | DEVIATED | REVERTED
    expected_monthly_cost_saving: Mapped[float]=mapped_column(Float, default=0.0)
    expected_monthly_carbon_saving_kg: Mapped[float]=mapped_column(Float, default=0.0)
    verified_cost_saving: Mapped[float]=mapped_column(Float, default=0.0)
    verified_carbon_saving_kg: Mapped[float]=mapped_column(Float, default=0.0)
    measurement_window_start: Mapped[datetime|None]=mapped_column(DateTime, nullable=True)
    measurement_window_end: Mapped[datetime|None]=mapped_column(DateTime, nullable=True)
    caveats: Mapped[str|None]=mapped_column(Text, nullable=True)
    notes: Mapped[str|None]=mapped_column(Text, nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class SimulationScenario(Base):
    __tablename__="simulation_scenarios"
    id: Mapped[str]=mapped_column(String, primary_key=True, default=uid)
    organization_id: Mapped[str]=mapped_column(String, index=True)
    user_id: Mapped[str]=mapped_column(String)
    name: Mapped[str]=mapped_column(String)
    scenario_type: Mapped[str]=mapped_column(String, default="RECOMMENDATION")  # RECOMMENDATION | RIGHTSIZING | SCHEDULED_IDLE | SAVINGS_PLAN | REGION_MIGRATION
    inputs: Mapped[str]=mapped_column(Text)  # JSON serialized parameters
    assumptions: Mapped[str]=mapped_column(Text)  # JSON serialized assumptions
    pricing_source: Mapped[str]=mapped_column(String, default="AWS On-Demand Catalog 2025")
    factor_source: Mapped[str]=mapped_column(String, default="EPA eGRID 2024")
    results: Mapped[str]=mapped_column(Text)  # JSON serialized results
    created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)
