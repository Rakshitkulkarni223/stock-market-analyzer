"""Offline tests. No network, no API keys — run with `pytest` from backend/.

These exist so you can change the scoring rules and immediately see whether the
trade plan still makes structural sense (stop below entry, targets above it,
downtrends scored negative, and so on).
"""
from __future__ import annotations

import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import analysis, backtest, indicators as ind, providers, seasonality  # noqa: E402

DAY_MS = 86_400_000


def series(n: int, fn, start: float = 100.0) -> list[dict]:
    """Build n daily bars from a price function of the bar index."""
    t0 = int((datetime.now(tz=timezone.utc) - timedelta(days=n)).timestamp() * 1000)
    bars, p = [], start
    for i in range(n):
        p = fn(i, p)
        bars.append({"t": t0 + i * DAY_MS, "o": p * 0.999, "h": p * 1.007,
                     "l": p * 0.993, "c": p, "v": 1_000_000})
    return bars


def uptrend(n=520):
    return series(n, lambda i, p: p * (1 + 0.0018 + math.sin(i / 11) * 0.004))


def downtrend(n=520):
    return series(n, lambda i, p: p * (1 - 0.0016 + math.sin(i / 9) * 0.006), start=5000)


def choppy(n=520):
    return series(n, lambda i, p: 200 + math.sin(i / 6) * 4 + math.cos(i / 17) * 2)


def noisy(n=700, seed=7):
    rng = np.random.default_rng(seed)
    return series(n, lambda i, p: p * (1 + 0.0004 + float(rng.normal(0, 0.011))), start=21000)


# --------------------------------------------------------------------- indicators
def test_sma_matches_manual_mean():
    v = np.arange(1, 11, dtype=float)
    out = ind.sma(v, 3)
    assert np.isnan(out[:2]).all()
    assert out[2] == pytest.approx(2.0)
    assert out[-1] == pytest.approx(9.0)


def test_rsi_bounds_and_extremes():
    up = np.arange(1, 60, dtype=float)
    r = ind.rsi(up, 14)
    assert r[-1] == pytest.approx(100.0)
    vals = ind.rsi(np.array([b["c"] for b in noisy()]), 14)
    finite = vals[np.isfinite(vals)]
    assert finite.min() >= 0 and finite.max() <= 100


def test_atr_is_positive_and_scaled():
    bars = noisy()
    h = np.array([b["h"] for b in bars])
    l = np.array([b["l"] for b in bars])
    c = np.array([b["c"] for b in bars])
    a = ind.atr(h, l, c, 14)
    finite = a[np.isfinite(a)]
    assert (finite > 0).all()
    assert finite[-1] < c[-1] * 0.5


def test_macd_hist_is_line_minus_signal():
    c = np.array([b["c"] for b in noisy()])
    m = ind.macd(c)
    idx = np.isfinite(m.hist)
    assert np.allclose(m.hist[idx], (m.line - m.signal)[idx])


def test_adx_in_range():
    bars = uptrend()
    a = ind.adx(np.array([b["h"] for b in bars]), np.array([b["l"] for b in bars]),
                np.array([b["c"] for b in bars]), 14).adx
    finite = a[np.isfinite(a)]
    assert len(finite) and finite.min() >= 0 and finite.max() <= 100


def test_max_drawdown():
    assert ind.max_drawdown(np.array([1.0, 1.2, 0.6, 0.9])) == pytest.approx(0.5)
    assert ind.max_drawdown(np.array([1.0, 1.1, 1.2])) == pytest.approx(0.0)


def test_clean_replaces_nan_with_none():
    assert ind.clean(np.array([1.5, np.nan, 3.0])) == [1.5, None, 3.0]


# --------------------------------------------------------------------- analysis
@pytest.mark.parametrize("bars", [uptrend(), downtrend(), choppy(), noisy()])
@pytest.mark.parametrize("style", ["swing", "position"])
def test_plan_is_structurally_sane(bars, style):
    r = analysis.analyse(bars, style)
    p = r["plan"]
    assert p["stop"] < p["entry_low"] <= p["entry_high"]
    assert p["target1"] > p["entry_mid"]
    assert p["target2"] >= p["target1"]
    assert p["risk_per_unit"] > 0
    assert all(math.isfinite(v) for v in p.values())
    assert r["verdict"]["headline"]
    assert r["verdict"]["tone"] in ("positive", "neutral", "negative")


def test_every_factor_scores_a_finite_number():
    r = analysis.analyse(noisy(), "swing")
    assert r["factors"]
    for f in r["factors"]:
        assert math.isfinite(f["score"])
        assert f["label"] and f["note"]


def test_uptrend_scores_above_downtrend():
    up = analysis.analyse(uptrend(), "swing")
    down = analysis.analyse(downtrend(), "swing")
    assert up["verdict"]["score"] > down["verdict"]["score"]
    assert down["verdict"]["tone"] == "negative"
    assert "Don't buy" in down["verdict"]["headline"]


def test_bear_regime_gate_beats_a_positive_bounce():
    """Price under the 200-day with the 50 under the 200 must never read as a buy,
    even when short-term momentum has turned up."""
    bars = series(520, lambda i, p: p * (1 - 0.0016 + math.sin(i / 9) * 0.006), start=5000)
    r = analysis.analyse(bars, "swing")
    assert r["verdict"]["tone"] == "negative"
    assert "Downtrend" in r["verdict"]["headline"]
    # the individual factors may well be net-positive on the bounce; the gate still holds
    assert any(f["score"] > 0 for f in r["factors"])


def test_thin_history_refuses_to_judge():
    r = analysis.analyse(noisy()[-90:], "swing")
    assert r["meta"]["thin_history"] is True
    assert "Not enough history" in r["verdict"]["headline"]
    assert r["verdict"]["score"] == 0


def test_too_short_raises():
    with pytest.raises(ValueError):
        analysis.analyse(noisy()[-20:], "swing")


def test_series_arrays_align_with_bars():
    bars = noisy()
    r = analysis.analyse(bars, "swing")
    s = r["series"]
    assert all(len(v) == len(bars) for v in s.values())
    assert r["meta"]["bars"] == len(bars)


def test_levels_are_sorted_around_price():
    r = analysis.analyse(noisy(), "swing")
    px = r["meta"]["price"]
    for lv in r["levels"]:
        assert lv["hits"] >= 1
        if lv["kind"] == "resistance":
            assert lv["price"] > px
        else:
            assert lv["price"] < px


# --------------------------------------------------------------------- backtest
def test_backtest_reports_consistent_arithmetic():
    r = analysis.analyse(noisy(), "swing")
    arrays = r.pop("_arrays")
    b = backtest.run(arrays)
    assert b["trades"] >= 0
    assert 0 <= b["win_rate"] <= 100
    assert b["stopped_out"] <= b["trades"]
    assert b["max_drawdown"] >= 0
    assert b["note"]
    if b["trades"]:
        expected = (b["win_rate"] / 100 * b["avg_win"]
                    + (1 - b["win_rate"] / 100) * b["avg_loss"])
        assert b["expectancy"] == pytest.approx(expected, abs=0.02)


def test_backtest_on_thin_history_is_empty_not_broken():
    r = analysis.analyse(noisy()[-100:], "swing")
    b = backtest.run(r.pop("_arrays"))
    assert b["trades"] == 0
    assert "No trade ever triggered" in b["note"]


# --------------------------------------------------------------------- seasonality
def test_seasonality_shape_and_counts():
    bars = noisy()
    s = seasonality.run(bars)
    assert len(s["months"]) == 12
    assert len(s["weekdays"]) == 5
    assert sum(m["n"] for m in s["months"]) == len(bars) - 1
    assert s["note"]


# --------------------------------------------------------------------- csv
def _csv(bars, header=True, delim=",", reverse=False, cols=("date", "o", "h", "l", "c")):
    rows = []
    if header:
        names = {"date": "Date", "o": "Open", "h": "High", "l": "Low", "c": "Close"}
        rows.append(delim.join(names[c] for c in cols))
    body = list(reversed(bars)) if reverse else bars
    for b in body:
        d = datetime.fromtimestamp(b["t"] / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        vals = {"date": d, "o": f"{b['o']:.2f}", "h": f"{b['h']:.2f}",
                "l": f"{b['l']:.2f}", "c": f"{b['c']:.2f}"}
        rows.append(delim.join(vals[c] for c in cols))
    return "\n".join(rows)


def test_csv_yahoo_style():
    bars = noisy(300)
    parsed = providers.parse_csv(_csv(bars))
    assert len(parsed) == len(bars)
    assert parsed[0]["t"] < parsed[-1]["t"]


def test_csv_newest_first_is_sorted():
    bars = noisy(300)
    parsed = providers.parse_csv(_csv(bars, reverse=True))
    assert parsed[0]["t"] < parsed[-1]["t"]


def test_csv_close_only_backfills_ohlc():
    bars = noisy(300)
    parsed = providers.parse_csv(_csv(bars, cols=("date", "c")))
    assert len(parsed) == len(bars)
    assert parsed[10]["o"] == parsed[10]["c"]


def test_csv_semicolon_and_indian_dates():
    bars = noisy(200)
    rows = ["Date;Open;High;Low;Close"]
    for b in bars:
        d = datetime.fromtimestamp(b["t"] / 1000, tz=timezone.utc).strftime("%d-%m-%Y")
        rows.append(f"{d};{b['o']:.2f};{b['h']:.2f};{b['l']:.2f};{b['c']:.2f}")
    assert len(providers.parse_csv("\n".join(rows))) == len(bars)


def test_csv_thousands_separators():
    bars = noisy(120)
    rows = ["Date,Close"]
    for b in bars:
        d = datetime.fromtimestamp(b["t"] / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        rows.append(f'{d},"{b["c"]:,.2f}"')
    assert len(providers.parse_csv("\n".join(rows))) == len(bars)


def test_csv_too_short_raises_with_a_useful_message():
    with pytest.raises(providers.DataError) as exc:
        providers.parse_csv("Date,Close\n2024-01-01,100\n2024-01-02,101")
    assert "40 rows" in str(exc.value)


def test_csv_end_to_end_into_analysis():
    bars = providers.parse_csv(_csv(noisy(400)))
    r = analysis.analyse(bars, "swing")
    assert r["plan"]["stop"] < r["plan"]["entry_low"]
