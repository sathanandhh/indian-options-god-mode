# Indian Options God Mode MCP v5.1.0-rc1

Institutional-grade quantitative analytics engine for **NSE Indian Options**, providing volatility analytics, Greeks, IV surface analysis, model-based dealer positioning proxies, GARCH volatility forecasting and EVT tail-risk analysis.

The project is exposed through both:

* **MCP Server** — for MCP-compatible clients such as Claude Desktop
* **REST API** — for n8n, websites, automation workflows and other HTTP clients
* **Render Deployment** — live hosted API available without running the project locally

---

## Current Status

**Version:** `5.1.0-rc1`
**Status:** Release Candidate
**Deployment:** Live on Render
**Primary deployment URL:**

`https://indian-options-god-mode.onrender.com`

Health check:

`GET /`

API endpoint:

`POST /api/quant-map`

---

## What the System Does

The system converts live NSE option-chain data and historical market data into a structured quantitative market map.

### Volatility

* ATM Call IV
* ATM Put IV
* ATM IV
* 25-Delta Call IV
* 25-Delta Put IV
* 25-Delta Risk Reversal
* Realized Volatility
* IV-RV Spread
* GARCH volatility forecast
* SVI volatility surface
* SVI parameters
* Volatility residuals / mispricing signals
* Term structure
* Vertical arbitrage check

### Options Positioning

* Model GEX Proxy
* Call GEX
* Put GEX
* Gamma regime
* Model Gamma Flip
* Vanna exposure
* Charm exposure

### Tail Risk

* EVT / Peaks-over-Threshold
* Generalized Pareto Distribution
* Tail-shape parameter
* 99% VaR
* 99% Expected Shortfall
* Tail exceedance statistics

---

# Architecture

```text
                         MCP Client
                    Claude Desktop / Other
                              │
                              │ MCP
                              ▼
                ┌────────────────────────────┐
                │ Indian Options God Mode    │
                │       MCP Server           │
                └──────────────┬─────────────┘
                               │
                               │
                ┌──────────────┴─────────────┐
                │                            │
                ▼                            ▼
        NSE Option Chain                yfinance
        Spot / OI / Prices              Historical OHLC
                │                            │
                └──────────────┬─────────────┘
                               ▼
                    Data Quality Engine
                               │
                               ▼
                    Quantitative Engine
              ┌──────────────────────────────┐
              │ Black-Scholes                │
              │ Greeks                       │
              │ Implied Volatility            │
              │ GEX                          │
              │ Gamma Flip                   │
              │ Vanna / Charm                │
              └──────────────┬───────────────┘
                             │
                             ▼
                    Statistical Engine
              ┌──────────────────────────────┐
              │ Realized Volatility          │
              │ GARCH                        │
              │ EVT / POT                    │
              │ VaR / Expected Shortfall     │
              └──────────────┬───────────────┘
                             │
                             ▼
                    Volatility Engine
              ┌──────────────────────────────┐
              │ SVI Surface                  │
              │ Arbitrage Checks              │
              │ Term Structure               │
              │ IV Residuals                 │
              └──────────────┬───────────────┘
                             │
                             ▼
                    Quant Market Map
```

---

# Data Sources

## NSE

Primary source for live Indian index option data:

* Underlying spot
* Option expiries
* Strike prices
* Call / Put prices
* Bid / Ask
* Open Interest

The system validates the requested expiry against the expiry list returned by NSE.

## Yahoo Finance

Used for historical OHLC data required for:

* Realized volatility
* GARCH forecasting
* EVT tail-risk analysis

---

# Data Provenance

The system explicitly separates observed market information from model-derived information.

| Classification | Meaning                                           |
| -------------- | ------------------------------------------------- |
| `OBSERVED`     | Directly obtained from NSE or another data source |
| `DERIVED`      | Calculated mathematically from observed data      |
| `INFERRED`     | Model-based interpretation                        |
| `ASSUMED`      | Explicit modelling assumption                     |

### Important GEX Limitation

Actual dealer positioning is not observable from a public option chain.

Therefore:

```text
Model_GEX_Proxy ≠ Actual Dealer GEX
```

The current model assumes:

```text
Call inventory → Dealer short calls
Put inventory  → Dealer long puts
```

and labels the resulting positioning as a **Model GEX Proxy**.

The system does **not** claim to know the actual dealer book.

---

# Data Quality Controls

Before quantitative calculations, option contracts are filtered using configurable quality rules.

Current configuration includes:

```text
Minimum OI              = 500
Minimum Bid             = 0.05
Maximum Bid/Ask Spread  = 50%
Maximum 25D Delta Error = 0.05
```

The system records:

* Rows received
* Rows used
* Zero-OI rejections
* Zero-bid rejections
* Invalid-price rejections
* Wide-spread rejections
* Invalid-IV rejections

This information is returned through the `PROVENANCE` section of the Quant Market Map.

---

# Quantitative Models

## Black-Scholes

Used for:

* Delta
* Gamma
* Vanna
* Charm
* Implied Volatility

The system uses an exact time-to-expiry calculation based on:

```text
15:30 IST
ACT/365.25 calendar-second convention
```

---

## Implied Volatility

IV is calculated using a Brent root solver.

The implementation includes no-arbitrage price-bound validation before attempting inversion.

Invalid contracts return `NaN` and are excluded from downstream calculations.

---

## GEX

Gamma exposure is calculated using:

```text
GEX = Sign × Gamma × OI × Lot Size × Spot² × 0.01
```

Current model sign convention:

```text
Call = -1
Put  = +1
```

The result is explicitly classified as:

```text
INFERRED / MODEL PROXY
```

---

## Gamma Flip

The system scans approximately:

```text
Spot × 0.90 → Spot × 1.10
```

and uses a Brent root solver when a GEX sign change exists.

Output:

```text
Model_Gamma_Flip_Level
```

This represents the model's estimated transition between positive and negative gamma regimes.

---

# Volatility Surface Engine

The project includes an SVI-based volatility engine.

For a selected expiry it:

1. Fetches the option chain
2. Calculates market IV
3. Converts IV into total variance
4. Fits an SVI slice
5. Generates theoretical IV
6. Calculates market-vs-SVI residuals
7. Checks vertical arbitrage
8. Calculates 25D volatility metrics
9. Builds a term structure
10. Identifies potential IV mispricing signals

The primary MCP tool is:

```text
generate_volatility_surface_map
```

---

# Statistical Engine

## Realized Volatility

Current implementation calculates:

```text
30-day close-to-close realized volatility
```

using annualization based on:

```text
252 trading days
```

## GARCH

The system fits:

```text
GARCH(1,1)
```

and generates a:

```text
5-day forward volatility forecast
```

reported on an annualized basis.

## EVT

The system uses:

```text
Peaks Over Threshold
Generalized Pareto Distribution
```

to estimate:

* Tail shape
* Scale
* 99% VaR
* 99% Expected Shortfall

---

# Live Render Deployment

The application is currently deployed on Render.

### Production URL

```text
https://indian-options-god-mode.onrender.com
```

### Health Check

```http
GET /
```

Expected response:

```json
{
  "status": "online",
  "message": "Indian Options God Mode API is running."
}
```

### Live API

```http
POST /api/quant-map
```

Full endpoint:

```text
https://indian-options-god-mode.onrender.com/api/quant-map
```

---

# Calling the Live API

The API accepts:

```json
{
  "ticker": "NIFTY",
  "expiry": "27-Aug-2026"
}
```

Example using Python:

```python
import requests

url = "https://indian-options-god-mode.onrender.com/api/quant-map"

payload = {
    "ticker": "NIFTY",
    "expiry": "27-Aug-2026"
}

response = requests.post(url, json=payload, timeout=120)

print(response.status_code)
print(response.json())
```

Example using PowerShell:

```powershell
$body = @{
    ticker = "NIFTY"
    expiry = "27-Aug-2026"
} | ConvertTo-Json

Invoke-RestMethod `
    -Uri "https://indian-options-god-mode.onrender.com/api/quant-map" `
    -Method POST `
    -ContentType "application/json" `
    -Body $body
```

---

# Calling from n8n

The deployed REST API can be directly consumed by an n8n **HTTP Request** node.

### HTTP Request Node

```text
Method:
POST

URL:
https://indian-options-god-mode.onrender.com/api/quant-map

Send Body:
Yes

Body Content Type:
JSON
```

JSON body:

```json
{
  "ticker": "NIFTY",
  "expiry": "27-Aug-2026"
}
```

The response contains the complete Quant Market Map and can be passed into subsequent n8n nodes for:

* Formatting
* Telegram notifications
* Email
* Database storage
* Dashboards
* LLM interpretation
* Scheduled market monitoring
* Alert generation

Example workflow:

```text
n8n Schedule Trigger
        │
        ▼
Determine NSE Expiry
        │
        ▼
HTTP Request
        │
        │ POST /api/quant-map
        ▼
Indian Options God Mode
        │
        ▼
Quant Market Map JSON
        │
        ├───────────────┐
        ▼               ▼
   LLM Analysis     Store Data
        │
        ▼
Telegram / Email / Dashboard
```

---

# MCP Usage

The project also contains a native MCP server using FastMCP.

The MCP server exposes tools including:

```text
generate_quant_market_map
generate_volatility_surface_map
```

For local MCP usage, run:

```bash
python -m indian_options_god_mode.mcp_server
```

For Claude Desktop, configure:

```json
{
  "mcpServers": {
    "indian-options-god-mode": {
      "command": "C:\\path\\to\\project\\.venv\\Scripts\\python.exe",
      "args": [
        "-m",
        "indian_options_god_mode.mcp_server"
      ],
      "cwd": "C:\\path\\to\\project"
    }
  }
}
```

Restart Claude Desktop after changing the configuration.

You can then ask:

```text
Generate the Quant Market Map for NIFTY for the next valid NSE expiry.
```

or:

```text
Generate the SVI volatility surface for NIFTY for the specified expiry.
```

---

# Important: MCP vs Render REST API

The current architecture has two different access paths.

### Local MCP

```text
Claude Desktop
      │
      │ MCP
      ▼
mcp_server.py
      │
      ▼
Quantitative Engines
```

### Render / HTTP API

```text
n8n / Website / Python / HTTP Client
              │
              │ HTTPS POST
              ▼
https://indian-options-god-mode.onrender.com/api/quant-map
              │
              ▼
          web_app.py
              │
              ▼
    generate_quant_market_map()
```

The current Render deployment exposes the **FastAPI REST interface**.

It should therefore be treated as an HTTP quantitative analytics service rather than described as a remotely hosted MCP endpoint.

A future deployment can expose a proper remote MCP transport if required.

---

# Example Quant Market Map

The main API/MCP output follows this general structure:

```json
{
  "STATUS": "LIVE_CALCULATED",
  "MODEL_VERSION": "5.1.0-rc1",

  "MODEL_INPUTS": {
    "risk_free_rate": 0.07,
    "lot_size": 25,
    "time_convention": "ACT/365.25 calendar seconds",
    "timezone": "Asia/Kolkata"
  },

  "PROVENANCE": {
    "source": "NSE_DIRECT",
    "timestamp": "...",
    "rows_received": 0,
    "rows_used": 0,
    "rejection_reasons": {}
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
    "ATM_Call_IV": null,
    "ATM_Put_IV": null,
    "ATM_IV_Mid": null,
    "IV_25D_Call": null,
    "IV_25D_Put": null,
    "Risk_Reversal_25D": null,
    "RV_30D": null,
    "GARCH_5D_Annualized": null,
    "IV_RV_Spread": null
  },

  "POSITIONING_INFERENCE": {
    "Model_GEX_Proxy": null,
    "Call_GEX": null,
    "Put_GEX": null,
    "Total_Vanna": null,
    "Total_Charm_Daily": null,
    "Gamma_Regime": null,
    "Model_Gamma_Flip_Level": null
  },

  "TAIL_RISK": {}
}
```

Actual values are calculated dynamically from the market data available at request time.

---

# Error Handling

The system intentionally avoids fabricating missing market information.

Possible responses include:

```text
LIVE_CALCULATED
DATA_UNAVAILABLE
INVALID_EXPIRY
DATA_QUALITY_FAILURE
SYSTEM_ERROR
```

Examples:

```json
{
  "status": "DATA_UNAVAILABLE",
  "error": "NSE spot unavailable."
}
```

or:

```json
{
  "status": "INVALID_EXPIRY",
  "error": "Requested expiry is not available from NSE."
}
```

---

# Project Structure

```text
indian-options-god-mode/
│
├── .github/
│   └── workflows/
│       └── tests.yml
│
├── src/
│   ├── __init__.py
│   ├── data_fetcher.py
│   ├── quant_engine.py
│   ├── statistical_engine.py
│   └── indian_options_god_mode/
│       ├── __init__.py
│       ├── config.py
│       ├── data_fetcher.py
│       ├── quant_engine.py
│       ├── statistical_engine.py
│       ├── volatility_engine.py
│       ├── mcp_server.py
│       └── web_app.py
│
├── tests/
│   ├── __init__.py
│   ├── test_greeks.py
│   ├── test_quant_engine.py
│   └── test_statistical_engine.py
│
├── Codeflattener.py
├── restore_flattened.py
├── pyproject.toml
├── requirements.txt
├── render.yaml
└── README.md
```

> Note: The project currently contains both the newer package-based implementation under `src/indian_options_god_mode/` and older compatibility modules directly under `src/`. The package-based implementation is the current production-oriented implementation.

---

# Local Installation

```bash
git clone <your-repository>
cd indian-options-god-mode

python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Install:

```bash
pip install -e .
```

Run tests:

```bash
pytest tests/
```

---

# Local REST API

Run the FastAPI application locally:

```bash
uvicorn src.indian_options_god_mode.web_app:app --host 0.0.0.0 --port 8000
```

Then:

```text
http://localhost:8000
```

API:

```text
POST http://localhost:8000/api/quant-map
```

---

# Render Deployment

The project includes:

```text
render.yaml
```

Current deployment configuration:

```yaml
services:
  - type: web
    name: indian-options-god-mode
    env: python
    region: singapore
    plan: free
    buildCommand: pip install -e .
    startCommand: uvicorn src.indian_options_god_mode.web_app:app --host 0.0.0.0 --port $PORT
    healthCheckPath: /
```

Render provides the runtime `$PORT`, which is passed to Uvicorn.

The service is therefore externally accessible through the Render HTTPS URL.

---

# CI Testing

GitHub Actions runs the test suite on pushes and pull requests against:

```text
main
master
```

Current CI environment:

```text
Ubuntu
Python 3.11
pytest
```

---

# Current Capabilities

```text
[✓] Live NSE option-chain ingestion
[✓] NSE expiry validation
[✓] Spot retrieval
[✓] Option liquidity filtering
[✓] Bid/ask quality checks
[✓] Black-Scholes Greeks
[✓] Implied Volatility
[✓] 25D volatility metrics
[✓] IV-RV spread
[✓] Model GEX
[✓] Gamma regime
[✓] Model Gamma Flip
[✓] Vanna
[✓] Charm
[✓] Realized Volatility
[✓] GARCH forecast
[✓] EVT / POT tail risk
[✓] VaR / Expected Shortfall
[✓] SVI volatility surface
[✓] Term structure
[✓] IV residual / mispricing signals
[✓] Arbitrage checks
[✓] Data provenance
[✓] REST API
[✓] Render deployment
[✓] n8n-compatible HTTP interface
[✓] MCP server
[✓] Automated tests
[✓] GitHub Actions CI
```

---

# Future Scope

Potential extensions include:

### Market Data

* Bank NIFTY / FINNIFTY / MIDCPNIFTY expansion
* Individual NSE equity options
* Futures basis
* Volume and trade-flow analytics
* Historical option-chain database
* Intraday option-chain snapshots

### Volatility

* Full SVI term-structure surface
* Surface calibration across expiries
* Calendar arbitrage checks
* Butterfly arbitrage checks
* Volatility-of-volatility analysis
* Forward volatility
* Skew dynamics
* Volatility risk premium monitoring

### Positioning

* Strike-by-strike GEX map
* Dealer positioning scenarios
* GEX concentration zones
* Vanna / Charm scenario analysis
* Spot-vs-GEX regime map
* Expiry-specific positioning evolution

### Risk

* Stress testing
* Scenario analysis
* Monte Carlo simulation
* Expected shortfall scenarios
* Crash-risk monitoring
* Volatility shock analysis

### Macro Integration

Future versions can incorporate:

* RBI policy data
* Federal Reserve data
* Interest-rate curves
* India VIX
* USD/INR
* Bond yields
* Commodity markets
* Global equity indices
* Crypto volatility

This would allow the Quant Market Map to evolve from an **options-only analytics engine** into a broader cross-asset risk and volatility intelligence system.

---

# Design Philosophy

The project is deliberately built around four principles:

### 1. No Fabricated Market Data

If the required data cannot be retrieved, the system returns an explicit unavailable/error state.

### 2. Observable vs Modelled

Market observations and model assumptions are kept separate.

### 3. Quantitative Transparency

Important model assumptions, input parameters and data-quality decisions are returned with the result.

### 4. Automation Ready

The same quantitative engine can be accessed through:

```text
MCP
REST API
n8n
Python
Web applications
Automated workflows
```

---

# Production Endpoint

**Live deployment:**

```text
https://indian-options-god-mode.onrender.com
```

**Health check:**

```text
GET /
```

**Quant Market Map:**

```text
POST /api/quant-map
```

**Full API endpoint:**

```text
https://indian-options-god-mode.onrender.com/api/quant-map
```

Example request:

```json
{
  "ticker": "NIFTY",
  "expiry": "27-Aug-2026"
}
```

---

## Version

```text
Indian Options God Mode
Version: 5.1.0-rc1
Deployment: Render
Status: Release Candidate
```
