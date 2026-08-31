"""Where the price bars come from.

Fetching happens server-side, which is the main reason this app has a backend at
all: the browser gets blocked by CORS on most market data endpoints, a Python
process does not.

Bars are normalised to a list of dicts: {t (epoch ms), o, h, l, c, v}, oldest
first, with any incomplete row dropped.
"""
from __future__ import annotations

import csv
import io
import logging
import time
from datetime import datetime, timezone
from typing import Any, Optional

import requests

log = logging.getLogger(__name__)

RANGE_BARS = {"6mo": 132, "1y": 260, "2y": 515, "5y": 1290, "10y": 2570, "max": 5200}
VALID_RANGES = tuple(RANGE_BARS)
WARMUP_BARS = 240          # extra history so the 200-day average is defined on bar 1
CACHE_TTL = 300            # seconds
HTTP_TIMEOUT = 15

_cache: dict[str, tuple[float, list[dict]]] = {}


class DataError(RuntimeError):
    """Raised when no provider could return usable bars."""


# --------------------------------------------------------------------------- cache
def _cache_get(key: str) -> Optional[list[dict]]:
    hit = _cache.get(key)
    if not hit:
        return None
    ts, bars = hit
    if time.time() - ts > CACHE_TTL:
        _cache.pop(key, None)
        return None
    return bars


def _cache_put(key: str, bars: list[dict]) -> None:
    _cache[key] = (time.time(), bars)


def cache_clear() -> int:
    n = len(_cache)
    _cache.clear()
    return n


# --------------------------------------------------------------------------- helpers
def _row(t: Any, o: Any, h: Any, l: Any, c: Any, v: Any) -> Optional[dict]:
    try:
        o, h, l, c = float(o), float(h), float(l), float(c)
        v = float(v or 0)
    except (TypeError, ValueError):
        return None
    if not all(x > 0 for x in (o, h, l, c)):
        return None
    return {"t": int(t), "o": o, "h": h, "l": min(l, o, c), "c": c, "v": v}


def _finish(bars: list[dict], want: Optional[int]) -> list[dict]:
    bars = [b for b in bars if b]
    bars.sort(key=lambda b: b["t"])
    # drop duplicate timestamps, keeping the last
    dedup: dict[int, dict] = {b["t"]: b for b in bars}
    bars = [dedup[k] for k in sorted(dedup)]
    if want and len(bars) > want + WARMUP_BARS:
        bars = bars[-(want + WARMUP_BARS):]
    return bars


# --------------------------------------------------------------------------- yahoo
def _yahoo_via_yfinance(symbol: str, rng: str) -> list[dict]:
    import yfinance as yf  # imported lazily so the app boots without it

    period = "max" if rng == "max" else rng
    df = yf.Ticker(symbol).history(period=period, interval="1d", auto_adjust=False)
    if df is None or df.empty:
        raise DataError(f"yfinance returned nothing for {symbol}")
    out = []
    for idx, r in df.iterrows():
        ts = int(idx.timestamp() * 1000)
        out.append(_row(ts, r.get("Open"), r.get("High"), r.get("Low"),
                        r.get("Close"), r.get("Volume")))
    return out


def _yahoo_via_http(symbol: str, rng: str) -> list[dict]:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    r = requests.get(
        url,
        params={"range": rng, "interval": "1d"},
        headers={"User-Agent": "Mozilla/5.0 (market-desk)"},
        timeout=HTTP_TIMEOUT,
    )
    r.raise_for_status()
    result = (r.json().get("chart") or {}).get("result") or []
    if not result:
        raise DataError(f"no series in Yahoo response for {symbol}")
    res = result[0]
    q = res["indicators"]["quote"][0]
    ts = res.get("timestamp") or []
    vols = q.get("volume") or [0] * len(ts)
    return [_row(t * 1000, q["open"][i], q["high"][i], q["low"][i], q["close"][i], vols[i])
            for i, t in enumerate(ts)]


def fetch_yahoo(symbol: str, rng: str) -> list[dict]:
    errors = []
    for name, fn in (("yfinance", _yahoo_via_yfinance), ("yahoo-http", _yahoo_via_http)):
        try:
            bars = _finish(fn(symbol, rng), RANGE_BARS.get(rng))
            if len(bars) >= 60:
                log.info("%s: %d bars for %s via %s", rng, len(bars), symbol, name)
                return bars
            errors.append(f"{name}: only {len(bars)} usable bars")
        except Exception as exc:  # noqa: BLE001 - provider failures are expected
            errors.append(f"{name}: {exc}")
    raise DataError(f"could not load {symbol}. Tried — " + "; ".join(errors))


# --------------------------------------------------------------------------- binance
def fetch_binance(symbol: str, rng: str) -> list[dict]:
    limit = min(1000, RANGE_BARS.get(rng, 515) + WARMUP_BARS)
    r = requests.get(
        "https://api.binance.com/api/v3/klines",
        params={"symbol": symbol, "interval": "1d", "limit": limit},
        timeout=HTTP_TIMEOUT,
    )
    r.raise_for_status()
    bars = _finish([_row(k[0], k[1], k[2], k[3], k[4], k[5]) for k in r.json()],
                   RANGE_BARS.get(rng))
    if len(bars) < 60:
        raise DataError(f"Binance returned only {len(bars)} bars for {symbol}")
    return bars


# --------------------------------------------------------------------------- dispatch
def fetch(symbol: str, source: str, rng: str) -> list[dict]:
    if rng not in RANGE_BARS:
        raise DataError(f"unknown range {rng!r}; use one of {', '.join(VALID_RANGES)}")
    key = f"{source}:{symbol}:{rng}"
    cached = _cache_get(key)
    if cached:
        return cached
    bars = fetch_binance(symbol, rng) if source == "binance" else fetch_yahoo(symbol, rng)
    _cache_put(key, bars)
    return bars


# --------------------------------------------------------------------------- csv
_DATE_FORMATS = ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y", "%d-%b-%Y",
                 "%d %b %Y", "%b %d, %Y", "%Y/%m/%d", "%d-%b-%y")


def _parse_date(s: str) -> Optional[int]:
    s = s.strip().strip('"')
    for fmt in _DATE_FORMATS:
        try:
            return int(datetime.strptime(s, fmt).replace(tzinfo=timezone.utc).timestamp() * 1000)
        except ValueError:
            continue
    try:  # ISO with time, or anything fromisoformat accepts
        return int(datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp() * 1000)
    except ValueError:
        return None


def _to_float(s: Any) -> Optional[float]:
    if s is None:
        return None
    txt = str(s).strip().replace(",", "").replace("\u20b9", "").replace("$", "")
    if txt in ("", "-", "N/A", "null", "None"):
        return None
    try:
        return float(txt)
    except ValueError:
        return None


def parse_csv(text: str) -> list[dict]:
    """Accepts the exports from Yahoo Finance, NSE, Investing.com and friends."""
    text = text.strip()
    if not text:
        raise DataError("the file was empty")
    sample = "\n".join(text.splitlines()[:5])
    try:
        delim = csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
    except csv.Error:
        delim = ","

    rows = list(csv.reader(io.StringIO(text), delimiter=delim))
    rows = [r for r in rows if any(cell.strip() for cell in r)]
    if len(rows) < 41:
        raise DataError(f"need at least 40 rows of daily data, got {max(0, len(rows) - 1)}")

    header = [h.strip().lower().replace(" ", "").replace("_", "") for h in rows[0]]
    body = rows[1:]

    def find(*keys: str) -> int:
        for k in keys:
            for i, h in enumerate(header):
                if h == k:
                    return i
        for k in keys:
            for i, h in enumerate(header):
                if k in h:
                    return i
        return -1

    iD, iO = find("date", "time", "timestamp"), find("open")
    iH, iL = find("high"), find("low")
    iC = find("close", "closeprice", "ltp", "price", "adjclose")
    iV = find("volume", "vol", "sharestraded", "turnover")

    if iD < 0 or iC < 0:  # headerless file — assume the conventional column order
        iD, iO, iH, iL, iC, iV = 0, 1, 2, 3, 4, 5
        body = rows

    out: list[dict] = []
    for r in body:
        if len(r) <= max(iD, iC):
            continue
        t = _parse_date(r[iD])
        c = _to_float(r[iC])
        if t is None or c is None:
            continue
        o = _to_float(r[iO]) if 0 <= iO < len(r) else None
        h = _to_float(r[iH]) if 0 <= iH < len(r) else None
        l = _to_float(r[iL]) if 0 <= iL < len(r) else None
        v = _to_float(r[iV]) if 0 <= iV < len(r) else None
        o = o if o else c
        h = h if h else max(o, c)
        l = l if l else min(o, c)
        row = _row(t, o, h, l, c, v)
        if row:
            out.append(row)

    bars = _finish(out, None)
    if len(bars) < 40:
        raise DataError(f"parsed only {len(bars)} valid rows — check the date and close columns")
    return bars
