from datetime import datetime, timedelta
from typing import Any
from sqlalchemy import func
from sqlalchemy.orm import Session
from ..models import CostRecord
from ..ml import forecast

def generate_cost_forecast(
    db: Session,
    organization_id: str,
    horizon: int = 30,
    provider: str | None = None,
    confidence: float = 0.95,
    confidence_level: float | None = None,
) -> dict[str, Any]:
    if confidence_level is not None:
        confidence = confidence_level
    h = max(1, min(180, int(horizon)))
    conf = float(confidence) if 0.5 <= float(confidence) <= 0.99 else 0.95

    # Retrieve daily costs
    q = db.query(
        func.date(CostRecord.recorded_at).label("d"),
        func.sum(CostRecord.amount).label("amt")
    ).filter(CostRecord.organization_id == organization_id)

    if provider and provider.upper() != "ALL":
        q = q.filter(func.upper(CostRecord.provider) == provider.upper())

    rows = q.group_by(func.date(CostRecord.recorded_at)).order_by(func.date(CostRecord.recorded_at)).all()

    values = [float(amt) for _, amt in rows]
    
    # Run ML forecasting
    ml_result = forecast(values, horizon=h, confidence=conf)

    # Determine date range for predictions
    if rows:
        last_date_str = str(rows[-1][0])
        try:
            last_date = datetime.strptime(last_date_str, "%Y-%m-%d").date()
        except Exception:
            last_date = datetime.utcnow().date()
    else:
        last_date = datetime.utcnow().date()

    future_dates = [(last_date + timedelta(days=i + 1)).strftime("%Y-%m-%d") for i in range(h)]

    forecast_series = [
        {
            "date": future_dates[i],
            "prediction": ml_result["predictions"][i],
            "lower": ml_result["lower"][i],
            "upper": ml_result["upper"][i],
        }
        for i in range(h)
    ]

    historical_series = [
        {"date": str(d), "cost": round(float(amt), 2)}
        for d, amt in rows[-60:]
    ]

    total_predicted = round(sum(ml_result["predictions"]), 2)
    daily_avg_predicted = round(total_predicted / h, 2) if h > 0 else 0.0

    return {
        "predictions": ml_result["predictions"],
        "lower": ml_result["lower"],
        "upper": ml_result["upper"],
        "forecast_series": forecast_series,
        "historical_series": historical_series,
        "mae": ml_result["mae"],
        "rmse": ml_result["rmse"],
        "baseline_mae": ml_result["baseline_mae"],
        "baseline_rmse": ml_result["baseline_rmse"],
        "improvement_pct": ml_result["improvement_pct"],
        "total_predicted_spend": total_predicted,
        "daily_average_predicted": daily_avg_predicted,
        "model_name": ml_result["model_name"],
        "confidence": conf,
        "horizon": h,
        "training_samples": ml_result["training_samples"],
        "provider": provider if provider and provider.upper() != "ALL" else "ALL"
    }
