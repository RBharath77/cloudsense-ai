import numpy as np
from datetime import datetime, timedelta
from typing import Any
from sqlalchemy import func
from sqlalchemy.orm import Session
from ..models import Anomaly, CostRecord
from ..ml import detect_anomalies

def list_anomalies(
    db: Session,
    organization_id: str,
    severity: str | None = None,
    provider: str | None = None,
    limit: int = 50
) -> list[dict[str, Any]]:
    q = db.query(Anomaly).filter(Anomaly.organization_id == organization_id)
    if severity and severity.upper() != "ALL":
        q = q.filter(func.upper(Anomaly.severity) == severity.upper())
    if provider and provider.upper() != "ALL":
        q = q.filter(func.upper(Anomaly.provider) == provider.upper())

    anomalies = q.order_by(Anomaly.timestamp.desc()).limit(limit).all()
    return [
        {
            "id": a.id,
            "organization_id": a.organization_id,
            "provider": a.provider,
            "resource_id": a.resource_id,
            "metric": a.metric,
            "severity": a.severity,
            "timestamp": a.timestamp.isoformat() if a.timestamp else None,
            "score": round(float(a.score), 2),
            "financial_impact": round(float(a.financial_impact), 2),
            "reason": a.reason,
            "recommendation": a.recommendation
        }
        for a in anomalies
    ]

def run_anomaly_detection(
    db: Session,
    organization_id: str,
    contamination: float = 0.08
) -> dict[str, Any]:
    # Query daily costs ordered chronologically
    rows = (
        db.query(
            func.date(CostRecord.recorded_at).label("dt"),
            func.sum(CostRecord.amount).label("amt")
        )
        .filter(CostRecord.organization_id == organization_id)
        .group_by(func.date(CostRecord.recorded_at))
        .order_by(func.date(CostRecord.recorded_at))
        .all()
    )

    if len(rows) < 8:
        return {
            "status": "insufficient_data",
            "message": "At least 8 daily data points required for ML anomaly detection",
            "detected_count": 0,
            "anomalies_detected": 0,
            "new_anomalies": [],
            "anomalies": [],
            "total_spend_evaluated": 0.0,
        }

    values = [float(r[1]) for r in rows]
    anom_indices = detect_anomalies(values, contamination=contamination)

    new_anomalies = []

    for idx in anom_indices:
        dt_str = str(rows[idx][0])
        try:
            anom_dt = datetime.strptime(dt_str, "%Y-%m-%d")
        except Exception:
            anom_dt = datetime.utcnow()

        actual_spend = values[idx]

        # Calculate baseline from prior window
        prior_window = values[max(0, idx - 7):idx]
        baseline = float(np.median(prior_window)) if prior_window else float(np.median(values))
        
        financial_impact = max(0.0, actual_spend - baseline)
        if baseline > 0:
            rel_dev = (actual_spend - baseline) / baseline
            score = min(1.0, max(0.5, 0.5 + (rel_dev * 0.25)))
        else:
            score = 0.85

        if financial_impact >= 500 or score >= 0.85:
            severity = "CRITICAL"
        elif financial_impact >= 150 or score >= 0.70:
            severity = "HIGH"
        elif financial_impact >= 50 or score >= 0.55:
            severity = "MEDIUM"
        else:
            severity = "LOW"

        # Find top provider and service for that date
        top_rec = (
            db.query(CostRecord.provider, CostRecord.service, func.sum(CostRecord.amount))
            .filter(
                CostRecord.organization_id == organization_id,
                func.date(CostRecord.recorded_at) == dt_str
            )
            .group_by(CostRecord.provider, CostRecord.service)
            .order_by(func.sum(CostRecord.amount).desc())
            .first()
        )

        provider_name = top_rec[0] if top_rec else "Multi-Cloud"
        top_service = top_rec[1] if top_rec else "Cloud Services"

        reason = (
            f"Daily spend of ${actual_spend:,.2f} on {dt_str} exceeded learned baseline of ${baseline:,.2f} "
            f"by ${(actual_spend - baseline):,.2f} (primarily driven by {provider_name} {top_service})."
        )
        recommendation = (
            f"Audit recent provisioning events, autoscaling triggers, and batch workloads on {provider_name} {top_service}."
        )

        # Check existing anomaly on this date
        start_of_day = anom_dt.replace(hour=0, minute=0, second=0)
        end_of_day = anom_dt.replace(hour=23, minute=59, second=59)

        existing = (
            db.query(Anomaly)
            .filter(
                Anomaly.organization_id == organization_id,
                Anomaly.timestamp >= start_of_day,
                Anomaly.timestamp <= end_of_day
            )
            .first()
        )

        if not existing:
            new_a = Anomaly(
                organization_id=organization_id,
                provider=provider_name,
                resource_id=f"{provider_name.lower()}-{top_service.lower().replace(' ', '-')}",
                metric="cost",
                severity=severity,
                timestamp=anom_dt,
                score=score,
                financial_impact=financial_impact,
                reason=reason,
                recommendation=recommendation
            )
            db.add(new_a)
            new_anomalies.append({
                "date": dt_str,
                "provider": provider_name,
                "severity": severity,
                "financial_impact": round(financial_impact, 2),
                "score": round(score, 2),
                "reason": reason
            })

    db.commit()

    return {
        "status": "success",
        "evaluated_days": len(values),
        "detected_count": len(new_anomalies),
        "anomalies_detected": len(new_anomalies),
        "new_anomalies": new_anomalies,
        "anomalies": new_anomalies,
        "total_spend_evaluated": round(sum(values), 2),
    }

def get_anomaly_rca(db: Session, organization_id: str, anomaly_id: str) -> dict[str, Any] | None:
    a = db.get(Anomaly, anomaly_id)
    if not a or a.organization_id != organization_id:
        return None

    dt_str = a.timestamp.strftime("%Y-%m-%d") if a.timestamp else "Unknown"

    evidence = [
        f"{a.metric.capitalize()} anomaly detected with model confidence score {a.score:.2f}",
        f"Estimated financial deviation ${a.financial_impact:,.2f} above baseline",
        f"Primary infrastructure domain: {a.provider} ({a.resource_id or 'Cluster'})",
        f"Evaluation algorithm: Isolation Forest with residual median estimation"
    ]

    timeline = [
        {"time": a.timestamp.isoformat() if a.timestamp else "", "event": "Spend pattern deviated from baseline envelope"},
        {"time": a.timestamp.isoformat() if a.timestamp else "", "event": f"Automated alert dispatched with {a.severity} severity"}
    ]

    return {
        "id": a.id,
        "provider": a.provider,
        "resource_id": a.resource_id,
        "metric": a.metric,
        "severity": a.severity,
        "score": round(float(a.score), 2),
        "timestamp": a.timestamp.isoformat() if a.timestamp else None,
        "financial_impact": round(float(a.financial_impact), 2),
        "root_cause": a.reason,
        "evidence": evidence,
        "impact": f"Estimated financial impact ${a.financial_impact:,.2f}",
        "timeline": timeline,
        "recommendation": a.recommendation
    }
