"""Technical indicators.

Everything here takes plain numpy float arrays and returns arrays of the same
length, padded at the front with NaN where there isn't enough history yet.
Wilder smoothing is used for RSI, ATR and ADX so the numbers line up with what
TradingView and most brokers show.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

Array = np.ndarray


def _blank(n: int) -> Array:
    return np.full(n, np.nan, dtype=float)


def sma(v: Array, p: int) -> Array:
    n = len(v)
    out = _blank(n)
    if n < p:
        return out
    csum = np.cumsum(np.insert(v, 0, 0.0))
    out[p - 1:] = (csum[p:] - csum[:-p]) / p
    return out


def ema(v: Array, p: int) -> Array:
    n = len(v)
    out = _blank(n)
    if n < p:
        return out
    k = 2.0 / (p + 1)
    prev = float(np.mean(v[:p]))
    out[p - 1] = prev
    for i in range(p, n):
        prev = v[i] * k + prev * (1 - k)
        out[i] = prev
    return out


def rsi(v: Array, p: int = 14) -> Array:
    n = len(v)
    out = _blank(n)
    if n < p + 1:
        return out
    d = np.diff(v)
    gain = np.where(d > 0, d, 0.0)
    loss = np.where(d < 0, -d, 0.0)
    ag = float(gain[:p].mean())
    al = float(loss[:p].mean())
    out[p] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    for i in range(p, n - 1):
        ag = (ag * (p - 1) + gain[i]) / p
        al = (al * (p - 1) + loss[i]) / p
        out[i + 1] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    return out


@dataclass
class Macd:
    line: Array
    signal: Array
    hist: Array


def macd(v: Array, fast: int = 12, slow: int = 26, sig: int = 9) -> Macd:
    n = len(v)
    f, s = ema(v, fast), ema(v, slow)
    line = f - s
    signal = _blank(n)
    valid = ~np.isnan(line)
    if valid.any():
        idx = np.flatnonzero(valid)
        smoothed = ema(line[idx], sig)
        signal[idx] = smoothed
    return Macd(line=line, signal=signal, hist=line - signal)


def true_range(h: Array, l: Array, c: Array) -> Array:
    n = len(c)
    tr = _blank(n)
    if n < 2:
        return tr
    prev = c[:-1]
    tr[1:] = np.maximum.reduce([h[1:] - l[1:], np.abs(h[1:] - prev), np.abs(l[1:] - prev)])
    return tr


def atr(h: Array, l: Array, c: Array, p: int = 14) -> Array:
    n = len(c)
    out = _blank(n)
    tr = true_range(h, l, c)
    if n < p + 1:
        return out
    prev = float(np.nanmean(tr[1:p + 1]))
    out[p] = prev
    for i in range(p + 1, n):
        prev = (prev * (p - 1) + tr[i]) / p
        out[i] = prev
    return out


@dataclass
class Bands:
    mid: Array
    upper: Array
    lower: Array


def bollinger(v: Array, p: int = 20, k: float = 2.0) -> Bands:
    n = len(v)
    mid = sma(v, p)
    up, lo = _blank(n), _blank(n)
    for i in range(p - 1, n):
        window = v[i - p + 1:i + 1]
        sd = float(window.std(ddof=0))
        up[i] = mid[i] + k * sd
        lo[i] = mid[i] - k * sd
    return Bands(mid=mid, upper=up, lower=lo)


@dataclass
class Adx:
    adx: Array
    plus_di: Array
    minus_di: Array


def adx(h: Array, l: Array, c: Array, p: int = 14) -> Adx:
    n = len(c)
    blank = _blank(n)
    if n < 2 * p + 2:
        return Adx(adx=blank, plus_di=blank.copy(), minus_di=blank.copy())

    tr = np.zeros(n)
    pdm = np.zeros(n)
    mdm = np.zeros(n)
    for i in range(1, n):
        tr[i] = max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
        up, dn = h[i] - h[i - 1], l[i - 1] - l[i]
        pdm[i] = up if (up > dn and up > 0) else 0.0
        mdm[i] = dn if (dn > up and dn > 0) else 0.0

    str_, sp, sm = tr[1:p + 1].sum(), pdm[1:p + 1].sum(), mdm[1:p + 1].sum()
    pdi, mdi, dx = _blank(n), _blank(n), _blank(n)

    def push(i: int) -> None:
        P = 100 * sp / str_ if str_ else 0.0
        M = 100 * sm / str_ if str_ else 0.0
        pdi[i], mdi[i] = P, M
        dx[i] = 100 * abs(P - M) / (P + M) if (P + M) else 0.0

    push(p)
    for i in range(p + 1, n):
        str_ = str_ - str_ / p + tr[i]
        sp = sp - sp / p + pdm[i]
        sm = sm - sm / p + mdm[i]
        push(i)

    out = _blank(n)
    seed = dx[p:2 * p]
    seed = seed[~np.isnan(seed)]
    if len(seed):
        prev = float(seed.mean())
        out[2 * p - 1] = prev
        for i in range(2 * p, n):
            if np.isnan(dx[i]):
                continue
            prev = (prev * (p - 1) + dx[i]) / p
            out[i] = prev
    return Adx(adx=out, plus_di=pdi, minus_di=mdi)


def pivots(h: Array, l: Array, k: int = 4) -> tuple[list[tuple[int, float]], list[tuple[int, float]]]:
    """Fractal swing highs and lows: a bar that is the extreme of its +/-k window."""
    highs: list[tuple[int, float]] = []
    lows: list[tuple[int, float]] = []
    n = len(h)
    for i in range(k, n - k):
        win = slice(i - k, i + k + 1)
        others = np.r_[h[i - k:i], h[i + 1:i + k + 1]]
        if len(others) and h[i] > others.max():
            highs.append((i, float(h[i])))
        others_l = np.r_[l[i - k:i], l[i + 1:i + k + 1]]
        if len(others_l) and l[i] < others_l.min():
            lows.append((i, float(l[i])))
    return highs, lows


def max_drawdown(equity: Array) -> float:
    if len(equity) == 0:
        return 0.0
    peak = equity[0]
    worst = 0.0
    for v in equity:
        peak = max(peak, v)
        if peak > 0:
            worst = max(worst, (peak - v) / peak)
    return float(worst)


def clean(a: Array) -> list[Optional[float]]:
    """NaN -> None, so the values survive JSON."""
    return [None if (v is None or not np.isfinite(v)) else round(float(v), 6) for v in a]
