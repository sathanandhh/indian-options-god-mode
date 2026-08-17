# src/indian_options_god_mode/data_fetcher.py
import requests
import pandas as pd
import yfinance as yf

NSE_BASE_URL = "https://www.nseindia.com"
NSE_CHAIN_URL = "https://www.nseindia.com/api/option-chain-indices?symbol={}"

# Create a global session to maintain cookies and bypass Cloudflare
session = requests.Session()
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
session.headers.update(headers)

def _format_ticker(symbol: str) -> str:
    s = symbol.replace("^", "").replace(".NS", "")
    if s == "NSEI": return "NIFTY"
    if s == "NSEBANK": return "BANKNIFTY"
    return s

def _fetch_raw_chain(symbol: str) -> dict:
    ticker = _format_ticker(symbol)
    url = NSE_CHAIN_URL.format(ticker)
    
    # Hit homepage first to get required cookies
    try:
        session.get(NSE_BASE_URL, timeout=5)
    except Exception:
        pass
        
    response = session.get(url, timeout=10)
    response.raise_for_status()
    return response.json()

def get_expirations(symbol: str) -> list[str]:
    try:
        data = _fetch_raw_chain(symbol)
        return data['records']['expiryDates']
    except Exception:
        return []

def get_spot(symbol: str) -> float | None:
    try:
        data = _fetch_raw_chain(symbol)
        return float(data['records']['underlyingValue'])
    except Exception:
        return None

def fetch_option_chain_df(symbol: str, expiry: str) -> pd.DataFrame:
    try:
        data = _fetch_raw_chain(symbol)
        records = data['records']['data']
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
    except Exception:
        return pd.DataFrame()

def fetch_ohlc_data(symbol: str, period="1y") -> pd.DataFrame:
    yf_symbol = "^NSEI" if symbol.upper() == "NIFTY" else "^NSEBANK"
    return yf.Ticker(yf_symbol).history(period=period)