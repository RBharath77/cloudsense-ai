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
    created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)

class Report(Base):
    __tablename__="reports"
    id: Mapped[str]=mapped_column(String, primary_key=True, default=uid)
    organization_id: Mapped[str]=mapped_column(String, index=True)
    name: Mapped[str]=mapped_column(String)
    status: Mapped[str]=mapped_column(String, default="GENERATED")
    file_path: Mapped[str|None]=mapped_column(String, nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)

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
