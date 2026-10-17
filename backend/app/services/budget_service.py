import calendar
from datetime import datetime, timedelta
from typing import Any
from sqlalchemy import func
from sqlalchemy.orm import Session
from ..models import Budget, CostRecord, CloudResource

def get_budget_period_window(period: str = "MONTHLY", ref_date: datetime | None = None) -> tuple[datetime, datetime]:
    ref = ref_date or datetime.utcnow()
    period_upper = (period or "MONTHLY").upper()

    if period_upper == "ALL":
        start_dt = datetime(2000, 1, 1, 0, 0, 0)
        end_dt = datetime(2099, 12, 31, 23, 59, 59)
    elif period_upper == "MONTHLY":
        start_dt = datetime(ref.year, ref.month, 1, 0, 0, 0)
        _, last_day = calendar.monthrange(ref.year, ref.month)
        end_dt = datetime(ref.year, ref.month, last_day, 23, 59, 59)
    elif period_upper == "QUARTERLY":
        quarter = (ref.month - 1) // 3 + 1
        start_month = (quarter - 1) * 3 + 1
        end_month = start_month + 2
        start_dt = datetime(ref.year, start_month, 1, 0, 0, 0)
        _, last_day = calendar.monthrange(ref.year, end_month)
        end_dt = datetime(ref.year, end_month, last_day, 23, 59, 59)
    elif period_upper == "ANNUAL":
        start_dt = datetime(ref.year, 1, 1, 0, 0, 0)
        end_dt = datetime(ref.year, 12, 31, 23, 59, 59)
    else:
        # Default rolling 30-day window
        start_dt = ref - timedelta(days=30)
        end_dt = ref

    return start_dt, end_dt

def evaluate_budget(db: Session, budget: Budget) -> dict[str, Any]:
    start_dt, end_dt = get_budget_period_window(budget.period)
    now = datetime.utcnow()

    # Query matching CostRecords
    q = db.query(CostRecord).filter(
        CostRecord.organization_id == budget.organization_id,
        CostRecord.recorded_at >= start_dt,
        CostRecord.recorded_at <= end_dt
    )

    scope = (budget.scope or "ORGANIZATION").upper()
    target = budget.target or "ALL"

    if scope == "PROVIDER" and target.upper() != "ALL":
        q = q.filter(func.upper(CostRecord.provider) == target.upper())
    elif scope == "SERVICE" and target.upper() != "ALL":
        q = q.filter(CostRecord.service == target)

    actual_sum = q.with_entities(func.sum(CostRecord.amount)).scalar() or 0.0
    actual_spend = round(float(actual_sum), 2)

    limit = float(budget.amount)
    pct_used = round((actual_spend / limit) * 100, 1) if limit > 0 else 0.0

    # Linear burn-rate projection
    days_elapsed = max(1, (min(now, end_dt) - start_dt).days + 1)
    total_days = max(1, (end_dt - start_dt).days + 1)
    daily_rate = actual_spend / days_elapsed
    forecast_spend = round(daily_rate * total_days, 2)

    # Determine status
    thresh = float(budget.threshold or 0.9)
    if actual_spend >= limit:
        status = "EXCEEDED"
    elif pct_used >= (thresh * 100):
        status = "WARNING"
    else:
        status = "OK"

    if forecast_spend >= limit:
        forecast_status = "EXCEEDED"
    elif limit > 0 and (forecast_spend / limit) >= thresh:
        forecast_status = "WARNING"
    else:
        forecast_status = "OK"

    return {
        "id": budget.id,
        "organization_id": budget.organization_id,
        "name": budget.name or f"{budget.scope.capitalize()}: {budget.target}",
        "scope": budget.scope,
        "target": budget.target,
        "amount": round(limit, 2),
        "threshold": round(thresh, 2),
        "period": budget.period or "MONTHLY",
        "created_at": budget.created_at.isoformat() if budget.created_at else None,
        "period_start": start_dt.strftime("%Y-%m-%d"),
        "period_end": end_dt.strftime("%Y-%m-%d"),
        "actual_spend": actual_spend,
        "remaining_amount": round(max(0.0, limit - actual_spend), 2),
        "percentage_used": pct_used,
        "forecast_spend": forecast_spend,
        "status": status,
        "forecast_status": forecast_status,
        "currency": "USD"
    }

def list_budgets(db: Session, organization_id: str) -> list[dict[str, Any]]:
    budgets = (
        db.query(Budget)
        .filter(Budget.organization_id == organization_id)
        .order_by(Budget.created_at.desc())
        .all()
    )
    return [evaluate_budget(db, b) for b in budgets]

def get_budget_detail(db: Session, organization_id: str, budget_id: str) -> dict[str, Any] | None:
    budget = db.get(Budget, budget_id)
    if not budget or budget.organization_id != organization_id:
        return None

    evaluation = evaluate_budget(db, budget)
    start_dt, end_dt = get_budget_period_window(budget.period)

    # Daily spend history for this budget
    daily_q = (
        db.query(func.date(CostRecord.recorded_at), func.sum(CostRecord.amount))
        .filter(
            CostRecord.organization_id == organization_id,
            CostRecord.recorded_at >= start_dt,
            CostRecord.recorded_at <= end_dt
        )
    )

    scope = (budget.scope or "ORGANIZATION").upper()
    target = budget.target or "ALL"
    if scope == "PROVIDER" and target.upper() != "ALL":
        daily_q = daily_q.filter(func.upper(CostRecord.provider) == target.upper())
    elif scope == "SERVICE" and target.upper() != "ALL":
        daily_q = daily_q.filter(CostRecord.service == target)

    daily_rows = daily_q.group_by(func.date(CostRecord.recorded_at)).order_by(func.date(CostRecord.recorded_at)).all()
    evaluation["daily_trend"] = [
        {"date": str(d), "cost": round(float(amt), 2)}
        for d, amt in daily_rows
    ]

    return evaluation

def create_budget(db: Session, organization_id: str, data: dict) -> dict[str, Any]:
    amount = float(data.get("amount", 0))
    if amount <= 0:
        raise ValueError("Budget amount must be strictly greater than 0")

    threshold = float(data.get("threshold", 0.9))
    if threshold <= 0 or threshold > 1.0:
        raise ValueError("Budget threshold must be between 0.01 and 1.0 (e.g. 0.8 for 80%)")

    scope = (data.get("scope") or "ORGANIZATION").upper()
    if scope not in {"ORGANIZATION", "PROVIDER", "SERVICE"}:
        raise ValueError("Budget scope must be ORGANIZATION, PROVIDER, or SERVICE")

    target = str(data.get("target") or "ALL").strip()
    name = data.get("name") or f"{scope.capitalize()}: {target}"
    period = (data.get("period") or "MONTHLY").upper()
    if period not in {"MONTHLY", "QUARTERLY", "ANNUAL", "ALL"}:
        period = "MONTHLY"

    b = Budget(
        organization_id=organization_id,
        name=name,
        scope=scope,
        target=target,
        amount=amount,
        threshold=threshold,
        period=period,
        created_at=datetime.utcnow()
    )
    db.add(b)
    db.commit()
    db.refresh(b)
    return evaluate_budget(db, b)

def update_budget(db: Session, organization_id: str, budget_id: str, data: dict) -> dict[str, Any] | None:
    b = db.get(Budget, budget_id)
    if not b or b.organization_id != organization_id:
        return None

    if "amount" in data:
        amt = float(data["amount"])
        if amt <= 0:
            raise ValueError("Budget amount must be strictly greater than 0")
        b.amount = amt

    if "threshold" in data:
        thresh = float(data["threshold"])
        if thresh <= 0 or thresh > 1.0:
            raise ValueError("Budget threshold must be between 0.01 and 1.0")
        b.threshold = thresh

    if "name" in data and data["name"]:
        b.name = str(data["name"]).strip()

    if "period" in data and data["period"]:
        period = str(data["period"]).upper()
        if period in {"MONTHLY", "QUARTERLY", "ANNUAL", "ALL"}:
            b.period = period

    if "scope" in data and data["scope"]:
        scope = str(data["scope"]).upper()
        if scope in {"ORGANIZATION", "PROVIDER", "SERVICE"}:
            b.scope = scope

    if "target" in data and data["target"]:
        b.target = str(data["target"]).strip()

    db.commit()
    db.refresh(b)
    return evaluate_budget(db, b)

def delete_budget(db: Session, organization_id: str, budget_id: str) -> bool:
    b = db.get(Budget, budget_id)
    if not b or b.organization_id != organization_id:
        return False
    db.delete(b)
    db.commit()
    return True
