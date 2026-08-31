"""Turns a price series into a trade plan.

The output deliberately leads with risk: where you get out, how much that costs,
and only then where the upside might be. A large share of the possible verdicts
are "don't trade this", which is the point rather than a shortcoming.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Optional

import numpy as np

from . import indicators as ind

MIN_BARS = 40
THIN_BARS = 120


@dataclass
class Factor:
    label: str
    value: str
    score: float
    note: str


@dataclass
class Level:
    price: float
    hits: int
    kind: str
    distance_pct: float


@dataclass
class Plan:
    entry_low: float
    entry_high: float
    entry_mid: float
    stop: float
    target1: float
    target2: float
    risk_per_unit: float
    risk_pct: float
    rr1: float
    rr2: float


def _fmt(x: float) -> str:
    if x is None or not np.isfinite(x):
        return "-"
    a = abs(x)
    d = 0 if a >= 1000 else 2 if a >= 10 else 3 if a >= 1 else 5
    return f"{x:,.{d}f}"


def _last(a: np.ndarray) -> Optional[float]:
    if len(a) == 0:
        return None
    v = a[-1]
    return None if not np.isfinite(v) else float(v)


def analyse(bars: list[dict], style: str = "swing") -> dict[str, Any]:
    if len(bars) < MIN_BARS:
        raise ValueError(f"need at least {MIN_BARS} daily bars, got {len(bars)}")

    o = np.array([b["o"] for b in bars], dtype=float)
    h = np.array([b["h"] for b in bars], dtype=float)
    l = np.array([b["l"] for b in bars], dtype=float)
    c = np.array([b["c"] for b in bars], dtype=float)
    n = len(c)
    px = float(c[-1])

    s20, s50, s200 = ind.sma(c, 20), ind.sma(c, 50), ind.sma(c, 200)
    rsi = ind.rsi(c, 14)
    mac = ind.macd(c)
    bands = ind.bollinger(c, 20, 2.0)
    atr_arr = ind.atr(h, l, c, 14)
    adx_obj = ind.adx(h, l, c, 14)

    a = _last(atr_arr) or px * 0.02
    atr_pct = a / px
    rsi_now = _last(rsi)
    adx_now = _last(adx_obj.adx)
    hist_now = _last(mac.hist)
    hist_prev = float(mac.hist[-2]) if n >= 2 and np.isfinite(mac.hist[-2]) else None

    # ---------------- support / resistance clusters ----------------
    lookback = min(n, 500 if style == "position" else 260)
    start = n - lookback
    ph, pl = ind.pivots(h[start:], l[start:], 6 if style == "position" else 4)
    touches = [(i + start, p) for i, p in ph] + [(i + start, p) for i, p in pl]

    clusters: list[dict[str, Any]] = []
    for i, p in sorted(touches, key=lambda t: t[1]):
        hit = next((z for z in clusters if abs(z["price"] - p) < a * 0.85), None)
        if hit:
            hit["price"] = (hit["price"] * hit["hits"] + p) / (hit["hits"] + 1)
            hit["hits"] += 1
            hit["last_i"] = max(hit["last_i"], i)
        else:
            clusters.append({"price": p, "hits": 1, "last_i": i})

    below = sorted([z for z in clusters if z["price"] < px * 0.997], key=lambda z: -z["price"])
    above = sorted([z for z in clusters if z["price"] > px * 1.003], key=lambda z: z["price"])
    sup1 = below[0] if below else None
    res1 = above[0] if above else None
    res2 = above[1] if len(above) > 1 else None

    window = c[max(0, n - 252):]
    hi52, lo52 = float(window.max()), float(window.min())

    # ---------------- scoring ----------------
    F: list[Factor] = []

    def add(label: str, value: str, score: float, note: str) -> None:
        F.append(Factor(label, value, round(float(score), 2), note))

    above_200 = np.isfinite(s200[-1]) and px > s200[-1]
    golden = np.isfinite(s50[-1]) and np.isfinite(s200[-1]) and s50[-1] > s200[-1]

    if np.isfinite(s200[-1]):
        add("Price vs 200-day average", f"{(px / s200[-1] - 1) * 100:.1f}%",
            2 if above_200 else -2,
            "long-term uptrend intact" if above_200
            else "below the long-term average — the tide is against you")
    else:
        add("200-day average", "not enough history", 0, "needs 200 bars")

    if np.isfinite(s50[-1]) and np.isfinite(s200[-1]):
        add("50-day vs 200-day", "50 above 200" if golden else "50 below 200",
            1.5 if golden else -1.5,
            "medium-term trend agrees" if golden else "medium-term trend disagrees")

    if np.isfinite(s20[-1]):
        up20 = px > s20[-1]
        add("Price vs 20-day average", f"{(px / s20[-1] - 1) * 100:.1f}%", 0.8 if up20 else -0.5,
            "short-term buyers in control" if up20 else "short-term pullback under way")

    if rsi_now is not None:
        if rsi_now > 78:
            sc, note = -1.6, "overbought — buying here is chasing"
        elif rsi_now > 62:
            sc, note = 0.4, "strong but extended"
        elif rsi_now >= 45:
            sc, note = 1.2, "healthy zone, room to move"
        elif rsi_now >= 32:
            sc = 1.0 if above_200 else -0.6
            note = ("pullback inside an uptrend — the useful kind" if above_200
                    else "weak and getting weaker")
        else:
            sc = 0.6 if above_200 else -1.4
            note = ("deeply oversold in an uptrend" if above_200
                    else "oversold in a downtrend — falling knife")
        add("Relative strength (14)", f"{rsi_now:.1f}", sc, note)

    if hist_now is not None and hist_prev is not None:
        rising = hist_now > hist_prev
        note = ("momentum building" if hist_now > 0 and rising
                else "momentum draining" if hist_now < 0 and not rising
                else "momentum turning")
        add("MACD momentum",
            f"{'positive' if hist_now > 0 else 'negative'}, {'rising' if rising else 'falling'}",
            (0.8 if hist_now > 0 else -0.8) + (0.7 if rising else -0.7), note)

    if adx_now is not None:
        add("Trend strength (ADX)", f"{adx_now:.1f}",
            -0.8 if adx_now < 18 else 0.2 if adx_now < 25 else 0.9,
            "no real trend — signals here misfire often" if adx_now < 18
            else "trend forming" if adx_now < 25 else "trend is strong")

    if sup1:
        near = (px - sup1["price"]) / a < 1.6
        add("Nearest support",
            f"{_fmt(sup1['price'])} ({(px / sup1['price'] - 1) * 100:.1f}% below)",
            1.2 if near else 0.2,
            f"sitting close to a level buyers defended {sup1['hits']}x" if near
            else "support is far — a stop would be wide")

    if res1:
        tight = (res1["price"] - px) / a < 1.2
        add("Nearest resistance",
            f"{_fmt(res1['price'])} ({(res1['price'] / px - 1) * 100:.1f}% above)",
            -1.0 if tight else 0.3,
            "resistance right overhead, little room" if tight else "clear air above")

    add("Daily volatility (ATR)", f"{atr_pct * 100:.2f}% of price",
        -1.0 if atr_pct > 0.045 else -0.3 if atr_pct > 0.03 else 0.3,
        "very wide daily swings — size down hard" if atr_pct > 0.045
        else "lively" if atr_pct > 0.03 else "calm enough to place a tight stop")

    rng = hi52 - lo52 or 1.0
    add("Position in 52-week range", f"{(px - lo52) / rng * 100:.0f}%", 0,
        f"low {_fmt(lo52)} — high {_fmt(hi52)}")

    score = round(sum(f.score for f in F), 2)

    # ---------------- trade plan ----------------
    stop_mult = 2.2 if style == "position" else 1.5
    entry_high = px
    entry_low = max(min(s20[-1], px) if np.isfinite(s20[-1]) else px - a * 0.8, px - a * 1.2)
    if sup1 and (px - sup1["price"]) / a < 2.2:
        entry_low = max(sup1["price"] + a * 0.15, px - a * 1.6)
    entry_low = min(entry_low, px * 0.999)
    entry_mid = (entry_low + entry_high) / 2

    stop = entry_low - a * stop_mult
    if sup1 and sup1["price"] < entry_low:
        stop = min(stop, sup1["price"] - a * 0.4)
    risk = entry_mid - stop

    t1 = entry_mid + risk * 2
    if res1 and entry_mid < res1["price"] < t1:
        t1 = res1["price"] - a * 0.15
    t1 = max(t1, entry_mid + risk * 0.35)          # never let the ladder invert
    t2 = entry_mid + risk * 3.5
    if res2 and res2["price"] > t1:
        t2 = max(t1 * 1.001, res2["price"] - a * 0.15)
    t2 = max(t2, t1 + risk * 0.4)

    plan = Plan(
        entry_low=round(entry_low, 6), entry_high=round(entry_high, 6),
        entry_mid=round(entry_mid, 6), stop=round(stop, 6),
        target1=round(t1, 6), target2=round(t2, 6),
        risk_per_unit=round(risk, 6), risk_pct=round(risk / entry_mid * 100, 3),
        rr1=round((t1 - entry_mid) / risk, 2), rr2=round((t2 - entry_mid) / risk, 2),
    )

    # ---------------- verdict ----------------
    # Protective gate, applied before the score is consulted: when price is under its
    # 200-day average AND the 50-day is under the 200-day, the long-term trend is
    # broken. Short-term momentum can look excellent inside that regime — that is
    # exactly what a bounce in a downtrend looks like, and buying it is one of the
    # most reliable ways retail money disappears. The gate only ever restricts
    # buying; it is deliberately asymmetric and never turns a caution into a green light.
    bear_regime = (np.isfinite(s200[-1]) and px < s200[-1]
                   and np.isfinite(s50[-1]) and s50[-1] < s200[-1])

    if n < THIN_BARS:
        verdict = "Not enough history to judge this"
        tone = "negative"
        why = (f"Only {n} bars loaded. The 200-day average, trend strength and level "
               "detection all need more than that, so anything below is built on air. "
               "Load at least a year of daily data before taking a number from this seriously.")
        score = 0.0
    elif bear_regime:
        verdict = "Downtrend. Don't buy this, and trim what you hold"
        tone = "negative"
        bounce = (" Short-term momentum is currently positive, which is what makes this "
                  "dangerous rather than safe: a bounce inside a downtrend is the most "
                  "expensive trade there is."
                  if hist_now is not None and hist_now > 0 else "")
        why = (f"Price is {abs((px / s200[-1] - 1) * 100):.1f}% below its 200-day average and the "
               f"50-day sits below the 200-day.{bounce} Averaging down here is how small losses "
               f"become permanent ones. If you already own it, decide now what price makes you "
               f"exit — {_fmt(stop)} is a defensible line — and honour it.")
    elif score >= 4.5 and plan.rr1 >= 1.6:
        verdict = "Buy into the marked zone, in two tranches"
        tone = "positive"
        why = (f"Trend, momentum and location all line up, and the nearest resistance leaves "
               f"enough room that a {plan.rr1:.1f}:1 payoff is realistic. Split the order: half "
               f"near {_fmt(entry_high)}, half if it dips toward {_fmt(entry_low)}. If it closes "
               f"below {_fmt(stop)}, you were wrong — leave.")
    elif score >= 1.8 and plan.rr1 >= 1.5:
        verdict = "Worth a starter position, not a full one"
        tone = "neutral"
        add_above = res1["price"] if res1 else entry_high * 1.02
        why = ("More agrees than disagrees, but not enough to bet heavily. Take a third of your "
               f"normal size in the zone below, and only add once price closes above "
               f"{_fmt(add_above)}. Same exit either way: below {_fmt(stop)}.")
    elif score >= 1.8:
        verdict = "Right idea, wrong price — wait for a pullback"
        tone = "neutral"
        why = ("The setup is fine but you're paying too much for it: resistance sits close enough "
               f"that the reward-to-risk is only {plan.rr1:.1f}:1. Set an alert near "
               f"{_fmt(entry_low)} and let the market come to you. A skipped trade costs nothing.")
    elif score > -1.5:
        verdict = "No edge here. Sit this one out"
        tone = "neutral"
        extra = (f" and there's no trend to lean on (ADX {adx_now:.0f})"
                 if adx_now is not None and adx_now < 18 else "")
        why = (f"The readings contradict each other{extra}. This is the state where most money "
               "gets lost — small losses, repeatedly, from trading a market that isn't going "
               "anywhere. Cash is a position.")
    else:
        verdict = "Downtrend. Don't buy this, and trim what you hold"
        tone = "negative"
        why = ("Price is below its long-term average with momentum still falling. Averaging down "
               "here is how small losses become permanent ones. If you already own it, decide now "
               f"what price makes you exit — {_fmt(stop)} is a defensible line — and honour it.")

    def levels(src: list[dict], kind: str, limit: int = 3) -> list[Level]:
        return [Level(price=round(z["price"], 6), hits=z["hits"], kind=kind,
                      distance_pct=round((z["price"] / px - 1) * 100, 2))
                for z in src[:limit]]

    prev_close = float(c[-2]) if n >= 2 else px

    return {
        "meta": {
            "bars": n,
            "style": style,
            "price": round(px, 6),
            "prev_close": round(prev_close, 6),
            "change_pct": round((px / prev_close - 1) * 100, 3),
            "atr": round(a, 6),
            "atr_pct": round(atr_pct * 100, 3),
            "high_52w": round(hi52, 6),
            "low_52w": round(lo52, 6),
            "thin_history": n < THIN_BARS,
        },
        "verdict": {"headline": verdict, "why": why, "tone": tone, "score": score},
        "plan": asdict(plan),
        "factors": [asdict(f) for f in F],
        "levels": [asdict(x) for x in levels(above, "resistance")[::-1]]
                  + [asdict(x) for x in levels(below, "support")],
        "series": {
            "t": [b["t"] for b in bars],
            "o": ind.clean(o), "h": ind.clean(h), "l": ind.clean(l), "c": ind.clean(c),
            "sma20": ind.clean(s20), "sma50": ind.clean(s50), "sma200": ind.clean(s200),
            "bb_upper": ind.clean(bands.upper), "bb_lower": ind.clean(bands.lower),
            "rsi": ind.clean(rsi), "macd_hist": ind.clean(mac.hist),
        },
        "_arrays": {  # internal, stripped before the response leaves main.py
            "c": c, "h": h, "l": l, "s50": s50, "s200": s200,
            "rsi": rsi, "hist": mac.hist,
        },
    }
