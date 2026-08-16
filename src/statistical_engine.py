import numpy as np
import pandas as pd
from scipy.stats import genpareto
from arch import arch_model
import sys, os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config

def calculate_realized_volatility(hist: pd.DataFrame) -> dict:
    hist = hist.dropna()
    if len(hist) < 2: return {"error": "Insufficient historical data"}
    log_returns = np.log(hist['Close'] / hist['Close'].shift(1)).dropna()
    rv_30d_cc = np.std(log_returns.tail(30)) * np.sqrt(252) * 100  # 252 trading days convention
    return {"rv_30d_close_to_close": round(rv_30d_cc, 2)}

def calculate_garch_forecast(hist: pd.DataFrame) -> dict:
    try:
        log_returns = np.log(hist['Close'] / hist['Close'].shift(1)).dropna() * 100
        res = arch_model(log_returns, vol='Garch', p=1, q=1, rescale=False).fit(disp='off')
        variance_5d = res.forecast(horizon=5, reindex=False).variance.values[-1].mean()
        return {"garch_5d_forecast_vol": round(np.sqrt(variance_5d / 100 * 252) * 100, 2)}
    except Exception: return {"error": "GARCH fit failed"}

def calculate_evt_tail_risk(hist: pd.DataFrame) -> dict:
    try:
        log_returns = np.log(hist['Close'] / hist['Close'].shift(1)).dropna()
        losses = -log_returns[log_returns < 0]
        threshold = np.quantile(losses, Config.EVT_THRESHOLD_PERCENTILE)
        exceedances = losses[losses > threshold] - threshold
        n_total, n_exc = len(log_returns), len(exceedances)
        if n_exc < 10: return {"error": "Insufficient exceedances"}
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
            "var_99_daily_pct": round(var_99 * 100, 2), "es_99_daily_pct": round(es_99 * 100, 2)
        }
    except Exception: return {"error": "EVT failed"}
