from app.ml import forecast, detect_anomalies

def test_forecast():
    r=forecast(list(range(30)),7); assert len(r['predictions'])==7; assert r['rmse']>=0
    assert len(r['lower'])==7
    assert len(r['upper'])==7

def test_forecast_multiple_horizons():
    for h in [1, 7, 14, 30, 60]:
        res = forecast(list(range(40)), horizon=h)
        assert len(res['predictions']) == h
        assert len(res['lower']) == h
        assert len(res['upper']) == h
        assert res['mae'] is not None and res['mae'] >= 0
        assert res['rmse'] is not None and res['rmse'] >= 0

def test_forecast_insufficient_data():
    res = forecast([10.0, 12.0], horizon=10)
    assert len(res['predictions']) == 10
    assert res['mae'] is None
    assert res['rmse'] is None

def test_anomaly():
    vals=[1]*30+[50]; assert 30 in detect_anomalies(vals)
