"""Market Desk API.

Endpoints
---------
GET  /api/health                     liveness
GET  /api/universe                   the pickable asset catalog
GET  /api/analyse                    analyse a catalog symbol (or any Yahoo ticker)
POST /api/analyse/csv                analyse an uploaded CSV of daily bars
POST /api/position-size              units to buy for a given stop and risk budget
POST /api/cache/clear                drop the price cache

Everything is read-only. No orders are placed anywhere, ever.
"""
from __future__ import annotations

import logging
import os

from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import analysis, backtest, providers, seasonality, universe

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"),
                    format="%(asctime)s %(levelname)-7s %(name)s | %(message)s")
log = logging.getLogger("market-desk")

ALLOWED_ORIGINS = [o.strip() for o in os.getenv(
    "ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if o.strip()]

app = FastAPI(
    title="Market Desk API",
    version="1.0.0",
    description="Technical analysis with the risk numbers first. Not investment advice.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

DISCLAIMER = (
    "Information only, not investment advice. No system can guarantee you won't lose money — "
    "what a plan can do is cap the loss on any single trade to an amount you chose in advance."
)


# --------------------------------------------------------------------------- helpers
def _assemble(bars: list[dict], style: str, label: str, currency: str,
              source: str, symbol: Optional[str]) -> dict:
    result = analysis.analyse(bars, style)
    arrays = result.pop("_arrays")
    result["backtest"] = backtest.run(arrays)
    result["seasonality"] = seasonality.run(bars)
    result["asset"] = {
        "name": label,
        "symbol": symbol,
        "currency": currency,
        "currency_symbol": universe.CURRENCY_SYMBOL.get(currency, ""),
        "source": source,
        "first_bar": bars[0]["t"],
        "last_bar": bars[-1]["t"],
    }
    result["disclaimer"] = DISCLAIMER
    return result


# --------------------------------------------------------------------------- routes
@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "cached_series": len(providers._cache)}


@app.get("/api/universe")
def get_universe() -> dict:
    return {
        "categories": [{"name": cat, "assets": rows} for cat, rows in universe.UNIVERSE.items()],
        "ranges": list(providers.VALID_RANGES),
        "styles": [
            {"id": "swing", "label": "Swing (days–weeks)"},
            {"id": "position", "label": "Position (weeks–months)"},
        ],
        "disclaimer": DISCLAIMER,
    }


@app.get("/api/analyse")
def analyse_symbol(
    symbol: str = Query(..., min_length=1, max_length=24, description="e.g. ^NSEI, AAPL, BTCUSDT"),
    range: str = Query("2y", description="6mo | 1y | 2y | 5y | 10y | max"),
    style: str = Query("swing", pattern="^(swing|position)$"),
    source: Optional[str] = Query(None, pattern="^(yahoo|binance)$"),
) -> dict:
    known = universe.lookup(symbol)
    src = source or (known["source"] if known else "yahoo")
    label = known["name"] if known else symbol
    currency = known["currency"] if known else ("USD" if src == "binance" else "")

    try:
        bars = providers.fetch(symbol, src, range)
    except providers.DataError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    try:
        return _assemble(bars, style, label, currency, src, symbol)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/analyse/csv")
async def analyse_csv(
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
    style: str = Form("swing"),
    label: str = Form("Imported series"),
    currency: str = Form(""),
) -> dict:
    if style not in ("swing", "position"):
        raise HTTPException(status_code=422, detail="style must be swing or position")

    if file is not None:
        raw = await file.read()
        if len(raw) > 8_000_000:
            raise HTTPException(status_code=413, detail="file larger than 8 MB")
        try:
            payload = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            payload = raw.decode("latin-1")
        label = label if label != "Imported series" else (file.filename or label)
    elif text:
        payload = text
    else:
        raise HTTPException(status_code=422, detail="send either a file or a text field")

    try:
        bars = providers.parse_csv(payload)
        return _assemble(bars, style, label, currency, "csv", None)
    except (providers.DataError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


class SizeRequest(BaseModel):
    capital: float = Field(gt=0, description="total account value")
    risk_pct: float = Field(1.0, gt=0, le=20, description="percent of capital risked on this trade")
    entry: float = Field(gt=0)
    stop: float = Field(gt=0)
    target: Optional[float] = Field(None, gt=0)


@app.post("/api/position-size")
def position_size(req: SizeRequest) -> dict:
    per_unit = req.entry - req.stop
    if per_unit <= 0:
        raise HTTPException(status_code=422, detail="the stop must sit below the entry price")

    budget = req.capital * req.risk_pct / 100
    units = int(budget // per_unit)
    value = units * req.entry
    share = value / req.capital if req.capital else 0.0

    # The account size at which one unit fits inside the chosen risk budget.
    # Useful when the answer is zero: it says what would have to change.
    min_capital = per_unit / (req.risk_pct / 100)

    warning = None
    if units <= 0:
        warning = (f"One unit risks {per_unit:,.2f}, which is more than your whole risk budget of "
                   f"{budget:,.2f}. At {req.risk_pct:g}% risk you would need about "
                   f"{min_capital:,.0f} of capital to take even one unit. Use a cheaper proxy for "
                   "the same exposure (an ETF, or a smaller-lot instrument), widen your risk "
                   "percentage knowingly, or skip the trade — do not just buy one anyway.")
    elif share > 0.35:
        warning = (f"That position is {share * 100:.0f}% of your capital in one name. The maths "
                   "says the loss is capped, but a gap through your stop overnight would not be. "
                   "Consider halving it.")
    elif share > 0.20:
        warning = (f"Note: {share * 100:.0f}% of capital in a single position. Fine if it is one "
                   "of a few, dangerous if it is one of two.")

    return {
        "units": units,
        "position_value": round(value, 2),
        "capital_share_pct": round(share * 100, 2),
        "risk_per_unit": round(per_unit, 4),
        "loss_if_stopped": round(units * per_unit, 2),
        "loss_pct_of_capital": round(units * per_unit / req.capital * 100, 3) if req.capital else 0,
        "gain_if_target": round(units * (req.target - req.entry), 2) if req.target else None,
        "min_capital_for_one_unit": round(min_capital, 2),
        "warning": warning,
    }


@app.post("/api/cache/clear")
def clear_cache() -> dict:
    return {"cleared": providers.cache_clear()}
