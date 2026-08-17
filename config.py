class Config:
    RISK_FREE_RATE = float(os.getenv("RISK_FREE_RATE", 0.07))
    DIVIDEND_YIELD = float(os.getenv("DIVIDEND_YIELD", 0.0))
    LOT_SIZE = int(os.getenv("LOT_SIZE", 25))
    MARKET_CLOSE_HOUR = 15
    MARKET_CLOSE_MINUTE = 30
    
    EVT_THRESHOLD_PERCENTILE = 0.95
    
    # Data Quality
    MIN_OI = 500
    MIN_BID = 0.05
    MAX_SPREAD_PCT = 0.50       # Reject options where bid-ask spread > 50% of mid
