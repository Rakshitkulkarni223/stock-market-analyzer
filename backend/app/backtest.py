"""Walk the same rule the analyser suggests over the loaded history.

The point of this module is disillusionment. If the rule loses money on this
market over this window, the numbers say so plainly, and the UI repeats it.

Supports both long and short directions.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from . import indicators as ind

WARMUP = 210          # need a 200-day average before the first trade
MAX_HOLD = 90         # bars
STOP_ATR = 1.6
TARGET_R = 2.0


def _run_long(arrays: dict[str, np.ndarray]) -> dict[str, Any]:
    """Backtest the long-side rule: buy when trend is up and momentum turns."""
    try:
        c, h, l = arrays["c"], arrays["h"], arrays["l"]
        s50, s200 = arrays["s50"], arrays["s200"]
        rsi, hist = arrays["rsi"], arrays["hist"]
        at = ind.atr(h, l, c, 14)
        n = len(c)

        trades: list[dict[str, Any]] = []
        pos = None

        for i in range(WARMUP, n):
            if pos is None:
                trend_ok = np.isfinite(s200[i]) and c[i] > s200[i]
                rsi_cross = (np.isfinite(rsi[i]) and np.isfinite(rsi[i - 1])
                             and rsi[i - 1] < 45 <= rsi[i])
                macd_cross = (np.isfinite(hist[i]) and np.isfinite(hist[i - 1])
                              and hist[i - 1] < 0 <= hist[i])
                if trend_ok and (rsi_cross or macd_cross) and np.isfinite(at[i]) and at[i] > 0:
                    entry = float(c[i])
                    stop = entry - STOP_ATR * at[i]
                    pos = {"i": i, "entry": entry, "stop": stop,
                           "target": entry + TARGET_R * (entry - stop)}
                continue

            exit_px, reason = None, ""
            if l[i] <= pos["stop"]:
                exit_px, reason = pos["stop"], "stop"
            elif h[i] >= pos["target"]:
                exit_px, reason = pos["target"], "target"
            elif np.isfinite(s50[i]) and c[i] < s50[i] and i - pos["i"] > 5:
                exit_px, reason = float(c[i]), "trend break"
            elif i - pos["i"] > MAX_HOLD:
                exit_px, reason = float(c[i]), "time"

            if exit_px is not None:
                trades.append({"ret": exit_px / pos["entry"] - 1,
                               "bars": i - pos["i"], "reason": reason})
                pos = None

        return _summarise(
            trades, c, n,
            rule=(f"Long: buy when price is above its 200-day average and momentum turns up. "
                  f"Exit at {TARGET_R:g}x the risk, at a {STOP_ATR:g}-ATR stop, on a break of "
                  f"the 50-day average, or after {MAX_HOLD} bars."),
        )
    except Exception as exc:
        return _empty_result(f"Long backtest failed: {exc}")


def _run_short(arrays: dict[str, np.ndarray]) -> dict[str, Any]:
    """Backtest the short-side rule: short when trend is down and momentum turns."""
    try:
        c, h, l = arrays["c"], arrays["h"], arrays["l"]
        s50, s200 = arrays["s50"], arrays["s200"]
        rsi, hist = arrays["rsi"], arrays["hist"]
        at = ind.atr(h, l, c, 14)
        n = len(c)

        trades: list[dict[str, Any]] = []
        pos = None

        for i in range(WARMUP, n):
            if pos is None:
                # Short entry: price below 200-day AND momentum turns down
                trend_down = np.isfinite(s200[i]) and c[i] < s200[i]
                rsi_cross_down = (np.isfinite(rsi[i]) and np.isfinite(rsi[i - 1])
                                  and rsi[i - 1] > 55 >= rsi[i])
                macd_cross_down = (np.isfinite(hist[i]) and np.isfinite(hist[i - 1])
                                   and hist[i - 1] > 0 >= hist[i])
                if trend_down and (rsi_cross_down or macd_cross_down) and np.isfinite(at[i]) and at[i] > 0:
                    entry = float(c[i])
                    stop = entry + STOP_ATR * at[i]      # stop above for shorts
                    target = entry - TARGET_R * (stop - entry)  # target below
                    pos = {"i": i, "entry": entry, "stop": stop, "target": max(target, 0.01)}
                continue

            exit_px, reason = None, ""
            if h[i] >= pos["stop"]:
                exit_px, reason = pos["stop"], "stop"
            elif l[i] <= pos["target"]:
                exit_px, reason = pos["target"], "target"
            elif np.isfinite(s50[i]) and c[i] > s50[i] and i - pos["i"] > 5:
                exit_px, reason = float(c[i]), "trend break"
            elif i - pos["i"] > MAX_HOLD:
                exit_px, reason = float(c[i]), "time"

            if exit_px is not None:
                # Short profit: entry - exit (you sold high, buy back low)
                trades.append({"ret": pos["entry"] / exit_px - 1,
                               "bars": i - pos["i"], "reason": reason})
                pos = None

        return _summarise(
            trades, c, n,
            rule=(f"Short: sell when price is below its 200-day average and momentum turns down. "
                  f"Cover at {TARGET_R:g}x the risk, at a {STOP_ATR:g}-ATR stop, on a break above "
                  f"the 50-day average, or after {MAX_HOLD} bars."),
        )
    except Exception as exc:
        return _empty_result(f"Short backtest failed: {exc}")


def _summarise(trades: list[dict[str, Any]], c: np.ndarray, n: int, rule: str) -> dict[str, Any]:
    """Compute summary statistics from a list of trades."""
    try:
        wins = [t["ret"] for t in trades if t["ret"] > 0]
        losses = [t["ret"] for t in trades if t["ret"] <= 0]
        count = len(trades)
        win_rate = len(wins) / count if count else 0.0
        avg_win = float(np.mean(wins)) if wins else 0.0
        avg_loss = float(np.mean(losses)) if losses else 0.0
        expectancy = win_rate * avg_win + (1 - win_rate) * avg_loss

        equity = [1.0]
        for t in trades:
            equity.append(equity[-1] * (1 + t["ret"]))

        buy_hold = float(c[-1] / c[WARMUP] - 1) if n > WARMUP else 0.0

        if count == 0:
            note = ("No trade ever triggered on this window. Either the history is too short or the "
                    "market never met the entry conditions.")
        elif count < 12:
            note = ("Fewer than a dozen trades. That is far too small a sample to trust — treat these "
                    "numbers as noise.")
        elif expectancy <= 0:
            note = "Negative expectancy: this rule lost money on this market over this window. Don't run it here."
        else:
            note = "Positive on this window only. Re-run with a longer history before believing it."

        return {
            "rule": rule,
            "trades": count,
            "win_rate": round(win_rate * 100, 1),
            "avg_win": round(avg_win * 100, 2),
            "avg_loss": round(avg_loss * 100, 2),
            "expectancy": round(expectancy * 100, 2),
            "net_return": round((equity[-1] - 1) * 100, 2),
            "buy_hold_return": round(buy_hold * 100, 2),
            "max_drawdown": round(ind.max_drawdown(np.array(equity)) * 100, 2),
            "avg_bars_held": round(float(np.mean([t["bars"] for t in trades])), 1) if count else 0.0,
            "stopped_out": sum(1 for t in trades if t["reason"] == "stop"),
            "note": note,
        }
    except Exception as exc:
        return _empty_result(f"Summary failed: {exc}")


def _empty_result(note: str) -> dict[str, Any]:
    """Return a valid but empty backtest result."""
    return {
        "rule": "N/A",
        "trades": 0,
        "win_rate": 0.0,
        "avg_win": 0.0,
        "avg_loss": 0.0,
        "expectancy": 0.0,
        "net_return": 0.0,
        "buy_hold_return": 0.0,
        "max_drawdown": 0.0,
        "avg_bars_held": 0.0,
        "stopped_out": 0,
        "note": note,
    }


def run(arrays: dict[str, np.ndarray], direction: str = "long") -> dict[str, Any]:
    """Run the backtest for the given direction."""
    try:
        if direction == "short":
            return _run_short(arrays)
        return _run_long(arrays)
    except Exception as exc:
        return _empty_result(f"Backtest failed: {exc}")
