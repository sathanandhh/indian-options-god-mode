import sys, os
import numpy as np
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
from scipy.optimize import brentq
from mcp.server.fastmcp import FastMCP

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quant_engine import (d1, bs_delta, bs_gamma, bs_vanna, bs_charm, 
                          calculate_implied_vol, get_exact_time_to_expiry, calculate_gex_at_spot)
from data_fetcher import get_expirations, get_spot, fetch_option_chain_df, fetch_ohlc_data
from statistical_engine import calculate_realized_volatility, calculate_garch_forecast, calculate_evt_tail_risk
from config import Config

IST = ZoneInfo("Asia/Kolkata")
mcp = FastMCP("IndianOptionsGodModeV5_1_RC")

@mcp.tool()
def generate_quant_market_map(ticker: str, expiry: str) -> dict:
    """
    MASTER ORCHESTRATOR: Institutional-grade Quant Market Map.
    """
    try:
        spot = get_spot(ticker)
        if spot is None: 
            return {"status": "DATA_UNAVAILABLE", "error": f"NSE API failed to return spot for {ticker}."}
            
        df_raw = fetch_option_chain_df(ticker, expiry)
        if df_raw.empty:
            return {"status": "DATA_UNAVAILABLE", "error": f"NSE API returned empty option chain."}
            
        rows_received = len(df_raw)
        timestamp = datetime.now(IST).isoformat()
        
        # 1. Data Quality Engine
        df_raw['mid_price'] = (df_raw['bid'] + df_raw['ask']) / 2
        df_raw['mid_price'] = df_raw['mid_price'].fillna(df_raw['lastPrice'])
        df_raw['spread_pct'] = (df_raw['ask'] - df_raw['bid']) / df_raw['mid_price']
        
        rejection_reasons = {"zero_oi": 0, "zero_bid": 0, "invalid_price": 0, "wide_spread": 0, "invalid_iv": 0}
        
        df = df_raw.copy()
        rejection_reasons["zero_oi"] = len(df[df['openInterest'] <= Config.MIN_OI])
        df = df[df['openInterest'] > Config.MIN_OI]
        
        rejection_reasons["zero_bid"] = len(df[df['bid'] < Config.MIN_BID])
        df = df[df['bid'] >= Config.MIN_BID]
        
        rejection_reasons["invalid_price"] = len(df[df['mid_price'] <= 0])
        df = df[df['mid_price'] > 0]
        
        rejection_reasons["wide_spread"] = len(df[df['spread_pct'] > Config.MAX_SPREAD_PCT])
        df = df[df['spread_pct'] <= Config.MAX_SPREAD_PCT]
        
        rows_used = len(df)
        if rows_used < 10: return {"status": "DATA_QUALITY_FAILURE", "error": "Insufficient liquid contracts."}
            
        # 2. Time & Models
        T = get_exact_time_to_expiry(expiry)
        r, q = Config.RISK_FREE_RATE, Config.DIVIDEND_YIELD
        
        hist_df = fetch_ohlc_data(ticker, "1y")
        rv_stats = calculate_realized_volatility(hist_df)
        garch_stats = calculate_garch_forecast(hist_df)
        evt_stats = calculate_evt_tail_risk(hist_df)
        
        # 3. Options Processing
        total_call_gex, total_put_gex = 0, 0
        total_vanna, total_charm = 0, 0
        valid_options_list = []
        
        atm_call_iv, atm_put_iv = 0.0, 0.0
        iv_25d_call, iv_25d_put = 0.0, 0.0
        min_diff_atm, min_diff_25c, min_diff_25p = float('inf'), float('inf'), float('inf')
        
        for _, row in df.iterrows():
            K, oi, opt_type = row['strike'], row['openInterest'], row['option_type']
            iv = calculate_implied_vol(row['mid_price'], spot, K, T, r, opt_type, q)
            if np.isnan(iv): 
                rejection_reasons["invalid_iv"] += 1
                continue
                
            gamma = bs_gamma(spot, K, T, r, iv, q)
            
            # Explicit Sign Mapping: Dealer short calls (-1), long puts (+1)
            sign = -1 if opt_type == 'call' else 1
            gex = sign * gamma * oi * Config.LOT_SIZE * (spot**2) * 0.01
            
            if opt_type == 'call': total_call_gex += gex
            else: total_put_gex += gex
            
            # Higher Order Greeks Exposure
            total_vanna += bs_vanna(spot, K, T, r, iv, q) * oi * Config.LOT_SIZE * sign
            total_charm += bs_charm(spot, K, T, r, iv, opt_type, q) * oi * Config.LOT_SIZE * sign
            
            valid_options_list.append({'K': K, 'oi': oi, 'iv': iv, 'type': opt_type, 'sign': sign})
            
            # IV Surface
            if opt_type == 'call':
                diff = abs(spot - K)
                if diff < min_diff_atm: atm_call_iv = iv * 100; min_diff_atm = diff
                diff_d = abs(bs_delta(spot, K, T, r, iv, 'call', q) - 0.25)
                if diff_d < min_diff_25c: iv_25d_call = iv * 100; min_diff_25c = diff_d
            else:
                diff = abs(spot - K)
                if diff < min_diff_atm: atm_put_iv = iv * 100; min_diff_atm = diff
                diff_d = abs(bs_delta(spot, K, T, r, iv, 'put', q) + 0.25)
                if diff_d < min_diff_25p: iv_25d_put = iv * 100; min_diff_25p = diff_d

        atm_iv_mid = (atm_call_iv + atm_put_iv) / 2
        
        # 4. Model Gamma Flip
        gamma_flip = None
        try:
            lower_bound, upper_bound = spot * 0.90, spot * 1.10
            gex_low = calculate_gex_at_spot(lower_bound, valid_options_list, T, r, q, Config.LOT_SIZE)
            gex_high = calculate_gex_at_spot(upper_bound, valid_options_list, T, r, q, Config.LOT_SIZE)
            if gex_low * gex_high < 0:
                gamma_flip = brentq(calculate_gex_at_spot, lower_bound, upper_bound, 
                                    args=(valid_options_list, T, r, q, Config.LOT_SIZE))
        except Exception: pass

        # 5. Map Construction
        rv_30d = rv_stats.get("rv_30d_close_to_close", 0)
        iv_rv_spread = atm_iv_mid - rv_30d
        
        quant_map = {
            "STATUS": "LIVE_CALCULATED",
            "MODEL_VERSION": "5.1.0",
            "MODEL_INPUTS": {
                "risk_free_rate": r,
                "risk_free_rate_source": "CONFIG_STATIC",
                "lot_size": Config.LOT_SIZE,
                "lot_size_source": "CONFIG_STATIC",
                "time_convention": "ACT/365.25 calendar seconds",
                "timezone": "Asia/Kolkata"
            },
            "PROVENANCE": {
                "source": "NSE_DIRECT",
                "timestamp": timestamp,
                "rows_received": rows_received,
                "rows_used": rows_used,
                "rejection_reasons": rejection_reasons
            },
            "DATA_CLASSIFICATION": {
                "Spot": "OBSERVED",
                "OI": "OBSERVED",
                "IV": "DERIVED",
                "GEX": "INFERRED",
                "Dealer_Position": "ASSUMED",
                "Gamma_Flip": "MODEL_DERIVED"
            },
            "VOLATILITY_STATE": {
                "ATM_Call_IV": round(atm_call_iv, 2),
                "ATM_Put_IV": round(atm_put_iv, 2),
                "ATM_IV_Mid": round(atm_iv_mid, 2),
                "IV_25D_Call": round(iv_25d_call, 2),
                "IV_25D_Put": round(iv_25d_put, 2),
                "Risk_Reversal_25D": round(iv_25d_call - iv_25d_put, 2),
                "RV_30D": rv_30d,
                "GARCH_5D": garch_stats.get("garch_5d_forecast_vol", 0),
                "IV_RV_Spread": round(iv_rv_spread, 2)
            },
            "POSITIONING_INFERENCE": {
                "Total_Proxy_GEX": round(total_call_gex + total_put_gex, 2),
                "Call_GEX": round(total_call_gex, 2),
                "Put_GEX": round(total_put_gex, 2),
                "Total_Vanna": round(total_vanna, 2),
                "Total_Charm_Daily": round(total_charm, 4),
                "Gamma_Regime": "Short Gamma (Trend)" if (total_call_gex + total_put_gex) < 0 else "Long Gamma (Mean Revert)",
                "Model_Gamma_Flip_Level": round(gamma_flip, 2) if gamma_flip else "NOT_CALCULATED",
                "gamma_flip_method": "BS_gamma_static_IV_spot_scan",
                "positioning_assumption": {
                    "call_sign": -1,
                    "put_sign": +1,
                    "interpretation": "Dealer short calls / long puts",
                    "observed_dealer_positioning": False
                }
            },
            "TAIL_RISK": evt_stats
        }
        return quant_map
        
    except Exception as e:
        return {"status": "SYSTEM_ERROR", "error": str(e)}

if __name__ == "__main__":
    mcp.run()
