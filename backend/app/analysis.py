"""Turns a price series into a trade plan.

The output deliberately leads with risk: where you get out, how much that costs,
and only then where the upside might be. A large share of the possible verdicts
are "don't trade this", which is the point rather than a shortcoming.

Supports both long and short directions. The system picks the direction based on
trend, momentum and location — it will say "short" when the weight of evidence
points down, "long" when it points up, and "neutral" when the picture is mixed.
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
    direction: str          # "long", "short", or "neutral"
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
    try:
        if x is None or not np.isfinite(x):
            return "-"
        a = abs(x)
        d = 0 if a >= 1000 else 2 if a >= 10 else 3 if a >= 1 else 5
        return f"{x:,.{d}f}"
    except (TypeError, ValueError):
        return "-"


def _last(a: np.ndarray) -> Optional[float]:
    try:
        if len(a) == 0:
            return None
        v = a[-1]
        return None if not np.isfinite(v) else float(v)
    except (IndexError, TypeError):
        return None


def analyse(bars: list[dict], style: str = "swing") -> dict[str, Any]:
    try:
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
        sup2 = below[1] if len(below) > 1 else None
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

        # ---------------- regime detection ----------------
        bear_regime = (np.isfinite(s200[-1]) and px < s200[-1]
                       and np.isfinite(s50[-1]) and s50[-1] < s200[-1])

        bull_regime = (np.isfinite(s200[-1]) and px > s200[-1]
                       and np.isfinite(s50[-1]) and s50[-1] > s200[-1])

        momentum_down = (hist_now is not None and hist_now < 0
                         and hist_prev is not None and hist_now < hist_prev)

        # ---------------- direction decision ----------------
        stop_mult = 2.2 if style == "position" else 1.5

        if n < THIN_BARS:
            direction = "neutral"
        elif bear_regime and score <= -2.5 and (adx_now is None or adx_now >= 18):
            direction = "short"
        elif bear_regime and score <= -1.5 and momentum_down:
            direction = "short"
        elif score >= 1.8:
            direction = "long"
        else:
            direction = "neutral"

        # ---------------- long plan ----------------
        entry_high_l = px
        entry_low_l = max(min(s20[-1], px) if np.isfinite(s20[-1]) else px - a * 0.8, px - a * 1.2)
        if sup1 and (px - sup1["price"]) / a < 2.2:
            entry_low_l = max(sup1["price"] + a * 0.15, px - a * 1.6)
        entry_low_l = min(entry_low_l, px * 0.999)
        entry_mid_l = (entry_low_l + entry_high_l) / 2

        stop_l = entry_low_l - a * stop_mult
        if sup1 and sup1["price"] < entry_low_l:
            stop_l = min(stop_l, sup1["price"] - a * 0.4)
        risk_l = entry_mid_l - stop_l

        t1_l = entry_mid_l + risk_l * 2
        if res1 and entry_mid_l < res1["price"] < t1_l:
            t1_l = res1["price"] - a * 0.15
        t1_l = max(t1_l, entry_mid_l + risk_l * 0.35)
        t2_l = entry_mid_l + risk_l * 3.5
        if res2 and res2["price"] > t1_l:
            t2_l = max(t1_l * 1.001, res2["price"] - a * 0.15)
        t2_l = max(t2_l, t1_l + risk_l * 0.4)

        long_plan = Plan(
            direction="long",
            entry_low=round(entry_low_l, 6), entry_high=round(entry_high_l, 6),
            entry_mid=round(entry_mid_l, 6), stop=round(stop_l, 6),
            target1=round(t1_l, 6), target2=round(t2_l, 6),
            risk_per_unit=round(risk_l, 6), risk_pct=round(risk_l / entry_mid_l * 100, 3),
            rr1=round((t1_l - entry_mid_l) / risk_l, 2),
            rr2=round((t2_l - entry_mid_l) / risk_l, 2),
        )

        # ---------------- short plan ----------------
        # For shorts: entry zone is at or slightly above current price (sell high),
        # stop is above entry (you lose if price rises), targets are below (you profit
        # if price falls).
        entry_low_s = px
        entry_high_s = min(max(s20[-1], px) if np.isfinite(s20[-1]) else px + a * 0.8, px + a * 1.2)
        if res1 and (res1["price"] - px) / a < 2.2:
            entry_high_s = min(res1["price"] - a * 0.15, px + a * 1.6)
        entry_high_s = max(entry_high_s, px * 1.001)
        entry_mid_s = (entry_low_s + entry_high_s) / 2

        stop_s = entry_high_s + a * stop_mult
        if res1 and res1["price"] > entry_high_s:
            stop_s = max(stop_s, res1["price"] + a * 0.4)
        risk_s = stop_s - entry_mid_s

        t1_s = entry_mid_s - risk_s * 2
        if sup1 and t1_s < sup1["price"] < entry_mid_s:
            t1_s = sup1["price"] + a * 0.15
        t1_s = min(t1_s, entry_mid_s - risk_s * 0.35)
        t2_s = entry_mid_s - risk_s * 3.5
        if sup2 and sup2["price"] < t1_s:
            t2_s = min(t1_s * 0.999, sup2["price"] + a * 0.15)
        t2_s = min(t2_s, t1_s - risk_s * 0.4)

        # Guard against negative targets
        t1_s = max(t1_s, 0.01)
        t2_s = max(t2_s, 0.01)

        short_plan = Plan(
            direction="short",
            entry_low=round(entry_low_s, 6), entry_high=round(entry_high_s, 6),
            entry_mid=round(entry_mid_s, 6), stop=round(stop_s, 6),
            target1=round(t1_s, 6), target2=round(t2_s, 6),
            risk_per_unit=round(risk_s, 6), risk_pct=round(risk_s / entry_mid_s * 100, 3),
            rr1=round((entry_mid_s - t1_s) / risk_s, 2),
            rr2=round((entry_mid_s - t2_s) / risk_s, 2),
        )

        # Pick the plan matching the direction; use long plan for neutral
        if direction == "short":
            plan = short_plan
        else:
            plan = long_plan

        # Keep references for verdict text
        entry_high = plan.entry_high
        entry_low = plan.entry_low
        stop = plan.stop

        # ---------------- verdict ----------------
        if n < THIN_BARS:
            verdict = "Not enough history to judge this"
            tone = "negative"
            why = (f"Only {n} bars loaded. The 200-day average, trend strength and level "
                   "detection all need more than that, so anything below is built on air. "
                   "Load at least a year of daily data before taking a number from this seriously.")
            score = 0.0

        elif direction == "short" and bear_regime:
            # ------- short verdicts -------
            if score <= -4.0 and plan.rr1 >= 1.6:
                verdict = "Short this — sell into the marked zone"
                tone = "negative"
                why = (f"Trend, momentum and location all point down. Price is "
                       f"{abs((px / s200[-1] - 1) * 100):.1f}% below the 200-day average, the "
                       f"50-day sits under the 200-day, and the reward-to-risk on the short side "
                       f"is {plan.rr1:.1f}:1. Enter the short near {_fmt(entry_high)}, cover half "
                       f"at {_fmt(plan.target1)} and trail the rest. If price closes above "
                       f"{_fmt(stop)}, you were wrong — cover and move on.")
            elif score <= -2.5 and plan.rr1 >= 1.3:
                verdict = "Short opportunity — starter size, not full"
                tone = "negative"
                bounce = (" Short-term momentum has turned up, which is the bounce you want to "
                          "sell into — wait for it to stall before adding."
                          if hist_now is not None and hist_now > 0 else "")
                why = (f"The downtrend is intact.{bounce} Take a smaller short near "
                       f"{_fmt(entry_high)} with a stop above {_fmt(stop)}. Cover at "
                       f"{_fmt(plan.target1)} for {plan.rr1:.1f}:1.")
            else:
                verdict = "Downtrend — short possible, but wait for a better entry"
                tone = "negative"
                why = (f"Price is below its 200-day average and the trend is down, but the current "
                       f"position doesn't offer a clean short entry. Set an alert near "
                       f"{_fmt(entry_high)} and wait for a bounce into resistance before shorting. "
                       f"Stop above {_fmt(stop)}.")

        elif direction == "short":
            # Short outside bear_regime (momentum-based)
            verdict = "Momentum is weak — consider a short"
            tone = "negative"
            why = (f"While the long-term trend isn't fully broken, momentum is clearly negative. "
                   f"A short near {_fmt(entry_high)} with stop above {_fmt(stop)} targets "
                   f"{_fmt(plan.target1)} for {plan.rr1:.1f}:1. Size small — you're trading "
                   f"against a trend that hasn't fully turned yet.")

        elif bear_regime:
            # Bear regime but direction is neutral (not short-able enough)
            verdict = "Downtrend — don't buy, and trim what you hold"
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
            verdict = "Go long — buy into the marked zone, in two tranches"
            tone = "positive"
            why = (f"Trend, momentum and location all line up, and the nearest resistance leaves "
                   f"enough room that a {plan.rr1:.1f}:1 payoff is realistic. Split the order: half "
                   f"near {_fmt(entry_high)}, half if it dips toward {_fmt(entry_low)}. If it closes "
                   f"below {_fmt(stop)}, you were wrong — leave.")

        elif score >= 1.8 and plan.rr1 >= 1.5:
            verdict = "Go long — worth a starter position, not a full one"
            tone = "neutral"
            add_above = res1["price"] if res1 else entry_high * 1.02
            why = ("More agrees than disagrees, but not enough to bet heavily. Take a third of your "
                   f"normal size in the zone below, and only add once price closes above "
                   f"{_fmt(add_above)}. Same exit either way: below {_fmt(stop)}.")

        elif score >= 1.8:
            verdict = "Bullish setup but wrong price — wait for a pullback"
            tone = "neutral"
            why = ("The setup is fine but you're paying too much for it: resistance sits close enough "
                   f"that the reward-to-risk is only {plan.rr1:.1f}:1. Set an alert near "
                   f"{_fmt(entry_low)} and let the market come to you. A skipped trade costs nothing.")

        elif score > -1.5:
            verdict = "No edge either way — sit this one out"
            tone = "neutral"
            extra = (f" and there's no trend to lean on (ADX {adx_now:.0f})"
                     if adx_now is not None and adx_now < 18 else "")
            why = (f"The readings contradict each other{extra}. This is the state where most money "
                   "gets lost — small losses, repeatedly, from trading a market that isn't going "
                   "anywhere. Cash is a position. Neither long nor short has an edge here.")

        else:
            verdict = "Bearish — don't buy, and trim what you hold"
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
            "direction": direction,
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
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"Analysis failed: {exc}") from exc
