import pytest
import sys
import os

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.quant_engine import (bs_delta, bs_gamma, bs_vanna, bs_charm, calculate_implied_vol, 
                              calculate_gex_at_spot, get_exact_time_to_expiry)
from datetime import datetime, timedelta

# Standard test parameters
S = 24000
K = 24000
T = 7 / 365
r = 0.07
sigma = 0.12
q = 0.0

def test_delta_bounds():
    """Delta should be between 0 and 1 for calls, -1 and 0 for puts."""
    call_delta = bs_delta(S, K, T, r, sigma, 'call', q)
    put_delta = bs_delta(S, K, T, r, sigma, 'put', q)
    assert 0 <= call_delta <= 1
    assert -1 <= put_delta <= 0

def test_put_call_parity():
    """Call Delta - Put Delta should equal e^(-qT) (approx 1 for q=0)."""
    call_delta = bs_delta(S, K, T, r, sigma, 'call', q)
    put_delta = bs_delta(S, K, T, r, sigma, 'put', q)
    assert abs((call_delta - put_delta) - 1.0) < 0.01

def test_gamma_positive():
    """Gamma must always be positive."""
    gamma = bs_gamma(S, K, T, r, sigma, q)
    assert gamma > 0

def test_iv_inversion():
    """Calculating IV from a BS price should return the original sigma."""
    from scipy.stats import norm
    import numpy as np
    d1_val = (np.log(S / K) + (r - q + sigma**2 / 2) * T) / (sigma * np.sqrt(T))
    d2_val = d1_val - sigma * np.sqrt(T)
    call_price = S * np.exp(-q * T) * norm.cdf(d1_val) - K * np.exp(-r * T) * norm.cdf(d2_val)
    
    calculated_iv = calculate_implied_vol(call_price, S, K, T, r, 'call', q)
    assert abs(calculated_iv - sigma) < 0.0001

def test_gex_conservation():
    """Total GEX must equal Call GEX + Put GEX."""
    options_list = [
        {'K': 23000, 'oi': 1000, 'iv': 0.15, 'type': 'put'},
        {'K': 24000, 'oi': 1500, 'iv': 0.12, 'type': 'call'},
        {'K': 25000, 'oi': 800, 'iv': 0.14, 'type': 'call'}
    ]
    lot_size = 25
    total_gex = calculate_gex_at_spot(S, options_list, T, r, q, lot_size)
    
    # Since calculate_gex_at_spot sums internally, we validate the logic:
    # Call GEX is negative, Put GEX is positive.
    call_opts = [o for o in options_list if o['type'] == 'call']
    put_opts = [o for o in options_list if o['type'] == 'put']
    
    call_gex = calculate_gex_at_spot(S, call_opts, T, r, q, lot_size)
    put_gex = calculate_gex_at_spot(S, put_opts, T, r, q, lot_size)
    
    assert abs(total_gex - (call_gex + put_gex)) < 1e-6
    assert call_gex < 0  # Dealers short calls
    assert put_gex > 0   # Dealers short puts

def test_time_to_expiry_zero():
    """Time to expiry should be 0 for past dates."""
    past_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    T = get_exact_time_to_expiry(past_date)
    assert T == 0.0
