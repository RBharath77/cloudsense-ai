import csv
import io
from datetime import datetime, timedelta
from typing import Any
from sqlalchemy import func, distinct
from sqlalchemy.orm import Session
from ..models import CostRecord, BillingImport, CloudResource, Recommendation, Anomaly, CarbonRecord

def _parse_filter_date(val: str | datetime | None) -> datetime | None:
    if not val:
        return None
    if isinstance(val, datetime):
        return val
    try:
        if len(val) == 10:
            return datetime.strptime(val, "%Y-%m-%d")
        return datetime.fromisoformat(val)
    except Exception:
        return None

def _sanitize_csv_cell(value: Any) -> Any:
    if isinstance(value, str) and value and value[0] in ("=", "+", "-", "@", "\t", "\r"):
        return f"'{value}"
    return value

def _build_cost_query(
    db: Session,
    organization_id: str,
    start_date: str | datetime | None = None,
    end_date: str | datetime | None = None,
    provider: str | None = None,
    service: str | None = None,
    region: str | None = None,
):
    query = db.query(CostRecord).filter(CostRecord.organization_id == organization_id)
    
    start_dt = _parse_filter_date(start_date)
    if start_dt:
        query = query.filter(CostRecord.recorded_at >= start_dt)
        
    end_dt = _parse_filter_date(end_date)
    if end_dt:
        if len(str(end_date)) == 10:
            # End of day
            end_dt = end_dt.replace(hour=23, minute=59, second=59)
        query = query.filter(CostRecord.recorded_at <= end_dt)
        
    if provider and provider.upper() != "ALL":
        query = query.filter(func.upper(CostRecord.provider) == provider.upper())
        
    if service and service.upper() != "ALL":
        query = query.filter(CostRecord.service == service)
        
    if region and region.upper() != "ALL":
        query = query.filter(CostRecord.region == region)
        
    return query

def get_cost_summary(
    db: Session,
    organization_id: str,
    start_date: str | datetime | None = None,
    end_date: str | datetime | None = None,
    provider: str | None = None,
    service: str | None = None,
    region: str | None = None,
    group_by: str = "provider",
) -> dict:
    base_q = _build_cost_query(db, organization_id, start_date, end_date, provider, service, region)
    
    # 1. Total Spend and Count
    total_spend = base_q.with_entities(func.sum(CostRecord.amount)).scalar() or 0.0
    total_spend = round(float(total_spend), 2)
    record_count = base_q.count()
    
    # 2. Prior Period Comparison
    start_dt = _parse_filter_date(start_date)
    end_dt = _parse_filter_date(end_date) or datetime.utcnow()
    
    if start_dt:
        window = end_dt - start_dt
        prev_end = start_dt
        prev_start = start_dt - window
    else:
        window = timedelta(days=30)
        prev_end = end_dt - window
        prev_start = prev_end - window
        
    prev_q = _build_cost_query(db, organization_id, prev_start, prev_end, provider, service, region)
    prev_spend = prev_q.with_entities(func.sum(CostRecord.amount)).scalar() or 0.0
    prev_spend = round(float(prev_spend), 2)
    
    change_amount = round(total_spend - prev_spend, 2)
    change_pct = round(((total_spend - prev_spend) / prev_spend) * 100, 1) if prev_spend > 0 else None
    
    # 3. Breakdown
    items: list[dict] = []
    if group_by == "service":
        col = CostRecord.service
    elif group_by == "region":
        col = CostRecord.region
    else:
        col = CostRecord.provider
        group_by = "provider"
        
    group_rows = (
        base_q.with_entities(col, func.sum(CostRecord.amount), func.count(CostRecord.id))
        .group_by(col)
        .order_by(func.sum(CostRecord.amount).desc())
        .all()
    )
    
    for key, amt, count in group_rows:
        cost_val = round(float(amt), 2)
        pct = round((cost_val / total_spend) * 100, 1) if total_spend > 0 else 0.0
        items.append({
            "key": key or "Unknown",
            "cost": cost_val,
            "percentage": pct,
            "record_count": count,
        })
        
    # 4. Data Lineage: Contributing Imports
    distinct_import_ids = [
        r[0] for r in base_q.with_entities(distinct(CostRecord.import_id)).all() if r[0]
    ]
    
    return {
        "total_cost": total_spend,
        "previous_cost": prev_spend,
        "change_amount": change_amount,
        "change_percentage": change_pct,
        "group_by": group_by,
        "items": items,
        "record_count": record_count,
        "providers": [
            {"provider": item["key"], "cost": item["cost"]}
            for item in items
        ] if group_by == "provider" else [
            {"provider": item["key"], "cost": item["cost"]}
            for item in items
        ],
        "lineage": {
            "contributing_import_ids": distinct_import_ids,
            "contributing_import_count": len(distinct_import_ids),
        },
        "filters_applied": {
            "start_date": start_dt.strftime("%Y-%m-%d") if start_dt else None,
            "end_date": end_dt.strftime("%Y-%m-%d") if end_dt else None,
            "provider": provider if provider and provider.upper() != "ALL" else None,
            "service": service if service and service.upper() != "ALL" else None,
            "region": region if region and region.upper() != "ALL" else None,
        }
    }

def get_daily_costs(
    db: Session,
    organization_id: str,
    start_date: str | datetime | None = None,
    end_date: str | datetime | None = None,
    provider: str | None = None,
    service: str | None = None,
    region: str | None = None,
) -> list[dict]:
    base_q = _build_cost_query(db, organization_id, start_date, end_date, provider, service, region)
    
    # Group by recorded date
    rows = (
        base_q.with_entities(
            func.date(CostRecord.recorded_at),
            func.sum(CostRecord.amount),
            func.count(CostRecord.id)
        )
        .group_by(func.date(CostRecord.recorded_at))
        .order_by(func.date(CostRecord.recorded_at))
        .all()
    )
    
    return [
        {
            "date": str(d),
            "cost": round(float(amt), 2),
            "record_count": cnt,
        }
        for d, amt, cnt in rows
    ]

def get_dashboard_metrics(db: Session, organization_id: str, days: int = 30) -> dict:
    now = datetime.utcnow()
    period_start = now - timedelta(days=days)
    
    summary = get_cost_summary(db, organization_id, start_date=period_start, end_date=now)
    total_spend = summary["total_cost"]
    
    # Fallback to monthly cost on resources if cost records empty
    res_monthly = db.query(func.sum(CloudResource.monthly_cost)).filter_by(organization_id=organization_id).scalar() or 0.0
    display_spend = total_spend if total_spend > 0 else round(float(res_monthly), 2)
    
    savings = (
        db.query(func.sum(Recommendation.monthly_saving))
        .filter(Recommendation.organization_id == organization_id, Recommendation.action_status == "PENDING")
        .scalar()
        or 0.0
    )
    
    res_count = db.query(CloudResource).filter_by(organization_id=organization_id).count()
    avg_health = db.query(func.avg(CloudResource.health)).filter_by(organization_id=organization_id).scalar()
    health_val = round(float(avg_health), 1) if avg_health is not None else 100.0
    
    carbon_val = (
        db.query(func.sum(CarbonRecord.co2_kg))
        .filter_by(organization_id=organization_id)
        .scalar()
        or 0.0
    )
    
    latest_import = (
        db.query(BillingImport)
        .filter_by(organization_id=organization_id, status="COMPLETED")
        .order_by(BillingImport.created_at.desc())
        .first()
    )
    
    return {
        "total_spend": display_spend,
        "current_month_spend": display_spend,
        "previous_period_spend": summary["previous_cost"],
        "change_percentage": summary["change_percentage"],
        "predicted_month_end": round(display_spend * 1.102, 2),
        "potential_savings": round(float(savings), 2),
        "active_resources": res_count,
        "anomalies": db.query(Anomaly).filter_by(organization_id=organization_id).count(),
        "cloud_health": health_val,
        "carbon_kg": round(float(carbon_val), 2),
        "contributing_imports": summary["lineage"]["contributing_import_count"],
        "latest_import_time": latest_import.created_at.isoformat() if latest_import else None,
    }

def generate_costs_csv(
    db: Session,
    organization_id: str,
    start_date: str | datetime | None = None,
    end_date: str | datetime | None = None,
    provider: str | None = None,
    service: str | None = None,
    region: str | None = None,
) -> tuple[str, float, int]:
    base_q = _build_cost_query(db, organization_id, start_date, end_date, provider, service, region)
    records = base_q.order_by(CostRecord.recorded_at.desc()).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Headers
    writer.writerow([
        "id",
        "date",
        "provider",
        "service",
        "region",
        "resource_id",
        "amount",
        "currency",
        "import_id",
    ])
    
    total_amount = 0.0
    for r in records:
        amt = round(float(r.amount), 4)
        total_amount += amt
        writer.writerow([
            r.id,
            r.recorded_at.strftime("%Y-%m-%d %H:%M:%S") if r.recorded_at else "",
            _sanitize_csv_cell(r.provider),
            _sanitize_csv_cell(r.service),
            _sanitize_csv_cell(r.region),
            _sanitize_csv_cell(r.resource_id or ""),
            f"{amt:.2f}",
            r.currency or "USD",
            r.import_id or "",
        ])
        
    return output.getvalue(), round(total_amount, 2), len(records)

def get_cost_lineage(
    db: Session,
    organization_id: str,
    start_date: str | datetime | None = None,
    end_date: str | datetime | None = None,
    provider: str | None = None,
    service: str | None = None,
    region: str | None = None,
) -> dict:
    base_q = _build_cost_query(db, organization_id, start_date, end_date, provider, service, region)
    
    total_cost = round(float(base_q.with_entities(func.sum(CostRecord.amount)).scalar() or 0.0), 2)
    record_count = base_q.count()
    
    distinct_imports = (
        base_q.filter(CostRecord.import_id.isnot(None))
        .with_entities(distinct(CostRecord.import_id))
        .all()
    )
    import_ids = [r[0] for r in distinct_imports if r[0]]
    
    import_details = []
    if import_ids:
        imports = db.query(BillingImport).filter(BillingImport.id.in_(import_ids)).all()
        for imp in imports:
            import_details.append({
                "id": imp.id,
                "filename": imp.filename,
                "created_at": imp.created_at.isoformat(),
                "status": imp.status,
                "total_rows": imp.total_rows,
                "imported_rows": imp.imported_rows,
            })
            
    return {
        "total_cost": total_cost,
        "record_count": record_count,
        "contributing_imports": import_details,
        "import_coverage_count": len(import_details),
    }
