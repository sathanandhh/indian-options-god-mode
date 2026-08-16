## Indian Options God Mode MCP v5.1.0-rc1

A professional-grade Model Context Protocol (MCP) server for Indian Options (NSE) valuation. This system acts as a quantitative research assistant, providing volatility analysis, tail risk metrics, and dealer positioning proxies.

### Core Principles
- **No Hallucinations:** If NSE data is unavailable, the system returns `null` with a `DATA_UNAVAILABLE` status. It never substitutes missing quantitative values with `0`.
- **Provenance & Classification:** Every output tracks rows received, rejected, and explicitly classifies data as `OBSERVED`, `DERIVED`, `INFERRED`, or `ASSUMED`.
- **Asumption Transparency:** Dealer GEX is labeled as `Model_GEX_Proxy` because actual dealer books are unavailable.

### What this system does NOT know
- Dealer inventory
- Customer/dealer identity
- Actual dealer delta/gamma
- OTC or structured positions

Therefore, GEX is an inferred positioning proxy under a hypothetical inventory assumption, not observed dealer exposure.

### Setup
```bash
pip install -e .
pytest tests/
python -m indian_options_god_mode.mcp_server
```
