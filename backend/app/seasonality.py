"""Average daily move grouped by calendar month and weekday.

Every bucket ships its sample count, because a "seasonal pattern" built on
twenty observations is a coincidence with a nice chart.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import numpy as np

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]
TRUSTWORTHY_N = 60


def run(bars: list[dict]) -> dict[str, Any]:
    months: list[list[float]] = [[] for _ in range(12)]
    days: list[list[float]] = [[] for _ in range(5)]

    for prev, cur in zip(bars, bars[1:]):
        if not prev["c"]:
            continue
        ret = cur["c"] / prev["c"] - 1
        d = datetime.fromtimestamp(cur["t"] / 1000, tz=timezone.utc)
        months[d.month - 1].append(ret)
        if d.weekday() <= 4:
            days[d.weekday()].append(ret)

    def bucket(groups: list[list[float]], names: list[str]) -> list[dict[str, Any]]:
        return [{"name": names[i],
                 "avg_pct": round(float(np.mean(g)) * 100, 4) if g else 0.0,
                 "n": len(g)}
                for i, g in enumerate(groups)]

    m = bucket(months, MONTHS)
    d = bucket(days, WEEKDAYS)
    strongest = max(m, key=lambda x: x["avg_pct"])
    weakest = min(m, key=lambda x: x["avg_pct"])
    thinnest = min(x["n"] for x in m)

    tail = (" — nowhere near enough to act on." if thinnest < TRUSTWORTHY_N
            else ", so read it as a tendency, not a schedule.")
    note = (f"Average daily move by calendar period, from {len(bars)} bars. "
            f"Strongest: {strongest['name']}. Weakest: {weakest['name']}. "
            f"Thinnest month has only {thinnest} observations{tail}")

    return {"months": m, "weekdays": d, "note": note,
            "strongest_month": strongest["name"], "weakest_month": weakest["name"]}
