# src/indian_options_god_mode/web_app.py
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from .mcp_server import generate_quant_market_map

logger = logging.getLogger(__name__)

app = FastAPI(title="Indian Options God Mode API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QuantMapRequest(BaseModel):
    ticker: str
    expiry: str

@app.get("/")
def read_root():
    return {"status": "online", "message": "Indian Options God Mode API is running."}

@app.post("/api/quant-map")
def get_quant_map(request: QuantMapRequest):
    """
    REST endpoint for n8n and Websites to call.
    """
    logger.info(f"API Request received: {request.ticker} {request.expiry}")
    try:
        result = generate_quant_market_map(request.ticker, request.expiry)
        if "error" in result or ("status" in result and result["status"] != "LIVE_CALCULATED"):
            raise HTTPException(status_code=400, detail=result)
        return result
    except Exception as e:
        logger.error("API execution failed", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))