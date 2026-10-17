import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.metrics import mean_absolute_error, mean_squared_error

def forecast(values, horizon=30, confidence=0.95):
    y = np.asarray(values, dtype=float)
    h = max(1, int(horizon))

    if len(y) < 5:
        last_val = max(0.0, float(y[-1])) if len(y) else 0.0
        fallback = [last_val] * h
        return {
            "predictions": fallback,
            "lower": fallback,
            "upper": fallback,
            "mae": None,
            "rmse": None,
            "baseline_mae": None,
            "baseline_rmse": None,
            "improvement_pct": None,
            "confidence": confidence,
            "horizon": h,
            "model_name": "Fallback Naive",
            "training_samples": len(y)
        }

    # Zero forward data leakage: train model strictly on y[:split] to evaluate on unseen y[split:]
    val_size = max(1, min(max(1, h // 2), len(y) - 3))
    split = len(y) - val_size
    y_train = y[:split]
    y_val = y[split:]

    x_train = np.arange(len(y_train))
    coef_train = np.polyfit(x_train, y_train, 1)

    # Predictions on validation window
    x_val = np.arange(split, len(y))
    pred_val = np.maximum(0.0, np.polyval(coef_train, x_val))

    # Model evaluation metrics
    model_mae = float(mean_absolute_error(y_val, pred_val))
    model_rmse = float(mean_squared_error(y_val, pred_val) ** 0.5)
    std_val = float(np.std(y_val - pred_val)) if len(pred_val) else 0.0

    # Naive baseline model: project last known training value forward
    naive_pred = np.full(val_size, max(0.0, float(y_train[-1])))
    baseline_mae = float(mean_absolute_error(y_val, naive_pred))
    baseline_rmse = float(mean_squared_error(y_val, naive_pred) ** 0.5)

    improvement_pct = (
        round(((baseline_mae - model_mae) / baseline_mae) * 100, 1)
        if baseline_mae > 0
        else 0.0
    )

    # Fit final model on all observed data for future prediction
    x_full = np.arange(len(y))
    coef = np.polyfit(x_full, y, 1)
    future_x = np.arange(len(y), len(y) + h)

    raw_trend = np.polyval(coef, future_x)
    # Non-negative guardrail: cloud cost cannot be negative
    trend = np.maximum(0.0, raw_trend)

    z = 1.96 if float(confidence) >= 0.90 else 1.28
    lower = np.maximum(0.0, trend - (z * std_val))
    upper = np.maximum(0.0, trend + (z * std_val))

    return {
        "predictions": [round(float(v), 2) for v in trend],
        "lower": [round(float(v), 2) for v in lower],
        "upper": [round(float(v), 2) for v in upper],
        "mae": round(model_mae, 2),
        "rmse": round(model_rmse, 2),
        "baseline_mae": round(baseline_mae, 2),
        "baseline_rmse": round(baseline_rmse, 2),
        "improvement_pct": improvement_pct,
        "confidence": float(confidence),
        "horizon": h,
        "model_name": "Polynomial Trend with Non-Negative Bounds",
        "training_samples": len(y)
    }

def detect_anomalies(values, contamination=0.08):
    x = np.asarray(values, dtype=float).reshape(-1, 1)
    if len(x) < 8:
        return []
    model = IsolationForest(contamination=contamination, random_state=42).fit(x)
    preds = model.predict(x)
    scores = -model.score_samples(x)  # Higher score = more anomalous

    results = []
    for i, p in enumerate(preds):
        if p == -1:
            results.append({
                "index": int(i),
                "value": float(values[i]),
                "score": round(float(scores[i]), 3)
            })
    return [r["index"] for r in results]
