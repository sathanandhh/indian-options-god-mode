import math
import numpy as np
from datetime import datetime, time, date
from zoneinfo import ZoneInfo
from scipy.stats import norm
from scipy.optimize import brentq
import sys, os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config

IST = ZoneInfo("Asia/Kolkata")

def get_exact_time_to_expiry(expiry_date_str: str) -> float:
    """Calculates exact time to expiry in years based on seconds remaining to 15:30 IST."""
    try:
        try: exp_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()
        except ValueError: exp_date = datetime.strptime(expiry_date_str, '%d-%b-%Y').date()
    except ValueError:
        return 1 / 365.0 
        
    expiry_dt = datetime.combine(exp_date, time(Config.MARKET_CLOSE_HOUR, Config.MARKET_CLOSE_MINUTE), tzinfo=IST)
    now = datetime.now(IST)
    
    if expiry_dt <= now: return 0.0
        
    seconds_remaining = (expiry_dt - now).total_seconds()
    seconds_in_year = 365.25 * 24 * 3600  # ACT/365.25 calendar convention
    return seconds_remaining / seconds_in_year

def d1(S, K, T, r, sigma, q=0.0):
    if T <= 0 or sigma <= 0: return 0
    return (np.log(S / K) + (r - q + sigma**2 / 2) * T) / (sigma * np.sqrt(T))

def bs_delta(S, K, T, r, sigma, option_type='call', q=0.0):
    if T <= 0 or sigma <= 0: return 0.0
    d1_val = d1(S, K, T, r, sigma, q)
    return np.exp(-q * T) * (norm.cdf(d1_val) if option_type == 'call' else -norm.cdf(-d1_val))

def bs_gamma(S, K, T, r, sigma, q=0.0):
    if T <= 0 or sigma <= 0: return 0
    return np.exp(-q * T) * norm.pdf(d1(S, K, T, r, sigma, q)) / (S * sigma * np.sqrt(T))

def bs_vanna(S, K, T, r, sigma, q=0.0):
    """dDelta/dVol. Unit: Delta per 1.00 (100%) change in vol."""
    if T <= 0 or sigma <= 0: return 0
    d2_val = d1(S, K, T, r, sigma, q) - sigma * np.sqrt(T)
    return -np.exp(-q * T) * norm.pdf(d2_val) / sigma

def bs_charm(S, K, T, r, sigma, option_type='call', q=0.0):
    """dDelta/dTime. Unit: Delta decay per calendar day."""
    if T <= 0 or sigma <= 0: return 0
    d1_val = d1(S, K, T, r, sigma, q)
    d2_val = d1_val - sigma * np.sqrt(T)
    charm = -np.exp(-q * T) * norm.pdf(d1_val) * (2*(r-q)*T - d2_val * sigma * np.sqrt(T)) / (2 * T * sigma * np.sqrt(T))
    return (charm if option_type == 'call' else -charm) / 365

def calculate_implied_vol(market_price, S, K, T, r, option_type='call', q=0.0):
    if market_price <= 0 or T <= 0: return np.nan
    def objective(sigma): 
        d1_val = d1(S, K, T, r, sigma, q)
        d2_val = d1_val - sigma * np.sqrt(T)
        if option_type == 'call':
            p = S * np.exp(-q * T) * norm.cdf(d1_val) - K * np.exp(-r * T) * norm.cdf(d2_val)
        else:
            p = K * np.exp(-r * T) * norm.cdf(-d2_val) - S * np.exp(-q * T) * norm.cdf(-d1_val)
        return p - market_price
    try: return brentq(objective, 0.001, 5.0)
    except ValueError: return np.nan

def calculate_gex_at_spot(S_hyp, options_list, T, r, q, lot_size):
    """Helper function to calculate Total GEX at a hypothetical spot price."""
    total_gex = 0
    for opt in options_list:
        gamma = bs_gamma(S_hyp, opt['K'], T, r, opt['iv'], q)
        # Sign convention: -1 for calls, +1 for puts
        gex = opt['sign'] * gamma * opt['oi'] * lot_size * (S_hyp**2) * 0.01
        total_gex += gex
    return total_gex
