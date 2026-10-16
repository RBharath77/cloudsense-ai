from app.ml import forecast, detect_anomalies

def test_forecast():
    r=forecast(list(range(30)),7); assert len(r['predictions'])==7; assert r['rmse']>=0

def test_anomaly():
    vals=[1]*30+[50]; assert 30 in detect_anomalies(vals)
