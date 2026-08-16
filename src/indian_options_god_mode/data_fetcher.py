import pandas as pd
import yfinance as yf
from nsepython import nse_optionchain_scraper

def _format_ticker(symbol: str) -> str:
    s = symbol.replace("^", "").replace(".NS", "")
    if s == "NSEI": return "NIFTY"
    if s == "NSEBANK": return "BANKNIFTY"
    return s

def get_expirations(symbol: str) -> list[str]:
    try: return nse_optionchain_scraper(_format_ticker(symbol))['records']['expiryDates']
    except Exception: return []

def get_spot(symbol: str) -> float | None:
    try: return float(nse_optionchain_scraper(_format_ticker(symbol))['records']['underlyingValue'])
    except Exception: return None

def fetch_option_chain_df(symbol: str, expiry: str) -> pd.DataFrame:
    payload = nse_optionchain_scraper(_format_ticker(symbol))
    records = payload['records']['data']
    filtered = [r for r in records if r['expiryDate'] == expiry]
    
    rows = []
    for r in filtered:
        if 'CE' in r:
            rows.append({'strike': r['strike'], 'option_type': 'call', 'bid': r['CE'].get('bidPrice', 0), 
                         'ask': r['CE'].get('askPrice', 0), 'lastPrice': r['CE'].get('lastPrice', 0), 
                         'openInterest': r['CE'].get('openInterest', 0)})
        if 'PE' in r:
            rows.append({'strike': r['strike'], 'option_type': 'put', 'bid': r['PE'].get('bidPrice', 0), 
                         'ask': r['PE'].get('askPrice', 0), 'lastPrice': r['PE'].get('lastPrice', 0), 
                         'openInterest': r['PE'].get('openInterest', 0)})
    return pd.DataFrame(rows)

def fetch_ohlc_data(symbol: str, period="1y") -> pd.DataFrame:
    yf_symbol = "^NSEI" if symbol.upper() == "NIFTY" else "^NSEBANK"
    return yf.Ticker(yf_symbol).history(period=period)
