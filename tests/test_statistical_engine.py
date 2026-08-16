import pytest
import numpy as np
import pandas as pd
from indian_options_god_mode.statistical_engine import calculate_garch_forecast, calculate_evt_tail_risk

def test_garch_annualization():
    """Verify GARCH output is roughly in expected annualized vol range."""
    np.random.seed(42)
    # Simulate 100 days of 1% daily vol
    rets = np.random.normal(0, 0.01, 100)
    idx = pd.date_range('2023-01-01', periods=100)
    hist = pd.DataFrame({'Close': np.cumprod(1+rets)*100}, index=idx)
    
    res = calculate_garch_forecast(hist)
    assert res['status'] == 'CALCULATED'
    # 1% daily * sqrt(252) ~ 15.8%
    assert 10.0 < res['value'] < 25.0

def test_evt_pot_calculation():
    """Verify EVT runs and returns shape parameter."""
    np.random.seed(42)
    # Student-t dist has fat tails
    rets = np.random.standard_t(3, 500) / 100
    idx = pd.date_range('2023-01-01', periods=500)
    hist = pd.DataFrame({'Close': np.cumprod(1+rets)*100}, index=idx)
    
    res = calculate_evt_tail_risk(hist)
    assert res['status'] == 'CALCULATED'
    assert res['shape_xi'] > 0  # Fat tails
