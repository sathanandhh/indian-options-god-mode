##

import numpy as np
from scipy.optimize import minimize
from .quant_engine import calculate_implied_vol, d1, bs_price
from .data_fetcher import fetch_option_chain_df, get_spot, get_expirations

def svi_total_variance(k, a, b, rho, m, sigma):
    """SVI Parametrization for total variance (w = sigma^2 * T)."""
    return a + b * (rho * (k - m) + np.sqrt((k - m)**2 + sigma**2))

def fit_svi_slice(K_array, iv_array, F, T):
    """
    Fits SVI parameters to a single expiry slice.
    k = log-moneyness (ln(K/F))
    w = total variance (iv^2 * T)
    """
    k = np.log(K_array / F)
    w = (iv_array**2) * T
    
    # Initial guesses
    a0 = np.min(w) - 0.01
    b0 = 0.1
    rho0 = -0.2
    m0 = 0.0
    sig0 = 0.1
    
    def objective(params):
        a, b, rho, m, sigma = params
        w_model = svi_total_variance(k, a, b, rho, m, sigma)
        return np.sum((w - w_model)**2)
        
    # SVI Arbitrage Constraints (b>=0, |rho|<1, sigma>0, a + b*sig*sqrt(1-rho^2) >= 0)
    cons = (
        {'type': 'ineq', 'fun': lambda x: x[1] - 1e-5},
        {'type': 'ineq', 'fun': lambda x: 1 - abs(x[2]) - 1e-5},
        {'type': 'ineq', 'fun': lambda x: x[4] - 1e-5},
        {'type': 'ineq', 'fun': lambda x: (x[0] + x[1] * x[4] * np.sqrt(1 - x[2]**2))}
    )
    bounds = [(-1.0, 1.0), (1e-5, 2.0), (-0.999, 0.999), (-1.0, 1.0), (1e-5, 2.0)]
    
    res = minimize(objective, [a0, b0, rho0, m0, sig0], method='SLSQP', bounds=bounds, constraints=cons)
    
    a, b, rho, m, sigma = res.x
    w_fit = svi_total_variance(k, a, b, rho, m, sigma)
    iv_fit = np.sqrt(w_fit / T)
    return iv_fit, {'a': a, 'b': b, 'rho': rho, 'm': m, 'sigma': sigma}

def check_vertical_arbitrage(df):
    """Ensures call prices decrease monotonically as strike increases."""
    violations = 0
    calls = df[df['option_type'] == 'call'].sort_values('strike')
    for i in range(1, len(calls)):
        if calls.iloc[i]['mid_price'] > calls.iloc[i-1]['mid_price']:
            violations += 1
    return violations == 0

def generate_volatility_report(ticker: str, expiry: str) -> dict:
    """
    Natenburg-style Volatility Surface Analyzer.
    """
    spot = get_spot(ticker)
    if spot is None: return {"status": "DATA_UNAVAILABLE", "error": "NSE spot unavailable."}
        
    df = fetch_option_chain_df(ticker, expiry)
    if df.empty: return {"status": "DATA_UNAVAILABLE", "error": "NSE option chain empty."}
    
    r, q = 0.07, 0.0
    # Exact Time to expiry using the quant engine
    from .quant_engine import get_exact_time_to_expiry
    try: T = get_exact_time_to_expiry(expiry)
    except ValueError: return {"status": "INVALID_EXPIRY", "error": "Bad expiry format."}
        
    # 1. Clean prices and calculate IVs
    df['mid_price'] = (df['bid'] + df['ask']) / 2
    df = df[(df['bid'] > 0) & (df['openInterest'] > 0) & (df['mid_price'] > 0)]
    
    # Arbitrage Check
    arb_status = "PASS" if check_vertical_arbitrage(df) else "FAIL"
    
    # Calculate IVs
    df['market_iv'] = df.apply(lambda row: calculate_implied_vol(
        row['mid_price'], spot, row['strike'], T, r, row['option_type'], q
    ), axis=1)
    df = df.dropna(subset=['market_iv'])
    
    # 2. Fit SVI Surface (per expiry slice)
    # We fit calls and puts together in total variance space
    K_array = df['strike'].values
    iv_array = df['market_iv'].values
    F = spot * np.exp((r-q)*T) # Forward price
    
    iv_fit, svi_params = fit_svi_slice(K_array, iv_array, F, T)
    df['theoretical_iv'] = iv_fit
    df['residual_iv'] = df['market_iv'] - df['theoretical_iv']
    
    # 3. Surface Metrics (Smile/Skew)
    atm_idx = (df['strike'] - spot).abs().idxmin()
    atm_iv = df.loc[atm_idx, 'market_iv'] * 100
    
    # Find 25-Delta proxies (closest strike)
    def find_delta_iv(opt_type, target_delta):
        sub = df[df['option_type'] == opt_type].copy()
        sub['delta'] = sub.apply(lambda row: bs_delta(spot, row['strike'], T, r, row['market_iv'], opt_type, q), axis=1)
        sub['delta_diff'] = abs(abs(sub['delta']) - target_delta)
        idx = sub['delta_diff'].idxmin()
        return sub.loc[idx, 'market_iv'] * 100
        
    iv_25c = find_delta_iv('call', 0.25)
    iv_25p = find_delta_iv('put', 0.25)
    
    # 4. Term Structure (Requires fetching other expiries)
    all_expiries = get_expirations(ticker)
    term_structure = []
    for exp in all_expiries[:4]: # Check next 4 expiries
        if exp == expiry: continue
        try:
            exp_T = get_exact_time_to_expiry(exp)
            exp_df = fetch_option_chain_df(ticker, exp)
            exp_df['mid_price'] = (exp_df['bid'] + exp_df['ask']) / 2
            exp_df = exp_df[(exp_df['bid'] > 0) & (exp_df['mid_price'] > 0)]
            exp_df['market_iv'] = exp_df.apply(lambda row: calculate_implied_vol(
                row['mid_price'], spot, row['strike'], exp_T, r, row['option_type'], q
            ), axis=1)
            exp_atm_idx = (exp_df['strike'] - spot).abs().idxmin()
            exp_atm_iv = exp_df.loc[exp_atm_idx, 'market_iv'] * 100
            days = int(exp_T * 365)
            term_structure.append({"expiry": exp, "days": days, "atm_iv": round(exp_atm_iv, 2)})
        except: pass
            
    # 5. Mispricing Detection
    # Flag residuals > 1.0 vol points (100 bps)
    mispriced = df[df['residual_iv'].abs() > 0.01]
    mispricing_signals = []
    for _, row in mispriced.iterrows():
        mispricing_signals.append({
            "strike": row['strike'],
            "type": row['option_type'].upper(),
            "market_iv": round(row['market_iv'] * 100, 2),
            "svi_iv": round(row['theoretical_iv'] * 100, 2),
            "residual": round(row['residual_iv'] * 100, 2)
        })
        
    return {
        "STATUS": "LIVE_CALCULATED",
        "VOLATILITY_STRUCTURE": {
            "ATM_IV": round(atm_iv, 2),
            "IV_25D_Call": round(iv_25c, 2),
            "IV_25D_Put": round(iv_25p, 2),
            "Risk_Reversal_25D": round(iv_25c - iv_25p, 2),
            "SVI_Params": {k: round(v, 4) for k, v in svi_params.items()}
        },
        "TERM_STRUCTURE": term_structure,
        "ARBITRAGE_CHECK": arb_status,
        "MISPRICING_SIGNALS": mispricing_signals[:5] # Top 5 deviations
    }
