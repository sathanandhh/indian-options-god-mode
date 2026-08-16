import pytest
import numpy as np
from scipy.stats import norm
from indian_options_god_mode.quant_engine import bs_delta, bs_gamma, bs_vanna, bs_charm, calculate_implied_vol

S, K, T, r, sigma, q = 24000, 24000, 7/365, 0.07, 0.12, 0.0

def test_delta_bounds():
    assert 0 <= bs_delta(S, K, T, r, sigma, 'call', q) <= 1
    assert -1 <= bs_delta(S, K, T, r, sigma, 'put', q) <= 0

def test_put_call_parity():
    assert abs((bs_delta(S, K, T, r, sigma, 'call', q) - bs_delta(S, K, T, r, sigma, 'put', q)) - 1.0) < 0.01

def test_gamma_positive():
    assert bs_gamma(S, K, T, r, sigma, q) > 0

def test_numerical_delta():
    """Verify Delta via finite difference."""
    eps = 0.01
    d1 = (np.log((S+eps) / K) + (r - q + sigma**2 / 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    p_up = (S+eps) * np.exp(-q * T) * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    
    d1 = (np.log((S-eps) / K) + (r - q + sigma**2 / 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    p_dn = (S-eps) * np.exp(-q * T) * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    
    num_delta = (p_up - p_dn) / (2 * eps)
    assert abs(bs_delta(S, K, T, r, sigma, 'call', q) - num_delta) < 0.001

def test_numerical_gamma():
    """Verify Gamma via finite difference."""
    eps = 1.0
    d1 = (np.log((S+eps) / K) + (r - q + sigma**2 / 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    p_up = (S+eps) * np.exp(-q * T) * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    
    d1 = (np.log(S / K) + (r - q + sigma**2 / 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    p_mid = S * np.exp(-q * T) * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    
    d1 = (np.log((S-eps) / K) + (r - q + sigma**2 / 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    p_dn = (S-eps) * np.exp(-q * T) * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    
    num_gamma = (p_up - 2*p_mid + p_dn) / (eps**2)
    assert abs(bs_gamma(S, K, T, r, sigma, q) - num_gamma) < 0.001

def test_iv_inversion_and_bounds():
    """Calculating IV from a BS price should return the original sigma."""
    d1 = (np.log(S / K) + (r - q + sigma**2 / 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    call_price = S * np.exp(-q * T) * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    
    calculated_iv = calculate_implied_vol(call_price, S, K, T, r, 'call', q)
    assert abs(calculated_iv - sigma) < 0.0001
    
    # Test arbitrage bound rejection
    assert np.isnan(calculate_implied_vol(0.01, S, K, T, r, 'call', q))
