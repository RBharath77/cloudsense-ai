import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.metrics import mean_absolute_error, mean_squared_error

def forecast(values, horizon=30):
    y=np.asarray(values,dtype=float)
    if len(y)<5: return {"predictions": [float(y[-1]) if len(y) else 0]*horizon, "mae": None, "rmse": None}
    x=np.arange(len(y)); coef=np.polyfit(x,y,1); trend=np.polyval(coef,np.arange(len(y),len(y)+horizon))
    split=max(3,len(y)-horizon//2); pred=np.polyval(coef,np.arange(split,len(y)))
    mae=float(mean_absolute_error(y[split:],pred)); rmse=float(mean_squared_error(y[split:],pred)**0.5)
    std=float(np.std(y-pred)) if len(pred) else 0
    return {"predictions":trend.tolist(),"mae":mae,"rmse":rmse,"lower":(trend-1.96*std).tolist(),"upper":(trend+1.96*std).tolist()}

def detect_anomalies(values):
    x=np.asarray(values,dtype=float).reshape(-1,1)
    if len(x)<8: return []
    model=IsolationForest(contamination=0.08,random_state=42).fit(x)
    return [int(i) for i,p in enumerate(model.predict(x)) if p==-1]
