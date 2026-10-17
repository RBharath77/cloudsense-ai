import hashlib
from datetime import datetime, timedelta
from typing import Any
from sqlalchemy import func
from sqlalchemy.orm import Session
from ..models import Alert, Budget, CostRecord, Anomaly
from .budget_service import evaluate_budget, get_budget_period_window

def compute_alert_fingerprint(
    organization_id: str,
    entity_type: str,
    entity_id: str,
    alert_type: str,
    period_key: str
) -> str:
    raw = f"{organization_id}:{entity_type}:{entity_id}:{alert_type}:{period_key}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def evaluate_organization_alerts(db: Session, organization_id: str) -> dict[str, Any]:
    now = datetime.utcnow()
    created_count = 0
    updated_count = 0

    # 1. Evaluate All Active Budgets
    budgets = db.query(Budget).filter_by(organization_id=organization_id).all()
    for b in budgets:
        eval_res = evaluate_budget(db, b)
        status = eval_res["status"]
        period_key = f"{eval_res['period_start']}_{eval_res['period_end']}"

        if status in {"WARNING", "EXCEEDED"}:
            alert_type = f"BUDGET_{status}"
            severity = "CRITICAL" if status == "EXCEEDED" else "HIGH"
            title = (
                f"Budget Exceeded: {eval_res['name']}"
                if status == "EXCEEDED"
                else f"Budget Warning: {eval_res['name']}"
            )
            msg = (
                f"Current spend of ${eval_res['actual_spend']:,.2f} ({eval_res['percentage_used']}%) "
                f"has {'exceeded' if status == 'EXCEEDED' else 'reached threshold for'} the ${eval_res['amount']:,.2f} limit."
            )
            fp = compute_alert_fingerprint(organization_id, "BUDGET", b.id, alert_type, period_key)

            existing = db.query(Alert).filter_by(organization_id=organization_id, fingerprint=fp).first()
            if existing:
                existing.message = msg
                existing.severity = severity
                existing.created_at = now
                updated_count += 1
            else:
                new_alert = Alert(
                    organization_id=organization_id,
                    type=alert_type,
                    severity=severity,
                    title=title,
                    message=msg,
                    fingerprint=fp,
                    read=False,
                    created_at=now
                )
                db.add(new_alert)
                created_count += 1

    # 2. Check Daily Cost Acceleration Spikes (Yesterday vs 7-day baseline)
    yesterday = (now - timedelta(days=1)).date()
    yesterday_spend = (
        db.query(func.sum(CostRecord.amount))
        .filter(
            CostRecord.organization_id == organization_id,
            func.date(CostRecord.recorded_at) == str(yesterday)
        )
        .scalar() or 0.0
    )

    prior_start = (now - timedelta(days=8)).date()
    prior_end = (now - timedelta(days=2)).date()
    prior_avg_spend = (
        db.query(func.avg(CostRecord.amount))
        .filter(
            CostRecord.organization_id == organization_id,
            func.date(CostRecord.recorded_at) >= str(prior_start),
            func.date(CostRecord.recorded_at) <= str(prior_end)
        )
        .scalar() or 0.0
    )

    if prior_avg_spend > 0 and yesterday_spend > (prior_avg_spend * 2.0) and (yesterday_spend - prior_avg_spend) > 50.0:
        fp = compute_alert_fingerprint(organization_id, "COST_RECORD", str(yesterday), "COST_SPIKE", str(yesterday))
        existing = db.query(Alert).filter_by(organization_id=organization_id, fingerprint=fp).first()
        spike_msg = (
            f"Daily cost spike on {yesterday}: spend was ${yesterday_spend:,.2f}, which is "
            f"{(yesterday_spend / prior_avg_spend):.1f}x the prior 7-day average (${prior_avg_spend:,.2f}/day)."
        )
        if existing:
            existing.message = spike_msg
            existing.created_at = now
            updated_count += 1
        else:
            db.add(Alert(
                organization_id=organization_id,
                type="COST_SPIKE",
                severity="HIGH",
                title=f"Cost Acceleration Spike Detected ({yesterday})",
                message=spike_msg,
                fingerprint=fp,
                read=False,
                created_at=now
            ))
            created_count += 1

    # 3. Check Recent Critical Anomalies (Last 24 Hours)
    crit_anomalies = (
        db.query(Anomaly)
        .filter(
            Anomaly.organization_id == organization_id,
            Anomaly.severity == "CRITICAL",
            Anomaly.timestamp >= now - timedelta(days=1)
        )
        .all()
    )
    for anom in crit_anomalies:
        fp = compute_alert_fingerprint(organization_id, "ANOMALY", anom.id, "CRITICAL_ANOMALY", anom.timestamp.strftime("%Y%m%d"))
        existing = db.query(Alert).filter_by(organization_id=organization_id, fingerprint=fp).first()
        if not existing:
            db.add(Alert(
                organization_id=organization_id,
                type="ANOMALY",
                severity="CRITICAL",
                title=f"Critical Cost Anomaly ({anom.provider})",
                message=f"Financial impact: ${anom.financial_impact:,.2f}. Reason: {anom.reason}",
                fingerprint=fp,
                read=False,
                created_at=now
            ))
            created_count += 1

    db.commit()
    return {
        "status": "success",
        "evaluated_budgets": len(budgets),
        "created_alerts": created_count,
        "updated_alerts": updated_count,
        "timestamp": now.isoformat()
    }

def list_alerts(
    db: Session,
    organization_id: str,
    unread_only: bool = False,
    severity: str | None = None,
    limit: int = 50
) -> list[dict[str, Any]]:
    q = db.query(Alert).filter(Alert.organization_id == organization_id)
    if unread_only:
        q = q.filter(Alert.read == False)
    if severity and severity.upper() != "ALL":
        q = q.filter(Alert.severity == severity.upper())

    alerts = q.order_by(Alert.read.asc(), Alert.created_at.desc()).limit(limit).all()
    return [
        {
            "id": a.id,
            "organization_id": a.organization_id,
            "type": a.type,
            "severity": a.severity,
            "title": a.title,
            "message": a.message,
            "read": a.read,
            "fingerprint": a.fingerprint,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in alerts
    ]

def mark_alert_read(db: Session, organization_id: str, alert_id: str) -> bool:
    a = db.get(Alert, alert_id)
    if not a or a.organization_id != organization_id:
        return False
    a.read = True
    db.commit()
    return True

def mark_all_alerts_read(db: Session, organization_id: str) -> int:
    updated = (
        db.query(Alert)
        .filter(Alert.organization_id == organization_id, Alert.read == False)
        .update({"read": True}, synchronize_session=False)
    )
    db.commit()
    return updated

def delete_alert(db: Session, organization_id: str, alert_id: str) -> bool:
    a = db.get(Alert, alert_id)
    if not a or a.organization_id != organization_id:
        return False
    db.delete(a)
    db.commit()
    return True
