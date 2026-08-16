import numpy as np
import pandas as pd
from scipy.stats import genpareto
from arch import arch_model
from .config import Config

def calculate_realized_volatility(hist: pd.DataFrame) -> dict:
    hist = hist.dropna()
    if len(hist) < 2: return {"value": None, "status": "DATA_UNAVAILABLE", "reason": "Insufficient history"}
    log_returns = np.log(hist['Close'] / hist['Close'].shift(1)).dropna()
    rv_30d_cc = np.std(log_returns.tail(30)) * np.sqrt(252) * 100
    return {"value": round(rv_30d_cc, 2), "status": "CALCULATED"}

def calculate_garch_forecast(hist: pd.DataFrame) -> dict:
    try:
        log_returns = np.log(hist['Close'] / hist['Close'].shift(1)).dropna() * 100
        res = arch_model(log_returns, vol='Garch', p=1, q=1, rescale=False).fit(disp='off')
        variance_5d = res.forecast(horizon=5, reindex=False).variance.values[-1].mean()
        
        # FIX: Returns are in % (*100), so variance is in (%^2).
        # Daily vol = sqrt(variance). Annualized vol = sqrt(variance) * sqrt(252)
        forecast_vol = np.sqrt(variance_5d) * np.sqrt(252)
        
        return {"value": round(forecast_vol, 2), "status": "CALCULATED", "method": "GARCH_5D_MEAN_VAR_ANNUALIZED"}
    except Exception: 
        return {"value": None, "status": "SYSTEM_ERROR", "reason": "GARCH fit failed"}

def calculate_evt_tail_risk(hist: pd.DataFrame) -> dict:
    try:
        log_returns = np.log(hist['Close'] / hist['Close'].shift(1)).dropna()
        losses = -log_returns[log_returns < 0]
        threshold = np.quantile(losses, Config.EVT_THRESHOLD_PERCENTILE)
        exceedances = losses[losses > threshold] - threshold
        n_total, n_exc = len(log_returns), len(exceedances)
        if n_exc < 10: return {"value": None, "status": "DATA_UNAVAILABLE", "reason": "Insufficient exceedances"}
        shape, loc, scale = genpareto.fit(exceedances, floc=0)
        p_var = 0.01
        if abs(shape) < 1e-6:
            var_99 = threshold + scale * np.log(n_exc / (n_total * p_var))
            es_99 = var_99 + scale
        else:
            var_99 = threshold + (scale / shape) * (((n_exc / (n_total * p_var))**shape) - 1)
            es_99 = var_99 + (scale + shape * (var_99 - threshold)) / (1 - shape)
        return {
            "method": "POT", "threshold_pct": Config.EVT_THRESHOLD_PERCENTILE * 100,
            "exceedances": n_exc, "shape_xi": round(shape, 4), "scale_beta": round(scale, 4),
            "var_99_daily_pct": round(var_99 * 100, 2), "es_99_daily_pct": round(es_99 * 100, 2),
            "status": "CALCULATED"
        }
    except Exception: 
        return {"value": None, "status": "SYSTEM_ERROR", "reason": "EVT failed"}
