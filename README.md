````markdown
# Indian Options God Mode MCP v5.1.0-rc1

Institutional-grade quantitative MCP server for **NSE Indian Options**, providing volatility analysis, Greeks, tail-risk metrics, IV surface analysis and model-based dealer positioning proxies.

## Core Principles

- **No hallucinated data** — unavailable NSE data returns `null` / `DATA_UNAVAILABLE`.
- **Data provenance** — outputs distinguish `OBSERVED`, `DERIVED`, `INFERRED` and `ASSUMED` values.
- **Model transparency** — GEX is explicitly a `Model_GEX_Proxy`; actual dealer books are not observable.
- **Strict validation** — NSE expiry validation, liquidity filters and IV arbitrage-bound checks.

## Quantitative Pipeline

```text
                 ┌─────────────────────┐
                 │    Claude Desktop   │
                 │    MCP Client       │
                 └──────────┬──────────┘
                            │ MCP
                            ▼
              ┌──────────────────────────┐
              │ Indian Options God Mode  │
              │       MCP Server         │
              └────────────┬─────────────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
     NSE Option Chain   yfinance       Configuration
     Spot / OI / IV     Historical      R / Lot Size
          │             OHLC
          └──────────────┬─────────────────┘
                         ▼
              ┌─────────────────────┐
              │   Data Quality       │
              │   & Validation       │
              └──────────┬──────────┘
                         ▼
        ┌────────────────────────────────┐
        │       Quant Engine              │
        │ BS Greeks • IV • GEX • Gamma    │
        │ Flip • Vanna • Charm             │
        └───────────────┬────────────────┘
                        ▼
        ┌────────────────────────────────┐
        │ Statistical Engine              │
        │ RV • GARCH • EVT / POT          │
        └───────────────┬────────────────┘
                        ▼
              ┌─────────────────────┐
              │  Quant Market Map   │
              │ Volatility          │
              │ Positioning         │
              │ Tail Risk           │
              │ Provenance          │
              └─────────────────────┘
````

## Current Analysis

**Volatility**

* ATM Call / Put IV
* 25D Call / Put IV
* 25D Risk Reversal
* IV–RV spread
* 30D realized volatility
* 5D GARCH annualized forecast

**Positioning**

* Model GEX Proxy
* Call / Put GEX
* Gamma regime
* Model Gamma Flip
* Vanna
* Charm

**Tail Risk**

* EVT / Peaks-over-Threshold
* 99% VaR
* Expected Shortfall
* Tail-shape parameter

## Data Classification

| Classification | Meaning                                |
| -------------- | -------------------------------------- |
| `OBSERVED`     | Directly obtained from NSE/data source |
| `DERIVED`      | Calculated from observed market data   |
| `INFERRED`     | Model-based interpretation             |
| `ASSUMED`      | Explicit modelling assumption          |

> **Important:** GEX does not represent actual dealer positioning. The system assumes a hypothetical dealer inventory structure and labels the resulting exposure as `Model_GEX_Proxy`.

## Installation

```bash
git clone <your-repository>
cd indian-options-god-mode

python -m venv .venv
.venv\Scripts\activate       # Windows

pip install -e .
pytest tests/
```

Run the MCP server:

```bash
python -m indian_options_god_mode.mcp_server
```

## Claude Desktop Integration

Add the server to Claude Desktop's `claude_desktop_config.json`:

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

Restart Claude Desktop after saving the configuration.

You can then ask Claude:

```text
Generate the Quant Market Map for NIFTY for the next valid NSE expiry.
```

or:

```text
Analyze NIFTY options for the specified expiry and explain
the volatility, gamma regime, IV-RV spread and tail risk.
```

## Project Structure

```text
indian-options-god-mode/
├── src/
│   └── indian_options_god_mode/
│       ├── config.py
│       ├── quant_engine.py
│       ├── data_fetcher.py
│       ├── statistical_engine.py
│       └── mcp_server.py
├── tests/
├── .github/workflows/tests.yml
├── pyproject.toml
├── requirements.txt
└── README.md
```

**Version:** `5.1.0-rc1`
**Status:** Release Candidate

```
```
