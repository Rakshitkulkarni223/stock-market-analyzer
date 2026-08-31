# Market Desk

Risk-first technical analysis for stocks, indices, crypto and metals. React frontend,
FastAPI backend, no API keys, no database.

**It cannot promise you won't lose money.** Nothing can. What it does instead is put the
downside first: a stop-loss price, the loss in currency terms, and a position size that keeps
one wrong call to a percent of your account. Many of its verdicts are *don't trade this* — that
is the feature, not a gap.

---

## Running it

Two terminals. Python 3.10+ and Node 18+.

**Backend**

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload      # http://127.0.0.1:8000
```

Interactive API docs at <http://127.0.0.1:8000/docs>.

**Frontend**

```bash
cd frontend
npm install
npm run dev                        # http://localhost:5173
```

The Vite dev server proxies `/api` to `127.0.0.1:8000`, so the browser talks to one origin and
CORS never comes up. To point at a backend somewhere else, copy `.env.example` to `.env` and set
`VITE_PROXY_TARGET` (dev) or `VITE_API_BASE` (production build).

**Docker**

```bash
docker compose up --build          # frontend on :5173, backend on :8000
```

**Tests**

```bash
cd backend && pytest -q            # 33 offline tests, no network needed
```

---

## Why there is a backend at all

The single-file browser version of this tool kept getting blocked by CORS on Yahoo Finance.
Fetching server-side fixes that permanently: Python has no same-origin policy. The backend also
holds the risk rules in one place, so the position-size warnings can't drift out of sync with
whatever the UI happens to render.

Price data comes from `yfinance`, with a direct HTTP call to Yahoo's chart endpoint as a fallback,
and Binance's public REST API for crypto. Series are cached in memory for five minutes.

---

## API

| Method | Path                  | Purpose                                                |
| ------ | --------------------- | ------------------------------------------------------ |
| GET    | `/api/health`         | liveness plus cache size                               |
| GET    | `/api/universe`       | the pickable catalog, valid ranges and holding styles  |
| GET    | `/api/analyse`        | analyse a symbol — `?symbol=^NSEI&range=2y&style=swing` |
| POST   | `/api/analyse/csv`    | analyse an uploaded CSV (`file` or `text` form field)   |
| POST   | `/api/position-size`  | units to buy for a capital, risk %, entry and stop      |
| POST   | `/api/cache/clear`    | drop the price cache                                   |

```bash
curl 'http://127.0.0.1:8000/api/analyse?symbol=BTCUSDT&source=binance&range=2y&style=swing'

curl -X POST http://127.0.0.1:8000/api/position-size \
  -H 'Content-Type: application/json' \
  -d '{"capital":100000,"risk_pct":1,"entry":1420,"stop":1355,"target":1550}'

curl -X POST http://127.0.0.1:8000/api/analyse/csv \
  -F file=@RELIANCE.csv -F style=swing
```

`symbol` is not restricted to the catalog — any Yahoo ticker works (`ASIANPAINT.NS`, `BRK-B`,
`^VIX`). Add rows to `backend/app/universe.py` to make them pickable in the UI.

### Analyse response, abridged

```jsonc
{
  "asset":   { "name": "NIFTY 50", "symbol": "^NSEI", "currency_symbol": "₹", "source": "yahoo" },
  "meta":    { "bars": 620, "price": 24812.4, "change_pct": 0.42, "atr_pct": 0.81,
               "high_52w": 26277.3, "low_52w": 21281.4, "thin_history": false },
  "verdict": { "headline": "Worth a starter position, not a full one",
               "why": "...", "tone": "neutral", "score": 3.1 },
  "plan":    { "entry_low": 24610, "entry_high": 24812, "stop": 24310,
               "target1": 25315, "target2": 25920, "risk_per_unit": 401, "rr1": 2.0, "rr2": 3.5 },
  "factors": [ { "label": "Price vs 200-day average", "value": "6.2%",
                 "score": 2.0, "note": "long-term uptrend intact" } ],
  "levels":  [ { "kind": "resistance", "price": 25315, "hits": 3, "distance_pct": 2.0 } ],
  "series":  { "t": [], "o": [], "h": [], "l": [], "c": [],
               "sma20": [], "sma50": [], "sma200": [],
               "bb_upper": [], "bb_lower": [], "rsi": [], "macd_hist": [] },
  "backtest":{ "trades": 18, "win_rate": 44.4, "expectancy": 0.61,
               "net_return": 11.2, "buy_hold_return": 14.8, "max_drawdown": 7.4, "note": "..." },
  "seasonality": { "months": [ { "name": "Jan", "avg_pct": 0.07, "n": 52 } ], "weekdays": [] }
}
```

Every `series` array is the same length as `t`, front-padded with `null` where the indicator
isn't defined yet, so the frontend can index by bar without bookkeeping.

---

## How the verdict is reached

`backend/app/analysis.py` scores about ten independent readings — trend (price vs the 20, 50 and
200-day averages), momentum (RSI, MACD histogram direction), trend strength (ADX), location
relative to support and resistance clusters, volatility (ATR as a share of price), and position
in the 52-week range. Each contributes a signed number with a plain-English note, and the UI shows
all of them so you can disagree with any one.

Two rules sit above the score and can override it:

- **Thin history.** Under 120 bars, it refuses to judge rather than pretending.
- **Bear regime.** If price is below its 200-day average *and* the 50-day is below the 200-day,
  the verdict is "don't buy" no matter how good short-term momentum looks. A bounce inside a
  downtrend is the most expensive-looking setup there is. The gate only ever restricts buying —
  it never turns a caution into a green light.

The trade plan derives from ATR rather than round numbers: the stop sits 1.5 ATR (swing) or
2.2 ATR (position) below the entry zone, or below the nearest defended low, whichever is further.
Targets are 2x and 3.5x the risk, clipped back when a resistance cluster sits in the way — which
is often why the reward-to-risk comes out too low and the verdict becomes "wait for a pullback".

---

## CSV import

For anything the providers can't reach, or for exchanges they don't cover. The parser handles the
exports from Yahoo Finance, NSE and Investing.com: comma, semicolon or tab delimited, headers in
any order, `Date,Open,High,Low,Close,Volume` or just date and close, oldest-first or newest-first,
quoted thousands separators, and `YYYY-MM-DD` / `DD-MM-YYYY` / `DD-Mon-YYYY` dates. Minimum 40
rows; below 120 it will tell you the history is too thin to judge.

---

## Layout

```
market-desk/
├── backend/
│   ├── app/
│   │   ├── main.py           FastAPI routes, CORS, position sizing
│   │   ├── analysis.py       scoring, support/resistance, trade plan, verdict
│   │   ├── indicators.py     SMA, EMA, RSI, MACD, Bollinger, ATR, ADX, pivots
│   │   ├── backtest.py       walks the suggested rule over the loaded window
│   │   ├── seasonality.py    average move by month and weekday, with sample counts
│   │   ├── providers.py      yfinance / Yahoo HTTP / Binance / CSV, plus a TTL cache
│   │   └── universe.py       the pickable asset catalog
│   ├── tests/test_analysis.py
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── App.jsx           state and layout
    │   ├── api.js            fetch wrappers and number formatting
    │   └── components/
    │       ├── AssetPicker.jsx     category tabs, search, range, style, CSV import
    │       ├── RiskLadder.jsx      the hero: stop → buy zone → targets on one scale
    │       ├── PriceChart.jsx      canvas candles, averages, bands, plan levels, RSI, MACD
    │       ├── PositionSizer.jsx   calls the backend so risk rules have one home
    │       ├── IndicatorTable.jsx  every reading and its contribution
    │       ├── BacktestPanel.jsx   the disillusionment panel
    │       ├── Seasonality.jsx     month and weekday averages
    │       ├── LevelsTable.jsx     support and resistance with touch counts
    │       ├── Ticker.jsx          name, price, day change, ATR
    │       └── Limits.jsx          what this cannot tell you
    └── vite.config.js
```

The chart is hand-drawn on a canvas rather than pulled from a charting library — it keeps the
dependency list to React alone and lets the plan levels sit in the same coordinate space as
the candles.

---

## Known limits

- Daily bars only. No intraday, no options, no futures roll handling.
- The backtest assumes fills at your exact price with no slippage, and ignores brokerage, STT
  and taxes. Real returns come out lower than the panel shows.
- Backtest results are fitted to the window you loaded. Change the range and watch them move —
  that instability is the honest signal about how much to trust them.
- `yfinance` breaks from time to time when Yahoo changes its endpoints. The HTTP fallback usually
  survives it; CSV import always does.
- Seasonality on a two-year window means roughly 40 observations per month. That is a coincidence
  more often than a pattern, which is why every bucket ships its sample count.

Information only, not investment advice. For money you can't afford to lose, talk to a registered
investment adviser.
